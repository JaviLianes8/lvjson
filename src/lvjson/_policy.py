"""The options that decide how values cross the LabVIEW boundary, and their validation."""

from __future__ import annotations

from typing import Literal

# How non-finite floats (NaN, +inf, -inf) are treated:
# "extend": keep them as the bare extension tokens. LabVIEW 2026's Flatten To JSON writes
#   NaN, Infinity and -Infinity (verified against captured output).
# "null":   replace every non-finite float with JSON null, producing strict, portable JSON.
# "reject": refuse the value and raise, for pipelines that must never see a non-finite float.
NanInf = Literal["extend", "null", "reject"]

# How the infinities are spelled on output:
# "Infinity": Infinity / -Infinity, what LabVIEW 2026 writes and what the json module reads.
# "Inf":      Inf / -Inf, for consumers that expect the short spelling. LabVIEW 2026 does not
#   write it, and its JSON lexer's keyword table has no entry for it.
InfSpelling = Literal["Infinity", "Inf"]

# How finite floats are written:
# "shortest": the shortest text that round-trips the double (Python's repr), e.g. 0.1 and 1.0.
# "labview":  LabVIEW's own form, 20 significant digits with trailing zeros dropped (C "%.20g"),
#   e.g. 0.10000000000000000555 and 1. It reproduces captured Flatten To JSON output exactly.
NumberStyle = Literal["shortest", "labview"]

_CHOICES: dict[str, frozenset[str]] = {
    "nan_inf": frozenset(("extend", "null", "reject")),
    "infinity": frozenset(("Infinity", "Inf")),
    "number_style": frozenset(("shortest", "labview")),
}


def _validate(name: str, value: object) -> None:
    allowed = _CHOICES[name]
    if value not in allowed:
        listed = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of {listed}, got {value!r}")


def check(policy: NanInf) -> None:
    """Validate a ``nan_inf`` policy, so a typo fails loudly instead of being ignored."""
    _validate("nan_inf", policy)


def check_output(infinity: InfSpelling, number_style: NumberStyle) -> None:
    """Validate the output spelling options."""
    _validate("infinity", infinity)
    _validate("number_style", number_style)
