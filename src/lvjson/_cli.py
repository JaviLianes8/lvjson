"""Command line interface: convert LabVIEW JSON to portable JSON and back."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import cast

from . import __version__
from ._errors import LVJSONError
from ._policy import NanInf
from ._serialize import to_labview, to_portable

_EPILOG = """\
examples:
  # LabVIEW JSON to portable JSON, non-finite values become null (the default)
  echo '{"gain":2.5,"reading":NaN,"limit":Inf}' | lvjson to-portable

  # keep the infinities as the json module's tokens instead of dropping them
  lvjson to-portable data.lvjson --nan-inf extend

  # portable JSON back to the LabVIEW spelling (NaN / Inf / -Inf)
  echo '{"limit":Infinity}' | lvjson to-labview

  # fail loudly if any non-finite value is present
  lvjson to-portable data.lvjson --nan-inf reject
"""


def _read(source: str | None) -> str:
    if source is None or source == "-":
        return sys.stdin.read()
    with open(source, encoding="utf-8") as handle:
        return handle.read()


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", nargs="?", help="input file, or stdin when omitted or '-'")
    parser.add_argument(
        "--nan-inf",
        choices=("extend", "null", "reject"),
        help="how to treat NaN / Inf / -Inf (default: null for to-portable, extend for to-labview)",
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
    subparsers = parser.add_subparsers(dest="command", required=True)

    forward = subparsers.add_parser("to-portable", help="read LabVIEW JSON and emit standard JSON")
    _add_common(forward)

    reverse = subparsers.add_parser(
        "to-labview", help="read standard JSON and emit the LabVIEW JSON spelling"
    )
    _add_common(reverse)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvjson`` console script. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    convert: Callable[..., str]
    if args.command == "to-portable":
        convert = to_portable
        nan_inf = cast(NanInf, args.nan_inf or "null")
    else:
        convert = to_labview
        nan_inf = cast(NanInf, args.nan_inf or "extend")

    try:
        text = _read(args.file)
        result = convert(text, nan_inf=nan_inf, indent=args.indent, sort_keys=args.sort_keys)
    except LVJSONError as exc:
        print(f"lvjson: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"lvjson: {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0
