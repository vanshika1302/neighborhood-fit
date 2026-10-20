"""Regenerate tests/fixtures/parity.json from the Python scorer (source of truth).

Run: python tests/gen_parity_fixture.py   — then `node --test tests/` checks the JS scorer matches.
"""
import json
from pathlib import Path

from neighborhood_fit.score import rank

ROWS = [
    {"neighborhood_id": "a", "name": "Alpha", "rent": 2248.4, "minutes": 18.5, "nice": 0.55},
    {"neighborhood_id": "b", "name": "Bravo", "rent": 2505.0, "minutes": 7.2, "nice": 0.9},
    {"neighborhood_id": "c", "name": "Charlie", "rent": 3925.0, "minutes": 33.0, "nice": 0.7},
    {"neighborhood_id": "d", "name": "Delta", "rent": 2917.6, "minutes": 12.5, "nice": 0.0},
    {"neighborhood_id": "e", "name": "Echo", "rent": 2917.6, "minutes": 12.5, "nice": 0.0},
]
SCENARIOS = [(3000, 30), (4000, 45), (2600, 20), (2300, 10), (9000, 5), (3000, 12.5)]

cases = [
    {"budget": b, "max_commute": m, "hub_name": "Downtown", "rows": ROWS, "expected": rank(ROWS, b, m, "Downtown")}
    for b, m in SCENARIOS
]
out = Path(__file__).parent / "fixtures/parity.json"
out.write_text(json.dumps(cases, indent=1))
print(f"wrote {len(cases)} cases to {out}")
