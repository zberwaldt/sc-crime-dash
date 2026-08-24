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

EXPOSE 8000

# No curl/wget in slim; use Python's stdlib to probe the app. Hitting "/"
# also re-warms the Dash resource registry if a worker was recycled.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"]

ENV DB_HOST=db \
    DB_PORT=5432

CMD ["gunicorn", "--config", "gunicorn.conf.py", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "app:server"]