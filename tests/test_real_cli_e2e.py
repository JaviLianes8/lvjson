"""Real end-to-end: install the package editable and drive the genuine ``lvjson`` script.

No imports of the package's CLI, no mocks: every test shells out to the console script that
pip generated, feeding it the bytes captured from LabVIEW 2026. Inside a virtual environment
the project is installed into it; otherwise a throwaway virtual environment is created.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import sysconfig
import venv
from pathlib import Path

import pytest

import lvjson

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = _ROOT / "tests" / "fixtures" / "labview2026"
_NONFINITE = _FIXTURES / "flatten_to_json_nonfinite.json"
_ESCAPES = _FIXTURES / "flatten_to_json_escapes.json"


def _scripts_dir(env_dir: Path) -> Path:
    return env_dir / ("Scripts" if os.name == "nt" else "bin")


@pytest.fixture(scope="module")
def script(tmp_path_factory: pytest.TempPathFactory) -> str:
    if sys.prefix != sys.base_prefix:
        python, scripts = sys.executable, Path(sysconfig.get_path("scripts"))
        extra = ["--no-build-isolation"]
    else:
        env_dir = tmp_path_factory.mktemp("venv")
        venv.EnvBuilder(with_pip=True).create(env_dir)
        scripts = _scripts_dir(env_dir)
        python, extra = str(scripts / "python"), []
    command = [python, "-m", "pip", "install", "--quiet", "--no-deps", *extra, "-e", str(_ROOT)]
    subprocess.run(command, check=True, capture_output=True, timeout=600)
    found = shutil.which("lvjson", path=str(scripts))
    assert found is not None, "pip did not install the lvjson console script"
    return found


def _run(script: str, *args: str, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([script, *args], input=stdin, capture_output=True, timeout=60)


def test_version_comes_from_the_installed_package(script: str) -> None:
    result = _run(script, "--version")
    assert result.returncode == 0
    assert result.stdout.decode().strip() == f"lvjson {lvjson.__version__}"


def test_help_lists_the_commands_and_examples(script: str) -> None:
    result = _run(script, "--help")
    assert result.returncode == 0
    for text in (b"to-portable", b"to-labview", b"check", b"examples:"):
        assert text in result.stdout


def test_real_capture_to_portable_is_strict(script: str) -> None:
    result = _run(script, "to-portable", str(_NONFINITE))
    assert result.returncode == 0, result.stderr

    def refuse(token: str) -> None:
        raise AssertionError(token)

    data = json.loads(result.stdout, parse_constant=refuse)
    assert data["Data"][0] == [None, None, None, 0]
    assert data["Data"][1][0] == 0.1


def test_real_capture_is_reproduced_byte_for_byte(script: str, tmp_path: Path) -> None:
    for capture in sorted(_FIXTURES.glob("flatten_to_json_*.json")):
        out = tmp_path / capture.name
        args = ["to-labview", str(capture), "--number-style", "labview", "-o", str(out)]
        result = _run(script, *args)
        assert result.returncode == 0, result.stderr
        assert out.read_bytes() == capture.read_bytes()


def test_stdin_pipeline_keeps_labview_utf8(script: str) -> None:
    first = _run(script, "to-portable", "--nan-inf", "extend", stdin=_ESCAPES.read_bytes())
    assert first.returncode == 0, first.stderr
    assert "é".encode() in first.stdout
    back = _run(script, "to-labview", "--number-style", "labview", stdin=first.stdout)
    assert back.returncode == 0, back.stderr
    assert back.stdout.rstrip(b"\r\n") == _ESCAPES.read_bytes()


def test_check_reports_the_real_tokens_and_strict_fails(script: str) -> None:
    result = _run(script, "check", str(_NONFINITE))
    assert result.returncode == 0
    assert b"NaN x1, Infinity x1, -Infinity x1" in result.stdout
    assert _run(script, "check", "--strict", str(_NONFINITE)).returncode == 1


def test_short_spelling_is_available(script: str) -> None:
    result = _run(script, "to-labview", "--infinity", "Inf", stdin=b"[Infinity,-Infinity,NaN]")
    assert result.returncode == 0
    assert result.stdout.strip() == b"[Inf,-Inf,NaN]"


def test_errors_exit_one_and_bad_usage_exits_two(script: str) -> None:
    assert _run(script, "to-portable", stdin=b"{not json}").returncode == 1
    assert _run(script, "to-portable", "--nan-inf", "reject", str(_NONFINITE)).returncode == 1
    assert _run(script, "to-portable", "no-such-file.json").returncode == 1
    assert _run(script, "frobnicate").returncode == 2
