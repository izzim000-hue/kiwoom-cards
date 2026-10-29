# Phase 3: 점검과 검수 묶음 (Compliance & Review Bundle) - Context

**Gathered:** 2026-10-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Claude Code 세션에서 "이 주제로 릴스 만들어 줘" 한 번이면 10분 안에 검수 가능한 초안 묶음(원고·MP4·표지 PNG·게시글 문구·점검표·장면 모음 이미지·검수 요약)이 `2026/reels/drafts/<게시일>-<슬러그>/`에 생긴다. 금소법 표현 점검은 데이터 파일 규칙으로 원고·근거·게시글·해시태그를 모두 보고, "통과" 없이 "위험 표현 n건 발견" 또는 "패턴상 발견 없음 — 사람 검수 필요"로만 결과를 낸다. 사람이 승인하기 전에는 아무것도 정식 경로로 나가지 않는다.

요구사항: COMP-01 ~ COMP-06, BNDL-01 ~ BNDL-07. 자막 모션·배경음은 4단계, AI 의미 점검(COMP-V2-01)과 표지 후보 여러 안(BNDL-V2-01)은 v2.

</domain>

<decisions>
## Implementation Decisions

진행 방식: 사용자가 "추천대로"로 답해 온 방식에 따라 추천안으로 정했다(2026-10-29 재개 작업, 사용자는 앱을 보지 않는 중). 아래 오너 게이트는 ROADMAP의 기본값을 따르고, 모두 나중에 바꿀 수 있게 "미확인" 칸으로 둔다.

### 오너 게이트 (ROADMAP 기본값 채택)
- **D-01:** 금소법 광고 해당 여부는 **광고 후보로 간주**한다. 검수 요약 문서에 "광고 해당 여부: 미확인" 칸을 두고 사람이 기록한다. 키움 브랜드 관계도 같은 문서에 "미확인" 칸으로 둔다. — **Reversibility:** reversible — 문서 칸 값만 바뀜
- **D-02:** 필수 고지 문구는 Phase 2의 초안 고지(`tools/data/caption_config.json`)를 게시글에 쓰고, 영상에는 기존처럼 `basis`와 주의 장면으로 둔다. 문구·위치·내부 심의 절차는 "초안 — 준법 검토 전"으로 표시한다. 심의 상태(초안/내부 검수/승인)와 심의번호는 자유 입력 칸이며 기본값 "미확인".
- **D-03:** 표지는 **훅 장면 정지 화면**(렌더러의 `cover_ms` 시점)으로 만든다. 글자가 중앙 1080×1440 영역 안에 있는지 측정해 벗어나면 경고한다. 전용 표지 레이아웃은 만들지 않는다.

### 금소법 표현 점검 (COMP)
- **D-04:** 점검 규칙은 데이터 파일 `tools/data/compliance_rules.json`에 둔다(COMP-05). 규칙마다 id, 분류(단정·보장/세무 단정/상품 권유/비교·비방/개인정보/근거 누락 등), 패턴, 결과 등급("수정 필요"/"확인 필요"), 사유, 대체 표현 제안을 적는다. 파일에 규칙 버전과 기준일을 둔다.
- **D-05:** 규칙에는 "초안 규칙 — 준법 검토 전"을 표시하고, 금소법 조문 번호를 점검 메시지에 인용하지 않는다(ROADMAP Research flag).
- **D-06:** 점검 대상은 원고 장면 top·lines, basis, 게시글 문구(hook·요약·고정 고지 포함), 해시태그 전부(COMP-01). 결과 항목마다 위치(장면·줄 또는 게시글 줄), 문제 표현, 사유, 대체 표현 제안을 붙인다.
- **D-07:** "확인 필요" 항목(COMP-02)은 Phase 2 `check.json`의 확인 필요·가정 수치 결과를 그대로 가져오고, 여기에 세무 수치 장면의 "세무사 확인" 누락, 과거 성과 언급 시 "미래 보장 아님" 누락 같은 규칙을 더한다. 중복 판정 로직을 새로 만들지 않는다.
- **D-08:** 결과 머리말은 "위험 표현 n건 발견" 또는 "패턴상 발견 없음 — 사람 검수 필요" 둘 중 하나만, 규칙 버전·기준일과 함께 나온다(COMP-03). "통과"라는 말은 어디에도 쓰지 않는다.
- **D-09:** 탐지율·오탐 보고서(COMP-04)는 기존 10편 원고와 레드팀 사례(부적절 30건 이상, 적절 15건 이상)를 저장소의 테스트 데이터로 두고 명령 하나로 만든다. 레드팀 문장은 공개용 가상 문장만 쓴다(고객 사례 금지).
- **D-10:** 대체 표현은 제안만 하고 원고를 자동으로 고치지 않는다(REQUIREMENTS Out of Scope).

### 검수 묶음 (BNDL)
- **D-11:** 명령 하나(`draft.py bundle <dir>`)가 확장 → 점검 → 표현 점검 → 게시글 → 렌더 → 표지 → 장면 모음 → 검수 요약을 차례로 다시 만든다. 원고 수정 후에도 같은 명령으로 전부 다시 만든다(BNDL-05). `make-reel` 스킬은 이 명령을 쓰도록 바꾼다.
- **D-12:** 장면 모음 이미지(BNDL-03)는 장면마다 정지 화면 한 장씩을 한 이미지에 모은다. 새 패키지 없이 ffmpeg(또는 이미 설치된 Pillow)로 만든다.
- **D-13:** 검수 요약 문서(BNDL-04, COMP-06)는 초안 폴더의 Markdown 한 장(`review.md`): 상태 배너(초안 — 사람 검수 후 게시) → 점검 결과 → 사람 확인 목록(수치 재확인, 기준일, 표지 크롭, 음원 라이선스, 개인정보) → 광고 해당 여부·심의 상태·심의번호 기록 칸(기본 "미확인").
- **D-14:** 걸린 시간은 묶음 명령이 시작·끝 시각을 기록해 검수 요약과 별도 기록 파일에 남긴다(BNDL-07). 10분 기준은 주제 입력부터 묶음 완성까지의 실측으로 확인한다.

### 승인과 옮기기 (BNDL-06)
- **D-15:** 승인은 사람 전용이다. 승인 명령은 Phase 2의 `figures confirm`처럼 대화형 터미널과 재입력을 요구하고, 승인 시점의 파일 지문(sha256)을 초안 폴더에 기록한다. Claude는 승인 명령을 실행하지 않는다. — **Reversibility:** costly — 승인 기록 형식이 옮기기 판정의 기준이 됨
- **D-16:** 옮기기 명령은 승인 기록이 있고, "수정 필요"가 0건이고, 승인 뒤 파일 지문이 그대로일 때만 `2026/reels/<게시일>-<슬러그>.mp4`, `2026/reels/specs/<게시일>-<슬러그>.json`, `2026/reels/captions/<게시일>-<슬러그>.txt`(표지는 `2026/reels/<게시일>-<슬러그>-cover.png`)로 복사한다. 하나라도 어긋나면 거부한다. 이미 있는 게시 파일은 덮어쓰지 않는다.

### 이어지는 결정
- 새 릴스는 `--layout new`, 기존 10편과 게시된 파일은 건드리지 않는다(Phase 1·2).
- 등록부 수치는 사람만 "확인" 처리한다. 국민연금 평균 같은 통계 수치는 정확한 값을 쓰지 않고 필요할 때 조사한다(STATE.md).
- 사용량 절약: 계획 검토·재리뷰 없이 코드 리뷰 1회, 최종 검증 1회.

### Claude's Discretion
- 규칙 패턴 문법(정규식·조사 허용 방식), 규칙 파일 세부 스키마.
- 레드팀 문장 구성, 보고서 형식.
- 장면 모음 이미지의 배치·크기, 검수 요약 문서의 세부 문구.
- 승인 기록 파일 이름과 형식.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 프로젝트·요구사항
- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md` (COMP-01~06, BNDL-01~07), `.planning/ROADMAP.md` §Phase 3 (성공 기준 5개, Owner gates, Research flag)
- `.planning/research/PITFALLS.md`, `.planning/research/FEATURES.md` — 컴플라이언스 위험, 검수 흐름

### 이전 단계 결과
- `.planning/phases/02-draft-generation/02-CONTEXT.md`, `02-0*-SUMMARY.md`, `02-REVIEW-FIX.md`, `02-VERIFICATION.md` — draft.py, check.json 계약(needs_check, assumptions), caption, slot, make-reel 스킬, 남은 위험
- `.planning/phases/01-render-foundation/01-CONTEXT.md` — 렌더러, cover_ms, 안전영역
- `tools/README.md` — reel.py, draft.py 사용법·종료 코드
- `.claude/skills/make-reel/SKILL.md`, `references/house-style.md` (금지 표현 초안 목록) — 표현 점검 규칙의 출발점
- `tools/data/caption_config.json` — 초안 고지·CTA 문구

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/draft.py` + `tools/reelkit/{expand,check,caption,slot,figures,numscan}.py`: 초안 생성·수치 점검. 묶음 명령은 이것들을 차례로 부른다.
- `tools/reel.py` / `reelkit/render.py`: 렌더, `cover_ms` 출력, 안전영역 측정과 오버레이 PNG.
- `tools/specprobe.py`: 업로드 규격 검사.
- `tools/tests/` (stdlib unittest, 402개), `tools/golden.py` (회귀 10/10).

### Established Patterns
- stdlib만, 한국어 오류 메시지, 종료 코드 0/1/2/3/4. 사람 전용 명령은 TTY + 재입력(`figures confirm`).
- 초안 폴더는 git 제외. 게시된 파일은 읽기 전용.

### Integration Points
- `make-reel` 스킬 절차를 묶음 명령 하나로 단순화.
- 검수 요약이 check.json·lint 결과·caption 경고를 한 곳에 모은다.

</code_context>

<specifics>
## Specific Ideas

- 결과 머리말 예: "위험 표현 2건 발견 · 규칙 v0.1(초안) · 기준일 2026-10-29" / "패턴상 발견 없음 — 사람 검수 필요 · 규칙 v0.1(초안) · 기준일 2026-10-29".
- 사용자 지침의 금지 목록(원금 보장, 확정 수익, 무조건 절세, 단점 누락 비교, 타사 비방, 세무·법률 단정, 실명 고객 사례)을 규칙 초안에 반영.

</specifics>

<deferred>
## Deferred Ideas

- AI 의미 점검(암시적 보장 표현) — v2 (COMP-V2-01)
- 표지 후보 2~3안·3:4 그리드 미리보기 — v2 (BNDL-V2-01)
- 등록부 직접 편집을 막는 작업 환경 차단 규칙(PreToolUse) — 사용자 결정 대기 (Phase 2 남은 위험)

</deferred>

---

*Phase: 03-compliance-review-bundle*
*Context gathered: 2026-10-29*
