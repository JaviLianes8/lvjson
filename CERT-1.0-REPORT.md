# lvjson 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0)
- [x] Baseline gates run on 0.3.0
- [x] Real LabVIEW 2026 captures of Unflatten From JSON reading Flatten To JSON output (item 7)
- [x] Public sources fetched (NI function pages, RFC 8259), manifest tracked (item 7)
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, oracle, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [x] Gates (item 15)
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
- Flatten To JSON rounds an exact 20-digit tie away from zero: `2**-30` (exact value
  `9.31322574615478515625e-10`) is written `9.3132257461547851563e-10`. 0.3.0 used Python's
  `'.20g'`, which rounds the tie to even (`...562e-10`), so its claim to reproduce Flatten To JSON
  byte for byte was false for such values. Twelve tie doubles were captured (`readback_ties`).

Earlier captures (`flatten_to_json_*.json`, 2026-10-12) stay as they were.

Public sources, fetched 2026-10-13 by `scripts/fetch_sources.py` (copies git-ignored and excluded
from the sdist, `tests/fixtures/sources/MANIFEST.json` tracked with URL, date, size, SHA-256 and
licence): NI's Flatten To JSON and Unflatten From JSON pages (through NI's documentation API) and
RFC 8259. `tests/test_sources_truth.py` re-reads the defaults of *enable LabVIEW extensions* (true)
and *default null elements* (false, null is then an error) and the RFC number grammar, and checks
portable output against that grammar.

Independent oracles (`tests/test_oracle.py`): the 20-digit form is compared on 4000 seeded random
doubles, the `%g` boundaries and 548 exact ties (4734 values) with exact `Fraction` arithmetic written in the
test, and with `printf("%.20g")` of the Windows C runtime (`ucrtbase.dll`), which also rounds ties
away from zero; the shortest form and the reader are compared with the `json` module.

## API review and 1.0.0 changes (items 1 to 5)

Kept: the eleven public names of 0.3.0, their parameters and defaults. Changed, each listed in
CHANGELOG 1.0.0 and the guide's upgrade section:

- ties in `number_style="labview"` (above);
- `loads` under `nan_inf="null"` / `"reject"` treats numbers that overflow a double as
  non-finite (0.3.0 returned `inf`);
- `count_nonfinite` accepts `bytes` and `bytearray` like the other readers;
- `indent` validated (`TypeError` for non-int, `ValueError` for negative);
- options compared by their plain text, so a `StrEnum` member works and an object with a lying
  `__eq__` or `__hash__` cannot pass;
- error messages bounded (40 characters of a value or type name, 200 in total), UTF-8 errors
  reported by offset; `LVJSONError.__module__` is `lvjson`;
- `has_nonfinite` walks without recursion and survives cycles;
- command line: closed output (exit 1, silent), missing stdin (exit 1), interrupt (130), usage
  errors cut, `check` safe on very deep input.

Errors are documented in the guide's table: `LVJSONError` for data, `ValueError` for option
values, `TypeError` for argument types, as `json` does for unserialisable objects. Every public
function, `LVJSONError` and the package docstring (for the three option aliases) carry runnable
examples; `tests/test_docs.py` runs the doctests of every module and every `pycon` block and
command transcript in README and GUIDE. `loads` returns `Any`, as `json.loads` does, documented
in the guide.

## Author mutation round (item 18)

Each mutation was applied alone to a clean copy of the branch, `__pycache__` purged, the
suite run with `-x`, `PYTHONDONTWRITEBYTECODE=1` and no cache, then the file restored; the
baseline was green before and after. 55 mutations: 50 killed at once; D04, D07, S03 and Y03
survived and were killed by new contracts (D04 and D07 sit on a branch only exact ties reach,
which never have an exponent of 20 or more, so the new contract checks that branch on every
double); D01 first failed at import and was re-run as a valid mutation.

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| D01 | ties rounded to even | `_digits.py` | killed (re-run) | `tests/test_docs.py::test_module_doctests_pass[lvjson._digits]` |
| D02 | tie detection never fires | `_digits.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvjson._digits]` |
| D03 | fixed form one decade too low | `_digits.py` | killed | `tests/test_oracle.py::test_labview_style_matches_exact_rational_arithmetic` |
| D04 | fixed form one decade too high | `_digits.py` | survived, then killed | `tests/test_oracle.py::test_the_exact_path_agrees_with_the_oracle_on_every_double` |
| D05 | exponent not padded to two digits | `_digits.py` | killed | `tests/test_oracle.py::test_labview_style_matches_exact_rational_arithmetic` |
| D06 | 19 significant digits | `_digits.py` | killed | `tests/test_cli.py::test_to_labview_spelling_and_number_style_flags` |
| D07 | positive exponent unsigned | `_digits.py` | survived, then killed | `tests/test_oracle.py::test_the_exact_path_agrees_with_the_oracle_on_every_double` |
| D08 | sign dropped on exact ties | `_digits.py` | killed | `tests/test_fuzz.py::test_mutated_captures_never_crash` |
| L01 | NaN spelled nan | `_labview_format.py` | killed | `tests/test_docs.py::test_every_pycon_example_runs[README.md]` |
| L02 | infinity signs swapped | `_labview_format.py` | killed | `tests/test_cli.py::test_to_labview_spelling_and_number_style_flags` |
| L03 | True key spelled True | `_labview_format.py` | killed | `tests/test_labview_format.py::test_labview_style_coerces_keys_like_json` |
| L04 | non-ASCII escaped | `_labview_format.py` | killed | `tests/test_labview_format.py::test_labview_style_matches_json_layout_without_floats[None-value4]` |
| L05 | indented key separator without space | `_labview_format.py` | killed | `tests/test_labview_format.py::test_labview_style_matches_json_layout_without_floats[0-value2]` |
| L06 | shared children reported circular | `_labview_format.py` | killed | `tests/test_labview_format.py::test_labview_style_allows_shared_non_circular_children` |
| L07 | non-finite key policy inverted | `_labview_format.py` | killed | `tests/test_labview_format.py::test_both_styles_treat_a_nonfinite_key_alike[labview]` |
| L08 | sort on coerced keys | `_labview_format.py` | killed | `tests/test_labview_format.py::test_both_styles_sort_on_the_original_keys[labview]` |
| P01 | wrong token becomes -0.0 | `_parse.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvjson._parse]` |
| P02 | negative zero collapsed to int | `_parse.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvjson._parse]` |
| P03 | overflow kept under null | `_parse.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvjson._parse]` |
| P04 | overflow accepted under reject | `_parse.py` | killed | `tests/test_robustness.py::test_numbers_that_overflow_a_double_follow_the_policy` |
| P05 | has_nonfinite skips tuples | `_parse.py` | killed | `tests/test_docs.py::test_every_pycon_example_runs[GUIDE.md]` |
| P06 | null policy rejects tokens | `_parse.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvjson._parse]` |
| P07 | RecursionError escapes loads | `_parse.py` | killed | `tests/test_parse.py::test_loads_reports_excessive_nesting_as_lvjson_error` |
| P08 | dict keys searched instead of values | `_parse.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvjson._parse]` |
| T01 | no right word boundary | `_tokens.py` | killed | `tests/test_tokens.py::test_expand_inf_ignores_words_that_only_start_with_inf` |
| T02 | no left word boundary | `_tokens.py` | killed | `tests/test_tokens.py::test_expand_inf_ignores_words_that_only_start_with_inf` |
| T03 | report order changed | `_tokens.py` | killed | `tests/test_cli.py::test_check_lists_tokens_and_strict_fails` |
| T04 | unclosed string not skipped | `_tokens.py` | killed | `tests/test_tokens.py::test_an_unclosed_string_is_skipped_to_the_end` |
| T05 | short spelling INF | `_tokens.py` | killed | `tests/test_cli_robust.py::test_dash_output_means_standard_output` |
| T06 | respell touches every token | `_tokens.py` | killed | `tests/test_cli.py::test_to_portable_reads_stdin_and_defaults_to_null` |
| S01 | compact output with spaces | `_serialize.py` | killed | `tests/test_cli.py::test_to_portable_reads_stdin_and_defaults_to_null` |
| S02 | reject check on wrong policy | `_serialize.py` | killed | `tests/test_cli.py::test_to_portable_reads_stdin_and_defaults_to_null` |
| S03 | null policy skips tuples | `_serialize.py` | survived, then killed | `tests/test_robustness.py::test_tuples_follow_the_policy_like_lists` |
| S04 | portable uses labview digits | `_serialize.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvjson._serialize]` |
| S05 | Inf spelling ignored in shortest style | `_serialize.py` | killed | `tests/test_cli_robust.py::test_dash_output_means_standard_output` |
| S06 | shortest style escapes non-ASCII | `_serialize.py` | killed | `tests/test_cli.py::test_stdin_is_decoded_as_utf8_whatever_the_console_encoding` |
| S07 | unserialisable object gives LVJSONError | `_serialize.py` | killed | `tests/test_labview_format.py::test_both_styles_sort_on_the_original_keys[shortest]` |
| Y01 | indent -1 accepted | `_policy.py` | killed | `tests/test_robustness.py::test_indent_must_be_a_non_negative_int` (now `test_indent_must_be_an_int_from_0_to_1024`) |
| Y02 | bool accepted as indent | `_policy.py` | killed | `tests/test_robustness.py::test_indent_must_be_a_non_negative_int` (now `test_indent_must_be_an_int_from_0_to_1024`) |
| Y03 | str subclass compared with its own __eq__ | `_policy.py` | survived, then killed | `tests/test_robustness.py::test_an_option_that_lies_about_equality_is_refused_by_its_text` |
| X01 | values and type names quoted up to 400 characters (`_LIMIT`) | `_text.py` | killed | `tests/test_robustness.py::test_option_errors_quote_at_most_forty_characters` |
| X02 | BOM kept in str input | `_text.py` | killed | `tests/test_parse.py::test_loads_tolerates_a_byte_order_mark_in_str_input` |
| X03 | BOM kept in bytes input | `_text.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvjson._text]` |
| X04 | offset off by one | `_text.py` | killed | `tests/test_robustness.py::test_undecodable_bytes_name_the_offset_not_the_content[loads]` |
| X05 | type names not cut | `_text.py` | killed | `tests/test_robustness.py::test_long_type_names_are_cut_in_messages` |
| C01 | to-portable default keeps tokens | `_cli.py` | killed | `tests/test_cli.py::test_to_portable_reads_stdin_and_defaults_to_null` |
| C02 | closed output exits 0 | `_cli.py` | killed | `tests/test_cli_robust.py::test_a_reader_that_went_away_gives_exit_1_and_no_message` |
| C03 | interrupt exits 1 | `_cli.py` | killed | `tests/test_cli_robust.py::test_an_interrupt_while_reading_exits_130` |
| C04 | --strict never fails | `_cli.py` | killed | `tests/test_cli.py::test_check_lists_tokens_and_strict_fails` |
| C05 | overflows not counted | `_cli.py` | killed | `tests/test_cli.py::test_check_flags_numbers_that_overflow_to_infinity` |
| C06 | output file gets a newline | `_cli_io.py` | killed | `tests/test_cli.py::test_output_file_is_utf8_without_a_trailing_newline` |
| C07 | messages cut at 2000 | `_cli_io.py` | killed | `tests/test_cli_robust.py::test_usage_errors_do_not_echo_huge_arguments` |
| C08 | usage errors not cut | `_cli.py` | killed | `tests/test_cli_robust.py::test_usage_errors_do_not_echo_huge_arguments` |
| C09 | stdin named - | `_cli.py` | killed | `tests/test_cli.py::test_check_passes_strict_json_under_strict` |
| C10 | stdout without newline | `_cli_io.py` | killed | `tests/test_cli.py::test_stdin_is_decoded_as_utf8_whatever_the_console_encoding` |

## Packaging and end-to-end (items 8, 10, 14), author run at abd6293

- `python -m build`, `twine check --strict`: both PASSED.
- Wheel: the eleven modules, `py.typed`, LICENSE and metadata. Sdist: `src`, `tests` with the
  LabVIEW captures and the sources manifest, README, GUIDE, CHANGELOG, LICENSE, pyproject and
  the `.gitignore` hatchling adds; no fetched NI or RFC copies, no scripts, no report.
- The wheel in a fresh venv on 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t (every
  supported interpreter available), with the suite run from the extracted sdist with `src` removed (it
  imports the installed wheel and drives its console script): 2087 passed, 5 skipped (the
  sources module) on each.
- A strict consumer (`mypy --strict`) type-checks against the installed wheel on 3.10 and 3.14.
- PyPI 0.3.0 installed, then upgraded in place: tie output, overflow under `null` and `reject`,
  `count_nonfinite(bytes)`, `indent` checks and `has_nonfinite` on a cycle change as CHANGELOG
  1.0.0 says; capture parsing and `to_portable` output are unchanged.

## Independent QA lenses (item 19), first round at 7e0eee4

Each lens is an independent review of the branch against CERT-1.0.md, done by running the
library rather than reading it.

| Lens | Verdict | Findings | Fixed in |
| --- | --- | --- | --- |
| a. API and docs | FAIL (2 medium, 3 low, 3 info) | type names over 40 characters in default-style messages; a huge `indent` raised `OverflowError` (CLI traceback); CLI usage lines over 200 characters; `--indent -1` exit 1 against `--indent x` exit 2; `indent=True`, `LVJSONError.__module__`, option wording and str-subclass reading missing from the upgrade notes | ea43eb8 |
| b. Correctness and ground truth | PASS (1 low, 1 info) | 2,811,774 doubles against its own `%.20g` and the C runtime, 0 mismatches; four fresh LabVIEW runs (12 new ties, all away from zero); NI and RFC statements confirmed; 200,000 `to_portable` documents RFC-valid. Low: an escaped lone surrogate was written back raw, so output could not be encoded as UTF-8. Info: the capture script left LabVIEW running after `Quit` | 3a0dc9e |
| c. Adversarial and robustness | FAIL (2 medium, 2 low) | about 2,000,000 fuzz calls with no other exception, no hang, all scaling linear, threads with altered decimal contexts clean. Found: a non-finite key's `repr` was quoted unbounded (or its exception escaped); huge `indent`; long type names in default-style messages; `reject` bypassed in labview style by a container that changes between scans | ea43eb8, a2f0344 |
| d. Packaging and real e2e | FAIL (1 medium, 1 low, 1 info) | archives, metadata, six interpreters (2090 passed, 5 skipped each), 624 subprocess CLI cases, sabotage caught, 0.3.0 upgrade matches CHANGELOG. Found the same two message-length promises as lens a | ea43eb8 |
| e. Contract strength (blind) | FAIL | 89 mutations: 78 killed, 1 equivalent, 10 survivors (bytearray decoding, non-ASCII keys in labview style, `round_trip` pass-through, `to_labview` default, CLI `-`, `.` token boundaries, sorted option list, `emit` flush, message cut on user errors) | 97a9c7c |

Decisions on these findings: `indent` is limited to 0 to 1024 (a documented `ValueError`
outside it, a usage error on the command line); every message word longer than 40 characters
is cut; a lone surrogate is written as its `\uXXXX` escape in both number styles, as `json`
does with `ensure_ascii`; the labview encoder checks the non-finite policy again for each value.

## Later QA rounds (item 19)

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a | 2 (new reviewer) | 7857de8 | PASS | all seven earlier findings fixed; README 11/11, GUIDE 18/18 and module doctests, six command transcripts through the installed script, a strict consumer of every public name, 57 differential cases against PyPI 0.3.0 all listed in CHANGELOG. Low: the `dumps` docstring and `--indent` help did not state the 0 to 1024 range; fixed |
| b | 2 (new reviewer) | 7857de8 | PASS | lone surrogates written as escapes in both styles, capture script now refuses a running LabVIEW and closes only its own; 600,028 doubles (120,000 exact ties) against its own oracle, 0 mismatches; all captures reproduced byte for byte; 120,000 documents against `json.loads` and its own RFC 8259 validator, 0 differences. Info: adjacent high and low surrogates in a `str` read back as one character, now stated in the guide |
| c | 2 (new reviewer) | 7857de8 | FAIL | the four earlier findings fixed; about 1.08 million fuzz cases, 219 scaling pairs (all linear), threads with altered decimal contexts clean. New: a raising `__repr__` could still escape in the shortest style (on 3.14 `json` calls `repr(key)` for its error note; a dict subclass could hide a key or value from the policy scan); `indent` times depth output growth. Fixed in 9315b96 and 78cc79c: scans read `items()`, a failure of the value's own code becomes a chained `TypeError`, the growth is documented and the command line reports running out of memory |
| d | 2 (new reviewer) | 7857de8 | PASS | both earlier findings fixed; archives and metadata, six interpreters (2118 passed, 5 skipped each), 55 subprocess checks per interpreter including a real interrupt (exit 130), six of seven sabotages caught, 0.3.0 upgrade matches CHANGELOG. Low: no test guarded the 200-character line against messages of many short words; added |
| e | 2 (new reviewer, blind) | 7857de8 | FAIL | the ten earlier survivors killed; 85 new mutations: 66 killed, 1 equivalent (`Infinity|Inf` order), 18 survivors (exact message bounds, nested and tuple-held and infinite non-finite keys, an `int` subclass as `indent`, CLI `--indent 0`, word cutting in usage errors, a closed stream without a buffer, the circular message, two hangs only a timeout caught). Contracts added in `tests/test_contract_bounds.py` (9315b96, 78cc79c); each survivor re-applied and killed by a named test |

## Independent reviewer (item 16)

| Review | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- |
| 1 | 7857de8 | FAIL | items 1 to 5, 7 to 15 PASS, 17 ready; 22 table mutations re-applied (20 killed by the named test, C09 by another, X01 survived at that head), 27 of its own (17 killed, 2 equivalent, 8 survived). Survivors: nested non-finite keys, `--indent 0`, the 200 and 40 character edges and a 203-character error line (all already covered by contracts added after that head), labview-style `int` keys written through `repr`, more than one leading byte order mark accepted. Also: `tests/test_robustness.py` over 200 lines, stale names and counts in this report, process wording. Fixed: `int` key and byte order mark contracts, the test file split (and every test file now held to 200 lines by `test_contract`), the report corrected |
