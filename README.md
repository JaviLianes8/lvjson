# lvjson

Read and write LabVIEW **Flatten To JSON** text from Python: the non-finite tokens LabVIEW
really writes, its exact number formatting, and a strict portable mode for everything else.

Every claim about LabVIEW's output below is pinned to genuine bytes captured from LabVIEW 2026
and checked by the test suite. See [What rests on evidence](#what-rests-on-evidence).

## Install

```
pip install lvjson
```

Python 3.10 or newer, no dependencies.

## Usage

```python
import math

import lvjson

# Text in the form LabVIEW 2026's Flatten To JSON writes (see tests/fixtures/labview2026).
labview = '{"Data":[NaN,Infinity,-Infinity,0.10000000000000000555,-0]}'

data = lvjson.loads(labview)
assert math.isnan(data["Data"][0]) and data["Data"][1:3] == [math.inf, -math.inf]
assert data["Data"][3] == 0.1  # 20 digits in, the exact same double out
assert math.copysign(1.0, data["Data"][4]) == -1.0  # "-0" keeps its sign (json gives int 0)

# The short Inf / -Inf spelling some producers use is read too, never inside strings.
assert lvjson.loads('[Inf, -Inf, "Inf"]') == [math.inf, -math.inf, "Inf"]

# Strict, portable JSON for consumers that reject NaN and Infinity (the default is null).
assert lvjson.to_portable(labview) == '{"Data":[null,null,null,0.1,-0.0]}'

# Back to LabVIEW. number_style="labview" re-creates Flatten To JSON's own digits,
# so a value read from LabVIEW is written back byte for byte.
assert lvjson.dumps(data, number_style="labview") == labview
assert lvjson.dumps(data) == '{"Data":[NaN,Infinity,-Infinity,0.1,-0.0]}'

# The infinities can be spelled Inf / -Inf for a consumer that expects that.
assert lvjson.dumps([math.inf, -math.inf], infinity="Inf") == "[Inf,-Inf]"

# Non-finite policy at the boundary: keep, turn into null, or refuse.
assert lvjson.dumps([math.nan], nan_inf="null") == "[null]"
try:
    lvjson.dumps([math.nan], nan_inf="reject")
except lvjson.LVJSONError:
    pass

# Canonicalise LabVIEW's 20-digit numbers without changing any value.
assert lvjson.round_trip('{"v": 3.141592653589793116}') == '{"v":3.141592653589793}'

# Inspect before handing data to a strict consumer.
assert lvjson.count_nonfinite(labview) == {"NaN": 1, "Infinity": 1, "-Infinity": 1}
assert lvjson.has_nonfinite({"a": [1.0, math.inf]})
```

`loads`, `to_portable`, `to_labview` and `round_trip` accept `str` or UTF-8 `bytes` (the
encoding LabVIEW writes). Every error is an `lvjson.LVJSONError`, a `ValueError` subclass.

| Function | Purpose |
| --- | --- |
| `loads(text, nan_inf=)` | Parse; `nan_inf` is `"extend"` (floats), `"null"` (None) or `"reject"` |
| `dumps(obj, nan_inf=, infinity=, number_style=, indent=, sort_keys=)` | Serialise for LabVIEW |
| `to_portable(text, nan_inf="null", ...)` | LabVIEW text to strict RFC 8259 JSON |
| `to_labview(text, nan_inf=, infinity=, number_style=, ...)` | JSON text to LabVIEW text |
| `round_trip(text, ...)` | Re-emit LabVIEW text canonically, values unchanged |
| `count_nonfinite(text)` | Count each non-finite spelling outside strings |
| `has_nonfinite(obj)` | Whether a parsed value holds NaN or an infinity |

`infinity` is `"Infinity"` (default, what LabVIEW 2026 writes) or `"Inf"`. `number_style` is
`"shortest"` (default, the shortest exact text, e.g. `0.1`, `1.0`) or `"labview"` (C `%.20g`,
e.g. `0.10000000000000000555`, `1`). Both styles preserve every double exactly.

## Command line

```
# LabVIEW JSON to strict portable JSON: NaN / Infinity / -Infinity become null
echo '{"gain":2.5,"reading":NaN,"limit":Infinity}' | lvjson to-portable
# -> {"gain":2.5,"reading":null,"limit":null}

# back to LabVIEW, re-creating Flatten To JSON's exact number formatting
echo '{"x":0.1,"limit":Infinity}' | lvjson to-labview --number-style labview
# -> {"x":0.10000000000000000555,"limit":Infinity}

# the short spelling, written to a file (UTF-8, no trailing newline)
lvjson to-labview data.json --infinity Inf -o out.json

# list the non-finite values in a file (tokens, and numbers that overflow a double);
# --strict exits 1 if there are any
lvjson check data.json --strict
# -> data.json: valid, non-finite values: NaN x1, Infinity x1, -Infinity x1
```

Input is read as UTF-8 bytes and output written as UTF-8, whatever the console code page.
Exit status is 0 on success, 1 on an input, conversion or `--strict` failure, 2 on bad usage.
Run `lvjson --help` or `lvjson <command> --help` for every option.

## Why

Python's `json.loads` already parses what LabVIEW 2026 writes: `NaN`, `Infinity` and
`-Infinity` are the same tokens the standard library uses. Earlier releases of this library
said otherwise; that was wrong, and 0.3.0 corrects it. What `lvjson` adds is the boundary
around that parse:

- **A strict mode.** The non-finite tokens are not RFC 8259 JSON. Browsers, Go, Rust and many
  other parsers reject them. `to_portable` and `nan_inf` decide explicitly what a strict
  consumer receives (`null`, the tokens, or an error) instead of failing downstream.
- **Negative zero.** LabVIEW writes a `-0.0` double as `-0`; `json.loads` returns the integer
  `0`. `lvjson.loads` returns `-0.0`.
- **LabVIEW's number formatting.** LabVIEW writes 20 significant digits
  (`0.10000000000000000555`) and whole doubles without a decimal point. `number_style="labview"`
  reproduces that exactly, so text can be regenerated byte for byte; `round_trip` goes the
  other way and canonicalises to the shortest exact form.
- **Other spellings.** `Inf` / `-Inf` from other producers (and from lvjson 0.2.0) are read and
  can be written on request, always leaving string contents untouched.

## What rests on evidence

**Verified against real LabVIEW output.** Five files in `tests/fixtures/labview2026/` hold
the output of LabVIEW 2026 (26.3.1f1) running the shipped example
`examples\Strings\Unflatten From JSON.vi` unmodified, with chosen input values. Each is the
string its Flatten To JSON node produced, rebuilt byte for byte from what LabVIEW returned
(method, inputs and hashes in `manifest.json`; `scripts/capture-labview-json.ps1` reproduces
it, and a second run gave the same bytes apart from the run-time timestamp). For DBL values,
with the example's settings, they show:

- non-finite doubles written as the bare tokens `NaN`, `Infinity`, `-Infinity`;
- numbers consistent with C `%.20g` for every captured double, including where `%g` switches
  between fixed and exponent form: `0.10000000000000000555`, `1.0000000000000000818e-05`,
  `0.00010000000000000000479`, `10000000000000000000`, `1e+20`, `1.0000000000000000525e+300`,
  whole values as `-1` or `65536`, negative zero as `-0`;
- every captured double decoding to exactly the double that went in;
- compact separators, UTF-8 text, `\t` `\n` `\r` `\u0001` escapes, `/` left unescaped;
- token-like words inside strings written as ordinary string content.

`dumps(..., number_style="labview")` reproduces all five captures byte for byte.

**Supported by the runtime's strings only.** In `lvrt.dll` of the LabVIEW 2026 run-time, the
JSON lexer's keyword table (offset `0x119cb20`) holds the suffixes `aN`, `nfinity`, `rue`,
`alse`, `ull`, that is the keywords `NaN`, `Infinity`, `true`, `false`, `null`, and has no
entry for `Inf`. That suggests LabVIEW's own reader accepts `Infinity` and not `Inf`, which is
why `"Infinity"` is the default output spelling. It was not exercised.

**Not verified.** Output with the node's *enable LabVIEW extensions* input set to false (the
captured example does not wire it off); numeric types other than DBL (SGL and EXT were not
captured, integers only as the example's small fields, and `number_style="labview"` targets
DBL output); LabVIEW
versions other than 2026; and whether any LabVIEW reader accepts `Inf`. The `Inf` spelling is
supported for other producers, not because LabVIEW was seen to use it.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
