# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/lvjson/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change, including what it refuses and raises.
- Claims about LabVIEW are pinned to the genuine captures in `tests/fixtures/labview2026/`;
  never hand-write a file there. New captures come from `scripts/capture-labview-json.ps1`
  (Flatten To JSON output) or `scripts/capture-labview-readback.ps1` (what Unflatten From JSON
  reads back), run against a copy of LabVIEW's shipped example, and get a manifest entry.
- The end-to-end tests install the package editable into a throwaway environment and run the
  real `lvjson` script; they borrow the build backend from the running interpreter, so no
  network is needed.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

## Public sources

`tests/test_sources_truth.py` re-reads facts from NI's Flatten To JSON and Unflatten From JSON
pages and from RFC 8259. Those copies are not in the repository; fetch them with
`python scripts/fetch_sources.py`, which also rewrites `tests/fixtures/sources/MANIFEST.json`
(URL, date, size, SHA-256, licence). Without them the module skips.

Open an issue first if the change is large or shifts the public API.
