# 키움멘토 릴스 제작 자동화

## What This Is

키움멘토 인스타그램 릴스를 만드는 작업 흐름을 자동화하는 프로젝트다. 주제 한 줄이나 기존 카드뉴스 원고를 넣으면, 사람이 검수할 초안 묶음(릴스 원고 JSON · MP4 영상 · 표지 이미지 · 게시글 문구와 해시태그 · 금소법 표현 점검표)이 한 번에 나온다. 사용자는 Claude Code 세션에서 "이 주제로 릴스 만들어 줘"라고 요청하는 방식으로 쓴다. 1순위는 제작 자동화, 2순위는 자막 연출 강화(보는 맛)다.

## Core Value

주제 하나를 넣으면 기존 브랜드 형식을 지킨, 검수 가능한 릴스 초안 묶음이 10분 안에 나온다 — 그리고 단정 표현과 근거 없는 수치는 반드시 표시된다.

## Business Context

- **Customer**: 인스타그램 @kiwoom.mentor 팔로워 — 연금·절세·노후자금에 관심 있는 개인 및 자영업자·소규모 법인 대표
- **Revenue model**: 직접 수익 없음. 릴스 → 프로필 링크(1분 노후자금 계산기·전자책) → 상담 유입
- **Success metric**: 릴스 한 편 제작 시간(주제 → 검수 가능한 초안 묶음) 10분 이내
- **Strategy notes**: 상품 판매가 아닌 '교육적 중립성'이 신뢰의 핵심 (더원자산관리 표준 지침)

## Requirements

### Validated

<!-- 기존 저장소에서 이미 작동하는 것 -->

- ✓ 장면 원고 JSON(`scenes[].top`, `scenes[].lines`, `basis`)으로 자막형 릴스 MP4(1080×1920, 무음 트랙) 생성 — existing (`tools/reel.py`)
- ✓ `<g>` 금색 강조, `<s>` 작은 회색 글씨 마크업 — existing
- ✓ 브랜드 색: 세이지 그린 바탕 #DEE9E0, 딥그린 #2F4F3E, 골드 #B08D46, 하단 근거 표기 + @kiwoom.mentor — existing
- ✓ 카드뉴스 6장(1080×1350) PNG 생성 — existing (`tools/cards.py`)
- ✓ 파일 규칙: `2026/reels/<게시일>-<영문-슬러그>.mp4`, 원고 `2026/reels/specs/*.json` — existing
- ✓ 표지용 시점(cover_ms) 출력 — existing

### Active

- [ ] 주제 한 줄 입력 → 릴스 원고 JSON 초안 생성 (기존 10편의 장면 구성·말투 패턴 준수)
- [ ] 기존 카드뉴스 원고(spec) 입력 → 릴스 원고 JSON 변환
- [ ] 원고 → MP4 영상 + 표지 PNG 자동 생성 (기존 파일 규칙에 저장)
- [ ] 인스타 게시글 문구 + 해시태그 초안 생성
- [ ] 금소법 표현 점검표 자동 생성: 단정 표현("원금 보장", "확정 수익", "무조건 절세" 등), 근거·기준 미표기 수치, 세무 단정 표현을 표시하고 대체 표현 제안
- [ ] 한 번의 요청으로 위 산출물 전체를 묶음으로 출력 (Claude Code 스킬 형태)
- [ ] 자막 연출 강화: 글자 진입 모션, 장면 전환 효과, 숫자 카운트업 표현
- [ ] 배경음 삽입 옵션: 사용자가 제공한 저작권 문제 없는 음원 파일이 있을 때만

### Out of Scope

- AI 음성(TTS) 내레이션 — 외부 서비스·API 키 필요, 클라우드 네트워크 정책 제약. 릴스는 무음 시청이 많아 자막 연출이 우선. v2로 미룸
- 독립 실행 프로그램(API 직접 호출) — API 키·사용료 필요. 금융 콘텐츠는 매 편 사람 검수가 필수라 대화형(Claude Code)이 적합
- 인스타그램 자동 게시 — 모든 산출물은 사람 검수 후 게시해야 함
- 배경음 임의 수집 — 저작권 위험. 사용자 제공 음원만 사용
- 고객 사례·상담 자료 활용 — 저장소는 공개용 콘텐츠 전용, 개인정보보호

## Context

- 저장소 `kiwoom-cards`: 2026년 카드뉴스 8개 시리즈(`2026/01-net-worth` ~ `08-ebook-event`), 릴스 10편(2026-10-19 ~ 2026-11-07 게시분), 전자책 PDF 3종, 생성 도구 `tools/cards.py`·`tools/reel.py`
- 생성 도구는 Python + Playwright(Chromium 스크린샷) + ffmpeg(이미지 시퀀스 → MP4) 구조
- 같은 주제를 카드뉴스와 릴스로 함께 내는 경우가 많음(세액공제, 급여 두 사장님 시리즈) → 카드 원고 → 릴스 변환 수요
- 기존 릴스 패턴: 훅 질문 → 비유 → 수치 예시 → 결론 → 주의사항(세무사 확인 등) → CTA("저장해두고… 프로필 링크 · 1분 노후자금 계산기")
- 실행 환경: Claude Code 클라우드 세션. SessionStart 훅이 GSD·agent-browser를 설치하고 Chromium 경로(`/opt/pw-browsers/chromium`)를 지정
- 사용 가능한 스킬: agent-browser(화면 확인), design-taste-frontend(디자인 기준), compliance-review(고객 대면 자료 검수)

## Constraints

- **브랜드**: 기존 10편과 같은 색감·폰트·레이아웃 유지 — 시리즈 일관성
- **컴플라이언스**: "원금 보장", "확정 수익", "무조건 절세" 등 단정 표현 금지, 세무·법률 판단 단정 금지, 타사 비방 금지 — 금소법·보험업법
- **정확성**: 세법·요율·수치는 근거(기준·예시 조건)를 `basis`에 명시하고, 최신 여부를 확인해야 함 — 추정 수치는 추정임을 표시
- **개인정보**: 고객 실명·사례 사용 금지 — 공개용 콘텐츠만
- **검수**: 모든 산출물은 초안이며 사람 검수 후 게시
- **비용**: API 키·유료 서비스 없이 Claude Code 세션 안에서 동작
- **기술 스택**: 기존 Python + Playwright + ffmpeg 구조 확장 — 이미 검증된 파이프라인
- **환경**: 클라우드 네트워크 정책상 외부 다운로드가 제한될 수 있음 — 사전 설치된 Chromium 사용

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 대화형(Claude Code 세션) 방식 | 금융 콘텐츠는 매 편 사람 검수 필수, API 비용 없음 | — Pending |
| 입력은 주제 한 줄 + 기존 카드뉴스 원고 둘 다 지원 | 카드·릴스 동시 발행 패턴이 많음 | — Pending |
| 자동화 1순위, 보는 맛 2순위 | 제작 시간 단축이 우선 과제 | — Pending |
| 연출은 자막 모션 우선, 배경음은 사용자 제공 음원만, TTS는 v2 | 무음 시청 비중, 저작권·네트워크 제약 | — Pending |
| 금소법 점검표를 자동 흐름 안에 포함 | 컴플라이언스 리스크를 제작 단계에서 차단 | — Pending |
| 코드베이스 맵핑 생략 | 콘텐츠 저장소라 코드 구조 분석 이득이 작음 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-28 after initialization*
