"""Find and respell the bare non-finite tokens in extended JSON text.

LabVIEW 2026's Flatten To JSON writes ``NaN``, ``Infinity`` and ``-Infinity``, the same spelling
the standard ``json`` module uses (verified against captured LabVIEW output). Other producers,
and lvjson 0.2.0, spell the infinities ``Inf`` and ``-Inf``. Only bare words outside string
literals are tokens: text inside a string is never counted or changed. Working on the text,
rather than re-encoding, keeps everything else (key order, spacing, digits) byte for byte intact.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

# A string literal is matched first so that its contents are skipped as a whole. Otherwise a
# bare non-finite word, bounded so that "Infinity" is never read as "Inf" and "xNaN" is ignored.
_SCAN = re.compile(
    r'"[^"\\]*(?:\\.[^"\\]*)*"'
    r"|(?<![\w.])(?P<token>-?(?:Infinity|Inf)|NaN)(?![\w.])",
    re.DOTALL,
)

# Every spelling count_nonfinite can report, in the order it reports them.
SPELLINGS: tuple[str, ...] = ("NaN", "Infinity", "-Infinity", "Inf", "-Inf")


def iter_tokens(text: str) -> Iterator[re.Match[str]]:
    """Yield a match for each bare non-finite token outside string literals."""
    for match in _SCAN.finditer(text):
        if match.group("token") is not None:
            yield match


def count_nonfinite(text: str) -> dict[str, int]:
    """Count each non-finite spelling that appears as a bare token, outside string literals.

    The result maps a spelling (``'NaN'``, ``'Infinity'``, ``'-Infinity'``, ``'Inf'``,
    ``'-Inf'``) to how often it occurs; spellings that do not occur are left out, so an empty
    dict means the text holds no non-finite token at all. The text is not parsed, so this works
    on documents that are otherwise malformed too.
    """
    seen: dict[str, int] = {}
    for match in iter_tokens(text):
        token = match.group("token")
        seen[token] = seen.get(token, 0) + 1
    return {spelling: seen[spelling] for spelling in SPELLINGS if spelling in seen}


def _respell(text: str, source: str, target: str) -> str:
    def swap(match: re.Match[str]) -> str:
        token = match.group("token")
        if token is None or token.lstrip("-") != source:
            return match.group(0)
        return token.replace(source, target)

    return _SCAN.sub(swap, text)


def expand_inf(text: str) -> str:
    """Rewrite ``Inf`` / ``-Inf`` to the ``json`` module's ``Infinity`` / ``-Infinity``.

    ``Infinity`` and ``NaN`` are already the ``json`` spelling and pass through untouched, so
    real LabVIEW 2026 output comes back unchanged.
    """
    return _respell(text, "Inf", "Infinity")


def shorten_infinity(text: str) -> str:
    """Rewrite ``Infinity`` / ``-Infinity`` to the short ``Inf`` / ``-Inf`` spelling."""
    return _respell(text, "Infinity", "Inf")
