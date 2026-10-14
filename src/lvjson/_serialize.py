"""Emit JSON for LabVIEW or for strict consumers, without silent precision loss."""

from __future__ import annotations

import json
import re
from typing import Any

from ._errors import LVJSONError
from ._labview_format import NONFINITE_KEY, encode_labview
from ._parse import has_nonfinite, loads
from ._policy import InfSpelling, NanInf, NumberStyle, check, check_indent, check_output
from ._text import shorten
from ._tokens import shorten_infinity
from ._walk import nonfinite_key, to_null

# Compact separators match LabVIEW's own flattened output and keep the payload small.
_COMPACT = (",", ":")
# A lone surrogate cannot be encoded as UTF-8, so it is written as its escape, as json does
# with ensure_ascii; everything else stays as text.
_SURROGATE = re.compile("[" + chr(0xD800) + "-" + chr(0xDFFF) + "]")


def _escape_surrogates(text: str) -> str:
    return _SURROGATE.sub(lambda match: f"\\u{ord(match.group(0)):04x}", text)


def _encode(
    obj: Any,
    nan_inf: NanInf,
    indent: int | None,
    sort_keys: bool,
    number_style: NumberStyle,
    infinity: InfSpelling,
) -> str:
    """Encode to JSON text, applying the non-finite policy and the output spelling."""
    allow_nan = nan_inf == "extend"
    try:
        if nan_inf == "reject" and has_nonfinite(obj):
            raise LVJSONError("non-finite float is not allowed under nan_inf='reject'")
        if not allow_nan and nonfinite_key(obj):
            raise LVJSONError(NONFINITE_KEY)
        payload = to_null(obj) if nan_inf == "null" else obj
        if number_style == "labview":
            text = encode_labview(
                payload, infinity=infinity, allow_nan=allow_nan, indent=indent, sort_keys=sort_keys
            )
            return _escape_surrogates(text)
        text = json.dumps(
            payload,
            allow_nan=allow_nan,
            indent=indent,
            separators=None if indent is not None else _COMPACT,
            sort_keys=sort_keys,
            ensure_ascii=False,
        )
    except LVJSONError:
        raise
    except ValueError as exc:
        raise LVJSONError(shorten(str(exc))) from None
    except TypeError as exc:
        raise TypeError(shorten(str(exc))) from None
    except RecursionError:
        raise LVJSONError("value is circular or nested too deeply to encode") from None
    text = _escape_surrogates(text)
    return shorten_infinity(text) if infinity == "Inf" else text


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
    styles preserve every double exactly. A float dict key follows the same style; a
    non-finite float key is written as a string under ``'extend'`` and refused otherwise.

    Output is compact unless ``indent`` (an ``int`` from 0 to 1024) is given. Values that are not
    JSON types raise :class:`TypeError`; circular values raise :class:`LVJSONError`.

    >>> dumps({"x": [0.1, float("nan"), float("inf")]})
    '{"x":[0.1,NaN,Infinity]}'
    >>> dumps([0.1, 1.0, -0.0], number_style="labview")
    '[0.10000000000000000555,1,-0]'
    >>> dumps([float("-inf")], infinity="Inf"), dumps([float("nan")], nan_inf="null")
    ('[-Inf]', '[null]')
    """
    nan_inf = check(nan_inf)
    infinity, number_style = check_output(infinity, number_style)
    indent = check_indent(indent)
    return _encode(obj, nan_inf, indent, sort_keys, number_style, infinity)


def to_portable(
    text: str | bytes | bytearray,
    *,
    nan_inf: NanInf = "null",
    indent: int | None = None,
    sort_keys: bool = False,
) -> str:
    """Convert LabVIEW JSON text to standard JSON that ordinary parsers accept.

    Non-finite values follow ``nan_inf``: the default ``'null'`` yields strict RFC 8259 JSON,
    ``'extend'`` keeps them as the ``json`` module's ``NaN`` / ``Infinity`` / ``-Infinity``
    tokens, and ``'reject'`` raises :class:`LVJSONError`. Either input spelling is accepted,
    and numbers are written in the shortest form that keeps every double exact.

    >>> to_portable('{"gain":2.5,"reading":NaN,"limit":-Inf,"x":0.10000000000000000555}')
    '{"gain":2.5,"reading":null,"limit":null,"x":0.1}'
    """
    nan_inf = check(nan_inf)
    indent = check_indent(indent)
    return _encode(loads(text), nan_inf, indent, sort_keys, "shortest", "Infinity")


def to_labview(
    text: str | bytes | bytearray,
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

    >>> to_labview('{"x": 0.1, "limit": -Infinity}', number_style="labview")
    '{"x":0.10000000000000000555,"limit":-Infinity}'
    """
    nan_inf = check(nan_inf)
    infinity, number_style = check_output(infinity, number_style)
    indent = check_indent(indent)
    return _encode(loads(text), nan_inf, indent, sort_keys, number_style, infinity)


def round_trip(
    text: str | bytes | bytearray,
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
    follow ``nan_inf`` and ``infinity``. It is the same operation as :func:`to_labview`, named
    for the canonicalising use.

    >>> round_trip('{"v": 3.141592653589793116, "w": Inf}')
    '{"v":3.141592653589793,"w":Infinity}'
    """
    return to_labview(
        text,
        nan_inf=nan_inf,
        indent=indent,
        sort_keys=sort_keys,
        infinity=infinity,
        number_style=number_style,
    )
