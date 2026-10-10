"""Emit JSON that the LabVIEW JSON node ingests cleanly, without silent precision loss."""

from __future__ import annotations

import json
import math
from typing import Any

from ._errors import LVJSONError
from ._parse import loads
from ._policy import NanInf, check

# Compact separators mirror LabVIEW's own flattened output and keep the payload small; the
# standard library already formats floats with the shortest round-trippable repr, so a value
# read with loads and written with dumps survives unchanged.
_COMPACT = (",", ":")


def _to_null(obj: Any) -> Any:
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {key: _to_null(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_to_null(item) for item in obj]
    if isinstance(obj, tuple):
        return [_to_null(item) for item in obj]
    return obj


def dumps(
    obj: Any,
    *,
    nan_inf: NanInf = "extend",
    indent: int | None = None,
    sort_keys: bool = False,
) -> str:
    """Serialise ``obj`` to JSON the LabVIEW JSON node can ingest.

    Floats keep their full double precision (the shortest representation that round-trips),
    so there is no silent digit loss on the way back into LabVIEW. ``nan_inf`` controls
    non-finite floats: ``'extend'`` emits LabVIEW's ``NaN`` / ``Infinity`` / ``-Infinity``
    tokens, ``'null'`` replaces each with ``null`` for strict consumers, and ``'reject'``
    raises :class:`LVJSONError`.
    """
    check(nan_inf)
    payload = _to_null(obj) if nan_inf == "null" else obj
    separators = None if indent is not None else _COMPACT
    try:
        return json.dumps(
            payload,
            allow_nan=(nan_inf == "extend"),
            indent=indent,
            separators=separators,
            sort_keys=sort_keys,
            ensure_ascii=False,
        )
    except ValueError as exc:
        raise LVJSONError(str(exc)) from exc


def round_trip(
    text: str,
    *,
    nan_inf: NanInf = "extend",
    indent: int | None = None,
    sort_keys: bool = False,
) -> str:
    """Parse LabVIEW JSON and re-emit it in canonical, LabVIEW-ingestable form.

    Finite numbers are preserved exactly (they decode to IEEE 754 doubles and re-encode with
    the shortest round-trippable form), so this normalises LabVIEW's adaptive 13 to 17 digit
    formatting without changing any value. Non-finite floats follow ``nan_inf``.
    """
    return dumps(loads(text), nan_inf=nan_inf, indent=indent, sort_keys=sort_keys)
