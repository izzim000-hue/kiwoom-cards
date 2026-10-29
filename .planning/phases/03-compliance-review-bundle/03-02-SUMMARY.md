---
phase: 03-compliance-review-bundle
plan: 02
subsystem: compliance-redteam
tags: [compliance, redteam, held-out, detection-rate, stdlib]
status: complete

requires:
  - phase: 03-compliance-review-bundle
    provides: compliance.load_rules/run/Result, rules file v0.1 (28 rules), golden manifest
provides:
  - tools/tests/redteam/heldout.json (22 inappropriate / 10 appropriate, written blind, one commit)
  - tools/tests/redteam/corpus.json (seed 41 / 21, RESEARCH Appendix B verbatim)
  - tools/reelkit/redteam.py (load_corpus, entry_spec, evaluate, published_counts, report)
  - `draft.py redteam [--rules] [--corpus] [--heldout] [--json]`
  - tools/tests/test_redteam.py (30 tests)
affects: [03-03, 03-04]

requirements-completed: [COMP-04]

actuals:
  tokens: 30000
  tasks: 2
  commits: 2
plan_head_before: 7d4bbab26a5e25711653c1722beac5de0534ed94
plan_head_after: 96dfb2078ff0b6126eedd07365a70d745ddfe623

key-files:
  created:
    - tools/tests/redteam/heldout.json
    - tools/tests/redteam/corpus.json
    - tools/reelkit/redteam.py
    - tools/tests/test_redteam.py
  modified:
    - tools/draft.py
---

# Phase 3 Plan 02: Red-team Report Summary

**`python3 tools/draft.py redteam` prints one Korean report: published 10 reels, an in-sample seed corpus (41 bad / 21 good) and a held-out batch written blind to the rules (22 bad / 10 good) on separate lines marked as not used for tuning.**

## Accomplishments

- Task 1 (`40b3d8d`): held-out batch written from the category descriptions in REQUIREMENTS and CONTEXT only. Before this commit the rules file, engine, engine tests, RESEARCH and 03-01 SUMMARY were not opened. 22 inappropriate entries (단정·보장 4, 세무 단정 3, 상품 권유 3, 비교·비방 3, 개인정보 4, 근거 누락 5; tiers: 14 explicit, 3 obfuscated, 5 implicit) and 10 appropriate entries, including hard negatives (negated claim, quoted warning, compliant 예시 scene with basis, 세무사 확인 line, honorific, 부정 문맥의 절세). Phone numbers use the 010-0000-0000 form, the email is at example.com, the one customer name is fictional. The file has exactly one commit and was never edited afterwards.
- Task 2 (`96dfb20`): seed corpus copied from Appendix B (parsed from the markdown block, not retyped), `redteam.py`, `draft.py redteam`, 30 tests. Detection means at least one finding with the entry's category and a severity at or above `expect_severity`; a finding of another category or a lower severity is listed as 분류/등급 불일치. Rule scan time is measured per rule with `time.perf_counter` around a single-rule scan of each entry (`dataclasses.replace(rules, rules=[rule])`).
- Seed thresholds hold on the first run with the Plan 01 rules: published 10 수정 필요 = 0, explicit + obfuscated 38/38, good-set 수정 필요 false positives 0/21.

## Rule changes

None. `tools/data/compliance_rules.json` is unchanged in this plan. Every held-out result below is reported as it is and no rule was adjusted because of it.

## Evidence: full `python3 tools/draft.py redteam` output (COMP-04)

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
[규칙 시간] 가장 느린 규칙 G-01 0.31ms (문장당 최대)
주의: 표본 내 수치는 규칙을 쓴 쪽이 같은 문장을 보고 맞춘 결과라 실제보다 높게 나옵니다. 따로 쓴 문장 줄을 함께 보세요.
한계: 키워드·패턴 방식이라 암시적 표현은 잡지 못합니다 (AI 의미 점검은 v2)
redteam: 표본 내 탐지 41/41 · 오탐 0/21 · 따로 쓴 문장 탐지 14/22 · 오탐 1/10 · 기존 10편 수정 필요 0건
```

## What the held-out line says (for the owner, not acted on)

In-sample 100% versus held-out 64% (14/22) is the gap the caveat warns about. Findings that a rule reviewer may want, to be handled outside this plan:

- 세무 단정 is 0/3 on the held-out batch: "세금 한 푼도 안 냅니다" (H-B05, explicit) is missed outright, "환급은 따 놓은 당상" (H-B06) is implicit, and the spaced "무 조 건 절 세" (H-B07) is caught only as a 단정·보장 compact finding, so the category differs.
- H-B04 ("반드시 1억 원이 모입니다") is flagged only at 확인 필요 by G-07, where 수정 필요 was expected.
- One false positive on a good sentence: H-G01 "수익을 보장하는 상품은 없습니다" triggers G-02 at 수정 필요 (the negation follows the verb stem and is not recognised by the suppression window). This is the kind of 수정 필요 false positive that would block promotion with no waiver, so it is worth a decision before the rules are called ready.
- Implicit tier is 0/5, as the limits sentence says.

## Task Commits

1. Task 1: `40b3d8d` test(03-02): add held-out red-team batch written blind to the rules
2. Task 2: `96dfb20` feat(03-02): add draft.py redteam detection and false-positive report

## Verification

- `python3 -m unittest discover -s tools/tests -p 'test_redteam.py' -v`: Ran 30 tests, OK.
- `python3 tools/draft.py redteam`: exit 0, last line matches the required form with 기존 10편 수정 필요 0건; `규칙 조정에 쓰지 않음` present; `git log --format=%H -- tools/tests/redteam/heldout.json` lists one hash.
- `python3 tools/draft.py redteam --help`: exit 0.
- The report text contains no 통과 and no statute article number (asserted in tests).
- Full suite and golden were not run (instruction to save usage; this plan touches only new files and the `draft.py` subcommand table).

## Deviations from Plan

None - plan executed as written. One small formatting choice: the published-10 listing prints `수정 필요 (오탐 후보)` for 수정 필요 findings and the bare severity for 확인 필요, instead of repeating the word.

## Known Stubs

None.

## Threat Flags

None. No new network surface, no package installs. Red-team text is fictional (T-03-07); the held-out batch was committed before any rule was read (T-03-06).

## Self-Check: PASSED

- tools/tests/redteam/heldout.json, tools/tests/redteam/corpus.json, tools/reelkit/redteam.py, tools/tests/test_redteam.py: present.
- Commits 40b3d8d and 96dfb20: present on branch ccr-f9cedca2-3o2v27.
