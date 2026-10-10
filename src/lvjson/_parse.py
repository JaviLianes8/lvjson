"""Read LabVIEW "Flatten To JSON" text into Python objects."""

from __future__ import annotations

import json
import math
from typing import Any

from ._errors import LVJSONError
from ._policy import NanInf, check


def _reject_constant(token: str) -> float:
    raise LVJSONError(f"non-finite token {token!r} is not allowed under nan_inf='reject'")


def loads(text: str, *, nan_inf: NanInf = "extend") -> Any:
    """Parse LabVIEW JSON, accepting its ``NaN`` / ``Infinity`` / ``-Infinity`` extensions.

    LabVIEW's node emits those bare tokens, which strict parsers reject. With the default
    ``nan_inf='extend'`` they decode to ``float('nan')`` and the infinities. With
    ``nan_inf='reject'`` any of them raises :class:`LVJSONError` instead of decoding; and
    ``nan_inf='null'`` is treated the same as ``extend`` on input (there is nothing to drop
    when reading). Malformed JSON always raises :class:`LVJSONError`.
    """
    check(nan_inf)
    parse_constant = _reject_constant if nan_inf == "reject" else None
    try:
        return json.loads(text, parse_constant=parse_constant)
    except json.JSONDecodeError as exc:
        raise LVJSONError(str(exc)) from exc


def has_nonfinite(obj: Any) -> bool:
    """Return whether ``obj`` holds any NaN or infinite float, at any depth.

    Useful before handing a structure to a strict JSON consumer: a ``True`` result means a
    plain ``json.dumps`` would either emit the non-portable extension tokens or fail.
    """
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(has_nonfinite(value) for value in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(has_nonfinite(item) for item in obj)
    return False
