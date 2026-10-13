"""The options that decide how values cross the LabVIEW boundary, and their validation."""

from __future__ import annotations

from typing import Literal, cast

from ._text import describe, type_name

# How non-finite floats (NaN, +inf, -inf) are treated:
# "extend": keep them as the bare extension tokens. LabVIEW 2026's Flatten To JSON writes
#   NaN, Infinity and -Infinity (verified against captured output).
# "null":   replace every non-finite float with JSON null, producing strict, portable JSON.
# "reject": refuse the value and raise, for pipelines that must never see a non-finite float.
NanInf = Literal["extend", "null", "reject"]

# How the infinities are spelled on output:
# "Infinity": Infinity / -Infinity, what LabVIEW 2026 writes and what the json module reads.
# "Inf":      Inf / -Inf, for consumers that expect the short spelling. LabVIEW 2026 was not
#   seen to write it (DBL values, default settings), and its JSON lexer's keyword table has no
#   entry for it.
InfSpelling = Literal["Infinity", "Inf"]

# How finite floats are written:
# "shortest": the shortest text that round-trips the double (Python's repr), e.g. 0.1 and 1.0.
# "labview":  LabVIEW's DBL form, 20 significant digits with trailing zeros dropped (C "%.20g"),
#   e.g. 0.10000000000000000555 and 1. It reproduces captured Flatten To JSON output exactly.
NumberStyle = Literal["shortest", "labview"]

_CHOICES: dict[str, frozenset[str]] = {
    "nan_inf": frozenset(("extend", "null", "reject")),
    "infinity": frozenset(("Infinity", "Inf")),
    "number_style": frozenset(("shortest", "labview")),
}


def _validate(name: str, value: object) -> str:
    # Compare the plain text of a str (or str subclass such as a StrEnum member) only, so an
    # object with a permissive __eq__ cannot slip through; callers use the returned plain str.
    allowed = _CHOICES[name]
    plain = str.__str__(value) if isinstance(value, str) else ""
    if plain not in allowed:
        listed = ", ".join(repr(choice) for choice in sorted(allowed))
        raise ValueError(f"{name} must be one of {listed}, got {describe(value)}")
    return plain


def check(policy: NanInf) -> NanInf:
    """Validate a ``nan_inf`` policy and return it as a plain ``str``."""
    return cast(NanInf, _validate("nan_inf", policy))


def check_output(
    infinity: InfSpelling, number_style: NumberStyle
) -> tuple[InfSpelling, NumberStyle]:
    """Validate the output spelling options and return them as plain ``str`` values."""
    return (
        cast(InfSpelling, _validate("infinity", infinity)),
        cast(NumberStyle, _validate("number_style", number_style)),
    )


def check_indent(indent: int | None) -> int | None:
    """Validate ``indent`` (``None`` or a non-negative ``int``) and return it as a plain int."""
    if indent is None:
        return None
    if not isinstance(indent, int) or isinstance(indent, bool):
        raise TypeError(f"indent must be None or an int, got {type_name(indent)}")
    plain = int.__int__(indent)
    if plain < 0:
        raise ValueError("indent must not be negative")
    return plain
