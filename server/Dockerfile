FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/server

WORKDIR /app

COPY server/pyproject.toml server/uv.lock server/
RUN uv sync --locked --no-dev --extra postgres --no-install-project --project server

COPY server/cedar_press server/cedar_press
COPY data data
COPY public/data/cedar public/data/cedar

RUN useradd --system --uid 10001 --no-create-home press
USER press

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

WORKDIR /app/server
CMD ["uvicorn", "cedar_press.app:app", "--host", "0.0.0.0", "--port", "8000"]
