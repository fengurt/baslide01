#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${1:-P009}"
SCENARIO="${2:-sales-landing}"
BASE="http://127.0.0.1:8765"
REVISION="$(curl -fsS "$BASE/api/v1/projects/$PROJECT/snapshot?scenario=$SCENARIO&revision=published" | python3 -c 'import json,sys; print(json.load(sys.stdin)["revision"]["code"])')"
REL="export/$PROJECT/$SCENARIO/$REVISION"
node "$ROOT/scripts/project-render.mjs" "$BASE/projects/$PROJECT/$SCENARIO/landing" "$BASE/projects/$PROJECT/$SCENARIO/slides" "$ROOT/$REL/landing.png" "$ROOT/$REL/slides.pdf"
cd "$ROOT"
docker compose run --rm app python -m platform_app.register_export "$PROJECT" "$SCENARIO" png "$REL/landing.png"
docker compose run --rm app python -m platform_app.register_export "$PROJECT" "$SCENARIO" pdf "$REL/slides.pdf"
