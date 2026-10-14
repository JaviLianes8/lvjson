"""Turn the accepted input forms into one ``str``, and keep messages about bad values short."""

from __future__ import annotations

import re

from ._errors import LVJSONError

# Messages quote at most this many characters of a value or a type name, so a huge or hostile
# argument can never make an error message huge, and stay shorter than _MESSAGE in total.
_LIMIT = 40
_MESSAGE = 200
_WORD = re.compile(r"\S{" + str(_LIMIT + 1) + ",}")


def shorten(message: str) -> str:
    """Cut every word of ``message`` to 40 characters and the whole to under 200.

    Used for messages that come from elsewhere (the ``json`` module, the operating system),
    which may quote a type name, a path or a value at full length.

    >>> shorten("Object of type " + "X" * 300 + " is not JSON serializable")
    'Object of type XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX... is not JSON serializable'
    """
    message = _WORD.sub(lambda match: match.group(0)[:_LIMIT] + "...", message)
    if len(message) >= _MESSAGE:
        message = message[: _MESSAGE - 4] + "..."
    return message


# Messages of the json module and of comparisons that quote type names, which may hold spaces.
_NAMED = (
    re.compile(r"(Object of type )(.+)( is not JSON serializable)", re.DOTALL),
    re.compile(r"(keys must be str, int, float, bool or None, not )(.+)()", re.DOTALL),
    re.compile(r"('\W+' not supported between instances of ')(.+?)(' and ')(.+)(')", re.DOTALL),
)


_QUOTED = re.compile(r"'([^']{" + str(_LIMIT + 1) + r",})('|\Z)")


def error_text(error: BaseException) -> str:
    """Return the message of ``error`` cut short, without calling an overridden ``__str__``.

    Type names that the message quotes are cut to 40 characters like any other word.
    """
    try:
        text = str.__str__(str(BaseException.__str__(error)))
    except Exception:
        return type_name(error)
    # Only the head can be shown; cutting it first keeps the pattern matching linear.
    text = text[: _MESSAGE * 4]
    for pattern in _NAMED:
        match = pattern.fullmatch(text)
        if match:
            parts = list(match.groups())
            for index in range(1, len(parts), 2):
                if len(parts[index]) > _LIMIT:
                    parts[index] = parts[index][:_LIMIT] + "..."
            text = "".join(parts)
            break
    # Any other quoted name (an unhashable key's type, for example) is cut the same way.
    text = _QUOTED.sub(lambda match: "'" + match.group(1)[:_LIMIT] + "..." + match.group(2), text)
    return shorten(text)


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
