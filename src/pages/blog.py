import dash
from dash import html

dash.register_page(__name__)

def layout(**kwargs):
    return html.Div(
        "The Blog Index"
    )
