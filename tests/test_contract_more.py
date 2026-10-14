"""Contracts for paths a value or a stream can reach only by changing under the library."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import lvjson
from lvjson import LVJSONError, NumberStyle, dumps
from lvjson._cli import main

_STYLES: tuple[NumberStyle, ...] = ("shortest", "labview")


class _FlipKey(dict[Any, Any]):
    # A finite key for the policy scan, a non-finite one for the encoder.
    def __init__(self, key: float) -> None:
        super().__init__(a=1)
        self.key = key
        self.calls = 0

    def items(self) -> Any:
        self.calls += 1
        return [(1.0 if self.calls == 1 else self.key, 1)]


@pytest.mark.parametrize("key", [float("nan"), float("inf"), float("-inf")])
def test_the_labview_encoder_checks_every_key_it_writes(key: float) -> None:
    for policy in ("null", "reject"):
        with pytest.raises(LVJSONError, match="dict key is only allowed"):
            dumps(_FlipKey(key), nan_inf=policy, number_style="labview")


@pytest.mark.parametrize("style", _STYLES)
def test_every_key_of_a_dict_is_checked_not_only_the_first(style: NumberStyle) -> None:
    for policy in ("null", "reject"):
        with pytest.raises(LVJSONError, match="dict key is only allowed"):
            dumps({"a": 1, "b": 2, float("nan"): 3}, nan_inf=policy, number_style=style)


class _OutOfMemory(dict[str, Any]):
    def items(self) -> Any:
        raise MemoryError


@pytest.mark.parametrize("style", _STYLES)
def test_running_out_of_memory_is_never_disguised(style: NumberStyle) -> None:
    with pytest.raises(MemoryError):
        dumps(_OutOfMemory(a=1), number_style=style)


def test_the_command_line_reports_running_out_of_memory(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def exhausted(*args: Any, **kwargs: Any) -> str:
        raise MemoryError

    monkeypatch.setattr("lvjson._cli.to_portable", exhausted)
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"[1]"), encoding="utf-8"))
    assert main(["to-portable"]) == 1
    assert capsys.readouterr().err.startswith("lvjson: out of memory")


class _Meta(type):
    @property
    def __name__(cls) -> str:  # type: ignore[override]
        return "Fake"


class _Odd(metaclass=_Meta):
    pass


def test_a_metaclass_cannot_change_the_type_name_in_messages() -> None:
    cases: list[tuple[Any, NumberStyle]] = [
        ([_Odd()], "shortest"),
        ([_Odd()], "labview"),
        ({_Odd(): 1}, "labview"),
    ]
    for value, style in cases:
        with pytest.raises(TypeError) as info:
            dumps(value, number_style=style)
        assert "_Odd" in str(info.value) and "Fake" not in str(info.value)


class _LyingText(str):
    def __repr__(self) -> str:
        return "LIE" * 100


def test_a_lying_repr_is_never_used_to_describe_an_option() -> None:
    with pytest.raises(ValueError) as info:
        dumps([1], nan_inf=_LyingText("bogus"))  # type: ignore[arg-type]
    assert str(info.value).endswith("got 'bogus'")


class _FloatKey(float):
    pass


def test_float_subclass_keys_are_written_by_their_value() -> None:
    assert dumps({_FloatKey(0.1): 1}, number_style="labview") == '{"0.10000000000000000555":1}'
    assert dumps({_FloatKey(0.1): 1}) == '{"0.1":1}'


def test_a_closed_pipe_exits_1_quietly_in_a_real_process() -> None:
    package_root = str(Path(lvjson.__file__).resolve().parents[1])
    env = dict(os.environ, PYTHONPATH=package_root, PYTHONDONTWRITEBYTECODE="1")
    code = "import sys; from lvjson._cli import main; sys.exit(main(['to-portable']))"
    child = subprocess.Popen(
        [sys.executable, "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert child.stdin is not None and child.stdout is not None and child.stderr is not None
    child.stdout.close()  # the reader goes away before the child writes
    child.stdin.write(b"[1.5,1.5,1.5]")
    child.stdin.close()
    err = child.stderr.read()
    child.stderr.close()
    assert child.wait(timeout=60) == 1
    assert err == b""
