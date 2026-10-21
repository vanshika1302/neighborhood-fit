const $ = (id) => document.getElementById(id);
const money = (n) => "$" + Math.round(n).toLocaleString("en-US");

async function loadData() {
  const res = await fetch("data/neighborhoods.json");
  if (!res.ok) throw new Error("No neighborhood data found");
  return res.json();
}

// Pre-generated (claude -p) why lines exist only for preset budget/commute/hub combos.
async function loadWhy() {
  try {
    const res = await fetch("data/why.json");
    return res.ok ? (await res.json()).scenarios : {};
  } catch {
    return {};
  }
}

function ui(data, whyByScenario) {
  const { hubs, neighborhoods } = data;
  $("as-of").textContent = neighborhoods[0].as_of;
  $("hub").innerHTML = hubs.map((h) => `<option value="${h.hub_id}">${h.name}</option>`).join("");

  function render() {
    const budget = +$("budget").value, maxCommute = +$("commute").value;
    const hub = hubs.find((h) => h.hub_id === $("hub").value);
    $("budget-out").textContent = money(budget) + "/mo";
    $("commute-out").textContent = maxCommute + " min";

    const rows = neighborhoods.map((n) => ({
      neighborhood_id: n.neighborhood_id, name: n.name,
      rent: n.rent, minutes: n.minutes[hub.hub_id], nice: n.nice,
    }));
    const results = rank(rows, budget, maxCommute, hub.name);
    const llmWhy = whyByScenario[`${budget}|${maxCommute}|${hub.hub_id}`] || {};
    results.forEach((r) => { r.why = llmWhy[r.neighborhood_id] || r.why; });
    const byId = Object.fromEntries(neighborhoods.map((n) => [n.neighborhood_id, n]));

    $("summary").textContent = results.length
      ? `${results.length} of ${rows.length} neighborhoods fit your limits.`
      : "";
    $("results").innerHTML = results.length
      ? results.map((r, i) => card(r, i, byId[r.neighborhood_id])).join("")
      : `<li class="empty">${emptyMessage(rows, budget, maxCommute, hub)}</li>`;
  }

  ["budget", "commute", "hub"].forEach((id) => $(id).addEventListener("input", render));
  render();
}

// Say which limit is actually the problem instead of suggesting both fixes every time.
function emptyMessage(rows, budget, maxCommute, hub) {
  const by = (key) => (a, b) => a[key] - b[key];
  const affordable = rows.filter((r) => r.rent <= budget);
  const near = rows.filter((r) => r.minutes <= maxCommute);
  if (!affordable.length) {
    const c = [...rows].sort(by("rent"))[0];
    return `Nothing rents for ${money(budget)} or less. The cheapest is ${c.name} at ${money(c.rent)}/mo.`;
  }
  if (!near.length) {
    const c = [...rows].sort(by("minutes"))[0];
    return `Nothing is within ${maxCommute} min of ${hub.name}. The closest is ${c.name} at ${fmtMinutes(c.minutes)} min.`;
  }
  const a = [...affordable].sort(by("minutes"))[0];
  const c = [...near].sort(by("rent"))[0];
  return `No neighborhood meets both limits. Within budget, the closest to ${hub.name} is ${a.name} at ${fmtMinutes(a.minutes)} min (try a max commute of ${Math.ceil(a.minutes)}+). `
    + `Within ${maxCommute} min, the cheapest is ${c.name} at ${money(c.rent)}/mo.`;
}

function card(r, i, n) {
  const yoy = n.yoy_pct == null ? "" : ` · ${n.yoy_pct > 0 ? "+" : ""}${n.yoy_pct}% rent vs last year`;
  return `<li class="card">
    <span class="rank">${i + 1}</span>
    <span class="name">${r.name}<span class="score" title="Relative fit score">${Math.round(r.score * 100)}</span></span>
    <div class="bar" role="img" aria-label="Fit ${Math.round(r.score * 100)} out of 100"><span style="width:${r.score * 100}%"></span></div>
    <p class="why">${r.why}</p>
    <span class="meta">ZIP ${n.zip} · ${money(r.rent)}/mo · ${fmtMinutes(r.minutes)} min drive${yoy}</span>
  </li>`;
}

Promise.all([loadData(), loadWhy()]).then(([data, why]) => ui(data, why)).catch((e) => { $("results").innerHTML = `<li class="empty">${e.message}</li>`; });
