"""The error type lvjson raises for data it cannot read or write."""

from __future__ import annotations


class LVJSONError(ValueError):
    """Raised when LabVIEW JSON cannot be parsed or serialised under the chosen policy.

    It covers text that is not valid JSON or not valid UTF-8, non-finite values under
    ``nan_inf="reject"``, and values that cannot be encoded (circular, nested too deeply,
    integers too long to print). It subclasses :class:`ValueError` so existing ``json`` error
    handling keeps working. Invalid option values raise a plain :class:`ValueError` and wrong
    argument types a :class:`TypeError`. Messages never quote more than a few characters of
    the input.

    >>> from lvjson import loads
    >>> try:
    ...     loads("[NaN]", nan_inf="reject")
    ... except LVJSONError as error:
    ...     print(error)
    non-finite token NaN is not allowed under nan_inf='reject'
    """
