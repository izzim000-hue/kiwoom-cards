---
status: partial
phase: 02-draft-generation
source: [02-VERIFICATION.md]
started: 2026-10-29T04:00:00Z
updated: 2026-10-29T06:40:00Z
---

## Current Test

[testing paused — 1 item outstanding]

## Tests

### 1. make-reel 스킬로 주제 한 줄 → 초안 폴더
expected: 날짜·슬러그를 한 번 묻고, 등록부 수치만 쓰고, spec.src.json·spec.json·check.json·caption.txt·MP4를 drafts/에 남긴다. git status 변화 없음.
result: pass
note: "2026-10-29 세션에서 '연금저축 세액공제 한도'로 실행. 사용자가 날짜·슬러그 '추천대로' 승인. check 오류 0·경고 0·확인 필요 7줄, caption 해시태그 4개, MP4 23.5초 spec 9/9, git status 깨끗."

### 2. 시험 영상 보기 (브랜드 느낌·줄바꿈·근거 표기·계정명)
expected: 기존 릴스와 같은 색감·글씨체, 어색한 줄바꿈 없음, 근거 표기와 @kiwoom.mentor가 잘 보임
result: [pending]
note: "영상 확인 대기 — 사용자가 나중에 확인하기로 함 (2026-10-29)"

### 3. 수치 등록부 1차 출처 확인
expected: 사람이 원문과 대조해 figures confirm
result: skipped
reason: "설계상 사람 전용·사용 시점 확인. 국민연금 평균 등 통계 수치는 정확한 값을 원고에 쓰지 않고 필요할 때 조사하기로 함 (STATE.md 결정)"

## Summary

total: 3
passed: 1
issues: 0
pending: 1
skipped: 1
blocked: 0

## Gaps
