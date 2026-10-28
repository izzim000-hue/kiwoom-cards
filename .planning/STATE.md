---
gsd_state_version: "1.0"
current_phase: 2
current_phase_name: 초안 생성 (Draft Generation)
status: planning
stopped_at: Phase 1 complete, ready to plan Phase 2
last_updated: "2026-10-28T22:27:47.047Z"
last_activity: 2026-10-28
last_activity_desc: Phase 1 complete, transitioned to Phase 2
state_head: 83330e56c8ca56554a54988d6d8005cdafca9600
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-28)

**Core value:** 주제 하나를 넣으면 기존 브랜드 형식을 지킨, 검수 가능한 릴스 초안 묶음이 10분 안에 나온다. 단정 표현과 근거 없는 수치는 반드시 표시된다.
**Current focus:** Phase 2 — 초안 생성 (Draft Generation)

## Current Position

Phase: 2 — 초안 생성 (Draft Generation)
Plan: Not started
Status: Ready to plan
Last activity: 2026-10-28 — Phase 1 complete, transitioned to Phase 2

Progress: [███░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 4 | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 1 P01 | 3 min | 3 tasks | 14 files |
| Phase 1 P02 | 8 min | 2 tasks | 6 files |
| Phase 1 P03 | 14 min | 2 tasks | 9 files |
| Phase 1 P04 | 17 min | 2 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 4단계 coarse 구성. 순서는 렌더 기반 → 초안 생성 → 점검·검수 묶음(자동화 완성) → 자막 모션·선택 배경음
- [Roadmap]: Playwright 1.63.0 고정과 Chromium 경로 폴백을 함께 쓴다. Noto Sans KR 서브셋은 벤더링하고, 템플릿은 goto(file://)로 열어 폰트 로드를 확인한다 (research SUMMARY)
- [Roadmap]: 회귀 비교 기준. 길이·장면 경계·cover_ms는 정확히 일치해야 하고, 디코드 프레임은 허용 오차로 비교한다
- [Roadmap]: 모든 산출물은 `2026/reels/drafts/`에서 시작한다. 정식 경로로는 승인 후 promote로만 옮긴다
- [Phase 1]: Plan 01: 폰트 원본(무수정) 벤더링 FONT_VARIANT=original, 14,494,040 B; legacy 배치 <s>=display:block이 shim 기본; 폰트 로드 실패 시 exit 2로 중단
- [Phase 1]: Plan 02: legacy 원문 삽입은 유지하고 <g></g><s></s> 네 태그 허용 목록을 렌더 전에 검사한다. reel.py 종료 코드는 0 정상 / 1 원고 오류 / 2 환경 오류
- [Phase 1]: [01-03] reel.py exit codes: 3 = --strict with layout warnings, 4 = upload-spec FAIL (4 wins); MP4 is always written first
- [Phase 1]: [01-03] Legacy layout skips position measurement (only FONT_FALLBACK runs); new layout measured in-browser, warnings reported never auto-fixed
- [Phase 1]: ENV-02 accepted routes: pinned (hook installs playwright 1.63.0 into the user site) and no-install (system Playwright 1.64.1 + preinstalled Chromium via executable_path); doctor names the version and launch path
- [Phase 1]: Golden SSIM threshold stays 0.98 (lowest measured 0.9923); manifest built only from committed MP4s and specs, never from renderer output
- [Phase 1]: Golden treats a not-reproducible reel with an upload-spec FAIL as a failure (exit 1)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 2] 새 릴스 초안은 `--layout new`로 렌더한다 (legacy는 기존 10편 재현용)
- [Phase 1] 안전영역은 Android 실기기에서만 확인함. iOS 미확인
- [Phase 2] 리서치 필요: 세법·연금 수치 출처(law.go.kr·nts.go.kr 접근 불가), 2026 한도·세액공제율·IRP 개정안 상태 미확인
- [Phase 3 전] 오너 게이트: 금소법 광고 해당 여부·키움 브랜드 관계, 필수 고지 문구·위치·심의 절차, 표지 방식. 결정 전 기본값은 광고 후보로 간주하고 "미확인"으로 두는 것이다
- [Phase 3] 리서치 최우선: 금소법 제21·22조·시행령·금융광고 가이드라인 원문 미확인. 규칙은 "초안 규칙"으로 표시한다
- [Phase 4 전] 오너 게이트: 배경음 음원·라이선스. 결정 전까지 배경음 비활성
- [Phase 4] spike: 한글 자소 분리·줄별 투명도 적용 시 줄바꿈 안정성, 카운트업 고정 너비
- [ENV-03] 원고 없는 MP4는 요구사항에 "2편"으로 적혀 있지만 저장소에는 1편(`2026-10-19-savings-interest.mp4`)뿐이다. MP4는 11편, 원고는 10편이다

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-10-28T22:30:00Z
Stopped at: Phase 1 complete, ready to plan Phase 2
Resume file: None
