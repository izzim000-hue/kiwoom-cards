---
phase: 01-render-foundation
plan: 04
subsystem: infra
tags: [doctor, session-start-hook, golden-regression, ssim, playwright-pin, readme]

requires:
  - phase: 01-render-foundation
    provides: "reelkit renderer, spec loader, bundled fonts, specprobe, safe-zone layout (Plans 01-03)"
provides:
  - "tools/reelkit/doctor.py + tools/doctor.py: six-check render-environment report (ENV-01), --quiet / --json"
  - ".claude/hooks/session-start.sh: idempotent playwright pin install + one doctor summary line, never blocks (ENV-02)"
  - "tools/reelkit/golden.py + tools/golden.py: re-render of the 10 published specs vs the committed MP4s (ENV-03)"
  - "tools/tests/golden/manifest.json: 11 entries extracted from the committed MP4s (D-05, D-06)"
  - "tools/README.md: Korean guide for every phase-1 command"
affects: [phase-2-draft-generation]

actuals:
  tokens: 13300
  tasks: 2
  commits: 4
plan_head_before: 3243f31b1cb69cc2b0c173f4a9703c4e485e8510
plan_head_after: 9efe3b83e4b5eda2b7362a966fb5343770de9de9

tech-stack:
  added: []
  patterns:
    - "doctor and renderer share one code path (browser.launch / open_page / font_problems), so they cannot disagree"
    - "Playwright version mismatch is a warning; render ability is decided by the chromium and font-load checks"
    - "Golden compares structure exactly (frames, stream durations, boundaries, cover_ms, stdout) plus per-frame SSIM; renderer MP4 bytes are never compared"
    - "Manifest is built only from committed files and never from renderer output"

key-files:
  created:
    - tools/reelkit/doctor.py
    - tools/doctor.py
    - tools/tests/test_doctor.py
    - tools/reelkit/golden.py
    - tools/golden.py
    - tools/tests/golden/manifest.json
    - tools/tests/test_golden.py
  modified:
    - .claude/hooks/session-start.sh
    - tools/README.md

key-decisions:
  - "ENV-02 has two accepted routes, both proven: pinned (hook installs 1.63.0 into the user site) and no-install (system 1.64.1 + preinstalled Chromium via executable_path)"
  - "SSIM threshold stays 0.98 (lowest measured across the 10 reels: 0.9923); golden never relaxes it"
  - "A 재현 불가 reel with an upload-spec FAIL counts as a golden failure (exit 1) although its verdict stays 재현 불가"
  - "Hook calls doctor as python3 \"$PROJ\"/tools/doctor.py --quiet so the literal 'doctor.py --quiet' is greppable"

requirements-completed: [ENV-01, ENV-02, ENV-03]

coverage:
  - id: D1
    description: "python3 tools/doctor.py runs six checks in order, prints one line each plus a summary, exit 0 with 정상 here; --quiet prints exactly one stdout line and nothing on stderr; --json has ok, 6 checks, playwright, launch"
    requirement: ENV-01
    verification:
      - kind: unit
        ref: "tools/tests/test_doctor.py (18 tests, 5 CLI cases)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Broken Black face: doctor exits 1 and names NotoSansKR-Black.otf, the weight 900 load failure and the substituted system fonts; summary is never 정상 while font-files or font-load fail"
    requirement: ENV-01
    verification:
      - kind: unit
        ref: "test_doctor.Cli.test_broken_black_face_exits_1_naming_file_and_weight_900, PureChecks.test_summary_is_never_green_when_font_checks_fail"
        status: pass
    human_judgment: false
  - id: D3
    description: "Pinned route: fresh PYTHONUSERBASE, CLAUDE_CODE_REMOTE=true hook installs playwright 1.63.0, one stdout line with 정상, exit 0; second run exit 0 with empty stderr"
    requirement: ENV-02
    verification:
      - kind: integration
        ref: "plan Task 1 verify command 3 (rc1=0 rc2=0, ALL-PINNED-OK)"
        status: pass
    human_judgment: false
  - id: D4
    description: "No-install route: empty user site + PIP_NO_INDEX=1, hook exit 0 with one 정상 line (2 warnings); doctor --json ok true, playwright 1.64.1, launch /opt/pw-browsers/chromium; tax-deduction re-render stdout duration=26.1s cover_ms=1250, frames 781/781/781, min per-frame SSIM 0.993194"
    requirement: ENV-02
    verification:
      - kind: integration
        ref: "plan Task 1 verify command 4 (NOINSTALL-ALL-OK)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Hook still exits 0 with CLAUDE_CODE_REMOTE=true and a temp CLAUDE_ENV_FILE, and still writes AGENT_BROWSER_EXECUTABLE_PATH=/opt/pw-browsers/chromium; exits 0 immediately without CLAUDE_CODE_REMOTE"
    requirement: ENV-02
    verification:
      - kind: integration
        ref: "manual run with mktemp CLAUDE_ENV_FILE: rc=0, env file holds the export line; local run rc=0"
        status: pass
    human_judgment: false
  - id: D6
    description: "python3 tools/golden.py: per reel frames, boundaries, cover_ms, min SSIM, upload spec; last line 'golden: PASS 10/10 (재현 불가 1)', exit 0; savings-interest reported as 재현 불가 with its spec result; git status under 2026/reels empty"
    requirement: ENV-03
    verification:
      - kind: integration
        ref: "python3 tools/golden.py (rc=0, 82 s with 4 jobs); git status --porcelain -- 2026/reels empty"
        status: pass
    human_judgment: false
  - id: D7
    description: "Manifest: 11 entries, tax-deduction frames 781 / 21 boundaries, savings-interest not-reproducible (frames 622), len(boundaries) == states - 1 for all 10, spec and MP4 sha256 match the committed files"
    requirement: ENV-03
    verification:
      - kind: unit
        ref: "test_golden.GoldenManifestTest (9 tests) and the plan's manifest-ok python check"
        status: pass
    human_judgment: false
  - id: D8
    description: "Failure detection: changed MP4 hash, changed spec hash and a tampered frames/boundary/cover_ms entry each give FAIL with Korean reasons; MP4 outside the manifest is listed as 기준 목록 밖 and not judged; published files unchanged after the render tests"
    requirement: ENV-03
    verification:
      - kind: unit
        ref: "test_golden.GoldenUnitTest, GoldenRenderTest.test_structural_mismatch_fails_with_reasons, test_zz_published_reels_untouched"
        status: pass
    human_judgment: false
  - id: D9
    description: "Whole phase suite green: python3 -m unittest discover -s tools/tests (98 tests, 212 s)"
    requirement: ENV-03
    verification:
      - kind: integration
        ref: "python3 -m unittest discover -s tools/tests -> Ran 98 tests OK"
        status: pass
    human_judgment: false

duration: 17 min
completed: 2026-10-28
status: complete
---

# Phase 1 Plan 04: Doctor, SessionStart Pin Hook and Golden Regression Summary

**`doctor.py` reports Chromium / bundled font / ffmpeg health (and which Playwright and launch path it used), the SessionStart hook pins Playwright 1.63.0 without ever blocking a session, and `golden.py` proves all 10 published reels re-render with identical frames, durations, scene boundaries, cover time and per-frame SSIM >= 0.98**

## Performance

- **Duration:** about 17 min (2026-10-28T21:10Z to 21:27Z)
- **Tasks:** 2, both TDD (RED + GREEN commits each)
- **Files:** 9 changed (7 created, 2 modified), 1461 insertions
- **Tests:** 98 in `tools/tests` (18 doctor, 26 golden, 54 earlier), all OK in 212 s

## Accomplishments

- **ENV-01.** `python3 tools/doctor.py` runs playwright, chromium, font-files, font-load, ffmpeg, ffprobe in that order. Failures name cause and fix in Korean (`playwright 미설치 → python3 -m pip install --user -r tools/requirements.txt`, the changed or missing font file by name, `libx264 없음`). A garbage `NotoSansKR-Black.otf` gives exit 1 with both `font-files` (sha256 mismatch, file named) and `font-load` (`폰트 900 (NotoSansKR-Black.otf) 로드 실패: 상태 error / ... 대신 시스템 폰트 'Liberation Serif', 'Inter', 'WenQuanYi Zen Hei' 로 그려집니다`). The font-load check calls `browser.open_page` + `font_problems`, the renderer's own path.
- **ENV-02.** The hook block (appended after the unchanged AGENT_BROWSER_EXECUTABLE_PATH block) compares the pin in `tools/requirements.txt` with the installed version and runs a bounded `pip install --user --retries 1 --timeout 20` only on mismatch, inside an `if !` guard. Its only stdout is the doctor summary line. It runs no browser download and no version-control command.
- **ENV-03.** `python3 tools/golden.py` (82 s, 4 jobs) re-renders the 10 specs with the legacy layout into temp dirs, compares to the manifest built from the committed MP4s, and ends `golden: PASS 10/10 (재현 불가 1)`.

### Doctor output, pinned route (fresh user site after the hook installed 1.63.0, and the normal user site)

```
릴스 렌더 환경 점검: 정상 (playwright 1.63.0 (고정 버전) · Chromium 153.0.8010.12 (기본 실행) · 폰트 3/3 · ffmpeg 6.1.1-3ubuntu5)
```

`doctor.py --json`: `ok` true, `playwright` "1.63.0", `launch` "default". The hook's first run printed exactly this one line (exit 0); its second run printed it again with empty stderr (nothing reinstalled).

### Doctor output, no-install route (empty user site, PIP_NO_INDEX=1)

```
릴스 렌더 환경 점검: 정상 (playwright 1.64.1 사용 중 (고정 1.63.0 아님) · 기본 실행 실패 → /opt/pw-browsers/chromium 로 폴백함 (Chromium 153.0.8010.12) · 폰트 3/3 · ffmpeg 6.1.1-3ubuntu5), 경고 2건
```

`doctor.py --json`: `ok` true, `playwright` "1.64.1", `launch` "/opt/pw-browsers/chromium". The hook exited 0; its stderr held only the pip "no matching distribution" error and `playwright 1.63.0 설치 실패 — python3 tools/doctor.py 로 원인을 확인하세요`. Re-render through that route: `python3 tools/reel.py 2026/reels/specs/2026-10-26-tax-deduction.json <tmp>/t.mp4` printed `duration=26.1s cover_ms=1250`, frames 781/781/781, minimum per-frame SSIM 0.993194, `spec: PASS 9/9`.

### Full `python3 tools/golden.py` report

```
PASS  2026-10-19-rate-secret-1  frames 730/730  경계 19 일치  cover_ms 1250  SSIM 최소 0.9938  규격 PASS
재현 불가  2026-10-19-savings-interest  (원고 없음, D-06)  규격 PASS
PASS  2026-10-21-rate-secret-2  frames 705/705  경계 18 일치  cover_ms 1250  SSIM 최소 0.9985  규격 PASS
PASS  2026-10-24-rate-secret-3  frames 705/705  경계 18 일치  cover_ms 1250  SSIM 최소 0.9923  규격 PASS
PASS  2026-10-26-tax-deduction  frames 781/781  경계 21 일치  cover_ms 1250  SSIM 최소 0.9932  규격 PASS
PASS  2026-10-28-salary-two-owners-1  frames 654/654  경계 16 일치  cover_ms 1250  SSIM 최소 0.9932  규격 PASS
PASS  2026-10-29-ebook-event  frames 705/705  경계 18 일치  cover_ms 1250  SSIM 최소 0.9952  규격 PASS
PASS  2026-10-31-salary-two-owners-2  frames 756/756  경계 20 일치  cover_ms 1250  SSIM 최소 0.9941  규격 PASS
PASS  2026-11-02-salary-two-owners-3  frames 756/756  경계 20 일치  cover_ms 2100  SSIM 최소 0.9931  규격 PASS
PASS  2026-11-04-salary-two-owners-4  frames 730/730  경계 19 일치  cover_ms 1250  SSIM 최소 0.9930  규격 PASS
PASS  2026-11-07-salary-two-owners-5  frames 654/654  경계 16 일치  cover_ms 1250  SSIM 최소 0.9952  규격 PASS
golden: PASS 10/10 (재현 불가 1)
```

Boundary counts equal the grounded 19/18/18/21/16/18/20/20/19/16 and `states - 1` for every reproducible entry. The lowest SSIM across all frames of all reels is 0.9923 (rate-secret-3), matching the research measurement; the 0.98 threshold was not touched.

## Task Commits

1. **Task 1 RED: failing tests for doctor** - `d9a7d02` (test)
2. **Task 1 GREEN: doctor CLI and SessionStart pin hook** - `3c42f81` (feat)
3. **Task 2 RED: failing tests for golden regression** - `f87611f` (test)
4. **Task 2 GREEN: golden regression, manifest, README** - `9efe3b8` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## TDD Gate Compliance

Same approach as Plans 02-03: RED commits carry no-op placeholders (`reelkit/doctor.py`, `reelkit/golden.py` and the CLI stubs) so the test modules import. Task 1 RED: 18 tests, 15 failures and 1 error on assertions against the placeholders (not import or syntax faults). Task 2 RED: the manifest-reading classes error in `setUpClass` because `manifest.json` does not exist yet and the placeholder `check_reel` is a stub; the failure is the missing deliverable, not a fixture or import fault. GREEN: 18/18 and 26/26 pass. No REFACTOR commit.

## Files Created/Modified

- `tools/reelkit/doctor.py` - Check, Report, read_pin, installed_playwright, check_playwright_version, check_chromium, check_font_files, check_font_load, check_ffmpeg, check_ffprobe, run_checks, summarize, main
- `tools/doctor.py` - CLI entry
- `.claude/hooks/session-start.sh` - appended "릴스 렌더 환경 고정" block (PROJ, REQ, PW_PIN, PW_CUR); existing lines unchanged; settings.json untouched
- `tools/reelkit/golden.py` - constants, sha256/frame_count/stream_durations/boundaries/ssim_values, build_manifest, check_reel, unlisted_mp4s, run, format_report, main
- `tools/golden.py` - CLI entry
- `tools/tests/golden/manifest.json` - 11 entries from the committed MP4s and specs
- `tools/tests/test_doctor.py`, `tools/tests/test_golden.py`
- `tools/README.md` - reel.py (flags, exit codes 0-4, legacy vs new, overlay names), doctor.py, specprobe.py, golden.py, unittest command, fonts, requirements pin, drafts rule; original lines kept

## Decisions

- Playwright version mismatch is a warning, never a failure; the summary head names the Playwright version in use and the launch path.
- `golden.check_reel` verifies the committed MP4/spec sha256 before rendering, so a changed published file fails fast without spending a render.
- `format_report`/exit code treat a 재현 불가 reel whose upload-spec check fails as a golden failure.
- `run()` uses a `ProcessPoolExecutor`; results are returned in manifest order.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] RED commits needed no-op placeholders**
- **Found during:** both RED steps
- **Issue:** the test modules import `reelkit.doctor` / `reelkit.golden`, which did not exist.
- **Fix:** committed minimal placeholders with the tests, replaced in the GREEN commits (same as Plans 02-03).
- **Commits:** d9a7d02, f87611f

**2. [Rule 1 - Bug] Hook line did not contain the literal `doctor.py --quiet`**
- **Found during:** Task 1 acceptance check (`grep -c 'doctor.py --quiet'` returned 0)
- **Issue:** the first draft wrote `python3 "$PROJ/tools/doctor.py" --quiet`, the quote between `doctor.py` and `--quiet` broke the required key link pattern.
- **Fix:** `python3 "$PROJ"/tools/doctor.py --quiet || true`; behavior identical, re-verified the hook (rc 0, one 정상 line).
- **Files modified:** .claude/hooks/session-start.sh
- **Commit:** 3c42f81

**3. [Rule 2 - Missing critical] Extra tests beyond the plan's behavior list**
- Added tests that a changed MP4 hash, a changed spec hash and a tampered frames/boundary/cover_ms entry each produce FAIL with Korean reasons, and that an unlisted MP4 is listed not judged, so a green golden cannot come from a verdict that always passes.
- **Files modified:** tools/tests/test_golden.py
- **Commit:** f87611f

**Total deviations:** 3 (Rule 3, Rule 1, Rule 2). **Impact:** none on the plan's behavior.

## Authentication Gates

None.

## Issues Encountered

None. No package was installed outside the pinned `playwright==1.63.0` (T-01-SC): the only installs were the hook simulations into temporary `PYTHONUSERBASE` directories. `PYTHONDONTWRITEBYTECODE=1` was set throughout; no `__pycache__` exists.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-01-12/13 (install only on exact-pin mismatch, `--user`, bounded retries, `if !` guard, `|| true` on doctor, verified exit 0 with a fresh user site and with the index unreachable), T-01-14/15 (manifest from committed files only, hashes rechecked, renders in temp dirs, `test_zz_published_reels_untouched` and empty `git status -- 2026/reels`) mitigated as planned.

## User Setup Required

None.

## Next Phase Readiness

- Phase 1 render foundation is complete: pinned/no-install environment, doctor, bundled fonts, spec loader, upload-spec probe, safe-zone layout checks and a golden regression that protects the 10 published reels.
- Open human item carried over from Plan 03 (D8): calibrate `constants.SAFE` (top 270) against a real phone view of a `--layout new` overlay PNG.
- Assumption A5 (hook stdout reaches the session context) is still inferred from the existing hook comment, not observed.

## Self-Check: PASSED

All 9 listed files exist; commits `d9a7d02`, `3c42f81`, `f87611f`, `9efe3b8` are ancestors of HEAD; `python3 -m unittest discover -s tools/tests` (98 tests) OK; golden ends `golden: PASS 10/10 (재현 불가 1)`; `git status --porcelain -- 2026/reels` empty; no `__pycache__`/`.pyc`.

---
*Phase: 01-render-foundation*
*Completed: 2026-10-28*
