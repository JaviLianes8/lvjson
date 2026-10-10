import math

import pytest

from lvjson import LVJSONError, dumps, loads, round_trip


def test_dumps_emits_compact_json_by_default() -> None:
    assert dumps({"a": 1, "b": [2, 3]}) == '{"a":1,"b":[2,3]}'


def test_dumps_keeps_full_double_precision() -> None:
    assert dumps(0.1) == "0.1"
    assert dumps(0.1 + 0.2) == "0.30000000000000004"


def test_dumps_extend_emits_labview_tokens() -> None:
    assert dumps([math.nan, math.inf, -math.inf]) == "[NaN,Infinity,-Infinity]"


def test_dumps_null_policy_replaces_nonfinite_with_null() -> None:
    assert dumps({"x": math.nan, "y": math.inf}, nan_inf="null") == '{"x":null,"y":null}'


def test_dumps_reject_policy_raises_on_nonfinite() -> None:
    with pytest.raises(LVJSONError):
        dumps({"x": math.nan}, nan_inf="reject")


def test_dumps_reject_policy_passes_finite_values() -> None:
    assert dumps({"x": 1.5}, nan_inf="reject") == '{"x":1.5}'


def test_dumps_indent_switches_to_readable_separators() -> None:
    assert dumps({"a": 1}, indent=2) == '{\n  "a": 1\n}'


def test_dumps_rejects_unknown_policy() -> None:
    with pytest.raises(ValueError):
        dumps(1, nan_inf="skip")  # type: ignore[arg-type]


def test_round_trip_canonicalises_without_changing_values() -> None:
    # LabVIEW may emit extra trailing digits; the value is preserved, the text canonical.
    text = '{"v": 3.1400000000000001}'
    assert round_trip(text) == '{"v":3.14}'
    assert loads(round_trip(text))["v"] == 3.14


def test_round_trip_preserves_nonfinite_under_extend() -> None:
    out = round_trip('{"x": NaN, "y": Infinity}')
    assert out == '{"x":NaN,"y":Infinity}'


def test_round_trip_drops_nonfinite_under_null_policy() -> None:
    assert round_trip('{"x": -Infinity}', nan_inf="null") == '{"x":null}'


def test_round_trip_preserves_a_hard_double_exactly() -> None:
    text = "[1.7976931348623157e+308, 5e-324]"
    assert loads(round_trip(text)) == [1.7976931348623157e308, 5e-324]
