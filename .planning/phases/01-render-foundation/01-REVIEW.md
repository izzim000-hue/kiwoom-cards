---
phase: 01-render-foundation
reviewed: 2026-10-28T00:00:00Z
depth: standard
files_reviewed: 30
files_reviewed_list:
  - .claude/hooks/session-start.sh
  - .gitignore
  - tools/README.md
  - tools/doctor.py
  - tools/fonts/OFL.txt
  - tools/fonts/README.md
  - tools/golden.py
  - tools/reel.py
  - tools/reelkit/__init__.py
  - tools/reelkit/browser.py
  - tools/reelkit/constants.py
  - tools/reelkit/doctor.py
  - tools/reelkit/encode.py
  - tools/reelkit/golden.py
  - tools/reelkit/layout.py
  - tools/reelkit/render.py
  - tools/reelkit/spec.py
  - tools/reelkit/specprobe.py
  - tools/reelkit/templates/frame.html
  - tools/reelkit/timeline.py
  - tools/requirements.txt
  - tools/specprobe.py
  - tools/tests/fixtures/bad-layout.json
  - tools/tests/fixtures/ok-layout.json
  - tools/tests/golden/manifest.json
  - tools/tests/test_doctor.py
  - tools/tests/test_golden.py
  - tools/tests/test_layout.py
  - tools/tests/test_spec.py
  - tools/tests/test_specprobe.py
findings:
  critical: 0
  warning: 6
  info: 6
  total: 12
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-28
**Depth:** standard
**Files Reviewed:** 30
**Status:** issues_found

## Summary

Reviewed the render foundation (reelkit package, CLIs, session hook, tests). The 72 non-golden unit tests in `test_doctor`, `test_layout`, `test_spec` and `test_specprobe` pass. I did not re-run the golden render tests (3-4 min). I reproduced two failure paths by running `reel.py` directly.

No security vulnerabilities were found. Spec text is validated against a four-tag allow-list in legacy mode and fully escaped in new mode. Chromium blocks `http(s)` requests. All subprocess calls use argument lists with no shell.

The main weaknesses are failure handling and the CLI exit-code contract:

- Failures from ffmpeg, ffprobe or Playwright at runtime escape as raw tracebacks. They exit with code 1, which the documentation reserves for "spec/input error".
- One failing golden reel aborts the whole golden run.
- The session hook can add a slow, failing pip attempt to every session start.

There are no structural findings (no `<structural_findings>` block was provided).

## Warnings

### WR-01: ffmpeg / runtime failures escape `reel.py` as tracebacks with exit code 1

**File:** `tools/reel.py:45-55`, `tools/reelkit/encode.py:14-17`, `tools/reelkit/render.py:138`
**Issue:** `encode_concat` runs `subprocess.run(..., check=True)` with `-loglevel error`. Only `SpecError`, `ImportError`, `FontLoadError` and `BrowserLaunchError` are caught in `main`.

I reproduced this by passing a directory as the output path. The result was a full `CalledProcessError` traceback and exit code 1. The README and docstring define exit 1 as "spec/input error" and 2 as "environment error", so Phase 2 automation will misclassify this failure.

Other uncaught paths:
- `ffmpeg` missing from PATH raises `FileNotFoundError`.
- A Playwright `Error` or `TimeoutError` during `page.screenshot` or `evaluate` is also uncaught.
- ffmpeg's stderr is swallowed unless the traceback is read.

There is also a data-loss angle. ffmpeg writes straight to the final `out_path` with `-y`. If encoding fails midway, any existing good MP4 at that path is replaced with a truncated file.

**Fix:**
```python
# encode.py: capture stderr, write to a temp name, then rename
tmp = Path(out).with_name(Path(out).name + ".part.mp4")
r = subprocess.run([...], capture_output=True, text=True)
if r.returncode != 0:
    tmp.unlink(missing_ok=True)
    raise EncodeError(r.stderr.strip().splitlines()[-1] if r.stderr else f"ffmpeg exit {r.returncode}")
os.replace(tmp, out)

# reel.py: add after the existing handlers
except (EncodeError, FileNotFoundError, OSError) as e:   # and playwright Error
    print(f"렌더 환경 오류: {e}", file=sys.stderr)
    return 2
```

### WR-02: `reel.py` import guard reports any ImportError as "playwright not installed"

**File:** `tools/reel.py:27-34`
**Issue:** The `try` block imports `reelkit.render`, `reelkit.browser`, `reelkit.spec` and `reelkit.specprobe`. A genuine bug in this package (a bad relative import, a typo, a circular import) is caught by `except ImportError` and shown as "playwright 미설치". It then exits with code 2.

The render module imports Playwright lazily inside `render_reel`, so this top-level guard cannot actually detect a missing Playwright. It only masks real defects. The same applies to the `except ImportError` at line 50, though that one is correctly scoped to the Playwright import.

**Fix:** Remove the top-level `try/except ImportError` and import the modules plainly. Keep the `except ImportError` around `render_reel`, and check `e.name` is `playwright` (or `startswith("playwright")`) before printing the install hint. Otherwise re-raise.

### WR-03: One failing reel aborts the entire golden run

**File:** `tools/reelkit/golden.py:196-201, 207, 227, 263-266, 310-314`
**Issue:** `check_reel` wraps only `render_reel` in a try/except. The later calls (`frame_count`, `stream_durations`, `boundaries`, `ssim_values`) go through `_run(..., check=True)`, or `subprocess.run(check=True)` in `boundaries`. They can raise `CalledProcessError`, or `ValueError` when `int(out.strip())` hits empty output.

In `run()`, `pool.map` re-raises a worker exception at the matching `zip` iteration. All other reels' results are lost and the exception propagates out of `run()`. `main` catches only `(ValueError, OSError)`. `CalledProcessError` is a `SubprocessError`, so it produces a raw traceback with exit 1. That exit code is indistinguishable from "a reel failed".

A broken ffmpeg install therefore yields no per-reel report.

**Fix:** Wrap the whole body of the `try:` in `check_reel` with `except Exception as e` (which also covers `subprocess.CalledProcessError`) and return a FAIL `ReelResult`. In `main`, also catch `subprocess.SubprocessError` and return 2.

### WR-04: `cover_ms` truncates a float and is off by 1 ms for 4-line and 10-line first scenes

**File:** `tools/reelkit/timeline.py:41`
**Issue:** `int((LINE * (first - 1) + 0.4) * 1000)` truncates. I computed `first=4` as 2949.9999999999995, giving 2949 instead of 2950. `first=10` gives 8049 instead of 8050. The value is printed as the cover timestamp and recorded in the golden manifest. It is harmless today only because none of the 10 published reels has a first scene of 4 or 10 lines. A new reel would silently get a value that differs from the intended math. `golden.check_reel` has the same truncation pattern at line 216 (`int(LINE * (n - 1) * 1000)`).

**Fix:** Use `round(...)`: `return round((LINE * (first - 1) + 0.4) * 1000)`. Apply the same change in `golden.py:216`. No existing manifest entry changes value, since all published values are exact.

### WR-05: SessionStart hook can run a slow failing pip install on every session

**File:** `.claude/hooks/session-start.sh:33-39`
**Issue:** The hook re-runs `pip install --user` whenever the installed version differs from the pin. If the install can never succeed, every session start pays the failure cost (`--retries 1 --timeout 20`, so up to about a minute offline). Known failure modes:
- A virtualenv: `--user` is rejected.
- PEP 668 externally-managed Python: the hook fails, while the README and doctor advise `PIP_BREAK_SYSTEM_PACKAGES=1`, which the hook never applies.
- No network.

Also, the pin is parsed with `sed 's/^playwright==//p'`. This is stricter than `doctor.read_pin`, which accepts spaces around `==`, trailing comments and CRLF. A CRLF checkout or a `playwright == 1.63.0` line makes `PW_PIN` differ from `PW_CUR` forever, so pip reruns every session even when the right version is installed.

**Fix:** Strip whitespace and CR from the pin: `PW_PIN=$(sed -n 's/^[[:space:]]*playwright[[:space:]]*==[[:space:]]*\([^[:space:]#;]*\).*/\1/p' "$REQ" | head -n 1)`. Optionally retry once with `PIP_BREAK_SYSTEM_PACKAGES=1`. Skip the install when the doctor already reported an acceptable fallback, or record a stamp file so a failed attempt is not repeated within the same container.

### WR-06: Doctor/hook subprocesses have no timeout

**File:** `tools/reelkit/doctor.py:125-126`
**Issue:** `_run` calls `subprocess.run(cmd, capture_output=True, text=True)` with no `timeout`. The doctor runs synchronously from the SessionStart hook, so a hung `ffmpeg -encoders` or lavfi probe blocks session start indefinitely. `FileNotFoundError` and `OSError` from a race between `shutil.which` and execution are also unhandled in `check_ffmpeg` and `check_ffprobe`. They would crash the doctor with a traceback instead of reporting a FAIL line.

**Fix:**
```python
def _run(cmd, timeout=30):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as e:
        return subprocess.CompletedProcess(cmd, 127, "", f"{e.__class__.__name__}: {e}")
```

## Info

### IN-01: Legacy markup check does not require balanced tags

**File:** `tools/reelkit/spec.py:49-65`
**Issue:** `_check_text` only ensures every `<` starts one of the four tags. An unclosed `<g>` in `basis` leaves the outer `<span>` open, so `<b>@kiwoom.mentor</b>` nests inside it. That changes the `justify-content: space-between` layout silently, and `TAG_JS["legacy"]` then finds no account element. This is not exploitable, because the output stays inside the frame. Since legacy is limited to the published specs, the risk is low.
**Fix:** Optionally count `<g>`/`</g>` and `<s>`/`</s>` and raise `SpecError` on imbalance.

### IN-02: Spec loader reports a UTF-8 BOM as a JSON syntax error at line 1 column 1

**File:** `tools/reelkit/spec.py:19`
**Issue:** `read_text(encoding="utf-8")` keeps a leading BOM, which many Windows editors write. `json.loads` then fails with "Unexpected UTF-8 BOM". The user only sees "줄 1 열 1".
**Fix:** Read with `encoding="utf-8-sig"`.

### IN-03: Chromium fallback path selection sorts lexicographically

**File:** `tools/reelkit/browser.py:41-42`
**Issue:** `sorted(glob(...))[-1:]` picks the last path as a string. `chromium-999` sorts after `chromium-1243`. Only one revision is likely installed today.
**Fix:** Sort by the integer revision, for example `key=lambda p: int(re.search(r"chromium-(\d+)", p).group(1))`.

### IN-04: `SMALL` font-size checks can never fire

**File:** `tools/reelkit/layout.py:165-166, 170-171`
**Issue:** The basis and account font sizes are set from the same constants (`BASIS_PX`, `ACCT_PX`) that the check compares against. `fs` is read from `getComputedStyle` of an element whose inline `font-size` is exactly that constant, so `fs < BASIS_PX` is unreachable. This is dead validation. It would only matter if the style were later changed independently.
**Fix:** Keep it as a documented guard, or remove it. If kept, add a test that sets a smaller size and expects `SMALL`.

### IN-05: Doctor's ffmpeg probe does not exercise the features the render uses

**File:** `tools/reelkit/doctor.py:136-151`
**Issue:** The one-frame test covers only `lavfi color` plus libx264. The renderer depends on the `concat` demuxer, the `anullsrc` source, the `fps` filter and `aac`. The aac check only greps the encoder list. The doctor can report OK while a render fails, as in WR-01.
**Fix:** Add a tiny probe that mirrors the real encode: `-f lavfi -i anullsrc ... -c:a aac -t 0.1 -f null -`.

### IN-06: Hook installs unpinned `@opengsd/gsd-core@latest` and `agent-browser`

**File:** `.claude/hooks/session-start.sh:12, 17`
**Issue:** This is not part of Phase 1. It sits in the same file and runs arbitrary latest-tag npm code at session start, with `set -e` so a failed install aborts the new Phase 1 block as well. Playwright is pinned, but these are not.
**Fix:** Pin versions, or append `|| true` with a stderr message so a failed npm install does not prevent the Playwright pin and doctor from running.

---

_Reviewed: 2026-10-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
