"""Ground truth: bytes captured from LabVIEW 2026's Flatten To JSON node.

See ``fixtures/labview2026/manifest.json`` for where each file came from and the exact input
that produced it. These tests pin lvjson's claims to what LabVIEW really writes.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import pytest

from lvjson import count_nonfinite, dumps, loads, round_trip, to_labview, to_portable

_DIR = Path(__file__).parent / "fixtures" / "labview2026"
_MANIFEST = json.loads((_DIR / "manifest.json").read_text(encoding="utf-8"))
_FILES = [entry["file"] for entry in _MANIFEST["files"]]
_NONFINITE = [f"flatten_to_json_{case}.json" for case in ("nonfinite", "strings", "escapes")]

# The doubles the capture wrote into Data for the nonfinite, strings and escapes cases.
_DATA = [
    [math.nan, math.inf, -math.inf, 0.0],
    [0.1, 1e300, -2.5e-310, 3.141592653589793],
    [1.7976931348623157e308, 5e-324, 123456789.125, -0.0],
]


def _raw(name: str) -> bytes:
    return (_DIR / name).read_bytes()


def _bits(value: float) -> bytes:
    return struct.pack("<d", float(value))


@pytest.mark.parametrize("name", _FILES)
def test_fixture_bytes_match_the_manifest(name: str) -> None:
    entry = next(item for item in _MANIFEST["files"] if item["file"] == name)
    assert hashlib.sha256(_raw(name)).hexdigest() == entry["sha256"]


@pytest.mark.parametrize("name", _NONFINITE)
def test_labview_writes_nan_infinity_and_minus_infinity(name: str) -> None:
    text = _raw(name).decode("utf-8")
    assert "[NaN,Infinity,-Infinity,0]" in text
    assert count_nonfinite(text) == {"NaN": 1, "Infinity": 1, "-Infinity": 1}
    assert "Inf," not in text and "Inf]" not in text


def test_the_standard_library_already_parses_labview_output() -> None:
    for name in _FILES:
        json.loads(_raw(name))


@pytest.mark.parametrize("name", _NONFINITE)
def test_every_double_decodes_bit_for_bit_to_what_went_in(name: str) -> None:
    data = loads(_raw(name))["Data"]
    assert math.isnan(data[0][0])
    flat_in = [value for row in _DATA for value in row][1:]
    flat_out = [value for row in data for value in row][1:]
    assert [_bits(value) for value in flat_out] == [_bits(value) for value in flat_in]


def test_labview_writes_twenty_significant_digits_and_bare_negative_zero() -> None:
    text = _raw("flatten_to_json_nonfinite.json").decode("utf-8")
    for spelled in ("0.10000000000000000555", "4.9406564584124654418e-324", ",-0]"):
        assert spelled in text
    assert math.copysign(1.0, loads(text)["Data"][2][3]) == -1.0
    assert json.loads(text)["Data"][2][3] == 0 and isinstance(json.loads(text)["Data"][2][3], int)


@pytest.mark.parametrize("name", _FILES)
def test_labview_number_style_reproduces_the_capture_byte_for_byte(name: str) -> None:
    raw = _raw(name)
    assert dumps(loads(raw), number_style="labview").encode("utf-8") == raw
    assert to_labview(raw, number_style="labview").encode("utf-8") == raw


@pytest.mark.parametrize("name", _FILES)
def test_portable_output_is_strict_and_lossless_for_finite_values(name: str) -> None:
    def refuse(token: str) -> Any:
        raise AssertionError(token)

    portable = json.loads(to_portable(_raw(name)), parse_constant=refuse)
    original = loads(_raw(name))
    assert portable["Description"] == original["Description"]
    assert portable["Error"] == original["Error"]
    for row_out, row_in in zip(portable["Data"], original["Data"], strict=True):
        for out, inp in zip(row_out, row_in, strict=True):
            assert out is None if not math.isfinite(inp) else _bits(out) == _bits(inp)


@pytest.mark.parametrize("name", _FILES)
def test_shortest_round_trip_changes_digits_but_never_values(name: str) -> None:
    canonical = round_trip(_raw(name))
    before, after = loads(_raw(name)), loads(canonical)
    assert after["Description"] == before["Description"]
    for row_out, row_in in zip(after["Data"], before["Data"], strict=True):
        for out, inp in zip(row_out, row_in, strict=True):
            assert (math.isnan(out) and math.isnan(inp)) or _bits(out) == _bits(inp)


def test_token_words_inside_labview_strings_survive() -> None:
    raw = _raw("flatten_to_json_strings.json")
    expected = 'Inf -Inf NaN "quoted" back\\slash'
    assert loads(raw)["Description"]["Name"] == expected
    assert loads(to_labview(raw, infinity="Inf"))["Description"]["Name"] == expected
    assert json.loads(to_portable(raw))["Description"]["Name"] == expected


def test_labview_string_escapes_and_utf8_are_read_and_rewritten_exactly() -> None:
    raw = _raw("flatten_to_json_escapes.json")
    assert b"\\t" in raw and b"\\u0001" in raw and b"slash/" in raw and b"\xc3\xa9" in raw
    name = loads(raw)["Description"]["Name"]
    assert name == "tab\tnl\ncr\rctl\x01 slash/ e-acute é Infinity"
    assert dumps(name, number_style="labview").encode("utf-8") in raw


def test_number_form_boundaries_match_c_g20_exactly() -> None:
    raw = _raw("flatten_to_json_formats.json")
    values = [1e-5, 0.0001, 0.00012345, 1e-300, 1e19, 1e20, 1e21, 9007199254740992.0]
    values += [1.2345678901234568e20, 1.5, -1e-10, 65536.0]
    expected = [f"{value:.20g}" for value in values]
    rows = ",".join("[" + ",".join(expected[i : i + 4]) + "]" for i in (0, 4, 8))
    assert f'"Data":[{rows}]'.encode() in raw
    for spelled in (b"1.0000000000000000818e-05", b"10000000000000000000,1e+20,1e+21"):
        assert spelled in raw
    decoded = [value for row in loads(raw)["Data"] for value in row]
    assert [_bits(value) for value in decoded] == [_bits(value) for value in values]
