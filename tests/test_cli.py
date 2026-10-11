import io
from pathlib import Path

import pytest

from lvjson import __version__
from lvjson._cli import main


def _stdin(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    stream = io.TextIOWrapper(io.BytesIO(data), encoding="latin-1")
    monkeypatch.setattr("sys.stdin", stream)


def test_to_portable_reads_stdin_and_defaults_to_null(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b'{"x": Infinity, "y": 2}')
    assert main(["to-portable"]) == 0
    assert capsys.readouterr().out.strip() == '{"x":null,"y":2}'


def test_stdin_is_decoded_as_utf8_whatever_the_console_encoding(
    monkeypatch: pytest.MonkeyPatch, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    _stdin(monkeypatch, '{"n": "é€"}'.encode())
    assert main(["to-portable"]) == 0
    assert capsysbinary.readouterr().out == '{"n":"é€"}\n'.encode()


def test_plain_text_stdin_without_a_buffer_still_works(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("[Inf]"))
    assert main(["to-portable", "--nan-inf", "extend"]) == 0
    assert capsys.readouterr().out.strip() == "[Infinity]"


def test_to_labview_reads_a_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "data.json"
    path.write_text('{"limit": Inf, "x": 0.1}', encoding="utf-8")
    assert main(["to-labview", str(path)]) == 0
    assert capsys.readouterr().out.strip() == '{"limit":Infinity,"x":0.1}'


def test_to_labview_spelling_and_number_style_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "data.json"
    path.write_text('{"limit": -Infinity, "x": 0.1}', encoding="utf-8")
    args = ["to-labview", str(path), "--infinity", "Inf", "--number-style", "labview"]
    assert main(args) == 0
    assert capsys.readouterr().out.strip() == '{"limit":-Inf,"x":0.10000000000000000555}'


def test_output_file_is_utf8_without_a_trailing_newline(tmp_path: Path) -> None:
    source, target = tmp_path / "in.json", tmp_path / "out.json"
    source.write_bytes('{"n": "é", "v": NaN}'.encode())
    assert main(["to-portable", str(source), "-o", str(target)]) == 0
    assert target.read_bytes() == '{"n":"é","v":null}'.encode()


def test_indent_and_sort_keys(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b'{"b": 1, "a": 2}')
    assert main(["to-portable", "--indent", "2", "--sort-keys"]) == 0
    assert capsys.readouterr().out.strip() == '{\n  "a": 2,\n  "b": 1\n}'


def test_reject_mode_returns_error_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"[Infinity]")
    assert main(["to-portable", "--nan-inf", "reject"]) == 1
    assert "lvjson:" in capsys.readouterr().err


def test_malformed_input_returns_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    _stdin(monkeypatch, b"{not json}")
    assert main(["to-portable"]) == 1


def test_undecodable_input_returns_error_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.json"
    path.write_bytes(b'{"n": "\xff"}')
    assert main(["to-labview", str(path)]) == 1
    assert "UTF-8" in capsys.readouterr().err


def test_missing_file_returns_error_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["to-portable", "does-not-exist.json"]) == 1
    assert "lvjson:" in capsys.readouterr().err


def test_check_lists_tokens_and_strict_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "data.json"
    path.write_text('[NaN, Infinity, -Infinity, "NaN"]', encoding="utf-8")
    assert main(["check", str(path)]) == 0
    out = capsys.readouterr().out
    assert "non-finite values: NaN x1, Infinity x1, -Infinity x1" in out
    assert main(["check", str(path), "--strict"]) == 1


def test_check_flags_numbers_that_overflow_to_infinity(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b"[1e400, NaN, -1e999]")
    assert main(["check", "--strict"]) == 1
    out = capsys.readouterr().out
    assert "NaN x1, numbers that overflow a double x2" in out


def test_unencodable_output_is_a_clean_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b'["\\ud800"]')
    assert main(["to-portable"]) == 1
    assert "lvjson:" in capsys.readouterr().err


def test_check_passes_strict_json_under_strict(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stdin(monkeypatch, b'{"x": 1.5, "note": "Infinity"}')
    assert main(["check", "--strict"]) == 0
    assert "<stdin>: valid, no non-finite tokens" in capsys.readouterr().out


def test_check_reports_malformed_input(monkeypatch: pytest.MonkeyPatch) -> None:
    _stdin(monkeypatch, b"[NaN,")
    assert main(["check"]) == 1


def test_no_command_exits_with_usage_error() -> None:
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert capsys.readouterr().out.strip() == f"lvjson {__version__}"


def test_help_shows_runnable_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for command in ("lvjson to-portable", "lvjson to-labview", "lvjson check"):
        assert command in out
    assert "exit status" in out
