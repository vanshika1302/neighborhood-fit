"""Pre-generate one-line "why" explanations with `claude -p` for preset scenarios.

The static site can't call an LLM, so we run each preset (budget x max commute x hub) once
offline and ship site/data/why.json. The page uses an entry only when the sliders exactly
match a preset, and falls back to the template why otherwise.

Run: python -m neighborhood_fit.why [--only KEY] [--force]   (resumable: existing keys are skipped)
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from neighborhood_fit.export import OUT as NEIGHBORHOODS_JSON
from neighborhood_fit.score import rank

WHY_JSON = NEIGHBORHOODS_JSON.parent / "why.json"
BUDGETS = [2600, 3000, 3500]
COMMUTES = [20, 30, 45]
MODEL = "haiku"
MAX_LEN = 140
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
# Cross-neighborhood comparisons can't be verified automatically and the model got them wrong
# in testing (e.g. "shortest commute" for a neighborhood that wasn't), so they are rejected.
COMPARATIVES = re.compile(
    r"\b(lowest|highest|cheapest|priciest|shortest|longest|fastest|quickest|slowest|closest|farthest|"
    r"tightest|strongest|weakest|best|worst|most|least|fewest|than|cheaper|closer|shorter|longer|"
    r"higher|lower|faster|slower|tighter|stronger|weaker|more|less|fewer|among|others)\b",
    re.IGNORECASE,
)


def key(budget, commute, hub_id) -> str:
    return f"{budget}|{commute}|{hub_id}"


def _round(x: float) -> int:
    return int(x + 0.5)


def facts(results: list[dict], by_id: dict, budget: int) -> list[dict]:
    out = []
    for r in results:
        n = by_id[r["neighborhood_id"]]
        out.append({
            "id": r["neighborhood_id"],
            "name": r["name"],
            "rent_per_month": _round(r["rent"]),
            "under_budget_by": _round(budget - r["rent"]),
            "drive_minutes": r["minutes"] if r["minutes"] >= 0.5 else "under 1",
            "rent_change_vs_last_year_pct": n["yoy_pct"],
            "walkability_0_to_1": n["walkability"],
            "beach_0_to_1": n["beach"],
            "nightlife_0_to_1": n["nightlife"],
        })
    return out


def allowed_numbers(fs: list[dict], budget: int, commute: int) -> set[str]:
    nums = {str(budget), str(commute), f"{budget:,}"}
    for f in fs:
        for k in ("rent_per_month", "under_budget_by"):
            nums |= {str(f[k]), f"{f[k]:,}"}
        m = f["drive_minutes"]
        if isinstance(m, str):
            nums.add("1")  # "under 1 minute"
        else:
            nums |= {str(_round(m)), str(m)}
        if f["rent_change_vs_last_year_pct"] is not None:
            nums.add(str(f["rent_change_vs_last_year_pct"]))
    return nums


def build_prompt(fs: list[dict], hub_name: str, budget: int, commute: int) -> str:
    return f"""You write one-line explanations for a San Diego neighborhood-ranking tool.

A renter has a ${budget:,}/month rent budget and will accept at most {commute} minutes of driving to {hub_name}.
These neighborhoods passed those limits, listed best fit first (rent headroom counts most, then shorter commute, then walkability/beach/nightlife):

{json.dumps(fs, indent=1)}

For each neighborhood write ONE sentence, at most 110 characters, saying why it fits this renter.
Rules:
- Describe each neighborhood on its own terms using its own numbers. Do NOT compare it to the other neighborhoods: no superlatives or comparatives (lowest, shortest, most, best, cheaper, closer, more than...). Your comparisons are not checked and have been wrong before.
- Use only the facts above. Do not invent amenities, landmarks, safety claims, prices or anything not given.
- Any number you write must appear in that neighborhood's facts or be the budget or commute limit. Never mention rank or score.
- Tag values near 1 mean strong, near 0 mean weak; describe them in words, not numbers.
- The neighborhood name is already shown above your sentence, so do not start with it. Vary sentence openings.
- Round drive minutes to whole numbers. Lead with what stands out for this renter (rent headroom, short drive, or a strong tag) and add one honest tradeoff when a tag is weak.
- Plain, specific, no hype, no emoji.

Reply with ONLY a JSON object mapping each id to its sentence, no code fences, no other text."""


def parse_and_validate(text: str, fs: list[dict], budget: int, commute: int) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    data = json.loads(text)
    ids = {f["id"] for f in fs}
    if set(data) != ids:
        raise ValueError(f"ids mismatch: missing {sorted(ids - set(data))}, extra {sorted(set(data) - ids)}")
    ok = allowed_numbers(fs, budget, commute)
    for i, line in data.items():
        if not isinstance(line, str) or "\n" in line or not 15 <= len(line) <= MAX_LEN:
            raise ValueError(f"{i}: bad line {line!r}")
        m = COMPARATIVES.search(line)
        if m:
            raise ValueError(f"{i}: comparison word {m.group(0)!r}: {line!r}")
        bad = [n for n in NUM_RE.findall(line) if n.rstrip(".,") not in ok]
        if bad:
            raise ValueError(f"{i}: numbers not in facts {bad}: {line!r}")
    return data


def run_claude(prompt: str, timeout: int = 600) -> str:
    # cwd is a throwaway dir so no project files or CLAUDE.md are picked up. start_new_session lets us
    # kill the whole process group on timeout; killing only `claude` left children holding the pipes open.
    with tempfile.TemporaryDirectory() as tmp:
        p = subprocess.Popen(
            ["claude", "-p", "--model", MODEL, "--effort", "low", "--tools", "", "--no-session-persistence",
             "--output-format", "text"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=tmp, start_new_session=True,
        )
        try:
            out, err = p.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise RuntimeError(f"claude -p timed out after {timeout}s")
    if p.returncode != 0:
        raise RuntimeError(f"claude -p failed: {err.strip()[:300]}")
    return out


def generate_scenario(data: dict, budget: int, commute: int, hub: dict, runner=run_claude, tries: int = 2):
    by_id = {n["neighborhood_id"]: n for n in data["neighborhoods"]}
    rows = [
        {"neighborhood_id": n["neighborhood_id"], "name": n["name"], "rent": n["rent"],
         "minutes": n["minutes"][hub["hub_id"]], "nice": n["nice"]}
        for n in data["neighborhoods"]
    ]
    results = rank(rows, budget, commute, hub["name"])
    if not results:
        return None
    fs = facts(results, by_id, budget)
    prompt = build_prompt(fs, hub["name"], budget, commute)
    last = None
    for _ in range(tries):
        try:
            return parse_and_validate(runner(prompt), fs, budget, commute)
        except (ValueError, json.JSONDecodeError, RuntimeError) as e:
            last = e
    raise RuntimeError(f"{key(budget, commute, hub['hub_id'])}: {last}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="generate a single scenario key, e.g. 3000|30|downtown")
    ap.add_argument("--force", action="store_true", help="regenerate existing keys")
    args = ap.parse_args()

    data = json.loads(NEIGHBORHOODS_JSON.read_text())
    store = json.loads(WHY_JSON.read_text()) if WHY_JSON.exists() else {"model": MODEL, "scenarios": {}}
    todo = [
        (b, c, h) for h in data["hubs"] for b in BUDGETS for c in COMMUTES
        if (not args.only or key(b, c, h["hub_id"]) == args.only)
        and (args.force or key(b, c, h["hub_id"]) not in store["scenarios"])
    ]
    print(f"{len(todo)} scenarios to generate", file=sys.stderr)

    def work(t):
        b, c, h = t
        try:
            return key(b, c, h["hub_id"]), generate_scenario(data, b, c, h), None
        except Exception as e:
            return key(b, c, h["hub_id"]), None, e

    failures = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fut in as_completed([ex.submit(work, t) for t in todo]):
            k, why, err = fut.result()
            if err:
                failures.append(f"{k}: {err}")
            elif why is None:
                store["scenarios"][k] = {}  # nothing passes the limits; remember so we don't retry
            else:
                store["scenarios"][k] = why
            WHY_JSON.write_text(json.dumps(store, indent=1, sort_keys=True))
    print(f"done: {len(store['scenarios'])} scenarios stored, {len(failures)} failed", file=sys.stderr)
    for f in failures:
        print("FAILED", f, file=sys.stderr)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
