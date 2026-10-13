"""Read and write LabVIEW "Flatten To JSON" text from Python, with an explicit strict boundary.

LabVIEW 2026's Flatten To JSON writes non-finite doubles as the bare tokens ``NaN``,
``Infinity`` and ``-Infinity``, doubles with 20 significant digits, and negative zero as ``-0``
(all verified against captured output). This package reads that text (and the ``Inf`` / ``-Inf``
spelling other producers use), keeps negative zero, writes JSON in either the shortest form or
LabVIEW's exact 20-digit form, converts to strict portable JSON for consumers that reject the
extension tokens, and reports which non-finite tokens a document holds.

The three option types are plain string literals:

>>> from lvjson import InfSpelling, NanInf, NumberStyle, dumps
>>> policy: NanInf = "null"
>>> spelling: InfSpelling = "Inf"
>>> style: NumberStyle = "labview"
>>> dumps([float("nan"), float("inf"), 0.5], nan_inf=policy, infinity=spelling, number_style=style)
'[null,null,0.5]'
>>> dumps([float("-inf"), 0.1], infinity=spelling, number_style=style)
'[-Inf,0.10000000000000000555]'
"""

from __future__ import annotations

from ._errors import LVJSONError
from ._parse import has_nonfinite, loads
from ._policy import InfSpelling, NanInf, NumberStyle
from ._serialize import dumps, round_trip, to_labview, to_portable
from ._tokens import count_nonfinite

__version__ = "1.0.0"

# Tracebacks and pickles name the error where users import it from.
LVJSONError.__module__ = "lvjson"

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
