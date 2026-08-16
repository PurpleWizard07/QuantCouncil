# QuantCouncil API image.
# Build context is the REPO ROOT (compose sets context: .. with
# dockerfile: apps/api/Dockerfile), so all COPY paths are repo-root-relative.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

# The API imports these workspace packages at runtime (quant_engine,
# risk_engine, agents, data_connectors -- NOT mcp_server, which nothing
# under apps/api imports). Installed editable (-e), same as
# requirements-dev.txt: data_connectors.universe locates
# data/nifty50_symbols.json by walking up from its OWN module file, so it
# must keep resolving to its repo-relative source path, not a copied
# site-packages location.
COPY packages/quant_engine packages/quant_engine
COPY packages/risk_engine packages/risk_engine
COPY packages/agents packages/agents
COPY packages/data_connectors packages/data_connectors
COPY data/nifty50_symbols.json data/nifty50_symbols.json
RUN pip install --no-cache-dir \
    -e ./packages/quant_engine \
    -e ./packages/risk_engine \
    -e ./packages/agents \
    -e ./packages/data_connectors

COPY apps/api/ apps/api/
COPY infra/alembic.ini infra/alembic.ini
COPY infra/migrations/ infra/migrations/
RUN chmod +x apps/api/start.sh

EXPOSE 8000

CMD ["apps/api/start.sh"]
