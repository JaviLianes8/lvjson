"""The documentation is executable: doctests, README and GUIDE examples and transcripts run."""

from __future__ import annotations

import doctest
import importlib
import inspect
import io
import pkgutil
import re
import shlex
from pathlib import Path

import pytest

import lvjson
from lvjson._cli import main

_ROOT = Path(__file__).resolve().parent.parent
_MODULES = ["lvjson"] + [f"lvjson.{info.name}" for info in pkgutil.iter_modules(lvjson.__path__)]
_DOCS = ["README.md", "GUIDE.md"]
_PYCON = re.compile(r"```pycon\n(.*?)```", re.DOTALL)
_SHELL = re.compile(r"```\n(\$ .*?)```", re.DOTALL)
_ECHO = re.compile(r"^echo '(?P<data>[^']*)' \| lvjson (?P<args>.*)$")


def _text(name: str) -> str:
    return (_ROOT / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", _MODULES)
def test_module_doctests_pass(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name))
    assert result.failed == 0


@pytest.mark.parametrize(
    "name", [name for name in lvjson.__all__ if inspect.isroutine(getattr(lvjson, name))]
)
def test_every_public_function_has_a_docstring_with_an_example(name: str) -> None:
    assert ">>>" in (getattr(lvjson, name).__doc__ or "")


def test_the_error_type_and_the_option_aliases_have_examples() -> None:
    assert ">>>" in (lvjson.LVJSONError.__doc__ or "")
    examples = [line for line in (lvjson.__doc__ or "").splitlines() if line.startswith(">>>")]
    for alias in ("NanInf", "InfSpelling", "NumberStyle"):
        assert any(alias in line for line in examples)


@pytest.mark.parametrize("name", _DOCS)
def test_every_pycon_example_runs(name: str) -> None:
    blocks = _PYCON.findall(_text(name))
    assert blocks
    parser, runner = doctest.DocTestParser(), doctest.DocTestRunner()
    # Blocks of one document share a namespace, as a reader following along would.
    namespace: dict[str, object] = {}
    for number, block in enumerate(blocks):
        test = parser.get_doctest(block, namespace, f"{name}[{number}]", name, 0)
        runner.run(test, clear_globs=False)
        namespace.update(test.globs)
    assert runner.summarize(verbose=False).failed == 0


def _transcripts() -> list[tuple[str, str, str]]:
    found = []
    for name in _DOCS:
        for block in _SHELL.findall(_text(name)):
            command, output = "", list[str]()
            for line in [*block.splitlines(), "$ "]:
                if line.startswith("$ "):
                    if command:
                        found.append((name, command, "\n".join(output)))
                    command, output = line[2:], []
                else:
                    output.append(line)
    return found


_TRANSCRIPTS = _transcripts()


def test_both_documents_hold_command_line_transcripts() -> None:
    assert {name for name, _, _ in _TRANSCRIPTS} == set(_DOCS)


@pytest.mark.parametrize(("name", "command", "expected"), _TRANSCRIPTS)
def test_every_transcript_prints_what_it_shows(
    name: str,
    command: str,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    match = _ECHO.match(command)
    assert match, f"{name}: transcripts pipe echo into lvjson: {command}"
    stdin = io.TextIOWrapper(io.BytesIO((match["data"] + "\n").encode()), encoding="utf-8")
    monkeypatch.setattr("sys.stdin", stdin)
    main(shlex.split(match["args"]))
    assert capsysbinary.readouterr().out.decode() == expected + "\n"


@pytest.mark.parametrize("name", _DOCS)
def test_links_are_absolute_and_examples_use_only_public_names(name: str) -> None:
    text = _text(name)
    for target in re.findall(r"\]\(([^)]+)\)", text):
        assert target.startswith(("https://", "#")), target
    assert "lvjson._" not in text
    assert "\u2014" not in text
