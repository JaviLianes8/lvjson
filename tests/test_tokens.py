from lvjson._tokens import json_to_labview, labview_to_json


def test_labview_to_json_expands_inf() -> None:
    assert labview_to_json("[Inf, -Inf, NaN]") == "[Infinity, -Infinity, NaN]"


def test_labview_to_json_leaves_existing_infinity_untouched() -> None:
    assert labview_to_json("[Infinity]") == "[Infinity]"


def test_labview_to_json_skips_string_contents() -> None:
    assert labview_to_json('{"k": "Inf -Inf"}') == '{"k": "Inf -Inf"}'


def test_json_to_labview_contracts_infinity() -> None:
    assert json_to_labview("[Infinity, -Infinity, NaN]") == "[Inf, -Inf, NaN]"


def test_json_to_labview_skips_escaped_quote_in_string() -> None:
    assert json_to_labview('{"k": "a\\"Infinity"}') == '{"k": "a\\"Infinity"}'


def test_round_trip_of_the_two_translations_is_stable() -> None:
    text = '{"a":Inf,"b":-Inf,"note":"Inf"}'
    assert json_to_labview(labview_to_json(text)) == text
