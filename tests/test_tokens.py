import time

from lvjson import count_nonfinite
from lvjson._tokens import expand_inf, shorten_infinity


def test_expand_inf_rewrites_the_short_spelling() -> None:
    assert expand_inf("[Inf, -Inf, NaN]") == "[Infinity, -Infinity, NaN]"


def test_expand_inf_leaves_labview_2026_output_untouched() -> None:
    text = '{"a":[NaN,Infinity,-Infinity,0]}'
    assert expand_inf(text) == text


def test_expand_inf_skips_string_contents() -> None:
    assert expand_inf('{"k": "Inf -Inf"}') == '{"k": "Inf -Inf"}'


def test_expand_inf_ignores_words_that_only_start_with_inf() -> None:
    assert expand_inf("[Info, xInf, Inf_1]") == "[Info, xInf, Inf_1]"


def test_shorten_infinity_contracts_the_long_spelling() -> None:
    assert shorten_infinity("[Infinity, -Infinity, NaN]") == "[Inf, -Inf, NaN]"


def test_shorten_infinity_skips_escaped_quote_in_string() -> None:
    assert shorten_infinity('{"k": "a\\"Infinity"}') == '{"k": "a\\"Infinity"}'


def test_shorten_infinity_skips_a_string_ending_in_an_escaped_backslash() -> None:
    text = '["a\\\\", Infinity, "Infinity"]'
    assert shorten_infinity(text) == '["a\\\\", Inf, "Infinity"]'


def test_round_trip_of_the_two_respellings_is_stable() -> None:
    text = '{"a":Inf,"b":-Inf,"note":"Inf"}'
    assert shorten_infinity(expand_inf(text)) == text


def test_count_nonfinite_reports_each_spelling_in_a_fixed_order() -> None:
    text = "[-Inf, Inf, NaN, -Infinity, Infinity, NaN]"
    assert count_nonfinite(text) == {
        "NaN": 2,
        "Infinity": 1,
        "-Infinity": 1,
        "Inf": 1,
        "-Inf": 1,
    }
    assert list(count_nonfinite(text)) == ["NaN", "Infinity", "-Infinity", "Inf", "-Inf"]


def test_count_nonfinite_is_empty_for_strict_json() -> None:
    assert count_nonfinite('{"note": "NaN Infinity -Inf", "x": 1.5}') == {}


def test_count_nonfinite_works_on_malformed_text() -> None:
    assert count_nonfinite("[NaN,") == {"NaN": 1}


def test_an_unclosed_string_is_skipped_to_the_end() -> None:
    assert expand_inf('[Inf, "abc Inf') == '[Infinity, "abc Inf'
    assert count_nonfinite('["NaN') == {}


def test_scanning_truncated_input_stays_linear() -> None:
    hostile = ('"' + "\\") * 100_000  # 200 KB of quote/backslash pairs, never closed
    start = time.perf_counter()
    count_nonfinite(hostile)
    expand_inf('{"Name":"' + '\\"' * 100_000)
    assert time.perf_counter() - start < 1.0
