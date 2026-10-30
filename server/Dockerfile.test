FROM python:3.12-slim-bookworm
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --global --add safe.directory /workspace
COPY server/pyproject.toml /tmp/press/pyproject.toml
COPY server/cedar_press /tmp/press/cedar_press
RUN pip install --no-cache-dir '/tmp/press[dev,postgres]'
