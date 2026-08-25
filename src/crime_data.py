"""Shared data-access layer for the SC Crime Dashboard.

Holds the SQLAlchemy engine, the Flask-Caching instance, and the cached
fetch_* helpers used by both ``app.py`` (CSV export routes) and
``pages/home.py`` (map + charts). Kept separate so page modules can import
data helpers without creating a circular import with ``app.py``.
"""
import logging

import geopandas as gpd
import pandas as pd
from flask import Flask
from sqlalchemy import create_engine, text
from flask_caching import Cache

import queries as q
from db_config import DB_URL, DB_HOST, DB_PORT

DEFAULT_COUNTY = "York"

logger = logging.getLogger(__name__)

try:
    engine = create_engine(DB_URL)
except Exception as exc:
    logger.error("Failed to create database engine from DB_URL: %s", exc)
    raise RuntimeError(
        "Could not create the SQLAlchemy engine. Check that .env exists and "
        "DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME are set correctly."
    ) from exc


def get_engine(engine=None):
    """Resolve the DB engine used by a fetch function.

    Allows callers (or tests) to inject a fake/mocked engine instead of always
    hitting the global ``engine`` (TESTING_REPORT #2). Falls back to the
    module-level engine when ``engine`` is None.
    """
    if engine is not None:
        return engine
    return globals()["engine"]


# Created unbound here; app.py calls ``cache.init_app(server)`` once the Dash
# app (and its Flask server) exist.
cache = Cache(config={'CACHE_TYPE': 'flask_caching.backends.SimpleCache'})

# Bind the cache to a minimal throwaway Flask app so memoized fetches work
# even when this module is imported outside of app.py (e.g. by the test
# suite). app.py later calls ``cache.init_app(server)`` to attach it to the
# real Dash/Flask server.
cache.init_app(Flask(__name__))


@cache.memoize(timeout=300)
def fetch_county_geo(engine=None):
    engine = get_engine(engine)
    with engine.connect() as connection:
        return gpd.read_postgis(q.COUNTY_GEO_SQL, con=connection, geom_col="geometry")


@cache.memoize(timeout=300)
def fetch_top_offenses(county, engine=None):
    engine = get_engine(engine)
    with engine.connect() as connection:
        return pd.read_sql(
            text(q.TOP_OFFENSES_SQL),
            con=connection,
            params={"county": county, "top": 10},
        )


@cache.memoize(timeout=300)
def fetch_top_locations(county, engine=None):
    engine = get_engine(engine)
    with engine.connect() as connection:
        return pd.read_sql(
            text(q.TOP_LOCATIONS_SQL),
            con=connection,
            params={"county": county, "top": 10},
        )
