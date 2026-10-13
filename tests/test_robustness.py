"""Hostile, huge and unusual arguments: typed errors, short messages, no crash, no hang."""

from __future__ import annotations

import contextlib
import enum
import math
import sys
import time
from typing import Any

import pytest

from lvjson import (
    LVJSONError,
    NumberStyle,
    count_nonfinite,
    dumps,
    has_nonfinite,
    loads,
    round_trip,
    to_labview,
    to_portable,
)

_READERS = (loads, to_portable, to_labview, round_trip, count_nonfinite)


class _Policy(str, enum.Enum):
    NULL = "null"


class _Lying(str):
    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = str.__hash__


class _Impostor(str):
    # Hashes and compares like "null", whatever its text, to slip through a membership test.
    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return hash("null")


@pytest.mark.parametrize("reader", _READERS)
def test_every_reader_takes_str_bytes_and_bytearray(reader: Any) -> None:
    text = '{"x": [NaN, -Inf, 1.5]}'
    expected = reader(text)
    assert reader(text.encode()) == expected
    assert reader(bytearray(text.encode())) == expected
    assert reader("\ufeff" + text) == expected


@pytest.mark.parametrize("reader", _READERS)
@pytest.mark.parametrize("value", [12, None, memoryview(b"[1]"), ["[1]"]])
def test_every_reader_refuses_non_text_with_type_error(reader: Any, value: object) -> None:
    with pytest.raises(TypeError, match="expected str, bytes or bytearray"):
        reader(value)


@pytest.mark.parametrize("reader", _READERS)
def test_undecodable_bytes_name_the_offset_not_the_content(reader: Any) -> None:
    with pytest.raises(LVJSONError, match=r"not valid UTF-8 \(byte 0xff at offset 8\)$"):
        reader(b'["abc", \xff' + b"x" * 100_000)


def test_numbers_that_overflow_a_double_follow_the_policy() -> None:
    assert loads("[1e400, -1e400]") == [math.inf, -math.inf]
    assert loads("[1e400, 2.5]", nan_inf="null") == [None, 2.5]
    with pytest.raises(LVJSONError, match="overflows a double"):
        loads("[1e400]", nan_inf="reject")
    assert loads("[1e-400, 2.5]", nan_inf="reject") == [0.0, 2.5]
    assert to_portable("[1e400]") == "[null]"


def test_options_are_checked_on_their_exact_text() -> None:
    assert dumps([math.nan], nan_inf=_Policy.NULL) == "[null]"  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nan_inf must be one of"):
        loads("[1]", nan_inf=_Lying("anything"))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="got a value of type int"):
        dumps(1, number_style=3)  # type: ignore[arg-type]


def test_an_option_that_lies_about_equality_is_refused_by_its_text() -> None:
    for call in (
        lambda: loads("[NaN]", nan_inf=_Impostor("nope")),  # type: ignore[arg-type]
        lambda: dumps([1], infinity=_Impostor("x")),  # type: ignore[arg-type]
    ):
        with pytest.raises(ValueError, match="must be one of"):
            call()
    with pytest.raises(LVJSONError):
        loads("[NaN]", nan_inf=_Impostor("reject"))  # type: ignore[arg-type]


def test_tuples_follow_the_policy_like_lists() -> None:
    value = {"t": (math.nan, (math.inf, 1.5))}
    for style in ("shortest", "labview"):
        assert dumps(value, nan_inf="null", number_style=style) == '{"t":[null,[null,1.5]]}'
        with pytest.raises(LVJSONError):
            dumps(value, nan_inf="reject", number_style=style)


def test_option_errors_quote_at_most_forty_characters() -> None:
    with pytest.raises(ValueError) as info:
        dumps(1, infinity="x" * 100_000)  # type: ignore[arg-type]
    assert len(str(info.value)) < 120


def test_indent_must_be_an_int_from_0_to_1024() -> None:
    assert dumps([1], indent=0) == "[\n1\n]"
    assert dumps([1], indent=1024) == "[\n" + " " * 1024 + "1\n]"
    for bad in (-1, -100):
        with pytest.raises(ValueError, match="indent must not be negative"):
            dumps([1], indent=bad)
    styles: tuple[NumberStyle, ...] = ("shortest", "labview")
    for huge in (1025, 10**20):
        for style in styles:
            with pytest.raises(ValueError, match="indent must be at most 1024"):
                dumps([1], indent=huge, number_style=style)
        with pytest.raises(ValueError, match="at most 1024"):
            to_portable("[1]", indent=huge)
    for wrong in ("  ", 1.5, True):
        with pytest.raises(TypeError, match="indent must be None or an int"):
            dumps([1], indent=wrong)  # type: ignore[arg-type]


def test_long_type_names_are_cut_in_messages() -> None:
    odd = type("N" * 10_000, (), {})
    for call in (lambda: loads(odd()), lambda: dumps([odd()], number_style="labview")):
        with pytest.raises(TypeError) as info:
            call()
        assert len(str(info.value)) < 120
    for style in ("shortest", "labview"):
        for value in ([odd()], {odd(): 1}):
            with pytest.raises(TypeError) as info:
                dumps(value, number_style=style)
            message = str(info.value)
            assert len(message) < 120 and "N" * 41 not in message, message


def test_has_nonfinite_survives_circular_and_very_deep_values() -> None:
    loop: list[Any] = [1.0]
    loop.append(loop)
    assert has_nonfinite(loop) is False
    loop.append(math.nan)
    assert has_nonfinite(loop) is True
    deep: list[Any] = [math.inf]
    for _ in range(100_000):
        deep = [deep]
    assert has_nonfinite(deep) is True


def test_deep_nesting_is_an_lvjson_error_never_a_recursion_error() -> None:
    deep: list[Any] = []
    for _ in range(100_000):
        deep = [deep]
    for style in ("shortest", "labview"):
        for policy in ("extend", "null", "reject"):
            with pytest.raises(LVJSONError):
                dumps(deep, number_style=style, nan_inf=policy)
    for reader in (loads, to_portable, to_labview):
        with pytest.raises(LVJSONError):
            reader("[" * 100_000 + "]" * 100_000)


def test_huge_integers_are_refused_cleanly() -> None:
    digits = "9" * (sys.get_int_max_str_digits() + 1)
    with pytest.raises(LVJSONError):
        loads(f"[{digits}]")
    with pytest.raises(LVJSONError):
        loads(f"[-0, {digits}]")
    for style in ("shortest", "labview"):
        with pytest.raises(LVJSONError):
            dumps(10 ** (sys.get_int_max_str_digits() + 1), number_style=style)


def test_malformed_input_messages_stay_short() -> None:
    with pytest.raises(LVJSONError) as info:
        loads("[" + "1," * 500_000 + "x]")
    assert len(str(info.value)) <= 200


def test_subclasses_cannot_change_text_or_numbers() -> None:
    class Text(str):
        def __str__(self) -> str:
            return "[666]"

        def startswith(self, *args: Any) -> bool:
            return True

    class Number(float):
        def __float__(self) -> float:
            return 666.0

        def __format__(self, spec: str) -> str:
            return "666"

    assert loads(Text("[1]")) == [1]
    assert count_nonfinite(Text("[NaN]")) == {"NaN": 1}
    assert dumps([Number(0.1)], number_style="labview") == "[0.10000000000000000555]"
    assert dumps([Number(2.0**-30)], number_style="labview") == "[9.3132257461547851563e-10]"


@pytest.mark.parametrize("size", [20_000, 80_000])
def test_scanning_and_parsing_stay_linear(size: int) -> None:
    shapes = [
        "[" + "NaN," * size + "1]",
        '["' + "Inf " * size + '"]',
        "[" + "-0," * size + "0]",
        '"' + "\\" * (2 * size),
        "[" + "Infinit," * size,
    ]
    start = time.perf_counter()
    for text in shapes:
        count_nonfinite(text)
        with contextlib.suppress(LVJSONError):
            loads(text)
    assert time.perf_counter() - start < 2.0


class _LoudFloat(float):
    def __repr__(self) -> str:
        raise RuntimeError("repr must not be called")


class _SwitchingDict(dict[str, Any]):
    # Shows no value to the policy scan, then a NaN to the encoder.
    def items(self) -> Any:
        return [("x", math.nan)]

    def values(self) -> Any:
        return []


def test_a_nonfinite_key_is_refused_without_calling_its_repr() -> None:
    styles: tuple[NumberStyle, ...] = ("shortest", "labview")
    for style in styles:
        for policy in ("null", "reject"):
            with pytest.raises(LVJSONError, match="only allowed under nan_inf='extend'") as info:
                dumps({_LoudFloat("nan"): 1}, nan_inf=policy, number_style=style)
            assert len(str(info.value)) < 80


def test_reject_holds_even_when_a_container_changes_during_encoding() -> None:
    with pytest.raises(LVJSONError, match="only allowed under nan_inf='extend'"):
        dumps(_SwitchingDict(a=1), nan_inf="reject", number_style="labview")
    with pytest.raises(LVJSONError):
        dumps(_SwitchingDict(a=1), nan_inf="reject")
