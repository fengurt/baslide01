#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DUMP="${1:-}"
if [[ -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "usage: RESTORE=1 $0 /absolute/path/to/baslide.dump" >&2
  exit 2
fi
if [[ "${RESTORE:-}" != "1" ]]; then
  echo "restore replaces the local baslide database; rerun with RESTORE=1" >&2
  exit 2
fi
cd "$ROOT"
docker compose exec -T db dropdb -U baslide --if-exists baslide
docker compose exec -T db createdb -U baslide baslide
docker compose exec -T db pg_restore -U baslide -d baslide --clean --if-exists < "$DUMP"

