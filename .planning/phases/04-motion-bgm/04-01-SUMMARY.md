---
phase: 04-motion-bgm
plan: 01
subsystem: render
tags: [playwright, web-animations, ffmpeg, image2pipe, motion]
status: complete

requires:
  - phase: 03-compliance-gate
    provides: new layout (layout.py), bundle/draft flow, specprobe 9/9, golden 10/10
provides:
  - basic motion render path (per-line fade + 24 px rise, 0.3 s scene cross-fade) by deterministic time seeking into an ffmpeg PNG pipe
  - motion.py schedule (dwell formula and count-up settle term already included for Plan 02)
  - PipeEncoder (image2pipe, .part.mp4 atomic replace)
  - `motion` source field (none|basic) validated in expand, compared by check, overridable by reel.py --motion
  - none baseline guard (tools/tests/none_guard.py + golden/none-new.json) taken before any source edit
affects: [04-02 count-up and dwell warnings, 04-03 BGM]

actuals:
  tokens: 12200
  tasks: 2
  commits: 3
plan_head_before: aeb5361b38c627359ab490dddfa0a98664890211
plan_head_after: 9088549c779bcbfb75250d1b109ced35f81bb38b

tech-stack:
  added: []
  patterns:
    - paused Web Animations kept in window.A, currentTime set per frame, off-window layers display:none
    - frame sink receives the exact frame written to the pipe at each scene final_t

key-files:
  created:
    - tools/reelkit/motion.py
    - tools/tests/none_guard.py
    - tools/tests/golden/none-new.json
    - tools/tests/test_motion.py
  modified:
    - tools/reelkit/encode.py
    - tools/reelkit/layout.py
    - tools/reelkit/render.py
    - tools/reelkit/expand.py
    - tools/reelkit/check.py
    - tools/reelkit/stills.py
    - tools/reel.py
    - tools/tests/test_expand.py

key-decisions:
  - "Progress bar in the motion DOM animates width, not transform scaleX"
  - "Layer fade-in uses fill both, fade-out uses fill forwards only, so the later-created animation never overrides the earlier one before its start"
  - "SEEK_JS looks up each layer window by data-s so layers can be removed for measurement"

requirements-completed: [MOTN-01, MOTN-02, MOTN-04]

duration: not recorded
completed: 2026-10-29
---

# Phase 4 Plan 01: Basic motion render path Summary

**`"motion": "basic"` reels render by seeking paused Web Animations frame by frame into an ffmpeg PNG pipe (300 ms / 24 px / 120 ms line entries, 0.3 s cross-fade), pass the upload spec 9/9, and the `none` path is pinned by a baseline taken before the first source edit.**

## What was built

- **Task 1 (tracer):** `none_guard.py` and its baseline were committed alone first (3fde951), then `motion.py` (constants, `resolve`, `schedule`, layer DOM build, seek), `layout.stack_html` / `root_html` (with `new_inner_html` byte-identical), `PipeEncoder`, and `render_reel(motion=None)` dispatching basic to `_render_motion`. The `none` body and `encode_concat` argv were not edited. The tracer verify (reel.py on ok-layout plus motion basic: exit 0, `spec: PASS 9/9`, packet count equals schedule frames, one sink PNG per scene) passed before Task 2 started.
- **Task 2:** `motion` accepted in expand (none|basic, else ExpandError naming motion) and copied into the spec; `check.SOURCE_KEYS` includes it; `stills.scene_times` returns schedule `final_t` for basic; `reel.py --motion {none,basic}` prints `motion=basic` on its own line; legacy plus basic exits 1 before Chromium. `spec.py` and `draft.py bundle` were not touched (no bundle motion option).
- **Guards:** NoneUnchanged (both fixtures, frame hashes, durations, warnings, overlays, markup hashes, ffmpeg argv), Equivalence (motion final frame equals static frame from row 30, channel difference at most 1, for pension scenes 1 and 5 plus a wrapping scene), Geometry (line rectangles and counts equal the static layout to 0.01; mid-entry frames keep line count and width with 0 to 24 px offset), BundleBasic (7-scene bundle: exit 0, 9/9, review times equal schedule, cover equals scene-1 final frame, frame count equals schedule).

## Verification

- `test_motion.py`: 29 tests OK (about 195 s).
- `test_expand.py`: 27 OK. `test_encode.py` 11 OK (Task 1). `test_spec.py` 32 OK.
- golden: `golden: PASS 10/10 (재현 불가 1)`, rc 0, `git status --porcelain -- 2026/reels` empty.
- `draft.py bundle --help` lists no `--motion`; `spec.py` / `test_spec.py` unchanged since the plan base.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Progress bar bled ink below row 13 when animated with scaleX**
- **Found during:** Task 2 (BundleBasic: cover check reported `COVER_CROP ... y 14~21`, bundle exit 3)
- **Issue:** the plan specified `transform: scaleX(0)->scaleX(1)`; the compositor stretches the bar texture and blends its lower edge into rows 14 and below, which the cover crop check reads as text.
- **Fix:** animate the bar's `width` (0% to 100%, linear). The bar is absolutely positioned, so no other element's layout changes; verified rows 13 and below are crisp and the Equivalence / Geometry guards still hold.
- **Files modified:** tools/reelkit/motion.py
- **Commit:** 9088549

**2. [Rule 1 - Bug] Layer fade animations overrode each other**
- **Found during:** Task 1 design (before first run)
- **Issue:** with `fill: both` on both the fade-in and the fade-out of the same layer, the later-created fade-out's backwards fill (opacity 1) would override the fade-in while it runs.
- **Fix:** fade-in keeps `fill: both`; fade-out uses `fill: forwards` only.
- **Commit:** 8654522

**3. [Rule 1 - Bug] SEEK_JS indexed layer windows by DOM position**
- **Found during:** Task 2 (Geometry removes other layers before measuring)
- **Fix:** windows are looked up through each layer's `data-s`.
- **Commit:** 9088549

### Scope notes

- Tests for Task 2 were written after the source edits for expand/check/stills/reel.py rather than strictly before them; all behaviors listed in the plan are covered and pass.
- `check._house_pattern` DURATION still measures the `none` total for basic specs (not in this plan's file list; the research notes a basic branch). Left for a later plan.
- Estimate was 110000 tokens; the measured value is chars/4 over added diff lines only and is not comparable to a harness token count.

## Known Stubs

None.

## Threat Flags

None. All new surface (motion page, ffmpeg pipe) is covered by T-04-01 to T-04-04: layers go through `stack_html` / `markup_new`, page data goes in as `page.evaluate` JSON arguments, the page uses `browser.open_page` (http/https aborted), and PipeEncoder writes `.part.mp4` and replaces only on exit 0.

## Self-Check: PASSED

- FOUND: tools/reelkit/motion.py, tools/tests/none_guard.py, tools/tests/golden/none-new.json, tools/tests/test_motion.py
- FOUND commits: 3fde951, 8654522, 9088549 (ancestors of HEAD)
- `git log` shows the baseline commit (3fde951) older than the first commit touching tools/reelkit/render.py (8654522).
