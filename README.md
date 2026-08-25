# SC Crime Data Explorer

An exploratory data analysis + visualization project for 2024 South Carolina crime
data (ICPSR/NIBRS), combined with Census ACS population estimates (DP05) and
TIGER/Line county geography, analyzed with geopandas and served through an
interactive Dash choropleth app backed by PostGIS.

## What it does

- `src/learn_geopandas.ipynb` — the core analysis notebook: loads the raw NIBRS,
  ACS, and TIGER/Line data, merges them per-county, derives crime metrics, and
  loads results into a Postgres/PostGIS database (`sc_counties`,
  `sc_county_law_info`, `target_data`).
- `src/app.py` — a Dash web app showing the South Carolina county choropleth on
  the left; clicking a county renders its top crime types and top incident
  locations on the right. Exposes `server = app.server` for gunicorn.
- `tests/` — pytest suite for the Dash app.

## Layout

```
src/
  learn_geopandas.ipynb   # main analysis notebook (must run with cwd = src/)
  app.py                  # Dash choropleth app
  db_config.py            # DB connection settings (single source of truth)
  main.py                 # unrelated personal-finance Monte Carlo demo
data/                     # raw sources: TIGER shapefile zip, ACS CSVs, NIBRS
output/                   # generated plots (untracked)
tests/                    # pytest suite
.env.example              # template for local DB credentials
```

## Requirements

- Python 3.14 (see `.venv`); all dependencies pinned in `requirements.txt`
- An external Postgres + PostGIS server reachable on port **5432** with database
  `sc_crimes` (not included in the repo)

## Setup

```bash
# create/activate a venv, then:
pip install -r requirements.txt

cp .env.example .env       # then fill in DB_USER / DB_PASSWORD / etc.
```

`src/db_config.py` reads these from the root `.env` and builds `DB_URL`, used by
both the notebook and the app.

### Database tables

No migrations or ORM schemas exist; tables are created from notebook cells via
`to_postgis(..., if_exists='replace')`. Re-run those cells to (re)create schema:

- `sc_counties` — 46 counties (`county_name`, `geometry`, population)
- `sc_county_law_info` — county-by-agency FIPS crosswalk
- `target_data` — per-incident `offense_type` / `location` / `fips`

(`sc_crimes_by_county` is aspirational and does not exist yet.)

## Usage

```bash
# Run the analysis notebook (run cells with cwd set to src/)
jupyter lab src/learn_geopandas.ipynb

# Run the Dash app locally (:8050)
.venv/bin/python src/app.py

# Run tests
.venv/bin/python -m pytest tests/

# Production
gunicorn app:server   # run from src/
```

## Docker

A self-contained stack is provided: `web` serves the app on port **8000**, and a
`postgis/postgis` `db` service supplies the database (with healthcheck).

```bash
docker compose up --build   # -> http://localhost:8000
```

Configuration via env vars: `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST=db`,
`DB_PORT=5432`, `WEB_PORT`.

> **Data caveat:** PostGIS tables are not shipped in the image/repo. A fresh
> `db` container is empty — load an existing database dump or run the relevant
> notebook cells against it before the map shows data.

## Notes

- The notebook resolves repo paths relative to its cwd, so it must be executed
  with the notebook's working directory set to `src/`.
- `.env` is gitignored; commit only `.env.example`.
- `output/` and the large TIGER zip are untracked by design.
