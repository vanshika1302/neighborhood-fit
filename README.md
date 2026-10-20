# Neighborhood Fit

Find which San Diego neighborhoods fit your rent budget and commute. Live site: https://vanshika1302.github.io/neighborhood-fit/

Filter on hard limits (budget, max commute to a chosen job hub), then rank by a weighted score:
rent headroom 50%, commute 40%, nice-to-have (walkability, beach, nightlife) 10%, with a one-line "why" per result.
See `GLOSSARY.md` for terms and `docs/adr/` for design decisions.

## Data sources and limitations

- **Rent:** [Zillow Observed Rent Index](https://www.zillow.com/research/data/) (ZORI), ZIP level, smoothed, all homes + multifamily.
  Each neighborhood maps to one representative ZIP, so neighborhoods that share a ZIP share a rent figure, and a ZIP average can hide a lot of variation inside a neighborhood.
- **Commute:** driving minutes from each neighborhood centroid to 4 job hubs (Downtown, UTC, Kearny Mesa, Sorrento Valley), computed in a single request to the
  public [OSRM demo server](https://router.project-osrm.org) (OpenStreetMap data) and committed as `data/derived/commute_minutes.csv`.
  Limitations:
  - **Free-flow only.** No traffic, so rush-hour commutes will be longer, especially on I-5, I-805 and SR-163.
  - **Centroid to hub point**, snapped to the nearest road; real trips start and end elsewhere. A hub that sits at a neighborhood's centroid (Downtown to Downtown) shows 0 min.
  - **Driving only.** No transit, bike or parking time.
  - The demo server is a best-effort, rate-limited service with no guarantees. It's used once, offline; the site never calls it.
- **Nice-to-have tags:** hand-curated 0-1 estimates in `data/seed/neighborhoods.csv`, not measured data. Centroids there are also approximate.

## Layout

```
data/seed/       hand-edited neighborhoods and hubs
data/derived/    commute_minutes.csv (committed)
data/raw/        downloaded Zillow CSV (gitignored)
src/neighborhood_fit/  load.py (ZORI -> DuckDB), commute.py, score.py, export.py
site/            static dashboard; score.js mirrors score.py
tests/           pytest + node parity tests
```

## Rebuild

```
python -m pip install -e '.[dev]'
# download Zip_zori_uc_sfrcondomfr_sm_month.csv from Zillow Research into data/raw/
python -m neighborhood_fit.commute      # OSRM by default; --provider ors needs ORS_API_KEY
python -m neighborhood_fit.export       # writes site/data/neighborhoods.json
python -m pytest && node --test tests/
python tests/gen_parity_fixture.py      # after changing scoring in score.py
```

Pushes to `main` that touch `site/` deploy to GitHub Pages via `.github/workflows/pages.yml`.

Rent data: Zillow Research. Routing: OpenStreetMap contributors via OSRM.
