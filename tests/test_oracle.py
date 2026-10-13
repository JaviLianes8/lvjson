"""Independent oracles for the number forms, on seeded corpora.

The 20-digit LabVIEW form is checked against exact ``Fraction`` arithmetic written here (round
half away from zero, the rounding LabVIEW 2026 was captured using on exact ties, then C's
``%g`` layout) and, on Windows, against the C runtime's own ``printf("%.20g")`` in
``ucrtbase.dll``. The shortest form and the reader are checked against the ``json`` module.
"""

from __future__ import annotations

import ctypes
import json
import math
import random
import struct
import sys
from decimal import Decimal
from fractions import Fraction

import pytest

from lvjson import NumberStyle, dumps, loads, to_portable

_RNG = random.Random(20261013)


def _random_doubles(count: int) -> list[float]:
    found: list[float] = []
    while len(found) < count:
        value = struct.unpack("<d", _RNG.getrandbits(64).to_bytes(8, "little"))[0]
        if math.isfinite(value):
            found.append(value)
    return found


def _ties() -> list[float]:
    # Doubles whose exact decimal value has 21 significant digits ending in 5.
    found: list[float] = []
    for odd in range(1, 400, 2):
        for shift in range(1, 1075):
            value = math.ldexp(odd, -shift)
            digits = Decimal(value).as_tuple().digits
            if value and len(digits) == 21 and digits[-1] == 5:
                found.extend((value, -value))
    return found


def _boundaries() -> list[float]:
    values = [5e-324, 2.2250738585072014e-308, 1.7976931348623157e308, 2.0**53, 2.0**53 + 2]
    for power in range(-6, 23):
        ten = 10.0**power
        values += [ten, math.nextafter(ten, 0.0), math.nextafter(ten, math.inf)]
    return values + [-value for value in values]


_TIES = _ties()
_CORPUS = _random_doubles(4000) + _boundaries() + _TIES + [0.0, -0.0]


def _oracle_g20(value: float) -> str:
    if value == 0:
        return "-0" if math.copysign(1.0, value) < 0 else "0"
    exact = abs(Fraction(value))
    exponent = math.floor(math.log10(abs(value)))
    while Fraction(10) ** exponent > exact:
        exponent -= 1
    while Fraction(10) ** (exponent + 1) <= exact:
        exponent += 1
    scaled = exact / Fraction(10) ** (exponent - 19)
    number = math.floor(scaled)
    if scaled - number >= Fraction(1, 2):
        number += 1
    if number == 10**20:
        number, exponent = 10**19, exponent + 1
    digits = str(number)
    if -4 <= exponent < 20:
        if exponent >= 0:
            text = digits[: exponent + 1] + "." + digits[exponent + 1 :]
        else:
            text = "0." + "0" * (-exponent - 1) + digits
        text = text.rstrip("0").rstrip(".")
    else:
        mantissa = (digits[0] + "." + digits[1:]).rstrip("0").rstrip(".")
        text = f"{mantissa}e{'-' if exponent < 0 else '+'}{abs(exponent):02d}"
    return ("-" if value < 0 else "") + text


def test_the_corpus_holds_exact_ties_on_both_sides_of_even() -> None:
    assert len(_TIES) >= 40
    assert dumps(2.0**-30, number_style="labview") == "9.3132257461547851563e-10"
    assert format(2.0**-30, ".20g") == "9.3132257461547851562e-10"


def test_labview_style_matches_exact_rational_arithmetic() -> None:
    for value in _CORPUS:
        assert dumps(value, number_style="labview") == _oracle_g20(value), repr(value)


@pytest.mark.skipif(sys.platform != "win32", reason="ucrtbase.dll is the Windows C runtime")
def test_labview_style_matches_the_windows_c_runtime_printf() -> None:
    common = ctypes.CDLL("ucrtbase").__stdio_common_vsprintf
    common.restype = ctypes.c_int
    common.argtypes = [ctypes.c_ulonglong, ctypes.c_char_p, ctypes.c_size_t]
    common.argtypes += [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p]
    buffer = ctypes.create_string_buffer(64)
    for value in _CORPUS:
        arguments = (ctypes.c_double * 1)(value)
        common(0, buffer, 64, b"%.20g", None, ctypes.cast(arguments, ctypes.c_void_p))
        assert dumps(value, number_style="labview") == buffer.value.decode(), repr(value)


def test_both_styles_read_back_to_the_same_double() -> None:
    styles: tuple[NumberStyle, ...] = ("shortest", "labview")
    for value in _CORPUS:
        for style in styles:
            back = loads(dumps(value, number_style=style))
            assert struct.pack("<d", back) == struct.pack("<d", value)


def test_shortest_style_is_what_the_json_module_writes() -> None:
    assert dumps(_CORPUS) == json.dumps(_CORPUS, separators=(",", ":"))
    # LabVIEW's form drops ".0" from whole doubles, so compare the doubles, not the text.
    portable = loads(to_portable(dumps(_CORPUS, number_style="labview")))
    assert [struct.pack("<d", value) for value in portable] == [
        struct.pack("<d", value) for value in _CORPUS
    ]


def test_the_reader_agrees_with_the_json_module_on_ordinary_json() -> None:
    rng = random.Random(7)
    for _ in range(300):
        document = {
            str(index): [rng.uniform(-1e6, 1e6), rng.randrange(1, 10**30), None, "a\\u00e9"]
            for index in range(rng.randrange(1, 6))
        }
        text = json.dumps(document)
        assert loads(text) == json.loads(text)
        assert loads(text.encode()) == json.loads(text)
