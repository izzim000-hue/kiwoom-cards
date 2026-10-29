---
phase: 02-draft-generation
plan: 01
subsystem: draft-pipeline
tags: [figure-registry, decimal, placeholder-expansion, stdlib, unittest]
status: complete

requires:
  - phase: 01-render-foundation
    provides: "reel.py --layout new renderer, spec.py v1 loader, constants.TOOLS_DIR, unittest conventions"
provides:
  - "tools/data/figures.json: committed figure registry (schema 1), 30 ids, all 미확인, 3 unsourced figures listed apart"
  - "tools/reelkit/figures.py: loader/validator, get_figure with id suggestions, add/confirm/save"
  - "tools/reelkit/calc.py: 13 Decimal derive functions and 14 display formats (ROUND_HALF_UP)"
  - "tools/reelkit/expand.py: {{name|fmt}} expansion into a v2 spec with a per-number ledger and basis_items"
  - "tools/draft.py: expand and figures list/show/add/confirm"
affects: [02-02 check, 02-03 caption/series, 02-04 skill, 03 checklist]

actuals:
  tokens: 23400
  tasks: 3
  commits: 4
plan_head_before: 17ddcaac0dcc7e6f0802cc9a0179712f173b577a
plan_head_after: b548c8c059e6acdfc4d85f662d7d56a3a47741e8

tech-stack:
  added: []
  patterns:
    - "Numbers enter scene text only through {{ref|fmt}} placeholders resolved from the registry, labelled inputs, or calc derive; the ledger records each one"
    - "Decimal with prec 34 and ROUND_HALF_UP applied once at display time; no binary floats and no built-in rounding"
    - "Format callables return (text, shown) so exactness (shown == value) is recorded in the ledger"
    - "Atomic writes via temp file in the same directory plus os.replace"

key-files:
  created:
    - tools/data/figures.json
    - tools/reelkit/figures.py
    - tools/reelkit/calc.py
    - tools/reelkit/expand.py
    - tools/draft.py
    - tools/tests/fixtures/draft-tax.src.json
    - tools/tests/test_expand.py
    - tools/tests/test_calc_repro.py
    - tools/tests/test_figures.py
  modified: []

key-decisions:
  - "Registry entries use the D-01 field set exactly as written in the plan; unknown or missing entry keys are rejected by the loader"
  - "A derived figure's ledger sources are the transitive fig./inputs. leaves; basis_items lists each registry id once in first-use order"
  - "AI-name detection is a case-insensitive pattern (claude, anthropic, ai, assistant, bot, llm, gpt as whole tokens) shared by the validator and confirm"
  - "months_between_ages rejects an end age that is not greater than the start age (extra guard beyond the plan)"

patterns-established:
  - "Test convention: stdlib unittest, TOOLS on sys.path, CLI through subprocess with sys.executable, temp dirs removed via addCleanup"
  - "Error style: Korean messages naming the id/field/where; CLI prefixes 초안 오류 / 등록부 오류 / 환경 오류 and never prints a traceback for input errors"

requirements-completed: [DRAFT-03]

coverage:
  - id: D1
    description: "Placeholder source expands to the published tax-deduction scenes and basis character for character, with an 11-entry ledger and 6 basis_items"
    requirement: DRAFT-03
    verification:
      - kind: unit
        ref: "tools/tests/test_expand.py#TaxDeductionReproduction"
        status: pass
      - kind: integration
        ref: "draft.py expand fixture + reel.py --layout new prints duration=26.1s cover_ms=1250"
        status: pass
  - id: D2
    description: "Every derived figure of the published reels reproduced by calc (36-row table, 387.5 -> 388 tie)"
    requirement: DRAFT-03
    verification:
      - kind: unit
        ref: "tools/tests/test_calc_repro.py"
        status: pass
  - id: D3
    description: "Registry of 30 ids, all 미확인; add forces 미확인; confirm is human-only and refuses empty/Claude/AI names"
    requirement: DRAFT-03
    verification:
      - kind: unit
        ref: "tools/tests/test_figures.py"
        status: pass
---

# Phase 2 Plan 01: Figure registry, calculator and placeholder expander Summary

**Numbers in drafts now come only from a committed 30-id registry (all 미확인), labelled scenario inputs, or Decimal HALF_UP derivations, and a placeholder source reproduces the published tax-deduction reel exactly and renders with the unchanged Phase 1 renderer.**

## Performance

- **Tasks:** 3 of 3 (Task 1 tracer, Task 2 with RED/GREEN commits, Task 3)
- **Commits:** 4 (measured from the plan ledger)
- **Tests added:** 59 (test_expand 18, test_calc_repro 15, test_figures 26), all passing

## Accomplishments

- Tracer path proven end to end: `draft.py expand tools/tests/fixtures/draft-tax.src.json OUT` gives `scenes` and `basis` equal to `2026/reels/specs/2026-10-26-tax-deduction.json`, `version` 2, 11 ledger entries whose `field[start:end] == text`, all exact, and 6 `basis_items`. `reel.py OUT t.mp4 --layout new` exits 0 and prints exactly `duration=26.1s cover_ms=1250` (3 expected WRAP warnings from legacy-sized text, run without `--strict`).
- calc reproduces all 36 published derived strings (6.6만 through 3억 7,200만 원, including 72/151/329만, 7,712만 and 388만 from 387.5) with Decimal only. `calc.py` has no `float(` or `round(` on non-comment lines.
- Registry holds the 30 research-documented ids, every entry `미확인` with null `checked_on`/`checked_by`; 남자 55.3·여자 51.1세, 60세 여성 약 88세 and 최고세율 45% sit only in `unsourced`.
- `figures add` has no verification option and always writes `미확인`; `confirm` needs a checker name and refuses empty, Claude and AI names; the loader rejects `확인` without checker/date and `발의` entries whose source name lacks 발의/개정안/정부안.

## Task Commits

1. Task 1 (tracer): `596b2bb` feat(02-01): registry -> calc -> placeholder expand -> v2 spec reproducing tax-deduction
2. Task 2 RED: `32d652c` test(02-01): failing published derived-figure reproduction table (failed with KeyError on the missing functions/formats, i.e. missing behavior)
3. Task 2 GREEN: `3d49ccd` feat(02-01): complete calc functions and display formats
4. Task 3: `b548c8c` feat(02-01): seed 30-id registry and `draft.py figures` list/show/add/confirm

## Decisions Made

See key-decisions above. `confirm` was exercised only on temp copies; the committed registry was never changed by tests (each CLI test asserts the committed bytes are unchanged afterwards).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Edit script replaced from the wrong `FORMATS = {` occurrence**
- **Found during:** Task 2 (GREEN), before any commit
- **Issue:** my scripted edit matched the `FORMATS = {` text inside the module docstring and truncated calc.py (SyntaxError)
- **Fix:** restored the file from HEAD and reapplied the changes with exact-match edits
- **Files modified:** tools/reelkit/calc.py (never committed in the broken state)

### Additions beyond the plan text (Rule 2)

- Non-finite values (NaN, Infinity) rejected for registry values, input values, and calc arguments (threat T-02-02).
- `months_between_ages` requires an end age greater than the start age.
- `write_spec` creates missing parent directories so drafts can be written straight into new draft folders.

None of these change the plan's contracts.

## Issues Encountered

None beyond the edit slip above. The Task 1 render gate logged the 3 WRAP warnings the plan predicted.

## Known Stubs

None. Candidate-source URLs and article names in the registry are research leads for the human checker, not wired data.

## Open items for the human checker (D-02)

Every registry value is `미확인`. Items the research flagged for attention: `pension_credit_income_threshold` (4,500만 vs old 4,000만), `nps_avg_old_age_all` (69.6~69.8만 vs the 70만 used before), `pension_credit_young_gov_proposal` (start date 2027-01-01 vs 2026-01), `sp500_2008_return` (-37.0 total return vs -36.8 SPY), `cpi_yoy_2026_09` (base-year revision due 2026-12). Article numbers for the basic tax rates, local income tax and withholding rate are unconfirmed estimates noted in `notes`.

## Threat Flags

None. No new network endpoints or auth paths; `draft.py` reads and writes only the paths it is given.

## Self-Check: PASSED

- Files: tools/data/figures.json, tools/draft.py, tools/reelkit/{figures,calc,expand}.py, tools/tests/fixtures/draft-tax.src.json, tools/tests/test_{expand,calc_repro,figures}.py all present.
- Commits 596b2bb, 32d652c, 3d49ccd, b548c8c are ancestors of HEAD.
- `git status --porcelain -- 2026` is empty; STATE.md and ROADMAP.md untouched.
