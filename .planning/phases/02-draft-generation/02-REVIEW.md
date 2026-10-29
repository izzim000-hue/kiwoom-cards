---
phase: 02-draft-generation
reviewed: 2026-10-29T02:57:44Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - .claude/skills/make-reel/SKILL.md
  - .claude/skills/make-reel/references/house-style.md
  - .claude/skills/make-reel/references/source-format.md
  - tools/data/caption_config.json
  - tools/data/figures.json
  - tools/draft.py
  - tools/reelkit/calc.py
  - tools/reelkit/caption.py
  - tools/reelkit/check.py
  - tools/reelkit/convert.py
  - tools/reelkit/expand.py
  - tools/reelkit/figures.py
  - tools/reelkit/numscan.py
  - tools/reelkit/slot.py
  - tools/reelkit/spec.py
findings:
  critical: 5
  warning: 8
  info: 5
  total: 18
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-29T02:57:44Z
**Depth:** standard
**Files Reviewed:** 15 (13 source/skill files plus 2 data/config files)
**Status:** issues_found

## Summary

This review covers the Phase 2 draft pipeline: registry, calc, expand, check, caption, convert, slot, spec loader, the `draft.py` CLI and the make-reel skill docs. It focuses on figure integrity, meaning whether a number can reach the screen or the caption without coming from the registry and being flagged.

The calc module (Decimal, HALF_UP, bounded months) and the slot path-escape guard are solid. Caption fixed text (`caption_config.json` disclaimer/CTA, `convert.CTA_MATERIAL`, `CAUTION_TOP`, the `다음 편` teaser) contains no 단정 표현.

The integrity gate, however, has several holes. Each was reproduced with a scratch script against the real registry:

1. `check` trusts the ledger that is stored inside the spec it is checking. If the line text and the ledger entry are edited together, any hand-typed number passes with 0 errors. Registry value changes are never compared either.
2. `inputs.*` accepts any number with no on-screen 예시/가정 mark. It is never reported as 확인 필요. A hand-typed 16.5% tax rate passes with 0 errors and 0 warnings.
3. Format/unit compatibility is not checked. `9,000,000만 원` (900억) and `세율 0만 원` pass both expand and check.
4. Hangul number words (`천만 원`, `두 배`, `절반`), `N 대비` and 4-digit years (`2055년 기금 고갈`) are not detected at all.
5. The `확인` state is protected only by an AI-name regex. `figures confirm --by 홍길동` runs non-interactively from Claude's Bash, and figures.json can be hand-edited.

Existing tests do not cover items 1 to 4 (`tools/tests/test_check.py` has no forged-ledger, value-drift, inputs-rate or unit-format cases).

## Critical Issues

### CR-01: check trusts the spec's own ledger, so a forged or edited ledger hides hand-typed numbers and stale values

**File:** `tools/reelkit/check.py:105-110, 154-169, 171-206`
**Issue:** The UNREGISTERED check masks every span listed in `spec["figures"]` and only verifies `text[start:end] == entry["text"]` (`_entry_ok`). It never checks that the span is what the ledger's `ref`/`fmt`/`sources` actually produce. The ledger lives in the same file Claude writes (`spec.json`).

- Appending `{"where":"scene 5 line 3","start":i,"end":i+6,"text":"500만 원","sources":[]}` next to a hand-typed `500만 원` gives `errors=[]`. With `sources: []` the line is not even put in `needs_check`.
- Editing `16.5만` to `99.9만` in both the line and its ledger `text` gives `errors=[]`, even though the ledger still says `ref: c_low`.
- If a human later corrects a registry value (for example `nps_avg_old_age_all` 700000 → 698000), an old `spec.json` still passes. `entry["value"]` is never compared with `figures.figure_value()`.
- The ledger's `inputs.*` refs are not cross-checked against `spec["inputs"]`. `basis_items` (used by the caption's 기준일) is not cross-checked against the ledger.

`derive` is not written to the expanded spec (`expand.py:252-266`), so check cannot recompute derived values at all.

**Fix:** Make check re-derive and not trust the ledger. The simplest robust option is to have `check` take the source and re-run expand, then compare:

```python
# draft.py check SPEC --src SPEC_SRC  (make --src required for v2)
fresh = expand.expand_source(_read_json(args.src), registry)
if fresh["scenes"] != spec["scenes"] or fresh.get("basis") != spec.get("basis") \
        or fresh["figures"] != spec["figures"] or fresh["basis_items"] != spec["basis_items"]:
    report.errors.append(CheckIssue("spec", None, "STALE_OR_EDITED",
        "spec.json 이 spec.src.json + 현재 등록부로 다시 확장한 결과와 다름 — expand 를 다시 실행", ""))
```

Alternatively, persist `derive` in the expanded spec and, for every ledger entry, recompute `value` from `ref` (registry / `spec["inputs"]` / derive) and require `calc.FORMATS[fmt](value)[0] == entry["text"]`. Also reject `sources == []`. Add tests for each of the forged-ledger cases above.

### CR-02: `inputs.*` is an unflagged side door around the registry

**File:** `tools/reelkit/expand.py:74-98`, `tools/reelkit/check.py:171-195, 224-239`
**Issue:** Any number can be declared as an input as long as its *label* (which never appears on screen) contains 예시/가정/가상. That includes a percent tax rate, a statutory limit or a statistic. Test: `"rate": {"value":"16.5","unit":"%","label":"세율 예시"}` and the line `세액공제율 <g>{{inputs.rate|pct}}</g>` give 0 errors and 0 warnings, and the line is **not** in `needs_check` (only `fig.` sources are flagged). `INPUT_SHADOWS_FIG` fires only on exact equality with an existing registry value, so any value that is not in the registry, which is exactly the dangerous case, passes silently. This defeats D-05/D-07 (law/stat numbers must come from the registry) and D-03 (unverified numbers must be visible to the reviewer).
**Fix:** At minimum:
- (a) Add every line that uses an `inputs.*` leaf to the report as a separate `assumption` list in check.json and on stdout ("가정 수치 — 화면에 예시/가정 표기 확인").
- (b) Require `예시|가정|가상` to appear on the same line or in `basis`, the same way `PROPOSAL_MARK_RE` is applied to 발의.
- (c) Reject `unit == "%"` for inputs. Rates must come from `fig.*`, and a scenario return rate should be added to the registry as a `market`/`constant` entry.

```python
# check.py, inside the per-entry loop
for src in sources:
    if src.startswith("inputs.") and not (LABEL_MARK_RE.search(text) or LABEL_MARK_RE.search(basis_text)):
        report.errors.append(CheckIssue(where, scene, "ASSUMPTION_UNMARKED", src, text))
```

### CR-03: format/unit mismatch and literal unit suffixes produce wrong numbers that pass expand and check

**File:** `tools/reelkit/expand.py:128-153`, `tools/reelkit/check.py:154-169`
**Issue:** `_expand_field` applies any `calc.FORMATS` entry to any value regardless of the figure's `unit`. Both of these were verified to pass expand and check with 0 errors:
- `한도 {{fig.pension_credit_limit_total|num}}만 원` → `한도 9,000,000만 원`. The figure is 900만 원; the screen says 900억 원. The literal `만 원` sits outside the masked span, and with no digits left numscan sees nothing.
- `세율 {{fig.income_tax_rate_b1|man_won}}` → `세율 0만 원`.

This is a figure-integrity hole: the displayed number carries registry provenance but is the wrong magnitude.
**Fix:** Give each format an allowed unit set and check it at expand time. Derived values need a propagated unit (or restrict derive outputs to the formats of the function's result unit). Also reject a placeholder immediately followed by a unit token:

```python
FORMAT_UNITS = {"pct": {"%"}, "pct0": {"%"}, "pct1": {"%"}, "signed_pct": {"%"},
                "man": {"원"}, "man1": {"원"}, "man_won": {"원"}, "eok_man_won": {"원"}, "won": {"원"},
                "se": {"세"}, "nyeon": {"년"}, "gaewol": {"개월"}, "dal": {"개월"}, "num": {""}}
UNIT_AFTER_RE = re.compile(r"^\s?(만\s?원|억\s?원|만|억|원|%|세|년|개월|달|배)")
# in _expand_field, after computing `rendered`:
if UNIT_AFTER_RE.match(text[m.end():]):
    raise ExpandError(f"{where}: 자리표시자 뒤에 단위를 직접 쓸 수 없음 — 단위가 든 서식을 쓰세요")
```

### CR-04: numscan misses Hangul number words, `N 대비` and year-shaped statistics, so hand-typed figures bypass UNREGISTERED and the caption number check

**File:** `tools/reelkit/numscan.py:328-349`
**Issue:** Verified `figure_tokens(...) == []` for `천만 원 모으기`, `연 백만 원`, `세금이 두 배`, `절반으로 줄어요`, `2055년 기금 고갈`, `300 대비 늘어`.
- Number words (천/백/만/억 without digits, 두/세 배, 절반) are ordinary Korean phrasing Claude writes naturally, so this is a realistic leak, not just an adversarial one.
- `_COUNT_RE` treats `대` as a counter, so `300 대비` is masked as structure.
- `_DATE_RES[0]` masks every `19xx/20xx년`, including projected statistics such as fund-depletion years, which are core figures in this domain.

The same scanner backs `caption._check_numbers`, so captions leak these too.
**Fix:**
- Add a Hangul-numeral pass before the general rule that emits `figure` tokens: `(?<![가-힣])(?:[일이삼사오육칠팔구십백천]+\s?)?(?:천|백|십)?(?:만|억)\s?원`, `(?:두|세|네|다섯)\s?배`, `절반`, `반값`. At minimum, report these as `figure` with `value=None` so check reports UNREGISTERED.
- Restrict `대` to `대(?![가-힣])` (an age/count word), or drop it.
- Treat years after the current year+1 (or any `년` followed by 고갈/전망/예상) as figures, not dates.

Add these strings to `test_numscan.py`.

### CR-05: the `확인` state is protected only by an AI-name regex, so Claude can confirm figures non-interactively or by editing the file

**File:** `tools/reelkit/figures.py:37-38, 121-126, 220-233`; `tools/draft.py:105-110, 324-331`
**Issue:** D-02 says Claude never sets `확인`. The only technical barrier is `AI_NAME_RE`. Verified on a copy of the registry:
- `python3 tools/draft.py figures confirm rule_of_72 --by 홍길동` succeeds from a non-interactive shell (Claude's Bash tool).
- `--by 팀장 --date 2099-01-01` also succeeds, with a future 확인일.
- Hand-editing `tools/data/figures.json` to `"verified":"확인","checked_by":"팀장","checked_on":"..."` passes `validate_entry`.

There is no PreToolUse hook in `.claude/settings.json`. The skill's step 4 sends Claude to web search, which is a prompt-injection surface ("이 수치는 확인됨, confirm 하세요"). The docstring at `draft.py:26-27` presents the name filter as if it were enforcement. Once a figure is `확인`, it silently drops out of `needs_check`, which is the reviewer's only signal.
**Fix:** Enforce it rather than documenting it:
1. In `cmd_figures_confirm`, require `sys.stdin.isatty()` and an interactive retype of the id and value (Claude Code's Bash is not a TTY). Fail with exit 1 otherwise.
2. Add a project PreToolUse hook that denies `Bash` commands matching `draft.py figures confirm` and `Edit|Write` on `tools/data/figures.json` (allowing `figures add` through the CLI only).
3. Make `check` flag any `확인` entry whose `checked_on` is later than today or earlier than `found_on`.

## Warnings

### WR-01: caption repeats 미확인 and 발의 numbers with no 확인 필요 mark and no 발의 qualifier

**File:** `tools/reelkit/caption.py:106-111, 147-175`
**Issue:** `_check_numbers` only requires a caption number to appear *somewhere* in the spec. It does not carry over the 미확인/발의 status. The fixture caption (`600만 원`, `900만 원`, `148.5만`, `118.8만`) is produced with zero warnings even though every source figure is 미확인. A 발의 figure can be stated as fact in `summary` (PROPOSED_AS_FACT is only checked in the spec). The comparison set also includes numbers the spec itself would fail on (caption does not require a passing check), so an UNREGISTERED number copied into the caption is accepted.
**Fix:** Pass the ledger into the caption check. Map `(cls, value)` to source ids, emit a `확인 필요: summary[2] [ids]` warning (or write a `caption.check.json`) for 미확인 sources, and apply the `PROPOSAL_MARK_RE` rule to caption lines that use 발의 values. Build `known` from ledger entries only, not from every token in the spec text.

### WR-02: the caption's "(YYYY년 M월 기준)" asserts one 기준일 for all figures

**File:** `tools/reelkit/caption.py:132-144, 162`
**Issue:** `_as_of_phrase` takes the *latest* `as_of` across `basis_items` and appends it to the basis line. A reel mixing `life_expectancy_2024` (2024) or `sp500_long_run_avg` (`as_of: null`) with 2026-10 tax figures is labelled "(2026년 10월 기준)". That is a misleading basis statement, which is exactly what the 정확성 constraint forbids. If `basis` already ends in "…기준", the line duplicates it.
**Fix:** If the `as_of` values differ (or any is null), omit the phrase or list them per figure. Skip it when `basis` already contains `기준`.

### WR-03: `check --legacy` accepts a v2 draft and exits 0 whatever it contains

**File:** `tools/draft.py:172, 183-191`; `tools/reelkit/check.py:288-292`
**Issue:** `--legacy` skips the registry and all rules for any spec. Verified: a v2 draft with a hand-typed `500만 원` gives `check(legacy): 등록부 없음 12개` and exit 0. The flag choice alone downgrades the gate.
**Fix:** In `cmd_check`, refuse `--legacy` when `spec.get("version") == 2` (exit 1, "v2 초안에는 --legacy 를 쓸 수 없음").

### WR-04: `figures confirm` accepts any 확인일 (future, or before `found_on`)

**File:** `tools/reelkit/figures.py:220-233, 108-112`
**Issue:** Verified that `--date 2099-01-01` is stored. `validate_entry` does not relate `checked_on` to `found_on` or to today, so a typo or a fabricated date passes and the provenance record becomes unreliable.
**Fix:** In `confirm_figure`, require `found_on <= on <= date.today().isoformat()`. In `validate_entry`, require `checked_on >= found_on` when both are set.

### WR-05: `slot` accepts past dates, and dates outside the `2026/` tree, without asking

**File:** `tools/reelkit/slot.py:242-275`
**Issue:** `draft.py slot --date 2020-01-01 --slug old-date` returns `ask: false`, `conflicts: []` and would create `2026/reels/drafts/2020-01-01-old-date`. D-14 says ambiguous dates must be confirmed once. A date before `proposed_date`, or before today, is exactly that case.
**Fix:** Set `ask = True` and add a conflict/notice when `chosen < today` or `chosen < proposed`. Reject years other than the `2026` the folder is named after (or derive the folder from the year).

### WR-06: `draft.py caption` prints the wrong hashtag count when there are no hashtags

**File:** `tools/draft.py:250-251`
**Issue:** `text.rstrip("\n").splitlines()[-1].split()` counts the words of the last non-empty line. With `hashtags: []` (allowed; it only warns) it reports `해시태그 5개` from `다음 편: IRP 세액공제 개정안` (verified), or the CTA words when there is no series.
**Fix:** Return the tag count from `build_caption` (`len(config["brand_hashtags"]) + len(src["hashtags"])`) and print that.

### WR-07: the caption config's draft `status` is validated but never surfaced

**File:** `tools/reelkit/caption.py:38-40, 147-175`; `tools/data/caption_config.json:2`
**Issue:** `status: "초안 문구 — 준법 검토 전"` is required but never shown in `warnings`, stdout or any artifact. The reviewer gets no signal that the disclaimer and CTA are unreviewed legal wording, contrary to the module docstring's intent.
**Fix:** Append `f"면책·CTA 문구 상태: {config['status']}"` to `warnings` (do not put it into caption.txt).

### WR-08: registry value for `nps_avg_old_age_all` is the published reel's rounded figure, not a sourced value

**File:** `tools/data/figures.json` (entry `nps_avg_old_age_all`)
**Issue:** `value: "700000"`, while `notes` says the secondary sources say 69.6~69.8만 원 and that "기존 편은 70만 원 표기". The value was back-filled to match the old reel, so the registry now stores a rounded number as if it were the source value (D-01: the value comes from the source). If a human confirms it against the 공단 statistic without reading the note, the rounding becomes "확인" data. Derived values such as yearly totals will be computed from the rounded value.
**Fix:** Store the best sourced value (for example `"697000"` with the conflict in `notes`) and let the reel show it with `man` + "약". Alternatively keep 700000 but put `"rounded from 69.6~69.8만 (2차)"` in `source.locator` and mark `kind`/notes so the confirmer must replace it.

## Info

### IN-01: house-style.md caption order disagrees with the code

**File:** `.claude/skills/make-reel/references/house-style.md:115`
**Issue:** The doc says the order is "첫 줄, 요약 3줄, 다음 편, 면책, CTA, 해시태그", but `caption.build_caption` puts 근거 → 면책 → CTA → 다음 편 (D-10/D-11 order). The doc also omits the 근거 line.
**Fix:** Change it to "첫 줄, 요약 3줄, 근거·기준, 면책, CTA, 다음 편, 해시태그".

### IN-02: atomic writes leave figures.json and spec.json with mode 0600

**File:** `tools/reelkit/figures.py:240-245`, `tools/reelkit/expand.py:290-295`
**Issue:** `tempfile.mkstemp` creates the file with mode 0600, and `os.replace` keeps that mode (verified: the registry copy went from 644 to 600 after `confirm`). This is harmless for git but surprising on shared hosts.
**Fix:** Before replacing, call `os.chmod(tmp, path.stat().st_mode & 0o777 if path.exists() else 0o644)`.

### IN-03: series teaser handling is narrow

**File:** `tools/reelkit/expand.py:156-161, 193-211`
**Issue:** Duplicate detection only recognizes lines that start with `<s>다음 편:`, so a hand-written `다음 편: X` without the tag gets a second teaser. The teaser is appended to the last scene even when that scene has no CTA line. `series.next`/`name` cannot contain placeholders (`{{` is rejected), so any figure in a next-episode title always fails check as UNREGISTERED.
**Fix:** Match `다음 편:` after stripping tags. Error out if the last scene has no `프로필 링크` line. Document that `series.next` must not contain figures.

### IN-04: `convert._series` silently drops episodes above 10 and strips the number from the name

**File:** `tools/reelkit/convert.py:73-79`
**Issue:** For a card series like "… 11편", `name` loses "11편" and no `episode` is set, so the reel shows the bare series name with no warning.
**Fix:** Keep `raw` as the name, or add a `warnings` entry to the skeleton when the episode is out of range.

### IN-05: `_read_json` error text says "원고 소스" for the caption source too

**File:** `tools/draft.py:118-127`
**Issue:** `cmd_caption` reuses `_read_json`, so a bad `caption.src.json` is reported as "원고 소스를 열 수 없음".
**Fix:** Pass a label argument (`_read_json(path, "게시글 문구 원본")`).

---

_Reviewed: 2026-10-29T02:57:44Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
