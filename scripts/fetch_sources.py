"""Fetch the public references the source tests read, and record them in MANIFEST.json.

The copies stay on the maintainer's machine (git ignores them); only the manifest with each
URL, date, size and SHA-256 is tracked. Run from the repository root:

    python scripts/fetch_sources.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import urllib.request
from pathlib import Path

_NI = "https://docs-be.ni.com/api/bundle/labview-api-ref/page/functions/"
SOURCES = {
    "ni-flatten-to-json.json": _NI + "flatten-to-json.html",
    "ni-unflatten-from-json.json": _NI + "unflatten-from-json.html",
    "rfc8259.txt": "https://www.rfc-editor.org/rfc/rfc8259.txt",
}
LICENCES = {
    "ni-flatten-to-json.json": "NI documentation, copyright NI; local copy only",
    "ni-unflatten-from-json.json": "NI documentation, copyright NI; local copy only",
    "rfc8259.txt": "IETF Trust, BCP 78 (Revised BSD for code components); local copy only",
}

FOLDER = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sources"


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    entries = []
    for name, url in SOURCES.items():
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain"}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        (FOLDER / name).write_bytes(body)
        entries.append(
            {
                "file": name,
                "url": url,
                "fetched": today,
                "size": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "licence": LICENCES[name],
            }
        )
    manifest = {"note": "public references fetched for the source tests", "files": entries}
    text = json.dumps(manifest, indent=2) + "\n"
    (FOLDER / "MANIFEST.json").write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
