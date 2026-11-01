#!/bin/bash
# usage: deploy.sh <ecr-registry> <image-tag> <dev|prod>
set -euo pipefail

REGISTRY=$1
TAG=$2
ENVIRONMENT=$3
REGION=${AWS_REGION:-us-east-1}
PREFIX=/cedar-press/$ENVIRONMENT
IMAGE=$REGISTRY/cedar-press-api:$TAG
DIR=/opt/cedar-press
NAME=cedar-press

install -d -m 0700 "$DIR"
umask 077

aws ssm get-parameters-by-path --region "$REGION" --path "$PREFIX" --with-decryption \
  --query 'Parameters[].[Name,Value]' --output text |
  while IFS=$'\t' read -r name value; do
    # "unset" is the Cedar key's placeholder; leaving it out keeps Cedar off instead of sending a bad key.
    if [ "$value" != "unset" ]; then
      printf '%s=%s\n' "${name##*/}" "$value"
    fi
  done >"$DIR/env.new"
[ -s "$DIR/env.new" ] || { echo "no parameters found under $PREFIX"; exit 1; }
mv "$DIR/env.new" "$DIR/env"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
docker pull -q "$IMAGE" >/dev/null

docker run --rm --env-file "$DIR/env" "$IMAGE" python -m cedar_press.migrate

PREVIOUS=$(docker inspect --format '{{.Config.Image}}' "$NAME" 2>/dev/null || true)

# Optional reviewed release catalog (CEDAR_PRESS_RELEASE_CATALOG=/etc/cedar-press/release/catalog.json).
MOUNTS=()
[ -d "$DIR/release-catalog" ] && MOUNTS+=(-v "$DIR/release-catalog:/etc/cedar-press/release:ro")

# Finished customer spreadsheets, kept across deploys. 10001 is the image's press user.
install -d -m 0700 -o 10001 -g 10001 "$DIR/finished-sheets"
MOUNTS+=(-v "$DIR/finished-sheets:/var/lib/cedar-press/sheets")

start() {
  docker run -d --name "$NAME" --restart unless-stopped --env-file "$DIR/env" -p 8000:8000 \
    "${MOUNTS[@]}" -e CEDAR_PRESS_FINISHED_SHEETS=/var/lib/cedar-press/sheets \
    --memory 1g --pids-limit 256 --log-opt max-size=10m --log-opt max-file=3 "$1" >/dev/null
}

healthy() {
  for _ in $(seq 1 30); do
    if curl -fsS -m 3 http://127.0.0.1:8000/health >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  return 1
}

docker rm -f "$NAME" >/dev/null 2>&1 || true
start "$IMAGE"

if healthy; then
  echo "deployed $IMAGE"
  # In the background, at low priority; its lines appear in docker logs. A request
  # that arrives first builds its own file, as it would with no finished one.
  docker exec -d "$NAME" sh -c 'nice -n 10 python -m cedar_press.finished_sheets >/proc/1/fd/1 2>&1' || true
else
  echo "new container failed its health check; last logs:"
  docker logs --tail 30 "$NAME" 2>&1 || true
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  if [ -n "$PREVIOUS" ]; then
    start "$PREVIOUS"
    echo "rolled back to $PREVIOUS"
  fi
  exit 1
fi

docker image prune -af --filter "until=72h" >/dev/null || true
