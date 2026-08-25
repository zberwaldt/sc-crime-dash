import dash
from dash import html

dash.register_page(__name__,
                   name="Changelog",
                   title="Changelog")


# Date of change + description
CHANGELOG = [
    {
        "date": "2026-08-20",
        "description": "Added README file describing the project setup and usage.",
    },
    {
        "date": "2026-08-18",
        "description": "Added CSV export routes and export buttons for charts.",
    },
    {
        "date": "2026-08-15",
        "description": "Fixed container healthcheck and reduced gunicorn workers.",
    },
    {
        "date": "2026-08-12",
        "description": "Fixed Dockerfile build issues and restructured the project.",
    },
]


def layout(**kwargs):
    entries = [
        html.Li([
            html.Strong(entry["date"], style={"marginRight": "10px"}),
            entry["description"],
        ])
        for entry in CHANGELOG
    ]
    return html.Div(
        [
            html.H2("Changelog"),
            html.P("Changes made to this project:"),
            html.Ul(entries),
        ],
        style={
            "maxWidth": "720px",
            "margin": "0 auto",
            "textAlign": "left",
            "paddingLeft": "16px",
            "paddingRight": "16px",
        },
    )
