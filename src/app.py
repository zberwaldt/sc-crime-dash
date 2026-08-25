import logging
import traceback

from dash import Dash, html, dcc, Input, Output, callback, no_update
from sqlalchemy import create_engine, text
from flask import request as flask_request, Response
from flask_caching import Cache
from werkzeug.exceptions import HTTPException
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
import pandas as pd
import libpysal
from libpysal.weights import Queen
import esda
import queries as q

from db_config import DB_URL, DB_HOST, DB_PORT

DEFAULT_COUNTY = "York"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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

external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css',
    'https://codepen.io/chriddyp/pen/brPBPO.css'
]

app = Dash(name="Monte Carlo", external_stylesheets=external_stylesheets)

app.index_string = """
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .app-shell {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .grid-row {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .map-pane {
            width: 100%;
        }
        .charts-pane {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .charts-pane .chart {
            flex: 1 1 100%;
            min-width: 0;
        }
        @media (min-width: 2000px) {
            .grid-row {
                flex-direction: row;
                align-items: stretch;
            }
            .map-pane {
                flex: 1 1 50%;
                min-width: 50%;
            }
            .charts-pane {
                flex: 1 1 50%;
                min-width: 50%;
                flex-direction: column;
            }
            .charts-pane .chart {
                flex: 1 1 100%;
            }
        }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
"""

cache = Cache(app.server, config={'CACHE_TYPE': 'flask_caching.backends.SimpleCache'})

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

app.layout = html.Div(
    className="app-shell",
    children=[
        html.Header(
            children=[
                html.H2("South Carolina Crime Explorer"),
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
                            children=dcc.Graph(id="county-map", style={"height": "700px"}),
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
        zoom=6,
        opacity=0.7,
        center=center,
        map_style="open-street-map",
    )

    fig.update_layout(
        height=700,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
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

@app.server.route("/export/<county>/<data_type>")
def export_data(county, data_type):
    """CSV export endpoint for a given county's data."""
    try:
        if data_type == "offenses":
            df = fetch_top_offenses(county)
        elif data_type == "locations":
            df = fetch_top_locations(county)
        else:
            return "Invalid data type", 400
        
        csv = df.to_csv(index=False)
        return Response(
            csv,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={county}_{data_type}.csv"}
        )
    except Exception as exc:
        logger.exception("Failed to export data for %s/%s", county, data_type)
        return str(exc), 500


def _is_api_request():
    """Dash's internal endpoints (/_dash-update-component etc.) expect JSON."""
    return flask_request.path.startswith("/_dash") or _wants_json()


def _wants_json():
    return (
        flask_request.accept_mimetypes.best == "application/json"
        or flask_request.args.get("format") == "json"
    )


def _error_payload(code, message, detail=None):
    payload = {"error": message, "status": code}
    if detail:
        payload["detail"] = detail
    return payload


@app.server.errorhandler(HTTPException)
def handle_http_exception(exc):
    """Return meaningful messages for 404/405/etc. instead of bare HTML."""
    if _is_api_request():
        return _error_payload(exc.code, exc.description), exc.code
    return (
        render_error_page(
            code=exc.code,
            title=exc.name,
            message=exc.description,
        ),
        exc.code,
    )


@app.server.errorhandler(Exception)
def handle_unexpected_exception(exc):
    """Log the full traceback and surface a useful message to the client."""
    logger.exception("Unhandled exception while serving %s", flask_request.path)
    tb = traceback.format_exc(limit=5)
    if app.debug:
        detail = f"{type(exc).__name__}: {exc}\n{tb}"
    else:
        detail = None  # don't leak internals in production
    if _is_api_request():
        return _error_payload(500, "Internal server error", detail), 500
    return (
        render_error_page(
            code=500,
            title="Something went wrong",
            message=(
                "An unexpected error occurred. Check the server logs for a full "
                "traceback — common causes are an unreachable Postgres database or "
                "missing tables (sc_counties, target_data, sc_county_law_info)."
            ),
            detail=detail,
        ),
        500,
    )


def render_error_page(code, title, message, detail=None):
    """Minimal standalone error page (independent of Dash layout)."""
    detail_html = f"<pre>{detail}</pre>" if detail else ""
    return f"""<!DOCTYPE html>
<html>
<head><title>{code} - {title}</title></head>
<body style="font-family: sans-serif; max-width: 720px; margin: 3rem auto;">
    <h1>{code} &mdash; {title}</h1>
    <p>{message}</p>
    {detail_html}
    <p><a href="/">Back to the app</a></p>
</body>
</html>"""

if __name__ == "__main__":
    app.run(debug=True)
