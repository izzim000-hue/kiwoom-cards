---
phase: 03-compliance-review-bundle
plan: 03
subsystem: review-bundle
tags: [cover-crop-audit, contact-sheet, rebuild, failure-semantics, timing, ffmpeg, stdlib]
status: complete

requires:
  - phase: 03-compliance-review-bundle
    provides: bundle.run_cli spine, render_reel frame_sink, review.write_review, compliance Result (Plan 01)
provides:
  - tools/reelkit/stills.py (crop window constants, ink_rows_outside_crop, cover_crop_warnings, scene_times, contact_sheet)
  - bundle step `scenes` and `<name>-scenes.png` (4 columns, 360x640 tiles, labels 장면 N)
  - purge-at-start rebuild, failure review.md, bundle.final_code, resolve_request, timing_fields
  - render.env_error_message / PLAYWRIGHT_MISSING / playwright_error_types shared by reel.py and the bundle
  - slot --create stamps created.json; bundle.json request/timing fields; review.md section 5
affects: [03-04, make-reel skill]
requirements-completed: [BNDL-02, BNDL-03, BNDL-04, BNDL-05, BNDL-07]

actuals:
  tokens: 31000
  tasks: 3
  commits: 3
plan_head_before: 1ff2f4a19e342b929694ac5737175f07dc9f6c77
plan_head_after: 8e5b019cbd009aa071c12d09b847ceb8d776f557

tech-stack:
  added: []
  patterns:
    - "Crop window lives in one module (stills.py); cover audit decodes the PNG through ffmpeg rawvideo, no Pillow"
    - "Purge list is derived from the validated folder name only; human files (src, skeleton, record, created) are never in it"
    - "Failed run writes review.md + bundle.json (failed_step) in a finally path; old outputs were already purged"

key-files:
  created:
    - tools/reelkit/stills.py
    - tools/tests/test_stills.py
  modified:
    - tools/reelkit/bundle.py
    - tools/reelkit/review.py
    - tools/reelkit/render.py
    - tools/reel.py
    - tools/reelkit/slot.py
    - tools/draft.py
    - tools/tests/test_bundle.py
    - tools/tests/test_slot.py

key-decisions:
  - "Scene label uses drawtext `%{eif\\:n+1\\:d}`; `%{expr\\:n+1}` printed 1.000000"
  - "Without any request time, request_started_at, request_source, elapsed_since_request_s and within_10_min are all null (not a fallback to the bundle's own elapsed)"
  - "--request-start is parsed in the bundle (not argparse type=float) so a non-number exits 1 with 초안 오류 as the plan requires"
  - "review.md section 5 'end' is the moment the summary is written; bundle.json finished_at is a few ms later"

duration: about 40 min
---

# Phase 3 Plan 03: Reviewable and Rebuildable Bundle Summary

**The bundle now audits the cover against the Instagram grid crop, adds a labelled scene-still sheet and scene table to review.md, rebuilds from edited sources without leaving stale outputs or approval, and records measured time from request to finished bundle.**

## Accomplishments

- Task 1 (tracer): stills.py (crop window 240..1679, 14-px bar excluded, `COVER_CROP ... y A~B` warnings, 7 scenes -> 1500x1316, 3 -> 1128x664), `scenes` step in the bundle, cover warnings give exit 3 after everything is written, review.md section 2 (scene sheet link, crop line, scene table with tags stripped) and section 1 list of suppressed expressions ("없음" when empty). The pension fixture cover has no crop violation and the bundle exits 0.
- Task 2: purge of spec/check/caption/compliance/review/bundle/approval, MP4 (+ `.part.mp4`), cover, scenes and `.safe-s*.png` before any step; record.json, created.json, skeleton.json and the two sources survive byte for byte. Failures: expand/check/caption errors exit 1 with `원고 오류 — 영상 미생성` in review.md (check errors still write check.json and compliance.json), render environment errors exit 2 with the same text as reel.py via the shared `render.env_error_message`; bundle.json always written with `failed_step`.
- Task 3: `slot --create` writes created.json; `resolve_request` (flag wins, else created.json; future, NaN, inf or non-number rejected with exit 1); bundle.json and review.md section 5 carry start/end, per-step seconds, time since request and the 10-minute flag, with the note that the confirmation wait before `slot --create` is not included.

## Task Commits

1. Task 1: `5694781` feat(03-03): cover crop audit, scene sheet, review section 2
2. Task 2: `a56d5cf` feat(03-03): rebuild and failure semantics
3. Task 3: `8e5b019` feat(03-03): timing record

## Verification

- `test_stills.py` 10 tests OK; `test_bundle.py` 26 tests OK (3 renders: first bundle, rebuild pair); `test_slot.py` 20 OK; `test_encode.py` 11 OK.
- `grep -Ec '^(import|from) (PIL|numpy|cv2)' tools/reelkit/stills.py` prints 0; `grep -c env_error_message tools/reel.py` prints 2.
- `git status --porcelain -- 2026/reels` empty. Golden not re-run (frame_sink default path unchanged; render.py change is helper-only).
- Sheet rendering was checked by eye on a synthetic 2-frame sheet (labels `장면 1`, `장면 2`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Scene label printed as float**
- **Found during:** Task 1 (visual check of the sheet)
- **Issue:** `%{expr\:n+1}` rendered "장면 1.000000".
- **Fix:** switched to `%{eif\:n+1\:d}`.
- **Files modified:** tools/reelkit/stills.py
- **Commit:** 5694781

**2. [Rule 3 - Blocking] tools/draft.py touched although not in files_modified**
- **Found during:** Task 3
- **Issue:** argparse `type=float` made a non-numeric `--request-start` exit 2 instead of the planned exit 1 (초안 오류).
- **Fix:** option is now a plain string, converted and validated in `bundle.resolve_request`; help line mentions created.json.
- **Files modified:** tools/draft.py
- **Commit:** 8e5b019

**3. [Test adjustment] Rebuild test edit text**
- The first replacement line wrapped to two lines (layout warning, exit 3); shortened to `채운 만큼 받아요`.

None of the above changed plan scope. Otherwise executed as written.

## Known Stubs

None.

## Threat Flags

None. Purge only unlinks names derived from the validated `<date>-<slug>` folder name (T-03-08, T-03-11); ffmpeg is called with argument lists and an escaped font path (T-03-09); record.json is never rewritten (T-03-10, asserted by byte comparison in the rebuild test).

## Self-Check: PASSED

- Files found: tools/reelkit/stills.py, tools/tests/test_stills.py.
- Commits found in HEAD ancestry: 5694781, a56d5cf, 8e5b019.
