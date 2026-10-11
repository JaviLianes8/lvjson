"""Emit JSON for LabVIEW or for strict consumers, without silent precision loss."""

from __future__ import annotations

import json
import math
from typing import Any

from ._errors import LVJSONError
from ._labview_format import encode_labview
from ._parse import has_nonfinite, loads
from ._policy import InfSpelling, NanInf, NumberStyle, check, check_output
from ._tokens import shorten_infinity

# Compact separators match LabVIEW's own flattened output and keep the payload small.
_COMPACT = (",", ":")


def _to_null(obj: Any) -> Any:
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {key: _to_null(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_null(item) for item in obj]
    return obj


def _encode(
    obj: Any,
    nan_inf: NanInf,
    indent: int | None,
    sort_keys: bool,
    number_style: NumberStyle = "shortest",
) -> str:
    """Encode to JSON text with the ``Infinity`` spelling, applying the non-finite policy."""
    check(nan_inf)
    if nan_inf == "reject" and has_nonfinite(obj):
        raise LVJSONError("non-finite float is not allowed under nan_inf='reject'")
    payload = _to_null(obj) if nan_inf == "null" else obj
    try:
        if number_style == "labview":
            return encode_labview(payload, infinity="Infinity", indent=indent, sort_keys=sort_keys)
        return json.dumps(
            payload,
            allow_nan=(nan_inf == "extend"),
            indent=indent,
            separators=None if indent is not None else _COMPACT,
            sort_keys=sort_keys,
            ensure_ascii=False,
        )
    except LVJSONError:
        raise
    except ValueError as exc:
        raise LVJSONError(str(exc)) from exc


def dumps(
    obj: Any,
    *,
    nan_inf: NanInf = "extend",
    indent: int | None = None,
    sort_keys: bool = False,
    infinity: InfSpelling = "Infinity",
    number_style: NumberStyle = "shortest",
) -> str:
    """Serialise ``obj`` to JSON the LabVIEW JSON node can ingest.

    ``nan_inf`` controls non-finite floats: ``'extend'`` emits ``NaN`` and the infinities,
    ``'null'`` replaces each with ``null``, and ``'reject'`` raises :class:`LVJSONError`.
    ``infinity`` picks their spelling: ``'Infinity'`` (the default) is what LabVIEW 2026 writes,
    ``'Inf'`` gives ``Inf`` / ``-Inf`` for consumers that expect it.

    ``number_style`` picks how finite floats are written. ``'shortest'`` (the default) uses the
    shortest text that round-trips the double. ``'labview'`` uses LabVIEW's own 20-significant-
    digit form, so a value read from Flatten To JSON output is re-emitted byte for byte. Both
    styles preserve every double exactly.
    """
    check_output(infinity, number_style)
    text = _encode(obj, nan_inf, indent, sort_keys, number_style)
    return shorten_infinity(text) if infinity == "Inf" else text


def to_portable(
    text: str | bytes,
    *,
    nan_inf: NanInf = "null",
    indent: int | None = None,
    sort_keys: bool = False,
) -> str:
    """Convert LabVIEW JSON text to standard JSON that ordinary parsers accept.

    Non-finite floats follow ``nan_inf``: the default ``'null'`` yields strict RFC 8259 JSON,
    ``'extend'`` keeps them as the ``json`` module's ``NaN`` / ``Infinity`` / ``-Infinity``
    tokens, and ``'reject'`` raises :class:`LVJSONError`. Either input spelling is accepted.
    """
    check(nan_inf)
    return _encode(loads(text, nan_inf="extend"), nan_inf, indent, sort_keys)


def to_labview(
    text: str | bytes,
    *,
    nan_inf: NanInf = "extend",
    indent: int | None = None,
    sort_keys: bool = False,
    infinity: InfSpelling = "Infinity",
    number_style: NumberStyle = "shortest",
) -> str:
    """Convert standard (or LabVIEW) JSON text to the form the LabVIEW JSON node ingests.

    This is the reverse of :func:`to_portable`. Non-finite floats follow ``nan_inf`` and are
    spelled per ``infinity``; finite floats follow ``number_style`` (see :func:`dumps`).
    """
    check(nan_inf)
    check_output(infinity, number_style)
    return dumps(
        loads(text, nan_inf="extend"),
        nan_inf=nan_inf,
        indent=indent,
        sort_keys=sort_keys,
        infinity=infinity,
        number_style=number_style,
    )


def round_trip(
    text: str | bytes,
    *,
    nan_inf: NanInf = "extend",
    indent: int | None = None,
    sort_keys: bool = False,
    infinity: InfSpelling = "Infinity",
    number_style: NumberStyle = "shortest",
) -> str:
    """Parse LabVIEW JSON and re-emit it in canonical, LabVIEW-ingestable form.

    Finite numbers are preserved exactly: they decode to IEEE 754 doubles and re-encode in the
    chosen ``number_style``. With the default ``'shortest'`` this turns LabVIEW's 20-digit
    ``0.10000000000000000555`` into ``0.1`` without changing the value. Non-finite floats
    follow ``nan_inf`` and ``infinity``.
    """
    return to_labview(
        text,
        nan_inf=nan_inf,
        indent=indent,
        sort_keys=sort_keys,
        infinity=infinity,
        number_style=number_style,
    )
