"""Read LabVIEW "Flatten To JSON" text into Python objects."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any

from ._errors import LVJSONError
from ._policy import NanInf, check
from ._tokens import labview_to_json


def _reject_constant(token: str) -> float:
    raise LVJSONError(f"non-finite token {token!r} is not allowed under nan_inf='reject'")


def _null_constant(token: str) -> None:
    return None


def loads(text: str, *, nan_inf: NanInf = "extend") -> Any:
    """Parse LabVIEW JSON, accepting its ``NaN`` / ``Inf`` / ``-Inf`` extension tokens.

    LabVIEW's node writes ``Inf`` and ``-Inf``, which the standard ``json`` module cannot read
    (it only knows ``Infinity`` / ``-Infinity``). lvjson translates them first, so both
    spellings are accepted. ``nan_inf`` decides what a non-finite token becomes: ``'extend'``
    decodes to ``float('nan')`` and the infinities, ``'null'`` decodes each to ``None``, and
    ``'reject'`` raises :class:`LVJSONError`. Malformed JSON always raises :class:`LVJSONError`.
    """
    check(nan_inf)
    parse_constant: Callable[[str], Any] | None = None
    if nan_inf == "reject":
        parse_constant = _reject_constant
    elif nan_inf == "null":
        parse_constant = _null_constant
    try:
        return json.loads(labview_to_json(text), parse_constant=parse_constant)
    except json.JSONDecodeError as exc:
        raise LVJSONError(str(exc)) from exc


def has_nonfinite(obj: Any) -> bool:
    """Return whether ``obj`` holds any NaN or infinite float, at any depth.

    Useful before handing a structure to a strict JSON consumer: a ``True`` result means a
    plain ``json.dumps`` would either emit non-portable tokens or fail.
    """
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(has_nonfinite(value) for value in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(has_nonfinite(item) for item in obj)
    return False
