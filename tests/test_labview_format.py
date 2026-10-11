import json
import math

import pytest

from lvjson import LVJSONError, dumps

# Values with no float in them encode identically in both styles, so the hand-written LabVIEW
# encoder can be checked against the standard library's layout.
_NO_FLOATS: list[object] = [
    {},
    [],
    {"a": [], "b": {}},
    {"k": [1, "two", None, True, False, {"x": -7}]},
    ['tab\tquote"back\\slash/é€\U0001f600\x00\x1f\x7f'],
    (1, (2, 3)),
]


@pytest.mark.parametrize("value", _NO_FLOATS)
@pytest.mark.parametrize("indent", [None, 0, 2, 4])
def test_labview_style_matches_json_layout_without_floats(value: object, indent: int) -> None:
    separators = None if indent is not None else (",", ":")
    expected = json.dumps(value, ensure_ascii=False, indent=indent, separators=separators)
    assert dumps(value, number_style="labview", indent=indent) == expected


def test_labview_style_sorts_keys() -> None:
    assert dumps({"b": 1.0, "a": 0.5}, number_style="labview", sort_keys=True) == (
        '{"a":0.5,"b":1}'
    )


def test_labview_style_coerces_keys_like_json() -> None:
    value = {7: "i", True: "t", None: "n", 2.5: "f"}
    assert dumps(value, number_style="labview") == '{"7":"i","true":"t","null":"n","2.5":"f"}'


def test_labview_style_refuses_a_nonfinite_key() -> None:
    with pytest.raises(LVJSONError):
        dumps({math.nan: 1}, number_style="labview")


def test_labview_style_refuses_unsupported_types() -> None:
    with pytest.raises(TypeError):
        dumps({"x": object()}, number_style="labview")
    with pytest.raises(TypeError):
        dumps({(1, 2): 1}, number_style="labview")


def test_labview_style_detects_circular_references() -> None:
    loop: list[object] = []
    loop.append(loop)
    with pytest.raises(LVJSONError):
        dumps(loop, number_style="labview")


def test_labview_style_allows_shared_non_circular_children() -> None:
    shared = [0.5]
    assert dumps([shared, shared], number_style="labview") == "[[0.5],[0.5]]"


def test_labview_style_spells_nonfinite_per_option() -> None:
    value = [math.nan, math.inf, -math.inf]
    assert dumps(value, number_style="labview") == "[NaN,Infinity,-Infinity]"
    assert dumps(value, number_style="labview", infinity="Inf") == "[NaN,Inf,-Inf]"
    assert dumps(value, number_style="labview", nan_inf="null") == "[null,null,null]"


def test_labview_style_formats_large_and_tiny_doubles_like_c_g20() -> None:
    values = [1e16, 1e21, 2.0**-1074, 1e-7, 100.0, -123.456]
    expected = ",".join(f"{value:.20g}" for value in values)
    assert dumps(values, number_style="labview") == f"[{expected}]"
    assert dumps(values, number_style="labview").startswith("[10000000000000000,1e+21,")


def test_labview_style_handles_int_and_float_subclasses() -> None:
    class Code(int):
        def __repr__(self) -> str:
            return "Code()"

    class Gain(float):
        pass

    assert dumps([Code(3), Gain(0.5)], number_style="labview") == "[3,0.5]"
