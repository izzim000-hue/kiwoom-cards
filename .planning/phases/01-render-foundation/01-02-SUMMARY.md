---
phase: 01-render-foundation
plan: 02
subsystem: infra
tags: [spec-loader, markup-allowlist, input-validation, font-provenance, gitignore]

requires:
  - phase: 01-render-foundation
    provides: "tools/reelkit package, reel.py shim, vendored Noto Sans KR (Plan 01)"
provides:
  - "tools/reelkit/spec.py: SpecError, ALLOWED_TAGS, load_spec, check_legacy_markup"
  - "reel.py exit code 1 with Korean scene/line message for bad specs"
  - "tools/tests/test_spec.py (17 unittest cases)"
  - "tools/fonts/README.md font provenance with digests equal to constants.FONT_SHA256"
  - ".gitignore for drafts and render intermediates (D-08)"
affects: [01-03, 01-04, phase-2-draft-generation]

actuals:
  tokens: 3500
  tasks: 2
  commits: 3
plan_head_before: 012955698876714db581d93ce7ebec1d4b37970d
plan_head_after: fdb954ce3ca4438f6a4c262e0dab2b97b5eb104d

tech-stack:
  added: []
  patterns:
    - "Fail before launch: spec is loaded and markup-checked before the work dir or Chromium exists"
    - "Loader returns the parsed dict untouched; published specs are never rewritten (D-05)"
    - "stdlib unittest with tempfile fixtures, CLI cases via subprocess"

key-files:
  created:
    - tools/reelkit/spec.py
    - tools/tests/test_spec.py
    - tools/fonts/README.md
    - .gitignore
  modified:
    - tools/reelkit/render.py
    - tools/reel.py

key-decisions:
  - "Legacy raw insertion is kept for output identity (D-05) and guarded by a four-tag allowlist (<g> </g> <s> </s>) checked before anything is launched"
  - "reel.py exit codes are now 0 ok / 1 spec-input error / 2 environment error"

requirements-completed: [ENV-02, ENV-03]

coverage:
  - id: D1
    description: "All 10 committed specs load unchanged and pass the allowlist; malformed specs raise Korean SpecError naming file or 1-based scene/line"
    requirement: ENV-03
    verification:
      - kind: unit
        ref: "tools/tests/test_spec.py (python3 -m unittest discover -s tools/tests -p test_spec.py), 17 tests"
        status: pass
    human_judgment: false
  - id: D2
    description: "reel.py exits 1 with 'scene 1 line 1' on disallowed markup, writes no MP4, no traceback; missing spec path also exits 1 with no traceback"
    requirement: ENV-03
    verification:
      - kind: integration
        ref: "tools/tests/test_spec.py::CliExitCodes plus the plan's bad.json shell check (rc=1)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Loader swap leaves the legacy output unchanged: tax-deduction re-render prints duration=26.1s cover_ms=1250, 781/781/781 frames, min per-frame SSIM 0.993194"
    requirement: ENV-03
    verification:
      - kind: integration
        ref: "python3 tools/reel.py 2026/reels/specs/2026-10-26-tax-deduction.json <tmp>/t.mp4 + ffmpeg ssim + ffprobe -count_frames"
        status: pass
    human_judgment: false
  - id: D4
    description: "tools/fonts/README.md records source URLs, version 2.004, retrieval date, OFL 1.1, FONT_VARIANT=original and a bytes/sha256/weight table matching constants.FONT_SHA256 and the files on disk"
    requirement: ENV-02
    verification:
      - kind: other
        ref: "plan Task 2 verify command 1 (hashlib recompute against README and FONT_SHA256): variant original, no missing digests or sizes"
        status: pass
    human_judgment: false
  - id: D5
    description: ".gitignore holds exactly the five D-08 lines; drafts and intermediates ignored, published reels stay tracked"
    requirement: ENV-02
    verification:
      - kind: other
        ref: "plan Task 2 verify command 2 (git check-ignore probes + git ls-files -ci --exclude-standard empty): gitignore-ok"
        status: pass
    human_judgment: false

duration: 8 min
completed: 2026-10-28
status: complete
---

# Phase 1 Plan 02: Spec Loader, Markup Allowlist, Font Provenance Summary

**A stdlib spec loader with a four-tag legacy markup allowlist rejects bad specs with Korean scene/line messages (exit 1) before any browser launch, while the tax-deduction re-render stays identical (781 frames, min SSIM 0.9932); font provenance README and D-08 .gitignore added**

## Performance

- **Duration:** about 8 min
- **Tasks:** 2 (Task 1 as TDD: RED + GREEN commits)
- **Files:** 6 changed (4 created, 2 modified), 264 insertions, 4 deletions

## Accomplishments

- `load_spec(path)` turns an unreadable file, invalid JSON, a missing/empty `scenes`, a scene without lines, a non-string `top`/line, or a non-string `basis` into `SpecError` with a Korean message naming the file or the 1-based scene/line. It returns the parsed dict untouched and never writes.
- `check_legacy_markup(spec)` accepts only `<g>`, `</g>`, `<s>`, `</s>` at every `<` in top/lines/basis; `&` and everything else pass. `render_reel` runs it right after `_read_spec` for the legacy layout, before the work dir and before Chromium.
- `tools/reel.py` prints `원고 오류: ...` to stderr and returns 1 on `SpecError`; docstring exit codes updated to 0 / 1 / 2.
- All 10 committed specs load equal to `json.load` and pass the allowlist; `git status --porcelain -- 2026/reels` is empty after all runs.
- Test count: 17 (`python3 -m unittest discover -s tools/tests -p test_spec.py -v`, OK).
- Bad-markup stderr: `원고 오류: scene 1 line 1: 허용되지 않은 마크업 '<i>x' — legacy 원고에는 <g>, </g>, <s>, </s> 만 쓸 수 있음` (rc=1, no MP4, no traceback).
- Missing-file stderr: `원고 오류: 원고 파일을 열 수 없음: /nonexistent.json (No such file or directory)` (rc=1).
- Tax-deduction re-render after the loader swap: stdout `duration=26.1s cover_ms=1250`, frames 781/781/781, minimum per-frame SSIM 0.993194 (threshold 0.98).
- `tools/fonts/README.md` documents FONT_VARIANT `original` (unmodified upstream files), the three raw.githubusercontent.com URLs plus LICENSE, Noto Sans CJK 2.004, SIL OFL 1.1, retrieved 2026-10-28, and a file/bytes/sha256/weight table (plus OFL.txt) whose digests equal `constants.FONT_SHA256` and the files on disk.
- `.gitignore` has exactly the five D-08 lines; `git ls-files -ci --exclude-standard` prints nothing and the published tax-deduction MP4 is not ignored.

## Task Commits

1. **Task 1 RED: failing tests for loader/allowlist** - `012047b` (test)
2. **Task 1 GREEN: loader, allowlist, render/CLI wiring** - `dae1c6a` (feat)
3. **Task 2: font README and .gitignore** - `fdb954c` (docs)

**Plan metadata:** committed separately (docs: complete plan)

## TDD Gate Compliance

RED: 17 tests ran, 13 failed (11 failures, 2 errors that were the no-op placeholder raising JSONDecodeError/FileNotFoundError instead of SpecError), 4 passed (tests that the placeholder legitimately satisfied: constants, the committed-specs round trip, accepted markup, untouched return). `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK` (reason `target_test_failed`, target `test_i_tag_in_line`). Semantic assessment: the target tests failed on the planned assertions (SpecError not raised / no Korean message), not on import, syntax or fixture faults. The RED commit carries a minimal no-op `spec.py` so the test module imports. GREEN: 17/17 pass. No REFACTOR commit needed.

## Files Created/Modified

- `tools/reelkit/spec.py` - SpecError, ALLOWED_TAGS, load_spec, check_legacy_markup (stdlib only)
- `tools/tests/test_spec.py` - 17 unittest cases: 10 committed specs, malformed fixtures in a temp dir, allowlist cases, CLI exit codes
- `tools/reelkit/render.py` - `_read_spec` now returns `load_spec(spec_path)`; `check_legacy_markup(spec)` for the legacy layout before any launch; unused `json` import removed
- `tools/reel.py` - `SpecError` -> stderr + exit 1, docstring exit codes
- `tools/fonts/README.md` - font provenance and digest table
- `.gitignore` - D-08 entries

## Decisions

- Kept legacy raw insertion (needed for output identity with published reels, D-05) and made the allowlist the injection guard instead of escaping.
- Imported `check_legacy_markup`/`load_spec` by name in render.py to avoid colliding with `render_reel`'s local `spec` variable.
- README digests were taken from a hashlib recompute of the files and cross-checked against `FONT_SHA256` (all equal), not retyped from memory.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] RED commit needed a no-op placeholder spec.py**
- **Found during:** Task 1 RED
- **Issue:** the test module imports `reelkit.spec`, which did not exist; without it RED would be a load failure (INVALID_RED), not an assertion failure.
- **Fix:** committed a no-op `spec.py` (SpecError, ALLOWED_TAGS, passthrough load_spec, no-op check) with the tests, replaced in the GREEN commit.
- **Files modified:** tools/reelkit/spec.py
- **Commit:** 012047b

**Total deviations:** 1 auto-fixed (Rule 3). **Impact:** none on behavior; only the commit split.

## Issues Encountered

None. `PYTHONDONTWRITEBYTECODE=1` was set for all runs, so no `__pycache__` was created.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-01-18 (allowlist before launch, tested with `<i>`, script tag, `<g >`, `<gg>`, bare `<`), T-01-19 (all malformed input becomes SpecError, loader never writes) and T-01-20 (.gitignore) are mitigated as planned; no package installs.

## User Setup Required

None.

## Next Phase Readiness

- Ready for Plan 03 (v2 layout, basis/safe-area checks). `render_reel` has a layout-conditional markup check, so a future non-legacy layout skips the legacy allowlist.
- The other nine reels are still only checked at load/allowlist level; their rendered output is compared in Plan 04's golden run.

## Self-Check: PASSED

Created files exist (spec.py, test_spec.py, README.md, .gitignore); commits `012047b`, `dae1c6a`, `fdb954c` are ancestors of HEAD; test suite, bad-spec CLI check, tax-deduction regression, README digest check and .gitignore probe all re-run green; `git status --porcelain -- 2026/reels` empty; no tracked `__pycache__`/`.pyc`.

---
*Phase: 01-render-foundation*
*Completed: 2026-10-28*
