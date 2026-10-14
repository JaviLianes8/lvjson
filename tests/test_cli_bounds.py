"""Exact bounds of the command line: the indent range, error lines, dead and mixed streams."""

from __future__ import annotations

import io

import pytest

from lvjson._cli import main
from lvjson._cli_io import OutputClosed, emit, report


def test_cli_indent_zero_is_accepted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"[1]"), encoding="utf-8"))
    assert main(["to-portable", "--indent", "0"]) == 0
    assert capsys.readouterr().out == "[\n1\n]\n"


def test_usage_errors_cut_long_words(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["to-portable", "--nan-inf", "Z" * 60])
    err = capsys.readouterr().err
    assert "Z" * 39 + "..." in err and "Z" * 40 not in err


def test_report_lines_are_at_most_200_characters(capsys: pytest.CaptureFixture[str]) -> None:
    report("lvjson: " + "a " * 300)
    line = capsys.readouterr().err.rstrip("\n")
    assert len(line) == 200 and line.endswith("...")


def test_a_closed_stream_without_a_buffer_counts_as_closed_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stream = io.StringIO()
    stream.close()
    monkeypatch.setattr("sys.stdout", stream)
    with pytest.raises(OutputClosed):
        emit("[1]")
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"[1]"), encoding="utf-8"))
    assert main(["to-portable"]) == 1
    assert capsys.readouterr().err == ""


def test_text_written_before_emit_comes_out_first(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="utf-8")
    monkeypatch.setattr("sys.stdout", stream)
    stream.write("before|")
    emit("[1]")
    assert raw.getvalue() == b"before|[1]\n"
