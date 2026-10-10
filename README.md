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

LabVIEW's **Flatten To JSON** node does not emit portable JSON. Two concrete problems:

- **Adaptive double precision.** NI documents that the node changes how many digits a `DBL`
  gets depending on the value, so the same number can serialise differently and a naive
  round-trip loses or gains digits (NI: "Flatten To JSON changes the DBL digits"). `lvjson`
  re-emits every finite double with the shortest representation that round-trips exactly, so
  values survive the trip into LabVIEW and back unchanged.
- **NaN / Inf extensions.** When "enable LabVIEW extensions" is on, the node writes bare
  `NaN`, `Infinity` and `-Infinity` tokens, which strict parsers reject. Other JSON tooling
  hits the same wall (see JSONtext issue #116). `lvjson.loads` accepts those tokens safely,
  and `lvjson.dumps` lets you keep them (`extend`), convert them to `null`, or reject them,
  so you decide what the far end receives.

General-purpose JSON packages such as `json-flatten` and `flatten_json` solve a different
problem (flattening nested objects into dotted keys); none address LabVIEW's number
formatting or its NaN/Inf extensions. `lvjson` is a small, typed, zero-dependency layer over
the standard library `json` module aimed squarely at the LabVIEW boundary.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
