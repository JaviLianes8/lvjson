"""Read LabVIEW "Flatten To JSON" text into Python objects."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any

from ._errors import LVJSONError
from ._policy import NanInf, check
from ._tokens import expand_inf


def _reject_constant(token: str) -> float:
    raise LVJSONError(f"non-finite token {token!r} is not allowed under nan_inf='reject'")


def _null_constant(token: str) -> None:
    return None


def _parse_int(token: str) -> int | float:
    # LabVIEW writes a DBL negative zero as the bare "-0". No integer is negative zero, so the
    # token can only come from a double: keep its sign instead of collapsing it to int 0.
    if token == "-0":
        return -0.0
    return int(token)


def decode_text(text: str | bytes) -> str:
    """Return ``text`` as ``str``, decoding bytes as UTF-8 (LabVIEW's JSON encoding)."""
    if isinstance(text, str):
        return text
    if isinstance(text, (bytes, bytearray)):
        try:
            return bytes(text).decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise LVJSONError(f"input is not valid UTF-8: {exc}") from exc
    raise TypeError(f"expected str or bytes, got {type(text).__name__}")


def loads(text: str | bytes, *, nan_inf: NanInf = "extend") -> Any:
    """Parse LabVIEW JSON, accepting every non-finite spelling it may carry.

    LabVIEW 2026 writes ``NaN``, ``Infinity`` and ``-Infinity``; other producers write ``Inf``
    and ``-Inf``. Both spellings are accepted, never inside strings. ``nan_inf`` decides what a
    non-finite token becomes: ``'extend'`` decodes to ``float('nan')`` and the infinities,
    ``'null'`` decodes each to ``None``, and ``'reject'`` raises :class:`LVJSONError`.

    The bare token ``-0``, which LabVIEW writes for a negative-zero double, decodes to ``-0.0``
    rather than the integer ``0``. ``bytes`` input is decoded as UTF-8, the encoding LabVIEW
    writes, with a leading byte order mark tolerated. Malformed JSON always raises
    :class:`LVJSONError`.
    """
    check(nan_inf)
    text = decode_text(text)
    parse_constant: Callable[[str], Any] | None = None
    if nan_inf == "reject":
        parse_constant = _reject_constant
    elif nan_inf == "null":
        parse_constant = _null_constant
    parse_int = _parse_int if "-0" in text else None
    try:
        return json.loads(expand_inf(text), parse_constant=parse_constant, parse_int=parse_int)
    except LVJSONError:
        raise
    except ValueError as exc:
        raise LVJSONError(str(exc)) from exc
    except RecursionError as exc:
        raise LVJSONError("JSON nesting is too deep to parse") from exc


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
