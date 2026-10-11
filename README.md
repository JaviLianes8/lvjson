# lvjson

Normalise LabVIEW Flatten To JSON output for Python and back, lossless numbers and NaN/Inf policy

## Install

```
pip install lvjson
```

## Usage

```python
import lvjson

# Read text that LabVIEW's "Flatten To JSON" produced, including its NaN/Inf extensions.
data = lvjson.loads('{"gain": 2.5, "reading": NaN, "limit": Infinity}')
# -> {"gain": 2.5, "reading": nan, "limit": inf}

# Write JSON the LabVIEW JSON node ingests cleanly, keeping full double precision.
lvjson.dumps({"gain": 2.5, "offset": 0.1 + 0.2})
# -> '{"gain":2.5,"offset":0.30000000000000004}'

# Choose how non-finite floats cross the boundary.
lvjson.dumps([float("nan")], nan_inf="extend")  # -> '[NaN]'  (LabVIEW extension tokens)
lvjson.dumps([float("nan")], nan_inf="null")    # -> '[null]' (strict, portable JSON)
lvjson.dumps([float("nan")], nan_inf="reject")  # -> raises lvjson.LVJSONError

# Canonicalise LabVIEW's adaptive digit formatting without changing any value.
lvjson.round_trip('{"v": 3.1400000000000001}')  # -> '{"v":3.14}'

# Check before handing a structure to a strict consumer.
lvjson.has_nonfinite({"a": [1.0, float("inf")]})  # -> True
```

## Why

Python's own `json` is more capable than it is often given credit for, so this library does
not duplicate it. By default `json.loads` already accepts `NaN`, `Infinity` and `-Infinity`,
`json.dumps` already emits them (`allow_nan=True`), and since Python 3.1 `float.__repr__`
already produces the shortest string that round-trips a double exactly. None of that is the
gap `lvjson` closes.

The gap is byte-level compatibility with LabVIEW's **Flatten To JSON** node, which does not
emit portable JSON and does not format numbers the way `json` does:

- **Number formatting.** NI documents that the node changes how many digits a `DBL` gets
  depending on the value, so a value serialised by LabVIEW and re-serialised by `json` can
  differ character for character even though both are correct doubles (NI: "Flatten To JSON
  changes the DBL digits"). `lvjson` round-trips the LabVIEW form so the bytes match what
  LabVIEW reads and writes.
- **A strict boundary for non-finite floats.** LabVIEW's extension tokens (`NaN`,
  `Infinity`, `-Infinity`) are legal input to `json` but are rejected by strict,
  spec-conformant consumers elsewhere. `lvjson.loads` reads them, and `lvjson.dumps` lets you
  keep them (`extend`), convert them to `null`, or reject them (`reject`), so you choose what
  a strict far end receives instead of discovering the mismatch downstream.

So `lvjson` is a small, typed, zero-dependency layer over the standard library `json` module,
aimed squarely at matching LabVIEW's Flatten To JSON output and giving you an explicit strict
mode at the boundary, not at adding number or NaN/Inf support that `json` already has.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
