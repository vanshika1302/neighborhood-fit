"""Filter on hard limits, then rank by weighted fit score.

Pure functions over plain dicts so the JS scorer in site/ can mirror them exactly.
Row shape: {neighborhood_id, name, rent, minutes, nice}.
"""
import math

W_RENT, W_COMMUTE, W_NICE = 0.5, 0.4, 0.1
TAGS = ("walkability", "beach", "nightlife")


def nice_to_have(tags: dict) -> float:
    return sum(tags[t] for t in TAGS) / len(TAGS)


def _round_half_up(x: float) -> int:
    # Explicit half-up so Python and JS (Math.round) agree; format() and toFixed() don't.
    return math.floor(x + 0.5)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def rank(rows: list[dict], budget: float, max_commute: float, hub_name: str) -> list[dict]:
    survivors = [r for r in rows if r["rent"] <= budget and r["minutes"] <= max_commute]
    if not survivors:
        return []

    headroom = {r["neighborhood_id"]: _clamp01((budget - r["rent"]) / budget) for r in survivors}
    lo, hi = min(headroom.values()), max(headroom.values())

    results = []
    for r in survivors:
        h = headroom[r["neighborhood_id"]]
        # Relative to survivors; if all tie there is nothing to separate, so full marks.
        rent_score = (h - lo) / (hi - lo) if hi > lo else 1.0
        commute_score = _clamp01(1 - r["minutes"] / max_commute)
        score = W_RENT * rent_score + W_COMMUTE * commute_score + W_NICE * r["nice"]
        results.append({
            **r,
            "score": round(score, 4),
            "why": f"${_round_half_up(budget - r['rent']):,} under budget, {_round_half_up(r['minutes'])} min to {hub_name}",
        })
    results.sort(key=lambda x: (-x["score"], x["name"]))
    return results
