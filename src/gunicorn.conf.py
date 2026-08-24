"""Gunicorn config for the SC Crime Explorer Dash app.

Dash (v3+) registers its component-suite JS files lazily, the first time a
worker renders the index page. With multiple workers, a worker that never
served "/" has an empty ``registered_paths`` table and returns 500
(DependencyException) for any ``/_dash-component-suites/...`` request it
receives — the browser then fails with "DashRenderer is not defined".

The post_fork hook below renders the index once in every worker right after
it boots, warming that per-process state.
"""


def post_fork(server, worker):
    try:
        from app import app as dash_app

        client = dash_app.server.test_client()
        response = client.get("/")
        server.log.info(
            "Warmed Dash resource registry in worker %s (index -> %s)",
            worker.pid,
            response.status_code,
        )
    except Exception:  # pragma: no cover - never block worker boot
        server.log.exception("Failed to warm Dash resource registry")
