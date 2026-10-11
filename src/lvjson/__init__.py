"""Byte-level compatibility with LabVIEW "Flatten To JSON" output for Python and back.

LabVIEW's node writes JSON that trips up strict tooling: its non-finite values use the bare
tokens ``NaN``, ``Inf`` and ``-Inf``, where the standard ``json`` module reads and writes
``Infinity`` / ``-Infinity`` instead, so ``Inf`` and ``-Inf`` cannot be parsed by ``json`` at
all. This package translates those tokens both ways, writes JSON the LabVIEW node ingests
cleanly, converts to portable JSON for strict consumers, and canonicalises LabVIEW's adaptive
digit formatting without changing any value.
"""

from __future__ import annotations

from ._errors import LVJSONError
from ._parse import has_nonfinite, loads
from ._policy import NanInf
from ._serialize import dumps, round_trip, to_labview, to_portable

__version__ = "0.2.0"

__all__ = [
    "LVJSONError",
    "NanInf",
    "dumps",
    "has_nonfinite",
    "loads",
    "round_trip",
    "to_labview",
    "to_portable",
]
