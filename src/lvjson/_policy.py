"""How non-finite floats (NaN, Infinity, -Infinity) are treated at the boundary."""

from __future__ import annotations

from typing import Literal

# "extend": keep LabVIEW's JSON extension tokens (NaN, Infinity, -Infinity). This is what
#   the LabVIEW JSON node emits and ingests when "enable LabVIEW extensions" is on.
# "null":   replace every non-finite float with JSON null, producing strict, portable JSON.
# "reject": refuse the value and raise, for pipelines that must never see a non-finite float.
NanInf = Literal["extend", "null", "reject"]

_VALID: frozenset[str] = frozenset(("extend", "null", "reject"))


def check(policy: NanInf) -> None:
    """Validate a policy string, so a typo fails loudly instead of being ignored."""
    if policy not in _VALID:
        allowed = ", ".join(sorted(_VALID))
        raise ValueError(f"nan_inf must be one of {allowed}, got {policy!r}")
