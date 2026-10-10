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

LabVIEW's **Flatten To JSON** node does not emit portable JSON: doubles get adaptive
precision and non-finite floats become `NaN` / `Infinity` tokens that strict parsers reject.
`lvjson` reads that text, writes JSON LabVIEW ingests cleanly, and round-trips numbers
without silent precision loss.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
