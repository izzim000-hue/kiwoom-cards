---
phase: 03-compliance-review-bundle
plan: 04
subsystem: approval-promote-docs
tags: [approve, promote, human-gate, sha256, link-not-overwrite, make-reel-skill, stdlib]
status: complete

requires:
  - phase: 03-compliance-review-bundle
    provides: bundle.validate_draft_dir/draft_paths, compliance.run, review.ensure_record, figures.is_ai_name, golden manifest, redteam report
provides:
  - tools/reelkit/approve.py (PROMOTED, HASHED, file_hashes, approve_cli, promote_cli)
  - `draft.py approve DIR --by NAME [--rules]` (human only) and `draft.py promote DIR [--rules]`
  - tools/tests/test_approve.py (22 tests)
  - published-reel tests pinned to the golden manifest (5 modules)
  - make-reel SKILL.md on `draft.py bundle`, README sections for bundle, compliance/redteam, approve/promote
affects: [make-reel skill, first real promote]

requirements-completed: [BNDL-06, BNDL-01, BNDL-07]

actuals:
  tokens: 16100
  tasks: 3
  commits: 3
plan_head_before: 270f4fcf9c5ddaa517b996a400c9b491fb647353
plan_head_after: 96bfb09f59033171b9cb4304aa4c445bbc29ab37

key-files:
  created:
    - tools/reelkit/approve.py
    - tools/tests/test_approve.py
  modified:
    - tools/draft.py
    - tools/tests/test_check.py
    - tools/tests/test_layout.py
    - tools/tests/test_numscan.py
    - tools/tests/test_spec.py
    - tools/tests/test_specprobe.py
    - tools/tests/test_draft_e2e.py
    - .claude/skills/make-reel/SKILL.md
    - .claude/skills/make-reel/references/house-style.md
    - tools/README.md

key-decisions:
  - "approval.json holds sha256 of 8 files (mp4, cover, spec.json, caption.txt + spec.src.json, caption.src.json, check.json, compliance.json); promote recomputes them, re-scans live with the current rules, and notes a rules-sha change"
  - "approve hashes twice (before showing, after the retype) and refuses if anything changed while the human was reading"
  - "promote copies to `.<target>.part`, verifies the sha256 against the approval, then os.link (FileExistsError refuses); every target linked in the run and every part is removed on failure; specs/ and captions/ created by the run are removed again"
  - "SkillDoc no longer requires `check`/`caption` subcommands in the skill docs (the skill uses only bundle); it now requires bundle, approve and promote"
  - "The skill is told never to apply suggested wording without the user's OK and never to describe results as clean"

duration: about 45 min (full suite 6m25s, golden and fixture bundle included)
completed: 2026-10-29
---

# Phase 3 Plan 04: Approve, Promote, Skill and Docs Summary

**Only a human at a terminal can approve a bundle; `promote` then moves exactly the approved, unchanged, 수정 필요-free four files into the draft's own reels folder and can never overwrite a published reel. The make-reel skill now has one render path, `draft.py bundle`.**

## Accomplishments

- Task 1 (tracer, `1dad65a`): `approve_cli` refuses without a TTY before any work, rejects empty and AI-looking names, requires a complete bundle.json, re-scans live (수정 필요 > 0 refuses), shows headline, counts, record values (미확인 fields marked), the bundle exit-code note and the hashed file list, requires the folder name retyped (EOF counts as empty), and writes approval.json atomically. `promote_cli` is all-or-nothing in the planned order: folder validation, approval presence and name, per-file hash (names the first differing file), live re-scan with the current rules (rule sha change printed as a notice), year check, preflight of four targets, `.part` copy + sha check + `os.link`, rollback. It prints `git add` lines and never calls git (`reelkit.approve` has no `subprocess`). 22 tests cover every case in the plan plus EOF, incomplete bundle, provenance-file edit, a mid-run link failure (exit 2, nothing left, `captions/` removed again) and a year mismatch.
- Task 2 (`43731b4`): the five modules that globbed `2026/reels` now read `golden.load_manifest()["entries"]` (10 reproducible specs, 11 MP4s) with the `== 10` / `== 11` assertions kept. With a temporary 11th v2 spec and 12th MP4 present all five pass; `git status --porcelain -- 2026/reels` is empty afterwards.
- Task 3 (`96bfb09`): SKILL.md (Korean) records `date +%s` first, writes both sources, then `python3 tools/draft.py bundle <dir> --request-start <값>`; exit codes 1/3/2/4 handling with at most 2 fix rounds; findings are shown with suggested wording and only changed after the user's OK, then the bundle is rerun; report lists headline and counts line, cover and scenes paths, `elapsed_since_request_s` and `within_10_min`; approve is 사람 전용 / 금지 on every line, Claude never writes approval.json or record.json values other than 미확인, promote only on request after a human approval. house-style.md points at `tools/data/compliance_rules.json`. README has the three new sections (bundle, 표현 점검, 승인과 옮기기) including the deferred permission-rule residual risk. SkillDoc test updated (bundle/approve/promote exist, every approve line marked human-only).

## Phase gates (run once each)

| Gate | Result |
|------|--------|
| `python3 tools/doctor.py --quiet` (precondition) | exit 0, playwright 1.63.0, Chromium 153, fonts 3/3, ffmpeg 6.1.1 |
| `test_approve.py` | Ran 22, OK |
| five pinned modules with temporary 11th spec / 12th MP4 | all OK; `git status --porcelain -- 2026/reels` empty |
| `test_draft_e2e.py` | Ran 7, OK |
| full suite `test_*.py` | Ran 531 tests in 384.7 s, OK |
| `python3 tools/golden.py` | last line `golden: PASS 10/10 (재현 불가 1)`, rc 0, `git status --porcelain -- 2026/reels` empty |
| fixture bundle (pension) | exit 0, `elapsed_s 14.61 since_request 14.9 within_10_min True status complete` |
| `draft.py redteam` | last line ends `기존 10편 수정 필요 0건` |

### Fixture bundle timing (bundle.json)

```
bundle: 2026-11-08-pension-credit-limit · 패턴상 발견 없음 — 사람 검수 필요 · 규칙 v0.1(초안) · 기준일 2026-10-29 · 확인 필요 11건 · 14.6초
elapsed_s 14.61 since_request 14.9 within_10_min True status complete
```

### Red-team report (`python3 tools/draft.py redteam`)

```
규칙 v0.1(초안) · 기준일 2026-10-29 · 규칙 28개 · 초안 규칙 — 준법 검토 전
[기존 10편] 수정 필요 0건 · 확인 필요 2건
  확인 필요 · 2026-10-19-rate-secret-1 · scene 5 line 1 · R-02 · "이자소득세 15.4% 빼면 세후 약 2.3"
  확인 필요 · 2026-10-29-ebook-event · scene 3 line 2 · T-03 · "세금 없이"
[레드팀 부적절 41건 · 표본 내] 탐지 41/41 (100%) · explicit 36/36 · obfuscated 2/2 · implicit 3/3
  분류별: 단정·보장 15/15 · 세무 단정 6/6 · 상품 권유 5/5 · 비교·비방 5/5 · 개인정보 6/6 · 근거 누락 4/4
  놓친 문장: 없음
  분류/등급 불일치: 없음
[레드팀 적절 21건 · 표본 내] 오탐 0/21 (수정 필요 오탐 0)
  오탐 문장: 없음
[따로 쓴 문장 부적절 22건 — 규칙 조정에 쓰지 않음] 탐지 14/22 (64%) · explicit 12/14 · obfuscated 2/3 · implicit 0/5
  분류별: 단정·보장 2/4 · 세무 단정 0/3 · 상품 권유 2/3 · 비교·비방 2/3 · 개인정보 4/4 · 근거 누락 4/5
  놓친 문장:
    H-B01 (implicit) 가입만 하면 손해 볼 일은 없습니다 / 안전하게 불어나는 돈, 걱정 내려놓으세요
    H-B05 (explicit) 이렇게 하면 세금 한 푼도 안 냅니다 / 신고도 필요 없어요
    H-B06 (implicit) 연금저축에 넣으면 환급은 따 놓은 당상 / 돌려받는 세금, 걱정 마세요
    H-B10 (implicit) 다른 건 볼 것 없이 이 상품 하나면 끝 / 고민은 이쯤에서 접으세요
    H-B13 (implicit) 타사 상품에는 단점만 있고 / 저희 상품에는 장점만 있습니다
    H-B21 (implicit) 대부분의 사람들이 노후 자금이 모자랍니다 / 통계가 그렇게 말해 줍니다
  분류/등급 불일치:
    H-B04 기대 단정·보장/수정 필요 · 실제 단정·보장/확인 필요(G-07), 근거 누락/확인 필요(R-05)
    H-B07 기대 세무 단정/수정 필요 · 실제 단정·보장/수정 필요(X-compact)
[따로 쓴 문장 적절 10건] 오탐 1/10 (수정 필요 오탐 1)
  오탐 문장:
    H-G01 G-02 "수익을 보장"
[예외 처리로 제외] 10건 · G-01 3건 · G-02 3건 · G-03 1건 · G-05 1건 · G-07 1건 · T-01 1건
[규칙 시간] 가장 느린 규칙 P-01 0.17ms (문장당 최대)
주의: 표본 내 수치는 규칙을 쓴 쪽이 같은 문장을 보고 맞춘 결과라 실제보다 높게 나옵니다. 따로 쓴 문장 줄을 함께 보세요.
한계: 키워드·패턴 방식이라 암시적 표현은 잡지 못합니다 (AI 의미 점검은 v2)
redteam: 표본 내 탐지 41/41 · 오탐 0/21 · 따로 쓴 문장 탐지 14/22 · 오탐 1/10 · 기존 10편 수정 필요 0건
```

Open item for the rules owner (unchanged since Plan 02, not acted on here): the held-out line shows 64% detection and one 수정 필요 false positive (H-G01, "수익을 보장하는 상품은 없습니다" hits G-02). Because 수정 필요 blocks `promote` with no waiver, that false-positive class should be decided before the rules are called ready.

## Task Commits

1. Task 1: `1dad65a` feat(03-04): human approve and gated promote that never overwrites
2. Task 2: `43731b4` test(03-04): pin published reels to the golden manifest
3. Task 3: `96bfb09` docs(03-04): make-reel skill on draft.py bundle, README for bundle, compliance, approve, promote

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `approve --help` did not show 사람 전용**
- **Found during:** Task 1 (test_help_marks_human_only)
- **Issue:** the text was only in the top-level `help=`; argparse shows it in `draft.py --help`, not in `draft.py approve --help`.
- **Fix:** added the same text as `description=` for approve (and promote).
- **Files modified:** tools/draft.py
- **Commit:** 1dad65a

**2. [Rule 3 - Blocking] SkillDoc required `check` and `caption` to appear in the skill docs**
- **Found during:** Task 3
- **Issue:** the plan makes `draft.py bundle` the skill's only path, so the docs no longer name `check`/`caption` as separate steps; the old required set could not hold.
- **Fix:** required set is now slot, expand, convert, bundle, approve, promote, figures list, figures add (every named subcommand still has to answer `--help` with 0).
- **Files modified:** tools/tests/test_draft_e2e.py
- **Commit:** 96bfb09

### Environment note (not a code deviation)

`2026/reels/drafts/2026-11-08-pension-credit-limit/` existed before this plan (created earlier today, gitignored, from a previous manual run). It makes `test_draft_e2e.RealDirSlot.test_proposes_later_date_and_creates_nothing` fail with a slug conflict, independent of this plan's changes. To run the full-suite gate I moved the folder into a mktemp dir for the gate runs and moved it back afterwards (state unchanged, nothing deleted). It will fail that one test again for anyone who still has the folder; it is out of scope here and worth deleting by the owner.

### Interpretation choices

- The plan asks approve to show "layout/crop warning counts from bundle.json", but bundle.json stores only the exit code, not counts. approve prints a note when bundle.json's exit_code is 3 or 4 and points to review.md.
- `PROMOTED`/`HASHED` are tuples of `bundle.draft_paths` keys (the file names depend on the folder name); `file_hashes` maps real file names to sha256.

## Pending Human Verification (end of phase; not performed by the executor)

In a new Claude Code session:
1. Say "연금저축 세액공제 한도로 릴스 만들어 줘". Confirm the skill asks once for date/slug, writes the sources, runs `draft.py bundle ... --request-start`, and reports the review.md headline, findings with suggestions and the timing. Open bundle.json: `elapsed_since_request_s` recorded and `within_10_min` true (BNDL-07 real topic-to-bundle measurement; only the fixture measurement above was machine-checked).
2. Open review.md, `<name>-cover.png`, `<name>-scenes.png`: banner, 점검 결과, 사람 확인 목록, 광고·심의 기록 (미확인) present; cover text inside the grid crop; every scene visible.
3. Ask for a wording change; confirm the bundle reruns and the check results change.
4. In your own terminal run `python3 tools/draft.py approve <dir> --by <이름>` and retype the folder name; confirm Claude never ran approve. This executor never ran `draft.py approve` against any real folder; tests drove it only through the in-process FakeTty harness inside temp directories.
5. Optional: edit caption.txt and confirm `promote` refuses; or rerun the bundle and confirm approval.json is gone. Promote into the real 2026/reels only if you intend to publish; committing stays the human's step.
6. Compliance-owner review of tools/data/compliance_rules.json remains open (rules are 초안 규칙 — 준법 검토 전).

## Known Stubs

None. The mp4/cover bytes in test_approve.py are placeholders by design (promote only hashes and copies).

## Threat Flags

None beyond the plan's threat model (T-03-12 to T-03-17 mitigated as planned; residual pty-wrapper and hand-written approval.json/record.json risk documented in tools/README.md, permission deny rule left to the user). No package installs.

## Self-Check: PASSED

- tools/reelkit/approve.py, tools/tests/test_approve.py, this SUMMARY: present.
- Commits 1dad65a, 43731b4, 96bfb09: present on branch ccr-f9cedca2-3o2v27, not pushed.
- `git status --porcelain -- 2026/reels` empty; STATE.md and ROADMAP.md untouched.
