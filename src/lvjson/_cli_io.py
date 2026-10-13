"""Byte-exact input and output for the command line, and quiet handling of dead streams."""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from typing import TextIO

# Error messages printed by the command line are cut to this many characters.
MESSAGE_LIMIT = 200


class OutputClosed(Exception):
    """Standard output went away while writing (a closed pipe)."""


def read_source(source: str | None) -> bytes | str:
    """Read a file's bytes, or standard input when ``source`` is ``None`` or ``'-'``."""
    if source is not None and source != "-":
        return Path(source).read_bytes()
    stream = sys.stdin
    if stream is None:
        raise OSError("standard input is not available")
    buffer = getattr(stream, "buffer", None)
    return buffer.read() if buffer is not None else stream.read()


def write_file(text: str, target: str) -> None:
    """Write ``text`` to a file as UTF-8, with no trailing newline."""
    Path(target).write_bytes(text.encode("utf-8"))


def emit(text: str) -> None:
    """Write one line to standard output as UTF-8 bytes, whatever the console code page."""
    data = (text + "\n").encode("utf-8")
    stream = sys.stdout
    try:
        if stream is None:
            raise OutputClosed
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            stream.write(data.decode("utf-8"))
            stream.flush()
            return
        stream.flush()
        buffer.write(data)
        buffer.flush()
    except (OSError, ValueError) as exc:
        # A reader that went away is EPIPE on POSIX and EINVAL on Windows.
        silence(stream)
        raise OutputClosed from exc


def report(message: str) -> None:
    """Print an error message to standard error, cut short, never raising."""
    if len(message) > MESSAGE_LIMIT:
        message = message[:MESSAGE_LIMIT] + "..."
    try:
        print(message, file=sys.stderr, flush=True)
    except (OSError, ValueError, AttributeError, UnicodeError):
        silence(sys.stderr)


def silence(stream: TextIO | None) -> None:
    """Point a dead stream at the null device so the exit flush cannot fail."""
    with contextlib.suppress(OSError, ValueError, AttributeError):
        os.dup2(os.open(os.devnull, os.O_WRONLY), stream.fileno())  # type: ignore[union-attr]
