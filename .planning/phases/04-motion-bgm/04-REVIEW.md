---
phase: 04-motion-bgm
reviewed: 2026-10-29T14:16:23Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - .claude/skills/make-reel/SKILL.md
  - .claude/skills/make-reel/references/source-format.md
  - .gitignore
  - tools/README.md
  - tools/draft.py
  - tools/reel.py
  - tools/reelkit/approve.py
  - tools/reelkit/bgm.py
  - tools/reelkit/bundle.py
  - tools/reelkit/check.py
  - tools/reelkit/encode.py
  - tools/reelkit/expand.py
  - tools/reelkit/layout.py
  - tools/reelkit/motion.py
  - tools/reelkit/render.py
  - tools/reelkit/review.py
  - tools/reelkit/stills.py
findings:
  critical: 2
  warning: 4
  info: 6
  total: 12
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-29T14:16:23Z
**Depth:** standard (single pass, per user rule: no re-review)
**Files Reviewed:** 17
**Status:** issues_found

## Summary

I reviewed the Phase 4 diff (`aeb5361..HEAD`) for the motion render path, count-up, dwell timing, background music (BGM) validation and mixing, the approval fingerprint and promote, and the docs and skill. I ran three checks myself in this container: Chromium measurements of the count-up box (Playwright, bundled Noto Sans KR), a check of the ffmpeg fades and loudness on a sine wave, and a gitignore probe.

What holds up:
- **`none` path.** When `bgm is None`, the `encode_concat` argv is byte-identical to the pre-phase argv. `new_inner_html` still gives the same markup through `root_html(stack_html(...))`.
- **Final count-up frame.** It equals the ledger text: `cu_text` returns `entry["text"]` when p >= 1, and `final_t` always lands after `start + li*STAGGER + COUNT`.
- **Dwell timing.** `schedule`, `windows` and `final_frame` are consistent with each other.
- **ffmpeg calls.** They use argv lists only, the filter strings contain only numbers, and the `-i` paths are absolute. Content-sniffed playlists disguised as `.mp3` are refused: I tested HLS and ffconcat files and `validate` rejected both.
- **Approval chain.** It binds audio in both directions: `bundle.json` `bgm` is checked against `bgm.json` and the copy, and approval `bgm` is checked against `bundle.json`. promote still moves only the four files. A rebuild without `--bgm` purges `bgm.json` and the `bgm.*` copies.
- **Fades.** They survive `loudnorm`. I measured -42 dB at t=0, -18 dB mid-clip and -43 dB at T-0.1 s.

Two defects ship:
1. **Count-up overflow.** Count-up intermediate strings are often wider than the fixed-width box. The box keeps the final text's width, so intermediates overflow it and overlap the next glyphs in the MP4. This happens with the formats the docs call "safe".
2. **Uppercase audio extensions.** The BGM validator lower-cases extensions, but `.gitignore` matches case-sensitively. So an in-repo `Song.MP3` is accepted as "commit-safe" when git will in fact track it.

## Critical Issues

### CR-01: Count-up intermediate numbers overflow the fixed-width box and overlap neighbouring text

**File:** `tools/reelkit/motion.py:125-130` (cu_text), `tools/reelkit/motion.py:216-219` (BUILD_JS width fix); docs `.claude/skills/make-reel/references/source-format.md:105-107`
**Issue:** BUILD_JS fixes each `.rk-cu` span to `inline-block; white-space:nowrap; width = <final text width>`, and overflow stays visible. `cu_text` formats intermediate values with the same `calc.FORMATS` function. Those formats drop trailing `.0`, and `eok_man_won` switches unit structure at 1억. So intermediate strings are routinely **wider** than the final string:
- `man1` 150만: `98.6만 … 149.9만` while the final is `150만`
- `pct` 10%: `6.6% … 9.9%` while the final is `10%`
- `eok_man_won` 1억 원: `9,999만 원` while the final is `1억 원`

I measured this in Chromium with the bundled font on the real motion DOM (`motion.build` + `motion.seek` over every frame). The worst `scrollWidth - clientWidth` per case:

| fmt | final | box px | worst intermediate | overflow px |
|---|---|---|---|---|
| eok_man_won | `1억 원` | 256 | `1,199만 원` | **206** |
| man1 | `150만` | 263 | `105.6만` | **90** |
| pct | `10%` | 211 | `1.2%` | **33** |

For most of the 0.8 s count window, the number paints over the particle or words after it. For example, in `150만이면` the digits run into `이면`. No check catches this:
- COUNTUP_WRAP compares only line counts.
- The CountUp tests assert that box width, left and line height stay constant, and they do. The glyphs are what overflow.
- The final frame, cover and scene sheet are correct, so the defect is visible only in the moving video.

`source-format.md` makes it worse. It tells authors that `man1` and `pct` are the safe formats.
**Fix:** Make every intermediate string no wider than the final one. Then add a test that asserts `scrollWidth <= clientWidth` for every frame of every `.rk-cu`. For example, quantize intermediates to the final text's displayed precision, and keep the final's unit structure for `eok_man_won`:
```python
_SCALE = {"man1": 10000, "pct": 1, "num": 1, "se": 1, "dal": 1}   # formats that drop a trailing ".0"

def cu_text(entry, p):
    if p >= 1:
        return entry["text"]
    eased = 1 - (1 - max(p, 0)) ** 3
    v = Decimal(entry["value"]) * Decimal(str(eased))
    scale = _SCALE.get(entry["fmt"])
    if scale and "." not in entry["text"]:          # final shows no decimals -> neither do intermediates
        v = (v / scale).to_integral_value(rounding=ROUND_DOWN) * scale
    if entry["fmt"] == "eok_man_won" and "억" in entry["text"]:
        return _eok_countup(v)   # new helper: count in 억 units ("0억 원" … "1억 원"), never the wider "9,999만 원"
    return calc.FORMATS[entry["fmt"]](v)[0]
```
As a backstop, set `text-align:right; overflow:hidden` on `.rk-cu` in BUILD_JS. That clips instead of overlapping. Also have `_render_motion` warn (COUNTUP_OVERFLOW) if any frame overflows. Correct the "safe formats" sentence in source-format.md.

### CR-02: Uppercase audio extensions pass the "commit-safe" repository rule but are not gitignored

**File:** `tools/reelkit/bgm.py:88-94`, `.gitignore:6-13`
**Issue:** `validate` lower-cases the suffix (`ext = src.suffix.lower()`), so `Song.MP3`, `Track.M4A` and `x.WAV` are accepted. For in-repo files, the only commit guard is "same folder as the draft or output, not named `bgm.*`". It relies on `.gitignore`, but `.gitignore` lists lowercase `*.mp3` etc. only, and this repo has `core.ignorecase` unset (false) on Linux. I verified that `git check-ignore -v 2026/reels/Song.MP3` matches nothing while `2026/reels/x.mp3` is ignored. Concrete paths:
- `reel.py SPEC 2026/reels/x.mp4 --bgm 2026/reels/Song.MP3 --bgm-license …` is accepted. The draft_dir is the output folder, the tracked `2026/reels/`, so the original audio sits untracked-but-addable in the published folder.
- `bundle` accepts any folder whose parent is named `drafts`, including `<repo>/drafts/<name>/`, which is not ignored.

This defeats D-09 ("음원 파일은 저장소에 커밋되지 않게 .gitignore로 막고"), and README "커밋 방지" claims protection that does not exist. Separately, on a case-insensitive filesystem a source named `BGM.MP3` inside the draft folder passes the `COPY_NAMES` check (case-sensitive), then `purge_outputs` deletes it as `bgm.mp3`. That destroys the user's file.
**Fix:** Do both:
```gitignore
*.[mM][pP]3
*.[mM]4[aA]
*.[wW][aA][vV]
*.[aA][aA][cC]
*.[oO][gG][gG]
*.[oO][pP][uU][sS]
*.[fF][lL][aA][cC]
```
In `validate`, for in-repo sources, also require that git ignores the file, so the rule holds whatever `.gitignore` says:
```python
if src == repo or repo in src.parents:
    if src.parent != Path(draft_dir).resolve() or src.name.lower() in COPY_NAMES:
        raise BgmError(...)
    r = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "--", str(src)])
    if r.returncode != 0:
        raise BgmError("저장소 안 음원이 .gitignore 로 막혀 있지 않음 — 커밋 방지")
```
Compare `src.name.lower()` against `COPY_NAMES` so the case-insensitive filesystem deletion cannot happen.

## Warnings

### WR-01: `reel.py --bgm` validates the license memo, then discards it; a music MP4 can land in a tracked folder with no license record

**File:** `tools/reel.py:53-77`, `tools/reelkit/render.py:208-217`
**Issue:** reel.py requires a non-empty `--bgm-license` but never stores it: no `bgm.json`, no review line, no hash. The output path is unrestricted, so `reel.py … 2026/reels/<name>.mp4 --bgm song.mp3 --bgm-license x` writes a music-bearing MP4 straight into the published (tracked) folder. That bypasses D-11, which requires the license memo in review.md for human confirmation and the audio hash in the approval fingerprint, and it bypasses the approve/promote gate. The license gate in this path is decorative.
**Fix:** Pick one:
- (a) Refuse `--bgm` in reel.py when the output resolves inside the repository but outside a `drafts/` folder.
- (b) Write a sidecar `<out>.bgm.json` (file, sha256, memo) next to the MP4 and print it.
- (c) Drop `--bgm` from reel.py and keep BGM bundle-only, which is the only path with review and approval.

### WR-02: The inline-block count-up box changes line-break opportunities; COUNTUP_WRAP only compares line counts

**File:** `tools/reelkit/motion.py:209-223`, `tools/reelkit/render.py:172-178`
**Issue:** Turning the inline span into an atomic inline-block adds a break opportunity after it, even under `word-break: keep-all`. Korean almost always glues a particle to the number (`{{x|man1|up}}까지`). I measured `최대 연금 148.5만까지 받아요` at 100px/900 in Chromium:
- At container widths 820 to 920 px, the static layout puts `148.5만까지` on line 2. The motion DOM puts `148.5만` on line 1 and `까지 받아요` on line 2.
- Both have 2 lines, so COUNTUP_WRAP does not fire. The number is separated from its particle, and the motion frames, cover and scene sheet no longer match the statically measured layout that every WRAP, overflow and safe-zone warning and overlay was computed on.

This contradicts D-02 ("줄바꿈은 모션 없이 측정한 배치를 기준으로 고정한다"). It only happens on lines that already wrap statically, which is why I rate it a warning and not a blocker. Those bundles exit 3 and are still approvable.
**Fix:** In BUILD_JS, record for each count-up line the per-text-node line index (or the `getClientRects()` tops) before converting to inline-block, and again after. Raise COUNTUP_WRAP when any break position differs, not only the count. Alternatively, wrap the number and its trailing non-space run in a `white-space:nowrap` inline wrapper in both the static and the motion markup, so the break opportunities are identical.

### WR-03: The `none` regression guard pins raw pixel hashes, so it breaks on any Chromium, font or ffmpeg change and cannot be honestly regenerated

**File:** `tools/tests/none_guard.py:47-75`, `tools/tests/golden/none-new.json`, `tools/tests/test_motion.py:34-53`
**Issue:** NoneUnchanged compares SHA-256 hashes of decoded frames and overlays exactly. Any change in Chromium revision, font hinting, CPU rasterization path or ffmpeg build fails the guard even if the code is unchanged. The documented remedy is to regenerate "from code before the source edits", which after this phase means checking out 3fde951. So in practice someone will regenerate from current code, and the guard then protects nothing. This is an environment-dependent test on the most important invariant of the phase (MOTN-04).
**Fix:** Keep the exact checks that are environment-independent: `argv`, `total`, `cover_ms`, `warnings`, the `new_inner_html` markup hashes and the state durations. Replace the pixel hashes with a same-run differential. Render the fixture with the current `render_reel(layout="new")` and with a frozen copy of the pre-phase none renderer, or compare against `golden.py`'s tolerance-based frame comparison, and allow a channel difference of 1 or less. Alternatively, skip the pixel keys with a clear message when the `chromium`/ffmpeg version recorded in the baseline differs from the running one.

### WR-04: The BGM copy is never re-validated after `validate`; what gets mixed and recorded can differ from what was checked

**File:** `tools/reelkit/bundle.py:221-227, 416-418`, `tools/reelkit/bgm.py:117-146`
**Issue:** `validate` probes the source before `purge_outputs`. Then expand, check, caption and compliance run, which takes seconds. Only after that does `install` copy `src.path`. The copy is never re-probed:
- If the source was replaced or edited in between (for example, a user re-exporting the track), the copy can be a different track, a video file or a too-short file.
- The sha256 is taken from the copy, but `duration_s` comes from the earlier probe.
- review.md and approval then attest to a file that never passed the audio, video-stream and 3-second checks.
**Fix:** In `install`, after `os.replace`, re-run `_probe` and the stream and duration checks on the **copy**, and use that duration. On failure, delete the copy and raise BgmError, mapped to exit 1. Better still, hash the source in `validate` and compare it with the copy's hash in `install`.

## Info

### IN-01: The failure review always says "배경음 없음" even when a track was installed

**File:** `tools/reelkit/bundle.py:289-301` (fail ctx), `tools/reelkit/review.py:265`
**Issue:** `fail()` builds the failure ctx without `"bgm"`, so when render fails after the `bgm` step, review.md shows the no-BGM license line while `bundle.json` records `bgm`.
**Fix:** Add `"bgm": state.get("bgm")` to the failure ctx.

### IN-02: The license memo accepts invisible-only content

**File:** `tools/reelkit/bgm.py:77-79`
**Issue:** `str.strip()` does not remove U+200B/U+FEFF (zero-width) characters or NUL. A memo made only of such characters passes the "non-empty" gate and renders as blank in review.md. Bidi controls (U+202A-U+202E, U+2066-U+2069) are also not neutralised by `review.CONTROL_RE` or `approve._one_line`, so a file name or memo can be shown visually reordered to the approver.
**Fix:** Before the emptiness test, strip `unicodedata.category(c) in ("Cc", "Cf", "Zs")`. Add the Cf range to `CONTROL_RE`.

### IN-03: `|up` with `motion: none` is silently ignored

**File:** `tools/reelkit/expand.py:196-210`, `tools/reelkit/check.py:350-357`
**Issue:** The doc says this has no effect, but neither check nor review warns. An author who forgets `"motion": "basic"` gets a static reel with no hint.
**Fix:** Add a check warning (for example `COUNTUP_IGNORED`) when any ledger entry has `countup` and the resolved mode is `none`.

### IN-04: `schedule()` and `countup_entries()` disagree on what counts as a count-up

**File:** `tools/reelkit/motion.py:68-78` versus `motion.py:145-146`
**Issue:** `_countup_lines` accepts any truthy `countup`, while `countup_entries` requires exactly `True`. `check.py` DURATION and `stills.scene_times` call `schedule()` without the strict validator, so a hand-edited `"countup": 1` changes the timing in check output, then fails only at render.
**Fix:** Use `entry.get("countup") is True` in `_countup_lines`.

### IN-05: DWELL thresholds compare `dur`, which includes the outgoing cross-fade for every scene except the last

**File:** `tools/reelkit/motion.py:92, 102-111`
**Issue:** The same 1.5 s or 6.0 s bound means 0.3 s less readable time for non-last scenes than for the last one, and the README formula hides this.
**Fix:** Compare `sc.settle + sc.read`, the readable dwell, against the bounds. Or state the asymmetry in README and the constants comment.

### IN-06: Duplicated regex constants

**File:** `tools/reelkit/expand.py:28` (`LINE_WHERE_RE` without `^`), `tools/reelkit/motion.py:29-30` (`TAG_RE`, `LINE_WHERE_RE`)
**Issue:** These are the same patterns defined in two or three places, with slightly different anchoring. A future change to the `where` format will drift between them.
**Fix:** Define them once, for example in `constants.py` or `spec.py`, and import them.

---

_Reviewed: 2026-10-29T14:16:23Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
