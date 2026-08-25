#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ROOT/var/backups"
cd "$ROOT"
docker compose exec -T db pg_dump -U baslide -d baslide --format=custom > "$ROOT/var/backups/baslide-$STAMP.dump"
echo "$ROOT/var/backups/baslide-$STAMP.dump"

