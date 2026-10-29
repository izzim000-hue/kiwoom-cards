---
phase: 02-draft-generation
verified: 2026-10-29T12:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files:
  - .claude/skills/make-reel/SKILL.md
  - .planning/phases/02-draft-generation/02-01-PLAN.md
  - .planning/phases/02-draft-generation/02-01-SUMMARY.md
  - .planning/phases/02-draft-generation/02-02-PLAN.md
  - .planning/phases/02-draft-generation/02-02-SUMMARY.md
  - .planning/phases/02-draft-generation/02-03-PLAN.md
  - .planning/phases/02-draft-generation/02-03-SUMMARY.md
  - .planning/phases/02-draft-generation/02-04-PLAN.md
  - .planning/phases/02-draft-generation/02-04-SUMMARY.md
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
covered_digest: "v4:sha256:1dc4cab9d811e03955f8063c0cebd49a5421d98bdfd35fea230bb430230dd622"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "새 Claude Code 세션에서 '연금저축 세액공제 한도 주제로 릴스 만들어 줘'라고 요청한다 (make-reel 스킬 대화)"
    expected: "스킬이 게시일·슬러그를 제안하고 모호하면 한 번 묻는다. 등록부에 없는 수치가 필요하면 멈추고 먼저 묻는다. 끝에 2026/reels/drafts/<날짜>-<슬러그>/ 에 spec.src.json, spec.json, check.json, caption.txt, MP4가 생기고 '확인 필요' 줄 보고가 나온다."
    why_human: "스킬은 Claude 가 대화로 따르는 지시문이다. 주제 한 줄 -> 원고 소스 작성(7장면, 훅->비유->수치->결론->주의->CTA)은 도구가 아니라 모델이 하며, 자동 시험은 고정 fixture 의 소스만 쓴다. 대화 흐름과 원고 품질은 세션에서만 볼 수 있다."
  - test: "생성된 MP4 를 열어 글씨 가독성, 줄바꿈, 장면 흐름, 시리즈 표시(첫 장면 ② 와 마지막 장면 '다음 편')를 눈으로 확인한다"
    expected: "하우스 형식(색감·폰트·레이아웃)이 기존 10편과 같고 줄 넘침·깨짐이 없다."
    why_human: "시각 품질과 브랜드 일관성은 프레임 비교(SSIM)나 ffprobe 로 판단할 수 없다."
  - test: "tools/data/figures.json 의 수치 30개를 1차 출처(law.go.kr, nts.go.kr, 국민연금공단, 통계청 등)에서 확인하고, 사람이 터미널에서 'draft.py figures confirm' 으로 확인 처리한다. 특히 nps_avg_old_age_all(700000 은 기존 편의 반올림 값, 2차 자료는 69.6~69.8만 원)과 발의 상태 3건(pension_credit_young_gov_proposal, pension_credit_member_bill_irp, pension_credit_member_bill_young)"
    expected: "확인된 항목은 확인 상태·확인일·확인자가 채워지고 check/figures list 가 오류를 내지 않는다. 틀린 값은 고친 뒤 기존 초안을 다시 expand 한다."
    why_human: "세션에서 law.go.kr·nts.go.kr 이 열리지 않고 Claude 는 확인 처리를 하면 안 된다(D-02). 30개가 모두 미확인인 것은 설계된 상태이며 결함이 아니다."
---

# Phase 2: 초안 생성 Verification Report

**Phase Goal:** 주제 한 줄이나 기존 카드뉴스 원고를 주면 릴스 원고 JSON 초안과 게시글 문구·해시태그를 받는다. 원고는 하우스 패턴을 따르고, 검증된 수치만 쓴다.
**Verified:** 2026-10-29
**Status:** human_needed
**Re-verification:** No — initial verification (사용자 규칙에 따라 단일 검증, 재검증 루프 없음)

모든 자동 확인 가능한 성공 기준은 코드와 실행으로 확인되었다. 남은 것은 세션 대화 흐름, 영상 시각 확인, 등록부 1차 출처 확인이며 모두 설계상 사람 몫이다. 코드 gap 은 없다.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 주제 한 줄 -> 7장면 내외, 훅->비유->수치->결론->주의->CTA, 약 25초 원고가 Phase 1 렌더러로 바로 MP4 가 된다 | VERIFIED (도구 경로) / 대화 경로는 human | `draft-pension.src.json` fixture 를 `expand` -> `check` -> `reel.py --layout new --strict` 로 실행: 7장면(훅, 비유, 수치 2, 결론, 주의, CTA), exit 0, 24.4초, specprobe 9/9 PASS(1080x1920, 30fps, yuv420p, AAC, faststart). 스킬 SKILL.md 가 slot->convert->figures->expand->check->caption->render 10단계를 규정하고 문서의 모든 `draft.py` 하위 명령이 실제 존재함을 e2e 시험이 확인. 주제 -> 소스 작성은 모델 대화라 human_verification 1 |
| 2 | 카드 원고(`2026/02-tax-deduction/spec.json`) -> 릴스 골격, 원본에 없는 숫자가 든 장면·줄은 경고 | VERIFIED | `draft.py convert 2026/02-tax-deduction/spec.json` -> 카드 6장 -> 장면 8개 골격(role/material/notes/카드 숫자 13개). `check --card` 로 fixture 를 대조하면 `scene 6 line 2: NOT_IN_CARD (0원)`, pension 은 `scene 5 line 1: NOT_IN_CARD (148.5만)` 등 장면·줄 단위 경고와 `CARD_NOTE_DROPPED` 가 나온다 |
| 3 | 세법·통계 수치는 모두 등록부 항목으로 추적, 등록부 밖 수치 차단, 발의 수치 확정 표현 차단, 파생 수치는 프로그램 계산값과 일치 | VERIFIED | 등록부 30개 전부 value/unit/source/as_of/found_on/checked_on/legal_status(시행 27·발의 3)/verified(미확인). 시험: `연 7% 수익이 나요` -> `UNREGISTERED (7%)` exit 1. 발의 수치를 표기 없이 쓰면 `PROPOSED_AS_FACT` 오류. `draft-pension.json` 의 `148.5만` 을 `199.9만` 으로 손편집하면 `STALE_FIGURE` + `SOURCE_MISMATCH` 오류(장부 재계산·소스 재확장). `test_calc_repro` 가 게시된 연말정산 편의 6.6만·38.5만·16.5만·13.2만을 Decimal 계산으로 재현하고 통과. 미확인 수치를 쓴 줄은 `확인 필요`(D-03) 로 표시 |
| 4 | 게시글 문구(훅, 핵심 요약, 근거, 일반 정보 고지, CTA) + 해시태그 5개 이하, 시리즈·회차·다음 편이 원고(첫 장면 포함)와 문구에 같이 들어간다 | VERIFIED | `draft.py caption` 출력 순서: 첫 줄 `연말정산 바로 알기 ② | 훅` -> 요약 3줄 -> 근거·기준(2026년 10월 기준) -> 면책 -> CTA -> `다음 편: IRP 세액공제 개정안` -> 해시태그 4개. 원고 쪽: 장면 1 top `연말정산 바로 알기 ②`, 마지막 장면 `<s>다음 편: …</s>`. `series.episode` 를 3 으로 바꿔 expand 하면 원고 top 과 caption 첫 줄이 둘 다 ③ 으로 바뀜(한 곳에서 파생). 해시태그 6개는 `초안 오류: 해시태그 6개 — … 최대 5개` exit 1, 파일 미생성. 미확인 수치를 요약에 쓰면 caption 이 `확인 필요` 경고를 낸다 |
| 5 | 버전 표시 없는 기존 10편은 고치지 않아도 읽히고 렌더 결과 불변, 새 선택 항목을 쓴 원고도 같은 명령으로 읽힌다 | VERIFIED | `python3 tools/golden.py` -> `golden: PASS 10/10 (재현 불가 1)` (프레임·경계 일치, SSIM 최소 0.9923, 규격 PASS). `git status` 변경 없음, `git diff 1708d48 HEAD -- 2026/ tools/data/` 에 게시본 변경 없음(등록부는 Phase 2 신규). v1 10편 모두 `check --legacy` exit 0. v2 필드(series/inputs/derive/figures/basis_items)를 가진 fixture 가 `reel.py` 로 렌더됨. `--legacy` 로 v2 원고를 통과시키는 우회는 exit 1(WR-03) |

**Score:** 5/5 truths verified (0 behavior-unverified, 0 overrides)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/data/figures.json` | 수치 등록부 30개, 전부 미확인 | VERIFIED | 30개, 필드 완비. 1차 출처 URL 은 대부분 null 이고 `candidate_sources` 로 후보만 기록(D-02 설계) |
| `tools/data/caption_config.json` | 면책·CTA·해시태그 상한 | VERIFIED | `max_hashtags: 5`, 상태 `초안 문구 — 준법 검토 전` 이 caption 경고로 표시됨 |
| `tools/draft.py` | expand/check/caption/convert/slot/figures | VERIFIED | 6개 하위 명령 모두 실행 확인(408줄) |
| `tools/reelkit/{calc,expand,check,numscan,caption,convert,slot,figures,spec}.py` | 계산·확장·점검·문구·골격·슬롯·등록부 | VERIFIED | 실질 구현(각 130~400줄), TBD/FIXME/XXX 없음 |
| `.claude/skills/make-reel/SKILL.md` + `references/{source-format,house-style}.md` | 주제 -> 초안 폴더 스킬 | VERIFIED | 10단계 절차, 금지 사항(confirm 금지·추정 숫자 금지·legacy 금지), 문서의 명령이 실제 존재 |
| `tools/tests/` | 시험 | VERIFIED | 402 tests OK (287초) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| spec.src.json 자리표시자 | figures.json | `expand` 가 `fig.<id>` 를 조회·서식화, 장부(figures) 기록 | WIRED | 6개 id 가 spec.json `figures` 에 `ref/fmt/sources` 로 기록 |
| spec.json | figures.json | `check` 가 장부를 현재 등록부로 재계산 | WIRED | 변조 시 STALE_FIGURE / LEDGER_MISMATCH / SOURCE_MISMATCH |
| series 필드 | 첫 장면 top, 마지막 장면 다음 편, caption 첫 줄·끝 | `expand` + `caption` | WIRED | episode 변경이 양쪽에 동시 반영 |
| card spec.json | 릴스 골격 / check 경고 | `convert`, `check --card` | WIRED | NOT_IN_CARD, CARD_NOTE_DROPPED |
| 원고 JSON | Phase 1 렌더러 | `reel.py --layout new --strict` | WIRED | MP4 24.4초, 규격 9/9 PASS |
| make-reel 스킬 | draft.py 하위 명령 | SKILL.md 절차 | WIRED | 문서 명령 존재 시험 통과 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| spec.json 화면 숫자 | `lines`, `top`, `basis` | figures.json + Decimal 계산(`calc.py`) | 예: 900만 원 x (15%+10%분 지방세) = 148.5만 | FLOWING |
| caption.txt 숫자 | summary | 원고 장부 항목만 허용 | 요약 숫자가 장부와 일치해야 통과 | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 전체 시험 | `python3 -m unittest discover -s tools/tests -p 'test_*.py'` | 402 tests OK | PASS |
| golden | `python3 tools/golden.py` | `golden: PASS 10/10 (재현 불가 1)` | PASS |
| pension fixture expand/check | `draft.py expand` / `check` | 오류 0, 경고 0, 확인 필요 7줄, exit 0 | PASS |
| tax fixture expand/check | 동일 | 오류 0, 확인 필요 4줄, 가정 수치 7줄 | PASS |
| 등록부 밖 숫자 | 원고에 `연 7%` 삽입 | UNREGISTERED, exit 1 | PASS |
| 발의 확정 표현 | 발의 id 를 표기 없이 사용 | PROPOSED_AS_FACT 오류 | PASS |
| 렌더 | `reel.py … --layout new --strict` + specprobe | exit 0, 24.4초, 9/9 | PASS |
| caption 해시태그 6개 | `draft.py caption` | exit 1, 파일 없음 | PASS |
| slot | `slot` 제안, 임시 폴더 `--create`, `../evil` 슬러그 | 제안 2026-11-08, 생성 성공, 경로 문자 거부 exit 1 | PASS |
| 게시본 불변 | `git status --short` (시험·golden 후) | 변경 없음 | PASS |

### Probe Execution

해당 없음(Phase 2 는 `probe-*.sh` 를 선언하지 않음).

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| DRAFT-01 | 주제 한 줄 -> 하우스 패턴 릴스 원고 | SATISFIED (대화 경로는 human) | SC1. 스킬 + fixture e2e 렌더 |
| DRAFT-02 | 카드 원고 -> 골격, 원본에 없는 숫자 경고 | SATISFIED | SC2 |
| DRAFT-03 | 수치 등록부 기반, 파생 수치 프로그램 계산 | SATISFIED | SC3 (1차 출처 확인은 human) |
| DRAFT-04 | 게시글 문구 + 해시태그 5개 이하 | SATISFIED | SC4 |
| DRAFT-05 | 시리즈·회차·다음 편 일관 반영 | SATISFIED | SC4. 표지는 Phase 3 범위(첫 장면 화면은 반영) |
| DRAFT-06 | v1 그대로 읽힘, 선택 필드 추가 | SATISFIED | SC5 |

고아 요구사항 없음. 참고: `.planning/REQUIREMENTS.md` 의 DRAFT-01..06 체크박스와 추적 표가 아직 `Pending`/미체크이고 ROADMAP 의 Phase 2 체크박스도 비어 있다. 문서 상태 갱신은 오케스트레이터 몫이다.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| tools/data/figures.json | `nps_avg_old_age_all` | 값 700000 이 게시본의 반올림 값(2차 자료 69.6~69.8만 원) | Info | 미확인 상태라 사용 줄이 `확인 필요` 로 표시됨. 사람이 확인할 항목(REVIEW WR-08) |
| tools/reelkit/figures.py, expand.py | atomic write | 파일 모드 0600 (IN-02) | Info | 기능 영향 없음 |
| tools/reelkit/expand.py | 다음 편 처리 | 태그 없는 `다음 편:` 중복 감지 안 함, CTA 없는 마지막 장면 처리 (IN-03) | Info | 좁은 경계 사례 |
| tools/reelkit/convert.py | `_series` | 11편 이상 회차 번호 소실 (IN-04) | Info | 현재 카드 시리즈는 10편 이하 |
| 등록부 확인 상태 | CR-05 잔여 위험 | PTY 로 우회하거나 figures.json 직접 편집 시 '확인' 위조 가능, PreToolUse 훅 미추가 | Warning | 방어는 스킬 규칙과 git diff 검토. 설정 변경에 사용자 승인이 필요해 수정하지 않았음. Phase 3 에서 결정 권장 |
| numscan | CR-04 잔여 위험 | 정규식 사전 기반이라 '총천만 원', '천만이' 같은 표기는 놓침 | Warning | 알려진 한계로 문서화됨. 점검표(Phase 3)에서 보완 권장 |

차단 앵커(TBD/FIXME/XXX)는 없다.

### Human Verification Required

#### 1. 세션 대화로 주제 -> 초안 폴더 만들기

**Test:** 새 Claude Code 세션에서 "연금저축 세액공제 한도 주제로 릴스 만들어 줘"라고 요청한다.
**Expected:** 날짜·슬러그 제안과 확인, 등록부에 없는 수치는 멈추고 질문, `2026/reels/drafts/<날짜>-<슬러그>/` 에 원고·점검·문구·MP4 생성, `확인 필요` 줄 보고.
**Why human:** 원고 작성은 모델 대화이며 자동 시험은 고정 fixture 만 쓴다.

#### 2. MP4 시각 확인

**Test:** 생성된 MP4 를 열어 본다.
**Expected:** 기존 10편과 같은 브랜드 형식, 줄 넘침·깨짐 없음, 첫 장면 시리즈 ②, 마지막 장면 다음 편 예고.
**Why human:** 시각 품질은 프로그램으로 판단할 수 없다.

#### 3. 등록부 수치 1차 출처 확인

**Test:** `tools/data/figures.json` 30개를 1차 출처에서 확인하고 사람이 터미널에서 `figures confirm` 한다. 우선 `nps_avg_old_age_all` 과 발의 3건.
**Expected:** 확인 필드가 채워지고 `figures list` 가 오류 없이 끝난다.
**Why human:** 세션에서 1차 출처가 열리지 않고 Claude 의 확인 처리는 금지(D-02). 전부 미확인인 것은 설계된 상태다.

### Gaps Summary

코드 gap 없음. 5개 성공 기준이 실행으로 확인되었다. 수치 위조 시도(`199.9만`, `연 7%`, 발의 확정 표현), 해시태그 6개, 슬러그 경로 탈출이 모두 차단되었고, 게시된 10편은 golden 10/10 으로 불변이다. 상태가 `human_needed` 인 이유는 대화 스킬 흐름, 영상 시각 확인, 등록부 1차 출처 확인이 사람 몫이기 때문이다. Phase 3 로 넘길 권고: CR-05 잔여 위험(확인 상태 위조 방지 훅)과 numscan 한계를 점검표에서 다루기.

---

_Verified: 2026-10-29_
_Verifier: Claude (gsd-verifier)_
