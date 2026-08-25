# SC Crime Data Explorer

An exploratory data analysis + visualization project for 2024 South Carolina crime
data (ICPSR/NIBRS), combined with Census ACS population estimates (DP05) and
TIGER/Line county geography, analyzed with geopandas and served through an
interactive multi-page Dash app backed by PostGIS.

## What it does

- `src/learn_geopandas.ipynb` — the core analysis notebook: loads the raw NIBRS,
  ACS, and TIGER/Line data, merges them per-county, derives crime metrics, and
  loads results into a Postgres/PostGIS database (`sc_counties`,
  `sc_county_law_info`, `target_data`).
- `src/app.py` + `src/pages/` — a multi-page Dash web app:
  - **Home** — the South Carolina county choropleth; clicking a county renders
    its top crime types and top incident locations.
  - **Changelog** — project changelog.
  - CSV export routes (`/export/<county>/<data_type>`) for offenses/locations.
  - Exposes `server = app.server` for gunicorn, with friendly HTML/JSON error pages.
- `src/crime_data.py` / `src/queries.py` — shared, cached data-access layer
  (SQLAlchemy engine + Flask-Caching) used by both the app and its pages.
- `tests/` — pytest suite for the Dash app (uses an injectable fake DB engine).

## Layout

```
src/
  learn_geopandas.ipynb   # main analysis notebook (must run with cwd = src/)
  app.py                  # Dash app shell: layout, export routes, error handlers
  pages/                  # Dash pages (home, changelog)
  crime_data.py           # engine + cache + cached fetch_* helpers
  queries.py              # SQL constants
  db_config.py            # DB connection settings (single source of truth)
  gunicorn.conf.py        # gunicorn config (per-worker resource warmup)
  main.py                 # unrelated personal-finance Monte Carlo demo
backups/                  # sc_crimes_seed.dump + auto-restore init script
artifacts/                # planning/design notes
data/                     # raw sources: TIGER shapefile zip, ACS CSVs, NIBRS
output/                   # generated plots (untracked)
tests/                    # pytest suite (+ fake_db.py)
.env.example              # template for local DB credentials
```

## Requirements

- Python 3.14 (see `.venv`); all dependencies pinned in `requirements.txt`
- A reachable Postgres + PostGIS database — local on port **5432**, or a managed
  host such as Neon (TLS via `sslmode=require` is the default)

## Setup

```bash
# create/activate a venv, then:
pip install -r requirements.txt

cp .env.example .env       # then fill in DB_USER / DB_PASSWORD / etc.
```

`src/db_config.py` reads these from the root `.env` and builds `DB_URL`, used by
both the notebook and the app. Required vars: `DB_USER`, `DB_PASSWORD`,
`DB_HOST`, `DB_PORT`, `DB_NAME`. Optional: `DB_SSLMODE` (default `require`;
set `disable` for a local non-TLS Postgres).

### Database tables

No migrations or ORM schemas exist; tables are created from notebook cells via
`to_postgis(..., if_exists='replace')`. Re-run those cells to (re)create schema:

- `sc_counties` — 46 counties (`county_name`, `geometry`, population)
- `sc_county_law_info` — county-by-agency FIPS crosswalk
- `target_data` — per-incident `offense_type` / `location` / `fips`

Shortcut: restore `backups/sc_crimes_seed.dump` into your database instead of
running the notebook.

(`sc_crimes_by_county` is aspirational and does not exist yet.)

## Usage

```bash
# Run the analysis notebook (run cells with cwd set to src/)
jupyter lab src/learn_geopandas.ipynb

# Run the Dash app locally (:10000)
.venv/bin/python src/app.py

# Run tests
.venv/bin/python -m pytest tests/

# Production
gunicorn --config gunicorn.conf.py app:server   # run from src/
```

## Docker / deployment

The image targets Render-style platforms: it serves with gunicorn on `$PORT`
(default 10000, injected by the platform), includes a stdlib healthcheck, and
takes all `DB_*` settings from the environment at runtime.

```bash
docker compose up --build   # -> http://localhost:${WEB_PORT:-10000}
```

`docker-compose.yml` is web-only — point `DB_HOST` at your own Postgres (local
or managed) and pass `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT`
(from `.env` or environment). Set `DB_SSLMODE=disable` for local non-TLS
Postgres; `WEB_PORT` overrides the host port (default 10000).

> **Data caveat:** PostGIS tables are not shipped in the image/repo. Load the
> seed dump (`backups/sc_crimes_seed.dump`) or run the relevant notebook cells
> against your database before the map shows data.

## Notes

- The notebook resolves repo paths relative to its cwd, so it must be executed
  with the notebook's working directory set to `src/`.
- `.env` is gitignored; commit only `.env.example`.
- `output/` and the large TIGER zip are untracked by design.
