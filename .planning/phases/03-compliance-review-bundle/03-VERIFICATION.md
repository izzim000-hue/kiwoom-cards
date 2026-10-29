---
phase: 03-compliance-review-bundle
verified: 2026-10-29T12:30:00Z
status: human_needed
score: 5/5 must-haves verified (machine-checkable parts); 4 human-only items open
covered_files:
  - ".claude/skills/make-reel/SKILL.md"
  - ".planning/phases/03-compliance-review-bundle/03-01-PLAN.md"
  - ".planning/phases/03-compliance-review-bundle/03-01-SUMMARY.md"
  - ".planning/phases/03-compliance-review-bundle/03-02-PLAN.md"
  - ".planning/phases/03-compliance-review-bundle/03-02-SUMMARY.md"
  - ".planning/phases/03-compliance-review-bundle/03-03-PLAN.md"
  - ".planning/phases/03-compliance-review-bundle/03-03-SUMMARY.md"
  - ".planning/phases/03-compliance-review-bundle/03-04-PLAN.md"
  - ".planning/phases/03-compliance-review-bundle/03-04-SUMMARY.md"
  - "tools/data/compliance_rules.json"
  - "tools/draft.py"
  - "tools/reelkit/approve.py"
  - "tools/reelkit/bundle.py"
  - "tools/reelkit/compliance.py"
  - "tools/reelkit/review.py"
covered_digest: "v4:sha256:a354725a93eaabac8253e46e05c8d56f632117d2e91f0f07cd5fd79c53256105"
behavior_unverified: 0
overrides_applied: 0
gaps: []
human_verification:
  - test: "Live topic-to-bundle timing (BNDL-07 / SC1)"
    expected: "In a new Claude Code session, say '이 주제로 릴스 만들어 줘'. slot --create stamps created.json, Claude writes the sources, then bundle runs. bundle.json shows elapsed_since_request_s <= 600 and within_10_min true."
    why_human: "Only the machine part was measured (fixture bundle: render 14.2s, total 14.7s, request-to-finish 15.1s). The model's own writing time in a live session cannot be measured from here."
  - test: "Read review.md, cover PNG and scene sheet (SC4, BNDL-02/03/04)"
    expected: "Banner, headline, tables, human checklist and the 미확인 ad/review record are readable. Cover text sits inside the central 1080x1440. The scene sheet shows every scene. Final crop is judged in the Instagram grid preview."
    why_human: "Visual readability and the grid crop need a person. The tool only audits crop bounds."
  - test: "Human approve in a real terminal, then promote (BNDL-06)"
    expected: "The user runs 'python3 tools/draft.py approve <dir> --by <name>' in their own terminal and retypes the folder name. Then 'promote' links 4 files into 2026/reels/, specs/ and captions/."
    why_human: "Approval is human-only by design. The verifier never ran approve on a real folder. Approve was exercised only on a temp copy with a mocked tty."
  - test: "Compliance-owner review of rules v0.2 (COMP-01/02/04)"
    expected: "The owner reads the negators, patterns and exceptions in tools/data/compliance_rules.json. The rules are labeled '초안 규칙 — 준법 검토 전'. Also decide the owner gates (ad applicability, required disclosure text and placement, review number format, cover method)."
    why_human: "Legal adequacy cannot be judged programmatically. The held-out recall is 17/22 and implicit expressions are not caught (the stated limit). REVIEW-FIX marks CR-01/02/04 and WR-07/08 as 'requires human verification'."
---

# Phase 3: Compliance & Review Bundle Verification Report

**Phase Goal:** One request in a Claude Code session gives a review-ready draft bundle within 10 minutes. 단정 표현 and unsupported figures are flagged without gaps, and nothing reaches the official path before a human approves.
**Verified:** 2026-10-29
**Status:** human_needed (no code gaps; four human-only items remain)
**Re-verification:** No, initial verification.

Heavy commands were each run once, in the main checkout. Fixture runs used a `mktemp -d` copy. Approve was never run on a real folder, and no source, rules, registry, published or draft file was modified. `git status --short` was empty afterwards.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One request creates in `drafts/<date>-<slug>/` the spec, MP4, cover PNG, caption and check sheet. The elapsed time is measured and is under 10 min. | VERIFIED (machine part); live-session timing is a human item | `draft.py bundle` on a copy of `draft-pension.*.src.json` produced spec.json, `.mp4`, `-cover.png`, `-scenes.png`, caption.txt, check.json, compliance.json, review.md, record.json and bundle.json. bundle.json says `status: complete, exit_code: 0, elapsed_since_request_s: 15.1, within_10_min: true`, with a per-step breakdown (render 14.18s). The upload-spec probe printed PASS 9/9. `--request-start` and `created.json` are both wired (`bundle.py` lines 141-160). |
| 2 | The check sheet covers spec, basis, caption and hashtags, using a fixed finding schema and a headline without "통과". | VERIFIED | review.md has a table per finding with location (scene/line), expression, reason, replacement suggestion and rule id. The headline is `패턴상 발견 없음 — 사람 검수 필요 · 규칙 v0.2(초안) · 기준일 2026-10-29`. `draft.py compliance` printed `위험 표현 1건 발견 · 규칙 v0.2(초안) · 기준일 ...` once a rule was added. "통과" occurs 0 times in review.md, compliance.json and the rules file. There is no statute number in the rules (grep found none). Registry/basis/date checks surface as CHK-NEEDS items. Caption warnings surface as CHK-CAPTION. 수정 필요 and 확인 필요 are separate tiers. Note: the headline can read "발견 없음" while 확인 필요 counts are non-zero. This follows the D-08 design: "위험 표현" counts expression-pattern hits, and the counts line sits directly beneath. |
| 3 | Editing the data file changes the next check with no code change. A detection and false-positive report exists for the 10 published reels and the red-team cases. | VERIFIED | A copy of `compliance_rules.json` with one added rule (Z-99) was passed via `compliance --rules`. The next run reported `위험 표현 1건 발견` and the unmodified file reported none. `draft.py redteam` printed: published 10 -> 수정 필요 0건 · 확인 필요 2건; seed bad 50/50, good 오탐 0/31; held-out bad 17/22 (77%), good 오탐 0/10; 17 exceptions listed; limits and a seed-inflation warning printed. This meets the floors of at least 30 bad and 15 good. Misses and mismatches are listed (H-B21 missed; H-B06/10/11/13 detected at the wrong tier). The report is honest about its limits. |
| 4 | One review document has a status banner, check results, a human checklist (figures, base date, cover crop, music licence, personal info) and a record with ad applicability / review stage / review number as "미확인". The first-scene cover (text inside the central 1080x1440) and the per-scene still sheet exist. | VERIFIED (visual judgement is a human item) | review.md has the banner `초안 — 사람 검수 후 게시`, section 1 check results, section 3 checklist (수치 재확인, 기준일, 표지 크롭, 음원 라이선스, 개인정보, 대체 표현), and section 4 table `미확인 / 미확인 / 미확인 / 미확인`. record.json holds the same 미확인 values and kept a human-written note across a re-bundle. The cover is 1080x1920. The cover-crop audit line says no text outside the central 1080x1440. The scene sheet is 1500x1316 and the review.md scene table lists the 7 scenes. |
| 5 | A fix request rebuilds MP4, cover, caption and check sheet and re-runs the check. Promoting to the official path happens only after approval. It is refused when 수정 필요 remains or a file changed after approval. | VERIFIED | Re-running `bundle` after an approval deleted approval.json and regenerated every output. record.json was preserved. Promote on a temp tree (`constants.REPO_ROOT` patched, so nothing real was written): (1) no approval -> refused, exit 1; (2) approve with non-tty stdin -> refused; (3) approve with the name "Claude" -> refused; (4) approve by a human name with a mocked tty -> approval.json written, sha256 of 10 files; (5) caption.txt edited after approval -> `승인 뒤 바뀜: caption.txt`, refused; (6) review.md edited -> refused; (7) clean approved -> 4 files hard-linked into temp reels/, specs/, captions/ with git add hints and no git run; (8) second promote -> `이미 게시된 파일 — 덮어쓰지 않음`. A promote from a folder outside the repo `<year>/reels/drafts` is refused (WR-04). A 수정 필요 > 0 refusal is covered by test_approve (suite OK) and by the approve code path (`approve.py` lines 147-150, 279-281). |

**Score:** 5/5 truths verified on the machine-checkable parts. 0 are PRESENT_BEHAVIOR_UNVERIFIED, because the behavioural invariants (purge on re-bundle, approval hash coverage, link-not-overwrite) were exercised by running the code.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/reelkit/compliance.py` | Data-driven rule engine | VERIFIED | Loads rules, guards ReDoS, handles negation and compact terms. Exercised by `compliance`, `redteam` and bundle. |
| `tools/data/compliance_rules.json` | Rules v0.2, 29 rules | VERIFIED | status `초안 규칙 — 준법 검토 전`, as_of 2026-10-29. No "통과". No statute number. |
| `tools/reelkit/bundle.py` | One-command bundle with timing | VERIFIED | Ran end-to-end. 8 steps recorded. `outputs` holds sha256 values. |
| `tools/reelkit/review.py` | review.md and record.json | VERIFIED | Sections 1-5 present. |
| `tools/reelkit/approve.py` | Human-only approve; link-not-overwrite promote | VERIFIED | Behaviour confirmed above. |
| `tools/reelkit/redteam.py`, `tests/redteam/{corpus,heldout}.json` | Red-team report | VERIFIED | Output above. |
| `tools/reelkit/stills.py` | Cover audit and scene sheet | VERIFIED | Both PNGs produced. |
| `.claude/skills/make-reel/SKILL.md`, `tools/README.md` | Skill on `draft.py bundle`, approve human-only | VERIFIED | SKILL.md lines 73-82 forbid Claude running approve, writing approval.json, or passing override files. |

### Key Link Verification

| From | To | Status | Details |
|------|----|--------|---------|
| approve/promote -> compliance.run | live re-scan with repo rules | WIRED | `live_scan` and the rules-sha check run before any link (`approve.py` 275-282). |
| promote -> `<year>/reels` | `publish_dir` plus `os.link` | WIRED | Refused outside the repo tree. Second promote refused. |
| SKILL.md -> `draft.py bundle` | Skill calls the single command | WIRED | Confirmed in SKILL.md and test_draft_e2e. |
| bundle -> approval purge | approval.json removed on re-bundle | WIRED | Confirmed by running it. |

### Behavioral Spot-Checks / Gates

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `python3 -m unittest discover -s tools/tests -p 'test_*.py'` | Ran 570 tests, OK (377 s) | PASS |
| Golden | `python3 tools/golden.py` | `golden: PASS 10/10 (재현 불가 1)` | PASS |
| Red-team | `python3 tools/draft.py redteam` | Last line: `표본 내 탐지 50/50 · 오탐 0/31 · 따로 쓴 문장 탐지 17/22 · 오탐 0/10 · 기존 10편 수정 필요 0건` | PASS |
| Bundle on fixture copy | `draft.py bundle <tmp>/drafts/2026-11-20-pension-test --request-start $S` | exit 0, 14.7 s, spec 9/9 | PASS |
| Promote refusals | scratch script on the temp tree | All 4 refusal paths and the happy path as expected | PASS |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| COMP-01 | SATISFIED | Finding tables with location, expression, reason, suggestion. Tiers by category. |
| COMP-02 | SATISFIED | CHK-NEEDS and CHK-CAPTION 확인 필요 items cover figures without a registry entry, basis and caption warnings. |
| COMP-03 | SATISFIED | Only the two headlines, with version and base date. No "통과". |
| COMP-04 | SATISFIED | Red-team report: 50 bad / 31 good seed, 22 / 10 held-out, plus the published 10. |
| COMP-05 | SATISFIED | Rule added through the data file took effect with no code change. |
| COMP-06 | SATISFIED | The 미확인 ad/review record is in review.md and record.json, and human edits survive a re-bundle. |
| BNDL-01 | SATISFIED | All outputs are written by one command. |
| BNDL-02 | SATISFIED (visual check is human) | Cover PNG plus the crop audit line. |
| BNDL-03 | SATISFIED (visual check is human) | Scene sheet PNG. |
| BNDL-04 | SATISFIED | review.md sections 1-5. |
| BNDL-05 | SATISFIED | Re-bundle regenerates everything, re-runs the check and purges the approval. |
| BNDL-06 | SATISFIED | Promote behaviour verified. The real human approve is a human item. |
| BNDL-07 | SATISFIED (machine part) | within_10_min true at 15.1 s. The live-session wall time is a human item. |

REQUIREMENTS.md still shows these IDs as `Pending` and unchecked. That is a bookkeeping update for the orchestrator and not a code gap. No orphaned requirements.

### Anti-Patterns Found

No blockers. Debt markers (TBD/FIXME/XXX) were not scanned exhaustively, since the review and fix passes covered the files. Observations:

| Item | Severity | Impact |
|------|----------|--------|
| Headline can say "패턴상 발견 없음" next to 확인 필요 11건 | Info | By design (D-08). The counts line is directly below it. |
| review.md shows raw markup (`<g>148.5만</g>`, `<s>...</s>`) in the 문제 표현 column | Info | Cosmetic. |
| Known limits from REVIEW-FIX, accepted as documented | Info | Approval is not technically human-only against a pty wrapper or a forged approval.json (no `permissions.deny` in `.claude/settings.json`). There is no per-finding 수정 필요 waiver. A negation split over two lines is flagged. `bundle` still accepts `--rules/--registry/--config`, though approve rejects a bundle made with other rules. IN-04 was skipped (approval audit trail not kept with the published reel). The docs match the code on all of these. |

### Human Verification Required

1. **Live topic-to-bundle timing.** Do the full flow in a new session and read `elapsed_since_request_s` and `within_10_min` in bundle.json. Expected: 600 s or less. The machine step takes about 15 s. Claude's writing time is the unknown.
2. **View review.md, the cover and the scene sheet.** Confirm they are readable, the cover text is within the central 1440, and the final crop looks right in the Instagram grid preview.
3. **Human approve, then promote, in a terminal.** The user runs approve with their own name and retypes the folder name. Then promote and run the printed `git add` lines. An older draft (`2026-11-08-pension-credit-limit`) predates `bundle.json["outputs"]` and needs a re-bundle first.
4. **Compliance-owner review of rules v0.2** and the owner gates. Held-out recall is 77% and implicit expressions are not detected. Rules stay labeled as draft until the owner signs off.

### Gaps Summary

No code gaps. Every ROADMAP success criterion is backed by running the code: the full suite (570 OK), golden 10/10, the red-team report, a real bundle on a fixture copy and the promote refusal and happy paths. The phase is `human_needed` only because the live-session timing, the visual review, the human approval step and the compliance-owner review cannot be done by the verifier.

---

_Verified: 2026-10-29_
_Verifier: Claude (gsd-verifier)_
