"""Hostile values on the writing side: keys, changing containers, surrogates, subclasses."""

from __future__ import annotations

import contextlib
import enum
import math
import time
from typing import Any

import pytest

from lvjson import (
    LVJSONError,
    NumberStyle,
    count_nonfinite,
    dumps,
    loads,
    to_labview,
    to_portable,
)


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
    with pytest.raises(LVJSONError):
        dumps(_SwitchingDict(a=1), nan_inf="reject", number_style="labview")
    with pytest.raises(LVJSONError):
        dumps(_SwitchingDict(a=1), nan_inf="reject")


@pytest.mark.parametrize("style", ["shortest", "labview"])
def test_lone_surrogates_are_written_as_escapes_so_output_is_utf8(style: NumberStyle) -> None:
    backslash = chr(92)
    lone = '{"' + backslash + 'ud83d": ["' + backslash + 'udc00x", NaN]}'
    for text in (to_portable(lone), to_labview(lone, number_style=style)):
        text.encode("utf-8")
        assert backslash + "ud83d" in text and backslash + "udc00x" in text
        assert loads(text).keys() == loads(lone).keys()
    assert dumps(chr(0xD800) + "é", number_style=style) == '"' + backslash + 'ud800é"'
    pair = '"' + backslash + "ud83d" + backslash + 'ude00"'
    assert to_portable(pair) == '"' + chr(0x1F600) + '"'


class _Code(enum.IntEnum):
    A = 1


class _FakeInt(int):
    def __repr__(self) -> str:
        return "fake"


@pytest.mark.parametrize("style", ["shortest", "labview"])
def test_int_keys_and_values_are_written_by_their_value(style: NumberStyle) -> None:
    assert dumps({_Code.A: _Code.A, _FakeInt(2): _FakeInt(3)}, number_style=style) == (
        '{"1":1,"2":3}'
    )


def test_only_one_leading_byte_order_mark_is_ignored() -> None:
    bom = chr(0xFEFF)
    assert loads(bom + "[1]") == [1]
    with pytest.raises(LVJSONError):
        loads(bom + bom + "[1]")
    with pytest.raises(LVJSONError):
        loads((bom + bom + "[1]").encode())


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
