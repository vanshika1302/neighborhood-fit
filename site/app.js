const $ = (id) => document.getElementById(id);
const money = (n) => "$" + Math.round(n).toLocaleString("en-US");

async function loadData() {
  for (const url of ["data/neighborhoods.json", "data/neighborhoods.sample.json"]) {
    const res = await fetch(url);
    if (res.ok) return res.json();
  }
  throw new Error("No neighborhood data found");
}

function ui(data) {
  const { hubs, neighborhoods } = data;
  $("sample-banner").hidden = !data.sample;
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
    const byId = Object.fromEntries(neighborhoods.map((n) => [n.neighborhood_id, n]));

    $("summary").textContent = results.length
      ? `${results.length} of ${rows.length} neighborhoods fit your limits.`
      : "";
    $("results").innerHTML = results.length
      ? results.map((r, i) => card(r, i, byId[r.neighborhood_id])).join("")
      : `<li class="empty">Nothing fits. Try raising your budget above ${money(Math.min(...rows.map((r) => r.rent)))}
         or allowing a longer commute (closest option is ${Math.round(Math.min(...rows.map((r) => r.minutes)))} min to ${hub.name}).</li>`;
  }

  ["budget", "commute", "hub"].forEach((id) => $(id).addEventListener("input", render));
  render();
}

function card(r, i, n) {
  const yoy = n.yoy_pct == null ? "" : ` · ${n.yoy_pct > 0 ? "+" : ""}${n.yoy_pct}% rent vs last year`;
  return `<li class="card">
    <span class="rank">${i + 1}</span>
    <span class="name">${r.name}<span class="score" title="Relative fit score">${Math.round(r.score * 100)}</span></span>
    <div class="bar" role="img" aria-label="Fit ${Math.round(r.score * 100)} out of 100"><span style="width:${r.score * 100}%"></span></div>
    <p class="why">${r.why}</p>
    <span class="meta">ZIP ${n.zip} · ${money(r.rent)}/mo${yoy}</span>
  </li>`;
}

loadData().then(ui).catch((e) => { $("results").innerHTML = `<li class="empty">${e.message}</li>`; });
