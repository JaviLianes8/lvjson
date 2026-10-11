"""Command line interface: convert LabVIEW JSON to portable JSON and back, or check a file."""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from . import __version__
from ._errors import LVJSONError
from ._parse import decode_text, loads
from ._policy import InfSpelling, NanInf, NumberStyle
from ._serialize import to_labview, to_portable
from ._tokens import count_nonfinite

_EPILOG = """\
examples:
  # LabVIEW JSON to strict portable JSON: NaN / Infinity / -Infinity become null
  echo '{"gain":2.5,"reading":NaN,"limit":Infinity}' | lvjson to-portable

  # keep the non-finite tokens instead of dropping them
  lvjson to-portable data.json --nan-inf extend

  # back to LabVIEW, re-creating Flatten To JSON's exact 20-digit number formatting
  echo '{"x":0.1,"limit":null}' | lvjson to-labview --number-style labview

  # spell the infinities Inf / -Inf for a consumer that expects them
  lvjson to-labview data.json --infinity Inf -o out.json

  # list the non-finite values in a file; exit 1 if there are any
  lvjson check data.json --strict

exit status: 0 on success, 1 on an input, conversion or --strict failure, 2 on bad usage.
"""


def _read(source: str | None) -> bytes | str:
    if source is None or source == "-":
        buffer = getattr(sys.stdin, "buffer", None)
        return buffer.read() if buffer is not None else sys.stdin.read()
    return Path(source).read_bytes()


def _write(text: str, target: str | None) -> None:
    if target is not None and target != "-":
        Path(target).write_bytes(text.encode("utf-8"))
        return
    # Write UTF-8 bytes, so LabVIEW's UTF-8 text survives a narrow console code page.
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(text + "\n")
        return
    sys.stdout.flush()
    buffer.write((text + "\n").encode("utf-8"))
    buffer.flush()


def _add_io(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", nargs="?", help="input file, or stdin when omitted or '-'")
    parser.add_argument(
        "-o", "--output", metavar="FILE", help="write here (UTF-8, no trailing newline)"
    )
    parser.add_argument("--indent", type=int, metavar="N", help="pretty-print with N spaces")
    parser.add_argument("--sort-keys", action="store_true", help="sort object keys")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvjson",
        description="Convert between LabVIEW Flatten To JSON text and portable JSON.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvjson {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    forward = commands.add_parser("to-portable", help="read LabVIEW JSON, emit strict JSON")
    _add_io(forward)
    forward.add_argument(
        "--nan-inf",
        choices=("extend", "null", "reject"),
        default="null",
        help="non-finite values: null (default), keep them (extend) or fail (reject)",
    )

    reverse = commands.add_parser("to-labview", help="read JSON, emit LabVIEW JSON")
    _add_io(reverse)
    reverse.add_argument(
        "--nan-inf",
        choices=("extend", "null", "reject"),
        default="extend",
        help="non-finite values: keep them (extend, default), null or fail (reject)",
    )
    reverse.add_argument(
        "--infinity",
        choices=("Infinity", "Inf"),
        default="Infinity",
        help="spelling of the infinities (default: Infinity, as LabVIEW 2026 writes)",
    )
    reverse.add_argument(
        "--number-style",
        choices=("shortest", "labview"),
        default="shortest",
        help="shortest round-trip digits (default) or LabVIEW's 20-digit form",
    )

    check = commands.add_parser("check", help="parse a file and list its non-finite tokens")
    check.add_argument("file", nargs="?", help="input file, or stdin when omitted or '-'")
    check.add_argument(
        "--strict", action="store_true", help="exit 1 if any non-finite value is present"
    )
    return parser


def _nonfinite_values(obj: Any) -> int:
    if isinstance(obj, float):
        return 0 if math.isfinite(obj) else 1
    if isinstance(obj, dict):
        return sum(_nonfinite_values(value) for value in obj.values())
    if isinstance(obj, list):
        return sum(_nonfinite_values(item) for item in obj)
    return 0


def _check(args: argparse.Namespace) -> int:
    text = decode_text(_read(args.file))
    counts = count_nonfinite(text)
    # A finite-looking number such as 1e400 overflows to infinity when parsed.
    overflow = _nonfinite_values(loads(text)) - sum(counts.values())
    name = args.file if args.file not in (None, "-") else "<stdin>"
    found = [f"{token} x{count}" for token, count in counts.items()]
    if overflow > 0:
        found.append(f"numbers that overflow a double x{overflow}")
    if not found:
        _write(f"{name}: valid, no non-finite tokens (strict JSON)", None)
        return 0
    _write(f"{name}: valid, non-finite values: {', '.join(found)}", None)
    return 1 if args.strict else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvjson`` console script. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "check":
            return _check(args)
        source = _read(args.file)
        if args.command == "to-portable":
            result = to_portable(
                source,
                nan_inf=cast(NanInf, args.nan_inf),
                indent=args.indent,
                sort_keys=args.sort_keys,
            )
        else:
            result = to_labview(
                source,
                nan_inf=cast(NanInf, args.nan_inf),
                indent=args.indent,
                sort_keys=args.sort_keys,
                infinity=cast(InfSpelling, args.infinity),
                number_style=cast(NumberStyle, args.number_style),
            )
        _write(result, args.output)
    except (LVJSONError, OSError, UnicodeError) as exc:
        print(f"lvjson: {exc}", file=sys.stderr)
        return 1
    return 0
