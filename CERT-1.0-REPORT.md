# lvjson 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0)
- [x] Baseline gates run on 0.3.0
- [x] Real LabVIEW 2026 captures of Unflatten From JSON reading Flatten To JSON output (item 7)
- [ ] Public sources fetched (NI function pages, RFC 8259), manifest tracked (item 7)
- [ ] API review and 1.0.0 API changes (item 1)
- [ ] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Contract, oracle, fuzz and author mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [ ] Gates (item 15)
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Baseline on 0.3.0 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .`, `mypy --strict src tests` | exit 0 |
| `pytest` | 1977 passed |
| `pytest --doctest-modules src` | no doctests at all (exit 5) |

## Ground truth (item 7)

`tests/fixtures/labview2026/readback_*.json` and `readback_*.values.json` were written on
2026-10-13 by `scripts/capture-labview-readback.ps1`, which runs the shipped example
`examples\Strings\Unflatten From JSON.vi` of LabVIEW 2026 (26.3.1f1) unmodified. One run gives
the Flatten To JSON string and the doubles that the example's Unflatten From JSON nodes read
back from that same string, as IEEE 754 bit patterns. Findings:

- Unflatten From JSON reads `NaN`, `Infinity`, `-Infinity`, the 20-digit forms, the smallest
  subnormal and the largest finite double back to exactly the bits that went in.
- It reads the `-0` that Flatten To JSON writes for a negative zero as positive zero.
