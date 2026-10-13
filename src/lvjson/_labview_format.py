"""Encode Python objects exactly the way LabVIEW's Flatten To JSON formats them.

Captured LabVIEW 2026 output shows DBL values written with 20 significant digits and trailing
zeros dropped, in C's ``%.20g`` layout (see :mod:`lvjson._digits`, which also covers exact
ties): ``0.1`` becomes ``0.10000000000000000555``, ``1e-05`` becomes
``1.0000000000000000818e-05``, ``1e20`` becomes ``1e+20``, ``1.0``
becomes ``1``, ``-0.0`` becomes ``-0`` and ``1e300`` becomes ``1.0000000000000000525e+300``.
The standard ``json`` encoder hard-wires ``float.__repr__``, so this module walks the value
itself. Strings and layout match ``json.dumps`` with ``ensure_ascii=False``, which agrees
with the captured string escapes (``\\t``, ``\\n``, ``\\r``, ``\\u0001``, raw UTF-8, ``/`` kept).
"""

from __future__ import annotations

import json
import math
from typing import Any

from ._digits import format_g20
from ._errors import LVJSONError
from ._text import type_name

# Messages that never quote the value: a float subclass may have a huge or failing __repr__.
NONFINITE_KEY = "a non-finite float dict key is only allowed under nan_inf='extend'"
NONFINITE_VALUE = "a non-finite float is only allowed under nan_inf='extend'"


def format_double(value: float, infinity: str) -> str:
    """Format one double as LabVIEW writes it; ``infinity`` is the positive-infinity token."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return infinity if value > 0 else "-" + infinity
    return format_g20(value)


def _key(key: object, allow_nan: bool) -> str:
    # The key coercions json.dumps applies; a float key is written in the labview number style.
    if isinstance(key, str):
        return key
    if key is True:
        return "true"
    if key is False:
        return "false"
    if key is None:
        return "null"
    if isinstance(key, float):
        if not math.isfinite(key) and not allow_nan:
            raise LVJSONError(NONFINITE_KEY)
        # A non-finite key becomes a string, so it takes json's spelling in both styles.
        return format_double(key, "Infinity")
    if isinstance(key, int):
        return int.__repr__(key)
    raise TypeError(f"keys must be str, int, float, bool or None, not {type_name(key)}")


class _Encoder:
    def __init__(self, infinity: str, allow_nan: bool, indent: int | None, sort_keys: bool) -> None:
        self.infinity = infinity
        self.allow_nan = allow_nan
        self.indent = indent
        self.sort_keys = sort_keys
        self.key_sep = ":" if indent is None else ": "
        self.active: set[int] = set()

    def encode(self, obj: Any, level: int) -> str:
        if obj is None:
            return "null"
        if obj is True:
            return "true"
        if obj is False:
            return "false"
        if isinstance(obj, str):
            return json.dumps(obj, ensure_ascii=False)
        if isinstance(obj, int):
            return int.__repr__(obj)
        if isinstance(obj, float):
            # Checked here too, so a container that changes between the policy scan and the
            # encoding cannot slip a non-finite value past nan_inf="null" or "reject".
            if not self.allow_nan and not math.isfinite(obj):
                raise LVJSONError(NONFINITE_VALUE)
            return format_double(obj, self.infinity)
        if isinstance(obj, (list, tuple)):
            return self._container(obj, level, "[", "]", self._items)
        if isinstance(obj, dict):
            return self._container(obj, level, "{", "}", self._members)
        raise TypeError(f"Object of type {type_name(obj)} is not JSON serializable")

    def _items(self, obj: Any, level: int) -> list[str]:
        return [self.encode(item, level) for item in obj]

    def _members(self, obj: Any, level: int) -> list[str]:
        items = obj.items()
        if self.sort_keys:
            # Sort on the original keys before coercion, exactly as json.dumps does.
            items = sorted(items, key=lambda pair: pair[0])
        pairs = [(_key(key, self.allow_nan), value) for key, value in items]
        return [
            json.dumps(key, ensure_ascii=False) + self.key_sep + self.encode(value, level)
            for key, value in pairs
        ]

    def _container(self, obj: Any, level: int, open_: str, close: str, parts: Any) -> str:
        marker = id(obj)
        if marker in self.active:
            raise ValueError("Circular reference detected")
        self.active.add(marker)
        try:
            chunks: list[str] = parts(obj, level + 1)
        finally:
            self.active.discard(marker)
        if not chunks:
            return open_ + close
        if self.indent is None:
            return open_ + ",".join(chunks) + close
        inner = "\n" + " " * (self.indent * (level + 1))
        outer = "\n" + " " * (self.indent * level)
        return open_ + inner + ("," + inner).join(chunks) + outer + close


def encode_labview(
    obj: Any, *, infinity: str, allow_nan: bool, indent: int | None, sort_keys: bool
) -> str:
    """Encode ``obj`` with LabVIEW's number formatting; non-finite floats use ``infinity``.

    The caller applies the non-finite policy to values first; ``allow_nan`` only decides
    whether a non-finite dict key is written (as a string) or refused.
    """
    return _Encoder(infinity, allow_nan, indent, sort_keys).encode(obj, 0)
