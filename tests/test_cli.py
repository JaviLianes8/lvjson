import io
from pathlib import Path

import pytest

from lvjson._cli import main


def test_to_portable_reads_stdin_and_defaults_to_null(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO('{"x": Inf, "y": 2}'))
    code = main(["to-portable"])
    assert code == 0
    assert capsys.readouterr().out.strip() == '{"x":null,"y":2}'


def test_to_portable_extend_keeps_the_json_spelling(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("[Inf]"))
    main(["to-portable", "--nan-inf", "extend"])
    assert capsys.readouterr().out.strip() == "[Infinity]"


def test_to_labview_reads_a_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "data.json"
    path.write_text('{"limit": Infinity}', encoding="utf-8")
    code = main(["to-labview", str(path)])
    assert code == 0
    assert capsys.readouterr().out.strip() == '{"limit":Inf}'


def test_indent_and_sort_keys(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO('{"b": 1, "a": 2}'))
    main(["to-portable", "--indent", "2", "--sort-keys"])
    assert capsys.readouterr().out.strip() == '{\n  "a": 2,\n  "b": 1\n}'


def test_reject_mode_returns_error_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("[Inf]"))
    code = main(["to-portable", "--nan-inf", "reject"])
    assert code == 1
    assert "lvjson:" in capsys.readouterr().err


def test_malformed_input_returns_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json}"))
    assert main(["to-portable"]) == 1


def test_missing_file_returns_error_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["to-portable", "does-not-exist.json"]) == 1
    assert "lvjson:" in capsys.readouterr().err


def test_no_command_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code != 0
