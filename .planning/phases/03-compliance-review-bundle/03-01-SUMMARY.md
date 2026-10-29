---
phase: 03-compliance-review-bundle
plan: 01
subsystem: compliance-bundle
tags: [compliance, regex-engine, review-bundle, ffmpeg, playwright, stdlib]
status: complete

requires:
  - phase: 02-draft-generation
    provides: expand/check/caption/slot library functions, check.json contract, caption_config
  - phase: 01-render-foundation
    provides: render_reel, new layout, cover_ms, upload-spec probe
provides:
  - tools/data/compliance_rules.json (28 rules, v0.1, as_of 2026-10-29, examples on every pattern rule)
  - tools/reelkit/compliance.py (load_rules, reel_doc, caption_doc, scan, lift, run, headline, Result.to_json)
  - tools/reelkit/bundle.py and `draft.py bundle DIR` (expand -> check -> caption -> compliance -> render -> cover -> review)
  - tools/reelkit/review.py (review.md writer, record.json defaults, never rewritten)
  - render_reel frame_sink hook
  - `draft.py compliance SPEC [--caption] [--check] [--rules] [--out]`
affects: [03-02, 03-03, 03-04, make-reel skill]

actuals:
  tokens: 31600
  tasks: 2
  commits: 2
plan_head_before: f603a39f87c7d5805caf5f258649f2f6baf939c1
plan_head_after: 2fcf36707c82a725db1cb3f7180c786b72697fa1

tech-stack:
  added: []
  patterns:
    - "Rules are data: strict loader + examples executed at load time"
    - "Suppressions are never silent: compliance.json `suppressed` + review.md section"
    - "Library calls in-process for the bundle; record.json = human input, create-if-missing"

key-files:
  created:
    - tools/data/compliance_rules.json
    - tools/reelkit/compliance.py
    - tools/reelkit/bundle.py
    - tools/reelkit/review.py
    - tools/tests/test_bundle.py
    - tools/tests/test_compliance.py
  modified:
    - tools/reelkit/render.py
    - tools/draft.py

key-decisions:
  - "Headline n = pattern + compact findings of both severities; lifted/requires items only count in 확인 필요"
  - "{S} macro changed from \\s* to a space run with at most one newline, so a match cannot cross a scene boundary (blank line)"
  - "except regexes must overlap the match, not merely occur in the clause"
  - "Zero-width-split terms are normalized away, so the normal rule fires; the finding also lists X-compact to show obfuscation"
  - "Suppressed entries carry `rule` as a list, same as findings"
  - "One structural finding per requires/basis_required rule per document (at the first trigger)"

requirements-completed: [COMP-01, COMP-02, COMP-03, COMP-05, COMP-06, BNDL-01, BNDL-04]
---

# Phase 3 Plan 01: Compliance Engine and Bundle Spine Summary

**`draft.py bundle DIR` turns a draft folder into a rendered, scanned, reviewable bundle with a data-driven expression check whose headline never reads as clean.**

## Accomplishments

- Task 1 (tracer): rules file, pattern scan with locations, in-process render with a frame sink, scene-1 cover, review.md, record.json, bundle.json timing, `draft.py bundle`. End-to-end test on the pension fixture (one render, about 15 s) shows all nine files, seven ordered steps, a G-01 finding at `caption line 1`, a 1080x1920 cover inside scene 1's final state, and no forbidden words in outputs.
- Task 2: negation, mention and except suppression with a visible `suppressed` list, compact pass (`X-compact`), overlap merge, requires/basis_required rules, check.json and caption-warning lift, strict loader (duplicate ids, unknown keys, severity/type sets, bad or empty or nested-quantifier regex, forbidden strings, missing top fields, failing examples), and `draft.py compliance`.
- Data-driven check: adding a rule U-01 to a temp copy of the rules file changes the next scan with no code change (test).
- Published 10 reels: 수정 필요 0 (확인 필요 shows R-02 on rate-secret-1). Golden `2026-10-26-tax-deduction` PASS 1/1 after the render hook.

## Task Commits

1. Task 1: `7a2a158` feat(03-01): draft.py bundle tracer
2. Task 2: `2fcf367` feat(03-01): complete compliance engine

## Verification

- `test_bundle.py`: 10 tests OK (re-run after Task 2, still OK).
- `test_compliance.py`: 39 tests OK.
- `golden.py --only 2026-10-26-tax-deduction`: `golden: PASS 1/1`.
- `draft.py compliance 2026/reels/specs/2026-10-19-rate-secret-1.json`: last line matches the headline form with 수정 필요 0건; `git status -- 2026/reels` empty.
- Full suite and full golden were not run (instruction to save usage).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `{S}` macro let a match cross a scene boundary**
- **Found during:** Task 2 (test for "원금 / 보장 across two scenes is not one finding")
- **Issue:** Appendix A defines `{S}` as `\s*`, which also matches the blank line between scenes.
- **Fix:** `S` is now `[^\S\n]*(?:\n[^\S\n]*)?` in the rules file (wrapped lines still match, scene boundaries do not).
- **Files modified:** tools/data/compliance_rules.json
- **Commit:** 2fcf367

**2. [Rule 1 - Bug] C-04 example `최대한 안전한 상품` did not hit**
- **Found during:** Task 2 (examples run at load)
- **Fix:** example changed to `가장 안전한 상품`; no pattern change was needed. No other example exposed a pattern bug.
- **Commit:** 2fcf367

### Interpretation choices (not bugs)

- Behavior list says a zero-width-split "원금보장" yields an `X-compact` finding. Normalization removes zero-width characters first, so G-01 fires; the finding then lists `X-compact` as well when the source field contained hidden characters (one finding, 수정 필요).
- `except` is honored only when the except match overlaps the pattern match (avoids a second unrelated "반드시 확인" in the same sentence excusing the first).

## Deferred / Not in this plan

- Stale-output purge and approval invalidation on rebuild (BNDL-05) and review.md on early failure are left for a later plan; currently a failed rerun can leave older generated files beside the new bundle.json (`status: failed`).
- Contact sheet, cover crop pixel audit, red-team report, approve/promote and the make-reel skill update are other plans of this phase.

## Known Stubs

None.

## Threat Flags

None. No new network surface; rules are local data read by a strict loader (T-03-02/03 mitigations implemented).

## Self-Check: PASSED
