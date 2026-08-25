import dash
from dash import html

dash.register_page(__name__, path='/')

def layout(**kwargs):
    return html.Div(
        "The Home Page"
    )
