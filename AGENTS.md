# AGENTS.md

## What this is
Data analysis + Dash visualization project exploring 2024 South Carolina crime data (ICPSR/NIBRS), Census ACS DP05 population figures, and TIGER/Line county geography with geopandas. Served as a multi-page Dash app backed by Postgres/PostGIS.

## Layout
- `src/learn_geopandas.ipynb` (38MB, committed) — the real work: loads data, merges it, loads the Postgres DB. It derives the repo root via `Path.cwd().parent`, so **it must run with the notebook's cwd set to `src/`** (else `data/` and `output/` paths break).
- `src/app.py` — Dash app shell: index HTML/styles, header nav (links rendered inline from `dash.page_registry`), the `/export/<county>/<data_type>` CSV routes, and Flask error handlers. Exposes `server = app.server`; run with `gunicorn app:server` from `src/` or `python src/app.py` (dev, :10000).
- `src/pages/` — Dash pages (`use_pages=True`, pages folder = `src/pages`):
  - `home.py` — SC county choropleth; clicking a county renders its top crime types and top locations.
  - `changelog.py` — project changelog page.
  - Blog pages were removed deliberately; don't recreate them.
- `src/crime_data.py` — shared data-access layer: SQLAlchemy engine, Flask-Caching instance (`cache`, initialized on `app.server`), and cached `fetch_county_geo` / `fetch_top_offenses` / `fetch_top_locations`. All fetchers accept an optional `engine=` for test injection. Pages import from here (avoids circular imports with `app.py`).
- `src/queries.py` — raw SQL constants used by `crime_data.py`.
- `src/db_config.py` — single source of DB connection settings; reads required `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME` from a root `.env` (fails loudly if missing) and optional `DB_SSLMODE` (default `require`; set `disable` for local no-TLS Postgres). Builds `DB_URL` via `sqlalchemy.URL.create`. Notebook and app both import `DB_URL` from it.
- `src/main.py` — unrelated personal-finance Monte Carlo demo; saves PNG to `~/Pictures`.
- `src/gunicorn.conf.py` — gunicorn config; its `post_fork` hook warms each worker's Dash resource registry (prevents `/_dash-component-suites` 500s with multiple workers).
- `.venv` — Python 3.14.6; `requirements.txt` is fully pinned.
- `.env` — local DB credentials, gitignored; `.env.example` is the committed template.
- `backups/` — `sc_crimes_seed.dump` (pg_dump of the populated DB) and `10_restore_seed.sh` (used as a docker-entrypoint init script to auto-restore the seed into an empty volume).
- `artifacts/` — planning/design notes (deployment checklist, testing report, etc.); reference material only.
- `tests/` — pytest suite. `conftest.py` at repo root puts `src/` on `sys.path` so tests can `from src.app import ...`; `tests/fake_db.py` provides a fake engine injected via the fetchers' `engine=` parameter. `requirements.txt` pins pytest under a "Dev/test dependencies" section.
- `data/` — raw sources (TIGER county shapefile zip, ACS CSVs, ICPSR NIBRS). `tl_2025_us_county.zip` is untracked (large; don't commit).
- `output/` — generated plots; untracked (deliberately removed from git history once; don't commit).

## Database prerequisite
`src/db_config.py` loads DB settings from a root `.env` (gitignored; commit `.env.example`, don't commit `.env`). Point it at any reachable Postgres+PostGIS (local on 5432, or a managed host such as Neon via `DB_SSLMODE=require`).
- Tables used by the app are created from notebook cells via `to_postgis(..., if_exists='replace')`; re-run those cells to (re)create schema. No migrations/ORM schemas exist. Current tables: `sc_counties` (46 counties, `county_name`+`geometry`+pop), `sc_county_law_info` (county-by-agency fips crosswalk), `target_data` (per-incident `offense_type`/`location`/`fips`). Alternatively restore `backups/sc_crimes_seed.dump`.
- `sc_crimes_by_county` is an aspirational table (notebook cell 43) that does **not** exist yet — don't query it.
- DB settings live only in `src/db_config.py` + `.env`.

## Docker / deployment
- `Dockerfile` targets Render-style platforms: copies only `src/` (via `.dockerignore`, which also excludes `.env`/`.venv`/`data`/`output`), installs pinned deps + gunicorn, sets `WORKDIR /app/src` so `gunicorn app:server` resolves, serves on `$PORT` (default 10000; Render injects it), includes a stdlib-based healthcheck hitting `/`. DB settings are not baked into the image — missing env vars fail at import.
- `docker-compose.yml` is **web-only** (no `db` service anymore): pass `DB_*` vars from `.env`/environment and point `DB_HOST` at your database (local Postgres or managed). `WEB_PORT` overrides the host port (default 10000, matching the container's `$PORT`). Set `DB_SSLMODE=disable` when targeting a local non-TLS Postgres.
- Run: `docker compose up --build` -> http://localhost:10000

## Commands
- Install: `.venv/bin/pip install -r requirements.txt`
- Run notebook: start Jupyter from the repo root, open `src/learn_geopandas.ipynb` (run cells from `src/` cwd).
- Run Dash app: `.venv/bin/python src/app.py`
- Run tests: `.venv/bin/python -m pytest tests/`
- Note: importing `src.app` builds a SQLAlchemy engine from `DB_URL` (needs `.env` present; DB need not be reachable at import).

## Conventions
Scripts are plain top-level modules (no package/`__init__.py`) under `src/`, so imports like `from db_config import DB_URL` or `from crime_data import ...` work because notebooks run with cwd `src/`, `python src/app.py` puts `src/` on `sys.path`, and conftest adds it for tests.
