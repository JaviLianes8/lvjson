"""Errors raised by the caller's own objects while encoding: their type and their bounds."""

from __future__ import annotations

from typing import Any

import pytest

from lvjson import LVJSONError, NumberStyle, dumps

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
