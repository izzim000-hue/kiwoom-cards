---
phase: 04-motion-bgm
fixed_at: 2026-10-29T14:52:00Z
review_path: .planning/phases/04-motion-bgm/04-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 12
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-10-29T14:52:00Z
**Source review:** .planning/phases/04-motion-bgm/04-REVIEW.md
**Iteration:** 1 (single pass, per user rule: no re-review loop)

**Summary:**
- Findings in scope: 12 (CR-01, CR-02, WR-01..WR-04, IN-01..IN-06)
- Fixed: 12 (IN-05 fixed by documentation only, by choice; see below)
- Skipped: 0

**Where verification ran:** in the main checkout `/home/user/kiwoom-cards`, on branch `ccr-f9cedca2-3o2v27`. No isolated worktree was used: the orchestrator's root-pin guard requires the main checkout, and it was run before the first edit and before every commit. The results can be reproduced from this tree.

- Full suite, run once at the end: `python3 -m unittest discover -s tools/tests -p 'test_*.py'`. 703 tests ran in 804.7 s with no failures.
- Golden, run once at the end: `python3 tools/golden.py` returned `golden: PASS 10/10 (재현 불가 1)`. The one non-reproducible reel is the existing savings-interest entry, which has no spec.
- Repository state after both runs: the working tree is clean, there is no extra git worktree, and no audio file was added. All test audio is ffmpeg `sine` audio created in mktemp directories.

## Fixed Issues

### CR-01: Count-up intermediate numbers overflow the fixed-width box

**Files modified:** `tools/reelkit/motion.py`, `tools/tests/test_motion.py`, `tools/README.md`, `.claude/skills/make-reel/references/source-format.md`
**Commit:** 8888e05
**Applied fix:**
- **Counting step.** `countup_step` and `cu_text` now count intermediates at the final text's display precision, rounding toward zero:
  - a final with no decimal point (`150만`, `10%`) counts in integers;
  - `eok_man_won` counts in 만 units when the final has a 만 part, and in 억 units when it does not (so there is no `9,999만 원` step before `1억 원`).
  - Finals that show a decimal keep the old values, so the pension fixture strings are unchanged.
- **Box width.** The box no longer takes the final text's width blindly. `countup_variants` collects every string that any rendered frame shows, and BUILD_JS measures each of them in the page with the real font and sizes the box to the widest one. Text inside the box is right-aligned, so the particle after the number stays attached.
- **Tests.** The bundled font's digits turned out to be tabular, so the box stays at the final text's width and the static layout is unchanged.
  - `CountUpFit` measures overflow on every frame for man1 `150만`, pct `10%`, eok_man_won `1억 원` and `3억 7,200만 원`, and decimal man1. The text range and `scrollWidth` must stay within the box (tolerance 0.5 px).
  - It also checks that the box equals the static width.
  - It checks that a forced wider intermediate grows the box instead of overflowing.
  - `CountUpSteps` covers the counting rules.
- **Before and after.** The old code overflowed by 90, 33 and 206 px on the same cases; the new code overflows by 0.
- **Docs.** source-format.md no longer calls any format "safe".

### CR-02: Uppercase audio extensions pass the commit-safe rule but are not gitignored

**Files modified:** `.gitignore`, `tools/reelkit/bgm.py`, `tools/reelkit/bundle.py`, `tools/tests/test_bgm.py`, `tools/README.md`
**Commit:** a4ab5bb
**Applied fix:**
- **`.gitignore`.** The audio patterns now match any case (`*.[mM][pP]3` style, for all 7 extensions).
- **Git check.** For a source inside the repository, `bgm.validate` asks `git check-ignore`. If git is missing, the folder is not a repository, the file is tracked, or the file is not ignored, the source is refused. The rule therefore holds whatever `.gitignore` says.
- **Path checks.** The "is it inside the repository" and "same folder as the draft" checks use `os.path.samefile`, not the path text.
- **Reserved names.** `bgm.json`, `bgm.<ext>` and their `.part` files are reserved names, compared case-insensitively. A source named `BGM.MP3` is refused. A draft folder that holds a case variant of a reserved name is also refused, so the copy cannot overwrite it.
- **Purge.** `purge_outputs` deletes only the reserved names that appear with exactly that spelling in the folder listing, and never the current source (`keep=`). A user's `BGM.MP3` therefore survives on a case-insensitive filesystem.
- **Tests:**
  - uppercase extension accepted in the draft folder;
  - reserved name refused in any case;
  - case-variant clash refused;
  - in-repo file that git does not ignore refused;
  - no git refused;
  - the real `.gitignore` ignores `Song.MP3`, `T.M4A`, `a.Wav`, `b.AAC`, `c.OGG`, `d.Opus` and `e.FLAC` (asked with `check-ignore`, no files created);
  - purge removes only exact names.

### WR-01: `reel.py --bgm` discards the license memo

**Files modified:** `tools/reel.py`, `tools/README.md`, `tools/tests/test_bgm.py`
**Commit:** 53decd3
**Applied fix:** I chose the smaller safe option: background music is bundle-only.
- **Behaviour.** `reel.py` still parses `--bgm` and `--bgm-license`, but rejects them before Chromium starts: exit 1, `음원 오류`, and a pointer to `draft.py bundle --bgm`. No MP4 is written. Parsing them avoids argparse's exit 2, which this tool uses for environment errors.
- **What stays.** The `render_reel(bgm=...)` library path is unchanged, because bundle uses it.
- **Docs.** The docstring and README explain why the flags were removed.
- **Tests.** `ReelFlags` now asserts the refusal for every flag combination.

### WR-02: Count-up inline-block changes break opportunities; COUNTUP_WRAP only compared line counts

**Files modified:** `tools/reelkit/motion.py`, `tools/reelkit/render.py`, `tools/tests/test_motion.py`, `tools/README.md`, `.claude/skills/make-reel/references/source-format.md`
**Commit:** 95732e1
**Applied fix:**
- **Measurement.** For each count-up line, BUILD_JS records which row each non-space character sits on, before and after the number becomes a box. It returns `moved`, `before` and `after`.
- **Warning.** The new `render.countup_wrap_warnings` raises COUNTUP_WRAP when the line count differs from the static layout, or when any break position moved. The warning detail shows both layouts.
- **Test.** The reviewer's case, `최대 연금 <g>148.5만</g>까지 받아요`, has two rows in both layouts. It now warns: `'최대 연금 / 148.5만까지 받아요' -> '최대 연금 148.5만 / 까지 받아요'`. A test also checks that unchanged lines do not warn.

### WR-03: none guard pins raw pixel hashes

**Files modified:** `tools/tests/none_guard.py`, `tools/tests/test_motion.py`, `tools/README.md`
**Commit:** 035acd3
**Applied fix:** The guard is kept exact. Per the user's instruction it was not loosened.
- **Two groups of checks.** `NoneUnchanged` first checks the keys that do not depend on the environment: durations, total, cover_ms, warnings, markup hashes and ffmpeg argv. A failure there says "this is a code regression: fix the code, do not regenerate." It then checks the frame and overlay pixel hashes. A failure there explains the legitimate regeneration.
- **Regeneration.** `none_guard.py --write` from current code is now refused (exit 1). The only way to regenerate is `none_guard.py --regenerate-from-base`. It checks out the pre-phase commit `3fde951` in a temporary git worktree, captures the baseline there with that commit's code in the current environment, copies only the JSON, and removes the worktree.
- **Check run here.** I ran it once in this environment. It reproduced the committed baseline byte for byte (no diff).
- **Docs and tests.** The README section "모션 none 기준선" documents the procedure. `NoneGuardTool` asserts that `--write` is refused and that `BASE_COMMIT` is the commit that added the baseline.

### WR-04: The BGM copy is never re-validated after `validate`

**Files modified:** `tools/reelkit/bgm.py`, `tools/reelkit/bundle.py`, `tools/tests/test_bgm.py`, `tools/README.md`
**Commit:** 19acef0
**Applied fix:**
- **Hash and re-check.** `validate` records the source's sha256. `install` hashes the copy and compares it, then re-runs the audio checks on the copy: audio stream present, no video stream, at least 3 s. It records the duration measured on the copy.
- **Failure.** On a mismatch or a failed check, the copy is deleted and `BgmError` is raised. Bundle maps this to `음원 오류`, exit 1, header `음원 오류 — 영상 미생성`, and makes no video.
- **Tests:**
  - a source changed after validate;
  - a source that fails the re-probe;
  - the duration taken from the copy;
  - the bundle exit-1 path, with render mocked to prove it is never reached.

### IN-01: The failure review always says "배경음 없음"

**Files modified:** `tools/reelkit/bundle.py`, `tools/tests/test_bgm.py`
**Commit:** 4d3baaf
**Applied fix:** The failure ctx now carries `bgm: state.get("bgm")`. A test makes the render fail after install and checks that review.md shows the `s8.mp3` license line, matching bundle.json.

### IN-02: The license memo accepts invisible-only content

**Files modified:** `tools/reelkit/bgm.py`, `tools/reelkit/review.py`, `tools/tests/test_bgm.py`
**Commit:** 61313c5
**Applied fix:**
- **Memo check.** The emptiness test ignores characters in the Unicode categories Cc, Cf, Zs, Zl and Zp. The stored memo is unchanged.
- **Display filter.** `review.CONTROL_RE`, which `approve._one_line` also uses, now also replaces with a space:
  - zero-width characters and LRM/RLM (U+200B-U+200F);
  - bidi embedding and isolate controls (U+202A-U+202E, U+2066-U+2069);
  - U+2060-U+2064;
  - the BOM.

### IN-03: `|up` with `motion: none` is silently ignored

**Files modified:** `tools/reelkit/check.py`, `tools/tests/test_motion.py`, `tools/tests/test_expand.py`, `.claude/skills/make-reel/references/source-format.md`
**Commit:** 4daac1b
**Applied fix:**
- **Warning.** A new `COUNTUP_IGNORED` check warning, with a hint, fires when the ledger has count-ups and the resolved mode is `none`. Check warnings do not change the bundle exit code.
- **Test update.** `test_expand.test_check_accepts_up_source` now expects this one extra warning, because its source has no motion field.

### IN-04: `schedule()` and `countup_entries()` disagree on what counts as a count-up

**Files modified:** `tools/reelkit/motion.py`, `tools/tests/test_motion.py`
**Commit:** 1afc4a2
**Applied fix:** `_countup_lines` now uses `entry.get("countup") is True`. A test checks that `1`, `"yes"` and `[1]` leave the schedule unchanged.

### IN-05: DWELL thresholds compare `dur`, which includes the outgoing cross-fade

**Files modified:** `tools/reelkit/motion.py`, `tools/README.md`
**Commit:** cdf34cf
**Applied fix:** Documentation only, which is one of the two options the review offered. The thresholds were calibrated on the published ten reels, and changing them would move the existing warning values. The asymmetry (0.3 s less readable time for every scene except the last) is now stated in the constants comment, the `dwell_warnings` docstring and the README.

### IN-06: Duplicated regex constants

**Files modified:** `tools/reelkit/constants.py`, `tools/reelkit/motion.py`, `tools/reelkit/check.py`, `tools/reelkit/expand.py`
**Commit:** 1b4a04f
**Applied fix:** `TAG_RE` and `LINE_WHERE_RE` are defined once in `constants.py`, and check, motion and expand import them. expand's unanchored pattern was only used with `.match`, so the anchored pattern behaves the same. The private copies in caption, numscan and review are different patterns and were left alone.

## Kept invariants

- **`none` path.** Unchanged. NoneUnchanged still matches the committed baseline exactly, and without BGM the encoder argv is untouched.
- **Golden.** 10/10.
- **Music.** Nothing searches for or downloads music; tests use only ffmpeg `sine` audio in mktemp directories.
- **Untouched.** No audio was committed. approve was never run on real folders, and no file in `2026/reels/` changed. `.claude/settings.json`, STATE.md and ROADMAP.md were not touched. Nothing was pushed.

## Residual risk

1. **CR-01: some count-ups barely count.** A whole-억 `eok_man_won` value such as `1억 원` shows `0만 원` for the whole count window and then switches to `1억 원`. This is documented in source-format.md. If a future format ever produced a wider intermediate, the box would grow to fit it. That leaves a gap in the final frame and can move the static layout, which the WR-02 check would catch only if a line break changes. There is no separate "box grew" warning.
2. **WR-02: the warning does not fix the frames.** When COUNTUP_WRAP fires, the moving frames still differ from the static layout (exit 3, and the reel can still be approved). The author has to rephrase the line. Making the motion DOM keep the static break opportunities would mean changing the static markup, which the `none` invariant forbids.
3. **CR-02 on case-insensitive filesystems.** `approve.bgm_names` still checks the exact tool names with `lexists`. On macOS, a user file `BGM.MP3` in a draft without BGM therefore makes approve refuse with "bundle 을 다시 실행하세요", and re-bundling will not delete that file. The user has to rename it. This is conservative (it fails closed) but the message is misleading. Linux is unaffected.
4. **CR-02 relies on git.** An in-repo source is refused if `git` is missing or the checkout is not a git repository. Sources outside the repository are unaffected.
5. **WR-03 still needs a person.** Regeneration depends on commit `3fde951` staying reachable, and someone should read the regenerated JSON's `git diff` (only pixel hashes should change) before committing it.
6. **WR-01 is a capability removal.** Standalone `reel.py` renders can no longer carry music, and the 04-03 plan and summary still describe the old flag (they were not edited, by design).
7. **IN-05 was not changed in behaviour.** If the house prefers the bounds to apply to readable time, that is a later decision.

---

_Fixed: 2026-10-29T14:52:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
