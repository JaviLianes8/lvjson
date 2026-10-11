"""Read and write LabVIEW "Flatten To JSON" text from Python, with an explicit strict boundary.

LabVIEW 2026's Flatten To JSON writes non-finite doubles as the bare tokens ``NaN``,
``Infinity`` and ``-Infinity`` (verified against captured output), doubles with 20 significant
digits, and negative zero as ``-0``. This package reads that text (and the ``Inf`` / ``-Inf``
spelling other producers use), preserves negative zero, writes JSON in either the shortest
form or LabVIEW's exact number formatting, converts to strict portable JSON for consumers that
reject the extension tokens, and reports which non-finite tokens a document holds.
"""

from __future__ import annotations

from ._errors import LVJSONError
from ._parse import has_nonfinite, loads
from ._policy import InfSpelling, NanInf, NumberStyle
from ._serialize import dumps, round_trip, to_labview, to_portable
from ._tokens import count_nonfinite

__version__ = "0.3.0"

__all__ = [
    "InfSpelling",
    "LVJSONError",
    "NanInf",
    "NumberStyle",
    "count_nonfinite",
    "dumps",
    "has_nonfinite",
    "loads",
    "round_trip",
    "to_labview",
    "to_portable",
]
