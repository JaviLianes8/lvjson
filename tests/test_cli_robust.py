"""The command line under dead streams, interrupts, hostile arguments and odd input."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

from lvjson._cli import main


class _DeadBuffer(io.RawIOBase):
    # Fails the first write, as a pipe whose reader went away; later flushes at teardown pass.
    failed = False

    def writable(self) -> bool:
        return True

    def write(self, data: Any) -> int:
        if not self.failed:
            self.failed = True
            raise BrokenPipeError(32, "Broken pipe")
        return len(data)


class _DeadStdout(io.TextIOWrapper):
    def __init__(self) -> None:
        super().__init__(io.BufferedWriter(_DeadBuffer()), encoding="utf-8")

    def fileno(self) -> int:
        raise OSError("no descriptor")


class _Interrupting(io.RawIOBase):
    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Any) -> int:
        raise KeyboardInterrupt


def _stdin(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(data), encoding="latin-1"))


def test_a_reader_that_went_away_gives_exit_1_and_no_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"[NaN]")
    monkeypatch.setattr("sys.stdout", _DeadStdout())
    assert main(["to-portable"]) == 1
    assert capsys.readouterr().err == ""


def test_no_stdout_at_all_gives_exit_1(monkeypatch: pytest.MonkeyPatch) -> None:
    _stdin(monkeypatch, b"[NaN]")
    monkeypatch.setattr("sys.stdout", None)
    assert main(["check"]) == 1


def test_no_stdin_is_bad_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", None)
    assert main(["to-labview"]) == 1
    assert "standard input is not available" in capsys.readouterr().err


def test_an_interrupt_while_reading_exits_130(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = io.TextIOWrapper(io.BufferedReader(_Interrupting()), encoding="utf-8")
    monkeypatch.setattr("sys.stdin", stream)
    assert main(["to-portable"]) == 130


def test_a_closed_stderr_still_gives_exit_1(monkeypatch: pytest.MonkeyPatch) -> None:
    _stdin(monkeypatch, b"{not json")
    monkeypatch.setattr("sys.stderr", None)
    assert main(["to-portable"]) == 1


def test_usage_errors_do_not_echo_huge_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["to-portable", "--nan-inf", "x" * 100_000])
    assert info.value.code == 2
    assert len(capsys.readouterr().err) < 1_000


def test_error_messages_are_cut_short(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / ("m" * 150) / ("n" * 150)
    assert main(["to-portable", str(missing)]) == 1
    message = capsys.readouterr().err.strip()
    assert message.startswith("lvjson: ") and "..." in message
    assert len(message) <= 200


def test_check_reports_deep_nesting_as_bad_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"[" * 100_000 + b"]" * 100_000)
    assert main(["check"]) == 1
    assert "too deep" in capsys.readouterr().err


def test_check_counts_overflows_inside_strings_never(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b'{"1e400": "1e400", "v": [1e400, -1e999, 1e308]}')
    assert main(["check"]) == 0
    assert "numbers that overflow a double x2" in capsys.readouterr().out


@pytest.mark.parametrize("value", ["-2", "1025", "99999999999999999999", "x"])
def test_an_indent_outside_0_to_1024_is_bad_usage(
    value: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as info:
        main(["to-portable", "--indent", value])
    assert info.value.code == 2
    assert "argument --indent" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [
        ["to-portable", "--nan-inf", "z" * 5000],
        ["z" * 5000],
        ["to-portable", "--indent", "y" * 5000],
    ],
)
def test_every_usage_error_line_stays_within_200_characters(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(args)
    line = capsys.readouterr().err.strip().splitlines()[-1]
    assert "error:" in line and len(line) <= 200


def test_an_error_line_about_a_long_path_stays_within_200_characters(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["to-portable", str(tmp_path / ("p" * 500))]) == 1
    line = capsys.readouterr().err.strip()
    assert line.startswith("lvjson: ") and len(line) <= 200


def test_output_to_a_directory_is_bad_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"[1]")
    assert main(["to-labview", "-o", str(tmp_path)]) == 1
    assert capsys.readouterr().err.startswith("lvjson: ")


def test_dash_output_means_standard_output(
    monkeypatch: pytest.MonkeyPatch, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    _stdin(monkeypatch, b"[Inf]")
    assert main(["to-labview", "-o", "-", "--infinity", "Inf"]) == 0
    assert capsysbinary.readouterr().out == b"[Inf]\n"
