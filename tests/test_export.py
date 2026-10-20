import csv

import pytest

from neighborhood_fit.export import export
from neighborhood_fit.load import ZORI_CSV, build

pytestmark = pytest.mark.skipif(not ZORI_CSV.exists(), reason="ZORI CSV not downloaded")


def write_commute(path, skip=None):
    from neighborhood_fit.commute import SEED, read_rows
    rows = [
        {"neighborhood_id": n["neighborhood_id"], "hub_id": h["hub_id"], "minutes": 20.0}
        for n in read_rows(SEED / "neighborhoods.csv") for h in read_rows(SEED / "hubs.csv")
    ]
    if skip:
        rows = rows[:-1]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["neighborhood_id", "hub_id", "minutes"])
        w.writeheader()
        w.writerows(rows)


def test_export_shape(tmp_path):
    con = build(tmp_path / "t.duckdb")
    write_commute(tmp_path / "c.csv")
    p = export(con, tmp_path / "c.csv", tmp_path / "out.json")
    assert len(p["neighborhoods"]) == 14 and len(p["hubs"]) == 4
    n = p["neighborhoods"][0]
    assert set(n["minutes"]) == {h["hub_id"] for h in p["hubs"]}
    assert 0 <= n["nice"] <= 1 and n["rent"] > 0


def test_export_fails_on_missing_pair(tmp_path):
    con = build(tmp_path / "t.duckdb")
    write_commute(tmp_path / "c.csv", skip=True)
    with pytest.raises(ValueError):
        export(con, tmp_path / "c.csv", tmp_path / "out.json")
