"""Tests that run the app's real SQL against the in-memory mock database.

No Postgres/PostGIS server is required — see tests/fake_db.py and the
``mock_db`` fixture in conftest.py.
"""

import pandas as pd
import pytest

from src import app as app_module
from src import crime_data as cd
from src.pages import home


@pytest.fixture
def clear_cache():
    app_module.cache.clear()
    yield
    app_module.cache.clear()


def test_fetch_top_offenses_runs_real_sql(clear_cache, mock_db):
    df = app_module.fetch_top_offenses("York", engine=mock_db)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["county_name", "category", "incidents"]
    # Seed data: Larceny (3) > Simple Assault (2) > Burglary (1)
    assert list(df["category"]) == ["Larceny", "Simple Assault", "Burglary"]
    assert list(df["incidents"]) == [3, 2, 1]
    assert (df["incidents"] <= 10).all()  # LIMIT :top respected


def test_fetch_top_offenses_limit_and_filter(clear_cache, mock_db):
    df = app_module.fetch_top_offenses("Greenville", engine=mock_db)
    # Greenville seed data only; Motor Vehicle Theft leads with 2
    assert set(df["category"]).isdisjoint({"Burglary"})
    assert df.iloc[0]["category"] == "Motor Vehicle Theft"


def test_fetch_top_locations_runs_real_sql(clear_cache, mock_db):
    df = app_module.fetch_top_locations("Charleston", engine=mock_db)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["county_name", "category", "incidents"]
    # Charleston: Street & Convenience Store (1 each), Store (1) -> 3 rows of 1
    assert sorted(df["category"]) == ["Convenience Store", "Store", "Street"]


def test_fetch_county_geo_reads_wkb_geometry(clear_cache, mock_db):
    gdf = cd.fetch_county_geo(engine=mock_db)

    assert len(gdf) == 3
    assert set(gdf["county_name"]) == {"York", "Greenville", "Charleston"}
    # hex WKB was parsed back into shapely polygons
    york = gdf.loc[gdf["county_name"] == "York"].iloc[0]
    assert york.geometry.geom_type == "Polygon"
    assert abs(york.geometry.area - 1.0) < 1e-9


def test_unknown_county_returns_empty(clear_cache, mock_db):
    df = cd.fetch_top_offenses("NotACounty", engine=mock_db)
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_county_detail_figures_with_mock_db(clear_cache, mock_db):
    types_fig, locations_fig = home.county_detail_figures(
        "York", engine=mock_db
    )
    assert "Top Crime Types - York" in types_fig.layout.title.text
    assert types_fig.data[0].y.tolist() == ["Burglary", "Simple Assault", "Larceny"]
