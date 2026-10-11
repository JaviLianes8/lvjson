import math

import pytest

from lvjson import LVJSONError, has_nonfinite, loads


def test_loads_reads_plain_json() -> None:
    assert loads('{"a": 1, "b": [true, null]}') == {"a": 1, "b": [True, None]}


def test_loads_accepts_labview_nan_token() -> None:
    value = loads('{"x": NaN}')
    assert math.isnan(value["x"])


def test_loads_accepts_labview_inf_tokens() -> None:
    value = loads("[Inf, -Inf]")
    assert value[0] == math.inf
    assert value[1] == -math.inf


def test_loads_also_accepts_the_json_module_infinity_spelling() -> None:
    value = loads("[Infinity, -Infinity]")
    assert value[0] == math.inf
    assert value[1] == -math.inf


def test_loads_does_not_translate_inf_inside_a_string() -> None:
    assert loads('{"note": "Inf and -Inf"}') == {"note": "Inf and -Inf"}


def test_loads_rejects_nonfinite_when_policy_is_reject() -> None:
    with pytest.raises(LVJSONError):
        loads('{"x": Inf}', nan_inf="reject")


def test_loads_null_policy_decodes_nonfinite_to_none() -> None:
    assert loads('{"x": Inf, "y": NaN, "z": 1.5}', nan_inf="null") == {
        "x": None,
        "y": None,
        "z": 1.5,
    }


def test_loads_with_reject_still_reads_finite_json() -> None:
    assert loads('{"x": 1.5}', nan_inf="reject") == {"x": 1.5}


def test_loads_raises_on_malformed_json() -> None:
    with pytest.raises(LVJSONError):
        loads("{not json}")


def test_loads_rejects_unknown_policy() -> None:
    with pytest.raises(ValueError):
        loads("1", nan_inf="drop")  # type: ignore[arg-type]


def test_has_nonfinite_is_true_for_nested_nan() -> None:
    assert has_nonfinite({"a": [1.0, {"b": math.nan}]}) is True


def test_has_nonfinite_is_false_for_finite_structure() -> None:
    assert has_nonfinite({"a": [1.0, 2, "inf", None, True]}) is False
