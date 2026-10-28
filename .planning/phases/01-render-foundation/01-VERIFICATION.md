---
phase: 01-render-foundation
verified: 2026-10-28T23:10:00Z
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
  - "tools/tests/test_encode.py"
  - "tools/tests/test_golden.py"
  - "tools/tests/test_golden_failures.py"
  - "tools/tests/test_layout.py"
  - "tools/tests/test_session_hook.py"
  - "tools/tests/test_spec.py"
  - "tools/tests/test_specprobe.py"
  - "tools/tests/test_timeline.py"
covered_digest: "v4:sha256:9464194e82c2ee1251e8f50bda086bd1a9a14014a1182beb63a62bd6ead85d4c"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "안전영역 상수(SAFE: top 270, warn_y 1250, bottom_ui 450, right 150)를 실기기 비공개 업로드로 보정"
    expected: "새 배치(--layout new)로 만든 릴스를 인스타그램 앱에 비공개로 올렸을 때 근거 표기와 @kiwoom.mentor가 하단 UI(캡션·버튼)와 우측 버튼에 가려지지 않는다. 가려지면 tools/reelkit/constants.py의 SAFE 값만 바꾸고 overlay 미리보기로 다시 확인"
    why_human: "상수는 조사 중간 보수값(270은 research 가정 A1, 검증 전)이다. 코드는 이 값 기준의 위치만 검증할 수 있고 실제 인스타그램 UI 가림 여부는 실기기에서만 확인된다 (ROADMAP Owner input, CONTEXT D-03). 01-UAT.md 항목 1이 pending 상태로 남아 있다"
---

# Phase 1: 렌더 기반 고정 (Render Foundation) 검증 보고서

**Phase Goal:** 새 클라우드 세션에서 추가 설치 없이 기존 형식 그대로 릴스를 다시 만들 수 있다. 새 릴스의 근거 표기와 계정명은 인스타그램 UI에 가려지지 않는다. 화면 깨짐과 업로드 규격 위반은 렌더 단계에서 바로 드러난다.
**Verified:** 2026-10-28T23:10:00Z
**Status:** human_needed
**Re-verification:** 예 — 이전 보고서가 두 차례 코드 리뷰 수정(WR-01~06, CR-01·WR-07~09) 뒤에 낡아서 다시 검증

## 요약

이전 보고서(c9758e9 시점) 이후 바뀐 소스는 13개 파일이다(`.claude/hooks/session-start.sh`, `tools/reel.py`, `reelkit/{encode,golden,doctor,timeline}.py`, README·golden.py 문구, 시험 5개). 배치·렌더·폰트·규격 검사(`layout.py`, `render.py`, `browser.py`, `specprobe.py`, `constants.py`, `spec.py`)와 게시된 `2026/` 파일은 이전 검증 뒤로 바뀌지 않았다(`git diff --stat c9758e9 HEAD`, `git diff 313d420 HEAD -- 2026`가 비어 있음). SUMMARY의 주장은 근거로 쓰지 않고 전부 직접 다시 실행했다.

결과: ROADMAP 완료 기준 5개와 ENV-01~06은 수정 이후에도 모두 유지된다. 회귀 없음. 전체 시험 135개 통과, `tools/golden.py` 10/10 통과(재현 불가 1), `doctor` 6/6 정상, 11개 MP4 규격 검사 전부 `PASS 9/9`다. 리뷰 수정이 "사람 확인 필요"로 남겨 둔 WR-05·WR-07·WR-08은 실제 pip와 실제 렌더 오류로 직접 재현해 확인했다(아래). 차단 gap은 없다. 남은 것은 사람이 해야 하는 안전영역 상수의 실기기 보정 1건(이월)이라 상태는 `human_needed`다.

## Goal Achievement

### Observable Truths (ROADMAP 완료 기준)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 사전 점검 명령 하나로 Chromium 실행·번들 한글 폰트 로드·ffmpeg 확인. 모두 정상이면 종료 코드 0, 하나라도 실패하면 원인 메시지 | ✓ VERIFIED | `python3 tools/doctor.py`: 6개 항목 `[정상]`, rc=0. `--json` `ok:true`. `--quiet` 한 줄, rc=0. 실패 경로는 이전 검증에서 확인했고(Black 폰트 제거 시 `[실패] font-files`·`font-load`, rc=1) 코드가 바뀐 부분은 `doctor._run`의 30초 타임아웃·127 변환뿐이며 `test_doctor.py` 시험이 통과한다. 이번에 훅을 빈 `PYTHONUSERBASE`로 실행: 실제 pip가 playwright 1.63.0을 설치하고 정상 한 줄(stdout 1줄), rc=0. 두 번째 실행은 설치 없이 정상 한 줄, stderr 0바이트 |
| 2 | 기존 10편 회귀 시험이 편마다 길이·장면 경계·표지 시점·화면 일치를 보고. 원고 없는 MP4는 "재현 불가" | ✓ VERIFIED | `python3 tools/golden.py` 직접 실행(1분 24초): 10편 PASS, frames 730/705/705/781/654/705/756/756/730/654가 기준과 동일, 경계 19/18/18/21/16/18/20/20/19/16 일치, SSIM 최소 0.9923(rate-secret-3)~0.9985, `재현 불가 2026-10-19-savings-interest (원고 없음, D-06)`, 마지막 줄 `golden: PASS 10/10 (재현 불가 1)`, rc=0. SSIM 임계값 0.98과 `manifest.json`은 수정 대상이 아니며 변경 없음(`git status` 깨끗) |
| 3 | 새 릴스에서 근거와 @kiwoom.mentor가 하단 UI 영역 밖에 36px 이상으로 표시. 오버레이 미리보기로 확인 가능 | ✓ VERIFIED (실기기 보정은 human) | `reel.py tax-deduction.json OUT --layout new` 직접 렌더: 오버레이 `tax.safe-s05.png`를 눈으로 확인. 근거(`100만 원 공제 예시 · 지방소득세 포함`)와 `@kiwoom.mentor`가 y=270~1250 초록 띠 안쪽, 빨간 UI 띠(y≥1470)와 우측 150px 띠 밖. 경고 3건은 모두 본문 줄 WRAP이고 근거·계정명을 가리키는 경고는 0건. 단위 시험도 10편 모두 근거·계정명 경고 0건을 확인(시험 출력 집계) |
| 4 | 줄 넘침·줄바꿈 깨짐·안전영역 침범 원고는 해당 장면과 줄을 가리키는 경고 | ✓ VERIFIED | `bad-layout.json --layout new`: 9건 — `scene 1 line top: TOP`, `line 1: WRAP (4 lines)`, `line 1: TOP`, `line 2: RIGHT (right=1609 > 930)`, `line 7: WARN_Y`, `line basis: BASIS_LINES (3 lines > 2)`, `basis: UI_ZONE`, `account: UI_ZONE`, `line 7: FONT_FALLBACK (Noto Color Emoji)`. 기본은 rc=0(MP4 생성), `--strict`는 rc=3. `ok-layout.json --strict`는 경고 0건, rc=0 |
| 5 | 렌더된 MP4를 ffprobe 검사하면 1080×1920·30fps·H.264 yuv420p·AAC·faststart 충족 여부가 항목별로 확인 | ✓ VERIFIED | `python3 tools/specprobe.py 2026/reels/*.mp4`: 11개 모두 `spec: PASS 9/9`, rc=0. 이번 렌더 산출물(bad·ok·tax)도 전부 `spec: PASS 9/9`. 음성 시료(faststart 없음, 720x1280 등)가 항목별 FAIL이 되는 시험(`test_specprobe.py`)이 통과 |

**Score:** 5/5 truths verified (behavior-unverified 0건)

### 리뷰 수정(두 차례) 직접 재확인

코드 리뷰 수정 중 "사람 확인 필요"로 표시된 항목은 시험이 모의 객체에 의존했기 때문이다. 아래는 모의 없이 실제 도구로 재현한 결과이고, 수정 전 코드에 새 시험을 돌려 시험이 실제로 결함을 잡는지도 확인했다(별도 사본, 원본 수정 없음).

| 항목 | 직접 재현 | 결과 |
|------|-----------|------|
| CR-01 (`format_report` KeyError) | 수정 전 `golden.py`(2d49a7c^)에 새 `PartialDetailsReport` 3개 시험 실행 | 3개 모두 `KeyError: 'boundaries'`로 실패 → 시험이 결함을 잡음. 현재 코드는 통과. `_fmt_line`이 있는 항목만 출력 |
| WR-07 (환경 오류를 릴스 FAIL 10줄로 보고) | (a) 사본에서 Black 폰트를 지우고 `golden.py --only` 3편 실행 (b) `playwright` import를 막고 `golden.main(['--only', ...])` | (a) `golden 환경 오류: FontLoadError: 폰트 900 (NotoSansKR-Black.otf) 로드 실패 ...` 한 번, rc=2, FAIL 줄 없음 (b) `golden 환경 오류: playwright 미설치 ...`, rc=2. 수정 전 코드(5096025^)는 새 시험 8개가 실패 |
| WR-08 (pip 0 종료인데 고정 버전이 가려짐) | `PYTHONPATH`에 가짜 `playwright-1.99.0.dist-info`를 두고 빈 user site에서 훅 실행. 실제 pip는 1.63.0을 user site에 설치(`playwright-1.63.0.dist-info` 확인)했지만 가려져 import 버전은 1.99.0 | 훅 rc=0, doctor 정상 한 줄, stderr에 `playwright 1.63.0 설치 실패 — ...` 안내, 실패 표시 파일 `.reelkit-pw-install-failed-1.63.0` 생성. 두 번째 실행은 stderr 0바이트(pip 재시도 없음). 수정 전 훅(2ec89fd^)은 새 시험이 실패 |
| WR-05 (훅의 pip 재시도·표시 파일) | `PIP_NO_INDEX=1`과 빈 user site로 실제 pip 실패 유도 | pip 두 번 시도(두 번째는 `PIP_BREAK_SYSTEM_PACKAGES=1`) 후 실패 안내, 표시 파일 생성, rc=0. 훅 stdout은 doctor 한 줄뿐이며 시스템 playwright 1.64.1 + `/opt/pw-browsers/chromium` 폴백으로 `정상 ... 경고 2건`. 두 번째 실행 stderr 0바이트 |
| WR-01·02 (`reel.py` 실패 분류) | 출력 경로를 폴더로 지정, PATH에서 ffmpeg 제거, playwright import 차단 | 폴더: `렌더 환경 오류: 출력 파일을 쓸 수 없습니다: ... (Is a directory)` rc=2. ffmpeg 없음: `렌더 환경 오류: ffmpeg 를 실행하지 못했습니다`, rc=2, 이미 있던 MP4의 sha256 불변, `.part.mp4` 잔여물 없음. playwright 차단: `playwright 미설치: ...` rc=2, MP4 없음 |
| WR-04 (`cover_ms` 반올림) | `timeline.cover_ms`는 `round(...)`. 기존 10편의 cover_ms는 golden에서 기준과 일치(1250, 한 편 2100) | `test_timeline.py`가 1~12줄 첫 장면(2950, 8050 포함)을 검증하고 통과 |
| WR-06·09 | `doctor._run` 타임아웃, golden 사전 읽기 보호 | 코드 확인, `test_doctor.py`·`test_golden_failures.py` 통과 |

참고(환경 관찰, 코드 결함 아님): 검증 중 `TMPDIR`를 매우 긴 경로로 두고 훅을 실행했더니 Chromium 폴백 실행이 실패해 doctor가 `실패 2건`을 정확히 보고했다(소켓 경로 길이 제한 추정). 짧은 `TMPDIR`에서는 정상이었다. 훅의 실패 표시 파일은 `$TMPDIR`에 만들어지므로(리뷰 IN-08) 긴 `TMPDIR`를 쓰는 환경에서는 doctor 메시지를 보고 원인을 확인하면 된다.

### Plan must_haves 보조 확인 (주요 항목)

| Truth | Status | Evidence |
|-------|--------|----------|
| tax-deduction 재렌더 stdout `duration=26.1s cover_ms=1250`, 781프레임, 프레임별 SSIM ≥ 0.98 | ✓ | golden이 781/781, SSIM 최소 0.9932. `--layout new` 재렌더도 stdout 줄 동일 |
| 고정 Playwright 1.63.0, 번들 폰트만 사용, 폰트 로드 실패 시 exit 2·MP4 없음 | ✓ | `requirements.txt`=`playwright==1.63.0`(doctor `고정 버전`). Black 폰트를 지운 사본의 렌더는 `FontLoadError`로 중단(golden 경로 rc=2) |
| prohibition: 번들 폰트가 아닌 폰트로 릴스를 만들지 않는다 | ✓ (test 계층) | `_open_checked_page`가 첫 스크린샷 전에 `font_problems`를 검사해 `FontLoadError`를 낸다. 위 재현에서 시스템 폰트 대체(`'Liberation Serif', 'Inter', 'WenQuanYi Zen Hei'`)를 감지하고 중단 |
| prohibition: 근거·계정명을 자르거나 줄이지 않는다 | ✓ (test 계층) | `test_text_is_never_truncated_or_shrunk` 포함 135개 시험 통과. 오버레이에서 원고 문구가 그대로 그려짐 |
| prohibition: 측정 불가 항목을 PASS로 보고하지 않는다 | ✓ (test 계층) | `test_specprobe.py` 통과(비MP4는 9항목 전부 측정 불가 FAIL) |
| prohibition: 게시된 MP4·원고를 바꾸지 않고 SSIM 0.98을 낮추지 않는다 | ✓ (test 계층) | `git diff 313d420 HEAD -- 2026`이 비어 있음. `golden.SSIM_MIN = 0.98`, manifest는 변경 없음 |
| prohibition: doctor가 폰트 실패에도 정상이라고 하지 않는다 | ✓ (test 계층) | `summarize`가 실패 1건이라도 있으면 정상 문구를 내지 않음. 이전 검증의 폰트 제거 실험과 `test_doctor.py` |
| `.gitignore`가 drafts·`__pycache__`·`*.pyc`를 제외하고 게시된 릴스는 추적 유지 | ✓ | `git ls-files 2026/reels`에 MP4 추적. 시험 실행 후 `git status` 깨끗, `tools/`·`.claude/`에 `__pycache__` 없음 |

prohibition 6건은 모두 선언된 `verification: test` 계층이며 위 시험이 강제 장치로 이미 연결되어 있다. judgment 계층 prohibition은 없다.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/requirements.txt` | Playwright 고정 | ✓ VERIFIED | `playwright==1.63.0` |
| `tools/fonts/*.otf`, `OFL.txt`, `README.md` | 번들 폰트와 출처·라이선스 | ✓ VERIFIED | doctor `3/3 sha256 일치` |
| `tools/reelkit/*.py`, `templates/frame.html` | 렌더 패키지 | ✓ VERIFIED | 전부 실질 구현, CLI에서 import되어 실행됨. 이번에 수정된 `encode.py`(임시 파일 후 교체, `EncodeError`)·`golden.py`(`GoldenEnvError`)·`timeline.py`도 실행 확인 |
| `tools/{reel,doctor,golden,specprobe}.py` | CLI 진입점 | ✓ VERIFIED | 모두 직접 실행 |
| `.claude/hooks/session-start.sh` | 핀 설치 + doctor 요약 | ✓ VERIFIED | 위 재현 참조. 기존 GSD·agent-browser·`AGENT_BROWSER_EXECUTABLE_PATH` 단계 유지 |
| `tools/tests/*` (9개 시험 파일, fixtures, manifest) | 시험과 기준 목록 | ✓ VERIFIED | `python3 -m unittest discover -s tools/tests` 135 tests OK (226초) |
| `tools/README.md` | 명령 안내 | ✓ VERIFIED | golden 종료 코드 2 설명이 WR-07에 맞게 갱신됨(66행) |
| `.gitignore` | 초안·중간 산출물 제외 | ✓ VERIFIED | 변경 없음 |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `reel.py` | `render.render_reel` + 예외 분류 | import·호출, `EncodeError`·`OSError`·`SubprocessError`·Playwright `Error`→2, `SpecError`→1 | ✓ WIRED (폴더 출력·ffmpeg 없음·playwright 차단으로 확인) |
| `render.py` | `browser.font_problems` | 첫 스크린샷 전 `_open_checked_page` | ✓ WIRED (폰트 제거 실험) |
| `render.py` | `encode.encode_concat` | `<out>.part.mp4` → `os.replace` | ✓ WIRED (기존 MP4 불변 확인) |
| `render.py` | `specprobe.probe` | 인코딩 직후, stderr 보고와 exit 4 | ✓ WIRED |
| `render.py` | `layout.evaluate_layout`/`MEASURE_JS` | 새 배치 장면별 측정 | ✓ WIRED (bad-layout 9건) |
| `session-start.sh` | `requirements.txt`, `doctor.py --quiet` | 핀 파싱 → pip → 설치 후 재확인 → doctor 한 줄 | ✓ WIRED (실제 pip로 확인) |
| `golden.py` | `render_reel` + `manifest.json` + `GoldenEnvError` | 10편 재렌더·비교, 환경 오류는 `main`이 rc=2 | ✓ WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real Data | Status |
|----------|------|--------|-----------|--------|
| golden 보고 | frames·boundaries·ssim | 새 렌더 MP4를 ffprobe/ffmpeg로 측정해 커밋된 MP4 기준과 비교 | 예 | ✓ FLOWING |
| 레이아웃 경고 | 줄 수·경계 | 브라우저 `Range.getClientRects` 측정 | 예 (실측값 출력) | ✓ FLOWING |
| 규격 보고 | 항목별 값 | `ffprobe` JSON + MP4 atom 순회 | 예 | ✓ FLOWING |
| `format_report` 부분 결과 | `details` 일부 키 | `check_reel` 판정 중단 시점까지 채워진 항목 | 예 (CR-01 시험 3개) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 전체 단위·골든 시험 | `python3 -m unittest discover -s tools/tests` | 135 tests OK | ✓ PASS |
| 10편 회귀 | `python3 tools/golden.py` | `golden: PASS 10/10 (재현 불가 1)`, rc=0 | ✓ PASS |
| 사전 점검 | `python3 tools/doctor.py` | 6/6 정상, rc=0 | ✓ PASS |
| 규격 검사 | `python3 tools/specprobe.py 2026/reels/*.mp4` | 11×`PASS 9/9`, rc=0 | ✓ PASS |
| 새 배치 경고 | `reel.py bad-layout.json OUT --layout new [--strict]` | 경고 9건, rc=0 / rc=3 | ✓ PASS |
| 새 배치 정상 원고 | `reel.py ok-layout.json OUT --layout new --strict` | 경고 0건, rc=0 | ✓ PASS |
| 훅 신규 설치·재실행 | 빈 `PYTHONUSERBASE`로 `session-start.sh` 두 번 | 1.63.0 설치, 정상 한 줄 / 두 번째 stderr 0 | ✓ PASS |
| 환경 오류 분류 | 폰트 제거·playwright 차단·폴더 출력·ffmpeg 제거 | 모두 rc=2, 한 줄 메시지 | ✓ PASS |

### Probe Execution

SKIPPED: 이 단계는 `scripts/*/tests/probe-*.sh` 형식 프로브를 선언하지 않았다(검증은 doctor·golden·specprobe·unittest로 수행).

### Requirements Coverage

PLAN frontmatter의 requirements: 01-01 [ENV-02, ENV-03], 01-02 [ENV-02, ENV-03], 01-03 [ENV-04, ENV-05, ENV-06], 01-04 [ENV-01, ENV-02, ENV-03]. 합집합 = ENV-01~06, REQUIREMENTS.md의 Phase 1 매핑 6개와 일치한다. 고아 요구사항 없음.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ENV-01 | 01-04 | 사전 점검 명령 하나, 실패 시 원인 | ✓ SATISFIED | doctor 정상 실행(rc=0), 실패 경로 시험, 훅 요약 한 줄 |
| ENV-02 | 01-01, 01-02, 01-04 | 추가 설치 없이(고정 Playwright, 저장소 폰트) 렌더 | ✓ SATISFIED | 핀 설치 경로·무설치 경로·가려진 설치 경로 모두 실제 실행, 번들 폰트 로드 확인 |
| ENV-03 | 01-01, 01-02, 01-04 | 10편 회귀, 1편 재현 불가 | ✓ SATISFIED | golden 10/10 + 재현 불가 1, 환경 오류는 별도 종료 코드 2 |
| ENV-04 | 01-03 | 근거·계정명이 UI 밖, 36px 이상 | ✓ SATISFIED (실기기 보정 human) | 오버레이 이미지 육안 확인, 경고 0건 |
| ENV-05 | 01-03 | 넘침·깨짐·침범 경고와 오버레이 | ✓ SATISFIED | bad-layout 9건 경고, 오버레이 PNG |
| ENV-06 | 01-03 | 업로드 규격 ffprobe 검사 | ✓ SATISFIED | 11편 + 새 렌더 3건 PASS, 음성 시료 시험 |

REQUIREMENTS.md 체크박스와 Traceability 표는 ENV-01~06 모두 Complete로 코드 증거와 일치한다. ROADMAP.md의 Phase 1 체크박스(`- [ ] **Phase 1`)와 상단 목록은 아직 미완료 표시이며 단계 완료 처리는 오케스트레이터 몫이다.

### Anti-Patterns Found

`tools/`, `.claude/hooks/`, `.gitignore`에서 TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER 표지 0건. 빈 구현이나 하드코딩된 빈 데이터 없음. 차단 수준 패턴 없음.

### 코드 리뷰 처분 상태 (경고, 차단 아님)

| 항목 | 상태 | 비고 |
|------|------|------|
| WR-01~06, CR-01, WR-07~09 | 코드에서 수정 확인 | 위 직접 재확인 표 참조 |
| `01-REVIEW-DISPOSITION.md` | ⚠️ 낡음 | CR-01·WR-07·WR-08·WR-09가 아직 `open`으로 기록됨(요약 `open: 13`). 실제로는 수정되어 `fixed`가 맞다. 장부만 갱신하면 되며 코드 차단 사항은 아니다 |
| IN-01~IN-06 | 열림(미처리) | 리뷰가 범위 밖으로 둠. IN-04(`SMALL` 검사 도달 불가), IN-05(doctor ffmpeg 시험이 실제 인코딩 경로와 다름), IN-06(훅의 `@latest` 설치가 `set -e` 아래에서 Phase 1 블록을 막을 수 있음)은 Phase 2 이전 처분 권장 |
| IN-07 | 열림 | `tools/reel.py` 독스트링 8행과 `tools/README.md` 27행의 종료 코드 2 설명이 ffmpeg 인코딩 실패·출력 쓰기 실패를 아직 나열하지 않는다(동작은 맞고 문서만 낡음). Phase 2 자동화가 이 계약을 읽으므로 갱신 권장 |
| IN-08, IN-09 | 열림 | 실패 표시 파일이 공유 `/tmp`에 있음(싱글 유저 컨테이너라 위험 낮음), 일부 시험 보완 여지 |

### 추가 관찰 (이월, 경고 수준, 차단 아님)

1. **회귀 허용 오차가 푸터 글씨 변화에 둔감하다.** (이전 검증에서 확인) legacy 근거 글씨를 30px에서 34px로 키워도 golden은 SSIM 최소 0.9880으로 PASS한다. 하단 근거·계정명은 면적이 작아 프레임 전체 SSIM(임계 0.98)에 거의 반영되지 않는다. 이번 수정은 이 부분을 건드리지 않았다. 근거 줄 위치·크기를 legacy 재현에서 지켜야 한다면 푸터 영역만 따로 비교하는 보조 검사를 Phase 2 이전에 고려할 것.
2. **`reel.py`의 기본 배치는 legacy**이다(기존 사용법 보존, D-05). 새 릴스를 `--layout new` 없이 만들면 ENV-04를 만족하지 못한다. Phase 2·3의 초안 생성 경로가 반드시 `--layout new`를 쓰도록 연결해야 한다.
3. golden의 `cover_ms` 기준값은 커밋된 MP4가 아니라 `timeline.cover_ms(spec)`로 계산된다(MP4에서는 추출 불가). WR-04 수정으로 `round()`를 쓰지만 기존 10편의 값은 그대로다(manifest 변경 없음).

### Human Verification Required

### 1. 안전영역 상수의 실기기 보정 (이월, 01-UAT.md 항목 1 pending)

**Test:** `python3 tools/reel.py <원고> <출력>.mp4 --layout new`로 만든 릴스를 인스타그램 앱에 비공개로 올려, 장면 중 줄 수가 가장 많은 장면(안전영역 미리보기 `*.safe-sNN.png`의 두 번째 장)에서 근거와 @kiwoom.mentor가 캡션·좋아요·공유 버튼 등 UI에 가려지는지, 상단 라벨이 상태 표시줄에 가려지는지 본다. iOS·Android 모두.
**Expected:** 가려지지 않는다. 가려지면 `tools/reelkit/constants.py`의 `SAFE` 값만 조정하고 overlay 미리보기로 다시 확인한다.
**Why human:** 현재 값(top 270, warn_y 1250, bottom_ui 450, right 150)은 조사 중간 보수값이고 top 270은 research 가정 A1로 검증 전이다. 실제 인스타그램 UI 영역은 실기기에서만 확인된다. ROADMAP의 Owner input 항목이다.

### Gaps Summary

차단 gap 없음. 5개 완료 기준과 ENV-01~06이 두 차례 리뷰 수정 이후에도 코드와 직접 실행 결과로 확인되었다. 사람 확인 1건(실기기 안전영역 보정)이 남아 `human_needed`다. 권장 후속: `01-REVIEW-DISPOSITION.md`를 갱신해 CR-01·WR-07~09를 `fixed`로 기록하고, IN-07(종료 코드 문서)·IN-04~06을 Phase 2 시작 전에 처분하며, 위 관찰 1·2를 Phase 2 계획에 반영할 것.

---

_Verified: 2026-10-28T23:10:00Z_
_Verifier: Claude (gsd-verifier)_
