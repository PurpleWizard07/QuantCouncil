#!/bin/sh
# Container entrypoint: run pending Alembic migrations, then start the API.
# Runs on every boot -- Alembic no-ops when the schema is already current, so
# this is safe on repeated deploys/restarts.
#
# Must run from /app (the repo-root equivalent): infra/migrations/env.py
# locates the app package by walking up looking for an apps/api/app
# directory, which only exists at this cwd in the image.
set -e

alembic -c infra/alembic.ini upgrade head
cd apps/api
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
