"""Facts the documentation states, re-read from the public sources fetched for this purpose.

The copies live in ``fixtures/sources`` on the maintainer's machine only (``MANIFEST.json`` holds
each URL, date, size and SHA-256); ``python scripts/fetch_sources.py`` re-creates them. Without
them this module is skipped.

- NI, Flatten To JSON: https://docs-be.ni.com/api/bundle/labview-api-ref/page/functions/flatten-to-json.html
- NI, Unflatten From JSON: https://docs-be.ni.com/api/bundle/labview-api-ref/page/functions/unflatten-from-json.html
- RFC 8259: https://www.rfc-editor.org/rfc/rfc8259.txt
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path

import pytest

from lvjson import to_portable

_DIR = Path(__file__).parent / "fixtures" / "sources"
_MANIFEST = json.loads((_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
_PRESENT = all((_DIR / entry["file"]).is_file() for entry in _MANIFEST["files"])
pytestmark = pytest.mark.skipif(
    not _PRESENT, reason="source copies absent; run python scripts/fetch_sources.py"
)


def _ni_text(name: str) -> str:
    page = json.loads((_DIR / name).read_text(encoding="utf-8"))
    text = html.unescape(re.sub(r"<[^>]+>", " ", page["topic_html"]))
    return re.sub(r"\s+", " ", text)


def _rfc() -> str:
    return (_DIR / "rfc8259.txt").read_text(encoding="utf-8")


def test_copies_match_the_manifest() -> None:
    for entry in _MANIFEST["files"]:
        data = (_DIR / entry["file"]).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (entry["size"], entry["sha256"])


def test_flatten_to_json_enables_the_nan_and_inf_extension_by_default() -> None:
    text = _ni_text("ni-flatten-to-json.json")
    assert "enable LabVIEW extensions? (T)" in text
    assert re.search(r"extensions to support NaN and Inf values of floating-point", text)


def test_unflatten_from_json_refuses_null_unless_told_otherwise() -> None:
    text = _ni_text("ni-unflatten-from-json.json")
    assert "default null elements? (F)" in text
    assert "If default null elements is FALSE, LabVIEW returns an error for null values" in text
    assert "enable LabVIEW extensions? (T)" in text


# RFC 8259 section 6, quoted rule by rule; the pattern below is written from these rules.
_RULES = (
    "number = [ minus ] int [ frac ] [ exp ]",
    "exp = e [ minus / plus ] 1*DIGIT",
    "frac = decimal-point 1*DIGIT",
    "int = zero / ( digit1-9 *DIGIT )",
)
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?")


def test_rfc_8259_number_grammar_is_as_quoted() -> None:
    flat = re.sub(r"\s+", " ", _rfc())
    for rule in _RULES:
        assert rule in flat
    assert "(such as Infinity and NaN) are not permitted" in flat


def test_portable_output_follows_the_rfc_number_grammar() -> None:
    labview = (Path(__file__).parent / "fixtures" / "labview2026").glob("*.json")
    seen: list[str] = []

    def keep(token: str) -> float:
        seen.append(token)
        return float(token)

    def refuse(token: str) -> None:
        raise AssertionError(f"{token} is not RFC 8259 JSON")

    extra = "[1e400, -0, 5e-324, 1.7976931348623157081e+308, 0.10000000000000000555, -1e-7]"
    for text in [extra, *(path.read_text(encoding="utf-8") for path in labview)]:
        portable = to_portable(text)
        json.loads(portable, parse_constant=refuse, parse_float=keep, parse_int=keep)
    assert seen and all(_NUMBER.fullmatch(token) for token in seen)
    assert all(math.isfinite(float(token)) for token in seen)
