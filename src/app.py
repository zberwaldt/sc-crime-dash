import logging
import traceback

import dash
from dash import Dash, html, dcc
from flask import request as flask_request, Response
from werkzeug.exceptions import HTTPException
from pathlib import Path

from crime_data import cache, fetch_top_offenses, fetch_top_locations

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css',
    'https://codepen.io/chriddyp/pen/brPBPO.css'
]

PAGES_DIR = Path(__file__).parent / "pages"

app = Dash(name="SC Crime Dashboard", external_stylesheets=external_stylesheets, use_pages=True, pages_folder=PAGES_DIR)

app.title = "SC Crime Dashboard"

server = app.server

cache.init_app(server)

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
        .navigation {
            display: flex;
            justify-content: space-around;
            align-items: center;
        }
        .navigation a {
            display: inline-block;
            margin-left: 16px;
            text-decoration: none;
        }
        .app-shell {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        footer {
            text-align: center;
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

app.layout = html.Div(
    style={
        "display": "flex",
        "flexDirection": "column",
        "minHeight": "100vh",
    },
    children=[
        html.Header(
            [
                html.H2("South Carolina Crime Explorer"),
                html.Nav(
                    [
                        html.Div(
                            dcc.Link(f"{page['name']}", href=page['relative_path'])
                        ) for page in dash.page_registry.values()
                    ],
                    className='navigation'
                )
            ],
        ),
        html.Main(
            dash.page_container,
            style={"flex": "1 0 auto"},
        ),
        html.Footer(
            html.Div("South Carolina Crime Explorer \u00a9 2026"),
            style={
                "flexShrink": "0",
                "textAlign": "center",
                "padding": "16px",
                "marginTop": "24px",
            },
        )
    ],
)


@server.route("/export/<county>/<data_type>")
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


@server.errorhandler(HTTPException)
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


@server.errorhandler(Exception)
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
    app.run(debug=True, port=10000)
