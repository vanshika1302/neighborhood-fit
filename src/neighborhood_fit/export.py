"""Export DuckDB tables + commute minutes to site/data/neighborhoods.json for the static dashboard."""
import json
import sys
from pathlib import Path

from neighborhood_fit.load import ROOT, build
from neighborhood_fit.score import TAGS, nice_to_have

COMMUTE_CSV = ROOT / "data/derived/commute_minutes.csv"
OUT = ROOT / "site/data/neighborhoods.json"


def export(con, commute_csv: Path = COMMUTE_CSV, out: Path = OUT) -> dict:
    if not commute_csv.exists():
        sys.exit(f"Missing {commute_csv}. Run `python -m neighborhood_fit.commute` first (needs ORS_API_KEY).")
    con.execute(f"CREATE OR REPLACE TABLE commute AS SELECT * FROM read_csv('{commute_csv}')")

    hubs = [
        {"hub_id": h, "name": n}
        for h, n in con.execute("SELECT hub_id, name FROM hubs ORDER BY hub_id").fetchall()
    ]
    minutes: dict[str, dict[str, float]] = {}
    for nid, hid, m in con.execute("SELECT neighborhood_id, hub_id, minutes FROM commute").fetchall():
        minutes.setdefault(nid, {})[hid] = m

    cols = ["neighborhood_id", "name", "zip", *TAGS, "rent", "yoy_pct", "as_of"]
    q = f"SELECT {', '.join('n.' + c if c in ('neighborhood_id','name','zip',*TAGS) else 'r.' + c for c in cols)} " \
        "FROM neighborhoods n JOIN rent_latest r USING (zip) ORDER BY n.name"
    neighborhoods = []
    for row in con.execute(q).fetchall():
        d = dict(zip(cols, row))
        missing = {h["hub_id"] for h in hubs} - set(minutes.get(d["neighborhood_id"], {}))
        if missing:
            raise ValueError(f"{d['neighborhood_id']} has no commute to {sorted(missing)}")
        d["as_of"] = str(d["as_of"])
        d["nice"] = round(nice_to_have(d), 4)
        d["minutes"] = minutes[d["neighborhood_id"]]
        neighborhoods.append(d)

    payload = {"hubs": hubs, "neighborhoods": neighborhoods}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1))
    return payload


if __name__ == "__main__":
    p = export(build())
    print(f"Exported {len(p['neighborhoods'])} neighborhoods x {len(p['hubs'])} hubs to {OUT}")
