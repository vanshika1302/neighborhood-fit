// JS mirror of src/neighborhood_fit/score.py. Keep in sync; tests/parity.test.mjs enforces it.
const W_RENT = 0.5, W_COMMUTE = 0.4, W_NICE = 0.1;

const fmtMinutes = (m) => (Math.round(m) === 0 ? "<1" : String(Math.round(m)));

const clamp01 = (x) => Math.max(0, Math.min(1, x));

function rank(rows, budget, maxCommute, hubName) {
  const survivors = rows.filter((r) => r.rent <= budget && r.minutes <= maxCommute);
  if (survivors.length === 0) return [];

  const headroom = survivors.map((r) => clamp01((budget - r.rent) / budget));
  const lo = Math.min(...headroom), hi = Math.max(...headroom);

  const results = survivors.map((r, i) => {
    const rentScore = hi > lo ? (headroom[i] - lo) / (hi - lo) : 1.0;
    const commuteScore = clamp01(1 - r.minutes / maxCommute);
    const score = W_RENT * rentScore + W_COMMUTE * commuteScore + W_NICE * r.nice;
    return {
      ...r,
      score: Number(score.toFixed(4)),
      why: `$${Math.round(budget - r.rent).toLocaleString("en-US")} under budget, ${fmtMinutes(r.minutes)} min to ${hubName}`,
    };
  });
  results.sort((a, b) => b.score - a.score || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  return results;
}

if (typeof module !== "undefined") module.exports = { rank };
