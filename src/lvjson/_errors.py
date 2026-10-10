"""The single error type the public API raises."""

from __future__ import annotations


class LVJSONError(ValueError):
    """Raised when LabVIEW JSON cannot be parsed or serialised under the chosen policy.

    It subclasses :class:`ValueError` so existing ``json`` error handling keeps working,
    while giving callers one lvjson-specific type to catch.
    """
