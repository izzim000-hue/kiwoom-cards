# Project Research Summary

**Project:** 키움멘토 릴스 제작 자동화 (@kiwoom.mentor)
**Domain:** 자막형 금융교육 인스타그램 릴스 — LLM 초안 생성 + 금소법 표현 점검 + 자막 모션 렌더 (기존 Python + Playwright + ffmpeg 파이프라인 확장)
**Researched:** 2026-10-28
**Confidence:** MEDIUM overall (렌더러 HIGH — 이 컨테이너에서 실측 / Instagram 사양 MEDIUM·LOW / 금소법 조문 LOW–MEDIUM)

## Executive Summary

이 프로젝트는 "주제 한 줄 → 사람이 검수할 초안 묶음"을 Claude Code 세션 안에서 만드는 제작 도구다. 묶음은 릴스 원고 JSON, 1080×1920·30fps MP4, 표지 PNG, 게시글 문구와 해시태그(최대 5개), 금소법 표현 점검표로 구성된다. 이 유형의 제품에서 신뢰할 만한 방식은 "렌더링·타이밍·규칙은 결정적 코드가 맡고, LLM은 원고와 캡션 두 가지 창작 입력만 쓰며, 게시는 항상 사람이 한다"는 분업이다. 기존 Python + Playwright + ffmpeg 구조를 그대로 확장하고, 유료 API 없이 동작해야 한다.

권장 접근은 **기반 → 자동화 → 모션** 순서다(PROJECT.md 우선순위: 1순위 제작 자동화, 2순위 자막 연출). 먼저 렌더 환경을 고정한다. Playwright를 1.63.0에 맞추고, 한글 폰트를 벤더링하고, 기존 10편 spec을 회귀 기준(golden corpus)으로 삼는다. 동시에 현재 `bottom:150px`에 있는 근거(basis) 줄과 계정명이 인스타그램 UI에 가려질 가능성이 높다는 점을 고친다. 그다음 spec 스키마·초안 생성·카드 변환·캡션·사실 레지스트리를 붙이고, 규칙 기반 점검과 `REVIEW.md`/승인 게이트로 번들을 완성한다. 모션(줄 진입, 장면 전환, 숫자 카운트업)은 마지막에 얹는다. 모션은 시간 `t`의 순수 함수로 그린 페이지를 한 번의 ffmpeg 프로세스로 파이프하는 방식이며, 실측으로 25초 릴스가 약 43초에 렌더된다. 10분 예산 안에 충분히 들어간다.

가장 큰 위험은 세 가지다. (1) 세법·연금 수치가 LLM 기억에서 나와 낡거나 틀릴 수 있다. 사실 레지스트리(기준일·출처·상태)와 사람 검증으로 막는다. (2) 키워드 점검표가 "통과"처럼 보여 검수가 형식화될 수 있다. 점검표에는 PASS 상태를 두지 않고, 레드팀 코퍼스로 재현율을 측정한다. (3) 이 계정 게시물이 금소법상 "광고"에 해당하는지, 키움 브랜드와의 관계가 어떤지 아직 확인되지 않았다. 확인 전까지는 광고 후보로 보고 필수 고지·심의 칸을 비워 둔 채 "미확인"으로 표시한다.

## Key Findings

### Recommended Stack

기존 파이프라인은 유지한다. 바꿀 것은 프레임을 만드는 방식 하나다. 상태마다 HTML 문자열을 새로 만들지 말고, 페이지 한 장을 한 번 로드해 `renderAt(t)`로 시간을 옮기며 캡처한다. Python은 30fps로 `t`를 진행하면서 PNG 바이트를 ffmpeg stdin에 파이프하고, 같은 ffmpeg 호출에서 선택적 BGM을 믹스한다 (STACK, 실측 HIGH).

**Core technologies:**
- **Playwright (Python) ==1.63.0** — 기존 프리설치 Chromium 1243과 맞는 버전. 1.64.1은 1248을 찾다 실패 [TESTED].
- **Chromium 153 (프리설치, `/opt/pw-browsers`)** — 한글 셰이핑·그라데이션·이징을 HTML/CSS로 얻는다. 다운로드는 정책상 막힘.
- **Web Animations + `renderAt(t)`** — 프레임 단위로 결정적. 750프레임 검증 [TESTED].
- **ffmpeg 6.1.1 (프리설치)** — `image2pipe` 입력, libx264, aac, `afade`/`aloop`/`loudnorm`/`alimiter` 존재 [TESTED].
- **Noto Sans KR 서브셋 OTF (Regular/Bold/Black, SIL OFL 1.1)** — `tools/fonts/`에 벤더링. 기존 reel.py의 'Noto Sans CJK KR'과 같은 디자인. 이 컨테이너에는 한글 폰트가 없어 벤더링 필수 [TESTED].
- **Python stdlib (+ Jinja2 선택)** — spec 검증, 점검 린트, 번들 작성. 새 의존성 없음.

**Output encoding (모든 릴스 동일):** `-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -profile:v high`, BT.709 태그, `-c:a aac -b:a 160k -ar 44100 -movflags +faststart -r 30`. 30fps (60fps는 비용 2배, 이득 없음).

**Environment requirements:**
- `pip install playwright`를 고정 없이 실행하면 실패 → `tools/requirements.txt`에 `playwright==1.63.0` 고정.
- Chromium 경로는 `AGENT_BROWSER_EXECUTABLE_PATH` → `/opt/pw-browsers/chromium*` glob → 기본 `launch()` 순서. 리비전 번호(1243)는 주석 외에 하드코딩하지 않는다.
- `page.set_content()` 페이지는 `about:blank`라 `file://` 폰트가 로드되지 않는다 → 템플릿을 디스크에 쓰고 `goto(file://…)`로 연 뒤 `document.fonts.ready`와 로드 상태 확인.

### Expected Features

**Must have (table stakes):**
- 주제 한 줄 → 릴스 spec JSON 초안 (하우스 패턴: 7장면 내외, 훅→비유→수치→결론→주의→CTA, 17~22줄, 약 25초). 기존 10편이 모두 이 구조 [HIGH, 코드·spec 분석].
- 카드뉴스 spec → 릴스 spec 변환 (골격 생성, 압축은 Claude). 같은 주제를 카드와 릴스로 함께 내는 패턴이 많다.
- MP4 렌더 (기존 유지), 표지 PNG 자동 생성 (기존엔 10편 중 1편만 수작업 표지).
- 캡션 초안 + 해시태그 **최대 5개** (고정 브랜드 태그 1~2 + 주제 태그). 30개 복붙 관행 폐기.
- 컴플라이언스 점검표를 번들 필수 구성요소로 포함.
- 한 번의 요청으로 전체 번들 + 한눈에 보는 `REVIEW.md`, 모든 산출물에 "검수 전 초안" 표기.
- 안전영역: 근거(basis)와 계정명을 하단 UI 영역 밖으로, basis 글자 최소 36px (기존 30px는 모바일에서 판독 곤란) [MEDIUM].
- CTA는 템플릿 슬롯 (마지막 장면 고정: `저장해두고 / 내 ○○ / ○○해 보세요 / 프로필 링크 · 1분 노후자금 계산기`).

**Should have (differentiators):**
- 수치 사실표(facts) + 산식 재계산: spec 숫자가 레지스트리/산식에서 나왔는지 기계 대조.
- 구조화 basis(가정·출처·기준일·미반영 항목) → 화면용 한 줄 자동 합성.
- 시리즈 모드(시리즈명·회차·다음 편 예고). 10편 중 8편이 시리즈.
- 줄 진입 페이드 + 8~16px 슬라이드(250~350ms, ease-out), 장면 전환 크로스페이드 1종, 숫자 카운트업(최종값에서 정지).
- 읽기 속도 기반 체류시간 (초기값 휴리스틱, LOW).
- 정지 프레임 시트와 "변경 요청 → 재생성 → 점검 재실행" 루프.

**Defer / excluded:**
- AI 음성(TTS) — v2 확정.
- 비교 막대 시각화, 훅 대안, 중복 주제 탐지, LLM 의미 점검 고도화 — 후속.
- 자동 게시·예약·음원 수집·스톡 소재·A/B 성과 최적화 — 영구 제외.

### Architecture Approach

원칙: "Claude는 원고(reel.json)와 캡션(caption.json)만 작성하고, 나머지는 한 명령(`reelkit`)으로 호출되는 결정적 Python이 처리한다." 스킬은 얇은 오케스트레이션과 판단만 담당하고, 규칙·타이밍·색은 코드와 데이터 파일(`rules/*.json`, `hashtags.json`)에 둔다 (HIGH for 경계와 흐름).

**Major components:**
1. **`spec.py`** — 버전 감지, v1 → v2 메모리 내 정규화, 검증, `<g>`/`<s>`/`<n>` 파서, `plain_text()`. 기존 10개 spec 파일은 다시 쓰지 않는다 (published record이자 회귀 코퍼스).
2. **`timeline.py`** — spec을 정수 프레임 이벤트로 컴파일. 총 길이, cover 시점, 진행바, 읽기속도 린트가 모두 여기서 읽는다. `LINE=0.85`, `HOLD=1.9` 전역 상수 대체.
3. **`render`** — `renderAt(t)` 페이지, 줄 넘침·줄바꿈·안전영역 측정, `layout.json` 출력.
4. **`encode.py` / `cover.py`** — 프레임 파이프 → MP4(+선택 BGM), settled 장면 PNG, `contact.png`.
5. **`lint.py` + `rules/compliance_ko.json`** — 규칙을 데이터로. 차단(block)/경고(warn)/정보.
6. **`caption.py`** — caption.json + 고정 푸터(교육 목적 고지, CTA) + 해시태그 검증(≤5, 금지 태그) + 린트.
7. **`convert.py`** — 카드 spec → 릴스 골격 + 출처 추적.
8. **`bundle.py`** — 파이프라인 실행, `REVIEW.md` + `manifest.json`(sha256, 상태), `promote`(승인 전 차단, 해시 불일치 차단).
9. **스킬 `make-reel`** — 의도 파악, 날짜·슬러그 도출, reel.json·caption.json 작성, `reelkit build`, 점검, 요약.

**Draft staging:** 산출물은 `2026/reels/drafts/<date>-<slug>/`에 먼저 생성, 사람이 승인 후 `promote`로만 정식 경로 복사. 정식 경로 직접 쓰기 금지.

**Schema versioning:** v1(암묵적) 유지. v2는 `version: 2`와 선택 필드(`meta`, `motion`, `facts`, `audio`, `src`, `hold`). v1은 메모리에서 `motion: none` + 기본 페이싱으로 정규화해 기존 영상을 그대로 재현.

### Critical Pitfalls

1. **폰트 조용한 대체** — 이 컨테이너에서 `'Noto Sans CJK KR'`은 Inter/WenQuanYi로 대체 [TESTED]. → 벤더링 + `document.fonts` 상태 assert + 첫 프레임 골든 비교 (Phase 1).
2. **Playwright/Chromium 버전 불일치** — 고정 없는 설치는 실행 실패 [TESTED]. → 1.63.0 고정 + 경로 폴백 + selftest (Phase 1).
3. **낡거나 환각된 세법·연금 수치, 개정안을 확정으로 서술** — 연금저축 600만·IRP 합산 900만, 세액공제율 15%/12%(지방세 포함 16.5%/13.2%)는 2차 자료 기준 [CORROBORATED]. IRP 세율 상향 개정안은 발의 상태 미확인 [UNVERIFIED]. → 사실 레지스트리(`id, value, as_of, source, verified_on, status: in_force|proposed|repealed`), LLM은 레지스트리 ID만 참조 (Phase 2 + 3 게이트).
4. **키워드 점검표의 허위 안심감** — 패러프레이즈·세무 단정·부정문 과탐. → PASS 상태 금지(`FLAGGED (n)` 또는 `NO PATTERN FLAGS — HUMAN REVIEW STILL REQUIRED`), 규칙 버전·날짜, 레드팀 코퍼스(부적절 ≥30, 적절 ≥15)로 재현율 보고 (Phase 3).
5. **기존 10편 회귀 + 근거 줄 가림** — `reel.py`는 테스트 없음. `bottom:150px` basis 줄과 계정명은 인스타 하단 UI와 겹칠 가능성 높음. → golden corpus 먼저, legacy 모드는 프레임·길이·cover_ms 보존, 안전영역 상수 한 곳 정의 + 오버레이 미리보기 (Phase 1).

**Also:** 모든 산출물은 draft 폴더에서 시작 (Pitfall 14), BGM은 `license_note` 없으면 렌더 거부 (13), 캡션·해시태그에도 동일 점검 (15), 마크업 이스케이프 (23).

## Implications for Roadmap

**4 coarse phases.** 앞 세 단계는 자동화, 마지막은 모션과 선택 BGM. 오너 결정은 단계 사이의 게이트.

### Phase 1: 렌더 기반 고정 (Foundation & Regression Guard)
**Rationale:** 폰트·브라우저·타임라인·회귀 기준이 흔들리면 이후가 조용히 망가진다. 근거 줄 가림은 컴플라이언스 문제이므로 먼저 고침.
**Delivers:**
- `doctor`/selftest (Chromium 경로, Korean 폰트 로드, ffmpeg) — 세션 시작 시 실행
- `tools/requirements.txt`(playwright==1.63.0), `tools/fonts/`(Noto Sans KR 서브셋)
- `spec.py`(v1 정규화, 검증, 마크업 파서), `timeline.py`(정수 프레임)
- 레이아웃 측정 가드 (줄 넘침·줄바꿈 감지, `word-break: keep-all`)
- 안전영역 상수 + 오버레이 디버그, 근거 줄을 위로 이동
- `.gitignore` (drafts, 스크래치, 중간 프레임), golden corpus (10편; MP4만 있는 2편은 "legacy, 재현 불가" 표기)
**Addresses:** FEATURES §B 안전영역·글자 크기, §A 하우스 패턴 기준선
**Avoids:** Pitfalls 1, 2, 6, 7, 9, 17
**Exit criteria:** 새 세션에서 `doctor` 종료 코드 0; 10편 모두 길이·장면 경계·cover_ms 유지; 첫 프레임이 기존 릴스와 허용 오차 내 일치; 넘침 0건.
**Owner input:** 안전영역 기준값(Gap 8 참조), 기존 10편 레이아웃 보존 여부.

### Phase 2: 초안 생성 (Draft Generation)
**Rationale:** 번들 입력인 spec 계약과 사실 레지스트리가 먼저.
**Delivers:**
- spec v2 (`meta.series`, 명시적 `motion`, `facts[]`, 구조화 `basis`, `src`)
- 스킬 `make-reel` + references (scene-patterns, voice, spec-schema, caption-template); 최근 spec 2~3편을 예시로
- 주제 → reel.json 초안 (7장면·20줄 내외·약 25초 예산 검증)
- `convert.py`: 카드 spec → 골격 + 출처 + "원본에 없는 숫자" 경고
- 캡션 조립 + 고정 푸터 + 해시태그 ≤5
- 사실 레지스트리(`tools/facts.json`) + 계산 모듈 (기존 10편 수치 재현 단위 테스트)
**Addresses:** FEATURES §A 전부, 차별화(facts, 시리즈)
**Avoids:** Pitfalls 3, 8, 12, 15, 16, 23, 24
**Owner input:** 시리즈 메타 규칙, 레지스트리 최초 확인 담당.
**Research flag:** **필요** — 세법·연금 수치의 출처 확보 (law.go.kr, nts.go.kr 세션 접근 불가). `/gsd-plan-phase --research-phase`.

### Phase 3: 점검과 검수 번들 (Compliance Gate & Review Bundle)
**Rationale:** 번들이 "게시 가능"처럼 보이면 형식적으로 넘어간다 (Pitfall 14). 이 단계 완료가 **자동화 마일스톤**.
**Delivers:**
- `rules/compliance_ko.json` (버전·날짜): 단정·보장(차단), 세무 단정, 근거 없는 수치, 기준일 누락, 상품 권유, 타사 비교·비방, 개인정보
- 필수 요소: 고정 푸터, 세무 수치 시 "세무사 확인", CTA 템플릿, 캡션 근거
- 레드팀 코퍼스 `tests/compliance-cases.json` (Phase 2에서 시드, 여기서 재현율 보고)
- 숫자 출처 대조 + 점검 출력 (장면·줄 번호, 문제 표현, 사유, 대체 표현 제안만, 심각도)
- `cover.py`(settled 장면 PNG, 중앙 1080×1440 확인), `contact.png`
- `bundle.py`: `drafts/<date>-<slug>/`, `REVIEW.md`(상태 배너, 점검, 체크리스트), `manifest.json`(sha256 + 규칙 버전)
- 검수 슬롯 (검수자, 날짜, 심의 상태 `draft|internal_reviewed|approved`, 심의번호 자리)
- `promote`: 차단 항목 또는 해시 불일치 시 거부
- 엔드투엔드 시간 측정 (목표 ≤10분)
**Addresses:** FEATURES §C, §D
**Avoids:** Pitfalls 4, 5, 14
**Owner input (게이트):** 광고 여부·필수 고지·심의 절차(Gap 1–2), 표지(Gap 4), drafts 보존(Gap 3)
**Research flag:** **필요, 최우선** — 금소법 제21·22조·시행령·금융광고 가이드라인 원문 미확인. 준법 담당 검토 전까지 규칙 세부는 "초안 규칙"으로 표시.

### Phase 4: 자막 모션 + 선택 BGM (Motion & Optional Audio)
**Rationale:** 2순위. Phase 1 타임라인·렌더 인터페이스가 있으면 리팩터링 없이 추가. BGM은 라이선스 게이트 필수.
**Delivers:**
- `reel_template.html` 한 번 로드 + `renderAt(t)`; 프리셋 `none | fade | rise`; 장면별 `hold`
- 줄 진입 250~350ms ease-out; 장면 전환 1종 (~0.3초); 연속 진행바
- 카운트업 `<n>38.5</n>만`; 고정 너비 박스; 최종 프레임 = 정적 텍스트
- 읽기 속도 기반 체류시간 (Phase 3 가독성 경고와 연결)
- 단일 ffmpeg 파이프 + BT.709; `motion=none`이 Phase 1 골든과 일치
- BGM(선택): `license_note` 없으면 렌더 거부, 페이드아웃 1.5초, 약 -16~-18 LUFS, 음원은 git 밖
**Addresses:** FEATURES §B 차별화, §A 음원
**Avoids:** Pitfalls 8, 10, 11, 13
**Exit criteria:** `none`이 골든과 일치; 모션 프리셋이 기존 릴스와 나란히 검토 승인; 카운트업 최종 프레임 = 정적 텍스트; 장면당 렌더 ≤3분; ffprobe 검사 통과(길이 ±0.1초).
**Research flag:** 짧은 spike — `Intl.Segmenter` 자소 분리와 줄별 투명도 시 줄바꿈 안정성, 클라우드 렌더 시간. 나머지 표준.

### Phase Ordering Rationale
- 기반 먼저: 측정 가능한 회귀 기준 없이는 시각 변경 검증 불가.
- 안전영역은 모션보다 먼저: 근거 표기가 가려진 상태로 모션을 더하면 안 됨.
- 초안 → 점검 → 번들: 점검 규칙은 spec 계약에 의존, 해시·승인은 확정된 spec·캡션에 의존.
- 자동화 완료 후 모션: PROJECT.md 우선순위와 일치.
- 오너 결정은 게이트: 광고 여부(Phase 3 전), 표지(Phase 3 전), BGM 라이선스(Phase 4 전).

### Research Flags
Needs deeper research: Phase 2 (레지스트리 출처), Phase 3 (금소법 원문, 최우선), Phase 4 (자소 분리·줄 안정성 spike).
Standard patterns: Phase 1 (프레임 비교 허용 오차 spike 제외), Phase 4 렌더 경로 (실측 완료).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH (렌더·오디오·폰트) / MEDIUM (Instagram 사양) | 렌더·파이프·BGM·폰트 실측 [TESTED]. Instagram 인코딩·해시태그 5개는 2차 자료 [CORROBORATED] |
| Features | MEDIUM | 하우스 패턴 HIGH (10편 spec·코드). 안전영역·금소법 세부는 2차 자료 |
| Architecture | HIGH (경계·흐름) / MEDIUM (성능) | 코드·spec 직접 도출. 프레임 시간 0.054~0.14초로 환경별 편차 |
| Pitfalls | MEDIUM (엔지니어링) / LOW (법률·Instagram 세부) | 폰트·Chromium·회귀 테스트됨. 법령 원문, 세율 현행성, 안전영역 픽셀, 사업자 음원 제한은 미검증 |

**Overall confidence:** MEDIUM.

### Where the research disagrees (and decisions)

| # | Topic | Disagreement | Decision |
|---|-------|--------------|----------|
| 1 | 프레임 전달 | STACK: 모든 프레임 renderAt(t) → PNG 파이프 → ffmpeg 1회 (~43초). ARCHITECTURE: 전환 구간만 프레임, 정지는 concat (250~350프레임). PITFALLS: 정지 재사용 | **STACK 채택.** 실측 시간이 예산의 1/10 수준이라 경로를 둘로 나눌 이유 없음. 장면 정지는 같은 프레임 반복, concat 미사용. 렌더 3분 초과 시 재검토 |
| 2 | 회귀 비교 | ARCHITECTURE: 프레임 해시 동일. PITFALLS: x264 비결정적 | **길이·장면 경계·cover_ms 정확 일치, 디코드 프레임은 허용 오차(평균 차이 또는 SSIM)로 비교.** 임계값은 Phase 1 spike |
| 3 | Playwright | STACK: `==1.63.0`. ARCHITECTURE·PITFALLS: executable_path 폴백 (1.64.1도 가능) | **둘 다.** 1.63.0 고정 + 경로 폴백. 리비전 하드코딩 금지 |
| 4 | 폰트 로딩 | PITFALLS: set_content 후 fonts.ready. STACK: set_content는 file:// 폰트 차단 [TESTED] | **STACK 채택.** 디스크 템플릿 + goto(file://) + 상태 assert |
| 5 | 폰트 이름·서브셋 | reel.py: 'Noto Sans CJK KR'. STACK: Noto Sans KR 서브셋 다운로드. PITFALLS: pyftsubset KS X 1001 | **Noto Sans KR 서브셋 벤더링** (다운로드 검증됨). 첫 프레임을 기존 릴스와 비교 |
| 6 | 카운트업 마크업 | STACK `<c from to>`, ARCHITECTURE `<n>38.5</n>만`, FEATURES `<n from to unit>` | **ARCHITECTURE의 `<n>`** — 보이는 텍스트를 감싸 plain_text와 최종 프레임 자동 일치 |
| 7 | 안전영역 | FEATURES: 상단 250, 하단 340(또는 450+), 우측 120~150px. PITFALLS: x 60~960, y 270~1250 (하단 35% ≈ 672px) | **[CONFLICTING] 중간 보수값:** 근거 줄·계정명 하단에서 최소 450px 위, 우측 150px 여백, 중요 텍스트 y ≤ 1250. 오버레이에서 y > 1250은 경고. 실기기 비공개 업로드로 확인 |
| 8 | 표지 | STACK: renderAt(cover_t). ARCHITECTURE: 훅 장면 settled. FEATURES: 전용 표지. 그리드 3:4 (일부 1:1) | **훅 장면 settled 기본 구현**, 중앙 1080×1440 내 제목. 전용 레이아웃은 오너 선택 |
| 9 | 단계 구성 | ARCHITECTURE 4단계, PITFALLS P0–P5, FEATURES MVP 순서 | **4단계** (위) |
| 10 | 광고 해당성 | FEATURES: 보수적으로 광고 간주. PITFALLS: 미확인은 "충족" 표시 금지 | **일치:** 광고 후보로 간주, 확인 전까지 필수 고지·심의는 "미확인" |

## Gaps to Address

### 오너 결정 필요 (carry-forward open questions)
1. **금소법 광고 해당 여부 / 키움 브랜드 관계** — 판매 의도, 상품 식별 가능성, 운영 주체 등록 상태. 기본값: 광고 후보, 필수 고지·심의 칸 비움, "미확인". 결정 시점: Phase 3 전. 준법 담당 확인 권장.
2. **필수 고지 문구·위치(영상/캡션/둘 다)와 내부 심의 절차 / 심의필 번호 형식** — 근거 줄을 영상에 필수로 둘지 포함. 결정 시점: Phase 3.
3. **drafts/ 보존 방식** — 권장: 승인된 MP4·표지·spec만 커밋, drafts 전체 gitignore, 자동 커밋 금지. 결정 시점: Phase 1 .gitignore 전.
4. **표지 선택** — 훅 장면 settled vs 전용 표지 레이아웃. 기본 구현은 훅 장면. 결정 시점: Phase 3 cover.py 전.
5. **BGM 음원과 라이선스** — 사용자 제공 파일만. 사업자 계정 상업 사용 가능 여부 [UNVERIFIED], 증빙 형식. 결정 시점: Phase 4 전. 그 전까지 BGM 비활성.
6. **시리즈·날짜·슬러그 결정 주체** — 권장: 모호하면 스킬이 질문.
7. **MP4 2편 (spec 없음, 2026-10-19-savings-interest 포함)** — 역설계 또는 "legacy, 재현 불가" 표기.
8. **기존 10편 레이아웃** — 권장: 게시된 기록이므로 그대로 두고 차이를 문서화, 수정은 신규 릴스에만.

### 미검증 항목 (UNVERIFIED / LOW — 게시 전 재확인)
- **금소법 제21조·제22조와 시행령 원문** — 미확인. 조문 번호를 코드나 점검 메시지에 인용하지 말 것 [LOW].
- **2026 세율·한도** — 연금저축 600만, 합산 900만, 세액공제율 15%/12% (지방세 포함 16.5%/13.2%) [CORROBORATED, 블로그·검색 요약]. 옛 수치(400만/700만)도 웹에 남아 있음 [CONFLICTING]. 소득 구간 경계는 현행 확인 필요.
- **IRP 세율 상향 개정안** (15%, 청년 17%) — 발의 상태 미확인 [UNVERIFIED]. "확정 아님"으로만 표기.
- **통계·기관명** (물가, 국민연금 수령액, 퇴직 연령, 국가데이터처) — 레지스트리에서 기준일 관리.
- **광고 제도 개선 TF 일정** (2026 Q3 예정) — 단일 보도 [CORROBORATED, 1 source].
- **Instagram 안전영역 픽셀** — 2차 자료 충돌 [CONFLICTING]. 실기기 비공개 업로드 한 번으로 보정 (사람 몫).
- **프로필 그리드 크롭** — 3:4 중앙 크롭 다수 의견, 일부 1:1·4:5 [CONFLICTING]. 표지 편집 화면에서 확인.
- **해시태그 5개 상한** — 2025년 12월 발표 [CORROBORATED, 뉴스]. 적용 범위 상이. 설정값, 기본 5. "3~5 권장" 귀속은 [LOW].
- **캡션 2,200자** [UNVERIFIED].
- **업로드 길이·용량·비트레이트** — 충돌 [CONFLICTING]. 현재 길이(20~26초)는 문제 없음.
- **읽기 속도 기준** (글자당 0.1초 등) — 초기 휴리스틱 [UNVERIFIED]. 기존 10편을 기준선으로 튜닝.
- **BT.709 태깅 효과** — 사이니지 sage #DEE9E0가 220,233,221 → 221,232,223으로 변함 [TESTED, ffmpeg 디코더 기준]. 기기 확인, 골든 허용 오차 내인지 확인.

### 기술 gap
- **프레임 비교 허용 오차** — Phase 1 spike (다른 Chromium 빌드 간 차이 측정).
- **카운트업과 줄바꿈** — 고정 너비 박스 방식 Phase 4 spike.
- **클라우드 세션 재현성** — 새 세션마다 selftest 통과를 Phase 1 종료 조건으로.

## Sources

### Primary (HIGH)
- 로컬 코드: `tools/reel.py`, `tools/cards.py`, `tools/README.md` (렌더 방식, LINE=0.85/HOLD=1.9, 폰트, 인코딩)
- 로컬 spec: `2026/reels/specs/*.json` (10편), `2026/02-tax-deduction/spec.json`
- `.planning/PROJECT.md`
- 이 컨테이너 실측 (2026-10-28): fc-match 한글 폰트 부재, Playwright 1.64.1 실행 실패(1248) / 1.63.0 성공, Chromium 153 executable_path 실행, ffmpeg 6.1.1 필터 목록, 750프레임 벤치(PNG 54ms, 전체 ~43초), 폰트 로딩 상태(set_content error vs goto(file://) loaded), BGM 필터·라운드트립 색상

### Secondary (MEDIUM)
- Instagram 안전영역·그리드·사양: Hopper HQ, Planoly, GrowthScribe, First Pier, PostSyncer, House of Marketers (수치 불일치 [CONFLICTING])
- 해시태그 5개: Social Media Today, Social Samosa, BetaNews 2025-12-19
- 사업자 음원 제한 (벤더·블로그): Foxi Music, Osborne Clarke
- 금융광고 규제 보도: 금융위 보도자료, fnnews 2021-06-08, economist.co.kr, Herald 2025-12-14, Maeil 2026-04-23, KOFIA 광고심의, Citibank Korea 금소법 안내문
- Noto Sans KR 서브셋 (SIL OFL 1.1): notofonts/noto-cjk Sans/SubsetOTF/KR — 다운로드·렌더 [TESTED]
- Playwright 1.62.0/1.63.0/1.64.1 browsers.json [TESTED]

### Tertiary (LOW — 검증 필요)
- 금소법 원문·시행령·가이드라인 원문 — law.go.kr 접근 불가. 검색 링크만: 국가법령정보센터 소득세법 검색, 국세청 근로소득 연금계좌 세액공제, Korea.kr 정책뉴스
- Remotion 라이선스, ffmpeg concat 마지막 길이, BT.601/709 기본, x264 비결정성, KOMCA/Content ID — 미검증 일반 지식
- 2026 연금·세율 블로그 자료 (wikidocs.net 등) — 참고용

---
*Research completed: 2026-10-28*
*Ready for roadmap: yes (Phase 3 시작 전 오너 게이트 1·2·4, Phase 4 시작 전 게이트 5 해결 필요)*
