---
phase: 01-render-foundation
verified: 2026-10-28T22:10:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files:
  - ".claude/hooks/session-start.sh"
  - ".gitignore"
  - ".planning/phases/01-render-foundation/01-01-PLAN.md"
  - ".planning/phases/01-render-foundation/01-01-SUMMARY.md"
  - ".planning/phases/01-render-foundation/01-02-PLAN.md"
  - ".planning/phases/01-render-foundation/01-02-SUMMARY.md"
  - ".planning/phases/01-render-foundation/01-03-PLAN.md"
  - ".planning/phases/01-render-foundation/01-03-SUMMARY.md"
  - ".planning/phases/01-render-foundation/01-04-PLAN.md"
  - ".planning/phases/01-render-foundation/01-04-SUMMARY.md"
  - "tools/README.md"
  - "tools/doctor.py"
  - "tools/fonts/NotoSansKR-Black.otf"
  - "tools/fonts/NotoSansKR-Bold.otf"
  - "tools/fonts/NotoSansKR-Regular.otf"
  - "tools/fonts/OFL.txt"
  - "tools/fonts/README.md"
  - "tools/golden.py"
  - "tools/reel.py"
  - "tools/reelkit/__init__.py"
  - "tools/reelkit/browser.py"
  - "tools/reelkit/constants.py"
  - "tools/reelkit/doctor.py"
  - "tools/reelkit/encode.py"
  - "tools/reelkit/golden.py"
  - "tools/reelkit/layout.py"
  - "tools/reelkit/render.py"
  - "tools/reelkit/spec.py"
  - "tools/reelkit/specprobe.py"
  - "tools/reelkit/templates/frame.html"
  - "tools/reelkit/timeline.py"
  - "tools/requirements.txt"
  - "tools/specprobe.py"
  - "tools/tests/fixtures/bad-layout.json"
  - "tools/tests/fixtures/ok-layout.json"
  - "tools/tests/golden/manifest.json"
  - "tools/tests/test_doctor.py"
  - "tools/tests/test_golden.py"
  - "tools/tests/test_layout.py"
  - "tools/tests/test_spec.py"
  - "tools/tests/test_specprobe.py"
covered_digest: "v4:sha256:5a1d7e47b4d00b5f49b3aa4756cdaaf565f0f0888a299b14eb2a588993ad2964"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "안전영역 상수(SAFE: top 270, warn_y 1250, bottom_ui 450, right 150)를 실기기 비공개 업로드로 보정"
    expected: "새 배치(--layout new)로 만든 릴스를 인스타그램 앱에 비공개로 올렸을 때 근거 표기와 @kiwoom.mentor가 하단 UI(캡션·버튼)와 우측 버튼에 가려지지 않는다. 가려지면 tools/reelkit/constants.py의 SAFE 값만 바꾸고 overlay 미리보기로 다시 확인"
    why_human: "상수는 조사 중간 보수값(270은 research 가정 A1, 검증 전)이다. 코드는 이 값 기준의 위치만 검증할 수 있고 실제 인스타그램 UI 가림 여부는 실기기에서만 확인된다 (ROADMAP Owner input, CONTEXT D-03)"
---

# Phase 1: 렌더 기반 고정 (Render Foundation) 검증 보고서

**Phase Goal:** 새 클라우드 세션에서 추가 설치 없이 기존 형식 그대로 릴스를 다시 만들 수 있다. 새 릴스의 근거 표기와 계정명은 인스타그램 UI에 가려지지 않는다. 화면 깨짐과 업로드 규격 위반은 렌더 단계에서 바로 드러난다.
**Verified:** 2026-10-28T22:10:00Z
**Status:** human_needed
**Re-verification:** No — 최초 검증

## 요약

ROADMAP 완료 기준 5개와 요구사항 ENV-01~06 모두 코드와 실행 결과로 확인했다. SUMMARY의 주장은 근거로 쓰지 않고 직접 실행해 다시 측정했다. 자동 검사로 막힌 항목은 없다. 남은 것은 사람이 해야 하는 안전영역 상수의 실기기 보정 1건뿐이다(ROADMAP에 Owner input으로 이미 명시됨). 그래서 상태는 `human_needed`다. 코드 리뷰의 열린 경고 6건과 정보 6건은 완료 기준을 깨지는 않지만 아래 경고 절에 정리했다.

## Goal Achievement

### Observable Truths (ROADMAP 완료 기준)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 사전 점검 명령 하나로 Chromium 실행·번들 한글 폰트 로드·ffmpeg 확인. 모두 정상이면 종료 코드 0, 하나라도 실패하면 원인 메시지 | ✓ VERIFIED | `python3 tools/doctor.py` 6개 항목 모두 `[정상]`, rc=0. `--json`은 `ok:true`, `playwright:"1.63.0"`, `launch:"default"`. Black 폰트를 뺀 폴더로 `--fonts-dir` 실행 시 `[실패] font-files ... NotoSansKR-Black.otf 없음`과 `[실패] font-load ... 시스템 폰트 'WenQuanYi Zen Hei' 로 그려집니다`, rc=1(`--quiet`도 rc=1). 훅(`CLAUDE_CODE_REMOTE=true bash .claude/hooks/session-start.sh`)을 빈 `PYTHONUSERBASE`로 실행하면 1.63.0을 설치하고 정상 한 줄, rc=0. 두 번째 실행은 설치 없이 정상 한 줄, stderr 0바이트. `PIP_NO_INDEX=1`과 빈 사용자 site에서는 pip 실패 메시지를 stderr로 내고 시스템 playwright 1.64.1과 `/opt/pw-browsers/chromium` 폴백으로 정상(경고 2건), rc=0 |
| 2 | 기존 10편 회귀 시험이 편마다 길이·장면 경계·표지 시점·화면 일치를 보고. 원고 없는 MP4는 "재현 불가" | ✓ VERIFIED | `python3 tools/golden.py` 직접 실행: 10편 모두 PASS (frames 730/705/705/781/654/705/756/756/730/654 기준과 동일, 경계 19/18/18/21/16/18/20/20/19/16 일치, SSIM 최소 0.9923~0.9985), `재현 불가 2026-10-19-savings-interest (원고 없음, D-06)`, 마지막 줄 `golden: PASS 10/10 (재현 불가 1)`, rc=0. manifest의 mp4·spec sha256과 프레임 수를 파일에서 다시 계산해 전부 일치. `git diff 313d420 HEAD -- 2026`이 비어 있어 게시된 MP4·원고는 수정되지 않음. 민감도 확인: 복사본에서 legacy 배치의 gap을 40px에서 30px로 바꾸면 SSIM 최소 0.9521로 FAIL(rc=1) |
| 3 | 새 릴스에서 근거와 @kiwoom.mentor가 하단 UI 영역 밖에 36px 이상으로 표시. 오버레이 미리보기로 확인 가능 | ✓ VERIFIED (실기기 보정은 human) | `reel.py tax-deduction.json --layout new`: 기본 배치 대신 새 배치. 오버레이 `safe-s05.png`를 눈으로 확인: 근거와 계정명이 y=270~1250 안쪽에 있고 빨간 UI 띠(y≥1470)와 우측 150px 띠 밖. 36px 글자 높이 확인(계정명 행 1191~1226). MP4 프레임(17.5초)에는 오버레이 색이 없고 y>1226 영역은 세이지 배경 그대로. 기존 10편 원고를 새 배치로 측정하면 근거·계정명 경고 0건(`check_layout`, 10편 전부). `BASIS_PX=ACCT_PX=36`은 `constants.py` |
| 4 | 줄 넘침·줄바꿈 깨짐·안전영역 침범 원고는 해당 장면과 줄을 가리키는 경고 | ✓ VERIFIED | `tests/fixtures/bad-layout.json`을 `--layout new`로 렌더: `scene 1 line top: TOP`, `line 1: WRAP (4 lines)`, `line 2: RIGHT (right=1609 > 930)`, `line 7: WARN_Y`, `line basis: BASIS_LINES (3 lines > 2)`, `basis/account: UI_ZONE`, `line 7: FONT_FALLBACK (Noto Color Emoji)` 총 9건, MP4는 그대로 쓰이고 rc=0. 같은 원고 `--strict`는 rc=3. `ok-layout.json --strict`는 경고 0건, rc=0. 글자는 줄이거나 자르지 않고 원고 그대로 그림(테스트 `test_text_is_never_truncated_or_shrunk` 통과) |
| 5 | 렌더된 MP4를 ffprobe 검사하면 1080×1920·30fps·H.264 yuv420p·AAC·faststart 충족 여부가 항목별로 확인 | ✓ VERIFIED | `python3 tools/specprobe.py 2026/reels/*.mp4`: 11개 모두 `spec: PASS 9/9`, FAIL 0줄, rc=0. 음성 시료(scratch): moov가 뒤에 있는 MP4는 `FAIL faststart`만, 720x1280/24fps/yuv444p/무음은 size·fps·pix_fmt·profile·audio를 각각 FAIL, 비MP4 파일은 9항목 전부 `측정 불가`로 FAIL(PASS 아님), 종료 코드 1. `reel.py` 렌더마다 stderr에 항목별 보고와 `spec: PASS 9/9`를 출력 |

**Score:** 5/5 truths verified (behavior-unverified 0건)

### Plan must_haves 보조 확인 (주요 항목)

| Truth | Status | Evidence |
|-------|--------|----------|
| tax-deduction 재렌더 stdout `duration=26.1s cover_ms=1250`, 781프레임, 프레임별 SSIM ≥ 0.98 | ✓ | 직접 재렌더 후 별도 ffmpeg ssim: 781/781, 최소 0.993194 |
| 고정 Playwright 1.63.0, 번들 폰트만 사용, 폰트 로드 실패 시 exit 2·MP4 없음 | ✓ | `requirements.txt`=`playwright==1.63.0`. 복사본에서 Black 폰트를 지우고 `reel.py` 실행: `렌더 환경 오류: 폰트 900 (NotoSansKR-Black.otf) 로드 실패 ... 시스템 폰트로 대체하지 않고 중단합니다`, rc=2, MP4 없음 |
| 번들 폰트 sha256이 `constants.FONT_SHA256`·`fonts/README.md`와 일치 | ✓ | `sha256sum` 3개 값이 constants와 README 표에 모두 같음. OFL.txt 포함 |
| 허용되지 않은 마크업·없는 파일·잘못된 JSON은 Korean 메시지와 exit 1, 브라우저·MP4 없음 | ✓ | `<img ...>` 원고 `원고 오류: scene 1 line 2: 허용되지 않은 마크업`, rc=1, 출력 폴더 비어 있음. 없는 파일과 깨진 JSON도 rc=1 |
| `.gitignore`가 drafts·`__pycache__`·`*.pyc`를 제외하고 게시된 릴스는 추적 유지 | ✓ | `git check-ignore -v`로 두 경로 확인, `git ls-files 2026/reels`에 MP4 추적 중 |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/requirements.txt` | Playwright 고정 | ✓ VERIFIED | `playwright==1.63.0` 1줄, ASCII |
| `tools/fonts/*.otf`, `OFL.txt`, `README.md` | 번들 폰트와 출처·라이선스 | ✓ VERIFIED | 400/700/900 세 파일, sha256 일치 |
| `tools/reelkit/{constants,browser,timeline,layout,render,encode,spec,specprobe,doctor,golden}.py`, `templates/frame.html` | 렌더 패키지 | ✓ VERIFIED | 전부 실질 구현이며 CLI에서 import되어 실행됨 |
| `tools/{reel,doctor,golden,specprobe}.py` | CLI 진입점 | ✓ VERIFIED | 모두 직접 실행해 동작 확인 |
| `.claude/hooks/session-start.sh` | 핀 설치 + doctor 요약 | ✓ VERIFIED | 실행해 확인 (위 1번). 기존 GSD·agent-browser 단계는 그대로 |
| `tools/tests/*` (5 파일, fixtures, manifest) | 시험과 기준 목록 | ✓ VERIFIED | 비골든 72개 시험 직접 실행 OK(51.9초). 골든은 `tools/golden.py`로 따로 실행해 PASS |
| `tools/README.md` | 명령 안내 | ✓ VERIFIED | doctor·reel·specprobe·golden, 종료 코드, 기본 legacy·새 릴스는 `--layout new` 명시 |
| `.gitignore` | 초안·중간 산출물 제외 | ✓ VERIFIED | 5개 규칙 |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `reel.py` | `render.render_reel` | import와 호출, stdout 줄 | ✓ WIRED |
| `render.py` | `browser.font_problems` | 첫 스크린샷 전 `_open_checked_page` (폰트 제거 실험으로 실제 중단 확인) | ✓ WIRED |
| `render.py` | `specprobe.probe` | 인코딩 직후, `RenderResult.spec_checks` → stderr 보고 → exit 4 | ✓ WIRED |
| `render.py` | `layout.evaluate_layout` / `MEASURE_JS` / `platform_fonts` | 새 배치 장면별 측정, bad-layout 실행으로 확인 | ✓ WIRED |
| `session-start.sh` | `tools/doctor.py --quiet` | 훅 실행 시 한 줄 출력 확인 | ✓ WIRED |
| `golden.py` | `render_reel` + manifest | 10편 재렌더·비교 실행 확인 | ✓ WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real Data | Status |
|----------|------|--------|-----------|--------|
| golden 기준 목록 | frames·boundaries·sha256 | 커밋된 MP4에서 ffprobe/ffmpeg로 추출 (`build_manifest`는 렌더러를 호출하지 않음) | 예, 직접 재계산해 일치 | ✓ FLOWING |
| 레이아웃 경고 | 줄 수·경계 | 브라우저 `Range.getClientRects` 측정 | 예, bad-layout에서 실측값 출력 | ✓ FLOWING |
| 규격 보고 | 항목별 값 | `ffprobe` JSON + MP4 최상위 atom 순회 | 예 | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 사전 점검 | `python3 tools/doctor.py` | 6/6 정상, rc=0 | ✓ PASS |
| 10편 회귀 | `python3 tools/golden.py` | `golden: PASS 10/10 (재현 불가 1)`, rc=0 | ✓ PASS |
| 규격 검사 | `python3 tools/specprobe.py 2026/reels/*.mp4` | 11×`PASS 9/9`, rc=0 | ✓ PASS |
| 새 배치 경고 | `reel.py bad-layout.json OUT --layout new [--strict]` | 경고 9건, rc=0 / `--strict` rc=3 | ✓ PASS |
| 단위 시험 | `python3 -m unittest discover -s tools/tests -p 'test_[dlsp]*.py'` | 72 tests OK | ✓ PASS |
| 설치 없는 렌더 | 빈 사용자 site로 `reel.py` tax-deduction | `duration=26.1s cover_ms=1250`, 781프레임, SSIM 최소 0.9932 | ✓ PASS |

### Probe Execution

SKIPPED: 이 단계는 `scripts/*/tests/probe-*.sh` 형식 프로브를 선언하지 않았다(검증은 doctor·golden·specprobe·unittest로 수행).

### Requirements Coverage

PLAN frontmatter의 requirements: 01-01 [ENV-02, ENV-03], 01-02 [ENV-02, ENV-03], 01-03 [ENV-04, ENV-05, ENV-06], 01-04 [ENV-01, ENV-02, ENV-03]. 합집합 = ENV-01~06, REQUIREMENTS.md의 Phase 1 매핑 6개와 동일. 고아 요구사항 없음.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ENV-01 | 01-04 | 사전 점검 명령 하나, 실패 시 원인 | ✓ SATISFIED | doctor 정상·실패 양쪽 실행 확인 |
| ENV-02 | 01-01, 01-02, 01-04 | 추가 설치 없이(고정 Playwright, 저장소 폰트) 렌더 | ✓ SATISFIED | 핀 설치 경로와 무설치 경로 모두 실행, 번들 폰트 로드 확인 |
| ENV-03 | 01-01, 01-02, 01-04 | 10편 회귀, 1편 재현 불가 | ✓ SATISFIED | golden 10/10 + 재현 불가 1, manifest 독립 재계산 |
| ENV-04 | 01-03 | 근거·계정명이 UI 밖, 36px 이상 | ✓ SATISFIED (실기기 보정 human) | 오버레이 이미지, MP4 프레임 픽셀, 10편 측정 |
| ENV-05 | 01-03 | 넘침·깨짐·침범 경고와 오버레이 | ✓ SATISFIED | bad-layout 9건 경고, 오버레이 PNG |
| ENV-06 | 01-03 | 업로드 규격 ffprobe 검사 | ✓ SATISFIED | 11편 PASS, 음성 시료 FAIL |

REQUIREMENTS.md 체크박스와 Traceability 표는 6개 모두 Complete로 코드 증거와 일치한다.

### Anti-Patterns Found

`tools/`, `.claude/hooks/`, `.gitignore`에서 TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER 표지 0건(OFL.txt 제외 검색). 빈 구현이나 하드코딩된 빈 데이터 없음.

### 코드 리뷰(01-REVIEW.md) 열린 항목 재확인

리뷰는 critical 0, warning 6, info 6이며 처분 장부에는 12건 모두 `open`이다. 이 중 2건을 직접 재현했고, 어느 것도 완료 기준 5개를 깨지는 않는다. 아래 경고는 Phase 2 이전에 처분(수정 또는 연기)을 권한다.

| ID | 판단 | 비고 |
|----|------|------|
| WR-01 | 경고 (재현됨) | 출력 경로가 폴더이면 `CalledProcessError` 전체 트레이스백과 종료 코드 1. README는 1을 "원고 오류"로 정의하므로 Phase 2 자동화가 환경 오류를 원고 오류로 오분류. ffmpeg가 최종 경로에 바로 써서 기존 MP4를 깨뜨릴 수 있음 |
| WR-02 | 경고 | `reel.py` 최상단 `except ImportError`가 패키지 내부 버그도 "playwright 미설치"로 표시 |
| WR-03 | 경고 | golden에서 ffmpeg/ffprobe 예외 한 건이 전체 보고를 중단 (렌더 예외만 잡음) |
| WR-04 | 경고 (계산 확인) | 첫 장면이 4줄·10줄이면 `cover_ms`가 2949·8049로 1ms 짧음. 기존 `reel.py` 공식과 동일한 절삭이라 기존 10편과는 일치(10편의 첫 장면은 2줄 또는 3줄이라 해당 없음). 새 릴스의 표지 시점에만 영향 |
| WR-05 | 경고 | 훅의 핀 파싱이 CRLF·공백에 취약하고 PEP 668 환경 대응 없음. 현재 `requirements.txt`는 ASCII 1줄이라 지금은 영향 없음 |
| WR-06 | 경고 | doctor 하위 프로세스에 타임아웃 없음 |
| IN-01~06 | 정보 | 열린 상태. IN-04(`SMALL` 검사 도달 불가)와 IN-05(doctor의 ffmpeg 시험이 실제 인코딩 경로와 다름)는 이후 단계에서 처리 가능 |

### 추가 관찰 (경고 수준, 차단 아님)

1. **회귀 허용 오차가 푸터 글씨 변화에 둔감하다.** 복사본에서 legacy 근거 글씨를 30px에서 34px로 키워도 golden은 SSIM 최소 0.9880으로 PASS한다. 하단 근거·계정명은 면적이 작아 프레임 전체 SSIM(임계 0.98)에 거의 반영되지 않는다. 구조(프레임 수·경계·길이)와 큰 배치 변화는 잘 잡지만(gap 40→30은 FAIL), 근거 줄 위치·크기를 지키는 용도로는 약하다. 근거 표기 위치를 legacy 재현에서 지켜야 한다면 푸터 영역만 따로 비교하는 보조 검사를 Phase 2 이전에 고려할 것.
2. **`reel.py`의 기본 배치는 legacy**이다(기존 사용법 보존, D-05). 새 릴스를 `--layout new` 없이 만들면 근거가 하단 150px·30px에 놓여 ENV-04를 만족하지 못한다. README에는 "새 릴스는 new 로 만든다"고 명시되어 있으나, Phase 2·3의 초안 생성 경로가 반드시 `--layout new`를 쓰도록 연결해야 한다.
3. golden의 `cover_ms` 기준값은 커밋된 MP4가 아니라 `timeline.cover_ms(spec)`로 계산된다(MP4에서는 추출 불가). 기존 `reel.py` 공식(`int((LINE*(first-1)+0.4)*1000)`)과 글자 그대로 같음을 `git show 10d1b55^:tools/reel.py`로 확인했다.

### Human Verification Required

### 1. 안전영역 상수의 실기기 보정

**Test:** `python3 tools/reel.py <원고> <출력>.mp4 --layout new`로 만든 릴스를 인스타그램 앱에 비공개로 올려, 장면 중 줄 수가 가장 많은 장면(안전영역 미리보기 `*.safe-sNN.png`의 두 번째 장)에서 근거와 @kiwoom.mentor가 캡션·좋아요·공유 버튼 등 UI에 가려지는지 본다.
**Expected:** 가려지지 않는다. 가려지면 `tools/reelkit/constants.py`의 `SAFE` 값만 조정하고 overlay 미리보기로 다시 확인한다.
**Why human:** 현재 값(top 270, warn_y 1250, bottom_ui 450, right 150)은 조사 중간 보수값이고 top 270은 research 가정 A1로 검증 전이다. 실제 인스타그램 UI 영역은 실기기에서만 확인된다. ROADMAP의 Owner input 항목이다.

### Gaps Summary

차단 gap 없음. 5개 완료 기준과 ENV-01~06이 모두 코드와 직접 실행 결과로 확인되었다. 사람 확인 1건(실기기 안전영역 보정)이 남아 `human_needed`다. 리뷰 경고 WR-01~WR-06과 위 관찰 1·2는 Phase 2 시작 전에 처분하기를 권한다.

---

_Verified: 2026-10-28T22:10:00Z_
_Verifier: Claude (gsd-verifier)_
