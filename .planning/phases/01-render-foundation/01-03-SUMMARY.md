---
phase: 01-render-foundation
plan: 03
subsystem: infra
tags: [ffprobe, upload-spec, safe-zone, layout-measurement, overlay, playwright]

requires:
  - phase: 01-render-foundation
    provides: "reelkit package, reel.py shim, spec loader, bundled fonts (Plans 01-02)"
provides:
  - "tools/reelkit/specprobe.py + tools/specprobe.py: 9-item Instagram upload-spec check (ENV-06)"
  - "reel.py stderr spec report after every render, exit 4 on FAIL"
  - "layout 'new': basis 36px under the body, account below, inside the SAFE stack (ENV-04)"
  - "layout.evaluate_layout / MEASURE_JS / LayoutWarning and render.check_layout (ENV-05)"
  - "<out-stem>.safe-sNN.png overlay previews, reel.py --layout/--strict/--overlay-all, exit 3"
affects: [01-04, phase-2-draft-generation]

actuals:
  tokens: 11600
  tasks: 2
  commits: 4
plan_head_before: 8d590fbb0c28e800065b8f9b27bb55607e274907
plan_head_after: 7b63f7eb02f3d73e5c3d5bef7dee659774598910

tech-stack:
  added: []
  patterns:
    - "Unmeasurable = FAIL (측정 불가), never PASS, never an exception"
    - "Measure in the browser (Range.getClientRects clustering) after the frame screenshot so labels never reach the MP4"
    - "Safe-zone numbers live only in constants.SAFE; overlay bands and labels are computed from them"
    - "Warnings are reported, never fixed: text is not truncated, shrunk or reworded"

key-files:
  created:
    - tools/reelkit/specprobe.py
    - tools/specprobe.py
    - tools/tests/test_specprobe.py
    - tools/tests/test_layout.py
    - tools/tests/fixtures/ok-layout.json
    - tools/tests/fixtures/bad-layout.json
  modified:
    - tools/reelkit/layout.py
    - tools/reelkit/render.py
    - tools/reel.py

key-decisions:
  - "reel.py exit codes: 0 ok, 1 spec error, 2 environment, 3 --strict with layout warnings, 4 upload-spec FAIL (4 wins over 3)"
  - "Legacy layout skips position/line measurement on purpose; only the FONT_FALLBACK glyph check runs there"
  - "check_layout (no encode, no screenshots) is the seam Phase 2 reuses to vet drafts"

requirements-completed: [ENV-04, ENV-05, ENV-06]

coverage:
  - id: D1
    description: "python3 tools/specprobe.py 2026/reels/*.mp4: 11 files, each 'spec: PASS 9/9', exit 0"
    requirement: ENV-06
    verification:
      - kind: integration
        ref: "tools/specprobe.py on 2026/reels/*.mp4 (11 x PASS 9/9, 0 FAIL lines, rc=0); test_specprobe.ProbeCommitted"
        status: pass
    human_judgment: false
  - id: D2
    description: "No-faststart sample fails only faststart (duration WARN); 720x1280/24fps/yuv444p/silent sample fails size, fps, pix_fmt, profile, audio, faststart; text file is FAIL (측정 불가), CLI exit 1"
    requirement: ENV-06
    verification:
      - kind: unit
        ref: "tools/tests/test_specprobe.py (12 tests, ffmpeg lavfi samples)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every reel.py render prints the per-item spec report to stderr; salary-two-owners-1 stdout stays duration=21.8s cover_ms=1250 with spec: PASS 9/9"
    requirement: ENV-06
    verification:
      - kind: integration
        ref: "python3 tools/reel.py 2026/reels/specs/2026-10-28-salary-two-owners-1.json <tmp>/s.mp4"
        status: pass
    human_judgment: false
  - id: D4
    description: "New layout: basis 36px directly below body, account 36px below, inside SAFE stack; for all 10 committed specs no warning targets basis or account (only 8 WRAP warnings on body lines)"
    requirement: ENV-04
    verification:
      - kind: integration
        ref: "tools/tests/test_layout.py::BrowserChecks.test_committed_specs_never_warn_about_basis_or_account"
        status: pass
    human_judgment: false
  - id: D5
    description: "Wrap, right overflow, top/bottom safe-zone intrusion, basis >2 lines, sub-36px, non-bundled glyph (emoji -> Noto Color Emoji) each yield a 'scene N line M: KIND (value) \"text\"' warning; exit 0 by default, 3 with --strict, MP4 always written"
    requirement: ENV-05
    verification:
      - kind: unit
        ref: "tools/tests/test_layout.py::EvaluateLayout + BrowserChecks.test_bad_fixture_kinds_and_format + Cli.test_strict_bad_fixture_exit_3_and_mp4_written"
        status: pass
    human_judgment: false
  - id: D6
    description: "Overlay PNGs <out-stem>.safe-s01.png plus the tallest scene (all scenes with --overlay-all), 1080x1920, bands from constants.SAFE; overlay pixels absent from MP4 frames"
    requirement: ENV-05
    verification:
      - kind: unit
        ref: "tools/tests/test_layout.py::Cli.test_ok_new_layout_render_and_overlay + test_overlay_all_writes_one_per_scene"
        status: pass
    human_judgment: false
  - id: D7
    description: "Legacy output unchanged: tax-deduction re-render prints duration=26.1s cover_ms=1250, frames 781/781/781, min per-frame SSIM 0.993194; legacy emits no measurement warnings"
    requirement: ENV-04
    verification:
      - kind: integration
        ref: "reel.py tax-deduction re-render + ffmpeg ssim + ffprobe -count_frames; test_layout.BrowserChecks.test_legacy_layout_emits_no_measurement_warnings"
        status: pass
    human_judgment: false
  - id: D8
    description: "SAFE values (top 270 etc.) match a real phone screen"
    requirement: ENV-04
    verification:
      - kind: other
        ref: "human-check in plan Task 2: open <out>.safe-sNN.png from a --layout new render; real-device calibration is a human task (D-03, research A1)"
        status: pending
    human_judgment: true

duration: 14 min
completed: 2026-10-28
status: complete
---

# Phase 1 Plan 03: Upload-Spec Probe and Safe-Zone Layout Summary

**ffprobe + MP4 atom-walk upload checks (9 items, unmeasurable = FAIL) end every render, and `--layout new` stacks 36px basis and account inside the safe box with browser-measured per-scene/line warnings, overlay PNGs and `--strict`**

## Performance

- **Duration:** about 14 min (2026-10-28T20:55Z to 21:09Z)
- **Tasks:** 2, both TDD (RED + GREEN commits each)
- **Files:** 9 changed (6 created, 3 modified), 884 insertions, 18 deletions
- **Tests:** 54 in `tools/tests` (12 specprobe, 25 layout, 17 spec), all OK in about 40 s

## Accomplishments

- **ENV-06.** `python3 tools/specprobe.py FILE...` prints one line per item (video_stream, codec, size, fps, pix_fmt, profile, audio, faststart, duration) with actual vs expected, and a final `spec: PASS 9/9 — <path>`; exit 1 on any FAIL. All 11 committed MP4s PASS 9/9. `top_atoms` handles 64-bit and to-EOF sizes and stops on size < 8. The profile is read from the video stream only (the audio stream also reports `LC`). Duration outside 3-90 s is WARN only (research A3).
- Every `reel.py` run probes its own output and prints the report to stderr; any FAIL exits 4 after the unchanged stdout line.
- **ENV-04.** `--layout new`: `#rk-stack` is positioned from `constants.SAFE` (left 96, right 150, top 270, height up to the 1250 warn line, centered, gap 40, `word-break:keep-all`); top label 50px, body 100px/900 with all lines in layout, basis 36px directly below, `@kiwoom.mentor` 36px below it. Progress bar is the legacy 14px bar (D-04). Empty basis omits the block; empty top keeps its 60px slot. `markup_new` escapes everything and restores only `<g>`/`</g>`/`<s>`/`</s>`.
- **ENV-05.** `MEASURE_JS` clusters `Range.getClientRects` by vertical centre (tolerance font-size x 0.4); `evaluate_layout` emits WRAP, RIGHT, TOP, WARN_Y, UI_ZONE, BASIS_LINES, SMALL; a CDP `getPlatformFontsForNode` pass labels text via `TAG_JS` and emits FONT_FALLBACK. Warning format `scene N line M: KIND (value) "text"` with M = number, top, basis or account.
- Overlay PNGs `<out-stem>.safe-sNN.png` (scene 1 plus the tallest scene; every scene with `--overlay-all`) draw the bands and the three labeled rules, all computed from `constants.SAFE`. Overlay is added only after the frames are encoded-ready, so it never reaches the MP4 (pixel test: sage at (5,1900); overlay PNG red minus green 70).
- `check_layout(spec_path, layout="new")` runs the same checks with no screenshots or encode (Phase 2 reuse).

### Measured warning counts, 10 committed specs, new layout

Only body-line WRAP warnings (caused by the strict 150px right margin, Open Question 2), nothing on basis or account:

| Spec | Warnings |
|------|----------|
| 2026-10-19-rate-secret-1 | WRAP 1 |
| 2026-10-21-rate-secret-2 | none |
| 2026-10-24-rate-secret-3 | WRAP 1 |
| 2026-10-26-tax-deduction | WRAP 3 (scene 1 line 1; scene 5 lines 1, 2) |
| 2026-10-28-salary-two-owners-1 | none |
| 2026-10-29-ebook-event | WRAP 1 |
| 2026-10-31-salary-two-owners-2 | none |
| 2026-11-02-salary-two-owners-3 | WRAP 1 |
| 2026-11-04-salary-two-owners-4 | WRAP 1 |
| 2026-11-07-salary-two-owners-5 | none |

Total 8 WRAP, 0 RIGHT, 0 basis/account warnings, which matches the research measurement (8 of 195 lines).

### Overlay file names produced (verification runs, scratch only, not committed)

`ok.safe-s01.png`; `bad.safe-s01.png`; `tax-new.safe-s01.png` and `tax-new.safe-s05.png` (scene 5 is the tallest tax-deduction scene). `--overlay-all` on the ok fixture wrote `all.safe-s01.png` and `all.safe-s02.png`. I viewed `tax-new.safe-s05.png`: basis and account sit in the sage area between the 270 and 1250 rules, clear of the red right strip and bottom UI band.

### bad-layout fixture output

`--layout new --strict` prints 9 warnings and exits 3 with the MP4 written: TOP (label), WRAP and TOP (line 1), RIGHT (line 2, right=1609), WARN_Y (line 7), BASIS_LINES, UI_ZONE (basis and account), FONT_FALLBACK (line 7, `Noto Color Emoji`).

## Task Commits

1. **Task 1 RED: failing tests for the upload-spec probe** - `e0bb224` (test)
2. **Task 1 GREEN: specprobe CLI, render wiring, reel.py report/exit 4** - `971ca4c` (feat)
3. **Task 2 RED: failing tests for the new layout and warnings** - `fb11f15` (test)
4. **Task 2 GREEN: new layout, measurement, overlays, flags** - `7b63f7e` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## TDD Gate Compliance

RED commits carry no-op placeholders (`reelkit/specprobe.py`; layout/`check_layout` stubs with correct signatures) so the test modules import and fail on assertions rather than on import errors (same approach as Plan 02). Task 1 RED: 12 tests, 10 failing (9 failures, 1 error on the empty report), 2 trivially satisfied by placeholders. Task 2 RED: 25 tests, 32 failures/errors counted incl. subtests, all assertion or IndexError on the empty stub result, not import/syntax faults. GREEN: 12/12 and 25/25 pass. No REFACTOR commit.

## Files Created/Modified

- `tools/reelkit/specprobe.py` - Check, top_atoms, ffprobe_json, probe, format_report, main
- `tools/specprobe.py` - CLI entry
- `tools/reelkit/layout.py` - markup_new, new_inner_html, MEASURE_JS, TAG_JS, LayoutWarning, evaluate_layout, overlay_html, LAYOUTS["new"]; legacy_inner_html byte-identical
- `tools/reelkit/render.py` - spec_checks, _scene_checks, overlays, overlay_all, check_layout
- `tools/reel.py` - `--layout/--strict/--overlay-all`, stderr reports, exit codes 3 and 4, docstring
- `tools/tests/test_specprobe.py`, `tools/tests/test_layout.py`, `tools/tests/fixtures/{ok,bad}-layout.json`

## Decisions

- Exit 4 takes priority over exit 3 when both occur (spec FAIL is the harder failure); both write the MP4 first.
- Overlay choice (Open Question 5): scene 1 plus the scene with the largest top-to-account span; empty top falls back to the first body line top.
- FONT_FALLBACK reports one warning per (scene, label), value = first non-bundled familyName.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] RED commits needed no-op placeholders**
- **Found during:** both RED steps
- **Issue:** the test modules import `reelkit.specprobe` / new layout names, which did not exist, so RED would have been an import failure, not an assertion failure.
- **Fix:** committed minimal no-op placeholders with the tests, replaced in the GREEN commits.
- **Files modified:** tools/reelkit/specprobe.py, tools/reelkit/layout.py, tools/reelkit/render.py
- **Commits:** e0bb224, fb11f15

**2. [Rule 1 - Bug] ffmpeg pixel helper failed on 1x1 crop of yuv420p**
- **Found during:** Task 2 GREEN test run (ffmpeg exit 234)
- **Fix:** the test helper now converts to rgb24 before `crop=1:1:X:Y` (`-vf format=rgb24,crop=...`), instead of the plan's bare crop.
- **Files modified:** tools/tests/test_layout.py
- **Commit:** 7b63f7e

**Total deviations:** 2 auto-fixed (Rule 3, Rule 1). **Impact:** test plumbing only.

## Issues Encountered

None. One stray `tools/reelkit/__pycache__` created by an ad-hoc check was removed; nothing tracked.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-01-07 (new-layout spec text is HTML-escaped; only four tags restored; http(s) still aborted), T-01-09 (atom walk bounded by file length, ffprobe failures become FAIL items), T-01-10 (text file probe is FAIL 측정 불가, tested) mitigated as planned; no package installs (T-01-SC).

## User Setup Required

None. Human check still open (D8): open the overlay PNGs of a `--layout new` render on a real phone-sized view and confirm the SAFE values (research A1, top 270); recalibrate in `constants.SAFE` only.

## Next Phase Readiness

- Ready for Plan 04 (doctor, golden regression of all 10 reels, SessionStart hook). `check_layout` and `specprobe.probe` are reusable from there and from Phase 2.
- `git status --porcelain -- 2026/reels/*.mp4 2026/reels/specs` is empty; legacy output unchanged.

## Self-Check: PASSED

All 9 listed files exist; commits `e0bb224`, `971ca4c`, `fb11f15`, `7b63f7e` are ancestors of HEAD; `python3 -m unittest discover -s tools/tests` (54 tests) OK; specprobe on all 11 MP4s PASS 9/9; tax-deduction legacy re-render 781/781/781 frames, min SSIM 0.993194; `grep -nE '\b(270|1250|1470)\b'` on layout.py and render.py prints nothing; no tracked `__pycache__`/`.pyc`.

---
*Phase: 01-render-foundation*
*Completed: 2026-10-28*
