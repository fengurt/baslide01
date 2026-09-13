#!/usr/bin/env bash
# Run as root on the existing CVM from an exact-SHA release archive.
set -euo pipefail
RELEASE_SHA="${1:?40-character main SHA required}"
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]]
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ "$ROOT" == "/opt/tiansight-baslide/releases/$RELEASE_SHA" ]]
[[ "$(cat "$ROOT/REVISION")" == "$RELEASE_SHA" ]]
exec 9>/var/lock/tiansight-baslide.deploy.lock
flock -n 9
cd "$ROOT"
export RELEASE_SHA
PREVIOUS="$(readlink -f /opt/tiansight-baslide/current)"
OLD_IMAGE="$(docker inspect tiansight-baslide-app-1 --format '{{.Image}}')"
printf 'services:\n  app:\n    image: %s\n' "$OLD_IMAGE" > rollback.yaml
printf '%s\n' "$PREVIOUS" > PREVIOUS
printf 'phase=build sha=%s time=%s\n' "$RELEASE_SHA" "$(date -Is)"
docker compose -f compose.prod.yaml build app
NEW_IMAGE="$(docker image inspect tiansight-baslide-app --format '{{.Id}}')"
[[ "$(docker image inspect "$NEW_IMAGE" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')" == "$RELEASE_SHA" ]]
rollback() {
  echo 'phase=rollback'
  docker compose -p tiansight-baslide -f "$PREVIOUS/compose.prod.yaml" -f "$ROOT/rollback.yaml" up -d --no-build app
  ln -sfn "$PREVIOUS" /opt/tiansight-baslide/current
}
trap rollback ERR
printf 'phase=cutover time=%s\n' "$(date -Is)"
docker compose -f compose.prod.yaml up -d --no-build app
for attempt in $(seq 1 45); do
  if curl -fsS http://127.0.0.1:8765/healthz > health.json && python3 -c 'import json,sys; assert json.load(open("health.json"))["release"]==sys.argv[1]' "$RELEASE_SHA"; then break; fi
  [[ "$attempt" -lt 45 ]]
  sleep 2
done
python3 scripts/project-http-check.py http://127.0.0.1:8765
python3 scripts/check-pages.py http://127.0.0.1:8765 > smoke.log
docker compose -f compose.prod.yaml exec -T app python scripts/project-check.py
ln -sfn "$ROOT" /opt/tiansight-baslide/current
printf '%s\n' "$NEW_IMAGE" > IMAGE_DIGEST
trap - ERR
printf 'phase=verified sha=%s image=%s time=%s\n' "$RELEASE_SHA" "$NEW_IMAGE" "$(date -Is)"
