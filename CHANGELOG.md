# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-13

First stable release. The public API is the eleven names in `lvjson.__all__` (`loads`,
`dumps`, `to_portable`, `to_labview`, `round_trip`, `count_nonfinite`, `has_nonfinite`,
`LVJSONError`, `NanInf`, `InfSpelling`, `NumberStyle`) and the `lvjson` command, with the
signatures, defaults and error types the guide documents. New LabVIEW 2026 captures show what
Unflatten From JSON reads back from Flatten To JSON output.

### Fixed

- `number_style="labview"` rounds a double whose exact value lies halfway between two
  20-digit results away from zero, as Flatten To JSON was captured doing (`2**-30` is written
  `9.3132257461547851563e-10`). 0.3.0 rounded such ties to even and wrote `...562e-10`.
- `loads` with `nan_inf="null"` returns `None`, and with `nan_inf="reject"` raises
  `LVJSONError`, for a number that overflows a double (`1e400`). 0.3.0 returned `inf` in both.
- `has_nonfinite` no longer raises `RecursionError` on circular or very deep values.
- Error messages never quote more than 40 characters of a value or a type name and stay under
  200 characters; text that is not UTF-8 is reported by byte offset.
- Command line: a closed standard output exits with 1 quietly, a missing standard input is
  bad input (exit 1), an interrupt exits with 130, usage errors no longer echo huge arguments,
  and `check` reports input nested too deeply as bad input instead of a traceback.

### Changed

- `indent` must be `None` or a non-negative `int`: other types raise `TypeError`, negative
  values `ValueError`. 0.3.0 passed them to `json` unchecked.
- An option given as a `str` subclass (such as a `StrEnum` member) is checked by its text; any
  other value that is not one of the listed strings raises `ValueError`.
- `count_nonfinite` accepts UTF-8 `bytes` and `bytearray`, like the other readers.
- Values of a `str` or `float` subclass are read and written by their plain value; overridden
  methods do not change the output.
- Project metadata: `Production/Stable`, Python 3.10 to 3.14, `Source` and `Documentation`
  URLs; the sdist now holds only the package, tests, docs and license.

### Added

- `GUIDE.md`: every function, option, number form, error and command, the evidence, and the
  changes from 0.3.0.
- Captures of Unflatten From JSON reading Flatten To JSON output back
  (`tests/fixtures/labview2026/readback_*`), made by `scripts/capture-labview-readback.ps1`:
  every double reads back bit for bit except `-0`, which LabVIEW reads as `+0.0`.
- Tests against independent oracles (exact rational arithmetic and the Windows C runtime's
  `printf`), against RFC 8259 and NI's function pages (copies fetched locally by
  `scripts/fetch_sources.py`, only their manifest is tracked), seeded fuzzing, and executable
  README and GUIDE examples.

## [0.3.0]

Checked against genuine LabVIEW 2026 Flatten To JSON output for the first time (captures and
their provenance in `tests/fixtures/labview2026/`).

### Fixed

- The default output spelling of the infinities is now `Infinity` / `-Infinity`, which is what
  LabVIEW 2026 writes for DBL values with the node's default settings. 0.2.0 wrote `Inf` /
  `-Inf`, a spelling LabVIEW 2026 was not seen to produce. Pass `infinity="Inf"` (CLI:
  `--infinity Inf`) to keep the old output.
- `loads` decodes the bare token `-0`, which LabVIEW writes for a negative-zero double, to
  `-0.0` instead of the integer `0`. As a result `round_trip`, `to_portable` and `to_labview`
  write such a value as `-0.0` (or `-0` with `number_style="labview"`) instead of `0`.
- Scanning for non-finite tokens stays linear on truncated input with an unclosed string.
- Encoding a circular value raises `LVJSONError` under every `nan_inf` policy.
- The CLI reads input as UTF-8 bytes and writes UTF-8 bytes, so LabVIEW's UTF-8 text survives
  a narrow console code page; undecodable or unencodable text is a clean error (exit 1)
  instead of a traceback. On Windows, standard output lines now end in LF rather than CRLF.
- The README no longer claims that the standard `json` module cannot read LabVIEW output, and
  states which facts rest on real LabVIEW output and which do not.

### Added

- `number_style="labview"` for `dumps`, `to_labview` and `round_trip`: LabVIEW's own
  20-significant-digit number formatting, reproducing captured output byte for byte.
- `infinity` option (`"Infinity"` or `"Inf"`) for `dumps`, `to_labview` and `round_trip`.
- `count_nonfinite`: count each non-finite spelling outside string literals.
- `InfSpelling` and `NumberStyle` type aliases.
- `loads`, `to_portable`, `to_labview` and `round_trip` accept UTF-8 `bytes`; a leading byte
  order mark is tolerated in `bytes` and `str` input.
- CLI: `lvjson check [--strict]` (non-finite tokens and numbers that overflow a double),
  `-o/--output`, `--infinity`, `--number-style`, documented exit status.
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
