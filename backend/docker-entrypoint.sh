#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must be set}"

echo "Waiting for Postgres to accept connections..."
python - <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

database_url = os.environ["DATABASE_URL"]
deadline = time.time() + 60
last_error = None

while time.time() < deadline:
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Postgres connection ready.", flush=True)
        break
    except Exception as exc:  # pragma: no cover - runtime container startup guard
        last_error = exc
        print(f"Database not ready yet: {exc}", flush=True)
        time.sleep(2)
else:
    print("Postgres did not become ready in time.", file=sys.stderr, flush=True)
    if last_error is not None:
        print(str(last_error), file=sys.stderr, flush=True)
    raise SystemExit(1)
PY

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting backend server..."
exec "$@"
