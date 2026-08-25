import dash
from dash import html

dash.register_page(__name__,
                   name="Changelog",
                   title="Changelog")


def layout(**kwargs):
    return html.Div(
        "The Changelog"
    )
