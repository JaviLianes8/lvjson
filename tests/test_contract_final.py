"""Last edges: str subclasses in labview style, the top of the indent range, quoted names."""

from __future__ import annotations

import io

import pytest

from lvjson import NumberStyle, dumps
from lvjson._cli import main
from lvjson._cli_io import report
from lvjson._text import error_text

_STYLES: tuple[NumberStyle, ...] = ("shortest", "labview")


class _Loud(str):
    def __str__(self) -> str:
        return "LIE"

    def __repr__(self) -> str:
        return "LIE"


@pytest.mark.parametrize("style", _STYLES)
def test_both_styles_write_a_str_subclass_by_its_contents(style: NumberStyle) -> None:
    assert dumps([_Loud("ok"), {_Loud("k"): _Loud("v")}], number_style=style) == '["ok",{"k":"v"}]'


def test_the_command_line_accepts_indent_1024(
    monkeypatch: pytest.MonkeyPatch, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"[1]"), encoding="utf-8"))
    assert main(["to-portable", "--indent", "1024"]) == 0
    assert capsysbinary.readouterr().out == b"[\n" + b" " * 1024 + b"1\n]\n"


def test_quoted_names_with_spaces_are_cut_exactly_after_40_characters() -> None:
    forty = "a b " * 9 + "c de"
    assert len(forty) == 40
    assert error_text(TypeError(f"unhashable type: '{forty}'")) == f"unhashable type: '{forty}'"
    cut = error_text(TypeError(f"unhashable type: '{forty}f'"))
    assert cut == f"unhashable type: '{forty}...'"


def test_a_stderr_without_an_encoding_gets_the_text_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = io.StringIO()
    monkeypatch.setattr("sys.stderr", stream)
    report("lvjson: " + chr(0x4E2D))
    assert stream.getvalue() == "lvjson: " + chr(0x4E2D) + "\n"
