"""Turn the accepted input forms into one ``str``, and keep messages about bad values short."""

from __future__ import annotations

from ._errors import LVJSONError

# Messages quote at most this many characters of a value or a type name, so a huge or hostile
# argument can never make an error message huge.
_LIMIT = 40


def type_name(obj: object) -> str:
    """Return the name of ``obj``'s type, cut to a short length.

    The name is read through ``type`` itself, so a metaclass cannot substitute another value.
    """
    name: str = type.__dict__["__name__"].__get__(type(obj), type)
    return name if len(name) <= _LIMIT else name[:_LIMIT] + "..."


def describe(value: object) -> str:
    """Return a short description of ``value`` for an error message.

    Text is quoted (cut after 40 characters); anything else is named by its type, so a lying
    or expensive ``__repr__`` is never called.
    """
    if isinstance(value, str):
        text = str.__repr__(str.__str__(value))
        return text if len(text) <= _LIMIT else text[:_LIMIT] + "..."
    if value is None or value is True or value is False:
        return repr(value)
    return f"a value of type {type_name(value)}"


def decode_text(text: str | bytes | bytearray) -> str:
    """Return ``text`` as ``str``, decoding ``bytes`` and ``bytearray`` as UTF-8.

    UTF-8 is the encoding Flatten To JSON writes. A leading byte order mark is dropped from
    every form. Subclasses are read for their contents, never through overridden methods.

    >>> decode_text(b'\\xef\\xbb\\xbf[1]')
    '[1]'
    """
    if isinstance(text, str):
        value = str.__str__(text)
        return value[1:] if value.startswith("\ufeff") else value
    if isinstance(text, (bytes, bytearray)):
        try:
            if isinstance(text, bytes):
                return bytes.decode(text, "utf-8-sig")
            return bytearray.decode(text, "utf-8-sig")
        except UnicodeDecodeError as exc:
            reason = f"byte 0x{exc.object[exc.start]:02x} at offset {exc.start}"
            raise LVJSONError(f"input is not valid UTF-8 ({reason})") from None
    raise TypeError(f"expected str, bytes or bytearray, got {type_name(text)}")
