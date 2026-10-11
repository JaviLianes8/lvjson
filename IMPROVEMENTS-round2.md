# Improvements, round 2

Ranked by impact. Each item says what changes and why. The ranking was redone after the
ground-truth capture described first, because that capture overturned the central claim of
0.2.0.

## What the evidence changed

Until this round the README stated that LabVIEW writes non-finite doubles as `NaN`, `Inf` and
`-Inf`. That spelling had never been checked against LabVIEW. This round checked it:

- **Real output.** The shipped example `examples\Strings\Unflatten From JSON.vi` of LabVIEW
  2026 (26.3.1f1) was run unmodified through LabVIEW's ActiveX VI Server with NaN, +Inf and
  -Inf in its DBL data. Flatten To JSON wrote `NaN`, `Infinity` and `-Infinity`. Five captures
  are committed under `tests/fixtures/labview2026/` with a manifest and the capture script; one
  of them covers the values where C's `%g` switches between fixed and exponent form.
- **Runtime strings.** `lvrt.dll` of the LabVIEW 2026 run-time holds `Infinity` and `-Infinity`
  at file offsets `0x119c6d0` / `0x119c6e0`, next to the JSON parser's error messages
  ("unallowed token at this point in JSON text" at `0x119c900`). The JSON lexer's keyword
  suffix table at `0x119cb20` reads `aN`, `nfinity`, `rue`, `alse`, `ull`: the keywords
  `NaN`, `Infinity`, `true`, `false`, `null`. There is no entry for a bare `Inf`.

Consequences:

1. Python's standard `json.loads` already parses real LabVIEW 2026 output. The 0.2.0 "Why"
   section was wrong and must say so.
2. 0.2.0's `dumps` / `to_labview` wrote `Inf` and `-Inf`, a spelling LabVIEW 2026 was not
   seen to produce and that its lexer table does not list. That default was a bug.
3. The captures expose real gaps that 0.2.0 did not know about: LabVIEW writes doubles in a
   form consistent with `%.20g` for every captured value (20 significant digits, e.g.
   `0.10000000000000000555`), writes whole doubles with no
   decimal point (`-1`, `0`) and writes negative zero as `-0`, which `json.loads` turns into the
   integer `0`, losing the sign.

## Ranked improvements

1. **Correct the writer spelling (bug fix).** Emit `NaN`, `Infinity`, `-Infinity` by default,
   matching the captures. Keep a new `infinity="Inf"` option for consumers that expect the old
   spelling, so the writer stays configurable.
2. **Tolerant reader.** Accept both `Infinity` / `-Infinity` (LabVIEW 2026, verified) and
   `Inf` / `-Inf` (plausible from other producers and from lvjson 0.2.0), never inside strings.
3. **Byte-identical LabVIEW number style.** `number_style="labview"` re-emits doubles with
   LabVIEW's `%.20g` form, so `dumps(loads(capture), number_style="labview")` reproduces each
   capture byte for byte. This makes "byte-level compatibility" a tested claim, not a slogan.
4. **Preserve negative zero.** `loads` decodes the bare token `-0` to `-0.0` (no integer can be
   negative zero, so the token can only come from a double).
5. **Golden-fixture contracts.** Every capture is parsed, compared bit for bit against the
   doubles that went in, converted to portable JSON and checked strict, and re-emitted byte for
   byte.
6. **`count_nonfinite` and `lvjson check`.** Report which non-finite spellings a document holds,
   outside string literals, and give pipelines a `--strict` exit code before a strict consumer
   sees the file.
7. **CLI encoding safety.** Read input as UTF-8 bytes (BOM tolerated) and write UTF-8 bytes, so
   LabVIEW's UTF-8 output survives a Windows console code page. Report undecodable input as a
   clean error instead of a traceback. Add `-o/--output`, `--infinity` and `--number-style`.
8. **Real end-to-end test.** Install the package editable and drive the real `lvjson` console
   script with the captures through subprocess, with no mocks.
9. **Honest README.** State which facts rest on real LabVIEW output, which rest on runtime
   strings only, and which are not verified (the extensions-off behaviour, whether LabVIEW's
   reader rejects `Inf`, older LabVIEW versions).

## Considered and left out

- Inferring DBL versus integer from the text: LabVIEW writes `1.0` as `1`, so the type is not
  recoverable from JSON alone. A schema-driven decoder belongs in a separate tool.
- Decoding LabVIEW timestamps (the example's `Time` field): out of scope for a JSON layer.
- Reproducing the extensions-off behaviour of Flatten To JSON: no shipped VI wires that input
  off, so it could not be observed and is not guessed at.
