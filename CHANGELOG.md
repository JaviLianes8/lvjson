# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- `loads`: parse LabVIEW JSON, accepting the `NaN` / `Infinity` / `-Infinity` extension
  tokens, with a `nan_inf="reject"` option to refuse them.
- `dumps`: emit JSON the LabVIEW JSON node ingests cleanly, with full double precision and a
  `nan_inf` policy of `extend`, `null` or `reject` for non-finite floats.
- `round_trip`: canonicalise LabVIEW's adaptive digit formatting without changing any value.
- `has_nonfinite`: report whether a parsed structure holds any NaN or infinite float.
- `LVJSONError`: single error type for parse and serialisation failures.
- First release.
