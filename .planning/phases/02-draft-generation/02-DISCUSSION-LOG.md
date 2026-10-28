# Phase 2: 초안 생성 (Draft Generation) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-28
**Phase:** 02-draft-generation
**Areas discussed:** 수치 등록부 확인 절차, 등록부에 없는 수치, 시리즈·회차·예고 표시, 게시글 문구 형식, 게시일·슬러그

모든 항목을 추천안과 함께 한 번에 제시했고, 사용자가 "추천대로"로 답했다.

---

## 수치 등록부 확인 절차

| Option | Description | Selected |
|--------|-------------|----------|
| 미확인으로 넣고 초안엔 쓰되 "확인 필요" 표시 | 최초 확인은 사람, 발의 수치는 확정 표현 금지 | ✓ |
| 사람 확인 전에는 사용 금지 | 확인 전까지 초안 작업이 막힘 | |

**User's choice:** 추천대로

---

## 등록부에 없는 수치가 필요할 때

| Option | Description | Selected |
|--------|-------------|----------|
| 멈추고 먼저 묻기 | 추정 숫자로 채우지 않음 | ✓ |
| 추정치로 채우고 "추정" 표시 | 근거 없는 숫자 위험 | |

**User's choice:** 추천대로

---

## 시리즈·회차·다음 편 예고 표시

| Option | Description | Selected |
|--------|-------------|----------|
| 첫 장면 상단 `시리즈명 ①` + 마지막 장면 `다음 편: ○○` + 문구 첫 줄 자동 반영 | 기존 첫 장면=시리즈명 관례 유지 | ✓ |
| 게시글 문구에만 표시 | 영상에서는 시리즈가 보이지 않음 | |

**User's choice:** 추천대로

---

## 게시글 문구 형식

| Option | Description | Selected |
|--------|-------------|----------|
| 훅→핵심 3줄→근거·기준일→일반 정보 고지→CTA, 주제 태그 3~5개 (브랜드 태그는 사용자 지정 시 추가) | 임의 브랜드 태그 생성 안 함 | ✓ |

**User's choice:** 추천대로 (고정 브랜드 태그는 미정)

---

## 게시일·슬러그

| Option | Description | Selected |
|--------|-------------|----------|
| 다음 빈 날짜 제안 + 영문 슬러그 자동, 모호하면 질문 | 로드맵 권장안 | ✓ |
| 매번 사용자가 지정 | | |

**User's choice:** 추천대로

---

## Claude's Discretion

- 등록부 파일 위치·형식, 원고의 수치 참조 문법
- 숫자 탐지 정규식과 예외 규칙, 카드 → 릴스 골격 변환 세부
- 생성(Claude)과 검증·계산(프로그램)의 분담 구조
- 게시글 문구 파일 형식·이름

## Deferred Ideas

- 고정 브랜드 해시태그 (사용자 지정 대기)
- 훅 대안, 중복·모순 경고 (v2)
