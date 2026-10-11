import math
import struct

import pytest

from lvjson import LVJSONError, dumps, loads, round_trip, to_labview, to_portable


def test_dumps_emits_compact_json_by_default() -> None:
    assert dumps({"a": 1, "b": [2, 3]}) == '{"a":1,"b":[2,3]}'


def test_dumps_keeps_full_double_precision() -> None:
    assert dumps(0.1) == "0.1"
    assert dumps(0.1 + 0.2) == "0.30000000000000004"


def test_dumps_extend_emits_the_labview_2026_spelling() -> None:
    assert dumps([math.nan, math.inf, -math.inf]) == "[NaN,Infinity,-Infinity]"


def test_dumps_infinity_inf_emits_the_short_spelling() -> None:
    assert dumps([math.nan, math.inf, -math.inf], infinity="Inf") == "[NaN,Inf,-Inf]"


def test_dumps_short_spelling_does_not_corrupt_strings() -> None:
    value = {"note": "Infinity ahead", "x": math.inf}
    assert dumps(value, infinity="Inf") == '{"note":"Infinity ahead","x":Inf}'


def test_dumps_null_policy_replaces_nonfinite_with_null() -> None:
    assert dumps({"x": math.nan, "y": math.inf}, nan_inf="null") == '{"x":null,"y":null}'


def test_dumps_reject_policy_raises_on_nonfinite() -> None:
    for style in ("shortest", "labview"):
        with pytest.raises(LVJSONError):
            dumps({"x": [math.nan]}, nan_inf="reject", number_style=style)


def test_dumps_reject_policy_passes_finite_values() -> None:
    assert dumps({"x": 1.5}, nan_inf="reject") == '{"x":1.5}'


def test_dumps_indent_switches_to_readable_separators() -> None:
    assert dumps({"a": 1}, indent=2) == '{\n  "a": 1\n}'


def test_dumps_labview_style_uses_twenty_significant_digits() -> None:
    assert dumps([0.1, 1.0, -0.0, 1e300], number_style="labview") == (
        "[0.10000000000000000555,1,-0,1.0000000000000000525e+300]"
    )


def test_both_number_styles_preserve_every_double() -> None:
    values = [0.1, 1 / 3, 5e-324, -2.5e-310, 1.7976931348623157e308, 123456789.125, -0.0]
    for style in ("shortest", "labview"):
        back = loads(dumps(values, number_style=style))
        assert [struct.pack("<d", v) for v in back] == [struct.pack("<d", v) for v in values]


def test_dumps_rejects_unknown_options() -> None:
    with pytest.raises(ValueError):
        dumps(1, nan_inf="skip")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        dumps(1, infinity="inf")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        dumps(1, number_style="g20")  # type: ignore[arg-type]


def test_round_trip_canonicalises_labview_digits_without_changing_values() -> None:
    text = '{"v": 0.10000000000000000555, "w": 3.141592653589793116}'
    assert round_trip(text) == '{"v":0.1,"w":3.141592653589793}'
    assert loads(round_trip(text)) == loads(text)


def test_round_trip_preserves_nonfinite_under_extend() -> None:
    expected = '{"x":NaN,"y":Infinity,"z":-Infinity}'
    assert round_trip('{"x": NaN, "y": Inf, "z": -Inf}') == expected


def test_round_trip_drops_nonfinite_under_null_policy() -> None:
    assert round_trip('{"x": -Infinity}', nan_inf="null") == '{"x":null}'


def test_round_trip_preserves_a_hard_double_exactly() -> None:
    text = "[1.7976931348623157e+308, 5e-324]"
    assert loads(round_trip(text)) == [1.7976931348623157e308, 5e-324]


def test_to_portable_defaults_to_strict_null() -> None:
    assert to_portable('{"a": Infinity, "b": NaN, "c": 2}') == '{"a":null,"b":null,"c":2}'


def test_to_portable_extend_uses_the_json_module_spelling() -> None:
    assert to_portable("[Inf, -Inf, NaN]", nan_inf="extend") == "[Infinity,-Infinity,NaN]"


def test_to_portable_reject_raises_on_nonfinite() -> None:
    with pytest.raises(LVJSONError):
        to_portable("[Infinity]", nan_inf="reject")


def test_to_portable_validates_its_policy_before_parsing() -> None:
    with pytest.raises(ValueError):
        to_portable("{", nan_inf="nope")  # type: ignore[arg-type]


def test_to_labview_keeps_the_labview_2026_spelling() -> None:
    text = '{"x": Infinity, "y": -Infinity, "z": NaN}'
    assert to_labview(text) == '{"x":Infinity,"y":-Infinity,"z":NaN}'
    assert to_labview(text, infinity="Inf") == '{"x":Inf,"y":-Inf,"z":NaN}'


def test_to_portable_and_to_labview_round_trip() -> None:
    labview = '{"a":Infinity,"b":-Infinity,"c":NaN,"d":1.5}'
    portable = to_portable(labview, nan_inf="extend")
    assert to_labview(portable) == labview


def test_circular_values_raise_lvjson_error_under_every_policy() -> None:
    loop: list[object] = [1.5]
    loop.append(loop)
    table: dict[str, object] = {}
    table["self"] = table
    for value in (loop, table):
        for policy in ("extend", "null", "reject"):
            for style in ("shortest", "labview"):
                with pytest.raises(LVJSONError):
                    dumps(value, nan_inf=policy, number_style=style)
