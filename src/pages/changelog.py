import dash
from dash import html

dash.register_page(__name__,
                   name="Changelog",
                   title="Changelog")


# Date of change + description
CHANGELOG = [
    {
        "date": "2026-08-25 2:15pm",
        "description": "Switch to multi-page app, add changelog, favicon, and page title"
    },
    {
        "date": "2026-08-25 11:00am",
        "description": "Update favicon and html title"
    },
    {
        "date": "2026-08-25 8:30am",
        "description": "Add export data buttons to charts on home page"
    },
    {
        "date": "2026-08-24 3:00pm",
        "description": "Launch South Carolina Crime Explorer"
    }
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
