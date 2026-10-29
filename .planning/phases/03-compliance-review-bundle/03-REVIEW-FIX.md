---
phase: 03-compliance-review-bundle
fixed_at: 2026-10-29T00:00:00Z
review_path: .planning/phases/03-compliance-review-bundle/03-REVIEW.md
iteration: 1
findings_in_scope: 21
fixed: 20
skipped: 1
status: partial
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-10-29
**Source review:** .planning/phases/03-compliance-review-bundle/03-REVIEW.md
**Iteration:** 1 (single pass, no re-review loop)

**Summary:**
- Findings in scope: 21 (CR-01..04, WR-01..09, IN-01..08)
- Fixed: 20. WR-01 is fixed only in part; the rest is residual risk that needs the user's decision.
- Skipped: 1 (IN-04)
- Where verification ran: in the **main checkout** `/home/user/kiwoom-cards`, not in an isolated worktree. The orchestrator's root-pin guard requires `git rev-parse --show-toplevel` to equal the main checkout, so a worktree would fail it. The numbers below can be reproduced from this tree.

Compliance rule changes are general morphology, anchoring and negation-scope changes. None of them was tuned to `tools/tests/redteam/heldout.json`, and that file was not edited. New regression sentences went into the seed corpus (`corpus.json`) only. The rules file is now **v0.2** (as_of 2026-10-29). Its status is still `초안 규칙 — 준법 검토 전`. Every pattern rule keeps hit and miss examples, and there is no "통과" and no statute number in it.

Because the rule changes are logic changes, CR-01, CR-02, CR-04, WR-07 and WR-08 are marked **fixed: requires human verification**. A human should read the new negators and patterns in `tools/data/compliance_rules.json` before relying on them.

## Fixed Issues

### CR-01: The negation window crossed scene lines and clauses
**Status:** fixed: requires human verification · **Commit:** abc2dfe
**Files:** `tools/reelkit/compliance.py`, `tools/data/compliance_rules.json`, `tools/tests/test_compliance.py`, `tools/tests/test_redteam.py`, `tools/tests/test_bundle.py`, `tools/tests/redteam/corpus.json`
**Applied fix:**
- The negation window now stops at a single newline, at a comma, at sentence ends and at 지만-type connectors. It never crosses a scene line.
- `negators` and `mention_markers` are anchored at the start of the window (`re.match`). A negation must therefore attach to the matched predicate, as in 보장하지 않 / 보장 안 돼 / 보장된다는 뜻은 아니 / 기대하지 마세요 / …라고 생각하면 안 됩니다.
- `오해` was dropped from the negators.
- `except` rules keep their own wider sentence window.
- A line that ends in a quotative (…이라고 / …다고) or "…다는 보장은" counts as a mention.

Regressions:
- `NegationScope` tests.
- Seed entries B42–B46 and G22–G24.
- New rule examples, for instance "원금 보장 상품이에요\n놓치지 마세요", which is now a hit.

### CR-02: 수정 필요 false positives on correct wording
**Status:** fixed: requires human verification · **Commit:** 7520fba
**Files:** `tools/reelkit/compliance.py`, `tools/data/compliance_rules.json`, tests, `corpus.json`
**Applied fix:**
- **Existential negation.** "…하는 상품은 없습니다", "확정 수익이란 없습니다" and "손실 없는 투자는 없어요" now count as negated. The head nouns come from a closed list, so "원금 보장 걱정은 없어요" is still flagged.
- **C-03.** The bare `사기|바가지` alternatives are gone, and C-03 now needs a competitor subject. The 사다+기 reading is excluded (사기 전에, 사기 위한). A new rule, C-05, catches any remaining bare 사기/바가지/엉터리 at **확인 필요** only.
- **무조건.** G-03 and T-01 match `무조건` only at the start of a word.
- **X-compact.** A compact term counts only when it starts a word in the original field, so 근무 조건 and 의무 조건 no longer hit.
- **P-02.** Title nouns (고객님, 강사님, …) and common modifiers before 고객님 are no longer read as names. The `고객님께` except, which was hiding "김철수 고객님께", was removed.

Regressions: `CorrectWordingIsNotMustFix` tests and seed good entries G25–G30.

**Not done:** a per-finding human waiver for 수정 필요. That is a product decision, so a remaining false positive is still a hard stop at promote.

### CR-03: The caller could choose promote's rules, and empty rule lists loaded
**Status:** fixed · **Commit:** 14a5a13
**Files:** `tools/reelkit/approve.py`, `tools/reelkit/compliance.py`, `tools/draft.py`, `tools/tests/test_approve.py`, `.claude/skills/make-reel/SKILL.md`, `tools/README.md`
**Applied fix:**
- `approve` and `promote` no longer have `--rules`. Both always load `tools/data/compliance_rules.json`.
- `promote` refuses when the rules sha256 differs from the one in the approval. Before, it printed a notice and carried on.
- `load_rules` refuses an empty `rules` list.
- `approve` refuses a bundle whose `compliance.json` was made with another rules file.
- The SKILL "하면 안 되는 것" list now forbids passing `--rules`, `--registry` or `--config` overrides.

Regressions:
- `test_rules_changed_since_approval_refuses`
- `test_rules_flag_removed_from_approve_and_promote`
- `test_empty_rule_list_is_refused_at_load`
- `test_bundle_checked_with_other_rules_refuses_approval`

### CR-04: Explicit tax and loss-denial claims got no finding
**Status:** fixed: requires human verification · **Commit:** fa77d5b
**Files:** `tools/reelkit/compliance.py`, `tools/data/compliance_rules.json`, tests, `corpus.json`
**Applied fix:**
- **T-01** now covers the 냅/낸다/낸/낼 forms and 내실 필요. It also has an intensifier slot (한 푼도 / 하나도 / 일절 / 땡전 한 푼). Conditionals such as "안 내면" and "안 낸 사람" stay out.
- **G-05** gets a particle slot ("손해 볼 일은 없"), plus 날/입을 and "손해 보지 않 / 안 봐". Advice forms (보지 않도록, 않으려면) are excluded.
- **`compact_terms`** now accepts `{term, category}`. X-compact findings use that category, and the longest term wins, so "무 조 건 절 세" becomes 세무 단정. New tax composites were added.

Regressions: `TaxAndLossClaims` tests and seed entries B47–B49 and G31.

### WR-01: Nothing technically enforces human-only approval; approval.json can be forged
**Status:** fixed in part · **Commit:** a014c51
**Files:** `tools/reelkit/approve.py`, `tools/tests/test_approve.py`, `tools/README.md`
**Applied fix:** `promote` now refuses an approval record when any of these is true:
- the approver is empty or an AI name;
- `approved_at` is not in the format approve writes;
- the rules version or sha256 differs from the repository rules;
- the recorded counts differ from a fresh re-scan;
- the record copy is missing.

The approval also now covers `review.md` and `bundle.json` (WR-02). `.claude/settings.json` was **not** changed, and no hooks were added. See Residual risk.

### WR-02: Approve did not tie files to the bundle, and review.md was not hashed
**Status:** fixed · **Commit:** d3d48d9
**Applied fix:**
- A complete bundle now writes `bundle.json["outputs"]`. It holds sha256 values for the sources, spec, check, caption, compliance, MP4, cover, scene sheet and review.md.
- `approve` refuses any file that changed after the bundle.
- The approval now hashes 10 files, including `review.md` and `bundle.json`.

Tests: `test_hand_edit_after_bundle_refuses`, `test_bundle_json_without_output_hashes_refuses`, and an `outputs` assertion in `test_bundle`.

**Note for the user:** the existing draft `2026/reels/drafts/2026-11-08-pension-credit-limit/` was bundled before this change, so its `bundle.json` has no `outputs`. Approve will ask for a re-bundle. The folder itself was not touched.

### WR-03: Approve accepted bundles that failed the upload spec (exit 4)
**Status:** fixed · **Commit:** 897d6ee
**Applied fix:**
- `approve` refuses exit code 4 and any code other than 0 or 3.
- `promote` re-reads `bundle.json` and re-checks status, exit code and output hashes.

### WR-04: The promote target was not tied to the repository's `<year>/reels`
**Status:** fixed · **Commit:** c85a8aa
**Applied fix:**
- New `publish_dir()`. The resolved draft must sit in `REPO_ROOT/<게시일 연도>/reels/drafts`. Both approve and promote check this, so a symlinked `drafts/` is caught too.
- Tests now patch `constants.REPO_ROOT` to a temp root.

### WR-05: The ReDoS guard was easy to get around, and examples were optional
**Status:** fixed · **Commit:** 4a25deb
**Applied fix:** The loader walks `re._parser`'s parse tree. It rejects a nested repeat when either repeat is unbounded, and an alternation inside an unbounded repeat. Each regex is also timed on long probe strings, with a budget of 0.1 s. Pattern rules must now have non-empty `hit` and `miss` examples.

### WR-06: The compact pass was skipped for fields with an unrelated finding
**Status:** fixed · **Commit:** c02e4b2
**Applied fix:** The compact pass now runs on every field. A compact hit is dropped only when it overlaps a pattern match at the same place, whether that match was found or suppressed. Negated compact terms are suppressed.

### WR-07: G-04 needed 반드시 right before the verb
**Status:** fixed: requires human verification · **Commit:** cf1b382
**Applied fix:**
- G-04 now allows up to 14 characters on the same line between 반드시 and the verb, with a broader set of result verbs (모입/쌓입/…).
- Imperative and obligation endings are excluded, and G-07's advice except is reused.

### WR-08: The implicit tier was 0/5
**Status:** fixed: requires human verification · **Commit:** 05806d9
**Applied fix:** New patterns at **확인 필요** only, so they cannot block promote:
- C-02: one-sided comparison with (단점|장점)만.
- G-08: "하나면 끝", "따 놓은 당상", "보장된 거나 마찬가지".

The implicit-tier limitation statement is kept.

### WR-09: An environment-dependent slot test failed when a draft folder existed
**Status:** fixed · **Commit:** 30cc592
**Applied fix:** `RealDirSlot` and the real-folder slot tests now use a temp `<tmp>/2026/reels` that mirrors only the published MP4 and spec names. They never read `drafts/`. The user's draft folder was not touched, and the suite passes with it present.

### IN-01: The statute guard missed "22조" and Article N
**Status:** fixed · **Commit:** ba81ff5
**Applied fix:**
- The guard now matches `(?:제\s*)?\d+\s*조(?:의\d+)?` and `Article \d+`. Money such as "1조 원" and "3조건" is excluded.
- A shared `compliance.forbidden_text` is also applied to `caption_config.json` at load.

### IN-02: Purge deleted approval.json last
**Status:** fixed · **Commit:** fba978a
**Applied fix:** bundle now deletes `approval.json` right after validating the folder, before the argument checks. It is also first in `PURGE_FIXED`.

### IN-03: Promote mishandled stale `.part` files and interrupts
**Status:** fixed · **Commit:** 8252608
**Applied fix:**
- A stale `.part` is refused up front with its own message and is never deleted.
- Rollback removes only the temp files this run created.
- `BaseException` (for example Ctrl-C) rolls back what was made so far and is re-raised.

### IN-05: review.md upload-spec line hid WARN items
**Status:** fixed · **Commit:** be1d529
**Applied fix:** The line now reads "(실패 n, 경고 n)", built by `review.upload_spec_line`.

### IN-06: basis_required location was wrong when the match spanned scenes
**Status:** fixed · **Commit:** 6e5ae12
**Applied fix:** The field is now found from the body offsets used to build the body, not from `doc.text.find`.

### IN-07: A failed `stamp_created` left a folder that could not be re-created
**Status:** fixed · **Commit:** 2687522
**Applied fix:** On OSError, `create_draft_dir` removes the new folder if it is still empty, then raises `SlotError`.

### IN-08: Unused aliases in approve.py
**Status:** fixed · **Commit:** fb22df4
**Applied fix:** Removed `PROMOTED` and `_names`, leaving one constant set (`HASHED`).

Docs commit: 25b2650. It covers the README text for rules v0.2: negation scope, the compact-term format, and the loader guards.

## Skipped Issues

### IN-04: The approval audit trail is not kept with the published reel
**File:** `tools/reelkit/approve.py:236-262`
**Reason:** This is more than a few lines, and it is a product decision rather than a code fix. Linking `approval.json` and `record.json` into `2026/reels/approvals/` would commit the approver's name and the ad-review fields to the public repository. That touches the personal-information constraint and changes the published layout, so it needs the user's call.
**Original issue:** approval.json, review.md and record.json stay only in the gitignored drafts folder.

## Residual risk (awaiting the user's decision)

- **WR-01 / D-15.** Approval is still not technically human-only. Three gaps remain:
  - A pty wrapper (`script -qc …`) can satisfy the `isatty` check.
  - Any process can write an `approval.json` with consistent hashes, counts and rules sha.
  - `.claude/settings.json` has no `permissions.deny`.

  The proposed deny entries are for `Bash(python3 tools/draft.py approve:*)`, `Bash(script:*)`, `Write/Edit(**/approval.json)` and `Write(**/record.json)`. They were **not** added, as instructed. A forged approval still only stages files and never commits them, so `git diff` and `review.md` stay the human check.
- There is no 수정 필요 waiver (CR-02). Any remaining false positive blocks promote until the wording changes.
- **Negation split over two lines.** The window never crosses a line. A negation written on the next line, such as "원금 보장 상품은" / "어디에도 없어요", is flagged. The exceptions are a quotative or "…다는 보장은" at the end of the line. The README tells writers to keep the negation on the same line.
- **Bundle flags still accepted.** `bundle` still takes `--rules`, `--registry` and `--config`. Approve rejects a bundle made with other rules. Overrides of the registry and the caption config are only forbidden in SKILL.md.

## Red-team report: before vs after (`python3 tools/draft.py redteam`)

| Line | Before (v0.1) | After (v0.2) |
|---|---|---|
| 기존 10편 | 수정 필요 0건 · 확인 필요 2건 | 수정 필요 0건 · 확인 필요 2건 |
| 표본 내 부적절 (seed) | 41/41 (explicit 36/36 · obfuscated 2/2 · implicit 3/3) | 50/50 (explicit 44/44 · obfuscated 3/3 · implicit 3/3) |
| 표본 내 적절 (seed) | 오탐 0/21 (수정 필요 0) | 오탐 0/31 (수정 필요 0) |
| 따로 쓴 문장 부적절 — 규칙 조정에 쓰지 않음 | 14/22 (64%) · explicit 12/14 · obfuscated 2/3 · implicit 0/5 | 17/22 (77%) · explicit 13/14 · obfuscated 3/3 · implicit 1/5 |
| 따로 쓴 문장 적절 | 오탐 1/10 (수정 필요 1: H-G01) | 오탐 0/10 (수정 필요 0) |
| 예외 처리로 제외 | 10건 | 17건 |
| 가장 느린 규칙 | G-05 0.23ms | C-02 0.32ms |

Before:
`redteam: 표본 내 탐지 41/41 · 오탐 0/21 · 따로 쓴 문장 탐지 14/22 · 오탐 1/10 · 기존 10편 수정 필요 0건`

After:
`redteam: 표본 내 탐지 50/50 · 오탐 0/31 · 따로 쓴 문장 탐지 17/22 · 오탐 0/10 · 기존 10편 수정 필요 0건`

How to read these numbers:
- **Seed corpus.** It grew by 9 bad and 10 good regression entries written for these findings, so its numbers are not comparable with v0.1 and are inflated by construction.
- **Held-out file.** It was not used to tune rules and was not edited. The general fixes still moved its numbers, in both directions:
  - **Up:** H-B01 (G-05 particle), H-B04 (G-04 object between 반드시 and the verb), H-B05 (T-01 conjugation and intensifier) and H-B07 (compact tax category) are now detected. H-G01 is no longer a false positive.
  - **Down:** H-B11 dropped from 비교·비방/수정 필요 to C-05 확인 필요, because bare 사기/바가지 was removed (CR-02). Held-out 비교·비방 went from 2/3 to 1/3.
  - **New 확인 필요 only (mismatch, not detected):** H-B06, H-B10 and H-B13 now get 확인 필요 findings (G-08, C-02) where they had none.
  - **Still missed:** H-B21.
- The published 10 still have 수정 필요 0건.

## Final verification (run once, main checkout)

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'`: **Ran 570 tests, OK** (exit 0). This was run with the user's `2026/reels/drafts/2026-11-08-pension-credit-limit/` present.
- `python3 tools/golden.py`: **golden: PASS 10/10 (재현 불가 1)** (exit 0)
- `python3 tools/draft.py redteam`: exit 0, last line as above.
- `git status` was clean afterwards. `approve` was never run on a real folder, and no figure was set to 확인.

---

_Fixed: 2026-10-29_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
