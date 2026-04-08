FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/backend/ src/backend/
COPY src/frontend/public/data/countries-110m.geojson src/frontend/public/data/countries-110m.geojson

EXPOSE 8001

CMD ["uv", "run", "uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
