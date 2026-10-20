"""Precompute driving minutes from each neighborhood to each hub (OpenRouteService free tier).

One-time/rare run. Reads ORS_API_KEY from the environment or a gitignored .env,
writes data/derived/commute_minutes.csv, which is committed.
"""
import csv
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "data/seed"
OUT = ROOT / "data/derived/commute_minutes.csv"
ORS_URL = "https://api.openrouteservice.org/v2/matrix/driving-car"


def read_rows(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def build_request(neighborhoods: list[dict], hubs: list[dict]) -> dict:
    """ORS wants [lon, lat]. Neighborhoods are sources, hubs are destinations."""
    locations = [[float(r["lon"]), float(r["lat"])] for r in neighborhoods + hubs]
    n = len(neighborhoods)
    return {
        "locations": locations,
        "sources": list(range(n)),
        "destinations": list(range(n, n + len(hubs))),
        "metrics": ["duration"],
    }


def parse_response(data: dict, neighborhoods: list[dict], hubs: list[dict]) -> list[dict]:
    rows = []
    for i, n in enumerate(neighborhoods):
        for j, h in enumerate(hubs):
            seconds = data["durations"][i][j]
            if seconds is None:
                raise ValueError(f"No route {n['neighborhood_id']} -> {h['hub_id']}")
            rows.append({
                "neighborhood_id": n["neighborhood_id"],
                "hub_id": h["hub_id"],
                "minutes": round(seconds / 60, 1),
            })
    return rows


def load_key() -> str:
    key = os.environ.get("ORS_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ORS_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("Set ORS_API_KEY in the environment or .env (free key: openrouteservice.org)")
    return key


def main() -> None:
    neighborhoods = read_rows(SEED / "neighborhoods.csv")
    hubs = read_rows(SEED / "hubs.csv")
    resp = requests.post(
        ORS_URL,
        json=build_request(neighborhoods, hubs),
        headers={"Authorization": load_key()},
        timeout=60,
    )
    resp.raise_for_status()
    rows = parse_response(resp.json(), neighborhoods, hubs)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["neighborhood_id", "hub_id", "minutes"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
