# lvjson guide

`lvjson` sits between Python and LabVIEW's JSON functions. It reads what Flatten To JSON writes,
writes what Unflatten From JSON reads, and gives strict JSON consumers text they accept. This
guide covers every public name, the options, the number forms, errors, the command line, what
the evidence shows, and the changes from 0.3.0.

Contents: [Reading](#reading) · [Writing](#writing) · [Converting text](#converting-text) ·
[Inspecting](#inspecting) · [Options](#options) · [Number forms](#number-forms) ·
[Errors](#errors) · [Command line](#command-line) · [Evidence](#evidence) ·
[Upgrading from 0.3.0](#upgrading-from-030)

## Reading

`loads(text, *, nan_inf="extend")` parses JSON text into Python objects, like `json.loads`,
with these differences:

- `NaN`, `Infinity` and `-Infinity` (what LabVIEW 2026 writes) and `Inf` / `-Inf` (what some
  other producers write) are read as non-finite floats. Words inside strings are never touched.
- The bare token `-0`, which Flatten To JSON writes for a negative-zero double, becomes `-0.0`
  instead of the integer `0`. No integer is negative zero, so the token can only come from a
  double.
- `text` may be `str`, or `bytes` / `bytearray` decoded as UTF-8 (the encoding Flatten To JSON
  writes). A leading byte order mark is ignored in every form.

```pycon
>>> from lvjson import loads
>>> loads(b'{"Data":[NaN,-Inf,0.10000000000000000555,-0,65536]}')
{'Data': [nan, -inf, 0.1, -0.0, 65536]}
>>> loads('["Infinity", Infinity]')
['Infinity', inf]

```

Whole numbers come back as `int`, because Flatten To JSON writes a whole double without a
decimal point (`65536`, `-1`): the JSON text does not say whether the LabVIEW value was a
DBL or an integer. Duplicate keys keep the last value, as in `json.loads`. The return type is
`Any`, as for `json.loads`: the shape depends on the text.

## Writing

`dumps(obj, *, nan_inf="extend", indent=None, sort_keys=False, infinity="Infinity",
number_style="shortest")` serialises `dict`, `list`, `tuple`, `str`, `int`, `float`, `bool`
and `None` (and their subclasses, by value). Output is compact (`","` and `":"`, as Flatten To
JSON writes) unless `indent` is an `int` from 0 to 1024 (not a `bool`). Indented output grows with
indent times nesting depth on every line, as with `json.dumps`: a 2 KB document nested 1,000 deep
becomes about a gigabyte at `indent=1024`. Non-ASCII text is written as is, not as
`\u` escapes; control characters, quotes and backslashes are escaped as `json.dumps` does.
A lone surrogate code point (from an unpaired `\ud800` escape) is written back as its
escape, so the output can always be encoded as UTF-8. A high and a low surrogate that sit next to
each other in a `str` are written as two escapes and read back as one character, as with
`json.dumps`: JSON text cannot keep them apart.

```pycon
>>> from lvjson import dumps
>>> dumps({"gain": 2.5, "limits": [float("-inf"), float("inf")], "name": "é"})
'{"gain":2.5,"limits":[-Infinity,Infinity],"name":"é"}'
>>> dumps({"b": 1.0, "a": 0.1}, number_style="labview", sort_keys=True)
'{"a":0.10000000000000000555,"b":1}'
>>> print(dumps({"a": [1, None]}, indent=2))
{
  "a": [
    1,
    null
  ]
}

```

Dict keys follow `json.dumps`: `str` stays, `int`, `float`, `bool` and `None` become strings,
anything else is a `TypeError`. A float key is written in the chosen number style. A
non-finite float key becomes the string `"NaN"`, `"Infinity"` or `"-Infinity"` under
`nan_inf="extend"` and is refused under `"null"` and `"reject"`.

## Converting text

| Function | Reads | Writes |
| --- | --- | --- |
| `to_portable(text, *, nan_inf="null", indent=None, sort_keys=False)` | any JSON text `loads` reads | the shortest number form, non-finite values per `nan_inf` (`null` by default: strict RFC 8259 JSON) |
| `to_labview(text, *, nan_inf="extend", indent=None, sort_keys=False, infinity="Infinity", number_style="shortest")` | any JSON text `loads` reads | the text `dumps` writes for the parsed value |
| `round_trip(...)` | same as `to_labview` | same as `to_labview`; the name for canonicalising LabVIEW's 20-digit numbers |

```pycon
>>> from lvjson import round_trip, to_labview, to_portable
>>> to_portable('{"reading": NaN, "x": 0.10000000000000000555}')
'{"reading":null,"x":0.1}'
>>> to_portable("[NaN, -Inf]", nan_inf="extend")
'[NaN,-Infinity]'
>>> to_labview('{"x": 0.1, "limit": -Infinity}', number_style="labview", infinity="Inf")
'{"x":0.10000000000000000555,"limit":-Inf}'
>>> round_trip('{"v": 3.141592653589793116}')
'{"v":3.141592653589793}'

```

Every conversion keeps every finite double exactly. Key order is kept unless `sort_keys` is
true. Spacing is not kept: output is compact or indented with `indent`.

## Inspecting

`count_nonfinite(text)` counts each non-finite spelling that appears as a bare word outside
string literals, without parsing, so it also works on malformed text. The result lists only
the spellings present, in the order `NaN`, `Infinity`, `-Infinity`, `Inf`, `-Inf`.

`has_nonfinite(obj)` says whether a parsed value holds a NaN or infinite float in a value at
any depth (dict keys are not searched). It walks deep and circular structures without
recursion.

```pycon
>>> from lvjson import count_nonfinite, has_nonfinite
>>> count_nonfinite('[-Inf, NaN, "NaN", Infinity, NaN]')
{'NaN': 2, 'Infinity': 1, '-Inf': 1}
>>> has_nonfinite({"a": [1.0, (2.0, float("nan"))]})
True

```

## Options

Every option is a plain string; the type aliases `NanInf`, `InfSpelling` and `NumberStyle` name
the accepted values for type checkers. A `str` subclass (such as a `StrEnum` member) is accepted
by its text.

| Option | Values | Meaning |
| --- | --- | --- |
| `nan_inf` | `"extend"` | non-finite values stay floats on reading and are written as tokens |
| | `"null"` | they become `None` on reading and `null` on writing |
| | `"reject"` | they raise `LVJSONError` |
| `infinity` | `"Infinity"` (default) | write `Infinity` / `-Infinity`, as LabVIEW 2026 does |
| | `"Inf"` | write `Inf` / `-Inf` |
| `number_style` | `"shortest"` (default) | the shortest text that reads back as the same double |
| | `"labview"` | Flatten To JSON's 20-significant-digit form |

A number too large for a double, such as `1e400`, reads as an infinity, so it counts as
non-finite: `inf` under `"extend"`, `None` under `"null"`, an error under `"reject"`.
`NaN` is always written as `NaN`.

```pycon
>>> loads("[1e400, 2]", nan_inf="null")
[None, 2]
>>> dumps([float("nan"), float("-inf")], infinity="Inf")
'[NaN,-Inf]'

```

## Number forms

`number_style="labview"` writes a finite double as Flatten To JSON does:

- 20 significant digits, correctly rounded from the exact binary value; when the exact value
  lies halfway between two 20-digit results, away from zero (LabVIEW 2026 writes `2**-30` as
  `9.3132257461547851563e-10`, where Python's `format(x, ".20g")` gives `...562e-10`);
- C's `%g` layout: fixed notation from `1e-4` up to below `1e20`, exponent notation outside
  that, trailing zeros and a bare decimal point dropped, exponent signed with at least two
  digits;
- negative zero as `-0`.

```pycon
>>> dumps([0.1, 1e-05, 1e20, 65536.0, -0.0, 2.0**-30], number_style="labview")
'[0.10000000000000000555,1.0000000000000000818e-05,1e+20,65536,-0,9.3132257461547851563e-10]'

```

Integers (`int`) are written in full in both styles. `number_style` describes DBL output; it
was not checked against SGL or EXT values.

## Errors

| Situation | Raised |
| --- | --- |
| `text` is not `str`, `bytes` or `bytearray` | `TypeError` |
| `bytes` that are not UTF-8 (the message names the offset) | `LVJSONError` |
| malformed JSON, nesting too deep to parse, an integer longer than Python's digit limit | `LVJSONError` |
| a non-finite value under `nan_inf="reject"`, or a non-finite float key under `"null"` or `"reject"` | `LVJSONError` |
| a circular value, a value nested too deeply to encode, an integer too long to write | `LVJSONError` |
| an object of a non-JSON type, a dict key of an unsupported type, `sort_keys` with keys that do not compare | `TypeError` |
| an exception raised by the value's own methods while encoding (a failing `__iter__`, `items()` or `__repr__`): a `ValueError` (an `LVJSONError` included) | `LVJSONError` |
| the same, a `TypeError` | `TypeError` |
| the same, any other exception; the original is chained | `TypeError` |
| an unknown option value | `ValueError` |
| `indent` that is not `None` or an `int` (a `bool` included); an `indent` below 0 or above 1024 | `TypeError`; `ValueError` |

`LVJSONError` subclasses `ValueError`, so code that catches `json`'s `ValueError` keeps
working. Messages quote at most 40 characters of a value, a type name or any other single word
(longer ones are cut and end in `...`; a quoted type name counts as one word even if it holds
spaces) and stay under 200 characters in total, whatever the input. An overridden `__str__` of an
exception is never called. `has_nonfinite` is a plain predicate: an exception raised by the
value's own methods (a failing `items()` or `__iter__`) passes through it unchanged. A value nested
too deeply to encode gives `LVJSONError`, and `MemoryError` always passes through unchanged.

## Command line

```
lvjson to-portable [FILE] [-o FILE] [--indent N] [--sort-keys] [--nan-inf {extend,null,reject}]
lvjson to-labview  [FILE] [-o FILE] [--indent N] [--sort-keys] [--nan-inf {extend,null,reject}]
                   [--infinity {Infinity,Inf}] [--number-style {shortest,labview}]
lvjson check       [FILE] [--strict]
```

`FILE` defaults to standard input (also `-`). Input is read as UTF-8 bytes (a byte order mark
is ignored); output is written as UTF-8 with a newline, or to `-o FILE` without one. `check`
reports the non-finite tokens and the numbers that overflow a double; `--strict` makes it exit
1 when there are any.

```
$ echo '[1.5, Infinity, -Inf]' | lvjson to-portable --nan-inf extend
[1.5,Infinity,-Infinity]
$ echo '{"b": 1.0, "a": NaN}' | lvjson to-labview --sort-keys --number-style labview
{"a":NaN,"b":1}
$ echo '{"note": "NaN", "x": 2}' | lvjson check --strict
<stdin>: valid, no non-finite tokens (strict JSON)
```

| Exit status | Meaning |
| --- | --- |
| 0 | success |
| 1 | bad input, a failed conversion, a `--strict` finding, or standard output closed early |
| 2 | bad usage: an unknown command or option, or a bad option value such as `--indent -1` |
| 130 | interrupted |

Error messages go to standard error, prefixed `lvjson:`, in one line of at most 200 characters.
Usage errors print argparse's usage line and then an error line of at most 200 characters.
`--indent` takes 0 to 1024.

## Evidence

**Captured from LabVIEW 2026.** `tests/fixtures/labview2026/` holds output of LabVIEW 2026
(26.3.1f1, 64-bit, Windows) running the shipped example `examples\Strings\Unflatten From
JSON.vi` unmodified, driven through LabVIEW's ActiveX server with chosen DBL values (the
manifest records inputs, method and hashes; `scripts/capture-labview-json.ps1` and
`scripts/capture-labview-readback.ps1` reproduce them). They show:

- Flatten To JSON writes `NaN`, `Infinity`, `-Infinity`, negative zero as `-0`, compact
  separators, UTF-8 text with `\t`, `\n`, `\r` and `\u0001` escapes and `/` unescaped, and
  token-like words inside strings as ordinary string content;
- its numbers match the 20-digit form above for every captured double, including the `%g`
  switch points and twelve exact ties, all rounded away from zero;
- Unflatten From JSON, with the example's settings, reads `NaN`, `Infinity`, `-Infinity`, the
  20-digit forms, the smallest subnormal and the largest double back to the exact bits that
  went in, and reads `-0` as positive zero.

`number_style="labview"` reproduces every captured string byte for byte, and `loads` decodes
each to exactly the doubles that went in (keeping the sign of `-0`).

**From NI's documentation** (fetched 2026-10-13): Flatten To JSON and Unflatten From JSON both
have an *enable LabVIEW extensions* input, true by default, that NI describes as supporting
NaN and Inf values; Unflatten From JSON's *default null elements* input is false by default,
and then LabVIEW returns an error for null values. So text written with `nan_inf="null"` is
refused by an Unflatten From JSON node left at its defaults; this was not exercised.

**From the runtime's strings only.** In `lvrt.dll` of the LabVIEW 2026 run-time, the JSON
lexer's keyword table lists `NaN`, `Infinity`, `true`, `false` and `null`, and no `Inf`. That
suggests LabVIEW's reader does not accept `Inf`, which is why `Infinity` is the default output
spelling. It was not exercised.

**Not verified.** Output with *enable LabVIEW extensions* set to false; numeric types other
than DBL; LabVIEW versions other than 2026; whether any LabVIEW reader accepts `Inf`.

## Upgrading from 0.3.0

- `number_style="labview"` rounds an exact 20-digit tie away from zero, as LabVIEW 2026 was
  captured doing; 0.3.0 rounded it to even. Only doubles whose exact value has 21 significant
  digits ending in 5 change.
- `loads(..., nan_inf="null")` returns `None`, and `nan_inf="reject"` raises, for numbers that
  overflow a double (`1e400`); 0.3.0 returned `inf` in both.
- `count_nonfinite` accepts `bytes` and `bytearray`, like the other readers.
- `indent` must be `None` or an `int` from 0 to 1024, not a `bool` (0.3.0 passed any value to
  `json`, which accepted strings, `True` and negative numbers and failed on huge ones).
- An option given as a `str` subclass is checked by its text; anything else that is not one of
  the listed strings is refused. The message names the type of a value that is not text
  (`got a value of type int`).
- A `str` subclass passed as text is read by its plain value, so overridden methods such as
  `__len__` or `__getitem__` no longer change what is parsed.
- Error messages are shorter and never quote more than 40 characters of the input. A
  `bytes` input that is not UTF-8 is reported by offset. `LVJSONError` reports its module as
  `lvjson` (it was its private module; the class still lives there, so old pickles load).
- `has_nonfinite` no longer raises `RecursionError` on circular or very deep values.
- A lone surrogate is written as its `\uXXXX` escape (0.3.0 wrote the raw code point, which
  cannot be encoded as UTF-8).
- Command line: a closed output, a missing standard input and an interrupt exit with 1, 1 and
  130 instead of a traceback; `check` no longer fails with a traceback on very deep input;
  `--indent` outside 0 to 1024 is bad usage (exit 2).
