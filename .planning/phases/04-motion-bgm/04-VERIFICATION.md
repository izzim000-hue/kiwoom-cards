---
phase: 04-motion-bgm
verified: 2026-10-29T16:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files:
  - ".gitignore"
  - ".planning/phases/04-motion-bgm/04-01-PLAN.md"
  - ".planning/phases/04-motion-bgm/04-01-SUMMARY.md"
  - ".planning/phases/04-motion-bgm/04-02-PLAN.md"
  - ".planning/phases/04-motion-bgm/04-02-SUMMARY.md"
  - ".planning/phases/04-motion-bgm/04-03-PLAN.md"
  - ".planning/phases/04-motion-bgm/04-03-SUMMARY.md"
  - "tools/draft.py"
  - "tools/reel.py"
  - "tools/reelkit/approve.py"
  - "tools/reelkit/bgm.py"
  - "tools/reelkit/bundle.py"
  - "tools/reelkit/check.py"
  - "tools/reelkit/encode.py"
  - "tools/reelkit/expand.py"
  - "tools/reelkit/motion.py"
  - "tools/reelkit/render.py"
  - "tools/reelkit/review.py"
  - "tools/tests/test_bgm.py"
  - "tools/tests/test_motion.py"
covered_digest: "v4:sha256:3cb947a51a0cef4b5233c8a9350db3b27779abe5b07b988cc37d55335b2f94e5"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Watch a motion reel (a bundle of a spec with \"motion\": \"basic\", e.g. tools/tests/fixtures/draft-pension-motion.src.json) on a phone-size player"
    expected: "Each line fades in and rises slightly (about 0.3 s); scenes cross-fade in about 0.3 s; Hangul line breaks never jump; the two count-ups in scene 5 end on 148.5만 / 118.8만; no scene feels rushed or stalled; the 0.3 s overlap of basis/account text during a cross-fade is acceptable"
    why_human: "Feel and readability of motion cannot be judged from frames or tests. DWELL coefficients (READ_BASE 0.6, READ_CPS 16, bounds 1.5-6.0 s) are calibrated on the published ten scripts only (assumption A1/A4 in 04-03-SUMMARY)"
  - test: "Bundle one draft with `--bgm <own licensed track> --bgm-license \"<license note>\"` and listen to the MP4"
    expected: "About 1 s fade-in and fade-out, comfortable level (target about -16 LUFS; real music can differ by 1-2 LU), review.md shows the original file name, sha256 prefix and license memo"
    why_human: "Only synthetic ffmpeg sine tones were used in verification; real-music loudness and the licence itself need a person"
  - test: "Owner decision on license evidence format for BGM"
    expected: "Owner states what counts as evidence (free-form memo today, max 500 characters, stored verbatim) and whether a stricter format (URL, receipt id, licence type field) is required"
    why_human: "ROADMAP Owner gate for Phase 4 is still open; the implementation deliberately accepts any non-blank memo"
---

# Phase 4: 자막 연출 + 선택 배경음 (Motion & BGM) Verification Report

**Phase Goal:** 같은 원고로 줄 진입, 장면 전환, 숫자 카운트업이 들어간 보는 맛 있는 릴스를 받는다. 원하면 라이선스가 확인된 자기 음원으로 배경음을 넣을 수 있다. Phase 3 검수 묶음 흐름과 업로드 규격은 그대로 지켜진다.
**Verified:** 2026-10-29
**Status:** human_needed
**Re-verification:** No - initial verification (HEAD e9b51c8, after the code-review fixes)

## Goal Achievement

All five ROADMAP success criteria are verified against code and my own runs. The status is `human_needed`, not `passed`, because motion feel and real-music listening are human-only and the licence-evidence owner gate is open. No gap blocks the goal.

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Motion-on reel: each line fades in with a slight rise (about 250-350 ms), one 0.3 s scene transition, Hangul line breaks do not move | VERIFIED | `motion.py` constants ENTER 0.30 / STAGGER 0.12 / RISE_PX 24 / CROSS 0.30; rendered by paused Web Animations + per-frame PNG pipe (`render._render_motion`, `encode.PipeEncoder`), no real-time recording. My bundle of the motion fixture: exit 0, 26.3 s, 789 frames = `schedule().total` 26.3 s. Line-break stability is covered by `test_motion.py` Geometry/Equivalence classes (line rects and counts equal the static layout, motion final frame equals static frame from row 30), which passed (74 OK). Visual check of extracted frames: scene 5 lays out the same before and after count-up. The 0.3 s overlap look is a human item |
| 2 | Count-up shows rising numbers; final frame's number equals the script number character for character | VERIFIED | `{{ref\|fmt\|up}}` -> ledger `countup: true`; `cu_text` returns the ledger text object when p >= 1. Extracted frames from my MP4: t=12.95 s shows `126.9만` / `82.1만`, t=13.60 s shows `148.5만` / `118.8만`, which equal the two ledger texts (`scene 5 line 1/2`). CountUp tests (final line text equals script line, per-frame overflow check after CR-01 fix) passed |
| 3 | `none` render equals the Phase 1 regression baseline in length, scene boundaries, cover time, and pixels within tolerance | VERIFIED | `python3 tools/golden.py` run by me: `golden: PASS 10/10 (재현 불가 1)`, every reel frames N/N, boundaries match, cover_ms unchanged, SSIM min 0.9923, spec PASS. `NoneUnchanged` (frame hash baseline `tools/tests/golden/none-new.json`, taken at commit 3fde951 before any source edit, plus encoder argv) passed in my `test_motion.py` run. `git status` clean, nothing changed under `2026/reels` |
| 4 | Scene dwell is set from character count; too fast or too long scenes warn at render | VERIFIED | `motion.schedule` (settle + READ_BASE + chars/READ_CPS + CROSS) and `dwell_warnings` (DWELL_SHORT < 1.5 s, DWELL_LONG > 6.0 s, constants defined once). My fixture schedule: scenes 2.94-4.94 s, no warnings, total 26.3 s (inside the 21-27 s house range). Dwell tests cover the published ten (no warnings), short and long scenes, `--strict` exit 3. Bundle treats warnings as exit 3 and still approvable |
| 5 | Audio file + licence memo -> MP4 with BGM, fades and proper level that passes the upload spec; no memo -> render refused; audio not committed | VERIFIED | My run with a 10 s ffmpeg sine (looped to 26.3 s): bundle exit 0, `spec: PASS 9/9`, AAC 44.1 kHz stereo, A/V duration both 26.300 s. Loudness measured with ebur128: -15.9 LUFS. Volume at t=0 -42 dB, t=0.05 -36.9 dB, mid -18.1 dB, t=26.2 -43 dB (fade in and out confirmed). Refusals (all exit 1, before any purge or render, no MP4 produced): `--bgm` without memo, memo without `--bgm`, blank memo, zero-width-only memo. `git ls-files` audio count 0; `.gitignore` ignores `tools/x.MP3` (case-insensitive patterns). `test_bgm.py` 42 OK |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified). Human items below are about feel and licence, not missing code.

### Plan-level truths spot-checked (beyond the roadmap)

| Truth | Status | Evidence |
|-------|--------|----------|
| bundle.json records motion, countups, bgm; outputs include `bgm.json` + copy only when BGM is mixed | VERIFIED | No-BGM bundle: `motion: basic, countups: 2, bgm: null`, 10 outputs. BGM bundle: `bgm` object equals `bgm.json` (`file sine.mp3`, `copy bgm.mp3`, sha256, memo, `duration_s 10.03`), outputs end with `bgm.json`, `bgm.mp3`. Steps in order; elapsed 90.2 s and 95.7 s (budget 600 s) |
| review.md shows motion line and licence line | VERIFIED | No BGM: `- 모션: basic — 줄 진입·장면 전환 0.3초 · 카운트업 2곳 (중간 숫자는 연출, 최종값만 장부 값)`, count-up checklist item, and the old `음원 라이선스 — 배경음 없음 = 무음 ...` line unchanged. With BGM: `배경음: sine.mp3 — 페이드 인·아웃 1초, 음량 정규화`, `음원 라이선스 — 파일 sine.mp3 (sha256 7823a54fbd7e) · 메모: ... — 사업자 계정 상업 사용 권리를 사람이 확인`, plus a loudness check item |
| Approval fingerprint covers audio both ways, promote never moves audio | VERIFIED (by tests, not by running approve on real folders as instructed) | `approve.bgm_names` two-way check, `PROMOTED_KEYS = ("mp4","cover","spec","caption")`; `ApproveBgm` tests in `test_approve.py` and `test_bgm.py` pass. I did not re-run `test_approve.py` (fixer's full suite of 703 passed at HEAD) |
| Count-up box does not overflow (CR-01 fix) | VERIFIED | `CountUpFit` tests (per-frame overflow <= 0.5 px for man1/pct/eok_man_won) passed |
| `reel.py --bgm` | NOTE | Deliberately refused with exit 1 and a pointer to `draft.py bundle --bgm` (review fix WR-01). BGM is bundle-only; the roadmap criterion is met through the bundle. 04-03-PLAN still describes the old `reel.py --bgm`; it was not edited |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/reelkit/motion.py` | schedule, resolve, build/seek, count-up, dwell warnings | VERIFIED | 396 lines, used by `render._render_motion`, `stills.scene_times`, `check._house_pattern`; data flows (frames extracted from my MP4 show the effect) |
| `tools/reelkit/encode.py` `PipeEncoder` | image2pipe encoder, atomic `.part.mp4` | VERIFIED | Used by the motion render; MP4 passes 9/9 with and without BGM; `encode_concat` argv unchanged when `bgm is None` (NoneUnchanged) |
| `tools/reelkit/bgm.py` | validate, install, read_meta, filter_graph | VERIFIED | Wired from `bundle.run_cli` (validate before purge, install before render) and `encode`; no network imports |
| `tools/tests/none_guard.py`, `golden/none-new.json` | none baseline captured before source edits | VERIFIED | Baseline commit 3fde951; guard passes |
| `tools/tests/test_motion.py`, `test_bgm.py` | tests | VERIFIED | Run by me: 74 tests OK (391 s) and 42 tests OK (77 s) |
| `.gitignore` audio patterns | 7 extensions, any case | VERIFIED | `git check-ignore tools/x.MP3` matches |
| `tools/README.md`, make-reel SKILL.md, source-format.md | docs | VERIFIED | Present per summaries; not read line by line (low risk) |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| render.py | motion.py / encode.PipeEncoder | `motion.resolve`, `PipeEncoder` in `_render_motion` | WIRED |
| stills.py / check.py | motion.schedule | final_t for stills and cover; DURATION for basic | WIRED (cover_ms 467 = scene-1 final frame 0.4667 s) |
| bundle.py | bgm.py | validate before purge, install as `bgm` step, bundle.json `bgm` | WIRED (observed in my BGM bundle) |
| encode.py | bgm.filter_graph | only when a bgm path is given | WIRED (observed: loop, fades, -15.9 LUFS) |
| approve.py | bgm.json | two-way check, hashes in approval.json | WIRED (tests) |

### Behavioral Spot-Checks and Probe Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Golden regression | `python3 tools/golden.py` | `golden: PASS 10/10 (재현 불가 1)`, rc 0 | PASS |
| Motion tests | `unittest discover -s tools/tests -p test_motion.py` | 74 tests OK, 391 s | PASS |
| BGM tests | `unittest discover -s tools/tests -p test_bgm.py` | 42 tests OK, 77 s | PASS |
| Motion + count-up bundle, no BGM | `draft.py bundle <mktemp>/...` with `draft-pension-motion.src.json` | exit 0, specprobe 9/9, 90.2 s, bgm null | PASS |
| Same with 10 s sine + licence memo | `draft.py bundle ... --bgm sine.mp3 --bgm-license ...` | exit 0, specprobe 9/9, 95.7 s, -15.9 LUFS, fades | PASS |
| Licence-missing refusals | 4 variants (see truth 5) | exit 1 each, `음원 오류` | PASS |
| Repository hygiene | `git status`, `git ls-files` audio count | clean, 0 | PASS |

No probe scripts (`scripts/*/tests/probe-*.sh`) are declared for this phase: Step 7c not applicable.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| MOTN-01 | line fade + rise, about 250-350 ms | SATISFIED | motion.py ENTER 0.30; geometry tests; feel is a human item |
| MOTN-02 | one 0.3 s scene transition | SATISFIED | CROSS 0.30 cross-fade, schedule windows |
| MOTN-03 | count-up, final value equals script | SATISFIED | frames extracted from my MP4; CountUp tests |
| MOTN-04 | `none` equals existing format | SATISFIED | golden 10/10, NoneUnchanged |
| MOTN-05 | dwell by characters with warnings | SATISFIED | schedule + DWELL_SHORT/LONG |
| MOTN-06 | BGM with memo, fades, level, refused without memo, not committed | SATISFIED | my BGM bundle and refusals; .gitignore |

No orphaned requirements. Housekeeping (not a code gap): `.planning/REQUIREMENTS.md` still lists MOTN-01..06 as Pending/unchecked and ROADMAP Phase 4 plan checkboxes and progress row (0/3 Planned) were not updated; the orchestrator should update these when the phase is closed.

### Anti-Patterns Found

None blocking. `grep TBD|FIXME|XXX` over the phase's changed source files returned nothing.

### Warnings (known residual risks, non-blocking, from 04-REVIEW-FIX.md and my reading)

| # | Item | Severity | Impact |
|---|------|----------|--------|
| 1 | COUNTUP_WRAP only warns; it does not fix the moving frames. If a count-up line breaks differently in the motion DOM than in the static layout, the reel is exit 3 and still approvable; the author must rephrase | Warning | Line-break stability is guaranteed only when no COUNTUP_WRAP warning appears; the reviewer must treat that warning as a real defect |
| 2 | Whole-억 `eok_man_won` count-ups (e.g. `1억 원`) show `0만 원` for the whole count window before switching | Info | Documented in source-format.md; barely counts but is correct at the end |
| 3 | On case-insensitive filesystems (macOS) a user file `BGM.MP3` in a draft without BGM makes approve refuse with a misleading message | Info | Fails closed; Linux unaffected |
| 4 | In-repo BGM sources need git (`check-ignore`); missing git refuses them | Info | Sources outside the repo unaffected |
| 5 | `none_guard` regeneration depends on commit 3fde951 being reachable | Info | Procedure documented in README |
| 6 | Standalone `reel.py` cannot carry music (bundle-only); 04-03 plan text is stale on this point | Info | Roadmap criterion still met via `draft.py bundle` |
| 7 | Dwell bounds compare scene length including the outgoing 0.3 s cross-fade | Info | Intentional, documented (IN-05) |

### Human Verification Required

1. **Watch a motion reel.** Test: bundle `draft-pension-motion.src.json` (or a real draft with `"motion": "basic"`) and watch the MP4 at phone size. Expected: line entry and 0.3 s cross-fade look natural, Hangul breaks never jump, scene-5 count-ups land on 148.5만 / 118.8만, no scene rushed or stalled, the 0.3 s overlap of basis and account text during a cross-fade is acceptable. Why human: motion feel and readability.
2. **Listen with a licensed own track.** Test: `draft.py bundle <draft> --bgm <file> --bgm-license "<note>"`. Expected: 1 s fades, comfortable level, review.md lists file name, sha256 prefix and memo. Why human: real-music loudness (can differ 1-2 LU from the sine result) and the actual licence.
3. **Owner decision on licence evidence format.** The tool accepts any non-blank memo (max 500 characters). Why human: Phase 4 owner gate is still open.

### Gaps Summary

No gaps. Every roadmap criterion is backed by my own golden run, test runs, two bundle runs (with and without BGM), extracted frames, and audio measurements. The phase is waiting only on the three human items above.

---

_Verified: 2026-10-29_
_Verifier: Claude (gsd-verifier)_
