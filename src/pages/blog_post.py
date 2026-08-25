import dash
from dash import html

def title(post_id=None):
    return f"Blog: {post_id}"


def description(post_id=None):
    return f"Blog: {post_id}"

dash.register_page(__name__,
                   path_template="/blog/<post_id>",
                   title=title,
                   description=description
                   )

def layout(post_id=None, **kwargs):
    return html.Div(
        f"The Blog post: {post_id}"
    )
