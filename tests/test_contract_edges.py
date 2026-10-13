"""Edge contracts that pin defaults, pass-through options and boundaries one by one."""

from __future__ import annotations

import inspect
import io
import json
from typing import Any

import pytest

import lvjson
from lvjson import LVJSONError, count_nonfinite, dumps, loads, round_trip, to_labview, to_portable
from lvjson._cli import main
from lvjson._cli_io import emit

_DEFAULTS = {
    "loads": {"nan_inf": "extend"},
    "dumps": {
        "nan_inf": "extend",
        "indent": None,
        "sort_keys": False,
        "infinity": "Infinity",
        "number_style": "shortest",
    },
    "to_portable": {"nan_inf": "null", "indent": None, "sort_keys": False},
    "to_labview": {
        "nan_inf": "extend",
        "indent": None,
        "sort_keys": False,
        "infinity": "Infinity",
        "number_style": "shortest",
    },
}
_DEFAULTS["round_trip"] = _DEFAULTS["to_labview"]


@pytest.mark.parametrize("name", sorted(_DEFAULTS))
def test_documented_defaults_are_the_signature_defaults(name: str) -> None:
    parameters = inspect.signature(getattr(lvjson, name)).parameters
    found = {
        key: value.default for key, value in parameters.items() if value.kind.name == "KEYWORD_ONLY"
    }
    assert found == _DEFAULTS[name]


def test_defaults_act_as_documented_without_passing_them() -> None:
    text = '{"b": 0.10000000000000000555, "a": Inf}'
    for convert in (to_labview, round_trip):
        assert convert(text) == '{"b":0.1,"a":Infinity}'
    assert to_portable(text) == '{"b":0.1,"a":null}'
    assert dumps(loads(text)) == '{"b":0.1,"a":Infinity}'


@pytest.mark.parametrize("convert", [to_labview, round_trip])
def test_every_keyword_is_passed_through(convert: Any) -> None:
    text = '{"b": [0.1, -Infinity, NaN], "a": 1}'
    assert convert(text, sort_keys=True).startswith('{"a":1,')
    assert convert(text, indent=1).startswith('{\n "b": [')
    assert '"b":[0.10000000000000000555,' in convert(text, number_style="labview")
    assert "-Inf," in convert(text, infinity="Inf")
    assert convert(text, nan_inf="null") == '{"b":[0.1,null,null],"a":1}'
    with pytest.raises(LVJSONError):
        convert(text, nan_inf="reject")
    assert to_portable(text, sort_keys=True, indent=1).startswith('{\n "a": 1,')


def test_bytearray_input_is_utf8_and_refuses_invalid_bytes() -> None:
    data = bytearray('{"é": [NaN, "ü"]}'.encode())
    assert loads(data)["é"][1] == "ü"
    assert count_nonfinite(data) == {"NaN": 1}
    with pytest.raises(LVJSONError, match="not valid UTF-8"):
        loads(bytearray(b'["\xe9"]'))


def test_non_ascii_keys_are_written_as_text_in_both_styles() -> None:
    for style in ("shortest", "labview"):
        assert dumps({"é": "ü"}, number_style=style) == '{"é":"ü"}'


def test_a_token_touching_a_dot_is_not_counted() -> None:
    for text in ("[.NaN]", "[NaN.5]", "[1.Inf]", "[Infinity.]"):
        assert count_nonfinite(text) == {}, text


def test_option_errors_list_the_choices_in_a_fixed_order() -> None:
    with pytest.raises(ValueError) as info:
        loads("[1]", nan_inf="x")  # type: ignore[arg-type]
    assert str(info.value) == "nan_inf must be one of 'extend', 'null', 'reject', got 'x'"
    with pytest.raises(ValueError) as info:
        dumps(1, number_style="x")  # type: ignore[arg-type]
    assert str(info.value) == "number_style must be one of 'labview', 'shortest', got 'x'"


def test_user_errors_raised_while_encoding_are_cut_short() -> None:
    class Key(str):
        def __lt__(self, other: object) -> bool:
            raise ValueError("x" * 5000)

    with pytest.raises(LVJSONError) as info:
        dumps({Key("a"): 1, Key("b"): 2}, sort_keys=True)
    assert len(str(info.value)) < 200


@pytest.mark.parametrize("command", [["check", "-"], ["to-portable", "-"]])
def test_a_dash_reads_standard_input(
    command: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"[NaN]"), encoding="utf-8"))
    main(command)
    out = capsys.readouterr().out
    assert "<stdin>: valid, non-finite values: NaN x1" in out or json.loads(out) == [None]


def test_emit_writes_and_flushes_a_stream_without_a_buffer(monkeypatch: pytest.MonkeyPatch) -> None:
    class Stream(io.StringIO):
        flushes = 0

        def flush(self) -> None:
            self.flushes += 1
            super().flush()

    stream = Stream()
    monkeypatch.setattr("sys.stdout", stream)
    emit("[1]")
    assert stream.getvalue() == "[1]\n" and stream.flushes >= 1
