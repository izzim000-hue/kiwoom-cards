---
phase: 04-motion-bgm
plan: 02
subsystem: render
tags: [countup, dwell, motion, review, bundle]
status: complete

requires:
  - phase: 04-motion-bgm
    provides: basic motion render path, schedule with countup settle term, none baseline guard (Plan 01)
provides:
  - "`{{ref|fmt|up}}` source syntax (scene lines only) -> ledger `countup: true`"
  - count-up DOM (fixed-width `.rk-cu` spans), per-frame strings from calc.FORMATS, final frame = ledger text
  - COUNTUP_WRAP, DWELL_SHORT, DWELL_LONG render warnings (bundle exit 3, approvable)
  - basic-aware DURATION house-pattern check and MOTION check error
  - review.md motion line and count-up check item; bundle.json `motion` / `countups`
affects: [04-03 BGM and phase gate (bundles draft-pension-motion.src.json)]

actuals:
  tokens: 8200
  tasks: 3
  commits: 3
plan_head_before: e846ffa6752cbe8312bf4b3455c608edb41cd893
plan_head_after: ec0fda4ff99347c2da48b5c0473eae8f9ab72b24

tech-stack:
  added: []
  patterns:
    - count-up box width fixed from the measured final text before any animation exists
    - frame strings set with textContent only
    - scene-level LayoutWarning uses line "" and prints without a line part

key-files:
  created:
    - tools/tests/fixtures/draft-pension-motion.src.json
  modified:
    - tools/reelkit/expand.py
    - tools/reelkit/motion.py
    - tools/reelkit/render.py
    - tools/reelkit/layout.py
    - tools/reelkit/check.py
    - tools/reelkit/review.py
    - tools/reelkit/bundle.py
    - tools/tests/test_motion.py
    - tools/tests/test_expand.py
    - tools/tests/test_bundle.py

key-decisions:
  - "Count start value is 0 only; a configurable start is a later option (documented for Plan 03)"
  - "countup_entries is strict: `countup` must be exactly true, the entry must sit on an existing scene line with a matching text span, a known format and a finite value, and may not overlap another count-up"
  - "check._house_pattern now takes (spec, warn, err) so an unknown motion value becomes a MOTION error instead of a crash"
  - "bundle.json motion/countups are null when the run stopped before render"

requirements-completed: [MOTN-03, MOTN-05]

duration: not recorded
completed: 2026-10-29
---

# Phase 4 Plan 02: Count-up and dwell warnings Summary

**`{{ref|fmt|up}}` makes a number count up from 0 over 0.8 s in a fixed-width box and land on the ledger text exactly; basic scenes get character-count dwell times with DWELL_SHORT/DWELL_LONG warnings, and review.md / bundle.json record the motion mode.**

## What was built

- **Task 1 (tracer, e0c5b48):** `PLACEHOLDER` takes an optional `|up`; only scene `line` fields accept it (top and basis raise ExpandError naming the field) and only that ledger entry gains `"countup": true`, so sources without `up` expand to the same ledger keys as before. `motion.py` gained `cu_text` (p >= 1 returns the ledger text object itself; otherwise ease-out cubic through `calc.FORMATS`), `countup_entries` (validates where/start/end/text/fmt/value/overlap, raises SpecError before Chromium), `countup_texts`, and count-up line markup. `BUILD_JS` fixes every `.rk-cu` to `inline-block` with its measured final width before any animation exists and returns the motion-DOM line count of each count-up line; `SEEK_JS` writes frame strings with `textContent`. `render._render_motion` compares those counts with the static layout and emits COUNTUP_WRAP, and sets `RenderResult.countups`.
- **Task 2 (c82ecbc):** `motion.dwell_warnings` (DWELL_SHORT under 1.5 s, DWELL_LONG over 6.0 s, scene-level, no clamping); `LayoutWarning.__str__` drops the ` line X` part only when `line == ""`; render appends dwell warnings in basic only (none never computes them); `check._house_pattern` measures the schedule total for basic specs and the existing timeline total for none, and reports an unknown `motion` as a `MOTION` error. This resolves the 04-01 note that DURATION still used the `none` total.
- **Task 3 (ec0fda4):** review.md `## 2` shows `- 모션: basic — ... 카운트업 N곳 (중간 숫자는 연출, 최종값만 장부 값)` or `- 모션: none (기존 형식)`; the checklist gets a count-up line when N > 0; bundle.json records `motion` and `countups`. New fixture `draft-pension-motion.src.json` (pension source + `"motion": "basic"` + `|up` on the two scene-5 numbers) now drives `BundleBasic`.

## Verification

- `test_motion.py`: 60 tests OK (about 349 s), including NoneUnchanged, CountUpUnit, CountUp (DOM, one width/left/line height over the count window, final line text equals the script line, `<b>x</b>` stays literal text), CountUpRender (`reel.py --layout new` exit 0, `spec: PASS 9/9`, countups == 2, forged ledger exits 1 with no file), Dwell (published ten: 21.5 to 26.7 s, no warnings; short/long scenes; basic render returns DWELL_SHORT and `--strict` exits 3), CheckDuration, BundleBasic with count-up (exit 0, review.md and bundle.json records).
- `test_expand.py`: 32 OK. `test_check.py`: 74 OK. `test_layout.py`: 25 OK. `test_bundle.py`: 28 OK. `test_approve.py`: 34 OK.
- `DWELL_MIN`, `DWELL_MAX`, `READ_BASE`, `READ_CPS` are each assigned once, in motion.py only.
- Golden was not re-run (not required by this plan's verify); the `none` guard (`golden/none-new.json`) still matches via NoneUnchanged; no files under `2026/` or `.claude/settings.json` were touched.

## Deviations from Plan

None - plan executed exactly as written.

Notes (not deviations):
- The plan's DOM test names "scenes 5 and 7"; scene 7 has no figures in the pension source, so the count-up tests mark the two scene-5 numbers (c_low, c_high), which matches the `countups == 2` expectation.
- Tests for Task 1 were written together with the implementation and passed on the first full run; Task 2 tests were written first and failed before `dwell_warnings` existed.
- `actuals.tokens` is chars/4 over added diff lines (about 32,981 chars); it is not a harness token count.

## Known Stubs

None.

## Threat Flags

None. New surface is covered by T-04-06 (countup ledger validation before Chromium), T-04-07 (final frame equals ledger text, review.md note and checklist item), and T-04-08 (textContent only, escaped ledger text in spans).

## Self-Check: PASSED

- FOUND: tools/reelkit/motion.py, tools/tests/fixtures/draft-pension-motion.src.json, tools/tests/test_motion.py
- FOUND commits: e0c5b48, c82ecbc, ec0fda4 (ancestors of HEAD)
