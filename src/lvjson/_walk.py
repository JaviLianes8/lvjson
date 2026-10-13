"""Walks over values to encode: the null policy and the search for non-finite keys."""

from __future__ import annotations

import math
from typing import Any


def to_null(obj: Any) -> Any:
    """Return ``obj`` with every non-finite float value replaced by ``None``."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {key: to_null(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_null(item) for item in obj]
    return obj


def nonfinite_key(obj: Any) -> bool:
    """Return whether a dict at any depth of ``obj`` has a NaN or infinite float key."""
    # json would call repr() on such a key to build its message; find it first, without recursion.
    pending: list[Any] = [obj]
    seen: set[int] = set()
    while pending:
        item = pending.pop()
        if isinstance(item, (dict, list, tuple)) and id(item) not in seen:
            seen.add(id(item))
            if isinstance(item, dict):
                if any(isinstance(key, float) and not math.isfinite(key) for key in item):
                    return True
                pending.extend(item.values())
            else:
                pending.extend(item)
    return False
