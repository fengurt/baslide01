"""Apply the existing gallery navigation to packaged HTML once at build time."""
from pathlib import Path
from serve import CHROME_MARK, CHROME_SNIPPET

root = Path(__file__).resolve().parents[1]
for path in root.rglob("*.html"):
    if "platform_app" in path.parts:
        continue
    data = path.read_bytes()
    if CHROME_MARK in data:
        continue
    index = data.lower().rfind(b"</body>")
    path.write_bytes(data[:index] + CHROME_SNIPPET + data[index:] if index >= 0 else data + CHROME_SNIPPET)
