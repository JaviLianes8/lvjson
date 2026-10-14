"""LabVIEW's 20-significant-digit form of a finite double.

Flatten To JSON writes a DBL like C's ``%.20g``: 20 significant digits, trailing zeros and a
bare decimal point dropped, exponent form below 1e-4 and from 1e20 up, with a signed exponent of
at least two digits. Where the exact value lies exactly halfway between two 20-digit results,
LabVIEW 2026 rounds away from zero (``2**-30`` is written ``9.3132257461547851563e-10``), while
Python's ``'.20g'`` rounds to even (``...562e-10``). Such ties are rare: the exact decimal value
must have 21 significant digits ending in 5. They are detected and rounded exactly.

>>> format_g20(0.1), format_g20(1e20), format_g20(-0.0), format_g20(2.0**-30)
('0.10000000000000000555', '1e+20', '-0', '9.3132257461547851563e-10')
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Context, Decimal

_DIGITS = 20
# A private context, so the caller's decimal settings never change a result.
_CONTEXT = Context(
    prec=_DIGITS,
    rounding=ROUND_HALF_UP,
    Emin=-999999,
    Emax=999999,
    capitals=1,
    clamp=0,
    flags=[],
    traps=[],
)


def format_g20(value: float) -> str:
    """Return ``value`` (finite) in Flatten To JSON's 20-digit form."""
    # The plain float behind a subclass, so overridden methods cannot change the digits.
    value = float.__float__(value)
    text = float.__format__(value, ".20g")
    # 25 correctly rounded digits end in "50000" whenever the 21st exact digit is a 5 followed by
    # nothing else, the only case where rounding half up and half to even disagree.
    probe = float.__format__(value, ".24e").partition("e")[0].replace(".", "").lstrip("-")
    if probe[_DIGITS:] != "50000":
        return text
    return _exact(value)


def _exact(value: float) -> str:
    rounded = _CONTEXT.plus(Decimal(value))
    sign, digits, _ = rounded.as_tuple()
    coefficient = "".join(map(str, digits)).ljust(_DIGITS, "0")
    exponent = rounded.adjusted()
    if -4 <= exponent < _DIGITS:
        if exponent >= 0:
            whole, fraction = coefficient[: exponent + 1], coefficient[exponent + 1 :]
        else:
            whole, fraction = "0", "0" * (-exponent - 1) + coefficient
        fraction = fraction.rstrip("0")
        body = whole + ("." + fraction if fraction else "")
    else:
        fraction = coefficient[1:].rstrip("0")
        mark = "+" if exponent >= 0 else "-"
        body = coefficient[0] + ("." + fraction if fraction else "") + f"e{mark}{abs(exponent):02d}"
    return ("-" if sign else "") + body
