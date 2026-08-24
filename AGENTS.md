# AGENTS.md

## What this is
Data analysis + Dash visualization project exploring 2024 South Carolina crime data (ICPSR/NIBRS), Census ACS DP05 population figures, and TIGER/Line county geography with geopandas.

## Layout
- `src/learn_geopandas.ipynb` (38MB, committed) — the real work: loads data, merges it, loads the Postgres DB. It derives the repo root via `Path.cwd().parent`, so **it must run with the notebook's cwd set to `src/`** (else `data/` and `output/` paths break).
- `src/app.py` — Dash choropleth app backed by Postgres. Shows the SC county map on the left; clicking a county renders its top crime types and top locations on the right. Exposes `server = app.server`; run with `gunicorn app:server` from `src/` or `python src/app.py` (dev, :8050). Reads `sc_counties` + `target_data` + `sc_county_law_info` (not `sc_crimes_by_county`).
- `src/db_config.py` — the single source of DB connection settings; reads `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME` from a root `.env` and builds `DB_URL` via `sqlalchemy.URL.create`. Both the notebook and `app.py` import `DB_URL` from it.
- `src/main.py` — unrelated personal-finance Monte Carlo demo; saves PNG to `~/Pictures`.
- `src/dash_*.py`, `src/monte.ipynb`, `src/learn_geopandas.ipynb.invalid` (0-byte dummy) — scratch/learning files, ignore.
- `tests/` — pytest suite. `conftest.py` at repo root puts `src/` on `sys.path` so tests can `from src.app import ...`. `requirements.txt` pins `pytest` under a "Dev/test dependencies" section.
- `data/` — raw sources (TIGER county shapefile zip, ACS CSVs, ICPSR NIBRS). `tl_2025_us_county.zip` is untracked (large; don't commit).
- `output/` — generated plots; untracked (deliberately removed from git history once; don't commit).
- `.venv` — Python 3.14.6; `requirements.txt` is fully pinned.
- `.env` — local DB credentials, gitignored; `.env.example` is the committed template.

## Database prerequisite (external, not in repo)
`src/db_config.py` loads DB settings from a root `.env` (gitignored; commit `.env.example`, don't commit `.env`).
- Postgres must be running externally on port **5433** with database `sc_crimes`. No docker-compose or DB setup exists in the repo.
- Tables used by `app.py` are created from notebook cells via `to_postgis(..., if_exists='replace')`; re-run those cells to (re)create schema. No migrations/ORM schemas exist. Current geography/crime tables: `sc_counties` (46 counties, `county_name`+`geometry`+pop), `sc_county_law_info` (county-by-agency fips crosswalk), `target_data` (per-incident `offense_type`/`location`/`fips`). `sc_crimes_by_county` is an aspirational table (notebook cell 43) that does **not** exist yet — don't query it from `app.py`.
- DB settings live only in `src/db_config.py` + `.env`; the notebook and `app.py` both import `DB_URL` from `db_config`.

## Docker
- `Dockerfile` copies only `src/` (via `.dockerignore`, which also excludes `.env`/`.venv`/`data`/`output`), installs pinned deps + gunicorn, sets `WORKDIR /app/src` so `gunicorn app:server` resolves, and serves on port 8000.
- `docker-compose.yml` runs the web service plus a `postgis/postgis` `db` service (auto-healthcheck) so the stack is self-contained on any provider. `web` gets `DB_HOST=db`, `DB_PORT=5432`; override via env (`DB_USER`, `DB_PASSWORD`, `DB_NAME`, `WEB_PORT`).
- **Data caveat:** the app reads PostGIS tables (`sc_counties`, `sc_county_law_info`, `target_data`) that aren't shipped in the image/repo. A fresh `db` container is empty — load an existing database dump (or run the notebook cells against it) before the map shows data. Drop the `db` service and point `web` at a managed DB if you prefer.
- Build/run: `docker compose up --build` -> http://localhost:8000

## Commands
- Install: `.venv/bin/pip install -r requirements.txt`
- Run notebook: start Jupyter from the repo root, open `src/learn_geopandas.ipynb` (run cells from `src/` cwd).
- Run Dash app: `.venv/bin/python src/app.py`
- Run tests: `.venv/bin/python -m pytest tests/`
- Note: importing `src.app` builds a SQLAlchemy engine from `DB_URL` (needs `.env` present, DB need not be reachable at import).
- No lint/typecheck/formatter config — nothing else to run.

## Conventions
Scripts are plain top-level modules (no package/`__init__.py`), so imports like `from db_config import DB_URL` work because notebooks run with cwd `src/` and `python src/app.py` puts `src/` on `sys.path`.