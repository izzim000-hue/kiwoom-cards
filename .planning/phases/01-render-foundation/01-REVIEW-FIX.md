---
phase: 01-render-foundation
fixed_at: 2026-10-28T00:00:00Z
review_path: .planning/phases/01-render-foundation/01-REVIEW.md
iteration: 2
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 1: Code Review Fix Report

## Iteration 2 (re-review: CR-01, WR-07, WR-08, WR-09)

**Fixed at:** 2026-10-28
**Source review:** .planning/phases/01-render-foundation/01-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 4 (1 critical, 3 warning; Info IN-01..IN-09 out of scope)
- Fixed: 4
- Skipped: 0

**Verification location:** all gates ran in the main checkout `/home/user/kiwoom-cards` (branch `ccr-f9cedca2-3o2v27`), no worktree (edits committed directly, not pushed).

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/tests`: 135 tests, OK (217 s).
- `PYTHONDONTWRITEBYTECODE=1 python3 tools/golden.py`: `golden: PASS 10/10 (재현 불가 1)`, exit 0, SSIM minimum 0.9923 (threshold 0.98 unchanged).
- `.claude/hooks/session-start.sh` with `CLAUDE_CODE_REMOTE=true`, temp `CLAUDE_ENV_FILE` and temp `TMPDIR`: exit 0, doctor summary printed, `export AGENT_BROWSER_EXECUTABLE_PATH=/opt/pw-browsers/chromium` still written, no stamp created.
- `2026/reels/` and `tools/tests/golden/manifest.json` untouched. No `__pycache__` left under `tools/`.

### Fixed Issues

#### CR-01: `golden.format_report` raises `KeyError` on partial results

**Files modified:** `tools/reelkit/golden.py`, `tools/tests/test_golden_failures.py`
**Commit:** 2d49a7c
**Status:** fixed
**Applied fix:** `_fmt_line` formats `frames`, `boundaries`, `cover_ms`, `ssim_min` and `spec` each only when present. New tests: every prefix of the details dict through `format_report`; a mocked mid-judging failure (`stream_durations` raises after `frames` is set) through `format_report`; and an integrated `golden.main([])` run (process pool swapped for a thread pool so mocks apply) with one reel failing mid-judging and a second reel failing the sha check. It asserts exit 1, a `FAIL` line with `판정 중 오류` for the first reel, the second reel still reported, last line `golden: FAIL 0/2 (재현 불가 0)`, empty stderr and no traceback. Confirmed the three new tests raise `KeyError: 'boundaries'` against the old code.

#### WR-09: pre-render file reads outside the per-reel guard

**Files modified:** `tools/reelkit/golden.py`, `tools/tests/test_golden_failures.py`
**Commit:** b22e7b3
**Status:** fixed
**Applied fix:** The `sha256(committed)` and `sha256(spec_path)` checks are wrapped in `try/except OSError` and return a FAIL `ReelResult` for that reel only. The `from .render import render_reel` import is handled under WR-07 (an unrelated `ImportError` there stays loud). Tests cover an unreadable MP4 and a spec that vanishes mid-run.

#### WR-07: render environment failures reported as ten reel FAILs (exit 1)

**Files modified:** `tools/reelkit/golden.py`, `tools/tests/test_golden_failures.py`, `tools/golden.py` (docstring), `tools/README.md` (golden exit codes)
**Commit:** 5096025
**Status:** fixed: requires human verification (exception classification is logic; unit-tested with mocks, and the real run only exercises the success path)
**Applied fix:** New `GoldenEnvError`. In `check_reel`, the errors `reel.py` maps to exit 2 (`ImportError` for playwright, `BrowserLaunchError`, `FontLoadError`, `EncodeError`, `OSError`, `SubprocessError`, Playwright `Error`) raised by the render step are re-raised as `GoldenEnvError`, and the outer judging `except Exception` now lets it through. `main` reports it once as `golden 환경 오류: ...` and returns 2. Genuine regressions stay FAIL/exit 1: `SpecError` from render, any other render exception, an `ImportError` not about playwright, and all judging-phase errors and metric mismatches. An `ImportError` at the `from .render import` line that is not about playwright still propagates. Tests: each environment error raises `GoldenEnvError`; `main` with every render raising `BrowserLaunchError` exits 2 with empty stdout; the FAIL cases above.

#### WR-08: hook reinstalls every session when pip exits 0 but the pin is still not importable

**Files modified:** `.claude/hooks/session-start.sh`, `tools/tests/test_session_hook.py`
**Commit:** 2ec89fd
**Status:** fixed: requires human verification (real pip shadowing was not exercised; the fake python3 now reports a post-install version)
**Applied fix:** After a pip run that exits 0, the hook recomputes the installed version with the same `importlib.metadata` call. A mismatch is treated as a failed install: same stderr hint, same stamp, so later sessions skip pip. The hook still always exits 0. Tests: successful install with the pin reached leaves no stamp; pip exit 0 with the version unchanged writes the stamp and the next session runs no pip.

### Skipped Issues

None.

### Notes

- IN-07 (doc text for exit-2 causes in `tools/reel.py` and `tools/README.md` line 27) is out of scope and untouched; only the golden exit-code text in README/`tools/golden.py` was updated for WR-07.
- REVIEW-FIX.md is not committed, as instructed.

---

# Iteration 1 (previous pass, retained)

**Fixed at:** 2026-10-28
**Source review:** .planning/phases/01-render-foundation/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (fix_scope critical_warning: 0 critical, 6 warning; the 6 Info findings are out of scope)
- Fixed: 6
- Skipped: 0

**Verification location:** all gates ran in the isolated review-fix worktree
(`.claude/worktrees/rf-01-10743-...`, branch `gsd-reviewfix/01-10743`), not in the
main checkout. The branch was then fast-forwarded into the user's branch and the
worktree removed, so the commits below are present in the main checkout.

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/tests`: 123 tests, OK (213 s, includes the golden render tests).
- `PYTHONDONTWRITEBYTECODE=1 python3 tools/golden.py`: `golden: PASS 10/10 (재현 불가 1)`, exit 0, SSIM minimum 0.9923 (threshold 0.98 unchanged).
- `.claude/hooks/session-start.sh` with `CLAUDE_CODE_REMOTE=true` and a temp `CLAUDE_ENV_FILE`: exit 0, doctor summary line printed, `export AGENT_BROWSER_EXECUTABLE_PATH=/opt/pw-browsers/chromium` still written.
- `tools/tests/golden/manifest.json`, `2026/reels/` and `2026/reels/specs/` are untouched (no diff against the pre-fix HEAD).

### Fixed Issues

#### WR-01: ffmpeg / runtime failures escape `reel.py` as tracebacks with exit code 1

**Files modified:** `tools/reelkit/encode.py`, `tools/reel.py`, `tools/tests/test_encode.py` (new)
**Commit:** bfeddc6
**Applied fix:** `encode_concat` now captures ffmpeg stderr, writes to `<out>.part.mp4` and `os.replace()`s it onto the output only on success, so a failed encode never truncates an existing MP4. Failures raise a new `EncodeError` with a Korean message that includes ffmpeg's last stderr line (missing ffmpeg, non-zero exit, unwritable/directory output). `reel.py` maps `EncodeError`, `OSError`, `subprocess.SubprocessError` and Playwright `Error` to exit code 2 with `렌더 환경 오류: ...`. Verified end to end: passing a directory as the output now exits 2 with a one-line message. Unit tests cover success, preserved existing output, missing ffmpeg, directory output, and each CLI exit-code mapping (spec error stays 1).

#### WR-02: `reel.py` import guard reports any ImportError as "playwright not installed"

**Files modified:** `tools/reel.py`, `tools/tests/test_encode.py`
**Commit:** 2ddd943
**Applied fix:** Removed the top-level `try/except ImportError` and import the reelkit modules plainly. The `except ImportError` around `render_reel` now prints the install hint (exit 2) only when `e.name` is `playwright` or a `playwright.*` submodule, and re-raises otherwise. Tests cover both branches.

#### WR-03: One failing reel aborts the entire golden run

**Files modified:** `tools/reelkit/golden.py`, `tools/tests/test_golden_failures.py` (new)
**Commit:** 11c89e7
**Applied fix:** `check_reel` now has an `except Exception` around the whole post-render judging body (covers `CalledProcessError` from ffprobe/ffmpeg and `ValueError` from empty ffprobe output) and records it as a FAIL reason for that reel only, so the rest are still reported and the temp dir is still cleaned. `main` also catches `OSError`, `subprocess.SubprocessError` and `BrokenExecutor` and returns 2 with `golden 환경 오류`, keeping exit 1 for "a reel failed". Tests use mocks (no rendering).

#### WR-04: `cover_ms` truncates a float and is off by 1 ms for 4-line and 10-line first scenes

**Files modified:** `tools/reelkit/timeline.py`, `tools/reelkit/golden.py`, `tools/tests/test_timeline.py` (new)
**Commit:** f836dc7
**Applied fix:** `timeline.cover_ms` uses `round(...)`. The matching `low`/`high` range check in `golden.check_reel` (line 216) also uses `round(...)` (the review only named `low`, `high` had the same truncation). Confirmed that every `cover_ms` in `manifest.json` is unchanged (no manifest edit). New test asserts exact values for 1..12-line first scenes, including 2950 and 8050.

#### WR-05: SessionStart hook can run a slow failing pip install on every session

**Files modified:** `.claude/hooks/session-start.sh`, `tools/tests/test_session_hook.py` (new)
**Commit:** f0c63df
**Status:** fixed: requires human verification (the real pip/PEP 668/virtualenv/offline behaviours cannot be exercised inside this container; the tests use a fake `python3`)
**Applied fix:** The pin is parsed with the same tolerance as `doctor.read_pin` (spaces around `==`, CRLF, trailing comments), so a matching install never triggers pip. On failure the hook retries once with `PIP_BREAK_SYSTEM_PACKAGES=1`, omits `--user` inside a virtualenv, and writes a stamp file `${TMPDIR:-/tmp}/.reelkit-pw-install-failed-<pin>` so the same container does not repeat a failing install every session. The hook still always exits 0 and the doctor summary remains its only stdout. Tests (fake python3 and agent-browser, temp HOME/TMPDIR) cover CRLF, spaced/commented pins, successful install, failure + retry + stamp, and the unchanged `AGENT_BROWSER_EXECUTABLE_PATH` export. Out of scope (IN-06) and left alone: the unpinned `@opengsd/gsd-core@latest` / `agent-browser` installs earlier in the same file.

#### WR-06: Doctor/hook subprocesses have no timeout

**Files modified:** `tools/reelkit/doctor.py`, `tools/tests/test_doctor.py`
**Commit:** 71625f4
**Applied fix:** `doctor._run` takes a 30 s timeout (`PROBE_TIMEOUT`) and converts `TimeoutExpired`/`OSError` into a `CompletedProcess` with return code 127 and the error text on stderr, so `check_ffmpeg` and `check_ffprobe` report a FAIL line instead of hanging or crashing. Three tests added to `test_doctor.py`.

### Skipped Issues

None.

### Notes for the orchestrator

- README (`tools/README.md`) exit-code text was not changed: its description of exit 2 (environment error) is now more accurate than before but still correct. ffmpeg encode failures could optionally be added to that list.
- Info findings IN-01 through IN-06 were out of scope (fix_scope `critical_warning`).
- REVIEW-FIX.md is not committed, as instructed.

---

_Fixed: 2026-10-28_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
