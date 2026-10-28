# Phase 1: 렌더 기반 고정 (Render Foundation) - Research

**Researched:** 2026-10-28
**Domain:** Python + Playwright(Chromium) + ffmpeg 릴스 렌더러 고정화 (재현 가능한 환경, golden 회귀 시험, 안전영역/레이아웃 측정, 업로드 규격 검사)
**Confidence:** HIGH (모든 핵심 수치는 이 세션 컨테이너에서 실측한 spike 결과) / MEDIUM (Instagram 안전영역 픽셀 — 사람이 실기기에서 보정)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)
- 진행 막대 위치 이동 — 실기기 시험에서 문제가 확인될 때만(이 단계 범위 밖의 결정이 아니라 조건부 후속 조치)
- 기존 10편을 새 배치로 다시 만들기 — 하지 않기로 결정. 필요해지면 별도 작업
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENV-01 | 사전 점검 명령 하나로 Chromium 실행·한글 폰트 로드·ffmpeg 사용 가능 여부 확인, 실패 시 원인 메시지 | §Doctor / Playwright 설치 경로: `goto(file://)` + `FontFace.status` + CDP `CSS.getPlatformFontsForNode`로 폰트 조용한 대체까지 탐지(0.83 s 실측). 실행 경로 폴백 체인 |
| ENV-02 | 새 세션에서 추가 설치 없이(고정 Playwright, 저장소 포함 OFL 폰트) 렌더 | §Playwright 설치 경로(`pip install --user playwright==1.63.0`, 사용자 site가 시스템 1.64.1보다 우선함을 실측), §폰트 벤더링(파일 3개, sha256 고정) |
| ENV-03 | 기존 10편 재렌더 시 길이·장면 경계·표지 시점 동일, 화면은 허용 오차 내 일치. 원고 없는 MP4는 "재현 불가" | §Golden 회귀 설계: 10/10 편이 프레임 수·길이·경계 정확 일치, 프레임별 SSIM ≥ 0.9923, 임계값 권고 |
| ENV-04 | 새 릴스의 근거·계정명은 하단 UI 밖, 36px 이상 | §새 배치(D-01~D-03): 안전영역 안에 중앙 정렬된 스택, 10편 장면 70개 전부 y ≤ 1216 실측 |
| ENV-05 | 줄 넘침·줄바꿈 깨짐·안전영역 침범 경고 + 오버레이 미리보기 | §레이아웃 측정(`Range.getClientRects` 줄 수 세기), 오버레이 PNG 구현 |
| ENV-06 | MP4가 업로드 규격 충족, ffprobe로 확인 | §ffprobe 규격 검사(stdlib, faststart는 MP4 atom 순서 파싱): 기존 11편 전부 PASS, 불량 샘플 항목별 FAIL 확인 |
</phase_requirements>

## Summary

이 단계의 위험은 "새 세션에서 렌더가 조용히 달라진다"와 "회귀 기준이 흔들린다" 두 가지다. 컨테이너에서 실측한 결과, 저장소의 번들 폰트(Noto Sans KR 서브셋 OTF 3종)를 `goto(file://…)`로 로드하면 기존에 게시된 MP4 10편과 **프레임 수·길이·장면 경계가 10편 모두 정확히 같고**, 디코드 프레임은 프레임별 SSIM 최소 0.9923(오탐 대조군은 0.951 이하)으로 일치한다. 폰트가 틀리면(WenQuanYi 대체) SSIM이 0.909~0.961로 떨어져 충분히 구분된다. 같은 입력의 두 번 렌더는 바이트까지 같고(같은 머신), headless-shell과 풀 Chrome의 출력도 같다. 단 x264 스레드 수가 다르면 바이트는 달라지지만(디코드 SSIM 1.0) 해시 비교는 금물이다.

**가장 중요한 발견(플래너가 설계에 반영해야 함):** 현재 HEAD의 `tools/reel.py`가 만드는 영상은 커밋된 MP4와 **`<s>` 줄에서 다르다.** HEAD는 `<s>`를 100px 줄 안의 인라인 `<span style="font-size:52px…">`로 만들어 줄 상자가 130px로 유지되지만, 커밋된 MP4들은 `<s>`가 블록(`display:block`)처럼 렌더되어 있다(52px 줄 상자). 진짜 Noto Sans CJK KR(OTF)을 fontconfig로 깔아서 HEAD 코드를 돌려도 같은 차이가 나므로 폰트 문제가 아니다. `<span>`에 `display:block`만 추가하면 10편 모두 일치한다. 따라서 legacy 경로의 정의는 "HEAD `reel.py`"가 아니라 **"커밋된 MP4를 재현하는 렌더러"**여야 하고, golden 기준은 **커밋된 MP4**다(§Golden 회귀 설계).

두 번째로, 이 세션 이미지에는 `playwright 1.64.1`이 이미 시스템에 깔려 있다(조사 STACK의 "미설치"와 다름). 1.64.1 기본 `launch()`는 Chromium 1248을 찾다 실패한다. 이미지가 바뀌어도 동작하도록 훅은 "현재 버전 ≠ 1.63.0이면 `pip install --user playwright==1.63.0`"으로 고정하고(사용자 site가 우선, 실측), 사전 점검은 기본 launch가 실패하면 `executable_path` 폴백으로 내려간다.

**Primary recommendation:** (1) `tools/fonts/`에 업스트림 OTF 3종+OFL을 무수정으로 넣고 템플릿은 `goto(file://)`로 연다. (2) legacy 렌더러는 ffmpeg concat+`fps=30` 경로를 그대로 쓰되 `<s>`를 블록으로 만들어 커밋 MP4와 대조한다. (3) 비교는 "구조는 정확 일치 + 프레임별 SSIM ≥ 0.98"로 한다. (4) 새 배치는 안전영역 박스(y 270~1250) 안에 [상단 라벨, 본문, 근거 36px, 계정 36px]를 중앙 정렬한 스택으로 만들고, 브라우저 안에서 줄 수·경계를 측정해 경고한다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 환경 사전 점검 (Chromium·폰트·ffmpeg) | Python CLI (`doctor`) | SessionStart 훅 (호출만) | 로직은 CLI 한 곳, 훅은 얇게 호출. 같은 명령을 직접 실행 가능해야 함(D-07) |
| Playwright 버전 고정 설치 | SessionStart 훅 + `tools/requirements.txt` | doctor (불일치 보고) | 설치는 세션 시작 시점 한 번, 검증은 doctor |
| 폰트 제공·로드 | 저장소 정적 파일 (`tools/fonts/`) | 브라우저(`@font-face`, `file://`) | 시스템 폰트 의존 제거. 로드 확인은 브라우저 안에서 |
| 레이아웃(legacy/new) 생성 | Python 렌더러 → HTML | 브라우저(CSS 레이아웃) | 줄바꿈·셰이핑은 브라우저가 계산 |
| 줄 넘침·안전영역 측정 | 브라우저(JS `getClientRects`) | Python(판정·경고 출력) | 실제 레이아웃 결과는 브라우저만 안다. 판정 상수는 Python 한 곳 |
| 프레임 인코딩 | ffmpeg (concat + `fps=30`) | Python(인자 조립) | legacy 경계가 ffmpeg 반올림에 의존함(§Pitfall 3) |
| 규격 검사 (ENV-06) | ffprobe + Python(atom 파싱) | — | faststart는 ffprobe가 직접 안 알려줌 → atom 순서 파싱 |
| golden 회귀 | Python `unittest` + ffmpeg(`scene`/`ssim`) | `tests/golden/manifest.json` | 외부 의존 0. numpy 불필요 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13.17 (시스템) | 렌더러·doctor·시험 | 기존 언어. `unittest`로 충분 [VERIFIED: `python3 --version` 실행] |
| playwright (PyPI) | **==1.63.0** | Chromium 구동·스크린샷·CDP | 프리설치 Chromium 1243과 맞음. 1.64.1은 1248을 찾다 실패 [VERIFIED: 이 세션 실행 — 1.64.1 `launch()` → "Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1248/…", 1.63.0 → 성공(153.0.8010.12)] |
| Chromium (프리설치) | 153.0.8010.12 (rev 1243) | 렌더 엔진 | 다운로드 차단 환경 [VERIFIED: `/opt/pw-browsers/chromium -> /opt/pw-browsers/chromium-1243/chrome-linux64/chrome`] |
| ffmpeg / ffprobe | 6.1.1 (시스템) | 인코딩, `scene`·`ssim` 필터, 규격 검사 | 이미 사용 중. 비교용 필터까지 내장 [VERIFIED: 이 세션에서 `ssim`, `select=scene`, `showinfo` 실행] |
| Noto Sans KR Subset OTF (Regular/Bold/Black) v2.004 | upstream `notofonts/noto-cjk` `Sans/SubsetOTF/KR/` | 브랜드 폰트 벤더링 | 기존 릴스의 Noto Sans CJK KR과 글리프·세로 메트릭 동일(§폰트) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest` (stdlib) | — | 단위·golden 시험 | pytest 미설치이므로 이것을 쓴다 |
| Pillow / numpy | 12.3.0 / 2.5.3 (이미지에 있음) | 사용 금지(필수 의존으로 쓰지 말 것) | 시험은 ffmpeg 필터만으로 구현 가능(실측). 이미지에서 사라져도 시험이 깨지지 않게 |
| fonttools | 4.68.0 | (선택) 폰트 서브셋 제작 | 무수정 벤더링을 택하면 불필요. 저장소 의존성에 넣지 말 것 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 무수정 OTF 3종 (14.5 MB) | `pyftsubset`으로 한글 완성형 11,172자+라틴+기호만 남긴 서브셋 (5.5 MB: 1.72/1.82/1.93 MB) | 같은 스펙의 렌더가 바이트까지 동일함을 실측(tax-deduction). 단 파생물 관리·범위 밖 글자 위험이 생김. 레포 크기가 문제가 될 때만 |
| golden = 커밋된 MP4 | golden = HEAD `reel.py`가 만든 새 기준선 | 후자는 `<s>` 레이아웃 드리프트를 숨긴다(§Golden) |
| 프레임 해시 일치 | SSIM 허용 오차 | x264 스레드 수에 따라 바이트가 달라짐(실측) → 해시 불가 |
| numpy로 프레임 차이 | ffmpeg `ssim`/`select=scene` | ffmpeg만으로 동일 결과(실측), 의존 0 |

**Installation (훅이 수행):**
```bash
# tools/requirements.txt 에는 한 줄만
#   playwright==1.63.0
python3 -m pip install --quiet --user -r tools/requirements.txt
```
**Version verification:** `pip install --dry-run` / 실제 `--user` 설치로 1.63.0 설치 확인, PyPI JSON에서 1.63.0 업로드일 2026-09-15 확인 [VERIFIED: pypi.org/pypi/playwright/1.63.0/json]. 이 이미지의 시스템 버전은 1.64.1 [VERIFIED: `pip list`].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| playwright | PyPI | 5 yrs (87 릴리스, 첫 업로드 2021-02-24) | (seam이 PyPI 다운로드 수를 못 가져옴) | github.com/Microsoft/playwright-python (project_urls) | **SUS** (seam: too-new, unknown-downloads, no-repository) | 플래너가 설치 단계 앞에 `checkpoint:human-verify` 추가. 아래 판단 참조 |
| pyee, greenlet (playwright 의존성) | PyPI | — | — | — | SUS (seam 동일 사유) | playwright 의존으로만 설치. 이미지에 greenlet 이미 존재 |

**seam 출력 해석:** `gsd-tools query package-legitimacy check --ecosystem pypi playwright pyee greenlet`가 세 패키지를 SUS로 판정했다. 사유는 "최신 릴리스가 2026-10-22로 너무 새로움", "다운로드 수 불명", "repoUrl 없음"이다. 내 판단으로는 오탐이다: 저자 Microsoft Corporation, `project_urls`에 github.com/Microsoft/playwright-python, 87개 릴리스, 이미지에 이미 설치된 패키지의 **이전 안정 버전(1.63.0, 2026-09-15 업로드)**을 고정 설치한다 [VERIFIED: PyPI JSON]. 그래도 프로토콜에 따라 SUS를 숨기지 않고 표기하며, 플래너는 사람 확인 체크포인트를 한 번 넣는다(비용 낮음). 새로 추가되는 다른 패키지는 없다(폰트 파일은 패키지가 아니며 sha256으로 고정).

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** playwright (+pyee, greenlet 전이 의존)

## Architecture Patterns

### System Architecture Diagram

```
                           세션 시작 (CLAUDE_CODE_REMOTE=true)
                                       │
                         .claude/hooks/session-start.sh
                ┌──────────────────────┼───────────────────────────────┐
         (기존) GSD / agent-browser    │ playwright 버전 != 1.63.0 ?   │
                                       │   └─ pip install --user -r tools/requirements.txt
                                       ▼                               │
                          python3 tools/doctor.py  ── 결과 한 줄을 stdout, 상세는 stderr
                          ├─ ① Playwright 버전/Chromium 실행 (기본 → 폴백 executable_path)
                          ├─ ② goto(file://fonts-probe.html): FontFace.status + CDP platform fonts
                          ├─ ③ ffmpeg/ffprobe + libx264/aac 인코더
                          └─ ④ (선택) 폰트 파일 sha256 대조
 
 spec.json ─► spec 로더(v1) ─► 타임라인(상태 목록: top, lines, k, dur)
                                   │
                                   ├─► [render] 템플릿 HTML(goto file://) ─ 상태마다 innerHTML 교체 ─► PNG/상태
                                   │        │   layout 변형: legacy(커밋 MP4 재현) | new(안전영역 스택)
                                   │        └─► [measure] JS: 줄 수·bbox ─► 경고 목록 (장면·줄 번호)
                                   │                      └─► (옵션) 오버레이 PNG
                                   └─► [encode] ffmpeg concat + fps=30 ─► out.mp4 ─► [specprobe] ffprobe+atom 검사
 
 golden 시험:  specs/*.json ─► legacy 렌더(임시 폴더) ─► 디코드 ─► 구조 정확 일치 + 프레임별 SSIM ≥ 0.98
               (기준 = 커밋된 2026/reels/*.mp4, 기준값 = tests/golden/manifest.json)
```

### Recommended Project Structure
```
tools/
├── reel.py              # shim: python3 tools/reel.py spec.json out.mp4 (stdout: duration=…s cover_ms=…)
├── cards.py             # 변경 없음 (이 단계 범위 밖)
├── doctor.py            # ENV-01 진입점(얇게). reelkit.doctor 호출
├── requirements.txt     # playwright==1.63.0
├── fonts/
│   ├── NotoSansKR-Regular.otf  NotoSansKR-Bold.otf  NotoSansKR-Black.otf
│   ├── OFL.txt          # 업스트림 Sans/LICENSE 그대로
│   └── README.md        # 출처 URL, 버전 2.004, sha256 3개, 받은 날짜
├── reelkit/             # 패키지 (아래 이름 충돌 주의)
│   ├── spec.py  timeline.py  render.py  layout.py  encode.py  specprobe.py  doctor.py  constants.py
│   └── templates/frame.html     # @font-face 포함 빈 템플릿 (goto 대상)
└── tests/
    ├── test_golden.py   test_specprobe.py   test_layout.py   test_doctor.py
    └── golden/manifest.json     # 커밋 MP4에서 한 번 뽑은 기준값
2026/reels/drafts/      # .gitignore (D-08)
```
**이름 충돌 주의:** `tools/reelkit.py`(진입 스크립트)와 `tools/reelkit/`(패키지)를 함께 두면, 스크립트 안의 `import reelkit`은 항상 패키지를 가져온다(실측). 동작은 하지만 혼란스럽다. 권고: 진입 스크립트는 `reel.py`(shim), `doctor.py`, (golden은 `python3 -m unittest`)로 나누고 패키지만 `reelkit/`로 둔다. 통합 디스패처가 필요해지면 Phase 3에서 `tools/reelkit_cli.py` 같은 다른 이름으로.

### Pattern 1: 템플릿은 디스크 파일, 프레임은 `innerHTML` 교체
**What:** `@font-face`가 든 빈 HTML을 디스크에 쓰고 `page.goto("file://…")`로 연 뒤, 상태마다 `document.body.innerHTML`만 바꿔 스크린샷한다.
**When to use:** 모든 렌더. `set_content()` 페이지는 `about:blank`라 `file://` 폰트가 막힌다(조사 STACK 실측과 일치).
**Example:**
```python
# Source: 이 세션 spike (legacy_spike.py) — 10편 중 10편에서 커밋 MP4와 일치
page.goto("file://" + str(tpl_path.resolve()))           # @font-face: file://…/NotoSansKR-*.otf
for n, (top, lines, k, dur) in enumerate(seq):
    page.evaluate("h=>{document.body.innerHTML=h}", inner_html(top, lines, k, prog, basis))
    page.evaluate("document.fonts.ready.then(()=>0)")
    page.screenshot(path=f"{work}/v{n:03d}.png")
```

### Pattern 2: legacy 인코딩은 기존 ffmpeg 경로 그대로
**What:** PNG + `duration` concat 파일 → `-vf fps=30,format=yuv420p -c:v libx264 -crf 20 -c:a aac -shortest -t <total> -movflags +faststart`, 무음 AAC는 `anullsrc=r=44100:cl=stereo`.
**Why:** 상태 전환 프레임 번호가 ffmpeg `fps` 필터의 반올림에 의존한다. 단순한 반올림 규칙으로는 재현되지 않는다(§Pitfall 3). 같은 경로를 쓰면 구성상 같다.
**Example:** 기존 `reel.py`의 `subprocess.run(["ffmpeg",…])` 인자를 그대로 둔다 (아래 인용).

```
# Source: tools/reel.py (이 세션에서 Read) — 값 그대로
SAGE="#DEE9E0"; DG="#2F4F3E"; GOLD="#B08D46"; LINE=0.85; HOLD=1.9
…"-vf","fps=30,format=yuv420p","-c:v","libx264","-crf","20","-c:a","aac","-shortest","-t",f"{total:.2f}","-movflags","+faststart",out
…print(f"duration={total:.1f}s cover_ms={int((LINE*(first-1)+0.4)*1000)}")
```

### Pattern 3: 상수 한 곳 (`constants.py`)
**What:** 색, 타이밍, 안전영역을 한 모듈에. 실기기 보정은 이 파일만 고친다(D-03).
```python
# Source: CONTEXT D-02/D-03 + SUMMARY 결정 7 (값은 그 문서에서 옮김)
SAFE = dict(
    top=270,            # [ASSUMED] SUMMARY의 y 270~1250 — 경고만
    warn_y=1250,        # D-03: y > 1250 경고
    bottom_ui=450,      # D-03: 아래에서 450px = y 1470 이후는 오류
    right=150,          # D-03
    left=96,            # 기존 padding (reel.py "padding:0 96px")
)
BASIS_PX = 36; BASIS_MAX_LINES = 2; ACCT_PX = 36      # D-02, ENV-04
```

### Anti-Patterns to Avoid
- **HEAD `reel.py`의 `<s>` 인라인 span을 "기존 레이아웃"으로 간주:** 커밋 MP4와 다르다. 반드시 MP4 대조로 확인.
- **`set_content` + `wait_for_timeout(60)`:** 폰트 로드를 보장하지 못한다. `goto(file://)` + `FontFace.status`.
- **MP4 바이트 해시/`cmp`로 회귀 판정:** 스레드 수에 따라 달라진다(실측).
- **legacy 모드에서 `word-break: keep-all`/폰트 교체:** 커밋 MP4와 줄바꿈이 달라진다. `keep-all`은 new 경로 전용.
- **golden 시험이 `2026/reels/*.mp4`를 덮어쓰기:** 출력은 항상 임시 폴더.

## Golden 회귀 설계 (ENV-03)

### 결정: 기준은 "커밋된 MP4", 비교는 "구조 정확 + 프레임 허용 오차"

**근거(실측):** 커밋된 MP4 10편 vs 번들 폰트 + legacy(`<s>`=block) 재렌더.

| 편 | 프레임 수(golden/new) | 경계 일치 | MAD 평균 / 최대 (270×480 gray) | SSIM 평균 / **프레임별 최소** | PSNR 최소(dB) |
|----|----------------------|-----------|------------------------------|------------------------------|---------------|
| rate-secret-1 | 730/730 | ✓ | 0.156 / 0.437 | 0.9970 / 0.9938 | 33.2 |
| rate-secret-2 | 705/705 | ✓ | 0.042 / 0.110 | 0.9994 / 0.9985 | 39.4 |
| rate-secret-3 | 705/705 | ✓ | 0.274 / 0.550 | 0.9953 / 0.9923 | 32.0 |
| tax-deduction | 781/781 | ✓ | 0.232 / 0.462 | 0.9960 / 0.9932 | 33.1 |
| salary-1 | 654/654 | ✓ | 0.239 / 0.504 | 0.9961 / 0.9932 | 32.4 |
| ebook-event | 705/705 | ✓ | 0.114 / 0.335 | 0.9978 / 0.9952 | 34.0 |
| salary-2 | 756/756 | ✓ | 0.272 / 0.410 | 0.9959 / 0.9941 | 33.5 |
| salary-3 | 756/756 | ✓ | 0.252 / 0.520 | 0.9961 / 0.9931 | 32.1 |
| salary-4 | 730/730 | ✓ | 0.252 / 0.546 | 0.9962 / 0.9930 | 31.9 |
| salary-5 | 654/654 | ✓ | 0.171 / 0.358 | 0.9975 / 0.9952 | 34.0 |

10편 모두 `ffprobe` 스트림 구성(코덱·프레임 수·duration)이 정확히 일치한다 [VERIFIED: 이 세션 실행, `cmp_all.py`].

**대조군(틀린 렌더가 걸러지는지):**

| 대조군 | 편 | MAD 최대 | SSIM 평균 / 최소 | PSNR 최소 |
|--------|----|----------|------------------|-----------|
| 폰트 대체(WenQuanYi) + `<s>` block | rate-secret-1 | 7.150 | 0.9605 / 0.9387 | 21.0 |
| 폰트 대체 + `<s>` block | tax-deduction | 9.636 | 0.9463 / 0.9089 | 19.9 |
| 번들 폰트 + HEAD식 `<s>` 인라인 | rate-secret-1 | 6.131 | 0.9862 / **0.9508** | 21.6 |
| 번들 폰트 + HEAD식 `<s>` 인라인 | tax-deduction | 7.219 | 0.9769 / 0.9332 | 20.8 |

**주의:** 평균 SSIM/MAD만 보면 구분이 약하다(정상 0.995 vs 대조군 0.986~0.977). 텍스트가 화면의 작은 부분이라 평균이 희석된다. **프레임별 최소 SSIM**이 구분력이 높다(정상 ≥ 0.9923, 대조군 ≤ 0.9508).

**권고 임계값:**
| 항목 | 규칙 | 근거 |
|------|------|------|
| 프레임 수, 비디오·오디오 duration | **정확 일치** | 10편 전부 일치 |
| 상태 전환(경계) 프레임 목록 | **정확 일치** (`tests/golden/manifest.json`의 목록과 같음) | 10편 전부 일치 |
| 표지 시점 | `cover_ms`가 1번째 장면의 "모든 줄 표시 완료" 구간 안(`[LINE*(n-1), +HOLD)`) + 출력 문자열 `cover_ms=` 값이 기존 공식과 같음 | 공식은 `reel.py` 인용 |
| 프레임별 SSIM (ffmpeg `ssim`, `All:`) | **모든 프레임 ≥ 0.98** | 정상 최솟값 0.9923(여유 0.012) / 대조군 최댓값 0.9508(여유 0.029) |
| 프레임별 PSNR | 모든 프레임 ≥ 28 dB (보조) | 정상 최소 31.9 / 대조군 최대 21.6 |
| MAD(270×480 gray) | 사용하지 않아도 됨. 쓴다면 프레임별 ≤ 1.5 | 정상 최대 0.55 / 대조군 6.1+ |

SSIM 임계값을 0.98로 두는 이유: 정상 분포의 최저(0.9923)와 대조군 최고(0.9508)의 중간보다 정상 쪽에 가깝게 잡아 x264/Chromium 미세 변동 여유를 확보했다. 호스트가 바뀌어 SSIM이 0.98~0.99로 흔들리면 임계값을 완화하지 말고 원인(폰트 로드·Chromium 빌드)을 먼저 본다.

### 왜 "커밋된 MP4"이고 "새 기준선"이 아닌가
1. 커밋된 MP4가 **게시된 기록**이다(D-05). "기존과 같다"의 정의가 이것이다.
2. 새 기준선(HEAD 코드 출력)을 기준으로 삼으면 위의 `<s>` 드리프트가 기준에 구워져 **조용히 통과**한다. 실제로 HEAD 코드는 MP4와 다르다(구분 가능한 대조군 SSIM 최소 0.9508).
3. 폰트 환경 차이는 문제가 되지 않음이 확인됐다: 번들 `Noto Sans KR`과 fontconfig로 설치한 진짜 `Noto Sans CJK KR` OTF가 **같은 SSIM(0.986224)**을 낸다 [VERIFIED: 이 세션]. 즉 커밋 MP4와의 차이는 폰트가 아니라 `<s>` 마크업이었다.
4. 기준값(프레임 수·경계)은 커밋 MP4에서 **한 번** 뽑아 `tests/golden/manifest.json`에 저장하고(원고 sha256 포함), 시험은 그 JSON과 MP4 두 가지를 모두 쓴다(구조는 JSON, 화면은 MP4).

**legacy 렌더러 변경점(HEAD 대비):** `<s>`를 `<span style="display:block;font-size:52px;font-weight:700;color:#5B6E62">`로, 폰트는 번들, `set_content` 대신 `goto(file://)`. 나머지(색, 레이아웃, 진행 막대, `bottom:150px`, 30px, concat+fps)는 동일. 10편의 `<s>`는 모두 줄 전체를 감싼다 [VERIFIED: 스캔 — 부분 `<s>` 없음; `<g>`는 한 줄에 여러 번 가능("`<g>증여</g> · <g>절세</g> · <g>연금</g>`")]. 마크업은 `<g>`, `<s>`뿐이다.

**`reel.py` shim 소유권 결정(플래너 확인 필요):** HEAD `reel.py`의 `<s>` 인라인 동작을 바꾸는 셈이다. 사용자가 그 동작을 의도했는지 알 수 없으므로(MP4가 먼저 만들어지고 `reel.py`가 나중에 커밋됨: `git log` — 릴스 커밋 dc96093·110c122… 뒤에 도구 커밋 434adc8) 근거는 "게시된 MP4가 진실"이다. Open Question 1.

### 상태 경계 규칙은 단순 반올림이 아니다
상태 시작 시각 `c`(초)를 프레임 `c*30`으로 환산한 값과 실제 MP4에서 검출한 경계를 비교하면, 정확한 .5 동점뿐 아니라 정수 위치도 +1 어긋나는 경우가 있다(예: 381.0 → 382, 25.5 → 25, 82.5 → 83). half-up/half-down/half-odd 어느 것도 10편에 맞지 않았다 [VERIFIED: 이 세션 시도]. 따라서 **Phase 1은 concat+`fps` 경로를 유지**하고, 경계는 manifest에 기록한다. Phase 4가 파이프 방식(`image2pipe`)으로 바꿀 때는 `motion=none`이 manifest 경계와 일치함을 시험으로 증명해야 한다(Phase 4 위험으로 이월).

### 경계 검출 (ffmpeg만, numpy 불필요)
```bash
# Source: 이 세션 실측 — 10편(golden+재렌더) 20개 영상에서 numpy 방식과 완전 일치
ffmpeg -hide_banner -i reel.mp4 -vf "scale=270:480,select='gt(scene,0.003)',showinfo" -an -f null - 2>&1 \
  | grep -o "pts_time:[0-9.]*"     # 프레임 = round(pts_time*30)
```
진행 막대가 매 상태마다 자라고 줄이 나타나므로 정적 홀드 중에는 장면 점수가 0.003 아래, 상태 전환에서는 위다(임계 0.002~0.005 모두 동일 결과). `showinfo`의 `n:`은 필터 후 번호이므로 `pts_time`을 쓴다.

### 프레임별 SSIM (ffmpeg만)
```bash
ffmpeg -i golden.mp4 -i new.mp4 -lavfi "[0:v][1:v]ssim=stats_file=ssim.txt" -f null -
# ssim.txt 각 줄: "n:1 Y:… U:… V:… All:0.9973 (25.7)" → All 값의 최솟값이 ≥ 0.98
```
두 영상의 프레임 수가 같아야 하므로 구조 검사를 먼저 한다.

### 시험 구성
- 기본 명령: `python3 -m unittest discover -s tools/tests -v` (전체), 빠른 확인은 1편만(`-k rate_secret_1`).
- 비용: 1편 렌더+인코딩 ≈ 11 s(4코어), 10편 병렬(`-P4` 상당) ≈ 40~60 s. 비교(`ssim` 2회 포함)는 편당 수 초. 전체 한 번에 2분 안쪽 [VERIFIED: 실측 11 s/편, cmp_all 약 2분].
- 임시 출력: `tempfile.mkdtemp()` → 시험 종료 시 삭제. 절대 `2026/reels/`에 쓰지 않는다.
- 원고 없는 MP4: manifest에 `"status": "not-reproducible", "reason": "no spec (D-06)"`로 기록하고 시험은 `skipTest("재현 불가: 원고 없음")`가 아니라 **보고서에 "재현 불가"로 출력**(ENV-03 문구). 같은 MP4에 대해 ENV-06 규격 검사는 수행한다(기존 11편 전부 PASS).
- **결정적 재현성 주의:** 같은 머신에서 같은 입력의 두 렌더는 바이트 동일(`cmp` 확인), headless-shell(기본 launch)과 풀 Chrome(`executable_path=/opt/pw-browsers/chromium`)도 바이트 동일. 그러나 `-threads 1/2/4`는 바이트가 모두 다르고 디코드 SSIM은 1.000000 [VERIFIED]. 시험에서 바이트를 비교하지 않는다.

## 폰트 벤더링

| 파일 | 크기(byte) | sha256 | weight |
|------|-----------|--------|--------|
| NotoSansKR-Regular.otf | 4,644,748 | `69975a0ac8472717870aefeab0a4d52739308d90856b9955313b2ad5e0148d68` | 400 |
| NotoSansKR-Bold.otf | 4,816,044 | `5a6ceb287ed2fc6cfc6213144ebea68cbd94b20fc9eb873d8486493bf02d9bda` | 700 |
| NotoSansKR-Black.otf | 5,033,248 | `a9977a588488d2a7f544bb2b589b01bed071dca64a4655d438696301b527884b` | 900 |
| OFL.txt (= upstream `Sans/LICENSE`) | 4,301 | `6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2` | — |

합계 14.49 MB(OTF 3종). 현재 `.git`은 7.4 MB [VERIFIED: `du -sh .git`]이므로 한 번 약 두 배로 커진다(OTF는 압축이 거의 안 된다). Medium은 `cards.py`용이며 이 단계에 필요 없다(`reel.py`는 400/700/900만 사용: 근거 400 기본, `<b>` 계정·`top`·`<s>` 700, 본문 900) [VERIFIED: reel.py Read].

**출처 URL (다운로드 검증됨, HTTP 200):**
- `https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/KR/NotoSansKR-{Regular,Bold,Black}.otf`
- `https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE`
`main`은 움직이므로 URL이 아닌 **sha256으로 고정**한다. 업스트림 커밋 SHA는 이 세션에서 GitHub API 접근 불가로 얻지 못했다 [UNVERIFIED].

**라이선스:** SIL OFL 1.1 — `LICENSE` 본문이 "licensed under the SIL Open Font License, Version 1.1"로 시작하고 폰트 name ID 0은 "© 2014-2021 Adobe (http://www.adobe.com/)." [VERIFIED: 파일 Read/fontTools]. 재배포 허용, 파일을 수정하지 않으면(무수정 벤더링) Reserved Font Name 조항 문제가 없다. 저작권·라이선스 고지는 `tools/fonts/OFL.txt`로 동반한다. (OFL은 "단독 판매 금지" 조건이 있으나 소프트웨어와 함께 재배포는 허용 — LICENSE 본문 §1.)

**검증된 속성:**
- cmap에 완성형 한글 **11,172자 전부** 포함, 10편이 쓰는 334개 문자 전부 포함(①~⑤, →, −, ÷, · 포함) [VERIFIED: fontTools 실행].
- 세로 메트릭 `hhea 1160/-288/0`, typo 880/-120/0, win 1160/288 — Noto Sans CJK와 동일 계열, 3개 굵기 동일 [VERIFIED].
- 패밀리 이름은 파일마다 다르다: Regular/Bold는 "Noto Sans KR", Black은 "Noto Sans KR Black"(name ID 1), 그러나 `@font-face`에서 family를 `'Noto Sans KR'`, `font-weight`를 400/700/900으로 직접 지정하므로 상관없다. CDP가 보고하는 familyName은 "Noto Sans KR Black"이 된다(아래 doctor 판정 시 주의).

**로드 방식 (검증됨):**
```html
<!-- tools/reelkit/templates/frame.html : file:// 절대경로는 Python이 치환 -->
<style>
@font-face{font-family:'Noto Sans KR';font-weight:400;src:url('file://{{FONTDIR}}/NotoSansKR-Regular.otf')}
@font-face{font-family:'Noto Sans KR';font-weight:700;src:url('file://{{FONTDIR}}/NotoSansKR-Bold.otf')}
@font-face{font-family:'Noto Sans KR';font-weight:900;src:url('file://{{FONTDIR}}/NotoSansKR-Black.otf')}
</style><body style="margin:0"></body>
```
`page.goto("file://…/frame.html")` 후 `Promise.all([...document.fonts].map(f=>f.load().then(()=>f.status)))` → 세 개 모두 `"loaded"` [VERIFIED]. `document.fonts.check()`만으로는 부족하다: `@font-face`에 없는 패밀리는 로드할 것이 없어 `true`를 돌려주므로(웹 표준 동작) **FontFace.status와 CDP 플랫폼 폰트**를 함께 본다 [ASSUMED: check() 의미는 CSS Font Loading 스펙 기억 기반, 이 세션에서 직접 반례를 만들지는 않음].

**폰트 조용한 대체 탐지 (CDP, 실측):**
```python
cdp = page.context.new_cdp_session(page); cdp.send("DOM.enable"); cdp.send("CSS.enable")
doc = cdp.send("DOM.getDocument", {"depth": 0})
nid = cdp.send("DOM.querySelector", {"nodeId": doc["root"]["nodeId"], "selector": "#a"})["nodeId"]
fonts = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": nid})["fonts"]
# → [{'familyName':'Noto Sans KR Black','isCustomFont':True,'glyphCount':19},
#    {'familyName':'Noto Color Emoji','isCustomFont':False,'glyphCount':1}]   ← 😀가 대체됨을 탐지
```
`isCustomFont == False`인 항목이 하나라도 있으면 "번들 폰트에 없는 글자가 시스템 폰트로 대체됨" 경고(장면·줄 번호와 함께). doctor는 한글·라틴·숫자·①·→ 샘플로 `isCustomFont`가 전부 True인지 확인한다. 이 방식은 0.83 s에 끝난다.

**서브셋 선택(재량 항목):** 이 세션의 spike에서 한글 완성형+라틴+기호 서브셋(1.72/1.82/1.93 MB)도 같은 영상을 바이트까지 똑같이 렌더했다(tax-deduction, `cmp` 동일). 그러나 무수정이 단순하고 OFL 면에서 안전하며 범위 밖 글자(한자·특수기호) 위험이 없다. 권고는 **무수정 3종**. 레포 크기가 문제로 지적되면 `pyftsubset` 서브셋으로 교체하되 sha256·README를 갱신하고 golden을 다시 돌린다.

## Playwright 설치 경로와 SessionStart 훅 (ENV-01, ENV-02, D-07)

**현재 훅 인용 (이 세션에서 Read):**
```
set -euo pipefail
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then exit 0; fi
…npx --yes @opengsd/gsd-core@latest --claude --global >&2
…npm install -g agent-browser >&2
…echo 'export AGENT_BROWSER_EXECUTABLE_PATH=/opt/pw-browsers/chromium' >> "$CLAUDE_ENV_FILE"
```
`.claude/settings.json`에는 `SessionStart` → `$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh`가 이미 등록되어 있다 [VERIFIED: Read]. 스크립트 상단 주석이 "설치 출력은 세션 컨텍스트에 섞이지 않도록 stderr로 보낸다"고 밝히므로, 훅 stdout은 컨텍스트로 들어간다는 전제로 짜여 있다 [VERIFIED: session-start.sh 2~3행]. 새 단계는 **stdout에는 한 줄 요약만**, 설치·상세 출력은 stderr.

**실측한 설치 방식:** `pip install --user playwright==1.63.0`은 `/root/.local/lib/python3.13/site-packages`에 설치되고 `sys.path`에서 시스템 `/usr/local/lib/python3.13/dist-packages`(1.64.1)보다 앞서므로 `importlib.metadata.version('playwright')`가 1.63.0을 돌려주고 기본 `launch()`가 성공한다. 이 이미지에는 `EXTERNALLY-MANAGED`가 없어 `--break-system-packages`가 필요 없다. 휠 캐시가 있으면 2.1 s, 이미 맞으면 0.8 s(pip 확인만) [VERIFIED: `PYTHONUSERBASE`를 scratch로 돌려 시스템에 영구 설치 없이 확인; 시스템 playwright는 1.64.1 그대로 확인]. 이미지가 바뀌어 `EXTERNALLY-MANAGED`가 생기면 `PIP_BREAK_SYSTEM_PACKAGES=1`을 쓰거나 `--user`가 거부되는지 doctor가 메시지로 알려야 한다 [ASSUMED: 이 이미지 이후 변화는 미관측].

**훅 추가분(권고 골격):**
```bash
# --- Phase 1: 릴스 렌더 환경 고정 (idempotent) ---
cd "${CLAUDE_PROJECT_DIR:-.}"
PW_PIN="$(sed -n 's/^playwright==//p' tools/requirements.txt | head -1)"
PW_CUR="$(python3 -c 'import importlib.metadata as m;print(m.version("playwright"))' 2>/dev/null || true)"
if [ "$PW_CUR" != "$PW_PIN" ]; then
  python3 -m pip install --quiet --user -r tools/requirements.txt >&2
fi
# 점검 결과 한 줄은 stdout(세션 컨텍스트), 실패해도 세션은 계속(훅은 0으로 종료)
python3 tools/doctor.py --quiet || true
```
- 위 `pip`는 시스템 Python을 건드리므로 훅 스킬 가이드대로 해시 파일 스킵 대상이 아니고, 매 세션 버전 비교(0.1 s 미만)만 한다.
- `pip`가 실패(네트워크·PyPI 차단)하면 `set -e`로 훅이 중단되어 뒤의 doctor가 안 돈다 → 설치는 `if ! pip …; then echo "…" >&2; fi`로 감싸 doctor가 원인을 보고하게 한다.
- `playwright install`(브라우저 다운로드)는 호출하지 않는다: `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`과 네트워크 정책 [VERIFIED: `env`].

**doctor 설계 (`python3 tools/doctor.py [--quiet|--json]`; 종료 코드 0 = 전부 정상):**
| # | 검사 | 방법 | 실패 시 원인 메시지 예 |
|---|------|------|------------------------|
| 1 | Playwright 버전 | `importlib.metadata.version` vs `tools/requirements.txt` | "playwright 1.64.1 설치됨, 1.63.0 필요 → `python3 -m pip install --user -r tools/requirements.txt`" (없으면 ModuleNotFoundError도 같은 안내) |
| 2 | Chromium 실행 | 기본 `launch()` → 실패 시 `AGENT_BROWSER_EXECUTABLE_PATH` → `/opt/pw-browsers/chromium` → glob `/opt/pw-browsers/chromium-*/chrome-linux*/chrome`. 쓴 경로를 출력 | "기본 launch 실패(…1248 없음) → /opt/pw-browsers/chromium으로 폴백함" (폴백 성공은 경고지만 통과) |
| 3 | 폰트 파일 존재·sha256 | `tools/fonts/*.otf` 해시 (3파일 14 MB, 수십 ms) | "tools/fonts/NotoSansKR-Black.otf 없음/변경됨" |
| 4 | 폰트 로드 | `goto(file://)` → `FontFace.status=="loaded"` 3개 + CDP `isCustomFont` 전부 True (한글·라틴·숫자 샘플, weight 400/700/900) | "weight 900 폰트가 시스템 폰트로 대체됨(familyName=…)" |
| 5 | ffmpeg | `ffmpeg -version`, `ffmpeg -encoders`에 `libx264`·`aac`, 짧은 `lavfi color` 1프레임 인코딩 → 종료 코드 | "ffmpeg 없음" / "libx264 없음" |
| 6 | ffprobe | `ffprobe -version` | — |

폴백 실행 경로에서도 렌더 결과가 같음을 확인했다(headless-shell vs `/opt/pw-browsers/chromium`: 같은 바이트) [VERIFIED]. 또한 1.64.1 + `executable_path`도 동작한다 [VERIFIED: 조사 STACK과 이 세션의 `exec ok 153.0.8010.12`].

**렌더러도 같은 launch 함수를 공유:** `reelkit.browser.launch(pw)`가 위 체인을 구현하고 doctor·렌더·시험이 모두 이것을 쓴다(리비전 번호 `1243`은 주석 외 하드코딩 금지).

## 새 배치 (D-01 ~ D-03, ENV-04) 와 레이아웃 측정 (ENV-05)

### 새 배치 구조 (spike에서 검증)
```
#root 1080×1920 (sage)  — 진행 막대 14px 그대로 (D-04)
 └ #stack  position:absolute; left:96px; right:150px; top:270px; height:980px  (= warn_y 1250 − top 270)
          display:flex; flex-direction:column; justify-content:center; gap:40px; word-break:keep-all
     ├ top 라벨      50px / 700 / min-height 60px        (legacy와 동일)
     ├ 본문 줄들     100px / 900 / line-height 1.3 / letter-spacing -.03em   (legacy와 동일)
     ├ 근거          36px / line-height 1.3 / #5B6E62   ← D-01: 본문 바로 아래, D-02: 36px, ≤2줄
     └ 계정명        36px / 700 / #5B6E62               ← 근거 아래, ENV-04: ≥36px
```
- 본문 줄 전부(`opacity:0` 포함)가 레이아웃에 참여하므로 줄 등장 중에도 위치가 변하지 않는다(legacy와 동일 성질).
- 상수는 `constants.py` 한 곳. `right=150`을 바꾸면 폭이 바뀐다(D-03 보정).
- **실측:** 기존 10편의 7장면×10 = 70개 장면을 이 배치에 넣으면 본문 최상단 y 410~500, 계정명 하단 최대 y 1216(tax-deduction), 모든 근거 ≤ 2줄, 안전영역 위반 0. 위반은 우측 150px 때문에 줄바꿈되는 8개 줄(전체 195줄의 4%)뿐이다: "돈이 머문 기간만큼만", "내 돈이 2배 되는 시간", "소득공제 vs 세액공제", "낮은 구간은 세액공제", "높은 구간은 소득공제", "지금 댓글 남겨 주세요", "60 · 150 · 30 · 160", "그냥 모아도 4,500만"(글자 오른쪽 끝 929~968px; 폭 834px 한계 초과).
- 비교용 legacy 배치 실측: 70개 장면 전부 근거·계정명 하단이 y=1770(> 1470 UI 영역), 계정명 오른쪽 끝 984px, 4줄 장면 1곳의 본문이 y=1283(> 1250). 즉 현 배치의 문제가 수치로 확인된다.

**플래너 결정 필요(Open Question 2):** D-03을 문자 그대로 "모든 중요 텍스트에 우측 150px"로 적용하면 위 8줄이 줄바꿈(경고)된다. 이는 ENV-05의 의도(생성기가 줄을 줄이게 함)와 부합하므로 기본값은 **엄격 적용**을 권한다. 대안은 본문 우측 여백은 96px로 두고 근거·계정명에만 150px를 적용하는 것인데, 그러면 Instagram 우측 버튼 영역과 본문이 겹칠 수 있다([CONFLICTING] 출처들).

### 측정 방법 (브라우저 안, 실측)
- **줄바꿈 감지:** 줄 요소의 텍스트 노드마다 `Range.selectNodeContents(node).getClientRects()` → 세로 중심 기준으로 군집(허용오차 = 글자 크기×0.4) → 줄 수. 줄 수 > 1이면 WRAP. 요소 높이/라인높이 비교보다 `<g>` 인라인에도 강하다.
- **넘침/침범:** 텍스트 사각형의 `right > 1080 − SAFE.right`, `bottom > SAFE.warn_y`(경고), `bottom > 1920 − SAFE.bottom_ui`(오류), `top < SAFE.top`(경고).
- **근거 2줄 초과:** 근거 텍스트 줄 수 > 2 → "BASIS>2LINES".
- **장면 단위 1회 측정:** 모든 줄이 레이아웃에 참여하므로 장면당 한 번이면 충분(이 시험에서 70장면 전체가 수 초).
- **실제 동작 확인(bad.json):** 줄 7개·긴 근거를 넣으면 `WRAP 1 1`, `TOP 1 1`, `WRAP 1 7`, `BASIS>2LINES 1 3`, `BASIS_Y>1250`, `ACCT_Y>1250`이 장면·줄 번호와 함께 나온다.

```js
// Source: 이 세션 spike (layout_spike.py MEASURE) — 줄 수 세기 핵심
const textRects=(el)=>{const out=[];const tw=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let n;
  while(n=tw.nextNode()){ if(!n.nodeValue.trim())continue; const r=document.createRange(); r.selectNodeContents(n);
    const fs=parseFloat(getComputedStyle(n.parentElement).fontSize);
    for(const q of r.getClientRects()) if(q.width>0.5) out.push({l:q.left,r:q.right,t:q.top,b:q.bottom,fs});}
  return out;};
const lineCount=(rs)=>{ if(!rs.length) return 0; const c=rs.map(q=>({y:(q.t+q.b)/2,tol:q.fs*0.4})).sort((a,b)=>a.y-b.y);
  let n=1,last=c[0].y; for(const q of c.slice(1)){ if(q.y-last>q.tol){n++;} last=q.y;} return n;};
```
- **경고 형식:** `scene N line M: <kind> (<value>)` + 가능하면 텍스트 일부. 경고는 렌더를 중단하지 않고 stderr/보고에 낸다. 종료 코드는 정책(Open Question 3). legacy 경로는 같은 측정을 "정보용"으로 돌리면 안 된다(기존 10편은 항상 근거가 UI 영역이라 경고 70건) — legacy는 측정 생략.

### 오버레이 미리보기 (ENV-05)
- 같은 페이지에 `#ov`(position:absolute; pointer-events:none)를 덧붙여 스크린샷: 상단 `0..270` 노랑, `1250..1470` 노랑(경고), `1470..1920` 빨강(UI 영역), 우측 `150px` 빨강, 경계선 라벨 `y=270`, `y=1250 warn`, `y=1470 UI zone`. 실제 영상 프레임에는 넣지 않고 **별도 PNG**(예: `<out>.safe.png`)만 만든다. 장면 1~7 중 가장 높은 스택(줄 수가 가장 많은 장면)과 첫 장면을 기본으로, 옵션으로 전체 장면 모음. 이 세션에서 4줄(+`<s>`) 장면과 legacy 비교 이미지를 만들어 눈으로 확인했다(근거·계정이 안전 영역 안, legacy는 빨강 구역 안) [VERIFIED: 이미지 Read].
- 실기기 보정: 사람이 오버레이 상수를 바꿔가며 비공개 업로드로 확인(사람 몫). 코드는 값을 한 곳에서 바꿀 수 있게만 하면 된다(CONTEXT specifics).

## ffprobe 규격 검사 (ENV-06)

| 항목 | 판정 | 필드 |
|------|------|------|
| 비디오 스트림 1개 | `codec_type=="video"` 개수 == 1 | `-show_streams` |
| H.264 | `codec_name=="h264"` | |
| 1080×1920 | `width`,`height` | |
| 30fps | `r_frame_rate=="30/1"` **그리고** `avg_frame_rate` 30 | 둘 다 확인(가변 프레임 레이트 방지) |
| yuv420p | `pix_fmt=="yuv420p"` | |
| 프로파일 | High/Main/Constrained Baseline 중 하나 | 불량 샘플은 "High 4:4:4 Predictive" |
| AAC 오디오 | 오디오 스트림 ≥ 1, `codec_name=="aac"` | |
| faststart | MP4 최상위 atom에서 `moov`가 `mdat`보다 앞 | **Python으로 8바이트 헤더 순회** (size==1 → 64비트, size==0 → 파일 끝). ffprobe는 직접 알려주지 않음 |
| 길이 3~90초 (경고) | `format.duration` | [ASSUMED] Instagram 릴스 길이 상한은 출처 간 상충(조사 SUMMARY [CONFLICTING]) → 실패가 아닌 경고 |

실측: 기존 `2026/reels/*.mp4` 11편 + 재렌더 결과 → 전부 PASS. 불량 샘플 2개: (a) `-c copy`로 faststart 없이 저장 → `atoms=ftyp,free,mdat,moov` 이어서 faststart만 FAIL, (b) 720×1280/24fps/yuv444p/무음 → size, fps, pix_fmt, profile, audio, faststart 항목별 FAIL [VERIFIED: 이 세션 실행]. 출력은 항목별 `PASS/FAIL + 실제 값`으로 해서 "항목별 확인"(성공 기준 5)을 만족시킨다. 색 태그(BT.709)는 이 단계에서 검사/변경하지 않는다: 기존 MP4는 `color_space=unknown`이고 golden 허용 오차와 얽히므로 Phase 4로 이월(조사 PITFALLS도 "golden이 허용하는 경우에만"이라 함).

## `python3 tools/reel.py spec.json out.mp4` shim

- 인자·stdout 형식 유지: 끝에 `duration=<소수 1자리>s cover_ms=<정수>` 출력(HEAD `f"duration={total:.1f}s cover_ms=…"`).
- 내부는 `reelkit` 호출. 기본 레이아웃은 **legacy**(커밋 MP4 재현), 새 배치는 명시적으로 선택(예: `--layout new`, 또는 v2 원고 필드 — Phase 2 소관). shim에는 reelkit과 어긋나는 새 플래그를 만들지 않는다(ARCHITECTURE).
- 새 세션 첫 실행에서 번들 폰트 로드가 실패하면 시스템 폰트로 조용히 대체하지 말고 doctor와 같은 메시지로 **중단**한다(조용한 대체가 이 단계의 핵심 위험).
- 출력 경로는 사용자 지정 그대로. 기존 `2026/reels/*.mp4`를 덮어쓰는 일은 shim이 막지는 않으나 문서(`tools/README.md`)와 시험에서 임시 경로만 쓴다.

## .gitignore (D-08)

현재 `.gitignore`는 없다 [VERIFIED: `cat .gitignore` → No such file]. 추가 항목:
```
2026/reels/drafts/
__pycache__/
*.pyc
tools/tests/_out/
.render-work/
```
렌더 중간물은 기본적으로 `tempfile.mkdtemp()`(시스템 tmp)를 쓰므로 저장소 안에 생기지 않지만, 사용자가 `--keep` 같은 옵션으로 저장소 안에 남기는 경우를 위해 `.render-work/`를 무시한다. `drafts/`를 ignore하면 빈 폴더가 git에 없으므로 코드가 필요할 때 `mkdir -p`한다.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 영상 유사도 | 프레임 디코드 + 직접 SSIM/MAD | ffmpeg `ssim`/`psnr` 필터(`stats_file`) | 의존성 0, 이미 설치됨, 실측 완료 |
| 장면 경계 검출 | 픽셀 비교 루프 | ffmpeg `select='gt(scene,0.003)',showinfo` | numpy 없이 동일 결과(20개 영상 일치) |
| 줄 수·넘침 측정 | 글자 폭 추정 공식 | 브라우저 `Range.getClientRects()` | 폰트 메트릭·셰이핑·자간을 이미 반영 |
| 폰트 대체 탐지 | `fc-match` 파싱 | CDP `CSS.getPlatformFontsForNode` | 실제 렌더에 쓰인 폰트를 노드별로 알려 줌 |
| MP4 규격 | mp4 파서 전체 | `ffprobe -show_streams -of json` + 최상위 atom 순회 20줄 | faststart만 직접 확인 필요 |
| 버전 비교/설치 | 설치 스크립트 | `importlib.metadata` + `pip install --user -r` | 사용자 site가 시스템 위에 얹힘(실측) |
| 해시 파일 검증 | 새 도구 | `hashlib.sha256` | 14 MB 해시 수십 ms |
| 테스트 러너 | 자체 러너 | `unittest` | pytest 미설치, 새 의존성 금지 |

**Key insight:** 이 단계의 모든 검사는 이미 설치된 도구(Chromium, ffmpeg, stdlib)로 가능하다. 새 의존성은 `playwright==1.63.0` 하나뿐이어야 한다.

## Common Pitfalls

### Pitfall 1: `<s>`를 인라인으로 렌더해 커밋 MP4와 어긋남
**What goes wrong:** HEAD `reel.py` 마크업 치환을 그대로 옮기면 `<s>` 줄 장면(7장면 중 최소 2개 × 10편)의 세로 배치가 약 58px 달라지고 프레임별 SSIM이 0.95 근처로 떨어진다.
**Why it happens:** 커밋된 MP4들은 `<s>`가 블록 줄로 렌더된 렌더러가 만든 것으로 보이며(도구 커밋이 MP4보다 나중), HEAD 코드는 그와 다르다.
**How to avoid:** legacy는 `display:block`; golden을 커밋 MP4에 대해 실행.
**Warning signs:** 마지막 두 장면에서만 SSIM이 낮다(실측: 상태 13~19에서 IoU 0.4).

### Pitfall 2: 폰트가 조용히 대체됨
**What goes wrong:** WenQuanYi로 대체되면 가는 글자·줄바꿈 3줄(실측 이미지) — 오류 없이 영상 생성.
**How to avoid:** goto(file://) + `FontFace.status` + CDP `isCustomFont`; shim/렌더가 이 확인 후에만 진행.
**Warning signs:** `fc-match "Noto Sans CJK KR"`이 Inter/WenQuanYi, 프레임별 SSIM < 0.98.

### Pitfall 3: 장면 경계를 직접 계산해서 맞추려 함
**What goes wrong:** `round(cum*30)`로 경계를 계산하면 10편 중 다수에서 ±1프레임 어긋난다(381.0→382 등).
**How to avoid:** Phase 1은 ffmpeg concat+fps 유지. 경계는 manifest(디코드 검출값)와 비교. 파이프 방식은 Phase 4에서 manifest 일치 시험과 함께.

### Pitfall 4: 바이트·해시 비교
**What goes wrong:** `-threads` 또는 호스트 코어 수가 다르면 MP4 바이트가 달라진다. 시험이 이유 없이 깨진다.
**How to avoid:** 디코드 프레임 SSIM.

### Pitfall 5: 시스템 pip가 없는/막힌 상황에서 훅이 통째로 실패
**What goes wrong:** `set -euo pipefail` 때문에 `pip` 실패가 훅 전체를 중단 → GSD/agent-browser 환경 변수 설정까지 못 하거나 doctor가 안 돎.
**How to avoid:** 새 단계를 기존 단계 **뒤에** 두고, 설치 실패는 메시지만 stderr로 내고 doctor가 원인을 보고(`|| true`는 doctor 호출에만 쓰되, doctor 직접 실행은 비-0 종료).

### Pitfall 6: 이미지가 바뀌어 Chromium 리비전/Playwright 버전이 어긋남
**What goes wrong:** 새 이미지의 브라우저가 1248이면 `1.63.0` 기본 launch 실패.
**How to avoid:** `executable_path` 폴백 체인과 doctor 메시지(어느 경로를 썼는지 출력). 리비전 숫자는 주석에만.

### Pitfall 7: 새 배치 + `keep-all`이 긴 무공백 문자열을 넘치게 함
**What goes wrong:** `word-break: keep-all`은 공백 없는 긴 토큰을 줄바꿈하지 않아 우측 영역을 침범한다.
**How to avoid:** 측정이 `RIGHT`로 잡는다(`right > 930`). 잡히면 경고. (`overflow-wrap:anywhere`는 쓰지 않는다 — 조용히 쪼개져 가독성을 해침.)

### Pitfall 8: 마크업 이스케이프(new 경로)
**What goes wrong:** legacy는 `top`/`basis`를 HTML에 원문 삽입한다(`S&P500`은 브라우저 관용으로 그대로 보임). new 경로에서 LLM이 쓴 문자열에 `<`·`&`가 있으면 DOM이 깨진다.
**How to avoid:** new는 `html.escape` 후 `<g>`/`<s>`만 허용 목록으로 치환(예: 이스케이프된 `&lt;g&gt;`를 되돌림). legacy는 원문 삽입 유지(출력 동일성).

### Pitfall 9: golden 시험이 느려져 안 돌게 됨
**How to avoid:** 빠른 스모크(1편, 약 15 s) + 전체(병렬 4, 약 1~2분) 두 단계. 커밋 훅에서는 스모크만.

### Pitfall 10: 레포 크기
**What goes wrong:** OTF 14.5 MB가 한 번에 들어간다(`.git` 7.4 MB 기준 약 3배 증가 가능). 폰트 파일을 갱신할 때마다 다시 불어난다.
**How to avoid:** 폰트는 고정 버전·sha256으로 바꾸지 않는다. 문제 시 서브셋 대안.

## Code Examples

### 상태 목록(legacy 타임라인)
```python
# Source: HEAD tools/reel.py 로직 그대로 (이 세션 Read) — LINE=0.85, HOLD=1.9
seq = []
for sc in spec["scenes"]:
    n = len(sc["lines"])
    for k in range(1, n + 1):
        seq.append((sc["top"], sc["lines"], k, LINE if k < n else HOLD))
total = sum(x[3] for x in seq)
# 진행 막대 폭: 상태 종료 시점 누적/total  (prog = t/total, "width:{prog*100:.1f}%")
# 표지 시점: cover_ms = int((LINE*(len(first_scene_lines)-1)+0.4)*1000)
```

### doctor의 폰트 점검 (핵심)
```python
# Source: 이 세션 spike (fontcheck_spike.py) — 0.83 s
st = page.evaluate("Promise.all([...document.fonts].map(f=>f.load().then(()=>f.family+' '+f.weight+' '+f.status)))")
assert all(s.endswith(" loaded") for s in st) and len(st) == 3
# + CDP CSS.getPlatformFontsForNode 로 isCustomFont 전부 True 확인 (위 §폰트)
```

### 프레임 비교 (golden)
```python
# Source: 이 세션 spike (cmp_all.py) — stdlib + ffmpeg
subprocess.run(["ffmpeg","-loglevel","error","-i",golden,"-i",new,"-lavfi",
                f"[0:v][1:v]ssim=stats_file={sf}","-f","null","-"], check=True)
vals = [float(re.search(r"All:(\S+)", l).group(1)) for l in open(sf)]
assert len(vals) == expected_frames and min(vals) >= 0.98, min(vals)
```

### faststart 검사
```python
# Source: 이 세션 spike (specprobe.py)
def top_atoms(path):
    out=[]; f=open(path,'rb'); f.seek(0,2); end=f.tell(); pos=0
    while pos+8<=end:
        f.seek(pos); size,typ=struct.unpack('>I4s',f.read(8))
        if size==1: size=struct.unpack('>Q',f.read(8))[0]
        elif size==0: size=end-pos
        out.append(typ.decode('latin1'));
        if size<8: break
        pos+=size
    return out        # faststart ⇔ out.index('moov') < out.index('mdat')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `set_content` + 고정 60 ms 대기 | `goto(file://)` + `FontFace.status`/CDP 확인 | 이 단계 | 폰트 조용한 대체 탐지 |
| 시스템 폰트 'Noto Sans CJK KR' 의존 | 저장소 번들 OTF 3종 | 이 단계 | 새 세션 재현성 |
| 회귀 시험 없음 | 커밋 MP4 대비 구조 정확 + 프레임별 SSIM | 이 단계 | `<s>` 드리프트 같은 문제 조기 탐지 |
| 근거 `bottom:150px` 30px | 본문 아래 36px, 안전영역 박스 | 이 단계(새 릴스만) | UI 가림 해소 |

**Deprecated/outdated:** 조사 STACK의 "Playwright 미설치" 사실 — 이 세션 이미지에는 1.64.1이 이미 있다. 어느 쪽이든 훅은 "버전이 1.63.0이 아니면 설치"로 동작한다.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 안전영역 상단값 270px(경고) — SUMMARY의 y 270~1250에서 가져옴, D-03에 없음 | 새 배치/상수 | 상단 경고 오탐/미탐. 상수 한 곳이라 낮음 |
| A2 | `document.fonts.check()`는 `@font-face`가 없는 패밀리에 대해 true를 돌려준다 | 폰트 | 틀려도 FontFace.status+CDP 이중 확인이라 영향 낮음 |
| A3 | 릴스 길이 3~90초 경고 범위(출처 상충) | ffprobe 검사 | 경고 전용이라 낮음 |
| A4 | 이미지에 `EXTERNALLY-MANAGED`가 생기면 `--user`가 막힐 수 있음 | 훅 | 새 이미지에서 훅 설치 실패 → doctor 메시지로 발견. 중간 |
| A5 | 훅 stdout이 세션 컨텍스트에 들어간다(기존 훅 주석이 그렇게 전제) | 훅 | 틀리면 doctor 요약이 안 보일 뿐 |
| A6 | 업스트림 폰트 커밋 SHA 미확인(sha256만 고정) | 폰트 | 폰트 재다운로드 시 `main`이 바뀌어 해시 불일치 가능 — 무수정 파일을 저장소에 넣으므로 실제 영향 낮음 |
| A7 | 커밋 MP4가 `<s>`=block 렌더러로 만들어졌다는 추정(도구 커밋 순서 기반). 실제 원인(과거 스크립트 차이)은 확인 불가 | Golden | 증거는 재현 결과(SSIM 0.997)이므로 결론에는 영향 없음 |

## Open Questions

1. **HEAD `reel.py`의 `<s>` 동작을 바꿔도 되는가?**
   - What we know: 커밋 MP4는 `<s>`=block과 일치(10/10), HEAD 코드는 불일치. D-05는 "기존 배치 그대로 재현"이라고만 했음.
   - What's unclear: 사용자가 `python3 tools/reel.py`로 만든 *새* 영상이 MP4와 다르게 나오는 현 동작을 원했는지.
   - Recommendation: legacy = 커밋 MP4 재현으로 확정하고 shim 기본값으로 둔다. 플래너가 1줄 확인 체크를 계획에 넣는다.

2. **우측 150px 여백을 본문 줄에도 적용할지.**
   - What we know: 엄격 적용 시 기존 10편의 195줄 중 8줄(4%)이 새 배치에서 줄바꿈된다. 근거·계정만 적용하면 본문 줄 우측 끝이 최대 968px까지 간다.
   - Recommendation: D-03 문구대로 엄격 적용(상수 `SAFE.right`). 생성기(Phase 2)가 한 줄 8~9자 이내로 쓰게 하는 근거가 됨.

3. **경고의 종료 코드 정책.** 경고만 내고 0으로 종료할지, `--strict`에서 비-0으로 낼지. 권고: 기본 0 + 경고 출력, `--strict`/Phase 3 번들 게이트에서 비-0.

4. **폰트 서브셋 여부(재량):** 권고는 무수정 3종(14.5 MB). 레포 크기를 줄이고 싶으면 5.5 MB 서브셋(바이트 동일 렌더 실측) — 사용자 선호 확인 가능.

5. **오버레이 PNG 위치/이름과 어떤 장면을 포함할지** — 플래너 재량(권고: `<out>.safe.png`, 최다 줄 장면 + 첫 장면).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | 전체 | ✓ | 3.13.17 | — |
| playwright (Python) | 렌더 | ✓ (시스템 1.64.1) | 1.64.1 → 1.63.0 필요 | `pip install --user playwright==1.63.0` (PyPI 도달 가능, 실측) |
| Chromium | 렌더 | ✓ | 153.0.8010.12 (rev 1243), `/opt/pw-browsers/chromium` | `executable_path` 폴백 |
| ffmpeg / ffprobe | 인코딩·검사 | ✓ | 6.1.1 | — |
| 한글 폰트 | 렌더 | ✗ (시스템엔 WenQuanYi만) | — | **저장소 번들 OTF** (이 단계의 산출물) |
| raw.githubusercontent.com | 폰트 1회 다운로드 | ✓ | HTTP 200 | 이후 저장소 파일 사용(네트워크 불필요) |
| PyPI | 훅 설치 | ✓ | — | 휠 캐시, 실패 시 doctor 메시지 |
| GitHub API (`gh api`) | 폰트 커밋 SHA 조회 | ✗ (이 세션에서 403) | — | sha256로 고정 |
| fontTools / numpy / pytest | — | fontTools ✗, numpy ✓, pytest ✗ | — | 사용하지 않음 |

**Missing dependencies with no fallback:** 없음.
**Missing dependencies with fallback:** 한글 폰트(번들로 해결), Playwright 1.63.0(훅이 설치).

## Validation Architecture

> `.planning/config.json`의 `workflow.nyquist_validation`이 `false`이므로 표준 Validation Architecture 섹션은 생략한다. 대신 위 "Golden 회귀 설계"와 "시험 구성"이 이 단계의 시험 설계이며, 요구사항별 자동화 명령은 다음과 같다(플래너 참고용).

| Req | 검증 | 명령(제안) |
|-----|------|------------|
| ENV-01 | doctor 종료 코드 0, 일부러 폰트 파일을 이름 바꿔 실패 메시지 확인 | `python3 tools/doctor.py` |
| ENV-02 | 새 venv/`PYTHONUSERBASE`에서 훅 재생 후 렌더 | `CLAUDE_CODE_REMOTE=true .claude/hooks/session-start.sh` (두 번째 실행에서 설치 건너뜀 확인) |
| ENV-03 | golden | `python3 -m unittest tools.tests.test_golden -v` |
| ENV-04/05 | 레이아웃 측정 단위 시험 + bad.json 경고 | `python3 -m unittest tools.tests.test_layout` |
| ENV-06 | specprobe 단위 시험(PASS/FAIL 샘플) | `python3 -m unittest tools.tests.test_specprobe` |

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | 원고 JSON → HTML 삽입 시 `html.escape` + 허용 태그(`<g>`,`<s>`)만 복원(new 경로). 출력 경로·인자는 `subprocess.run(list)`(셸 사용 금지) |
| V6 Cryptography | partial | 폰트 무결성은 `hashlib.sha256` 고정 비교(직접 암호 구현 없음) |
| V10 Malicious Code / 공급망 | yes | `playwright==1.63.0` 고정, `--user` 설치, 폰트 sha256 고정, 훅에서 `curl | sh` 금지 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 원고 문자열을 통한 HTML/스크립트 주입(렌더 페이지에서 `file://` 접근) | Tampering / Info disclosure | new 경로에서 이스케이프. 렌더 페이지는 `file://` 이므로 `<script>`/`<img src=file://…>`가 로컬 파일을 읽을 수 있다 → 이스케이프 필수, `page.route`로 외부 요청 차단 고려 [ASSUMED: 위협 추정, 이 세션에서 공격 재현은 안 함] |
| `ffmpeg` 인자에 사용자 경로 삽입 | Tampering | 리스트 인자, 경로 그대로 전달, 셸 미사용. 출력 파일명은 그대로 쓰되 `-y` 덮어쓰기에 주의(golden은 임시 폴더만) |
| 훅이 매 세션 외부에서 코드를 받아 실행 | Elevation / Supply chain | 버전 고정 + 이미 존재 시 건너뜀. 폰트는 저장소 안 파일 |
| 사전 점검 실패를 가려서 조용한 대체 | Repudiation / 신뢰성 | doctor 실패 시 원인 메시지, shim이 폰트 불일치면 중단 |

## Project Constraints (from CLAUDE.md)

`./.claude/CLAUDE.md`에서 이 단계에 해당하는 지시(PROJECT.md 발췌 포함):
- **브랜드:** 기존 10편과 같은 색감·폰트·레이아웃 유지(시리즈 일관성) → legacy 경로는 색 `#DEE9E0/#2F4F3E/#B08D46/#5B6E62` 유지, 새 배치도 폰트·색·본문 레이아웃 유지.
- **기술 스택:** 기존 Python + Playwright + ffmpeg 확장. 새 의존성 최소.
- **환경:** 클라우드 네트워크 정책상 외부 다운로드 제한 → 사전 설치 Chromium 사용, 브라우저 다운로드 금지.
- **비용:** API 키·유료 서비스 금지.
- **개인정보/컴플라이언스/검수:** 이 단계는 렌더 인프라라 직접 영향 없음(근거 표기 가림 해소는 컴플라이언스 관련).
- **GSD 워크플로 강제:** 직접 편집 전에 GSD 명령(`/gsd-execute-phase` 등)으로 시작.
- **프로젝트 스킬:** `.claude/skills/`에 `agent-browser`, `design-taste-frontend`, `find-skills`, `mcp-builder`가 있으나 이 단계 구현 패턴과 직접 관련 없음(agent-browser는 기존 훅이 `AGENT_BROWSER_EXECUTABLE_PATH`를 설정 — 훅 수정 시 그 줄 유지).

## Sources

### Primary (HIGH confidence)
- 로컬 코드/자산 (Read): `tools/reel.py`, `tools/cards.py`, `tools/README.md`, `.claude/hooks/session-start.sh`, `.claude/settings.json`, `2026/reels/specs/*.json`, `.planning/{PROJECT,REQUIREMENTS,STATE,ROADMAP}.md`, `.planning/research/{SUMMARY,STACK,PITFALLS,ARCHITECTURE}.md`
- 이 세션 컨테이너 실측(2026-10-28): playwright 1.64.1(시스템) 기본 launch 실패/1.63.0 성공, `pip --user` 우선순위, 폰트 3종 다운로드·cmap·메트릭, 번들 폰트 vs 커밋 MP4 10편 비교(프레임·경계·SSIM·PSNR), 대조군 4종, 진짜 Noto Sans CJK KR OTF를 scratch fontconfig로 설치한 대조 렌더, headless-shell vs 풀 Chrome 바이트 동일, 스레드별 바이트 차이/SSIM 1.0, 레이아웃 측정·오버레이, ffprobe 규격 검사 샘플, CDP 플랫폼 폰트
- PyPI JSON `pypi.org/pypi/playwright/1.63.0/json`, `pypi.org/pypi/playwright/json` — 저자·project_urls·업로드일·릴리스 수
- `gsd-tools query package-legitimacy check`(SUS 판정 출력 그대로 기재)

### Secondary (MEDIUM confidence)
- 조사 문서의 Instagram 안전영역 수치(2차 자료, [CONFLICTING]) — 값은 D-03이 확정, 보정은 실기기

### Tertiary (LOW confidence)
- 업스트림 폰트 커밋 SHA(미확인), `document.fonts.check()` 의미(기억 기반), 이미지 변화 시 pip 정책(미관측)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 전부 이 컨테이너에서 실행해 확인. SUS는 seam 판정 그대로 기재.
- Architecture / golden 설계: HIGH — 10편 전수 비교 + 대조군. 임계값은 정상/대조군 분포 사이.
- Pitfalls: HIGH(실측 항목) / MEDIUM(이미지 변화 대응)
- 안전영역 픽셀 값: MEDIUM — D-03 확정값이지만 실기기 미검증(사람 몫)

**Research date:** 2026-10-28
**Valid until:** 이미지(Chromium/Playwright 버전)가 바뀌면 재확인. 그 전까지 30일.
