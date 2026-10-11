"""Contract over the complete promise: every token, both directions, every mode, string safety.

The corpus is generated from a fixed seed, so each run checks the same few hundred documents.
"""

from __future__ import annotations

import json
import math
import random
import struct
from typing import Any

import pytest

from lvjson import LVJSONError, count_nonfinite, dumps, loads, round_trip, to_labview, to_portable

_SPELLINGS = {
    "NaN": math.nan,
    "Infinity": math.inf,
    "-Infinity": -math.inf,
    "Inf": math.inf,
    "-Inf": -math.inf,
}
# Strings that look like tokens, plus the escapes that could derail a naive scanner.
_TRAPS = ["NaN", "Inf", "-Inf", "Infinity", 'a"Inf', "back\\", '\\"NaN\\"', "é -Infinity", ""]
_STYLES: tuple[Any, ...] = ("shortest", "labview")
_INFINITIES = ("Infinity", "Inf")


def _strict(text: str) -> Any:
    def refuse(token: str) -> None:
        raise ValueError(f"strict JSON must not contain {token}")

    return json.loads(text, parse_constant=refuse)


def _bits(value: Any) -> Any:
    # Numbers compare as IEEE 754 bit patterns: the labview style writes 123.0 as 123, which
    # reads back as int, so the promise is the exact double, not the Python type.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "nan" if math.isnan(value) else struct.pack("<d", value)
    if isinstance(value, dict):
        return {key: _bits(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_bits(item) for item in value]
    return value


def _document(rng: random.Random) -> tuple[str, Any, dict[str, int]]:
    """Return LabVIEW-style text, the value it must decode to, and its token counts."""
    counts: dict[str, int] = {}

    def node(depth: int) -> tuple[str, Any]:
        pick = rng.randrange(6 if depth < 3 else 4)
        if pick == 0:
            token = rng.choice(list(_SPELLINGS))
            counts[token] = counts.get(token, 0) + 1
            return token, _SPELLINGS[token]
        if pick == 1:
            value = rng.choice([0.1, -2.5e-310, 1e300, 123.0, 5e-324, -0.5])
            return repr(value), value
        if pick == 2:
            text = rng.choice(_TRAPS)
            return json.dumps(text), text
        if pick == 3:
            return rng.choice([("true", True), ("null", None), ("7", 7), ("-12", -12)])
        children = [node(depth + 1) for _ in range(rng.randrange(4))]
        if pick == 4:
            return "[" + " , ".join(t for t, _ in children) + "]", [v for _, v in children]
        keys = [rng.choice(_TRAPS) + str(i) for i in range(len(children))]
        body = ", ".join(json.dumps(k) + ": " + t for k, (t, _) in zip(keys, children, strict=True))
        return "{" + body + "}", {k: v for k, (_, v) in zip(keys, children, strict=True)}

    text, value = node(0)
    return text, value, counts


_CORPUS = [_document(random.Random(seed)) for seed in range(300)]


def _nulled(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _nulled(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_nulled(item) for item in value]
    return value


@pytest.mark.parametrize(("text", "value", "counts"), _CORPUS)
def test_reading_accepts_every_spelling_in_every_mode(
    text: str, value: Any, counts: dict[str, int]
) -> None:
    assert _bits(loads(text)) == _bits(value)
    assert _bits(loads(text, nan_inf="null")) == _bits(_nulled(value))
    if counts:
        with pytest.raises(LVJSONError):
            loads(text, nan_inf="reject")
    else:
        assert _bits(loads(text, nan_inf="reject")) == _bits(value)
    assert count_nonfinite(text) == {k: counts[k] for k in _SPELLINGS if k in counts}


@pytest.mark.parametrize(("text", "value", "counts"), _CORPUS)
def test_portable_output_is_strict_json_and_keeps_every_finite_value(
    text: str, value: Any, counts: dict[str, int]
) -> None:
    portable = to_portable(text)
    assert _bits(_strict(portable)) == _bits(_nulled(value))
    assert count_nonfinite(portable) == {}
    extended = to_portable(text, nan_inf="extend")
    assert set(count_nonfinite(extended)) <= {"NaN", "Infinity", "-Infinity"}
    assert _bits(json.loads(extended)) == _bits(value)


@pytest.mark.parametrize(("text", "value", "counts"), _CORPUS)
@pytest.mark.parametrize("style", _STYLES)
@pytest.mark.parametrize("infinity", _INFINITIES)
def test_writing_round_trips_bit_for_bit_with_the_chosen_spelling(
    text: str, value: Any, counts: dict[str, int], style: Any, infinity: Any
) -> None:
    written = dumps(value, number_style=style, infinity=infinity)
    assert _bits(loads(written)) == _bits(value)
    assert to_labview(text, number_style=style, infinity=infinity) == written
    assert round_trip(text, number_style=style, infinity=infinity) == written
    found = set(count_nonfinite(written))
    allowed = {"NaN", "Infinity", "-Infinity"} if infinity == "Infinity" else {"NaN", "Inf", "-Inf"}
    assert found <= allowed
    strict = _strict(dumps(value, number_style=style, nan_inf="null"))
    assert _bits(strict) == _bits(_nulled(value))
    if counts:
        with pytest.raises(LVJSONError):
            dumps(value, number_style=style, nan_inf="reject")


@pytest.mark.parametrize("trap", _TRAPS)
@pytest.mark.parametrize("infinity", _INFINITIES)
def test_strings_never_change_in_any_direction(trap: str, infinity: Any) -> None:
    value = {trap: [trap, math.inf, trap]}
    modes: tuple[Any, ...] = ("extend", "null")
    for style in _STYLES:
        for mode in modes:
            back = loads(dumps(value, number_style=style, infinity=infinity, nan_inf=mode))
            assert list(back) == [trap]
            assert back[trap][0] == trap and back[trap][2] == trap
    assert loads(to_portable(json.dumps(value)))[trap][::2] == [trap, trap]
