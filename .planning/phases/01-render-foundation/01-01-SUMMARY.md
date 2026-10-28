---
phase: 01-render-foundation
plan: 01
subsystem: infra
tags: [playwright, chromium, ffmpeg, noto-sans-kr, reel-renderer]

requires: []
provides:
  - "tools/reelkit/ package (constants, browser, timeline, layout, templates/frame.html, render, encode)"
  - "tools/reel.py backward-compatible CLI shim (legacy layout, exit 0/2)"
  - "tools/requirements.txt pinning playwright==1.63.0"
  - "tools/fonts/ bundled Noto Sans KR 400/700/900 (unmodified) + OFL.txt"
affects: [01-02, 01-03, 01-04]

actuals:
  tokens: 3941
  tasks: 3
  commits: 1
plan_head_before: febc72886b8ba24c689381069e361f6e39eaaad6
plan_head_after: 10d1b5588ae06216800198a5ff9324844c32a7d6

tech-stack:
  added: [playwright==1.63.0 (pyee, greenlet), Noto Sans KR OTF 400/700/900 (SIL OFL 1.1)]
  patterns:
    - "file:// template page with @font-face, frames via document.body.innerHTML swap"
    - "Chromium launch fallback chain: default -> $AGENT_BROWSER_EXECUTABLE_PATH -> /opt/pw-browsers/chromium -> newest chromium-*/chrome-linux*/chrome"
    - "font verification before first screenshot: FontFace.status + CDP isCustomFont probe; abort instead of silent substitution"
    - "unchanged ffmpeg concat + fps=30 encode path"

key-files:
  created:
    - tools/requirements.txt
    - tools/fonts/NotoSansKR-Regular.otf
    - tools/fonts/NotoSansKR-Bold.otf
    - tools/fonts/NotoSansKR-Black.otf
    - tools/fonts/OFL.txt
    - tools/reelkit/__init__.py
    - tools/reelkit/constants.py
    - tools/reelkit/browser.py
    - tools/reelkit/timeline.py
    - tools/reelkit/layout.py
    - tools/reelkit/templates/frame.html
    - tools/reelkit/render.py
    - tools/reelkit/encode.py
  modified:
    - tools/reel.py

key-decisions:
  - "Fonts vendored unmodified (FONT_VARIANT='original', user answer 원본); FONT_SHA256 equals the research upstream digests"
  - "Legacy layout renders <s> as display:block (reproduces committed MP4s), shim default"
  - "Font failure aborts with FontLoadError and exit 2; no MP4 written"

requirements-completed: [ENV-02, ENV-03]

coverage:
  - id: D1
    description: "tools/reel.py re-renders the published tax-deduction reel through reelkit: stdout duration=26.1s cover_ms=1250, 781/781 frames, min per-frame SSIM 0.9932 vs the committed MP4"
    requirement: ENV-03
    verification:
      - kind: integration
        ref: "python3 tools/reel.py 2026/reels/specs/2026-10-26-tax-deduction.json <tmp>/t.mp4 + ffmpeg ssim + ffprobe -count_frames"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pinned Playwright 1.63.0 installed via pip --user, no browser download; bundled fonts hash-verified against constants.FONT_SHA256"
    requirement: ENV-02
    verification:
      - kind: other
        ref: "importlib.metadata.version('playwright') == 1.63.0; sha256 check of tools/fonts/*.otf against constants.FONT_SHA256"
        status: pass
    human_judgment: false
  - id: D3
    description: "Silent font substitution is impossible: font_problems is non-empty for an empty fonts dir and reel.py exits 2 with a Korean message and no MP4"
    requirement: ENV-02
    verification:
      - kind: other
        ref: "browser.font_problems with empty fonts_dir (6 problems); reel.main with fonts dir swapped for an empty one -> rc=2, no output file"
        status: pass
    human_judgment: false

duration: 3 min
completed: 2026-10-28
status: complete
---

# Phase 1 Plan 01: Render Foundation Tracer Summary

**Pinned Playwright 1.63.0 plus unmodified bundled Noto Sans KR render a published reel through the new reelkit package and match the committed MP4 (781/781 frames, min SSIM 0.9932), aborting instead of substituting fonts**

## Performance

- **Duration:** 3 min (executor run after both human gates were answered in the orchestrator session)
- **Started:** 2026-10-28T20:51:41Z
- **Completed:** 2026-10-28T20:54:34Z (approx., before SUMMARY/state close-out)
- **Tasks:** 3 (2 checkpoints answered upstream, 1 tracer executed)
- **Files modified:** 14 (13 created, 1 modified)

## Accomplishments

- `python3 tools/reel.py 2026/reels/specs/2026-10-26-tax-deduction.json <tmp>/t.mp4` prints `duration=26.1s cover_ms=1250`, writes 781 video frames (same as committed MP4), per-frame ffmpeg SSIM `All` minimum 0.993194 (threshold 0.98). Render took about 13 s.
- Font safety: the page loads the three bundled faces from `file://`, checks `FontFace.status` and a CDP `isCustomFont` probe for weights 400/700/900 before the first screenshot. With an empty fonts directory `font_problems` returns 6 Korean problem strings; the shim then exits 2 and writes no MP4.
- Chromium launch fallback chain implemented and exercised (forced default failure -> `/opt/pw-browsers/chromium`; all-fail -> `BrowserLaunchError` listing every attempt). In this container the plain default `launch()` works with 1.63.0, so launch path used was `default`.
- `tools/cards.py` and everything under `2026/reels/` untouched; no `__pycache__`/`.pyc` tracked.

## Task Commits

1. **Task 1: Playwright 1.63.0 legitimacy check** - no commit (checkpoint:human-verify, approved by the user, see Decisions)
2. **Task 2: font vendoring decision** - no commit (checkpoint:decision, user chose 원본, see Decisions)
3. **Task 3: Tracer** - `10d1b55` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `tools/requirements.txt` - one line `playwright==1.63.0`
- `tools/fonts/NotoSansKR-{Regular,Bold,Black}.otf`, `tools/fonts/OFL.txt` - unmodified upstream fonts and SIL OFL 1.1 text
- `tools/reelkit/constants.py` - colours, timing, canvas, SAFE (D-03), BASIS/ACCT px, paths, FONT_FILES, FONT_VARIANT, FONT_SHA256
- `tools/reelkit/browser.py` - launch fallback chain, file:// template page, http(s) request blocking, `font_problems`, `platform_fonts`, `BrowserLaunchError`, `FontLoadError`
- `tools/reelkit/timeline.py` - `State`, `build_states`, `total_duration`, `progress_values`, `cover_ms`
- `tools/reelkit/layout.py` - `legacy_inner_html` (`<s>` = block) and `LAYOUTS`
- `tools/reelkit/templates/frame.html` - quirks-mode page with three `@font-face` rules (`{{FONTDIR_URI}}`)
- `tools/reelkit/render.py` - `RenderResult`, `render_reel`, private `_read_spec` seam for Plan 02
- `tools/reelkit/encode.py` - `encode_concat` with HEAD's unchanged ffmpeg arguments
- `tools/reel.py` - CLI shim, docstring kept, exit codes 0 / 2

## Decisions

**Task 1 (package legitimacy, `playwright==1.63.0`):** the user replied "승인" in the orchestrator session before any install. The orchestrator showed live PyPI metadata: playwright 1.63.0 author "Microsoft Corporation", uploaded 2026-09-15T16:49:06; pyee 57 releases; greenlet 69 releases (already installed). Installed with `python3 -m pip install --quiet --user -r tools/requirements.txt`; `importlib.metadata.version('playwright')` = `1.63.0`. No browser download was triggered (`playwright install` never run).

**Task 2 (font vendoring):** the user's verbatim answer was "승인, 원본" ("원본" = option id `unmodified`). Recorded before any font download. `constants.FONT_VARIANT = 'original'`.

Font record (Plan 02 writes `tools/fonts/README.md` from this):

- Variant: `original` (unmodified upstream files, no subsetting, no fonttools)
- Source: `https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/KR/NotoSansKR-{Regular,Bold,Black}.otf` and `https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE`
- Retrieved: 2026-10-28
- Upstream: Noto Sans CJK version 2.004, SIL Open Font License 1.1, (c) 2014-2021 Adobe
- Upstream digest comparison: all three OTFs and LICENSE matched the research table exactly (no mismatch; `main` had not moved). So the digests below equal both the upstream and the recorded `constants.FONT_SHA256`.

| File | Bytes | sha256 | CSS weight |
|------|-------|--------|-----------|
| NotoSansKR-Regular.otf | 4,644,748 | `69975a0ac8472717870aefeab0a4d52739308d90856b9955313b2ad5e0148d68` | 400 |
| NotoSansKR-Bold.otf | 4,816,044 | `5a6ceb287ed2fc6cfc6213144ebea68cbd94b20fc9eb873d8486493bf02d9bda` | 700 |
| NotoSansKR-Black.otf | 5,033,248 | `a9977a588488d2a7f544bb2b589b01bed071dca64a4655d438696301b527884b` | 900 |
| OFL.txt | 4,301 | `6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2` | - |

Total OTF size 14,494,040 bytes (about 14.5 MB), permanently added to git history as intended by the user's choice.

**Chromium launch path used:** `default` (plain `pw.chromium.launch()` succeeded with Playwright 1.63.0 against the preinstalled Chromium 1243). Fallback chain was verified separately by forcing the default to fail.

**Other:** the SAFE dict holds the D-03 starting values (top 270 is research assumption A1, to be recalibrated after a private on-device upload).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Readable font-failure message and de-duplicated launch candidates**
- **Found during:** Task 3 verification of the abort path
- **Issue:** the first draft of `font_problems` emitted one line per substituted font per node (12 near-identical lines); the launch candidate list could try the same executable twice when `AGENT_BROWSER_EXECUTABLE_PATH` equals `/opt/pw-browsers/chromium`.
- **Fix:** one problem line per weight listing the distinct substituted family names; candidate paths are de-duplicated.
- **Files modified:** tools/reelkit/browser.py
- **Verification:** abort path re-run (exit 2, no MP4); full tax-deduction render and SSIM re-run after the edit (781/781, min SSIM 0.993194)
- **Committed in:** 10d1b55 (part of the Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 2)
**Impact on plan:** presentation only; no behaviour change to rendering or the pass/fail criteria.

## Issues Encountered

None. Note: pip printed its usual "running as root" warning; the install itself succeeded.

## Known Stubs

None. `RenderResult.warnings` and `overlays` are intentionally empty lists until Plan 03; `_read_spec` is the documented seam Plan 02 replaces.

## Threat Flags

None beyond the plan's threat model. `page.route` aborts every http/https request (T-01-01); font digests are pinned (T-01-02); ffmpeg is invoked with a list and no shell (T-01-03); font failures abort (T-01-04).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for Plan 02 (spec loader with legacy markup allowlist replacing `_read_spec`, `tools/fonts/README.md` from the Decisions record above, `.gitignore`).
- Only the tax-deduction reel was compared here; the other nine reels and the no-spec MP4 are covered by Plan 04's full golden run (assumption A7, why committed MP4s show `<s>` as a block, remains inferred, though SSIM 0.9932 on a reel with `<s>` lines supports it).
- A4 remains open: a future image with EXTERNALLY-MANAGED python may refuse `pip --user` (Plan 04 doctor reports it).

## Self-Check: PASSED

All 14 listed files exist, commit `10d1b55` is an ancestor of HEAD, all Task 3 acceptance criteria and the four `<verify>` commands re-run green, `git status --porcelain -- 2026/reels tools/cards.py` empty, no tracked `__pycache__`/`.pyc`.

---
*Phase: 01-render-foundation*
*Completed: 2026-10-28*
