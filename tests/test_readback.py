"""Ground truth: what LabVIEW 2026's Unflatten From JSON reads back from Flatten To JSON text.

``fixtures/labview2026/readback_<mode>.json`` is the string Flatten To JSON wrote in one run of
the shipped example, and ``readback_<mode>.values.json`` holds the doubles that went in and the
doubles the example's Unflatten From JSON nodes returned from that same string, as IEEE 754
bit patterns. See ``manifest.json`` (section ``readback``) and
``scripts/capture-labview-readback.ps1``.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import pytest

from lvjson import dumps, loads, to_labview

_DIR = Path(__file__).parent / "fixtures" / "labview2026"
_MANIFEST = json.loads((_DIR / "manifest.json").read_text(encoding="utf-8"))["readback"]
_MODES = ("nonfinite", "formats", "ties")


def _values(mode: str) -> dict[str, Any]:
    record: dict[str, Any] = json.loads(
        (_DIR / f"readback_{mode}.values.json").read_text(encoding="utf-8")
    )
    return record


def _bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def _decoded_bits(mode: str) -> list[str]:
    data = loads((_DIR / f"readback_{mode}.json").read_bytes())["Data"]
    return [_bits(float(value)) for row in data for value in row]


@pytest.mark.parametrize("entry", _MANIFEST["files"], ids=lambda entry: entry["file"])
def test_readback_files_match_the_manifest(entry: dict[str, str]) -> None:
    assert hashlib.sha256((_DIR / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]


@pytest.mark.parametrize("mode", _MODES)
def test_lvjson_decodes_labview_text_to_the_exact_doubles_that_went_in(mode: str) -> None:
    expected = _values(mode)["input_bits"]
    decoded = _decoded_bits(mode)
    # NaN payloads are not part of the promise: any NaN decodes to Python's NaN.
    for got, want in zip(decoded, expected, strict=True):
        if math.isnan(struct.unpack(">d", bytes.fromhex(want))[0]):
            assert math.isnan(struct.unpack(">d", bytes.fromhex(got))[0])
        else:
            assert got == want


@pytest.mark.parametrize("mode", _MODES)
def test_labview_reads_its_own_text_back_bit_for_bit_except_negative_zero(mode: str) -> None:
    record = _values(mode)
    sent = list(record["input_bits"])
    assert record["unflattened_first_data_row"] == sent[0:4]
    assert record["unflattened_cell"] == sent[7]
    returned = list(record["remaining_unflattened_data"])
    signless = ["0000000000000000" if bits == "8000000000000000" else bits for bits in sent[4:]]
    assert returned == signless


def test_negative_zero_is_where_lvjson_and_labview_readers_differ() -> None:
    record = _values("nonfinite")
    raw = (_DIR / "readback_nonfinite.json").read_bytes()
    assert raw.endswith(b',-0]],"Error":{"status":true,"code":1,"source":"Testing"}}')
    assert record["input_bits"][-1] == "8000000000000000"
    assert record["remaining_unflattened_data"][-1] == "0000000000000000"
    assert math.copysign(1.0, loads(raw)["Data"][2][3]) == -1.0


def test_labview_reads_every_nonfinite_token_it_writes() -> None:
    raw = (_DIR / "readback_nonfinite.json").read_bytes()
    assert b"[[NaN,Infinity,-Infinity,0]," in raw
    row = [
        struct.unpack(">d", bytes.fromhex(bits))[0]
        for bits in _values("nonfinite")["unflattened_first_data_row"]
    ]
    assert math.isnan(row[0]) and row[1:3] == [math.inf, -math.inf]


@pytest.mark.parametrize("mode", _MODES)
def test_labview_number_style_reproduces_the_readback_strings(mode: str) -> None:
    raw = (_DIR / f"readback_{mode}.json").read_bytes()
    assert dumps(loads(raw), number_style="labview").encode("utf-8") == raw
    assert to_labview(raw, number_style="labview").encode("utf-8") == raw
