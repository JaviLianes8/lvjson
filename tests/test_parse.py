import math

import pytest

from lvjson import LVJSONError, has_nonfinite, loads


def test_loads_reads_plain_json() -> None:
    assert loads('{"a": 1, "b": [true, null]}') == {"a": 1, "b": [True, None]}


def test_loads_accepts_the_labview_2026_spelling() -> None:
    value = loads("[NaN, Infinity, -Infinity]")
    assert math.isnan(value[0])
    assert value[1:] == [math.inf, -math.inf]


def test_loads_also_accepts_the_short_inf_spelling() -> None:
    assert loads("[Inf, -Inf]") == [math.inf, -math.inf]


def test_loads_does_not_translate_inf_inside_a_string() -> None:
    assert loads('{"note": "Inf and -Inf"}') == {"note": "Inf and -Inf"}


def test_loads_keeps_the_sign_of_negative_zero() -> None:
    value = loads("[-0, 0, -0.0, -0.5]")
    assert math.copysign(1.0, value[0]) == -1.0
    assert isinstance(value[0], float)
    assert value[1] == 0 and isinstance(value[1], int)
    assert math.copysign(1.0, value[2]) == -1.0
    assert value[3] == -0.5


def test_loads_keeps_ordinary_integers_as_int() -> None:
    assert loads("[-10, 7, 3874602249]") == [-10, 7, 3874602249]
    assert all(isinstance(item, int) for item in loads("[-10, 7, -0.25, 3]")[:2])


def test_loads_accepts_utf8_bytes_and_a_byte_order_mark() -> None:
    assert loads('{"n": "é"}'.encode()) == {"n": "é"}
    assert loads(b'\xef\xbb\xbf{"x": NaN}')["x"] != 0


def test_loads_rejects_bytes_that_are_not_utf8() -> None:
    with pytest.raises(LVJSONError, match="UTF-8"):
        loads(b'{"n": "\xe9"}')


def test_loads_rejects_a_non_text_argument() -> None:
    with pytest.raises(TypeError):
        loads(12)  # type: ignore[arg-type]


def test_loads_rejects_nonfinite_when_policy_is_reject() -> None:
    for text in ('{"x": Inf}', '{"x": Infinity}', '{"x": NaN}', "[-Infinity]"):
        with pytest.raises(LVJSONError):
            loads(text, nan_inf="reject")


def test_loads_null_policy_decodes_nonfinite_to_none() -> None:
    assert loads('{"x": Inf, "y": NaN, "w": -Infinity, "z": 1.5}', nan_inf="null") == {
        "x": None,
        "y": None,
        "w": None,
        "z": 1.5,
    }


def test_loads_with_reject_still_reads_finite_json() -> None:
    assert loads('{"x": 1.5}', nan_inf="reject") == {"x": 1.5}


def test_loads_raises_on_malformed_json() -> None:
    for text in ("{not json}", "", "[1,]", "[NaN", "-NaN", "[Infinityx]"):
        with pytest.raises(LVJSONError):
            loads(text)


def test_loads_reports_excessive_nesting_as_lvjson_error() -> None:
    with pytest.raises(LVJSONError):
        loads("[" * 200_000 + "]" * 200_000)


def test_loads_rejects_unknown_policy() -> None:
    with pytest.raises(ValueError):
        loads("1", nan_inf="drop")  # type: ignore[arg-type]


def test_lvjson_error_is_a_value_error() -> None:
    with pytest.raises(ValueError):
        loads("{")


def test_has_nonfinite_is_true_for_nested_nan() -> None:
    assert has_nonfinite({"a": [1.0, {"b": math.nan}]}) is True


def test_has_nonfinite_is_false_for_finite_structure() -> None:
    assert has_nonfinite({"a": [1.0, 2, "inf", None, True]}) is False


def test_loads_tolerates_a_byte_order_mark_in_str_input() -> None:
    assert loads("﻿[1, Inf]") == [1, math.inf]
