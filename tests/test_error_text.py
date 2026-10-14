"""Errors raised by the caller's own objects while encoding: their type and their bounds."""

from __future__ import annotations

import time
from typing import Any

import pytest

from lvjson import LVJSONError, NumberStyle, dumps, has_nonfinite

_STYLES: tuple[NumberStyle, ...] = ("shortest", "labview")


class _Boom(Exception):
    pass


class _BadValueError(ValueError):
    def __str__(self) -> str:
        raise _Boom("str")


class _BadTypeError(TypeError):
    def __str__(self) -> str:
        raise _Boom("str")


def _raising(error: BaseException) -> Any:
    class Items(dict[str, Any]):
        def items(self) -> Any:
            raise error

    return Items(a=1)


@pytest.mark.parametrize("style", _STYLES)
def test_an_exception_whose_str_fails_is_reported_by_its_arguments(style: NumberStyle) -> None:
    # The overridden __str__ is never called: the message comes from the arguments.
    with pytest.raises(LVJSONError, match=r"^x$"):
        dumps(_raising(_BadValueError("x")), number_style=style)
    with pytest.raises(TypeError, match=r"^x$"):
        dumps(_raising(_BadTypeError("x")), number_style=style)


@pytest.mark.parametrize("style", _STYLES)
def test_errors_raised_by_the_value_keep_the_message_bounds(style: NumberStyle) -> None:
    for error in (LVJSONError("y" * 5000), ValueError("z" * 5000)):
        with pytest.raises(LVJSONError) as info:
            dumps(_raising(error), number_style=style)
        assert len(str(info.value)) < 50 and str(info.value).endswith("...")


@pytest.mark.parametrize("style", _STYLES)
def test_type_names_with_spaces_are_cut_like_one_word(style: NumberStyle) -> None:
    spaced: Any = type("ab " * 60, (), {})
    values: list[tuple[Any, bool]] = [
        ([spaced()], False),
        ({spaced(): 1}, False),
        ({"a": 1, spaced(): 2}, True),
    ]
    for value, sort_keys in values:
        with pytest.raises(TypeError) as info:
            dumps(value, sort_keys=sort_keys, number_style=style)
        assert "ab " * 15 not in str(info.value) and len(str(info.value)) < 120


def test_a_hostile_comparison_message_is_handled_in_linear_time() -> None:
    message = "'<' not supported between instances of '" + "' and '" * 80_000 + "x"
    start = time.perf_counter()
    with pytest.raises(TypeError) as info:
        dumps(_raising(TypeError(message)))
    assert time.perf_counter() - start < 1.0
    assert len(str(info.value)) < 200


def test_has_nonfinite_passes_the_values_own_errors_through() -> None:
    error = RuntimeError("from items")
    with pytest.raises(RuntimeError, match="from items"):
        has_nonfinite(_raising(error))


def test_type_names_are_cut_exactly_at_40_characters() -> None:
    for length, cut in ((40, False), (41, True)):
        name = "Q" * length
        with pytest.raises(TypeError) as info:
            dumps([type(name, (), {})()])
        shown = "Q" * 40 + ("..." if cut else " ")
        assert shown in str(info.value)


def test_both_names_of_a_comparison_message_are_cut() -> None:
    spaced: Any = type("ab " * 60, (), {})
    with pytest.raises(TypeError) as info:
        dumps({"a": 1, spaced(): 2}, sort_keys=True)
    message = str(info.value)
    assert "ab " * 14 not in message and message.count("...") >= 1
    with pytest.raises(TypeError) as info:
        dumps({spaced(): 1, "a": 2}, sort_keys=True)
    assert "ab " * 14 not in str(info.value)


class _Unprintable:
    def __str__(self) -> str:
        raise RuntimeError("no text")


def test_an_error_whose_arguments_cannot_be_printed_is_named_by_its_type() -> None:
    with pytest.raises(LVJSONError, match=r"^ValueError$"):
        dumps(_raising(ValueError(_Unprintable())))
