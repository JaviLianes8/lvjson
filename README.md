# lvjson

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Read and write LabVIEW **Flatten To JSON** text from Python: the `NaN` and `Infinity` tokens,
LabVIEW's exact 20-digit numbers, negative zero, and strict portable JSON for everything else.

Every statement here about what LabVIEW writes or reads is pinned to output captured from
LabVIEW 2026 and checked by the test suite. Pure Python, typed, no dependencies.

- [Guide](https://github.com/JaviLianes8/lvjson/blob/main/GUIDE.md): every function, the
  options, the number forms, errors, the command line and the evidence.
- [Changelog](https://github.com/JaviLianes8/lvjson/blob/main/CHANGELOG.md)

## Install

```
pip install lvjson
```

Python 3.10 or newer.

## Quick start

```pycon
>>> import lvjson
>>> text = '{"Data":[NaN,Infinity,-Infinity,0.10000000000000000555,-0]}'
>>> data = lvjson.loads(text)
>>> data
{'Data': [nan, inf, -inf, 0.1, -0.0]}
>>> lvjson.to_portable(text)
'{"Data":[null,null,null,0.1,-0.0]}'
>>> lvjson.dumps(data, number_style="labview") == text
True
>>> lvjson.dumps(data)
'{"Data":[NaN,Infinity,-Infinity,0.1,-0.0]}'
>>> lvjson.count_nonfinite(text)
{'NaN': 1, 'Infinity': 1, '-Infinity': 1}

```

`loads` also reads the `Inf` / `-Inf` spelling other producers use, never inside strings.
`nan_inf` decides what non-finite values become at the boundary: kept (`"extend"`), `null`,
or an `LVJSONError` (`"reject"`):

```pycon
>>> lvjson.loads('[Inf, -Inf, "Inf", 1e400]', nan_inf="null")
[None, None, 'Inf', None]
>>> lvjson.dumps([float("nan")], nan_inf="reject")
Traceback (most recent call last):
  ...
lvjson.LVJSONError: non-finite float is not allowed under nan_inf='reject'
>>> lvjson.round_trip('{"v": 3.141592653589793116}')
'{"v":3.141592653589793}'

```

| Function | Purpose |
| --- | --- |
| `loads(text, nan_inf=)` | Parse LabVIEW JSON (`str`, or UTF-8 `bytes` / `bytearray`) |
| `dumps(obj, nan_inf=, infinity=, number_style=, indent=, sort_keys=)` | Serialise for LabVIEW |
| `to_portable(text, nan_inf="null", indent=, sort_keys=)` | LabVIEW text to strict RFC 8259 JSON |
| `to_labview(text, nan_inf=, infinity=, number_style=, indent=, sort_keys=)` | JSON text to LabVIEW text |
| `round_trip(text, ...)` | Re-emit LabVIEW text canonically, values unchanged |
| `count_nonfinite(text)` | Count each non-finite spelling outside strings |
| `has_nonfinite(obj)` | Whether a parsed value holds NaN or an infinity |

`number_style="labview"` writes doubles the way Flatten To JSON does: 20 significant digits
in C's `%g` layout, exact ties rounded away from zero. `"shortest"` (the default) writes the
shortest text that reads back as the same double. Both keep every double exact.
`infinity="Inf"` spells the infinities `Inf` / `-Inf`. Data errors raise `LVJSONError` (a
`ValueError`); the [guide](https://github.com/JaviLianes8/lvjson/blob/main/GUIDE.md#errors)
lists every error.

## Command line

```
$ echo '{"gain":2.5,"reading":NaN,"limit":Infinity}' | lvjson to-portable
{"gain":2.5,"reading":null,"limit":null}
$ echo '{"x":0.1,"limit":-Inf}' | lvjson to-labview --number-style labview
{"x":0.10000000000000000555,"limit":-Infinity}
$ echo '[NaN, 1e400, "NaN"]' | lvjson check --strict
<stdin>: valid, non-finite values: NaN x1, numbers that overflow a double x1
```

Files work too (`lvjson to-labview data.json -o out.json`). Input is read as UTF-8 bytes and
output written as UTF-8 whatever the console code page. Exit status: 0 success, 1 bad input,
failed conversion, `--strict` finding or closed output, 2 bad usage, 130 interrupted.

## Why

Python's `json.loads` already parses what LabVIEW 2026 writes: `NaN`, `Infinity` and
`-Infinity` are the tokens the standard library uses too. What `lvjson` adds is the boundary
around that parse:

- **A strict mode.** The non-finite tokens are not RFC 8259 JSON, which says values such as
  Infinity and NaN are not permitted. `to_portable` and `nan_inf` decide what a strict
  consumer receives (`null`, the tokens, or an error) instead of failing downstream.
- **Negative zero.** Flatten To JSON writes a `-0.0` double as `-0`; `json.loads` returns the
  integer `0`, and LabVIEW 2026's own Unflatten From JSON reads it back as `+0.0`.
  `lvjson.loads` returns `-0.0`, the double that was flattened.
- **LabVIEW's number form.** Flatten To JSON writes `0.1` as `0.10000000000000000555` and
  `1.0` as `1`; `json.dumps` writes `0.1` and `1.0`. `number_style="labview"` reproduces every
  captured LabVIEW string byte for byte, including exact ties that Python's own `'.20g'`
  formatting rounds the other way.
- **Other spellings.** `Inf` / `-Inf` from other producers are read and can be written on
  request, never touching string contents.

## Evidence

Eleven files in `tests/fixtures/labview2026/` come from LabVIEW 2026 (26.3.1f1) running the
shipped example `examples\Strings\Unflatten From JSON.vi` unmodified with chosen DBL values:
the strings its Flatten To JSON node wrote and the doubles its Unflatten From JSON nodes read
back from them, with a manifest of method, inputs and hashes. NI's function pages and RFC 8259
were fetched on 2026-10-13 for the source tests (only their manifest is in the repository). The
[guide](https://github.com/JaviLianes8/lvjson/blob/main/GUIDE.md#evidence) says what each
capture shows and what was not verified.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/lvjson/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
