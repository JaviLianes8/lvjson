"""Swap the non-finite value tokens between LabVIEW and standard JSON spellings.

LabVIEW's Flatten To JSON writes ``Inf`` and ``-Inf`` where the standard library ``json``
module writes ``Infinity`` and ``-Infinity``. ``NaN`` is spelled the same by both. Only the
bare value tokens differ, so the translation is a spelling swap applied to the text that lies
outside string literals. Working on the text, rather than re-encoding, keeps everything else
(key order, spacing, number digits) byte for byte intact.
"""

from __future__ import annotations


def _is_word_char(text: str, index: int) -> bool:
    return index < len(text) and (text[index].isalnum() or text[index] == "_")


def _translate(text: str, source: str, target: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if text.startswith(source, i) and not _is_word_char(text, i + len(source)):
            out.append(target)
            i += len(source)
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def labview_to_json(text: str) -> str:
    """Rewrite LabVIEW's ``Inf`` / ``-Inf`` tokens to the ``json`` module's spelling.

    ``-Inf`` is handled by the ``-`` passing through untouched and ``Inf`` becoming
    ``Infinity``. ``Infinity`` already present in the input is left alone, so standard JSON is
    accepted as well.
    """
    return _translate(text, "Inf", "Infinity")


def json_to_labview(text: str) -> str:
    """Rewrite the ``json`` module's ``Infinity`` / ``-Infinity`` tokens to LabVIEW's spelling."""
    return _translate(text, "Infinity", "Inf")
