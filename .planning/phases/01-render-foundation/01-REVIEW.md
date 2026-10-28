---
phase: 01-render-foundation
reviewed: 2026-10-28T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - .claude/hooks/session-start.sh
  - tools/reel.py
  - tools/reelkit/doctor.py
  - tools/reelkit/encode.py
  - tools/reelkit/golden.py
  - tools/reelkit/timeline.py
  - tools/tests/test_doctor.py
  - tools/tests/test_encode.py
  - tools/tests/test_golden_failures.py
  - tools/tests/test_session_hook.py
  - tools/tests/test_timeline.py
findings:
  critical: 1
  warning: 3
  info: 9
  total: 13
status: issues_found
---

# Phase 1: Code Review Report (re-review after WR-01..WR-06 fixes)

**Reviewed:** 2026-10-28
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This is an incremental re-review of the files changed by the six WR fix commits (`bfeddc6`, `2ddd943`, `11c89e7`, `f836dc7`, `f0c63df`, `71625f4`). I read each file in full and ran the new and changed unit tests. They all pass: 43 tests across `test_timeline`, `test_session_hook`, `test_golden_failures`, `test_encode` and `test_doctor`. I did not re-run the golden render suite. No new security issues were found. All subprocess calls still use argument lists with no shell.

Five of the six warnings are resolved. WR-03 is only partly resolved. The new per-reel `except Exception` stops the run from aborting inside `check_reel`. But the report formatter then crashes with a `KeyError` on exactly the partial results this fix produces, so the user still gets a traceback and loses every reel's report (CR-01). Two smaller problems in the same area are WR-07 and WR-08.

### Disposition of the earlier warnings

| ID | Status | Notes |
|----|--------|-------|
| WR-01 | Resolved | `encode_concat` now writes `<out>.part.mp4`, replaces only on success, and raises `EncodeError` with ffmpeg's last stderr line. `reel.main` maps `EncodeError`, `OSError`, `SubprocessError` and Playwright `Error` to exit 2. `SpecError` is a `ValueError`, so it is caught first and a missing spec file stays exit 1. The tests cover these paths. Only the doc text is stale (IN-07). |
| WR-02 | Resolved | The top-level import guard is gone. The `ImportError` handler re-raises unless `e.name` begins with `playwright`. |
| WR-03 | Partially resolved (reopened) | `check_reel` no longer aborts the run, but `format_report` crashes on the partial `details` it returns (CR-01). Render-time environment errors are also reported as reel FAILs with exit 1 (WR-07). |
| WR-04 | Resolved | `round()` is used in `timeline.cover_ms` and in the `low`/`high` check. The test covers first scenes of 1 to 12 lines, including 2950 and 8050. |
| WR-05 | Resolved, with a residual note | The pin parser now matches `doctor.read_pin` (spaces, CRLF, trailing comment). The hook retries with `PIP_BREAK_SYSTEM_PACKAGES=1`, omits `--user` inside a venv, and writes a failure stamp. The tests use a fake python3 and cover these cases. A real pip, PEP 668 or offline run was not exercised (see IN-08). |
| WR-06 | Resolved | `_run` has a 30 s timeout and turns `TimeoutExpired` and `OSError` into return code 127. `check_ffmpeg` and `check_ffprobe` report FAIL lines. |

## Critical Issues

### CR-01: `golden.format_report` raises `KeyError` on the partial results the WR-03 fix now produces

**File:** `tools/reelkit/golden.py:277-283` (producer: `golden.py:196-241`)
**Issue:** `check_reel` now converts any mid-judging exception into a FAIL result. But `details` is filled step by step:
- `frames` is set at line 197.
- `boundaries` is set at line 208.
- `cover_ms` is set at line 217.
- `ssim_min` is set at line 228.
- `spec` is set at line 234.

`_fmt_line` then gates on `if "frames" in d:` and reads `d['boundaries']`, `d['cover_ms']`, `d['ssim_min']` and `d['spec']` unconditionally. If `stream_durations`, `boundaries` or `ssim_values` fails after `frames` is set, `_fmt_line` raises `KeyError`. I reproduced both of these:
- `ReelResult("x", FAIL, {"frames": (1, 1)}, [...])` gives `KeyError('boundaries')`.
- A result with everything but `ssim_min` gives `KeyError('ssim_min')`.

`main` catches only `ValueError`, `OSError`, `SubprocessError` and `BrokenExecutor`. The result is a raw traceback, exit 1, and no per-reel report. The 10 other reels' results are lost, which is the outcome WR-03 asked to prevent. The new tests only call `check_reel`. None of them runs `format_report` or `_fmt_line` on the returned result, so the crash is not caught.

**Fix:** Make `_fmt_line` tolerant of missing keys:
```python
parts = [f"{r.verdict:<4}  {r.stem}"]
if "frames" in d:
    parts.append(f"frames {d['frames'][0]}/{d['frames'][1]}")
if "boundaries" in d:
    mismatch = d.get("boundary_mismatch")
    parts.append(f"경계 {d['boundaries']} 일치" if mismatch is None else f"경계 {mismatch}번째 불일치")
if "cover_ms" in d:
    parts.append(f"cover_ms {d['cover_ms']}")
if "ssim_min" in d:
    parts.append(f"SSIM 최소 {d['ssim_min']:.4f}")
if "spec" in d:
    parts.append(f"규격 {d['spec']}")
```
Add a test that feeds each partial `details` shape, or the `check_reel` result from the existing mocked failure tests, through `golden.format_report`.

## Warnings

### WR-07: golden reports render-time environment failures as reel FAILs (exit 1), contradicting its own exit-code contract

**File:** `tools/reelkit/golden.py:186-193, 317-320`
**Issue:** `main` states that environment problems exit 2 and are kept apart from a reel FAIL (exit 1). `check_reel` catches `Exception` around `render_reel`, and that includes the environment failures `reel.py` classifies as exit 2:
- `ImportError` for a missing playwright
- `BrowserLaunchError`
- `FontLoadError`
- `EncodeError`

Each of the 10 reels is then reported as `FAIL 렌더 실패: ...` with exit 1. This produces ten separate, identical failures for one root cause, and a caller cannot tell "the environment is broken" from "the renderer regressed". The tools README documents golden exit 1 as "a reel failed".

**Fix:** Let environment errors propagate. For example, catch `SpecError` and the genuine render regressions as FAIL, and re-raise `(BrowserLaunchError, FontLoadError, EncodeError, ImportError)`. Then add `EncodeError`, `BrowserLaunchError` and `FontLoadError` to the `except` tuple in `main` that returns 2. Alternatively, run `doctor` once up front. Add a test for it.

### WR-08: Failed pip install leaves no stamp when pip succeeds but the version stays wrong, so the hook reinstalls every session

**File:** `.claude/hooks/session-start.sh:38-50`
**Issue:** The stamp is written only when both pip attempts return non-zero. If pip returns 0 but the pin still does not match the importable version, the `PW_PIN != PW_CUR` condition stays true. This happens when:
- `--user` installs a copy that a system or venv `site-packages` copy shadows.
- An unusual version string such as `1.63.0.post1` is normalized differently.

Every later session then repeats the pip run, up to ~20 s per run with network. The hook has no post-install check that the install worked.

**Fix:** After the install block, recompute `PW_CUR` with the same `importlib.metadata` call. If it still differs from `PW_PIN`, write the stamp and print the same stderr hint.

### WR-09: golden pre-render file reads and the render import run outside the per-reel guard

**File:** `tools/reelkit/golden.py:171, 183, 186`
**Issue:** `sha256(committed)`, `sha256(spec_path)` and `from .render import render_reel` run before the `try`. An `OSError` there, such as a permission error or a file removed mid-run, propagates out of the worker. `pool.map` re-raises it at the matching `zip` step and discards the results of the remaining reels. `main` then returns 2 with no per-reel report. This is the same class of issue as WR-03, but at the head of the function.

**Fix:** Wrap the pre-render checks in the same per-reel guard. Return a FAIL `ReelResult` for `OSError`, and keep any `ImportError` loud.

## Info

### Carried forward from the first review (out of fix scope; none were touched)

`git diff 2d81d01..HEAD` shows no change to `spec.py`, `browser.py`, `layout.py`, or the doctor ffmpeg probe. `session-start.sh` changed only below line 24.

### IN-01: Legacy markup check does not require balanced tags — OPEN (unchanged)

**File:** `tools/reelkit/spec.py:49-65`
**Issue:** `_check_text` only ensures every `<` starts one of the four allowed tags. An unclosed `<g>` leaves the outer span open and silently changes the layout. This is not exploitable.
**Fix:** Count `<g>`/`</g>` and `<s>`/`</s>` and raise `SpecError` on imbalance.

### IN-02: Spec loader reports a UTF-8 BOM as a JSON syntax error at line 1 column 1 — OPEN (unchanged)

**File:** `tools/reelkit/spec.py:19`
**Issue:** `read_text(encoding="utf-8")` keeps a leading BOM. The user sees only "줄 1 열 1".
**Fix:** Read with `encoding="utf-8-sig"`.

### IN-03: Chromium fallback path selection sorts lexicographically — OPEN (unchanged)

**File:** `tools/reelkit/browser.py:41-42`
**Issue:** `sorted(glob(...))[-1:]` compares path strings, so `chromium-999` sorts after `chromium-1243`.
**Fix:** Sort by the integer revision parsed from the path.

### IN-04: `SMALL` font-size checks can never fire — OPEN (unchanged)

**File:** `tools/reelkit/layout.py:165-171`
**Issue:** The checked font size comes from the same constant that sets it, so the check is dead validation.
**Fix:** Keep it as a documented guard with a test, or remove it.

### IN-05: Doctor's ffmpeg probe does not exercise the features the render uses — OPEN (unchanged)

**File:** `tools/reelkit/doctor.py:136-151` (now about line 141-160)
**Issue:** The probe covers only `lavfi color` plus libx264. The render also depends on the `concat` demuxer, `anullsrc`, the `fps` filter and aac. WR-06 added timeouts but did not change what is probed.
**Fix:** Add a probe that mirrors the real encode, such as `-f lavfi -i anullsrc=... -c:a aac -t 0.1 -f null -`.

### IN-06: Hook installs unpinned `@opengsd/gsd-core@latest` and `agent-browser` under `set -e` — OPEN (unchanged)

**File:** `.claude/hooks/session-start.sh:4, 12, 17`
**Issue:** A failed npm install aborts the whole hook under `set -euo pipefail`, so the Playwright pin and the doctor never run. The commit comment says the Phase 1 block "does not block the session", but that holds only if the earlier npm steps succeed.
**Fix:** Pin the versions, or append `|| echo ... >&2` to each npm line.

### New Info items from this re-review

### IN-07: reel.py docstring and tools/README exit-code text omit the new exit-2 causes

**File:** `tools/reel.py:60`, `tools/README.md:27`
**Issue:** Exit 2 is documented as "playwright not installed, Chromium launch failure, bundled font load failure". It now also covers ffmpeg/encode failure, unwritable output, and Playwright runtime errors, which is the main point of WR-01. Phase 2 automation reads this contract.
**Fix:** Add "ffmpeg/ffprobe 실행·인코딩 실패, 출력 파일 쓰기 실패" to both places.

### IN-08: The failure stamp is a predictable file in a shared temp directory

**File:** `.claude/hooks/session-start.sh:37, 48`
**Issue:** `: > "$PW_STAMP"` writes `${TMPDIR:-/tmp}/.reelkit-pw-install-failed-<pin>`. If `/tmp` is shared and another user pre-creates this path as a symlink, the redirect truncates the link target. On a single-user cloud container the risk is negligible. The stamp also suppresses a retry for the rest of the container's life, even after the network comes back. The user must delete it by hand. The failure message does not name the stamp file.
**Fix:** Keep the stamp under `$PROJ/.planning` or `$HOME/.cache` instead of `/tmp`, and mention the path in the message. Also create it only if it is not a symlink (`[ ! -L ]`).

### IN-09: New tests do not cover the integrated failure path they were written for

**File:** `tools/tests/test_golden_failures.py:20-40`, `tools/tests/test_encode.py:70-72`
**Issue:**
- `CheckReelErrors` asserts only on `check_reel`'s return value, never on `format_report`, which is how CR-01 slipped through.
- `test_playwright_error_is_environment_error` imports `playwright` directly, so it errors rather than skips when Playwright is absent. That is the exact situation the reel.py exit-2 path covers.

**Fix:** Pass the failing result through `golden.format_report` in each test. Use `self.skipTest` when `playwright` cannot be imported, or build a fake error class and patch `_playwright_error_types`.

---

_Reviewed: 2026-10-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
