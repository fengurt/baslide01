#!/usr/bin/env bash
# Local entrypoint: free only this project's documented port, then serve the gallery.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
START_PORT="${PORT:-8765}"
PREFERRED_PORTS=(8765 8080 5173)

is_our_listener() {
  local pid="$1"
  local cwd
  cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | awk '/^n/ {print substr($0,2); exit}')"
  [[ "$cwd" == "$ROOT" ]]
}

free_our_port() {
  local port="$1"
  local pids
  pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
  [[ -z "$pids" ]] && return 0
  local pid
  for pid in $pids; do
    if is_our_listener "$pid"; then
      echo "stopping previous baslide01 listener pid=$pid port=$port"
      kill "$pid" 2>/dev/null || true
      sleep 0.3
    else
      echo "port $port is in use by pid=$pid (not this repo); skipping"
    fi
  done
}

find_free_port() {
  local port
  for port in "${PREFERRED_PORTS[@]}"; do
    free_our_port "$port"
    if ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "$port"
      return 0
    fi
  done
  python3 - "$START_PORT" <<'PY'
import socket, sys
start = int(sys.argv[1])
for port in range(start, start + 50):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            print(port)
            raise SystemExit(0)
        except OSError:
            pass
raise SystemExit("no free port")
PY
}

PORT="$(find_free_port)"
cd "$ROOT"
echo "serving $ROOT on http://${HOST}:${PORT}/"
python3 "$ROOT/scripts/serve.py" --host "$HOST" --port "$PORT" --dir "$ROOT" &
SERVER_PID=$!
sleep 0.6
if ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "server failed to bind port $PORT" >&2
  wait "$SERVER_PID" || true
  exit 1
fi

URL="http://${HOST}:${PORT}/"
echo "$URL" > "$ROOT/.dev-url"
if command -v open >/dev/null 2>&1; then
  open "$URL"
fi
echo "gallery     $URL"
echo "sidera      ${URL}demos/sidera/"
echo "zengcheng   ${URL}decks/zengcheng-taizikeng/deck.html"
echo "layouts     ${URL}templates/sidera/layouts.html"
wait "$SERVER_PID"
