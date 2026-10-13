"""Seeded fuzzing: mutated LabVIEW captures and random token soup never crash or hang.

Every reader either returns or raises :class:`LVJSONError`; where the standard library can
parse the text too, the token counts and values agree with it.
"""

from __future__ import annotations

import collections
import contextlib
import json
import math
import random
import struct
from pathlib import Path
from typing import Any

from lvjson import LVJSONError, count_nonfinite, dumps, loads, to_labview, to_portable

_CAPTURES = sorted((Path(__file__).parent / "fixtures" / "labview2026").glob("*.json"))
_SEEDS = [path.read_text(encoding="utf-8") for path in _CAPTURES]
_PIECES = ["NaN", "Inf", "-Inf", "Infinity", "-Infinity", "-0", '"', "\\", ",", "[", "]", "{"]
_PIECES += ["}", ":", "1e400", "0.10000000000000000555", "\\u00e9", "é", " ", "null", "e+", "."]


def _mutate(rng: random.Random, text: str) -> str:
    for _ in range(rng.randrange(1, 6)):
        at = rng.randrange(len(text) + 1)
        action = rng.randrange(3)
        if action == 0:
            text = text[:at] + rng.choice(_PIECES) + text[at:]
        elif action == 1:
            text = text[:at] + text[at + rng.randrange(1, 8) :]
        else:
            text = text[:at] + text[at:][::-1][: rng.randrange(1, 4)] + text[at:]
    return text


def _number(value: Any) -> Any:
    # LabVIEW's form writes whole doubles without ".0", so they read back as int.
    if isinstance(value, float) and value.is_integer():
        return int(value) if math.copysign(1.0, value) > 0 or value else value
    if isinstance(value, dict):
        return {key: _number(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_number(item) for item in value]
    return value


def _same(left: Any, right: Any) -> bool:
    if isinstance(left, float) and isinstance(right, float):
        return (math.isnan(left) and math.isnan(right)) or struct.pack("<d", left) == struct.pack(
            "<d", right
        )
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(map(_same, left, right))
    return bool(type(left) is type(right) and left == right)


def _check(text: str) -> None:
    counts = count_nonfinite(text)
    refused = object()
    try:
        value = loads(text)
    except LVJSONError:
        value = refused
        for convert in (to_portable, to_labview):
            try:
                convert(text)
            except LVJSONError:
                continue
            raise AssertionError("conversion accepted text that loads refused") from None
    else:
        assert _same(loads(dumps(value)), value)
        labview = loads(dumps(value, number_style="labview"))
        assert _same(_number(labview), _number(value))
    constants: list[str] = []

    def constant(token: str) -> float:
        constants.append(token)
        return float(token)

    try:
        reference = json.loads(text, parse_constant=constant)
    except (ValueError, RecursionError):
        return
    assert counts == dict(collections.Counter(constants))
    assert value is not refused, "the json module read text that loads refused"
    if "-0" not in text:
        assert _same(value, reference)


def test_mutated_captures_never_crash() -> None:
    rng = random.Random(1013)
    for _ in range(3000):
        _check(_mutate(rng, rng.choice(_SEEDS)))


def test_random_token_soup_never_crashes() -> None:
    rng = random.Random(2026)
    alphabet = [*_PIECES, "1", "2.5", "true", "false", '"NaN"', '"a\\"Inf"']
    for _ in range(3000):
        _check("".join(rng.choice(alphabet) for _ in range(rng.randrange(1, 40))))


def test_random_bytes_never_crash() -> None:
    rng = random.Random(8259)
    for _ in range(2000):
        data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 64)))
        for reader in (loads, to_portable, count_nonfinite):
            with contextlib.suppress(LVJSONError):
                reader(data)
