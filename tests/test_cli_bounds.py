"""Exact bounds of the command line: the indent range, error lines, dead and mixed streams."""

from __future__ import annotations

import io
from pathlib import Path

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


class _Narrow(io.TextIOWrapper):
    # A standard error that can only write Latin-1, as a Windows pipe in cp1252 does.
    def __init__(self) -> None:
        super().__init__(io.BytesIO(), encoding="cp1252", errors="backslashreplace")


@pytest.mark.parametrize("char", [chr(0x4E2D), chr(0x1F600)])
@pytest.mark.parametrize("words", [1, 3])
def test_error_lines_are_measured_as_a_narrow_stderr_writes_them(
    char: str, words: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    stream = _Narrow()
    monkeypatch.setattr("sys.stderr", stream)
    report("lvjson: " + " ".join([char * (60 if words == 1 else 39)] * words))
    stream.flush()
    raw = stream.buffer
    assert isinstance(raw, io.BytesIO)
    lines = raw.getvalue().decode("cp1252").splitlines()
    assert len(lines) == 1 and len(lines[0]) <= 200


def test_usage_errors_are_measured_as_a_narrow_stderr_writes_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = _Narrow()
    monkeypatch.setattr("sys.stderr", stream)
    with pytest.raises(SystemExit):
        main(["to-labview", "--infinity", chr(0x4E2D) * 60])
    stream.flush()
    raw = stream.buffer
    assert isinstance(raw, io.BytesIO)
    assert all(len(line) <= 200 for line in raw.getvalue().decode("cp1252").splitlines())


def test_check_names_a_file_whose_name_is_not_utf8(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = tmp_path / ("s" + chr(0xDC80) + ".json")
    try:
        path.write_text("[NaN]", encoding="utf-8")
    except (OSError, UnicodeError):
        pytest.skip("this file system cannot hold such a name")
    assert main(["check", str(path)]) == 0
    out = capsysbinary.readouterr().out
    assert out.endswith(b"s" + bytes([92]) + b"udc80.json: valid, non-finite values: NaN x1\n")


@pytest.mark.parametrize("code", [0x2028, 0x85, 0x0A, 0x1B])
def test_check_writes_a_file_name_on_one_line(
    code: int, tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = tmp_path / ("l" + chr(code) + "s.json")
    try:
        path.write_text("[1]", encoding="utf-8")
    except (OSError, UnicodeError):
        pytest.skip("this file system cannot hold such a name")
    assert main(["check", str(path)]) == 0
    out = capsysbinary.readouterr().out.decode("utf-8")
    assert len(out.splitlines()) == 1 and chr(code) not in out
