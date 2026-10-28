# Phase 1: 렌더 기반 고정 (Render Foundation) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-28
**Phase:** 01-render-foundation
**Areas discussed:** 근거 표기 새 위치, 근거 글자 크기와 줄 수, 진행 막대, 기존 10편, 사전 점검과 초안 폴더

모든 항목을 한 번에 제시하고, 사용자가 "추천대로"로 답했다.

---

## 근거 표기 새 위치

| Option | Description | Selected |
|--------|-------------|----------|
| 본문 바로 아래 | 본문 줄 밑에 근거, 그 아래 계정명. 하단 UI와 확실히 분리 | ✓ |
| 하단 고정 위치 상향 | 아래에서 450px 위로 이동, 본문이 길면 겹칠 수 있음 | |
| 화면 위쪽 | 진행 막대 아래, 상단 UI와 겹칠 위험 | |

**User's choice:** 추천대로 (본문 바로 아래)

---

## 근거 글자 크기와 줄 수

| Option | Description | Selected |
|--------|-------------|----------|
| 36px, 최대 2줄 | 넘치면 경고 | ✓ |
| 40px, 1줄 | 더 크지만 긴 근거는 못 넣음 | |

**User's choice:** 추천대로 (36px, 최대 2줄)

---

## 진행 막대

| Option | Description | Selected |
|--------|-------------|----------|
| 그대로 둠 | 실기기 시험에서 문제가 보이면 이동 | ✓ |
| 상단 안전영역 아래로 이동 | 약 250px 아래 | |

**User's choice:** 추천대로 (그대로 둠)

---

## 기존 10편

| Option | Description | Selected |
|--------|-------------|----------|
| 게시된 그대로 둠 | 회귀 시험은 기존 배치로, 새 배치는 새 릴스에만 | ✓ |
| 새 배치로 다시 만들기 | 게시된 영상과 달라짐 | |

**User's choice:** 추천대로 (그대로 둠)

---

## 사전 점검과 초안 폴더

| Option | Description | Selected |
|--------|-------------|----------|
| 세션 시작 훅 자동 실행 + 직접 실행 가능, 초안 폴더 git 제외 | | ✓ |
| 직접 실행할 때만, 초안 폴더 git 포함 | | |

**User's choice:** 추천대로

---

## Claude's Discretion

- 회귀 화면 비교 허용 오차 방식과 임계값
- 사전 점검 명령 이름·위치, 렌더러 모듈 분할 세부
- 폰트 서브셋 범위와 굵기 구성

## Deferred Ideas

- 진행 막대 위치 이동 (실기기 시험에서 문제 확인 시)
- 기존 10편 새 배치 재제작 (하지 않기로 함)
