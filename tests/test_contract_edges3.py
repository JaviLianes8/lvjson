"""Edges left after the fourth mutation round: subclass values, BOMs, stderr, descriptions."""

from __future__ import annotations

import io
import time
from typing import Any

import pytest

from lvjson import LVJSONError, NumberStyle, count_nonfinite, dumps, loads
from lvjson._cli import main

_STYLES: tuple[NumberStyle, ...] = ("shortest", "labview")


class _Float(float):
    pass


@pytest.mark.parametrize("style", _STYLES)
def test_float_subclass_nonfinite_values_become_null(style: NumberStyle) -> None:
    value = [_Float("nan"), _Float("inf"), {"k": (_Float("-inf"),)}]
    assert dumps(value, nan_inf="null", number_style=style) == '[null,null,{"k":[null]}]'


def test_a_byte_order_mark_is_dropped_from_bytearray_too() -> None:
    data = bytearray(b"\xef\xbb\xbf[1, NaN]")
    assert loads(data)[0] == 1
    assert count_nonfinite(data) == {"NaN": 1}


def test_a_stderr_without_write_still_gives_exit_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"[1"), encoding="utf-8"))
    monkeypatch.setattr("sys.stderr", object())
    assert main(["to-portable"]) == 1


@pytest.mark.parametrize(
    ("value", "shown"),
    [(None, "got None"), (True, "got True"), ("x" * 38, "got '" + "x" * 38 + "'")],
)
def test_option_values_are_described_exactly_at_the_limit(value: Any, shown: str) -> None:
    with pytest.raises(ValueError) as info:
        dumps([1], nan_inf=value)
    assert str(info.value).endswith(shown)
    with pytest.raises(ValueError) as info:
        dumps([1], nan_inf="x" * 39)  # type: ignore[arg-type]
    assert str(info.value).endswith("got '" + "x" * 39 + "...")


def _raising(error: BaseException) -> Any:
    class Items(dict[str, Any]):
        def items(self) -> Any:
            raise error

    return Items(a=1)


def test_a_message_like_jsons_keeps_its_end_and_its_trailing_text() -> None:
    long = "Object of type " + "A" * 500 + " is not JSON serializable"
    with pytest.raises(TypeError) as info:
        dumps(_raising(TypeError(long)))
    assert str(info.value) == "Object of type " + "A" * 40 + "... is not JSON serializable"
    trailing = "Object of type " + "B" * 50 + " is not JSON serializable, and more"
    with pytest.raises(TypeError) as info:
        dumps(_raising(TypeError(trailing)))
    assert str(info.value).endswith(", and more")


def test_loads_errors_stay_lvjson_errors() -> None:
    with pytest.raises(LVJSONError, match="not allowed under nan_inf='reject'"):
        loads("[NaN]", nan_inf="reject")


def test_labview_style_keeps_pace_with_the_shortest_style_on_deep_indented_values() -> None:
    value: Any = list(range(2000))
    for _ in range(300):
        value = [value]
    timings = []
    for style in _STYLES:
        start = time.perf_counter()
        dumps(value, number_style=style, indent=64)
        timings.append(time.perf_counter() - start)
    shortest, labview = timings
    assert labview < 4 * shortest + 0.5, timings


def test_a_usage_error_stays_on_one_line(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["to-portable", "a", "b" + chr(10) + "c"])
    err = capsys.readouterr().err.splitlines()
    assert err[-1].endswith("unrecognized arguments: b" + chr(92) + "nc")


@pytest.mark.parametrize("code", [0x0A, 0x7F, 0x85, 0x2028, 0x2029])
def test_a_usage_error_escapes_every_character_that_is_not_printable(
    code: int, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(["to-portable", "a", "b" + chr(code) + "c"])
    last = capsys.readouterr().err.splitlines()[-1]
    assert last.endswith("unrecognized arguments: b" + repr(chr(code))[1:-1] + "c")
