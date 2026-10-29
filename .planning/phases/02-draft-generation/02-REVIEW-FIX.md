---
phase: 02-draft-generation
fixed_at: 2026-10-29T00:00:00Z
review_path: .planning/phases/02-draft-generation/02-REVIEW.md
iteration: 1
findings_in_scope: 18
fixed: 14
skipped: 4
status: partial
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-10-29
**Source review:** .planning/phases/02-draft-generation/02-REVIEW.md
**Iteration:** 1 (single pass, no re-review loop)

**Summary:**
- Findings in review: 18 (5 critical, 8 warning, 5 info)
- Fixed: 14 (CR-01..CR-05, WR-01..WR-07, IN-01, IN-05)
- Skipped: 4. WR-08 is a human-confirmation item. IN-02, IN-03 and IN-04 were left out by instruction.
- Every fix has a regression test that reproduces the review's bypass and checks that it now fails.

**Verification (where it ran):** All checks ran in the **main checkout** `/home/user/kiwoom-cards`, not in an isolated worktree. The orchestrator's root-pin guard requires `git rev-parse --show-toplevel` to equal the pinned root, and a worktree would fail that check. The numbers below can be reproduced from this tree.
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` ran **402 tests, OK**. The baseline before the fixes was 344 tests, OK.
- `python3 tools/golden.py` gave **golden: PASS 10/10 (재현 불가 1)**.
- Published reels and specs (`2026/reels/*.mp4`, `2026/reels/specs/*.json`), the card specs (`2026/NN-*/spec.json`), `tools/data/figures.json` and `.claude/settings.json` are unchanged (`git diff 1708d48 HEAD -- 2026/ tools/data/ .claude/settings.json` is empty). No figure was set to 확인.

Logic changes are marked "fixed: requires human verification". Syntax checks and tests cannot prove that the rule set is complete.

## Fixed Issues

### CR-01: check trusts the spec's own ledger

**Status:** fixed: requires human verification
**Files modified:** `tools/reelkit/check.py`, `tools/reelkit/expand.py`, `tools/reelkit/spec.py`, `tools/draft.py`, `tools/tests/test_check.py`, `tools/tests/test_expand.py`, `.claude/skills/make-reel/SKILL.md`, `tools/README.md`
**Commit:** 38142d6
**Applied fix:**
- `expand` now writes the source's `derive` into `spec.json`. `build_values`, `render_ref` and `basis_items` are shared with `check`.
- `check` recomputes every ledger entry from `ref` + `fmt`, using the current registry and the spec's own `inputs`/`derive`. It reports:
  - `LEDGER_FORGED`: no ref/fmt, for example the `sources: []` forgery
  - `STALE_FIGURE`: the text no longer matches what the registry and inputs produce, for example 16.5만 → 99.9만, or a registry value change
  - `LEDGER_MISMATCH`: value, sources or exact was edited; this also covers 700000 → 698000, which still prints "70만 원"
  - `LEDGER_REF`, `UNKNOWN_FIG`, `UNIT_FORMAT`
- Spans that cannot be verified stay unmasked, so `UNREGISTERED` fires as well.
- Status rules (확인 필요, 발의, 폐지, EXPIRED) use the recomputed sources, not the stored ones.
- `basis_items` is rebuilt and compared (`BASIS_ITEMS`).
- `check` also re-expands the sibling `<name>.src.json`, or `--src`, and fails on any difference (`SOURCE_MISMATCH`). `check.json` records the `source` path.
- Existing test changed: `test_unknown_registry_id_in_ledger` now tampers with `ref`. Tampering with `sources` is a new test that expects `LEDGER_MISMATCH`.

### CR-02: `inputs.*` side door

**Status:** fixed: requires human verification
**Files modified:** `tools/reelkit/expand.py`, `tools/reelkit/check.py`, `tools/draft.py`, `tools/tests/test_check.py`, `.claude/skills/make-reel/SKILL.md`, `.claude/skills/make-reel/references/source-format.md`
**Commit:** 9920d3c
**Applied fix:**
- `expand` rejects any input with `unit: "%"`. It also rejects any `%` value with no `fig.` leaf, which blocks building a rate from two inputs with `yield_pct`.
- `check` lists every field that uses an `inputs.*` leaf, directly or through derive, in `check.json` `assumptions` (`where`, `text`, `inputs`, `labels`). It also prints `가정 수치: …` on stdout.
- A line that uses an input must show 예시/가정/가상 on the same line or in `basis`; otherwise `ASSUMPTION_UNMARKED` is an error.
- The summary now ends with `· 가정 수치 N줄`. The expected summary in `test_summary_never_says_tonggwa` was updated: the clean tax fixture has 7 lines that use inputs, which is correct.

### CR-03: format/unit mismatch and literal unit suffixes

**Status:** fixed: requires human verification
**Files modified:** `tools/reelkit/calc.py`, `tools/reelkit/expand.py`, `tools/reelkit/check.py`, `tools/tests/test_expand.py`, `tools/tests/test_check.py`, `.claude/skills/make-reel/references/source-format.md`
**Commit:** e0c948a
**Applied fix:**
- `calc.result_unit` gives every derive result a unit and rejects bad argument units. For example, `pct_of`/`after_tax`/`with_local` need `%` rates, add/sub need the same unit, and the instalment functions need (원, %, 개월). The rules keep all published derivations expressible:
  - 세−세 = 년
  - 원×개월 = 원
  - %×년 = %
  - 원÷개월 = 원
  - 72÷% = 년
  - 개월÷개월 = unitless, shown with `dal`
- `calc.FORMAT_UNITS` lets each format accept only matching units: `num` only unitless values, money formats only 원, pct formats only %.
- `expand` rejects a placeholder followed by a literal unit, such as `{{x|num}}만 원` or `{{x|man}}원`, even across `</g>`.
- `check` re-validates fmt/unit through the CR-01 recompute (`UNIT_FORMAT`) and flags a literal unit glued after a ledger span (`UNIT_AFTER`).

### CR-04: numscan misses Hangul number words, N 대비 and projected years

**Status:** fixed: requires human verification
**Files modified:** `tools/reelkit/numscan.py`, `tools/tests/test_numscan.py`, `tools/tests/test_check.py`, `tools/tests/test_caption.py`
**Commit:** 9fdf02c
**Applied fix:**
- Hangul amounts get exact values: 천만 원, 백만 원, 3천만 원, 일억 오천만 원, 만 원, 천만 관객.
- Vague amounts are still figures, with `value=None`: 수억 원, 몇 배.
- 두/세/네… 배 and 절반/반값/반토막 are `times` figures.
- 4-digit years beyond next year, or followed by 고갈/전망/예상/적자/…, are `year` figures instead of dates.
- `대비/대출/대금` no longer count as the counter 대, so 300 대비 is now a bare 300.
- False positives are excluded: 만 65세, 이만 가자, 천천히, 천만에요, 세배, 단위 만 원.
- Bare numbers were already figures (`bare`).
- **Published corpus:** comparing the old and new scanners over all 10 reel specs and 7 card specs gave **0 token differences**, so no expected count changed. A new test pins the per-spec counts.

### CR-05: the 확인 state is protected only by an AI-name regex

**Status:** fixed (CLI side only, as instructed)
**Files modified:** `tools/draft.py`, `tools/reelkit/figures.py`, `tools/reelkit/check.py`, `tools/tests/test_figures.py`, `tools/tests/test_check.py`, `tools/README.md`
**Commit:** 32e776d
**Applied fix:**
- `figures confirm` refuses unless stdin is an interactive TTY. Claude Code's Bash and piped input are refused.
- It then shows the value and source and requires the figure id to be retyped.
- `figures.confirmation_problems()` finds 확인 entries with no checker or date, an invalid date, a future date, a date before `found_on`, or an AI name.
- `check` reports each one as `REGISTRY_CONFIRM` (exit 1). `figures list` prints them and exits 1.
- A 확인 entry missing `checked_on`/`checked_by` already fails to load, which gives `등록부 오류` and exit 1.
- The docs no longer present the name filter as enforcement.
- `.claude/settings.json` and hooks were not touched.

### WR-01: caption repeats 미확인/발의 numbers without marks

**Status:** fixed: requires human verification
**Files modified:** `tools/reelkit/caption.py`, `tools/draft.py`, `tools/tests/test_caption.py`, `.claude/skills/make-reel/SKILL.md`, `.claude/skills/make-reel/references/source-format.md`, `tools/README.md`
**Commit:** 886591e
**Applied fix:**
- Caption numbers must match ledger entries only.
- A line that uses a 미확인 figure gets `확인 필요: summary[n] [ids] "…"`.
- A 발의 figure without 발의안/개정안/정부안 on the caption line is a `CaptionError`.
- An inputs number without 예시/가정/가상, on the caption line or in the spec's basis, is a `CaptionError`.
- `draft.py caption` loads the registry (`--registry`) and refuses a spec whose `check` has errors.
- The fixture caption now produces three `확인 필요` warnings, and `test_layout` was updated to expect them.

### WR-02: caption asserts one 기준일 for all figures

**Status:** fixed: requires human verification
**Files modified:** `tools/reelkit/caption.py`, `tools/tests/test_caption.py`
**Commit:** e1b7eac
**Applied fix:** The `(YYYY년 M월 기준)` phrase is added only when every used figure has the same non-null `as_of`. It is skipped when `basis` already contains 기준.

### WR-03: `check --legacy` accepts a v2 draft

**Status:** fixed
**Files modified:** `tools/draft.py`, `tools/tests/test_check.py`
**Commit:** 8a89f55
**Applied fix:** `--legacy` exits 1 when the spec has any v2 field: version, series, inputs, derive, figures or basis_items. Removing only `version` is therefore not enough to get through. Published v1 specs (basis + scenes) are unaffected.

### WR-04: `figures confirm` accepts any 확인일

**Status:** fixed
**Files modified:** `tools/reelkit/figures.py`, `tools/tests/test_figures.py`
**Commit:** 37088c2
**Applied fix:** `confirm_figure` requires `found_on <= 확인일 <= today`; `today` can be injected for tests. `validate_entry` rejects `checked_on < found_on`. The CLI test now confirms with today's date and checks that `--date 2099-01-01` is refused.

### WR-05: `slot` accepts past dates and dates outside the 2026 tree

**Status:** fixed: requires human verification
**Files modified:** `tools/reelkit/slot.py`, `tools/tests/test_slot.py`, `.claude/skills/make-reel/SKILL.md`
**Commit:** d65d6ee
**Applied fix:**
- A date before today, or before `proposed_date`, adds a `notices` entry and sets `ask: true`.
- Inside a year folder (`2026/reels`), a date from another year is a conflict, so `--create` refuses it. `slot --date 2020-01-01 --slug old-date --create` now exits 1.

### WR-06: wrong hashtag count with no hashtags

**Status:** fixed
**Files modified:** `tools/draft.py`, `tools/tests/test_caption.py`
**Commit:** 7691065
**Applied fix:** The printed count is now brand tags plus topic tags, instead of the number of words on the last line. With `hashtags: []` it prints `해시태그 0개`.

### WR-07: caption config `status` never surfaced

**Status:** fixed
**Files modified:** `tools/reelkit/caption.py`, `tools/tests/test_caption.py`
**Commit:** 47d693c
**Applied fix:** `면책·CTA 문구 상태: <status>` is added to the warnings, which `draft.py caption` prints to stderr. It is never written to caption.txt.

### IN-01: house-style caption order disagrees with the code

**Status:** fixed
**Files modified:** `.claude/skills/make-reel/references/house-style.md`, `tools/README.md`
**Commit:** ebf4c09
**Applied fix:** The documented order is now 첫 줄, 요약 3줄, 근거·기준, 면책, CTA, 다음 편, 해시태그, matching the code.

### IN-05: `_read_json` error text says 원고 소스 for the caption source

**Status:** fixed
**Files modified:** `tools/draft.py`, `tools/tests/test_caption.py`
**Commit:** 2bb74ed (the label parameter itself landed in 38142d6)
**Applied fix:** A bad caption source now reports `게시글 문구 원본 파일을 열 수 없음`.

## Skipped Issues

### WR-08: `nps_avg_old_age_all` value is the published reel's rounded figure

**File:** `tools/data/figures.json` (entry `nps_avg_old_age_all`)
**Reason:** By instruction, this is a human-confirmation item, so the value (700000) is left as is. The entry's `notes` already state the conflict: "2차 자료 69.6~69.8만 원(소수 충돌). 기존 편은 70만 원 표기 — 공단 통계로 정확값 확인 필요". The entry stays 미확인, so every line using it shows up as `확인 필요`. With CR-01, correcting the value later makes any existing spec.json fail check (`LEDGER_MISMATCH`/`STALE_FIGURE`) until it is re-expanded.
**Original issue:** The registry stores a rounded number as if it were the source value.

### IN-02: atomic writes leave mode 0600

**File:** `tools/reelkit/figures.py:240-245`, `tools/reelkit/expand.py:290-295`
**Reason:** Skipped by instruction (only IN-01 and IN-05 were requested).
**Original issue:** `mkstemp` + `os.replace` changes the file mode from 644 to 600.

### IN-03: series teaser handling is narrow

**File:** `tools/reelkit/expand.py:156-161, 193-211`
**Reason:** Skipped by instruction.
**Original issue:** Duplicate detection only matches lines tagged `<s>다음 편:`. The teaser is appended even when there is no CTA line. `series.next` cannot hold figures.

### IN-04: `convert._series` drops episodes above 10

**File:** `tools/reelkit/convert.py:73-79`
**Reason:** Skipped by instruction.
**Original issue:** For "… 11편", the name loses its number and no warning is given.

## Residual Risk

- **CR-05 (confirmation): the TTY check slows a non-human confirm down but does not prevent it.**
  - Wrapping the command in a pseudo-terminal, for example `script -qc "python3 tools/draft.py figures confirm …"` with piped input, gets past it.
  - Editing `tools/data/figures.json` directly to `확인` with a plausible human name and a past date (≥ found_on) passes `validate_entry`, `confirmation_problems`, `check` and `figures list`. Only malformed confirmations are caught: missing checker or date, future date, date before found_on, AI name.
  - The remaining controls are the skill rule (Claude must not confirm), git diff review of `figures.json`, and an optional project PreToolUse hook. The hook would deny `Bash` commands matching `draft.py figures confirm` and `Edit|Write` on `tools/data/figures.json`. It was **not** added because a settings/hook change needs the user's approval.
- **CR-01 when no `spec.src.json` is available:**
  - `check` recomputes from the spec's own `inputs`/`derive`. Any number on screen still traces to a registry id or a listed assumption.
  - A hand edit to `derive` itself (a different function) or to wording without numbers is not detected unless the source is present. The skill always writes `spec.src.json` next to `spec.json`, so the normal path is covered.
- **CR-02:** one 예시/가정/가상 in `basis` covers every inputs line of the reel, as instructed ("same line or basis"). A `%` value that mixes a registry rate with an input amount, such as a computed example yield, is allowed because it has a `fig.` leaf.
- **CR-03:** the unit and format rules are a closed list.
  - `dal` accepts unitless ratios so the published "2.2달" can still be reproduced.
  - `num` followed by 배/명 is allowed, for unitless multipliers and counts.
  - Literal-unit detection covers 만/억/천/백/십/원/%/퍼센트/프로/세/년/개월/달 only.
- **CR-04:** the scanner is a regex lexicon.
  - Known misses: Hangul numerals glued to a preceding Hangul word (총천만 원), Hangul amounts followed by a particle without 원 (천만이), other ways of writing a multiple.
  - "1억 2천만 원" splits into two tokens. Both are flagged, but a caption number written that way will not match the ledger.
  - Whether a year counts as a figure depends on today's date and a fixed list of context words.
- **WR-05:** a 2027 posting date now needs `--reels-dir 2027/reels`. This is deliberate, but in that folder, conflict detection cannot see the 2026 posts.
- **Commit trailer:** the commits use `Co-Authored-By: Claude Opus 5.5`, which is the model that actually made them, as the session attribution guidance specifies. The requested `Claude Sonnet 5.5` was not used.

---

_Fixed: 2026-10-29_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
