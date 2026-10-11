# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

- Correct the non-finite tokens to match LabVIEW exactly: `loads` now reads `Inf` and `-Inf`
  (which the standard `json` module cannot parse) and `dumps` now writes them, instead of the
  `json` module's `Infinity` / `-Infinity` spelling. Standard JSON is still accepted on input.
- `to_portable`: convert LabVIEW JSON text to standard JSON for strict consumers, with the
  non-finite policy (`null` by default, or `extend` / `reject`).
- `to_labview`: convert standard JSON text to the LabVIEW spelling, the reverse of `to_portable`.
- `loads` with `nan_inf="null"` now decodes non-finite tokens to `None` instead of keeping the
  float, mirroring the serialise side.
- Add the `lvjson` command line interface (`to-portable` / `to-labview`) with a `--nan-inf`
  mode flag, `--indent`, `--sort-keys`, stdin or file input, and examples in `--help`.

## [0.1.0]

- `loads`: parse LabVIEW JSON, accepting the `NaN` / `Infinity` / `-Infinity` extension
  tokens, with a `nan_inf="reject"` option to refuse them.
- `dumps`: emit JSON the LabVIEW JSON node ingests cleanly, with full double precision and a
  `nan_inf` policy of `extend`, `null` or `reject` for non-finite floats.
- `round_trip`: canonicalise LabVIEW's adaptive digit formatting without changing any value.
- `has_nonfinite`: report whether a parsed structure holds any NaN or infinite float.
- `LVJSONError`: single error type for parse and serialisation failures.
- First release.
