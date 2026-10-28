---
status: testing
phase: 01-render-foundation
source: [01-VERIFICATION.md]
started: 2026-10-28T21:45:00Z
updated: 2026-10-28T21:45:00Z
---

## Current Test

number: 1
name: 안전영역 상수의 실기기 보정 (새 배치 근거 표기·계정명이 인스타그램 UI에 가려지지 않는지)
expected: |
  `python3 tools/reel.py <spec.json> <out.mp4> --layout new` 로 만든 릴스를 인스타그램에 비공개(또는 보관)로 올려
  iOS·Android 실기기에서 재생했을 때, 근거 표기(36px)와 @kiwoom.mentor 계정명이 하단 캡션·버튼·계정명 UI에
  가려지지 않고 읽힌다. 상단 라벨도 상태 표시줄·상단 UI에 가려지지 않는다.
  가려지면 `tools/reelkit/constants.py`의 `SAFE` 값(top 270, warn_y 1250, bottom_ui 450, right 150)만 조정한다.
awaiting: user response

## Tests

### 1. 안전영역 상수의 실기기 보정 (새 배치 근거 표기·계정명이 인스타그램 UI에 가려지지 않는지)
expected: `--layout new` 렌더 릴스를 비공개 업로드해 실기기에서 볼 때 근거 표기·계정명·상단 라벨이 인스타그램 UI에 가려지지 않는다. 가려지면 `constants.SAFE`만 조정한다.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
