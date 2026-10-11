# lvjson

Byte-level compatibility with LabVIEW Flatten To JSON output, lossless numbers and a NaN/Inf policy.

## Install

```
pip install lvjson
```

## Usage

```python
import lvjson

# Read text that LabVIEW's "Flatten To JSON" produced, including its NaN / Inf / -Inf tokens.
data = lvjson.loads('{"gain": 2.5, "reading": NaN, "limit": Inf, "floor": -Inf}')
# -> {"gain": 2.5, "reading": nan, "limit": inf, "floor": -inf}

# Write JSON the LabVIEW JSON node ingests cleanly, keeping full double precision.
lvjson.dumps({"gain": 2.5, "offset": 0.1 + 0.2})
# -> '{"gain":2.5,"offset":0.30000000000000004}'

# Non-finite floats come out in LabVIEW's spelling, not the json module's.
lvjson.dumps([float("nan"), float("inf"), float("-inf")])
# -> '[NaN,Inf,-Inf]'

# Choose how non-finite floats cross the boundary.
lvjson.dumps([float("nan")], nan_inf="extend")  # -> '[NaN]'  (LabVIEW tokens)
lvjson.dumps([float("nan")], nan_inf="null")    # -> '[null]' (strict, portable JSON)
lvjson.dumps([float("nan")], nan_inf="reject")  # -> raises lvjson.LVJSONError

# Convert whole documents between the two worlds.
lvjson.to_portable('{"limit": Inf}')             # -> '{"limit":null}'   (strict by default)
lvjson.to_portable('{"limit": Inf}', nan_inf="extend")  # -> '{"limit":Infinity}'
lvjson.to_labview('{"limit": Infinity}')         # -> '{"limit":Inf}'

# Canonicalise LabVIEW's adaptive digit formatting without changing any value.
lvjson.round_trip('{"v": 3.1400000000000001}')   # -> '{"v":3.14}'

# Check before handing a structure to a strict consumer.
lvjson.has_nonfinite({"a": [1.0, float("inf")]}) # -> True
```

## Command line

The package installs an `lvjson` command for whole files or pipelines:

```
# LabVIEW JSON to portable JSON, non-finite values become null (the default)
echo '{"gain":2.5,"reading":NaN,"limit":Inf}' | lvjson to-portable
# -> {"gain":2.5,"reading":null,"limit":null}

# portable JSON back to the LabVIEW spelling (NaN / Inf / -Inf)
echo '{"limit":Infinity}' | lvjson to-labview
# -> {"limit":Inf}

# keep the infinities, pretty-print, or fail loudly
lvjson to-portable data.lvjson --nan-inf extend --indent 2
lvjson to-portable data.lvjson --nan-inf reject
```

Run `lvjson --help`, `lvjson to-portable --help` or `lvjson to-labview --help` for the full list.

## Why

Python's own `json` is more capable than it is often given credit for, so this library does
not duplicate it. `json.loads` already accepts `NaN`, `Infinity` and `-Infinity`, `json.dumps`
already emits them (`allow_nan=True`), and since Python 3.1 `float.__repr__` already produces
the shortest string that round-trips a double exactly. None of that is the gap `lvjson` closes.

The gap is byte-level compatibility with LabVIEW's **Flatten To JSON** node, which does not
emit portable JSON and does not spell its numbers the way `json` does:

- **Non-finite tokens that `json` cannot read.** LabVIEW writes the bare tokens `NaN`, `Inf`
  and `-Inf`. The standard library spells the infinities `Infinity` and `-Infinity`, so
  `json.loads('{"x": Inf}')` raises, and `json.dumps(float("inf"))` produces `Infinity`, which
  LabVIEW does not ingest. `lvjson` translates the tokens both ways, so the same value survives
  a round trip through either side.
- **A strict boundary for non-finite floats.** Those tokens are not valid JSON per RFC 8259 and
  are rejected by strict consumers elsewhere. `lvjson` lets you keep them (`extend`), convert
  them to `null` (`null`), or reject the value (`reject`), so you choose what a strict far end
  receives instead of discovering the mismatch downstream.
- **Number formatting.** NI documents that the node adapts how many digits a `DBL` gets to the
  value, so a number written by LabVIEW can carry redundant trailing digits. `round_trip`
  re-emits each double in its shortest exact form, so the text is canonical and the value is
  unchanged.

So `lvjson` is a small, typed, zero-dependency layer over the standard library `json` module,
aimed squarely at matching LabVIEW's Flatten To JSON output and giving you an explicit strict
mode at the boundary, not at adding number or NaN/Inf support that `json` already has.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
