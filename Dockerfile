FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System libraries the geo / spatial dependencies link against at install time.
# libgdal headers let pyogrio/geopandas build if a prebuilt wheel is unavailable
# for the base image's arch; removed after install to keep the image lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgdal-dev \
        gdal-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first so the layer is cached across rebuilds.
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential libgdal-dev \
    && rm -rf /root/.cache/pip

# Ship only the web app. Notebooks / data / outputs stay out of the image.
COPY src ./src

# app.py imports `db_config` as a sibling module, so the serving cwd is src/.
WORKDIR /app/src

# Render routes traffic to $PORT (default 10000); compose falls back to 8000.
ENV PORT=8000

EXPOSE 8000

# No curl/wget in slim; use Python's stdlib to probe the app. Hitting "/"
# also re-warms the Dash resource registry if a worker was recycled.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/', timeout=4)"

# Shell form so ${PORT} expands at runtime (Render injects it; DB_* come
# from the Render environment, e.g. a Neon pooler host). DB settings are not
# baked into the image — missing vars fail loudly at import in db_config.py.
CMD ["sh", "-c", "gunicorn --config gunicorn.conf.py --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120 --access-logfile - app:server"]