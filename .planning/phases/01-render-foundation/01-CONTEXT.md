# Phase 1: 렌더 기반 고정 (Render Foundation) - Context

**Gathered:** 2026-10-28
**Status:** Ready for planning

<domain>
## Phase Boundary

새 클라우드 세션에서 추가 설치 없이 기존 형식 그대로 릴스를 다시 만들 수 있게 한다. 기존 릴스 원고 10편을 지키는 회귀 시험을 만든다. 새 릴스의 근거 표기와 계정명이 인스타그램 UI에 가려지지 않게 한다. 줄 넘침·안전영역 침범·업로드 규격 위반을 렌더 단계에서 드러낸다.

요구사항: ENV-01 ~ ENV-06. 초안 생성, 금소법 점검, 검수 묶음, 모션은 이 단계 범위가 아니다(2~4단계).

</domain>

<decisions>
## Implementation Decisions

### 근거 표기·계정명 배치 (새 릴스 전용)
- **D-01:** 새 릴스의 근거(`basis`) 줄은 하단 고정 위치가 아니라 **본문 줄 바로 아래에 붙여** 배치하고, 계정명(@kiwoom.mentor)은 근거 줄 아래에 둔다. 하단 UI 영역과의 거리는 안전영역 상수로 검사한다.
- **D-02:** 근거 글자 크기는 **36px, 최대 2줄**. 2줄을 넘으면 렌더 시 경고한다(ENV-05).
- **D-03:** 안전영역 기준값은 조사 SUMMARY의 중간 보수값으로 시작한다. 중요 텍스트는 하단 UI 영역(아래에서 최소 450px)과 우측 150px 여백을 침범하지 않고, y > 1250 영역은 경고 대상이다. 값은 한 곳(상수 또는 설정)에 정의해 실기기 비공개 업로드 후 보정할 수 있게 한다. — **Reversibility:** reversible — 상수 한 곳만 바꾸면 됨

### 진행 막대
- **D-04:** 화면 맨 위 14px 진행 막대는 **그대로 둔다**. 실기기 시험 업로드에서 상태 표시줄과 겹치는 문제가 확인되면 그때 옮긴다.

### 기존 릴스 10편
- **D-05:** 이미 게시된 10편은 **그대로 둔다**. 회귀 시험은 기존 배치(근거 `bottom:150px`, 30px)를 그대로 재현하는 legacy 경로로 수행하고, D-01~D-03의 새 배치는 새 릴스에만 적용한다. 기존 원고 파일(`2026/reels/specs/*.json`)은 다시 쓰지 않는다. — **Reversibility:** costly — 기존 영상과 원고는 게시된 기록이며 회귀 기준(golden corpus)으로 쓰이므로, 나중에 새 배치로 바꾸면 회귀 기준을 다시 만들어야 함
- **D-06:** 원고 없는 MP4 1편(`2026/reels/2026-10-19-savings-interest.mp4`)은 회귀 시험에서 "재현 불가"로 표기하고 역설계하지 않는다.

### 사전 점검과 초안 폴더
- **D-07:** 사전 점검(Chromium 실행, 저장소 포함 한글 폰트 로드, ffmpeg)은 **기존 SessionStart 훅(`.claude/hooks/session-start.sh`)에 연결해 세션 시작 시 자동 실행**하고, 같은 명령을 직접 실행할 수도 있게 한다. 실패 시 원인 메시지를 낸다(ENV-01).
- **D-08:** 초안 폴더(`2026/reels/drafts/`)와 렌더 중간 산출물(프레임, 임시 폴더)은 **`.gitignore`에 넣어 git에 올리지 않는다**. 자동 커밋하지 않는다.

### Claude's Discretion
- 회귀 시험의 화면 비교 허용 오차 방식(평균 차이 또는 SSIM)과 임계값 — 짧은 spike로 정한다.
- 사전 점검 명령 이름과 위치, 렌더러 모듈 분할(`spec.py`, `timeline.py` 등)의 세부 구조 — 조사 ARCHITECTURE를 따르되 플래너 재량.
- 폰트 서브셋 범위와 굵기 구성(Regular/Bold/Black) — 기존 릴스 첫 프레임과 비교해 결정.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 프로젝트 정의
- `.planning/PROJECT.md` — 핵심 가치, 제약(브랜드·컴플라이언스·비용·환경), 주요 결정
- `.planning/REQUIREMENTS.md` — ENV-01 ~ ENV-06 원문
- `.planning/ROADMAP.md` §Phase 1 — 목표, 완료 기준 5개, owner input, research flag

### 조사 결과
- `.planning/research/SUMMARY.md` — 단계 구성, 조사 간 불일치와 결정(프레임 전달, 회귀 비교, Playwright 고정, 폰트 로딩, 안전영역 중간값)
- `.planning/research/STACK.md` — 컨테이너 실측 환경 사실(Playwright 1.63.0 / Chromium 1243, 한글 폰트 부재, ffmpeg 6.1.1), 출력 인코딩 규격, 설치 방법
- `.planning/research/PITFALLS.md` — 폰트 조용한 대체, 버전 불일치, 근거 줄 가림, 색 공간·비트레이트, 회귀 위험
- `.planning/research/ARCHITECTURE.md` — `spec.py` / `timeline.py` / 렌더러 분할, v1 정규화, golden 시험

### 기존 코드와 자산
- `tools/reel.py` — 현재 렌더러(LINE=0.85, HOLD=1.9, `bottom:150px` 근거 줄, `set_content` 방식)
- `tools/README.md` — 파일 규칙(실제 카드 폴더는 `2026/<NN>-<slug>/`로 README와 다름)
- `2026/reels/specs/*.json` — 회귀 기준 원고 10편
- `.claude/hooks/session-start.sh` — 사전 점검을 연결할 기존 SessionStart 훅

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/reel.py`의 `frame()` HTML 생성과 `<g>`/`<s>` 마크업 치환: legacy 경로 재현의 기준
- `tools/cards.py`: 같은 브랜드 색 상수(SAGE, DG, GOLD 등) — 공통 상수로 뺄 후보
- `.claude/hooks/session-start.sh`: 이미 GSD·agent-browser 설치와 `AGENT_BROWSER_EXECUTABLE_PATH` 지정을 수행 — 사전 점검·Playwright 설치를 여기에 추가

### Established Patterns
- 원고 JSON → Playwright 스크린샷 → ffmpeg concat → MP4 (무음 트랙 포함)
- 출력 경로 규칙 `2026/reels/<게시일>-<영문-슬러그>.mp4`, 원고 `2026/reels/specs/`
- 브랜드 색: 세이지 #DEE9E0, 딥그린 #2F4F3E, 골드 #B08D46, 회색 #5B6E62

### Integration Points
- SessionStart 훅 → 사전 점검 자동 실행
- `reel.py` 진입점은 유지(shim)하고 내부를 새 모듈로 교체 — 기존 사용법(`python3 tools/reel.py spec.json out.mp4`) 보존

</code_context>

<specifics>
## Specific Ideas

- 사용자는 모든 질문에서 추천안을 선택했다: 근거는 본문 바로 아래, 36px·최대 2줄, 진행 막대 유지, 기존 10편 보존, 사전 점검 자동 실행, 초안 폴더 git 제외.
- 실기기 비공개 업로드로 안전영역을 보정하는 일은 사람 몫이다. 코드는 값을 한 곳에서 바꿀 수 있게만 하면 된다.

</specifics>

<deferred>
## Deferred Ideas

- 진행 막대 위치 이동 — 실기기 시험에서 문제가 확인될 때만(이 단계 범위 밖의 결정이 아니라 조건부 후속 조치)
- 기존 10편을 새 배치로 다시 만들기 — 하지 않기로 결정. 필요해지면 별도 작업

</deferred>

---

*Phase: 01-render-foundation*
*Context gathered: 2026-10-28*
