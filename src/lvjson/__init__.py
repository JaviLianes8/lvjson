"""Normalise LabVIEW "Flatten To JSON" output for Python and back.

LabVIEW emits JSON that trips up strict tooling: doubles with adaptive 13 to 17 digit
formatting, and optional ``NaN`` / ``Infinity`` / ``-Infinity`` extension tokens that many
parsers reject. This package reads that text safely, writes JSON the LabVIEW JSON node
ingests cleanly, and round-trips numbers without silent precision loss.
"""

from __future__ import annotations

from ._errors import LVJSONError
from ._parse import has_nonfinite, loads
from ._policy import NanInf
from ._serialize import dumps, round_trip

__version__ = "0.1.0"

__all__ = [
    "LVJSONError",
    "NanInf",
    "dumps",
    "has_nonfinite",
    "loads",
    "round_trip",
]
