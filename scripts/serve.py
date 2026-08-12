#!/usr/bin/env python3
"""No-cache static server for HTML slide decks."""
from __future__ import annotations

import argparse
import os
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def bind_server(host: str, start_port: int) -> ThreadingHTTPServer:
    last_error = None
    for port in range(start_port, start_port + 50):
        try:
            httpd = ThreadingHTTPServer((host, port), NoCacheHandler)
            return httpd
        except OSError as exc:
            last_error = exc
            continue
    raise RuntimeError(f"No free port found between {start_port} and {start_port + 49}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve baslide01 with no-cache headers.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--dir", default=".", help="Directory to serve")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    os.chdir(root)
    httpd = bind_server(args.host, args.port)
    host, port = httpd.server_address[:2]
    print(f"baslide01 http://{host}:{port}/", flush=True)
    print(f"root {root}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
