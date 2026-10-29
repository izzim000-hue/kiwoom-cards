---
phase: 04-motion-bgm
plan: 03
subsystem: audio
tags: [bgm, ffmpeg, approval, gitignore, docs, phase-gate]
status: complete

requires:
  - phase: 04-motion-bgm
    provides: basic motion render path, PipeEncoder, count-up, bundle.json motion/countups (Plans 01-02)
provides:
  - "tools/reelkit/bgm.py: AUDIO_EXTS, COPY_NAMES, BgmError, validate, install, read_meta, filter_graph"
  - "`draft.py bundle DIR --bgm PATH --bgm-license TEXT` and `reel.py ... --bgm PATH --bgm-license TEXT` (both or refusal, exit 1, before any purge or render)"
  - bgm.<ext> copy + bgm.json in the draft folder, bundle.json `bgm` and outputs, review.md license line for human confirmation
  - two-way audio check in approve and promote, audio hashes in approval.json files
  - .gitignore audio patterns, README section on motion and BGM, make-reel skill and source-format updates
affects: [phase verification, human viewing of a motion reel, owner decision on license evidence format]

actuals:
  tokens: 14050
  tasks: 3
  commits: 3
plan_head_before: 77877064cd18f48aa915401db1a41f6f1ec07be0
plan_head_after: c0c951009468d58302f359074fb2515efdcda166

tech-stack:
  added: []
  patterns:
    - validate before purge, install after purge (a refused run leaves earlier outputs untouched)
    - expected approval file set derived from bundle.json `bgm` and checked against the disk both ways
    - encode argv built exactly as before when bgm is None (NoneUnchanged guard)

key-files:
  created:
    - tools/reelkit/bgm.py
    - tools/tests/test_bgm.py
  modified:
    - tools/reelkit/encode.py
    - tools/reelkit/render.py
    - tools/reelkit/bundle.py
    - tools/reelkit/review.py
    - tools/reelkit/approve.py
    - tools/draft.py
    - tools/reel.py
    - tools/tests/test_approve.py
    - tools/tests/test_bundle.py
    - .gitignore
    - tools/README.md
    - .claude/skills/make-reel/SKILL.md
    - .claude/skills/make-reel/references/source-format.md

key-decisions:
  - "The license memo is a free-form string (500 characters max, stored verbatim after strip); the owner decision on license evidence format stays open"
  - "validate runs after resolve_request and before purge_outputs; install runs as a `bgm` step between compliance and render and failures there map to exit 2"
  - "bundle.json outputs gain bgm.json and the copy only when a track was mixed; approve/promote derive the expected name set from the verified bundle.json and also require approval.json `bgm` to equal it"
  - "reel.py mixes from the validated path (no copy, no bgm.json) and checks the repository rule against the output MP4's folder"

requirements-completed: [MOTN-06, MOTN-01, MOTN-02, MOTN-03, MOTN-04, MOTN-05]

duration: not recorded
completed: 2026-10-29
---

# Phase 4 Plan 03: Background music, approval fingerprint, docs and phase gates Summary

**Optional BGM turns on only with a user-supplied audio file plus a license memo, is looped or trimmed, faded for 1 s and normalised to about -16 LUFS in the same ffmpeg run, is copied into the draft folder with its sha256 and memo, shows up in review.md for human license confirmation, joins the approval fingerprint both ways, and can never be committed; the phase gates pass once.**

## What was built

- **Task 1 (tracer, 446aec4):** `bgm.validate` refuses a missing or blank memo, a memo without a file or a file without a memo, symlinks, non-regular files, extensions outside the allow list, files ffprobe cannot read, files without an audio stream or with a real video stream (album art allowed), tracks under 3 s, and repository paths other than a non-`bgm.*` file inside that draft folder. `bundle.run_cli` validates before `purge_outputs` (refusal: exit 1, `음원 오류`, earlier MP4/cover bytes untouched, no bundle.json rewritten). `encode_concat(..., bgm=None)` and `PipeEncoder(out, bgm=, total=)` build the old argv when bgm is None and otherwise swap anullsrc and `-vf` for `-i <bgm>` plus `filter_graph(total)` (T rounded up to 1 ms, `aresample=44100` after loudnorm). The bundle adds a `bgm` step before render, writes `bgm.<ext>` and `bgm.json` {schema, file, copy, sha256, license, duration_s}, records the same object in bundle.json `bgm` and both files in `outputs`. review.md shows the original file name, sha256 prefix and the memo (control characters to spaces, backticks to `'`, pipes escaped) on the 음원 라이선스 line plus a 음량 check item; without BGM the old line is unchanged. `purge_outputs` also deletes `bgm.json`, every `bgm.<ext>` and its `.part` (done in this commit because the same bundle.py edit; its tests are in Task 2).
- **Task 2 (27b9b87):** `approve.bgm_names` checks bundle.json `bgm` against bgm.json and the copy on disk in both directions (null with files present, set with files missing/changed/duplicated, bgm.json differing from bundle.json). `check_outputs`, `file_hashes`, `hashed_names` take the extra names; approve shows `배경음: <file> · 라이선스 메모: <memo>` and stores `bgm` in approval.json; promote validates the digest loop first, then derives the expected set from the verified bundle.json, and still moves only the four files (`PROMOTED_KEYS` unchanged). `reel.py --bgm/--bgm-license` validates before Chromium and prints `bgm=<file>`.
- **Task 3 (c0c9510):** `.gitignore` audio patterns, README `## 자막 모션과 배경음`, make-reel SKILL.md and source-format.md (motion field, `|up` scene lines only, `--bgm` only with a user-given pair, never source/pick music, DWELL/COUNTUP_WRAP handled like other exit-3 warnings), measured suite time in the test section.

## Verification

- `test_bgm.py`: 32 tests OK (Validate, Mix none/loop and basic/trim with specprobe 9/9, AAC 44100 Hz 2 ch, durations within 0.1 s and loudness within -16 +/- 1.5 LUFS; BundleWithBgm; Refusal; Rebuild without --bgm; ReelFlags).
- `test_approve.py`: 43 OK (new `ApproveBgm`; existing approve/promote tests unchanged). `test_bundle.py`: 28 OK (purge list now includes bgm names, keeps `song.mp3`). `test_motion.py`: 60 OK in 372.8 s, NoneUnchanged still matches the none argv. `test_draft_e2e.py`: 7 OK.
- Phase gates, each run once:
  - Full suite: `Ran 679 tests in 792.798s` -> `OK` (elapsed_s=793).
  - Golden: last line `golden: PASS 10/10 (재현 불가 1)`, rc 0, `git status --porcelain -- 2026/reels` empty.
  - Motion + count-up fixture bundle (fresh mktemp draft folder, `draft-pension-motion.src.json`): bundle rc 0, spec PASS 9/9, printed line `0 basic 2 79.56 True None` (exit_code, motion, countups, elapsed_s, within_10_min, bgm), 26.3 s reel, 79.6 s total.
  - Git: tracked audio files 0; `git check-ignore` matches `tools/x.mp3` and `2026/reels/x.m4a`; nothing changed under `2026/reels`, `tools/data/figures.json` or `.claude/settings.json` since the 04-01 plan commit (321f713).
  - Acceptance greps: no network imports in bgm.py (0), no audio file left in the working tree (0), `PROMOTED_KEYS = ("mp4", "cover", "spec", "caption")`.
- No registry figure was set to 확인. No `approve` was run on a real folder (tests only, simulated TTY in temp dirs). No music was searched for or downloaded; all test audio is ffmpeg sine tones in temp dirs.

## Deviations from Plan

None - plan executed exactly as written.

Notes (not deviations):
- The Task 2 tests were written after the implementation rather than run failing first; the purge change to bundle.py landed in the Task 1 commit with the rest of that file's edit, its tests in Task 2.
- `actuals.tokens` is chars/4 over added diff lines (about 56,200 chars across 15 files), not a harness count. `commits` is measured from the ledger base (3 task commits; this SUMMARY commit follows).
- The README states the measured 79.6 s bundle time of the 26.3 s fixture reel and the 793 s suite time.

## Pending human verification (not performed by the executor)

1. **Watch a motion reel** (the gate bundle's MP4, or `python3 tools/draft.py bundle` on a real draft with `"motion": "basic"`): each line fades in and rises slightly, scenes cross-fade in about 0.3 s, Hangul line breaks never jump, the two count-ups end on script numbers, no scene feels rushed or stalled (dwell coefficients, assumption A1); the 0.3 s overlap of basis/account text during a cross-fade is acceptable (A4).
2. **Optional, only with an own track whose commercial use is licensed:** bundle a draft with `--bgm <file> --bgm-license "<license note>"` and listen: about 1 s fades, comfortable level (target about -16 LUFS; real music may differ by 1-2 LU, A2), review.md shows file name and memo. The license evidence format is still an open owner decision.

## Known Stubs

None.

## Threat Flags

None. New surface (user audio path, license memo, audio in the approval chain, audio in git) is covered by T-04-09 through T-04-15 and mitigated as listed in the plan.

## Self-Check: PASSED

- FOUND: tools/reelkit/bgm.py, tools/tests/test_bgm.py
- FOUND commits: 446aec4, 27b9b87, c0c9510 (ancestors of HEAD)
