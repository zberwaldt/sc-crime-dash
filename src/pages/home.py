import logging

import dash
from dash import html, dcc, Input, Output, callback, no_update
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd

from crime_data import (
    DEFAULT_COUNTY,
    DB_HOST,
    DB_PORT,
    fetch_county_geo,
    fetch_top_offenses,
    fetch_top_locations,
)

logger = logging.getLogger(__name__)

dash.register_page(__name__, path='/', name='Home')


def layout(**kwargs):
    return html.Div(
        className="app-shell",
        children=[
            html.Header(
                children=[
                    html.H3(id="selected-county", children=f"Selected county: {DEFAULT_COUNTY}"),
                ]
            ),
            html.Div(
                children=[
                    html.P("Click on a county in the map below to see more information about crime incidents")
                ]
            ),
            html.Div(
                className="grid-row",
                children=[
                    html.Div(
                        className="map-pane",
                        children=[
                            dcc.Loading(
                                id="loading-map",
                                type="default",
                                children=dcc.Graph(id="county-map", style={"height": "700px"}, config={
                                    'scrollZoom': False,
                                    'displayModeBar': False,
                                }),
                            )
                        ],
                    ),
                    html.Div(
                        className="charts-pane",
                        children=[
                            html.Div(
                                className="chart",
                                children=[
                                    dcc.Graph(id="crime-types-fig"),
                                    html.A(
                                        "Export CSV",
                                        id="export-offenses-link",
                                        href="#",
                                        className="button",
                                        style={"display": "block", "margin-top": "10px"},
                                    ),
                                ],
                            ),
                            html.Div(
                                className="chart",
                                children=[
                                    dcc.Graph(id="crime-locations-fig"),
                                    html.A(
                                        "Export CSV",
                                        id="export-locations-link",
                                        href="#",
                                        className="button",
                                        style={"display": "block", "margin-top": "10px"},
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            dcc.Store(id="county-geo"),
        ],
    )


def empty_figure():
    return go.Figure().update_layout(
        height=400,
        margin={"t": 30, "r": 0, "l": 0, "b": 0},
    )


def error_figure(message):
    """A figure that displays an error message instead of data."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font={"size": 16, "color": "#b30000"},
    )
    return fig.update_layout(
        height=400,
        margin={"t": 30, "r": 0, "l": 0, "b": 0},
    )


def describe_exception(exc):
    """Turn common failure modes into short, actionable messages."""
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return f"Cannot reach the Postgres database ({DB_HOST}:{DB_PORT}). Is it running?"
    if isinstance(exc, OSError):
        return f"Database connection failed: {exc}"
    name = type(exc).__name__
    msg = str(exc).strip() or name
    # Keep messages short enough to render in a chart annotation.
    if len(msg) > 200:
        msg = msg[:197] + "..."
    return f"{name}: {msg}"


def county_detail_figures(county, engine=None):
    try:
        offenses = fetch_top_offenses(county, engine=engine).sort_values("incidents")
        locations = fetch_top_locations(county, engine=engine).sort_values("incidents")
    except Exception as exc:
        raise RuntimeError(f"Failed to load crime data for county '{county}': {describe_exception(exc)}") from exc

    for label, df in (("offenses", offenses), ("locations", locations)):
        required = {"category", "incidents"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"Query result for top {label} of '{county}' is missing column(s): "
                f"{', '.join(sorted(missing))}. Check the SQL in queries.py and that "
                "target_data is loaded."
            )

    types_fig = px.bar(
        offenses,
        x="incidents",
        y="category",
        orientation="h",
        title=f"Top Crime Types - {county}",
    )
    types_fig.update_layout(
        height=400,
        margin={"t": 60, "r": 0, "l": 0, "b": 0},
    )

    locations_fig = px.bar(
        locations,
        x="incidents",
        y="category",
        orientation="h",
        title=f"Top Locations - {county}",
    )
    locations_fig.update_layout(
        height=400,
        margin={"t": 60, "r": 0, "l": 0, "b": 0},
    )

    return types_fig, locations_fig


@callback(
    Output('county-geo', 'data'),
    Input('county-geo', 'id')
)
def load_county_geo(_, engine=None):
    return fetch_county_geo(engine=engine).to_json()


@callback(
    Output('county-map', 'figure'),
    Input('county-geo', 'data')
)
def show_map(value):
    if not value:
        return empty_figure()

    try:
        sc = gpd.read_file(value)
    except Exception as exc:
        logger.exception("Failed to parse county geometry payload")
        return error_figure(
            "Could not parse the county GeoJSON returned by the database. "
            f"Details: {describe_exception(exc)}"
        )

    if sc.empty:
        return error_figure(
            "No counties were returned by the database. The sc_counties table may be "
            "empty — run the notebook cells that write it via to_postgis()."
        )

    if "county_name" not in sc.columns:
        return error_figure(
            "sc_counties is missing the 'county_name' column expected by the map."
        )

    minx, miny, maxx, maxy = sc.total_bounds

    center = {"lat": (miny + maxy) / 2, "lon": (minx + maxx) / 2}

    geojson = sc.__geo_interface__

    fig = px.choropleth_map(
        sc,
        geojson=geojson,
        locations="county_name",
        featureidkey="properties.county_name",
        zoom=6.9,
        opacity=0.7,
        center=center,
        map_style="open-street-map",
    )

    fig.update_layout(
        height=700,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        dragmode=False,
        showlegend=False
    )

    return fig


@callback(
    Output('crime-types-fig', 'figure'),
    Output('crime-locations-fig', 'figure'),
    Output('selected-county', 'children'),
    Output('export-offenses-link', 'href'),
    Output('export-locations-link', 'href'),
    Input('county-map', 'clickData')
)
def show_county_details(clickData):
    if clickData and clickData.get("points"):
        county = clickData["points"][0]["location"]
    else:
        county = DEFAULT_COUNTY

    export_offenses = f"/export/{county}/offenses"
    export_locations = f"/export/{county}/locations"

    try:
        types_fig, locations_fig = county_detail_figures(county)
    except Exception as exc:
        logger.exception("Error loading details for county '%s'", county)
        message = describe_exception(exc)
        return (
            error_figure(f"Could not load crime types — {message}"),
            error_figure(f"Could not load crime locations — {message}"),
            f"Selected county: {county} (error loading data)",
            export_offenses,
            export_locations,
        )

    return types_fig, locations_fig, f"Selected county: {county}", export_offenses, export_locations
