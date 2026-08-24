import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

REPO_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(REPO_ROOT / ".env")

# No insecure fallbacks: required settings must come from the environment
# (.env locally, orchestrator secrets in prod). Missing values fail loudly
# at import instead of silently connecting with known-default credentials.
_missing = [name for name in (
    "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME",
) if not os.getenv(name)]
if _missing:
    raise RuntimeError(
        f"Missing required database setting(s): {', '.join(_missing)}. "
        "Set them in a root .env (see .env.example) or via environment variables."
    )

del _missing

DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ["DB_PORT"])
DB_NAME = os.environ["DB_NAME"]

# TLS for the DB connection. Production hosts (e.g. Neon) require SSL;
# local Postgres usually does not. Set DB_SSLMODE=disable in a local .env
# to connect without TLS. See psycopg2 sslmode docs for other values
# (verify-full, prefer, etc.).
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

DB_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={"sslmode": DB_SSLMODE},
)