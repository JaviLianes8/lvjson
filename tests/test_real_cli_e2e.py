"""Real end-to-end: install the package editable and drive the genuine ``lvjson`` script.

No imports of the package's CLI, no mocks: every test shells out to the console script that
pip generated, feeding it the bytes captured from LabVIEW 2026. The project is installed into
a throwaway virtual environment, so the developer's own environment is never modified. The
build backend (hatchling, editables) is borrowed from the running interpreter for the install
only, so no network is needed; the test is skipped with a reason when it is not available.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import venv
from pathlib import Path

import pytest

import lvjson

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = _ROOT / "tests" / "fixtures" / "labview2026"
_NONFINITE = _FIXTURES / "flatten_to_json_nonfinite.json"
_ESCAPES = _FIXTURES / "flatten_to_json_escapes.json"


def _backend_dirs() -> list[str]:
    dirs: list[str] = []
    for name in ("hatchling", "editables"):
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None:
            pytest.skip(f"{name} is needed to build the editable install (pip install -e .[dev])")
        parent = str(Path(spec.origin).resolve().parents[1])
        if parent not in dirs:
            dirs.append(parent)
    return dirs


@pytest.fixture(scope="module")
def script(tmp_path_factory: pytest.TempPathFactory) -> str:
    backend = _backend_dirs()
    env_dir = tmp_path_factory.mktemp("venv")
    try:
        venv.EnvBuilder(with_pip=True).create(env_dir)
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"cannot create a virtual environment with pip: {exc}")
    scripts = env_dir / ("Scripts" if os.name == "nt" else "bin")
    python = str(scripts / "python")
    query = "import sysconfig; print(sysconfig.get_path('purelib'))"
    purelib = subprocess.run([python, "-c", query], capture_output=True, text=True, check=True)
    # A .pth file appends the backend's directories after the environment's own packages, so the
    # environment's pip still wins. It is removed once the install is done.
    borrowed = Path(purelib.stdout.strip()) / "_borrowed_build_backend.pth"
    borrowed.write_text("".join(f"{line}\n" for line in backend), encoding="utf-8")
    command = [python, "-m", "pip", "install", "--quiet", "--no-deps", "--no-build-isolation"]
    try:
        subprocess.run([*command, "-e", str(_ROOT)], check=True, capture_output=True, timeout=600)
    finally:
        borrowed.unlink()
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
