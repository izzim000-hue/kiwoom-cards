---
phase: 02-draft-generation
plan: 03
subsystem: draft-pipeline
tags: [series, caption, hashtags, card-convert, new-number-check, stdlib, unittest]
status: complete

requires:
  - phase: 02-draft-generation
    provides: "expand with ledger, numscan, check_spec/legacy_report, load_spec with series validation (Plans 01-02)"
provides:
  - "expand.py: optional `series` {name, episode 1..10, next}; series_top/next_line; scene 1 top fill and CTA 다음 편 line before the 프로필 링크 line"
  - "tools/reelkit/caption.py + tools/data/caption_config.json: build_caption(spec, src, config) in D-11 order, hashtag/length/number/series checks"
  - "tools/draft.py caption SPEC SRC --out TXT [--config]"
  - "tools/reelkit/convert.py: load_card, card_skeleton, new_number_warnings, dropped_notes"
  - "tools/draft.py convert CARD [--out JSON]; draft.py check --card CARD (NOT_IN_CARD, CARD_NOTE_DROPPED, check.json `card` block)"
  - "fixtures draft-pension.src.json / draft-pension.caption.src.json (series 2, teaser)"
affects: [02-04 skill (caption.src.json, convert skeleton, series field), 03 checklist (consumes check.json card block, caption_config status)]

actuals:
  tokens: 36000
  tasks: 2
  commits: 2
plan_head_before: 0d335f96cf44f640ed9ae655daf735855dcee339
plan_head_after: 396e8b041211849282913e4c35535623f868e806

tech-stack:
  added: []
  patterns:
    - "One formatter pair (series_top, next_line) in expand.py is imported by caption.py so scene text and caption cannot drift"
    - "Series is applied to the working scenes before placeholder resolution so ledger line numbers are final"
    - "convert.py has its own field iterator and does not import check.py; check.py imports convert (no cycle)"

key-files:
  created:
    - tools/reelkit/caption.py
    - tools/reelkit/convert.py
    - tools/data/caption_config.json
    - tools/tests/fixtures/draft-pension.src.json
    - tools/tests/fixtures/draft-pension.caption.src.json
    - tools/tests/test_caption.py
    - tools/tests/test_convert.py
  modified:
    - tools/reelkit/expand.py
    - tools/reelkit/check.py
    - tools/draft.py
    - tools/tests/test_expand.py

key-decisions:
  - "Caption source cannot carry series/episode/next; they come only from the spec series (D-10), and a spec whose scene 1 top or CTA teaser disagrees with its series is a CaptionError"
  - "Caption numbers are matched by (cls, value) against figure tokens of the spec tops, lines and basis, so 600만 원 style rewrites of the same quantity pass and invented numbers fail"
  - "Brand hashtags stay an empty list in config; max_hashtags above 5 is rejected at config load (D-12 hard cap)"
  - "check --legacy --card exits 0 by default and 3 under --strict when card warnings exist (legacy mode otherwise ignores --strict)"
  - "Caution-scene material in the skeleton is the card notes containing 세무사/보장/손실/권유/예시/가정, copied verbatim, never reworded"

patterns-established:
  - "Card comparison warnings reuse CheckIssue: `scene N line M: NOT_IN_CARD (raw)` and `card N note: CARD_NOTE_DROPPED (note)`"

requirements-completed: [DRAFT-05, DRAFT-04, DRAFT-02]

coverage:
  - id: C1
    description: "One series object lands in scene 1 top (`연말정산 바로 알기 ②`), the CTA scene (`<s>다음 편: ...</s>` right before the 프로필 링크 line) and the caption first line and 다음 편 line"
    requirement: DRAFT-05
    verification:
      - kind: unit
        ref: "tools/tests/test_caption.py#SeriesExpand,BuildCaption"
        status: pass
      - kind: integration
        ref: "Task 1 shell gate: expand, check --strict, caption, series+caption True"
        status: pass
  - id: C2
    description: "Caption in D-11 order with at most 5 hashtags (brand tags counted, empty by default); >5, duplicate, malformed tags and >2,200 chars are errors; <3 topic tags and a long first line warn"
    requirement: DRAFT-04
    verification:
      - kind: unit
        ref: "tools/tests/test_caption.py#BuildCaption,Cli"
        status: pass
  - id: C3
    description: "Caption number not in the spec, caption source setting series values, and spec/series mismatch are errors"
    requirement: DRAFT-04
    verification:
      - kind: unit
        ref: "tools/tests/test_caption.py#BuildCaption"
        status: pass
  - id: C4
    description: "convert returns a reel skeleton (series, roles, material without <br>, notes, source numbers) for all 7 card specs"
    requirement: DRAFT-02
    verification:
      - kind: unit
        ref: "tools/tests/test_convert.py#Skeletons,Cli"
        status: pass
      - kind: integration
        ref: "Task 2 shell gate: skeleton True, roles hook..caution,cta"
        status: pass
  - id: C5
    description: "check --card: NOT_IN_CARD set over the 7 published pairs is exactly the 7 known new numbers; CARD_NOTE_DROPPED lists the 4,500만 원 note and not the carried notes; 2026/ unchanged"
    requirement: DRAFT-02
    verification:
      - kind: unit
        ref: "tools/tests/test_convert.py#Comparison,Cli"
        status: pass
      - kind: integration
        ref: "Task 2 shell gate: check --legacy --card exit 0, stderr has 0원 and 4,500만 원 lines, git status -- 2026 empty"
        status: pass
---

# Phase 2 Plan 03: Series, caption and card conversion Summary

**One `series` field now writes the series name, episode and next-episode teaser into scene 1, the CTA scene and the caption; `draft.py caption` assembles the post text in the agreed order with at most 5 hashtags; `draft.py convert` turns a card-news spec into a reel skeleton, and `check --card` flags every reel number the card never had.**

## Performance

- **Tasks:** 2 of 2 (Task 1 tracer, Task 2)
- **Commits:** 2 task commits (measured from the plan ledger), plus the docs commit for this SUMMARY
- **Tests added:** test_caption 33, test_convert 17; test_expand (18), test_check (48) still pass. The full tools suite (305 tests) was run once in the background after Task 1 and passed; it predates test_convert.

## Accomplishments

- Pension draft (series 2, teaser "IRP 세액공제 개정안") expands, passes `check --strict` with 0 errors and 0 warnings, and the caption reads: first line `연말정산 바로 알기 ② | 연금계좌 세액공제, 한도가 얼마일까?`, three bullets, `근거 · 기준: 900만 원 납입 예시 · 지방소득세 포함 (2026년 10월 기준)`, disclaimer, CTA, `다음 편: IRP 세액공제 개정안`, `#연금저축 #IRP #세액공제 #연말정산`.
- Series validation in expand: scene 1 top empty is filled, an equal value is kept, any other value is an error naming the field; an identical existing teaser is kept once, a different one is an error; episode 11, 0, a bool or a string is an error.
- Convert on the tax card gives roles hook, body x4, conclusion, caution, cta, no `<br>`; the salary-1 card gives series `내 월급의 두 주인 / 1 / 미래 몫부터 떼는 순서` with the teaser and 저장해두고 lines removed from the conclusion.
- `NOT_IN_CARD` over the 7 published pairs is exactly: tax 0원; salary-1 25년; salary-2 4%, 72만, 151만, 329만; salary-4 8만 (7 total). Dropped notes on the tax pair include `종합소득자는 4,500만 원 기준` and exclude the two carried notes.

## Task Commits

1. Task 1 (tracer): `8f7822d` feat(02-03): tracer, one series field feeds scene 1, CTA teaser and caption.txt with <= 5 hashtags
2. Task 2: `396e8b0` feat(02-03): card spec -> reel skeleton (draft.py convert) and check --card NOT_IN_CARD / CARD_NOTE_DROPPED

Task 2 was committed once (tests and implementation together); convert.py was exercised against the 7 pairs before the tests were finalised, and the expected pair set was confirmed there.

## Decisions Made

See key-decisions. The caption disclaimer and CTA wording are drafts exactly as given in the plan (config `status` says so) and avoid 보장/확정/무조건/반드시; `brand_hashtags` is empty and no brand tags were invented.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing test used `series` as its "unknown top-level key" example**
- **Found during:** Task 1 verification (`test_expand.py`)
- **Issue:** `test_unknown_top_level_key` passed `series={"name": "x"}` and expected an unknown-key error; `series` is now an allowed key.
- **Fix:** changed the example key to `motion`, which is still not an allowed source key. The assertion about rejecting unknown keys is unchanged.
- **Files modified:** tools/tests/test_expand.py
- **Commit:** 8f7822d

### Additions beyond the plan text

- `check --legacy --card` returns 3 under `--strict` when card warnings exist (plan: "warnings follow --strict like other warnings"); legacy without a card still ignores `--strict`.
- The legacy summary line gains ` · 카드 대조: 카드에 없는 숫자 N개 · 옮기지 않은 note M개` only when `--card` is given.
- `load_card` also validates `lines`/`emph` as string lists and `note` as string or null, and `check --card` with an unreadable card exits 1 with `초안 오류`.

## Issues Encountered

- A first expand smoke run used an empty `$TMPDIR`, so it wrote a stray file at `/x.json` in the filesystem root. The sandbox blocked my attempt to delete it. It is outside the repo and harmless; please remove `/x.json` manually if desired.

## Known Stubs

None. The caption disclaimer/CTA are intentional draft wording awaiting the Phase 3 owner gate (recorded in `caption_config.json` `status`).

## Threat Flags

None. No new network endpoints or auth paths; new commands read the paths given and write only `--out`. T-02-09/T-02-10/T-02-12 mitigations (caption numbers, markup and tag rejection, ConvertError without traceback) are covered by tests.

## Self-Check: PASSED

- Files present: tools/reelkit/caption.py, tools/reelkit/convert.py, tools/data/caption_config.json, tools/tests/test_caption.py, tools/tests/test_convert.py, both pension fixtures.
- Commits 8f7822d and 396e8b0 are ancestors of HEAD.
- `git status --porcelain -- 2026` is empty; STATE.md and ROADMAP.md untouched.
