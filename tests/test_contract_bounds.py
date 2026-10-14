"""Exact bounds and hidden paths: message limits, key checks, indent subclasses, stream edges."""

from __future__ import annotations

import math
import threading
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from lvjson import LVJSONError, NumberStyle, dumps, has_nonfinite
from lvjson._text import shorten, type_name

_STYLES: tuple[NumberStyle, ...] = ("shortest", "labview")


class _LoudFloat(float):
    def __repr__(self) -> str:
        raise RuntimeError("repr must not be called")


def _finishes(call: Callable[[], object], seconds: float = 5.0) -> object:
    # A hang shows up as a named failure here instead of a stuck suite.
    outcome: list[object] = []

    def run() -> None:
        try:
            outcome.append(call())
        except BaseException as error:  # handed back to the test thread below
            outcome.append(error)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(seconds)
    assert not worker.is_alive(), "the call did not finish"
    if isinstance(outcome[0], BaseException):
        raise outcome[0]
    return outcome[0]


def test_word_and_message_limits_are_exact() -> None:
    assert shorten("A" * 40) == "A" * 40
    assert shorten("A" * 41) == "A" * 40 + "..."
    assert shorten("a " * 99 + "b") == "a " * 99 + "b"  # 199 characters stay
    cut = shorten("a " * 100)  # 200 characters are cut
    assert len(cut) == 199 and cut.endswith("...")
    assert type_name(type("N" * 40, (), {})()) == "N" * 40
    assert type_name(type("N" * 41, (), {})()) == "N" * 40 + "..."


def test_option_values_are_described_exactly() -> None:
    with pytest.raises(ValueError) as info:
        dumps(1, nan_inf="x" * 60)  # type: ignore[arg-type]
    assert str(info.value).endswith("got '" + "x" * 39 + "...")
    with pytest.raises(ValueError) as info:
        dumps(1, nan_inf=True)  # type: ignore[arg-type]
    assert str(info.value).endswith("got True")


@pytest.mark.parametrize("style", _STYLES)
@pytest.mark.parametrize("key", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("policy", ["null", "reject"])
def test_nonfinite_keys_are_found_at_any_depth_without_repr(
    style: NumberStyle, key: float, policy: str
) -> None:
    loud = _LoudFloat(key)
    for value in ({loud: 1}, {"a": {loud: 1}}, [({loud: 1},)], ({"b": [{loud: 2}]},)):
        with pytest.raises(LVJSONError, match="dict key is only allowed under nan_inf='extend'"):
            dumps(value, nan_inf=policy, number_style=style)  # type: ignore[arg-type]


class _HiddenKeys(dict[Any, Any]):
    # Iterating shows a harmless key; items() still yields the real, non-finite one.
    def __iter__(self) -> Iterator[Any]:
        return iter(["k"])


@pytest.mark.parametrize("key", [math.nan, math.inf])
def test_the_labview_encoder_checks_every_key_it_writes(key: float) -> None:
    for policy in ("null", "reject"):
        with pytest.raises(LVJSONError):
            dumps(_HiddenKeys({key: 1}), nan_inf=policy, number_style="labview")


class _Flip(list[Any]):
    # Finite values for the two policy scans, then a non-finite one for the encoder.
    def __init__(self, value: float) -> None:
        super().__init__([1.0])
        self.value = value
        self.passes = 0

    def __iter__(self) -> Iterator[Any]:
        self.passes += 1
        return iter([1.0] if self.passes <= 2 else [self.value])


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_the_labview_encoder_checks_every_value_it_writes(value: float) -> None:
    with pytest.raises(LVJSONError, match="only allowed under nan_inf='extend'"):
        dumps([_Flip(value)], nan_inf="reject", number_style="labview")


class _Wide(int):
    def __mul__(self, other: object) -> Any:
        return "\t"

    __rmul__ = __mul__


@pytest.mark.parametrize("style", _STYLES)
def test_an_int_subclass_indent_cannot_change_the_layout(style: NumberStyle) -> None:
    assert dumps({"a": [1]}, indent=_Wide(2), number_style=style) == '{\n  "a": [\n    1\n  ]\n}'


def test_circular_values_are_named_as_such_in_both_styles() -> None:
    loop: list[Any] = []
    loop.append(loop)
    for style in _STYLES:
        with pytest.raises(LVJSONError, match="ircular"):
            dumps(loop, number_style=style)


def test_cycles_end_quickly_everywhere() -> None:
    loop: list[Any] = [1.0]
    loop.append(loop)
    table: dict[str, Any] = {}
    table["t"] = table
    assert _finishes(lambda: has_nonfinite(loop)) is False
    for value in (loop, table):
        for policy in ("null", "reject"):
            with pytest.raises(LVJSONError):
                _finishes(lambda v=value, p=policy: dumps(v, nan_inf=p))  # type: ignore[misc]


def test_circular_values_give_the_same_message_in_both_styles() -> None:
    loop: list[Any] = []
    loop.append(loop)
    for style in _STYLES:
        with pytest.raises(LVJSONError) as info:
            dumps(loop, number_style=style)
        assert str(info.value) == "Circular reference detected"


class _HiddenByValues(dict[str, Any]):
    def values(self) -> Any:
        return []


@pytest.mark.parametrize("style", _STYLES)
def test_dict_subclasses_cannot_hide_keys_or_values_from_the_policy(style: NumberStyle) -> None:
    with pytest.raises(LVJSONError, match="dict key"):
        dumps(_HiddenKeys({_LoudFloat("nan"): 1}), nan_inf="null", number_style=style)
    with pytest.raises(LVJSONError):
        dumps(_HiddenByValues(a=_LoudFloat("inf")), nan_inf="reject", number_style=style)
    assert has_nonfinite(_HiddenByValues(a=math.nan)) is True


class _FailingList(list[Any]):
    def __iter__(self) -> Iterator[Any]:
        raise RuntimeError("iteration failed")


@pytest.mark.parametrize("style", _STYLES)
@pytest.mark.parametrize("policy", ["extend", "null", "reject"])
def test_an_exception_from_the_value_itself_becomes_a_type_error(
    style: NumberStyle, policy: str
) -> None:
    with pytest.raises(TypeError, match="its own code raised RuntimeError") as info:
        dumps({"a": _FailingList([1])}, nan_inf=policy, number_style=style)  # type: ignore[arg-type]
    assert isinstance(info.value.__cause__, RuntimeError)
