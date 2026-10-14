"""Command line interface: convert LabVIEW JSON to portable JSON and back, or check a file."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Sequence
from typing import NoReturn, cast

from . import __version__
from ._cli_io import MESSAGE_LIMIT, OutputClosed, emit, read_source, report, write_file
from ._errors import LVJSONError
from ._policy import MAX_INDENT, InfSpelling, NanInf, NumberStyle
from ._serialize import to_labview, to_portable
from ._text import decode_text, shorten
from ._tokens import count_nonfinite, expand_inf

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

exit status: 0 on success, 1 on an input, conversion or --strict failure or a closed
output, 2 on bad usage, 130 when interrupted.
"""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse quotes the offending argument: cut long words, and keep the whole error line
        # ("<prog>: error: <message>") within the limit.
        # One line: control characters in an argument are shown as escapes, as repr would.
        message = "".join(char if char >= " " else repr(char)[1:-1] for char in message)
        message = shorten(message)
        room = MESSAGE_LIMIT - len(f"{self.prog}: error: ")
        if len(message) > room:
            message = message[: max(room - 3, 0)] + "..."
        super().error(message)


def _indent(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {shorten(text)}") from None
    if not 0 <= value <= MAX_INDENT:
        raise argparse.ArgumentTypeError(f"must be from 0 to {MAX_INDENT}")
    return value


def _add_io(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", nargs="?", help="input file, or stdin when omitted or '-'")
    parser.add_argument(
        "-o", "--output", metavar="FILE", help="write here (UTF-8, no trailing newline)"
    )
    parser.add_argument(
        "--indent", type=_indent, metavar="N", help="pretty-print with N spaces, 0 to 1024"
    )
    parser.add_argument("--sort-keys", action="store_true", help="sort object keys")


def _add_policy(parser: argparse.ArgumentParser, default: str, help: str) -> None:
    choices = ("extend", "null", "reject")
    parser.add_argument("--nan-inf", choices=choices, default=default, help=help)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="lvjson",
        description="Convert between LabVIEW Flatten To JSON text and portable JSON.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvjson {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    forward = commands.add_parser("to-portable", help="read LabVIEW JSON, emit strict JSON")
    _add_io(forward)
    _add_policy(forward, "null", "non-finite values: null (default), keep (extend) or fail")

    reverse = commands.add_parser("to-labview", help="read JSON, emit LabVIEW JSON")
    _add_io(reverse)
    _add_policy(reverse, "extend", "non-finite values: keep (extend, default), null or fail")
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

    check = commands.add_parser("check", help="parse a file and list its non-finite values")
    check.add_argument("file", nargs="?", help="input file, or stdin when omitted or '-'")
    check.add_argument(
        "--strict", action="store_true", help="exit 1 if any non-finite value is present"
    )
    return parser


def _overflows(text: str) -> int:
    """Count the numbers that are finite in the text but overflow a double (``1e400``)."""
    found = 0

    def number(token: str) -> float:
        nonlocal found
        value = float(token)
        found += math.isinf(value)
        return value

    try:
        json.loads(expand_inf(text), parse_float=number)
    except ValueError as exc:
        raise LVJSONError(shorten(str(exc))) from None
    except RecursionError:
        raise LVJSONError("JSON nesting is too deep to parse") from None
    return found


def _check(args: argparse.Namespace) -> int:
    text = decode_text(read_source(args.file))
    overflow = _overflows(text)
    found = [f"{token} x{count}" for token, count in count_nonfinite(text).items()]
    if overflow:
        found.append(f"numbers that overflow a double x{overflow}")
    name = args.file if args.file not in (None, "-") else "<stdin>"
    if not found:
        emit(f"{name}: valid, no non-finite tokens (strict JSON)")
        return 0
    emit(f"{name}: valid, non-finite values: {', '.join(found)}")
    return 1 if args.strict else 0


def _convert(args: argparse.Namespace) -> int:
    source = read_source(args.file)
    nan_inf = cast(NanInf, args.nan_inf)
    if args.command == "to-portable":
        result = to_portable(source, nan_inf=nan_inf, indent=args.indent, sort_keys=args.sort_keys)
    else:
        result = to_labview(
            source,
            nan_inf=nan_inf,
            indent=args.indent,
            sort_keys=args.sort_keys,
            infinity=cast(InfSpelling, args.infinity),
            number_style=cast(NumberStyle, args.number_style),
        )
    if args.output is not None and args.output != "-":
        write_file(result, args.output)
    else:
        emit(result)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvjson`` console script. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        return _check(args) if args.command == "check" else _convert(args)
    except OutputClosed:
        return 1
    except KeyboardInterrupt:
        return 130
    except MemoryError:
        report("lvjson: out of memory (a deeply nested value with a wide --indent grows fast)")
        return 1
    except (LVJSONError, OSError, UnicodeError, ValueError) as exc:
        report(f"lvjson: {shorten(str(exc))}")
        return 1
