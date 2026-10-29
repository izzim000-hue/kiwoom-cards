---
phase: 03-compliance-review-bundle
reviewed: 2026-10-29T08:03:50Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - .claude/skills/make-reel/SKILL.md
  - .claude/skills/make-reel/references/house-style.md
  - tools/data/compliance_rules.json
  - tools/draft.py
  - tools/reel.py
  - tools/reelkit/approve.py
  - tools/reelkit/bundle.py
  - tools/reelkit/compliance.py
  - tools/reelkit/redteam.py
  - tools/reelkit/render.py
  - tools/reelkit/review.py
  - tools/reelkit/slot.py
  - tools/reelkit/stills.py
findings:
  critical: 4
  warning: 9
  info: 8
  total: 21
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-29T08:03:50Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

I reviewed the compliance engine and rules data, the bundle, approve and promote paths, the review writer, stills, slot, the render hook, the CLI wiring and the make-reel skill docs. I also checked the test cited for environment dependence. I confirmed every compliance claim below by running `compliance.run` on one-scene specs with the shipped `tools/data/compliance_rules.json`, using the probe script at `/tmp/claude-0/-home-user-kiwoom-cards/4de16945-3f5f-566a-ae8a-809ea3b681f7/scratchpad/probe.py`.

The bundle and promote mechanics are mostly sound: names are derived from the validated folder, `os.link` never overwrites, the copy is re-hashed, rollback works, and a rebuild deletes `approval.json`. The weak point is the 수정 필요 gate that promote relies on, which fails in both directions:

- **Missed claims.** The negation window reads into the next line of a scene and into unrelated clauses, so guarantee and product-push wording gets moved to `suppressed` and the headline reads "패턴상 발견 없음". Some explicit tax and loss claims also get no finding at all, because particles and verb endings are not tolerated.
- **False blocks.** Correct or neutral wording raises 수정 필요 ("수익을 보장하는 상품은 없습니다", "사기 전에", "근무 조건", "고객님"). Promote has no waiver, so these block it.
- **Bypassable gate.** `promote --rules` lets the caller (which may be Claude) choose the rules the gate uses, including an empty rule list.

I found no "통과" in any tool-generated text and no statute number in the rules file. One remaining gap is listed under IN-01. In `tools/data/compliance_rules.json` I found no catastrophic-backtracking patterns, but the loader's guard against them is easy to get around (WR-05).

## Critical Issues

### CR-01: Negation window crosses scene lines and clauses, so 수정 필요 claims are suppressed

**File:** `tools/reelkit/compliance.py:48`, `tools/reelkit/compliance.py:349-353`, `tools/reelkit/compliance.py:367-372`, `tools/data/compliance_rules.json:7`

**Issue:** `_window` takes the 22 characters after a match. It cuts only at `. ! ? ;`, a blank line, or 지만/그러나-style connectors, and the docstring says on purpose that a single newline does not cut. In `reel_doc`, each scene line is its own sentence joined by a single `\n`, and reel lines normally have no closing punctuation. As a result, any negator in the next line, or later in the same clause, suppresses the claim. Promote then sees 0 수정 필요. Probe results with shipped rules:

| Lines | Result |
|---|---|
| `["원금 보장 상품이에요", "놓치지 마세요"]` | G-01 suppressed (`지 마`) |
| `["원금 보장 상품이에요", "놓치지 않게 저장"]` | G-01 suppressed (`않`) |
| `["원금 보장되는 상품이라 손해 보지 않아요"]` | G-01 suppressed |
| `["확정 수익 상품", "중도 해지는 불가"]` | G-02 suppressed (`불가`) |
| `["무조건 오릅니다", "걱정하지 마세요"]` | G-03 suppressed |
| `["원금 보장", "오해 없도록 다시 말해요"]` | G-01 suppressed (`오해`) |
| `["지금 가입하세요", "망설이지 마세요"]` | S-01 suppressed |

Each of these has 0 findings, the headline is `패턴상 발견 없음 — 사람 검수 필요`, and approve and promote accept it. The entries do appear in review.md's "예외 처리로 제외" table, but they are not counted and do not block anything.

**Fix:** Tie the negation to the matched predicate instead of to the following text:

```python
_CUT_RE = re.compile(r"[.!?;,]|\n|하지만|지만|그러나|다만|그런데|(?:요|다|죠|까)(?=\s|$)")
# reel lines are separate sentences: cut at a single newline too
```

Beyond that:
- Accept a negator only if it starts within a few characters of `end` and comes before the first predicate-final ending (요/다/니다/죠).
- Drop `오해` from `negators`. It is a topic word, not a negation of the claim.
- Add regression entries to `corpus.json` (not `heldout.json`): bad claim followed by an unrelated negated line, bad claim followed by a CTA such as "놓치지 마세요".

### CR-02: 수정 필요 false positives on correct wording block promote with no waiver

**File:** `tools/data/compliance_rules.json:7` (negators), `:13` (G-02), `:11` (G-01), `:14` (G-03), `:16` (G-05), `:30` (C-03), `:32` (P-02), `:9` (compact_terms "무조건"); gate at `tools/reelkit/approve.py:123-126` and `:220-223`

**Issue:** The README's severity policy says 수정 필요 is for precise patterns only, because promote has no waiver. These neutral or compliant sentences each raise 수정 필요:

- **Existential negation is not recognised as a negator** (held-out H-G01 class):
  - "수익을 보장하는 상품은 없습니다" → G-02
  - "원금 보장 상품은 없어요" → G-01
  - "확정 수익이란 없습니다" → G-02
  - "손실 없는 투자는 없어요" → G-05
  - "절대 손해 안 보는 상품은 없어요" → G-03
  - "무조건 절세는 없어요" → G-03 and T-01
- **C-03 bare `사기|바가지`:**
  - "ETF를 사기 전에" (사다 + -기) and "주식을 사기 위한 돈" → C-03 (비교·비방)
  - "보이스피싱 사기 주의" and "연금 사기 피하는 법" → C-03 (fraud-prevention content)
  - "사기 진작" → C-03
- **`무조건` as a substring:**
  - "채무조건 조정 제도" → G-03
  - "근무 조건에 따라" and "가입 의무 조건 확인" → X-compact, because the squeezed text "근무조건" contains "무조건"
- **P-02:**
  - "고객님, 오늘은 …" → P-02 (the except list has only `고객님께`)
  - "강사님 추천 도서" → P-02

Any one of these blocks approve and promote permanently. The only way out is to change correct wording.

**Fix:** These are general fixes, not tuned to held-out sentences:

```json
"negators": "... |(?:는|은|ㄴ|한|할|될|된|있는)\\s*[가-힣]{1,6}(?:은|는|이|가|도|이란|란)\\s*(?:어디에도\\s*|하나도\\s*|전혀\\s*)?없(?:습|어|다|음|죠)"
```

- **C-03:** Remove bare `사기|바가지`. Keep them only when an industry or competitor subject appears in the same clause, for example `(?:타사|은행|보험사|증권사|설계사)[^.!?\n]{0,10}(?:사기|바가지)`. Downgrade any remaining bare occurrence to 확인 필요.
- **`무조건`:**
  - In G-03, use `(?<![가-힣])무조건`.
  - For compact terms, only accept a hit whose first character was a word start in the original field: map squeezed offsets back to the original and require `i == 0 or field[i-1].isspace()`.
  - Alternatively, replace the bare `무조건` compact term with composite terms such as `무조건수익` and `무조건절세`.
- **P-02:** Add title nouns (`고객님(?!께)`, `강사님`, `회원님`, `전문가님`, …) as an except, or restrict the surname alternative to names followed by 씨 or by 님 with no title-noun stem.

Also decide on a human waiver: approve could record a per-finding human reason for a 수정 필요 entry it shows, and promote would accept only those exact (rule, where, text) triples. Without one, any remaining false positive is a hard stop.

### CR-03: The caller chooses the rules for promote's 수정 필요 gate, and an empty rule list is accepted

**File:** `tools/reelkit/approve.py:67-71`, `tools/reelkit/approve.py:217-223`, `tools/draft.py` (promote and approve `--rules`), `tools/reelkit/compliance.py:245-246`, `.claude/skills/make-reel/SKILL.md:75`

**Issue:** D-16 says promote copies only when 수정 필요 is 0 under current rules. However:
- `promote_cli(draft_dir, rules=...)` loads whatever `--rules` names.
- `load_rules` accepts `"rules": []`. I verified this: a copy of the shipped file with an empty list loads with 0 rules.
- A rules sha that differs from the approval's is only reported as an `알림`.

Claude is allowed to run promote, so `draft.py promote DIR --rules /tmp/empty.json` gets past the live re-scan. The SKILL does not forbid `--rules`. Approve also accepts `--rules`, and its output shows only the version string from that file, which the file's author controls. A human who copies a suggested `approve … --rules X` command cannot tell that lax rules were used.

**Fix:**

```python
# approve.py
def _load_rules(_rules=None):
    return compliance.load_rules(compliance.RULES_PATH)   # gate always uses the canonical file
...
if approval["rules"].get("sha256") != loaded.sha256:
    raise ApproveError("승인 때와 점검 규칙 파일이 다름 — 사람이 approve 를 다시 실행해야 함")
```

- Remove `--rules` from the `approve` and `promote` parsers, or allow it only for tests through a private keyword argument.
- Make `load_rules` reject an empty `rules` list.
- Add to SKILL.md "하면 안 되는 것": never pass `--rules`, `--registry` or `--config` overrides to bundle or promote.

### CR-04: Explicit 세무 단정 and loss-denial claims get no finding (conjugation and particle gaps)

**File:** `tools/data/compliance_rules.json:19` (T-01), `:16` (G-05), `:9` (compact_terms)

**Issue:** Explicit tax and loss claims produce zero findings of any severity:
- **"세금 안 냅니다" → no finding.** `안{S}내` matches the syllable 내 only. 내다 conjugates to 냅니다/낸다/낼, which are different syllables. Only "세금은 안 내요" matches.
- **"세금 한 푼도 안 냅니다" → no finding** (held-out H-B05, explicit). In addition to the conjugation gap, the intensifier "한 푼도" sits between subject and predicate, and no slot allows it.
- **"무 조 건 절 세" (H-B07)** is caught only as X-compact, and compact findings are hard-coded to 단정·보장 (`compliance.py:512`). So 세무 단정 is 0/3 on the held-out batch.
- **"가입만 하면 손해 볼 일은 없습니다" (H-B01) → no finding.** G-05 has `(?:일|걱정|염려){S}없` with no particle slot. "손해 볼 일 없습니다" matches, but "일은 없" does not. This is explicit wording, not an implicit one.

In each case the bundle headline reads "패턴상 발견 없음".

**Fix:** These are general morphology fixes:
- In T-01, replace `안{S}내` with `안{S}(?:내|냅|낸|낼)`, and the same for `낼{S}필요` → `(?:낼|내실){S}필요`.
- Add an optional intensifier slot after `(?:세금|세액){J}{S}`: `(?:(?:한\s*푼|단\s*(?:한\s*)?푼|일\s*원|하나|전혀|조금|일절|땡전)\s*(?:도|이라도)?{S})?`.
- In G-05, add `{J}` after `(?:일|걱정|염려)`.
- Give compact terms a category, e.g. `"compact_terms": [{"term": "무조건절세", "category": "세무 단정"}, …]`, and use it instead of `SPECIFIC_FIRST`. Add tax composites (`무조건절세`, `절세보장`, `세금0원`, `세금안냅`).

Re-measure on a new blind batch. Do not edit `heldout.json`.

## Warnings

### WR-01: Nothing technically enforces the human-only approval (D-15); approval.json can be forged

**File:** `tools/reelkit/approve.py:96`, `tools/reelkit/approve.py:172-180`, `.claude/settings.json`

**Issue:**
- `approve_cli` checks only `sys.stdin.isatty()`, so `script -qc "python3 tools/draft.py approve DIR --by 홍길동"` with the name piped in satisfies it.
- `_read_approval` accepts any JSON with `schema`, `name`, `files` and `rules`. The sha256 values are trivial for any process to compute, and Claude may run promote.
- `.claude/settings.json` has no `permissions.deny`.

`tools/README.md:120` documents this as a residual risk left to the user, so I rate it WARNING rather than BLOCKER. It is still the single point that makes D-15 unenforced.

**Fix (needs the user's decision; an automated fixer must not change permission settings):** Add `permissions.deny` entries for `Bash(python3 tools/draft.py approve:*)`, `Bash(script:*)`, `Write(**/approval.json)`, `Edit(**/approval.json)` and `Write(**/record.json)`. Optionally, have promote print the approver and approval time and require them to appear in the commit message the human writes.

### WR-02: Approve does not check that the files are the ones the bundle produced; review.md is not hashed

**File:** `tools/reelkit/approve.py:111-121`, `tools/reelkit/bundle.py:208-216`

**Issue:** `bundle.json` records only status and timing, not output hashes. Approve checks `status == "complete"` and then hashes whatever is currently in the folder. Between `bundle` and `approve`, `caption.txt` or `spec.json` can be edited by hand (the published spec then no longer matches the MP4 or `spec.src.json`). `review.md` can also be edited to drop findings; it is the document the human actually reads, and it is not hashed. The live re-scan catches only 수정 필요 patterns. It does not catch removed 확인 필요 rows, an edited checklist, or a desynced spec and MP4.

**Fix:** In `_write_bundle_json`, also record `"outputs": {name: sha256}` for spec.json, check.json, caption.txt, compliance.json, the MP4, the cover, the scenes image and review.md. Approve must refuse when any current hash differs from `bundle.json["outputs"]`, and it should include `review.md` and `bundle.json` in the approval's `files`.

### WR-03: Approve accepts bundles that failed the upload spec (exit 4), and promote never reads bundle.json

**File:** `tools/reelkit/approve.py:137-141`, `tools/reelkit/approve.py:194-233`

**Issue:** A bundle whose MP4 failed the Instagram upload-spec probe (exit 4: fps, size, audio or faststart) has `status: complete`. Approve prints only a "주의" line and approves it, and promote then publishes an MP4 the tool itself measured as non-compliant. Promote also never checks `bundle.json`, so a later failed rebuild is caught only through the purge of `approval.json`.

**Fix:** Refuse approve when `info["exit_code"] == 4`. In promote, re-read `bundle.json` (hashed per WR-02) and refuse unless `status == "complete"` and `exit_code in (0, 3)`.

### WR-04: The promote target is not tied to the repository's `<year>/reels`

**File:** `tools/reelkit/approve.py:183-191`, `tools/reelkit/approve.py:224-227`, `tools/reelkit/bundle.py:43-45`

**Issue:** `validate_draft_dir` only requires `parent.name == "drafts"`, and `_targets` publishes to `d.parent.parent`. The year check is skipped entirely when `reels.parent.name` is not four digits, and `d.resolve()` follows a symlinked `drafts/`. Any `X/drafts/<name>` therefore promotes into `X/`. Writes cannot overwrite, but the "only into 2026/reels" guarantee of D-16 does not hold.

**Fix:**

```python
expected = (constants.REPO_ROOT / name[:4] / "reels").resolve()
if reels.resolve() != expected:
    raise ApproveError(f"초안 폴더가 {expected}/drafts 아래가 아님")
```

Make the test harness pass the repo root in explicitly instead of relying on the grandparent.

### WR-05: The ReDoS guard is easy to get around, and examples are not required

**File:** `tools/reelkit/compliance.py:47`, `tools/reelkit/compliance.py:189-190`, `tools/reelkit/compliance.py:297-303`

**Issue:** `_NESTED_QUANTIFIER_RE` only rejects the literal sequence `[+*])[+*{]`. Verified:
- `(?:가+나?)+다` loads and takes **1.86 s on a 25-character line**. The time grows exponentially.
- `(?:가{1,})+다` loads and takes 1.24 s.
- Only `(가*)*다` is rejected.

The rules file is meant to be extended without code changes (COMP-05). Python `re` has no timeout, so one bad rule hangs bundle, approve and promote. Also, `examples` are optional in the loader, although `tools/README.md` says they are required for pattern rules.

**Fix:** Walk `re._parser.parse(source)` (`sre_parse`) and reject any `MAX_REPEAT`/`MIN_REPEAT` with an unbounded max whose subpattern contains another unbounded repeat, or a `BRANCH` with overlapping alternatives. Require non-empty `examples.hit` and `examples.miss` for `type == "pattern"`. At load, time each rule on a 2,000-character adversarial string such as `"가" * 2000 + "!"` and reject it above a budget.

### WR-06: The compact pass is skipped for any field that has an unrelated finding or suppression

**File:** `tools/reelkit/compliance.py:503-514`

**Issue:** `touched` includes fields that have any finding or any suppressed match, including 확인 필요 hits and except-suppressed hits. Verified:
- `["반드시 확인! 원금 보 장 상품"]` → 0 findings: the G-07 except marks the field touched, so the compact pass is skipped.
- `["가장 유리한 원금 보 장"]` → only C-04 확인 필요.
- `["원금 보 장 상품"]` alone → X-compact 수정 필요.

So any innocuous phrase in the same line hides an obfuscated guarantee.

**Fix:** Run the compact pass on every field. Drop a compact hit only if it overlaps an existing pattern finding for the same term: map squeezed offsets back to original offsets and compare spans.

### WR-07: G-04 needs "반드시" right before the verb, so "반드시 1억 원이 모입니다" is only 확인 필요 (H-B04)

**File:** `tools/data/compliance_rules.json:15` (G-04), `:18` (G-07)

**Issue:** G-04 is `반드시{S}(?:오른|…)`, so any object between 반드시 and the result verb defeats it. The phrase then falls through to G-07 at 확인 필요, and promote is not blocked.

**Fix:** In G-04, allow an intervening phrase without a sentence end and broaden the result verbs:

```
반드시[^.!?\n]{0,14}?(?:오르|오릅|올라|받|돌려|환급|이득|유리|절세|벌|모이|모입|모아|불어|늘어|쌓이|됩니다|돼요)
```

Keep G-07's advice except (`확인|상담|…`) as the except of G-04. Exclude imperative endings (`세요|십시오`) so that "반드시 확인 받으세요" stays a miss.

### WR-08: The implicit tier is 0/5 on the held-out batch

**File:** `tools/reelkit/compliance.py:34`, `tools/reelkit/redteam.py:22`, `tools/data/compliance_rules.json:28` (G-08)

**Issue:** The missed held-out sentences are H-B01, H-B06, H-B10, H-B13 and H-B21. This is a documented limitation (COMP-V2-01), and the LIMITS line is printed. Two of the five are reachable with general rules, though:
- H-B01 is the G-05 particle gap (CR-04).
- H-B13 ("타사 상품에는 단점만 … 장점만") is a one-sided comparison that C-02 could cover with `단점만|장점만`-style patterns at 확인 필요.

**Fix:** Keep the limitation statement. Add 확인 필요 patterns for one-sided comparisons (`(?:단점|장점)만`), "이 상품 하나면 끝", and "따 놓은 당상"-type idioms that suggest certainty. All of these stay at 확인 필요 so they cannot cause promote-blocking false positives.

### WR-09: An environment-dependent test fails when a gitignored real draft folder exists

**File:** `tools/tests/test_draft_e2e.py:122-134`; same pattern in `tools/tests/test_slot.py:63-75` and `tools/tests/test_slot.py:135-144`

**Issue:** `RealDirSlot.test_proposes_later_date_and_creates_nothing` runs `slot --slug pension-credit-limit` against the real `2026/reels`. It asserts `conflicts == []` and a proposed date relative to whatever is on disk. With `2026/reels/drafts/2026-11-08-pension-credit-limit/` present (it exists now and is gitignored), the test fails: `['슬러그 사용 중: pension-credit-limit (초안 폴더 …)'] != []`. I re-ran it and it failed. The executor worked around this by moving the folder aside during the gate run.

**Fix:** Run the test against a temp `reels` dir that mirrors the published names from `golden.load_manifest()`, passed with `--reels-dir`. Alternatively, use a slug guaranteed unused, such as `f"zz-test-{uuid4().hex[:8]}"`, and assert only on published conflicts. Do not read `drafts/` from the working tree.

## Info

### IN-01: The statute guard misses common forms and covers only the rules file

**File:** `tools/reelkit/compliance.py:46`, `tools/reelkit/compliance.py:196-209`

**Issue:** `제\s*\d+\s*조` does not match "금융소비자보호법 22조" (no 제) or "Article 22". `_check_strings` runs only on the rules file. Caption config disclaimers, check.json `detail` text lifted into review.md (`compliance.py:547`) and record values are not screened.

**Fix:** Use `(?:제\s*)?\d+\s*조(?:\s*의\s*\d+)?|Article\s*\d+`, and run the same guard over `caption_config.json` at load.

### IN-02: Purge deletes approval.json last

**File:** `tools/reelkit/bundle.py:31`, `tools/reelkit/bundle.py:107-115`

**Issue:** `approval.json` is the last entry in `PURGE_FIXED`. If an earlier unlink raises, the loop stops and the approval survives. Today that is harmless because nothing was deleted and the hashes still match, but "rebuild always invalidates approval" then depends on ordering.

**Fix:** Unlink `approval.json` first, before `resolve_request`, so that any `bundle` invocation on the folder invalidates approval.

### IN-03: Promote's handling of stale `.part` files and interrupts

**File:** `tools/reelkit/approve.py:241-255`

**Issue:**
- If a `.<target>.part` was left by a killed run, `open(part, "xb")` raises FileExistsError, and the message reads "이미 게시된 파일 — 덮어쓰지 않음: …/.x.mp4.part", which is misleading.
- The rollback then deletes that pre-existing file.
- KeyboardInterrupt is not caught, so partial targets can remain.

**Fix:** Check `part` existence separately with its own message. Catch `BaseException` for the rollback, then re-raise.

### IN-04: The approval audit trail is not kept with the published reel

**File:** `tools/reelkit/approve.py:236-262`

**Issue:** `approval.json` (approver, time, hashes, record copy), `review.md` and `record.json` (심의 상태, 심의번호) stay in the gitignored drafts folder. Deleting the draft removes the only record of the human approval and the ad-review fields.

**Fix:** Also link `approval.json` and `record.json` to `2026/reels/approvals/<name>.json`, using the same no-overwrite path.

### IN-05: The review.md upload-spec line treats WARN as not met without saying so

**File:** `tools/reelkit/bundle.py:399`, `tools/reelkit/review.py:192-193`

**Issue:** `spec_ok` counts only PASS, so a duration WARN shows as "6/7 항목 충족" with no failure listed.

**Fix:** Show the WARN count, e.g. "(경고 1)".

### IN-06: basis_required finding location is wrong when the match spans scenes

**File:** `tools/reelkit/compliance.py:462-467`

**Issue:** `body` joins fields with `\n` but `doc.text` uses `\n\n` between scenes. `doc.text.find(m.group(0))` then returns -1, and `span_at(-1)` attributes the finding to the first field. This only happens when there is no basis.

**Fix:** Compute the location from the span offsets used to build `body`.

### IN-07: A failed `stamp_created` leaves a folder that cannot be re-created

**File:** `tools/reelkit/slot.py:119-124`

**Issue:** If writing `created.json` fails after `mkdir`, the folder remains without it, and a retry gets "이미 있는 폴더".

**Fix:** Wrap the stamp: on OSError, `rmdir` the new empty folder and raise SlotError.

### IN-08: Unused aliases in approve.py

**File:** `tools/reelkit/approve.py:21-39`

**Issue:** `PROMOTED` and the third return value of `_names` duplicate `PROMOTED_KEYS` and `HASHED`, and `PROMOTED` is referenced nowhere.

**Fix:** Keep one constant set.

---

_Reviewed: 2026-10-29T08:03:50Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
