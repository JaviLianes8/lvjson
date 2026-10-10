import math

import pytest

from lvjson import LVJSONError, has_nonfinite, loads


def test_loads_reads_plain_json() -> None:
    assert loads('{"a": 1, "b": [true, null]}') == {"a": 1, "b": [True, None]}


def test_loads_accepts_labview_nan_extension() -> None:
    value = loads('{"x": NaN}')
    assert math.isnan(value["x"])


def test_loads_accepts_positive_and_negative_infinity() -> None:
    value = loads("[Infinity, -Infinity]")
    assert value[0] == math.inf
    assert value[1] == -math.inf


def test_loads_rejects_nonfinite_when_policy_is_reject() -> None:
    with pytest.raises(LVJSONError):
        loads('{"x": Infinity}', nan_inf="reject")


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
