# 0001: Score in JavaScript on the static site

**Status:** accepted

GitHub Pages cannot run Python, but users adjust budget and max commute interactively. Python builds the data (DuckDB → `site/data/neighborhoods.json`); a small JS scorer ranks in the browser. A shared fixture test keeps Python and JS rankings identical. DuckDB-WASM was rejected as heavy overhead for ~14 rows.

# 0002: Template "why" first, `claude -p` pre-generation later

`claude -p` cannot run live on a static site. v1 builds the one-line why from a template. v2 pre-generates text for preset budget/commute scenarios offline.
