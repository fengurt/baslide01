#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "var/migration-file-manifest.json"
    excluded = {".git", "var", "node_modules", "__pycache__"}
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or excluded.intersection(path.relative_to(root).parts):
            continue
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        files.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": h.hexdigest()})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(files)} files -> {output}")


if __name__ == "__main__":
    main()
