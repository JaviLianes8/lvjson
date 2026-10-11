# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0]

Checked against genuine LabVIEW 2026 Flatten To JSON output for the first time (captures and
their provenance in `tests/fixtures/labview2026/`).

### Fixed

- The default output spelling of the infinities is now `Infinity` / `-Infinity`, which is what
  LabVIEW 2026 writes. 0.2.0 wrote `Inf` / `-Inf`, a spelling LabVIEW 2026 does not produce.
  Pass `infinity="Inf"` (CLI: `--infinity Inf`) to keep the old output.
- `loads` decodes the bare token `-0`, which LabVIEW writes for a negative-zero double, to
  `-0.0` instead of the integer `0`.
- The CLI reads input as UTF-8 bytes and writes UTF-8 bytes, so LabVIEW's UTF-8 text survives
  a narrow console code page; undecodable input is a clean error instead of a traceback.
- The README no longer claims that the standard `json` module cannot read LabVIEW output, and
  states which facts rest on real LabVIEW output and which do not.

### Added

- `number_style="labview"` for `dumps`, `to_labview` and `round_trip`: LabVIEW's own
  20-significant-digit number formatting, reproducing captured output byte for byte.
- `infinity` option (`"Infinity"` or `"Inf"`) for `dumps`, `to_labview` and `round_trip`.
- `count_nonfinite`: count each non-finite spelling outside string literals.
- `InfSpelling` and `NumberStyle` type aliases.
- `loads`, `to_portable`, `to_labview` and `round_trip` accept UTF-8 `bytes`.
- CLI: `lvjson check [--strict]`, `-o/--output`, `--infinity`, `--number-style`, documented
  exit status.
- Golden fixtures from LabVIEW 2026, a full-promise contract test and a real end-to-end test of
  the installed console script.

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
