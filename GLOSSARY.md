# Glossary

- **ZORI** — Zillow Observed Rent Index: smoothed typical asking rent for a ZIP, in USD/month.
- **Neighborhood** — A named area in `data/seed/neighborhoods.csv`, mapped to one representative ZIP. Several neighborhoods may share a ZIP.
- **Hub** — A major job center in `data/seed/hubs.csv` that commute time is measured to.
- **Commute** — Typical (free-flow) driving minutes from a neighborhood centroid to a hub, precomputed via OpenRouteService.
- **Hard limit** — Budget or max commute. A neighborhood over either is excluded, never just down-ranked.
- **Rent headroom** — `(budget - rent) / budget`, clamped to 0–1.
- **Nice-to-have** — Mean of the hand-curated 0–1 tags (walkability, beach, nightlife). Author estimates, not measured data.
- **Fit score** — `0.5·rent headroom + 0.4·commute + 0.1·nice-to-have`; relative to the surviving neighborhoods.
- **Why** — One-line explanation per ranked result (template first, `claude -p` later).
