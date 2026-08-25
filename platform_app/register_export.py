from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from .store import Store


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: python -m platform_app.register_export PROJECT SCENARIO KIND RELATIVE_PATH")
    project, scenario, kind, relative = sys.argv[1:]
    root = Path(os.environ.get("BASLIDE_ROOT", ".")).resolve()
    path = (root / relative).resolve()
    path.relative_to(root)
    if not path.is_file():
        raise SystemExit(f"missing export: {path}")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    store = Store(os.environ["DATABASE_URL"], root, Path(os.environ.get("ASSET_STORE", root / "var/assets")))
    try:
        print(store.register_export(project, scenario, kind, relative, checksum, path.stat().st_size))
    finally:
        store.close()


if __name__ == "__main__":
    main()
