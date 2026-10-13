"""Read LabVIEW "Flatten To JSON" text into Python objects."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any

from ._errors import LVJSONError
from ._policy import NanInf, check
from ._text import decode_text
from ._tokens import expand_inf


def _reject_constant(token: str) -> float:
    raise LVJSONError(f"non-finite token {token} is not allowed under nan_inf='reject'")


def _null_constant(token: str) -> None:
    return None


def _reject_overflow(token: str) -> float:
    value = float(token)
    if math.isinf(value):
        raise LVJSONError("a number overflows a double, which nan_inf='reject' refuses")
    return value


def _null_overflow(token: str) -> float | None:
    value = float(token)
    return None if math.isinf(value) else value


def _parse_int(token: str) -> int | float:
    # LabVIEW writes a DBL negative zero as the bare "-0". No integer is negative zero, so the
    # token can only come from a double: keep its sign instead of collapsing it to int 0.
    if token == "-0":
        return -0.0
    return int(token)


_HOOKS: dict[str, tuple[Callable[[str], Any], Callable[[str], Any]]] = {
    "reject": (_reject_constant, _reject_overflow),
    "null": (_null_constant, _null_overflow),
}


def loads(text: str | bytes | bytearray, *, nan_inf: NanInf = "extend") -> Any:
    """Parse LabVIEW JSON, accepting every non-finite spelling it may carry.

    LabVIEW 2026 writes ``NaN``, ``Infinity`` and ``-Infinity``; other producers write ``Inf``
    and ``-Inf``. Both spellings are accepted, never inside strings. ``nan_inf`` decides what a
    non-finite value becomes: ``'extend'`` decodes to ``float('nan')`` and the infinities,
    ``'null'`` decodes each to ``None``, and ``'reject'`` raises :class:`LVJSONError`. A
    number too large for a double (``1e400``) counts as non-finite under every policy.

    The bare token ``-0``, which LabVIEW writes for a negative-zero double, decodes to ``-0.0``
    rather than the integer ``0``. ``bytes`` and ``bytearray`` input is decoded as UTF-8, the
    encoding LabVIEW writes, and a leading byte order mark is ignored. Malformed JSON raises
    :class:`LVJSONError`; an argument that is not text raises :class:`TypeError`.

    >>> loads('{"Data":[NaN,Infinity,-Inf,0.10000000000000000555,-0]}')
    {'Data': [nan, inf, -inf, 0.1, -0.0]}
    >>> loads('[NaN, 1e400, 2]', nan_inf="null")
    [None, None, 2]
    """
    nan_inf = check(nan_inf)
    text = decode_text(text)
    parse_constant, parse_float = _HOOKS.get(nan_inf, (None, None))
    parse_int = _parse_int if "-0" in text else None
    try:
        return json.loads(
            expand_inf(text),
            parse_constant=parse_constant,
            parse_float=parse_float,
            parse_int=parse_int,
        )
    except LVJSONError:
        raise
    except ValueError as exc:
        raise LVJSONError(str(exc)[:200]) from None
    except RecursionError:
        raise LVJSONError("JSON nesting is too deep to parse") from None


def has_nonfinite(obj: Any) -> bool:
    """Return whether ``obj`` holds a NaN or infinite float in a value, at any depth.

    Lists, tuples and dict values are searched (dict keys are not: ``json`` writes a float key
    as a string). Deep and circular structures are walked without recursion. Useful before
    handing a structure to a strict consumer: ``True`` means a plain ``json.dumps`` would write
    non-portable tokens or, with ``allow_nan=False``, fail.

    >>> has_nonfinite({"a": [1.0, {"b": float("nan")}]})
    True
    >>> has_nonfinite({"a": [1.0, "inf", None]})
    False
    """
    pending: list[Any] = [obj]
    seen: set[int] = set()
    while pending:
        item = pending.pop()
        if isinstance(item, float):
            if not math.isfinite(item):
                return True
        elif isinstance(item, (dict, list, tuple)):
            if id(item) in seen:
                continue
            seen.add(id(item))
            pending.extend(item.values() if isinstance(item, dict) else item)
    return False
