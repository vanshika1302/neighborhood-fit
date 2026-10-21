import json

import pytest

from neighborhood_fit.why import build_prompt, generate_scenario, parse_and_validate

FS = [
    {"id": "a", "name": "Alpha", "rent_per_month": 2248, "under_budget_by": 752, "drive_minutes": 9.3,
     "rent_change_vs_last_year_pct": 1.4, "walkability_0_to_1": 0.6, "beach_0_to_1": 0.0, "nightlife_0_to_1": 0.3},
    {"id": "b", "name": "Bravo", "rent_per_month": 2505, "under_budget_by": 495, "drive_minutes": "under 1",
     "rent_change_vs_last_year_pct": None, "walkability_0_to_1": 0.8, "beach_0_to_1": 0.1, "nightlife_0_to_1": 0.8},
]
GOOD = {"a": "Low rent at $2,248, $752 under budget with a 9 minute drive.",
        "b": "Walkable with lively nightlife and a drive under a minute."}


def check(d):
    return parse_and_validate(json.dumps(d), FS, 3000, 30)


def test_valid_response_passes_and_code_fences_are_stripped():
    assert check(GOOD) == GOOD
    assert parse_and_validate("```json\n" + json.dumps(GOOD) + "\n```", FS, 3000, 30) == GOOD


def test_rejects_invented_numbers():
    with pytest.raises(ValueError, match="numbers not in facts"):
        check({**GOOD, "a": "Just $600 under budget with a 9 minute drive here."})


def test_rejects_cross_neighborhood_comparisons():
    for phrase in ["Shortest commute with $752 under budget.", "Cheaper than most, $752 under budget here.",
                   "Lowest rent on the list, $752 under budget."]:
        with pytest.raises(ValueError, match="comparison word"):
            check({**GOOD, "a": phrase})


def test_rejects_missing_or_extra_ids():
    with pytest.raises(ValueError, match="ids mismatch"):
        check({"a": GOOD["a"]})
    with pytest.raises(ValueError, match="ids mismatch"):
        check({**GOOD, "z": GOOD["a"]})


def test_rejects_multiline_and_overlong():
    with pytest.raises(ValueError):
        check({**GOOD, "a": "Line one is here.\nLine two is here."})
    with pytest.raises(ValueError):
        check({**GOOD, "a": "x" * 141})


def test_prompt_contains_limits_and_facts_but_no_instructions_from_data():
    p = build_prompt(FS, "Downtown San Diego", 3000, 30)
    assert "$3,000/month" in p and "30 minutes" in p and "Alpha" in p


def test_generate_retries_once_then_succeeds():
    data = {
        "hubs": [{"hub_id": "h", "name": "Hub"}],
        "neighborhoods": [
            {"neighborhood_id": "a", "name": "Alpha", "rent": 2248.0, "minutes": {"h": 9.3}, "nice": 0.3,
             "yoy_pct": 1.4, "walkability": 0.6, "beach": 0.0, "nightlife": 0.3},
        ],
    }
    replies = iter(["not json", json.dumps({"a": "Rent of $2,248 leaves $752 under budget, 9 minutes away."})])
    out = generate_scenario(data, 3000, 30, data["hubs"][0], runner=lambda _: next(replies))
    assert list(out) == ["a"]


def test_generate_returns_none_when_nothing_passes():
    data = {"hubs": [{"hub_id": "h", "name": "Hub"}], "neighborhoods": [
        {"neighborhood_id": "a", "name": "Alpha", "rent": 9000.0, "minutes": {"h": 9}, "nice": 0.3,
         "yoy_pct": 1.0, "walkability": 0.5, "beach": 0.5, "nightlife": 0.5}]}
    assert generate_scenario(data, 3000, 30, data["hubs"][0], runner=lambda _: "{}") is None
