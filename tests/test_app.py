import plotly.graph_objects as go
import pandas as pd
import pytest
from sqlalchemy import text

from src import app as app_module
from src import crime_data as cd
import src.queries as q
from src.pages.home import show_map, load_county_geo, county_detail_figures
from src.crime_data import DEFAULT_COUNTY


@pytest.fixture
def clear_cache():
    """Cache fresh data every test (TESTING_REPORT #10) so memoized fetch
    functions never hide the fake engine's results across tests."""
    app_module.cache.clear()
    yield
    app_module.cache.clear()


class FakeConnection:
    """A stand-in for ``engine.connect()`` that never touches Postgres."""

    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True
        return False


class FakeEngine:
    """Injected stand-in for the SQLAlchemy engine (TESTING_REPORT #2).

    ``connect()`` returns a FakeConnection so fetch functions exercise their
    engine-injection code path while (via mocked pandas.read_sql) producing
    canned results — no live Postgres required.
    """

    def __init__(self):
        self.connections = []

    def connect(self):
        conn = FakeConnection()
        self.connections.append(conn)
        return conn


@pytest.fixture
def fake_engine():
    return FakeEngine()


# ---------------------------------------------------------------------------
# Item #2: Abstract / inject the DB engine for mocking
# ---------------------------------------------------------------------------

def test_get_engine_defaults_to_module_engine():
    assert cd.get_engine(None) is cd.engine


def test_get_engine_returns_injected_engine(fake_engine):
    assert cd.get_engine(fake_engine) is fake_engine


def test_fetch_top_offenses_uses_injected_engine(clear_cache, fake_engine, monkeypatch):
    requested = {}
    fake_df = pd.DataFrame([{"category": "Larceny", "incidents": 5}])

    def fake_read_sql(sql, con, params):
        requested["sql_text"] = str(sql).lower()
        requested["con"] = con
        requested["params"] = params
        return fake_df

    monkeypatch.setattr(cd.pd, "read_sql", fake_read_sql)

    result = cd.fetch_top_offenses("York", engine=fake_engine)

    # The injected engine's connection was used (not the live global engine).
    assert isinstance(requested["con"], FakeConnection)
    assert fake_engine.connections, "fetch should have opened a connection on the injected engine"
    # Correct query and parameters went to pandas.read_sql.
    assert "target_data" in requested["sql_text"]
    assert requested["params"]["county"] == "York"
    assert requested["params"]["top"] == 10
    # And the decoupled fetch returns a plain DataFrame.
    assert isinstance(result, pd.DataFrame)


def test_fetch_top_locations_uses_injected_engine(clear_cache, fake_engine, monkeypatch):
    requested = {}
    fake_df = pd.DataFrame([{"category": "Store", "incidents": 9}])

    def fake_read_sql(sql, con, params):
        requested["con"] = con
        requested["params"] = params
        return fake_df

    monkeypatch.setattr(cd.pd, "read_sql", fake_read_sql)

    result = cd.fetch_top_locations("Greenville", engine=fake_engine)

    assert isinstance(requested["con"], FakeConnection)
    assert requested["params"]["county"] == "Greenville"
    assert requested["params"]["top"] == 10
    assert isinstance(result, pd.DataFrame)


def test_fetch_county_geo_uses_injected_engine(clear_cache, fake_engine, monkeypatch):
    fake_gdf = cd.gpd.GeoDataFrame(
        [{"county_name": "York", "geometry": None, "pop": 100}]
    )
    requested = {}

    def fake_read_postgis(sql, con, geom_col):
        requested["con"] = con
        requested["geom_col"] = geom_col
        return fake_gdf

    monkeypatch.setattr(cd.gpd, "read_postgis", fake_read_postgis)

    result = cd.fetch_county_geo(engine=fake_engine)

    assert isinstance(requested["con"], FakeConnection)
    assert requested["geom_col"] == "geometry"
    assert isinstance(result, cd.gpd.GeoDataFrame)


# ---------------------------------------------------------------------------
# Item #1: data access is decoupled from the Dash/Plotly layer
# ---------------------------------------------------------------------------

def test_fetch_top_offenses_is_pure_data_access(clear_cache, fake_engine, monkeypatch):
    # The fetch returns a plain DataFrame; no figure / no server involved.
    fake_df = pd.DataFrame(
        [{"category": "Assault", "incidents": 4}, {"category": "Larceny", "incidents": 7}]
    )
    monkeypatch.setattr(cd.pd, "read_sql", lambda *a, **k: fake_df)

    result = cd.fetch_top_offenses("York", engine=fake_engine)

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["category", "incidents"]


def test_fetch_top_locations_is_pure_data_access(clear_cache, fake_engine, monkeypatch):
    fake_df = pd.DataFrame([{"category": "Store", "incidents": 9}])
    monkeypatch.setattr(cd.pd, "read_sql", lambda *a, **k: fake_df)

    result = cd.fetch_top_locations("York", engine=fake_engine)

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["category", "incidents"]


def test_county_detail_figures_is_testable_without_server(clear_cache, fake_engine, monkeypatch):
    # Pure figure-builder: fed decoupled fetch output, returns Plotly figures.
    offenses = pd.DataFrame(
        [{"category": "Larceny", "incidents": 10}, {"category": "Robbery", "incidents": 3}]
    )
    locations = pd.DataFrame(
        [{"category": "Store", "incidents": 8}, {"category": "Street", "incidents": 2}]
    )

    def fake_read_sql(sql, con, params):
        return offenses if "offense_type" in str(sql) else locations

    monkeypatch.setattr(cd.pd, "read_sql", fake_read_sql)

    types_fig, locations_fig = county_detail_figures("York", engine=fake_engine)

    assert isinstance(types_fig, go.Figure)
    assert isinstance(locations_fig, go.Figure)
    # DataFrame sorted ascending by incidents; horizontal bar keeps that order.
    assert types_fig.data[0].y.tolist() == ["Robbery", "Larceny"]
    assert "Top Crime Types - York" in types_fig.layout.title.text
    assert "Top Locations - York" in locations_fig.layout.title.text


# ---------------------------------------------------------------------------
# Existing lightweight figure/layout/QoL tests (kept from the original suite)
# ---------------------------------------------------------------------------

def test_default_county():
    assert DEFAULT_COUNTY == "York"


def test_show_map():
    # No geo data supplied -> returns a valid (empty) figure rather than crashing.
    output = show_map("")
    assert isinstance(output, go.Figure)


def test_load_county_geo_picks_injected_engine(clear_cache, fake_engine, monkeypatch):
    fake_gdf = cd.gpd.GeoDataFrame(
        [{"county_name": "York", "geometry": None, "pop": 100}]
    )
    monkeypatch.setattr(cd.gpd, "read_postgis", lambda *a, **k: fake_gdf)

    output = load_county_geo(None, engine=fake_engine)

    assert isinstance(output, str)


def test_top_offenses_query():
    sql = text(q.TOP_OFFENSES_SQL).compile()
    assert "county" in q.TOP_OFFENSES_SQL


def test_top_locations_query():
    sql = text(q.TOP_LOCATIONS_SQL).compile()
    assert "county" in q.TOP_LOCATIONS_SQL
