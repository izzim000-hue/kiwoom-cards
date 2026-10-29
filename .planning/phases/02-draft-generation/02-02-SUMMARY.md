---
phase: 02-draft-generation
plan: 02
subsystem: draft-pipeline
tags: [number-trace, check, numscan, spec-loader, v1-compat, stdlib, unittest]
status: complete

requires:
  - phase: 02-draft-generation
    provides: "figures registry, calc, expand with per-number ledger and basis_items (Plan 01)"
provides:
  - "tools/reelkit/numscan.py: figure/structure number scanner (ranges, compound 억/만, dates, counting words, constant phrases)"
  - "tools/reelkit/check.py: check_spec / legacy_report, CheckReport.to_json (check.json), error and warning kinds"
  - "tools/draft.py check SPEC [--out] [--registry] [--date] [--strict] [--legacy]"
  - "tools/reelkit/spec.py: optional v2 field validation and refusal of unexpanded sources, v1 load unchanged"
affects: [02-03 caption/series, 02-04 skill, 03 checklist (consumes check.json)]

actuals:
  tokens: 31000
  tasks: 3
  commits: 4
plan_head_before: e8af98385632c50f60dc52a5c9fe78d82e3a1a33
plan_head_after: 9bcd2ef0ea84a96ef48596e0e3a463fcbe1ee6f6

tech-stack:
  added: []
  patterns:
    - "Ledger spans are masked with a same-length placeholder character, then numscan finds any figure token left over; positions stay stable so tokens come back in text order"
    - "Errors (exit 1) vs warnings (exit 3 only under --strict) vs needs_check (listed, never blocking)"
    - "Optional fields validated only when present; load_spec returns the parsed dict untouched"

key-files:
  created:
    - tools/reelkit/numscan.py
    - tools/reelkit/check.py
    - tools/tests/test_numscan.py
    - tools/tests/test_check.py
  modified:
    - tools/draft.py
    - tools/reelkit/spec.py
    - tools/tests/test_spec.py

key-decisions:
  - "A ledger mismatch leaves the number unmasked, so a hand-edited number yields both LEDGER_MISMATCH and UNREGISTERED at the same line (more informative than one)"
  - "A 발의 figure always lands in needs_check (reason 발의 수치 when it is 확인, 미확인 수치 otherwise) so a proposed-law line is never silently clean"
  - "UNREGISTERED hint text is printed by the CLI after the issue line, not stored in the issue, so check.json keeps the contracted issue shape"
  - "legacy mode never loads the registry and its check.json carries registry.path null"

patterns-established:
  - "Issue line format scene N line M: KIND (detail) \"text\" shared with LayoutWarning"
  - "House-pattern constants live in check.py with a comment citing the research measurements; LINE_MAX is a coarse pre-render signal and reel.py --layout new --strict stays the wrap authority"

requirements-completed: [DRAFT-03, DRAFT-06, DRAFT-01]

coverage:
  - id: C1
    description: "Expanded tax draft checks clean (0 errors, 0 warnings under --strict) and lists exactly scene 3 line 2/3 and scene 4 line 2/3 as needs_check"
    requirement: DRAFT-03
    verification:
      - kind: unit
        ref: "tools/tests/test_check.py#CleanDraft"
        status: pass
      - kind: integration
        ref: "draft.py expand + check --out + check --strict shell gates (Task 1, Task 2)"
        status: pass
  - id: C2
    description: "Hand-typed number exits 1 naming scene, line and number; PROPOSED_AS_FACT, REPEALED, UNKNOWN_FIG, LEDGER_MISMATCH, NOT_EXPANDED, MARKUP, PLACEHOLDER errors"
    requirement: DRAFT-03
    verification:
      - kind: unit
        ref: "tools/tests/test_check.py#Failures,StatusRules,MarkupAndPlaceholder"
        status: pass
  - id: C3
    description: "House-pattern structure and APPROX/INPUT_SHADOWS_FIG/EXPIRED/LOCAL_TAX_NOTE warnings; --strict exits 3"
    requirement: DRAFT-01
    verification:
      - kind: unit
        ref: "tools/tests/test_check.py#Warnings,HousePattern,CliModes"
        status: pass
  - id: C4
    description: "Number classification cases and corpus counts (tax-deduction 11 figure tokens, ebook-event 0, circled numerals structure)"
    requirement: DRAFT-03
    verification:
      - kind: unit
        ref: "tools/tests/test_numscan.py"
        status: pass
  - id: C5
    description: "Published 10 specs load unchanged; optional fields validated only when present; unexpanded source refused by load_spec and reel.py (exit 1, no MP4)"
    requirement: DRAFT-06
    verification:
      - kind: unit
        ref: "tools/tests/test_spec.py#CommittedSpecs,OptionalFieldsLoad,OptionalFieldsErrors,UnexpandedSource"
        status: pass
      - kind: integration
        ref: "reel.py on draft-tax.src.json exits 1 with draft.py expand hint; git diff HEAD -- 2026/reels/specs empty"
        status: pass
---

# Phase 2 Plan 02: Number trace check and v2 spec loader Summary

**`draft.py check` now proves every number in an expanded draft traces to the registry, a labelled input or a derivation, stops hand-typed numbers and 발의/폐지 misuse with the scene and line, lists 미확인 lines as 확인 필요 without blocking, and the spec loader reads the new optional fields while the 10 published v1 specs load exactly as before.**

## Performance

- **Tasks:** 3 of 3 (Task 1 tracer, Task 2 RED then GREEN, Task 3)
- **Commits:** 4 (measured from the plan ledger)
- **Tests added:** numscan 15, check 48 (36 new beyond the tracer's 12), spec 14 new (32 total); all passing. Neighbouring suites (expand, figures, calc_repro, layout, timeline) re-run green.

## Accomplishments

- Tracer: `draft.py expand` then `draft.py check --out` on the tax fixture gives exit 0, no errors, needs_check wheres exactly scene 3 line 2, scene 3 line 3, scene 4 line 2, scene 4 line 3, summary `오류 0건 · 경고 0건 · 확인 필요 4줄` (no 통과). The 7원 hand-typed copy exits 1 with `scene 6 line 2: UNREGISTERED (7원) ...` on stderr and no traceback; check.json is written even then.
- numscan classifies the corpus: tax-deduction has 11 figure tokens, ebook-event 0, every circled numeral is structure; compound money (3억 7,200만 원 = 372000000), ranges (55~79세), U+2212 negatives, birth years and constant phrases behave per the research rules.
- Status and markup rules: PROPOSED_AS_FACT (marker on the line or in basis), REPEALED, MARKUP (every disallowed `<`, all collected), PLACEHOLDER; warnings APPROX, INPUT_SHADOWS_FIG, EXPIRED (`--date`), LOCAL_TAX_NOTE, and house-pattern SCENES, DURATION, LINE_LONG, TOP_LONG, LINES, NO_CTA, NO_CAUTION, NO_EMPH. The expanded tax fixture has no warnings, so `check --strict` exits 0.
- `check --legacy` on all 10 published specs exits 0 and prints `check(legacy): 등록부 없음 N개 — 게시된 v1 원고는 고치지 않음` (N = 10, 9, 15, 11, 14, 0, 16, 6, 10, 11 in file order); nothing under `2026/` changed.
- `load_spec` validates `version`, `series`, `inputs`, `figures`, `basis_items`, `motion` only when present, refuses `{{`/`}}` with the `draft.py expand` hint, and returns the parsed dict untouched. CommittedSpecs is unchanged and passes; stripping the optional keys from the expanded fixture gives the published spec's states, duration and cover_ms.

## Task Commits

1. Task 1 (tracer): `8b2f1ed` feat(02-02): tracer — draft.py check traces numbers to the ledger
2. Task 2 RED: `2714e17` test(02-02): failing status-rule, markup, warning, house-pattern and --legacy checks (23 failures and 1 error from missing behavior; numscan cases already passed because numscan shipped with the tracer)
3. Task 2 GREEN: `cb0a576` feat(02-02): status rules, markup allowlist, warnings, house-pattern checks, --legacy/--strict/--date
4. Task 3: `9bcd2ef` feat(02-02): spec loader validates optional v2 fields and refuses unexpanded sources

## Decisions Made

See key-decisions. House-pattern constants follow the plan (6-8 scenes, 21-27 s, line 22, top 21, 2-5 lines per scene).

## Deviations from Plan

### Auto-fixed Issues

None needed beyond test expectations: my first version of the "changed text with ledger kept" test asserted a single LEDGER_MISMATCH, but the changed number is also (correctly) reported as UNREGISTERED; I changed the test to assert LEDGER_MISMATCH is present rather than narrowing the checker.

### Additions beyond the plan text (Rule 2)

- A 발의 figure is added to needs_check even when its registry status is 확인 (reason `발의 수치`), so a proposed-law line is never reported as clean.
- LEDGER_MISMATCH is also raised for ledger entries whose `where` points at a field that does not exist, and for non-integer or overlapping spans.
- `--date` rejects non-`YYYY-MM-DD` and impossible dates as an input error (exit 1).

Task 3 was committed once (tests and implementation together) rather than as separate RED/GREEN commits; the failing run (19 failures) was observed before implementing.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. No new network endpoints or auth paths; `check` reads the paths it is given and writes only `--out`.

## Self-Check: PASSED

- Files: tools/reelkit/numscan.py, tools/reelkit/check.py, tools/tests/test_numscan.py, tools/tests/test_check.py present; tools/draft.py, tools/reelkit/spec.py, tools/tests/test_spec.py modified.
- Commits 8b2f1ed, 2714e17, cb0a576, 9bcd2ef are ancestors of HEAD.
- `git status --porcelain -- 2026` is empty and `git diff --quiet HEAD -- 2026/reels/specs` holds; STATE.md and ROADMAP.md untouched.
