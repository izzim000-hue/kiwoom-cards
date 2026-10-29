---
phase: 02-draft-generation
plan: 04
subsystem: draft-pipeline
tags: [skill, slot, e2e, readme, golden, stdlib, unittest]
status: complete

requires:
  - phase: 02-draft-generation
    provides: "expand/check/caption/convert/figures commands, pension and tax fixtures (Plans 01-03)"
provides:
  - ".claude/skills/make-reel/SKILL.md + references/source-format.md + references/house-style.md: project skill topic/card -> draft folder"
  - "tools/reelkit/slot.py: REELS_DIR, SlotError, SLUG_RE, used_slots, propose, create_draft_dir (contained to 2026/reels/drafts/)"
  - "tools/draft.py slot [--date] [--slug] [--reels-dir] [--create]"
  - "tools/tests/test_draft_e2e.py (SkillDoc, EndToEnd render, RealDirSlot), tools/tests/test_slot.py (16 cases)"
  - "tools/README.md sections '## 릴스 초안: `draft.py`' and '## 수치 등록부'"
affects: [03 approval gate (promotion of drafts to 2026/reels/, compliance review of banned-expression list and caption_config)]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 229805bec9cb6127b76e004122faa55da32434af
plan_head_after: 150de59

tech-stack:
  added: []
  patterns:
    - "SKILL.md holds workflow only; grammar and rules live in two reference files; a unit test checks every documented draft.py subcommand exists"
    - "Publish date is computed from folder contents (max used date + 1 day vs today), never hard-coded"

key-files:
  created:
    - .claude/skills/make-reel/SKILL.md
    - .claude/skills/make-reel/references/source-format.md
    - .claude/skills/make-reel/references/house-style.md
    - tools/reelkit/slot.py
    - tools/tests/test_draft_e2e.py
    - tools/tests/test_slot.py
  modified:
    - tools/draft.py
    - tools/README.md

key-decisions:
  - "Tracer task was verified by its automated verify (e2e render passes, 7 scenes, duration in 21-27 s) before the expansion task; the end-of-phase human check is recorded below, not performed."
  - "Banned-expression list in house-style.md is marked 초안 규칙 — 준법 검토 전 (D-13); final list is a Phase 3 decision."

patterns-established:
  - "Skill rules: stop and ask when a figure is not in the registry (D-06); figures confirm is human-only and appears only on lines containing 사람 or 금지"

requirements-completed: [DRAFT-01, DRAFT-06]

duration: ~25 min
completed: 2026-10-29
---

# Phase 2 Plan 04: make-reel skill, slot, README and phase gates Summary

**Project skill `make-reel` that drives slot -> convert -> figures -> expand -> check -> caption -> `reel.py --layout new --strict` into a gitignored draft folder, plus `draft.py slot` and the phase gates (full suite 344 tests OK, golden PASS 10/10).**

## Performance

- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Commits:** 8fdc7d4 (Task 1), 150de59 (Task 2)
- **Files:** 6 created, 2 modified

## Accomplishments

- `make-reel` skill: Korean triggers in the frontmatter description; 10-step workflow; prohibitions (no `figures confirm`, no unapproved `figures add`, no estimated numbers, no customer names, no legacy layout, no commits of drafts); search text treated as data; stops and asks when a needed figure is not in the registry (D-06).
- `references/source-format.md`: spec.src.json grammar, placeholders, all calc functions and formats with examples checked against `calc.FORMATS` output, series behaviour, caption.src.json shape, fixture pointers.
- `references/house-style.md`: house pattern, new-layout width (about 8 syllables), few-shot spec pointers, D-13 banned expressions, caption guide.
- `tools/reelkit/slot.py` + `draft.py slot`: computed date proposal (currently 2026-11-08 for the real reels dir; the literal does not appear in slot.py), slug validation (`^[a-z0-9]+(-[a-z0-9]+)*$`, max 40), conflict reports, creation contained under `drafts/` via `is_relative_to`.
- E2E test renders the pension fixture through the whole pipeline: expand, check --strict, caption and `reel.py --layout new --strict` all exit 0; 7 scenes; 21-27 s; safe PNG written; check.json no errors with only 미확인 ids in needs_check; caption first line starts with the series line.
- README gained the draft.py and figure registry sections; states that `figures confirm` is run only by the human checker.

## Verification Results

- `test_draft_e2e.py`: 6 tests OK. `test_slot.py`: 16 tests OK.
- Slot proposal check against the real reels dir: proposed_date > 2026-11-07, ask true, no conflicts, nothing created; `--slug ../x` exits 1 with "초안 오류".
- Full suite: `python3 -m unittest discover -s tools/tests -v` -> Ran 344 tests, OK, no ERROR/FAIL lines.
- Golden: `golden: PASS 10/10 (재현 불가 1)`, rc 0, 재현 불가 line for 2026-10-19-savings-interest present.
- `git status --porcelain -- 2026/reels` empty after both runs; STATE.md and ROADMAP.md untouched.

## Deviations from Plan

None - plan executed as written. Two small notes:

- The CLI slug test passes `--slug=-x` instead of `--slug -x` because argparse reads a bare `-x` as an option and exits 2 before the tool sees it; the tool itself rejects the slug with exit 1. Test-form only, no tool bug found by test_slot.py.
- The per-plan commit ledger (protocol 0c) was not created before the first commit; `plan_head_before` is the parent of the first task commit (`git rev-parse 8fdc7d4~1`), and `commits: 2` equals `git rev-list --count 229805b..150de59`.

## Pending Human Verification (end of phase)

Not performed by the executor. In a new Claude Code session:

1. Say "연금저축 세액공제 한도로 릴스 만들어 줘" and, separately, give `2026/04-salary-two-owners-2/spec.json`.
2. Confirm the make-reel skill proposes a date and slug and asks once; stops and asks before using any figure not in the registry; writes spec.src.json, spec.json, check.json, caption.txt and the MP4 under `2026/reels/drafts/<date>-<slug>/`; reports the 확인 필요 lines; for the card input reports NOT_IN_CARD numbers; and that `git status` shows nothing new.
3. Watch the MP4: about 7 scenes, about 25 s, series line on the first scene, 다음 편 line in the last scene when a teaser was given.

## Known Stubs

None. Caption disclaimer/CTA text in `tools/data/caption_config.json` and the D-13 banned-expression list are explicitly drafts pending Phase 3 compliance review (not stubs blocking this plan's goal).

## Threat Flags

None. No new network endpoints or auth paths; the only new filesystem write path (draft folder creation) is the one covered by T-02-14 and is contained and tested.

## Self-Check: PASSED

- Files present: SKILL.md, both references, slot.py, test_draft_e2e.py, test_slot.py, README sections.
- Commits 8fdc7d4 and 150de59 are ancestors of HEAD.
- `grep -c '2026-11-08' tools/reelkit/slot.py` prints 0.
