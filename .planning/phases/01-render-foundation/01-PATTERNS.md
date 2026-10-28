# Phase 1: 렌더 기반 고정 (Render Foundation) - Pattern Map

**Mapped:** 2026-10-28
**Files analyzed:** 22 (신규 19, 수정 3)
**Analogs found:** 8 / 22 (나머지는 코드베이스에 유사 파일이 없어 RESEARCH.md spike 코드를 기준으로 함)

저장소에는 파이썬 도구가 `tools/reel.py`(39줄)와 `tools/cards.py`(33줄) 두 개뿐이고 테스트, 패키지, 설정 모듈이 없다. 따라서 "코드베이스 analog"는 사실상 `tools/reel.py`, `tools/cards.py`, `.claude/hooks/session-start.sh`, `.claude/settings.json`, `2026/reels/specs/*.json` 다섯 개이며, 나머지는 RESEARCH.md의 검증된 spike 코드를 따른다. 모든 analog 경로는 `git ls-files`로 추적 확인함 (미러 경로 없음).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/reel.py` (수정: shim) | CLI entry | request-response | `tools/reel.py` 현행 (자기 자신) | exact (보존 대상) |
| `tools/reelkit/render.py` | service | batch / file-I/O | `tools/reel.py` `main()` L24-38 | exact |
| `tools/reelkit/layout.py` (legacy + new 프레임 HTML, 측정) | utility | transform | `tools/reel.py` `frame()` L14-23 | exact (legacy) / no analog (new, 측정 JS) |
| `tools/reelkit/encode.py` | service | file-I/O | `tools/reel.py` L35-37 | exact |
| `tools/reelkit/timeline.py` | utility | transform | `tools/reel.py` L25-27 | exact |
| `tools/reelkit/spec.py` | utility | transform | `tools/reel.py` L25 + `2026/reels/specs/*.json` | role-match |
| `tools/reelkit/constants.py` | config | - | `tools/reel.py` L13, `tools/cards.py` L12 | role-match |
| `tools/reelkit/browser.py` (launch 폴백 체인) | utility | request-response | `tools/reel.py` L29-30 | partial |
| `tools/reelkit/doctor.py` + `tools/doctor.py` | service / CLI | request-response | `.claude/hooks/session-start.sh` (검사/보고 스타일) | partial |
| `tools/reelkit/specprobe.py` (ENV-06) | utility | transform | 없음 | no analog |
| `tools/reelkit/templates/frame.html` | config/template | - | `tools/reel.py` L19 의 HTML | partial |
| `tools/fonts/*.otf`, `OFL.txt`, `README.md` | asset | - | 없음 | no analog |
| `tools/requirements.txt` | config | - | `.claude/skills/mcp-builder/scripts/requirements.txt` (형식만) | partial |
| `tools/tests/test_golden.py` | test | batch | 없음 (저장소에 테스트 없음) | no analog |
| `tools/tests/test_specprobe.py`, `test_layout.py`, `test_doctor.py` | test | - | 없음 | no analog |
| `tools/tests/golden/manifest.json` | fixture | - | 없음 | no analog |
| `.claude/hooks/session-start.sh` (수정) | hook | event-driven | 자기 자신 | exact |
| `.gitignore` (신규) | config | - | 없음 (현재 없음) | no analog |
| `tools/README.md` (수정, 문서) | doc | - | 자기 자신 | exact |

## Pattern Assignments

### `tools/reel.py` -> shim (CLI entry, request-response)

**Analog:** `tools/reel.py` 현행. 인자 규약과 stdout 한 줄 형식을 그대로 유지해야 한다 (CONTEXT: 기존 사용법 보존).

**진입점/출력 계약** (L39, L38):
```python
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
...
first=len(s["scenes"][0]["lines"]); print(f"duration={total:.1f}s cover_ms={int((LINE*(first-1)+0.4)*1000)}")
```
shim은 `sys.path`에 `tools/`가 올라가므로 `from reelkit import ...`로 위임하고, 기본 레이아웃은 legacy. docstring(L1-10, spec 예시와 `<g>`/`<s>` 설명)은 shim에 남긴다. 폰트 로드 실패 시 조용히 대체하지 말고 중단(RESEARCH §shim).

---

### `tools/reelkit/layout.py` + `templates/frame.html` (transform)

**Analog:** `tools/reel.py` `frame()` L14-23. legacy 경로는 이 HTML을 그대로 옮기되 RESEARCH가 확정한 변경점만 적용한다.

**legacy 프레임 원본** (L16-23):
```python
for i,l in enumerate(lines):
    l=l.replace("<g>",f'<span style="color:{GOLD}">').replace("</g>","</span>").replace("<s>",'<span style="font-size:52px;font-weight:700;color:#5B6E62">').replace("</s>","</span>")
    out+=f'<div style="opacity:{1 if i<k else 0}">{l}</div>'
return f'''<body style="margin:0"><div style="width:1080px;height:1920px;background:{SAGE};display:flex;flex-direction:column;justify-content:center;padding:0 96px;gap:40px;font-family:'Noto Sans CJK KR',sans-serif;box-sizing:border-box;position:relative">
<div style="position:absolute;left:0;top:0;height:14px;width:{prog*100:.1f}%;background:{DG}"></div>
<div style="font-size:50px;font-weight:700;color:{DG};min-height:60px">{top}</div>
<div style="font-size:100px;font-weight:900;line-height:1.3;letter-spacing:-.03em;color:{DG};display:flex;flex-direction:column">{out}</div>
<div style="position:absolute;left:96px;right:96px;bottom:150px;display:flex;justify-content:space-between;font-size:30px;color:#5B6E62"><span>{basis}</span><b>@kiwoom.mentor</b></div></div></body>'''
```
**legacy에서 바꿀 것만 (RESEARCH §legacy 렌더러 변경점):**
- `<s>` 치환: `<span style="display:block;font-size:52px;font-weight:700;color:#5B6E62">` (display:block 추가가 핵심, 커밋 MP4 재현)
- `font-family:'Noto Sans KR'` + 번들 `@font-face` (템플릿에 400/700/900), `set_content` 대신 `goto(file://)` 후 `document.body.innerHTML` 교체
- 그 외(색, 진행 막대 14px, `bottom:150px`, 30px, `gap:40px`, `padding:0 96px`) 바이트 단위로 동일. `word-break:keep-all`은 legacy 금지(new 전용).

**new 레이아웃:** 동일 구조에 RESEARCH §새 배치의 `#stack`(left 96, right 150, top 270, height 980, flex column center, gap 40, keep-all)를 사용. 본문 줄 `opacity:0`도 레이아웃 참여 성질은 legacy 패턴(`opacity:{1 if i<k else 0}`)을 그대로 유지. 치수는 `constants.py`의 SAFE/BASIS_PX를 참조.

**측정 JS:** analog 없음. RESEARCH L414-422 (`textRects`, `lineCount`) spike 코드를 그대로 사용.

---

### `tools/reelkit/render.py` (batch, file-I/O)

**Analog:** `tools/reel.py` `main()` L24-38.

**프레임 시퀀스/스크린샷 루프** (L25-34) - 이 구조를 유지하고 launch, goto, innerHTML만 교체:
```python
s=json.load(open(spec,encoding="utf-8")); seq=[]
for sc in s["scenes"]:
    for k in range(1,len(sc["lines"])+1): seq.append((sc["top"],sc["lines"],k,LINE if k<len(sc["lines"]) else HOLD))
total=sum(x[3] for x in seq); t=0; d=tempfile.mkdtemp(); files=[]
with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={"width":1080,"height":1920})
    for n,(top,lines,k,dur) in enumerate(seq):
        t+=dur; pg.set_content(frame(top,lines,k,t/total,s.get("basis",""))); pg.wait_for_timeout(60)
        f=f"{d}/v{n:03d}.png"; pg.screenshot(path=f); files.append((f,dur))
    b.close()
```
**대체 대상 (RESEARCH Pattern 1, L175-182):**
```python
page.goto("file://" + str(tpl_path.resolve()))
page.evaluate("h=>{document.body.innerHTML=h}", inner_html(...))
page.evaluate("document.fonts.ready.then(()=>0)")
page.screenshot(path=f"{work}/v{n:03d}.png")
```
`pw.chromium.launch()`는 `reelkit.browser.launch(pw)`로, `wait_for_timeout(60)`은 `fonts.ready`로 교체. 진행률은 `t/total`(누적, 상태 종료 시점 기준) 그대로. 임시 폴더는 `tempfile.mkdtemp()` 유지(D-08, 저장소 안에 쓰지 않음).

---

### `tools/reelkit/encode.py` (file-I/O)

**Analog:** `tools/reel.py` L35-37. **인자를 한 글자도 바꾸지 말 것** (상태 경계가 ffmpeg `fps` 반올림에 의존, RESEARCH Pitfall 3 / Pattern 2).
```python
open(f"{d}/seq.txt","w").write("".join(f"file '{f}'\nduration {du}\n" for f,du in files)+f"file '{files[-1][0]}'\n")
subprocess.run(["ffmpeg","-loglevel","error","-y","-f","concat","-safe","0","-i",f"{d}/seq.txt","-f","lavfi","-i","anullsrc=r=44100:cl=stereo",
  "-vf","fps=30,format=yuv420p","-c:v","libx264","-crf","20","-c:a","aac","-shortest","-t",f"{total:.2f}","-movflags","+faststart",out],check=True)
```
오류 처리는 `check=True`(CalledProcessError 전파)가 기존 방식. doctor/CLI 층에서만 원인 메시지로 변환.

---

### `tools/reelkit/timeline.py`, `spec.py` (transform)

**Analog:** `tools/reel.py` L25-27 (장면->상태 목록 전개). 원고 v1 스키마는 `2026/reels/specs/*.json`이 정의 (읽기 전용, 수정 금지 D-05):
```json
{"basis":"100만 원 공제 예시 · 지방소득세 포함","scenes":[
{"top":"연말정산 바로 알기","lines":["소득공제 vs 세액공제","<g>뭐가 더 유리할까?</g>"]},
...,
{"top":"","lines":["저장해두고","내 세율 구간부터","확인해 보세요","<s>프로필 링크 · 1분 노후자금 계산기</s>"]}]}
```
타임라인 항목은 `(top, lines, k, dur)` 튜플 계약 유지, `dur = LINE if k<len(lines) else HOLD`. cover_ms 공식: `int((LINE*(first-1)+0.4)*1000)` (L38).

---

### `tools/reelkit/constants.py` (config)

**Analog:** `tools/reel.py` L13 와 `tools/cards.py` L12 (같은 브랜드 색을 각자 정의 중 - 공통 상수로 뺄 후보).
```python
SAGE="#DEE9E0"; DG="#2F4F3E"; GOLD="#B08D46"; LINE=0.85; HOLD=1.9        # reel.py L13
SAGE="#DEE9E0"; DG="#2F4F3E"; INK="#1B2A22"; MUT="#5B6E62"; GOLD="#B08D46"  # cards.py L12
```
새 값(SAFE, BASIS_PX=36, BASIS_MAX_LINES=2, ACCT_PX=36)은 RESEARCH Pattern 3(L200-207)을 그대로 옮긴다. `cards.py`는 이 단계에서 수정하지 않는다 (RESEARCH: 변경 없음). legacy가 쓰는 `#5B6E62`는 하드코딩이므로 `MUT`로 상수화하되 값 불변.

---

### `tools/reelkit/browser.py` (launch 폴백 체인)

**Analog (부분):** `tools/reel.py` L30 `pw.chromium.launch()` 한 줄 + `.claude/hooks/session-start.sh` L20-23 의 Chromium 경로 처리.
```bash
# Chrome 다운로드는 네트워크 정책에 막히므로 미리 설치된 Chromium을 쓰게 한다
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -x /opt/pw-browsers/chromium ]; then
  echo 'export AGENT_BROWSER_EXECUTABLE_PATH=/opt/pw-browsers/chromium' >> "$CLAUDE_ENV_FILE"
fi
```
체인: 기본 `launch()` -> `AGENT_BROWSER_EXECUTABLE_PATH` -> `/opt/pw-browsers/chromium` -> glob `/opt/pw-browsers/chromium-*/chrome-linux*/chrome` (RESEARCH §doctor #2). 리비전 번호 하드코딩 금지. doctor, render, 시험이 모두 이 함수를 공유.

---

### `tools/doctor.py` + `tools/reelkit/doctor.py` (CLI, request-response)

**Analog (스타일만):** `.claude/hooks/session-start.sh` - 얇은 진입 스크립트, 상세 출력은 stderr, 요약 한 줄만 stdout. `tools/doctor.py`는 `from reelkit.doctor import main`만. 검사 6항목과 메시지는 RESEARCH L374-381 표, CDP 폰트 대체 탐지 코드는 L332-337 사용. 옵션 `--quiet|--json`, 종료 코드 0 = 정상. 진입 스크립트와 같은 이름의 패키지/모듈 충돌 주의 (`tools/reelkit.py` 만들지 말 것).

---

### `.claude/hooks/session-start.sh` (수정, event-driven)

**Analog:** 자기 자신. 기존 관례를 따른다.

**관례** (L1-8, L11-13):
```bash
#!/bin/bash
# ... 설치 출력은 세션 컨텍스트에 섞이지 않도록 stderr로 보낸다.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# GSD: 전역(~/.claude)에 설치
if [ ! -d "$HOME/.claude/skills/gsd-help" ]; then
  npx --yes @opengsd/gsd-core@latest --claude --global >&2
fi
```
추가분은 파일 끝(L23 뒤)에 같은 스타일(한국어 주석, `>&2`, idempotent 가드)로 붙인다. 골격은 RESEARCH L359-368. 주의: `set -e` 때문에 pip 실패 시 훅이 중단되므로 `if ! pip ...; then ...; fi`로 감싸고, 마지막 `python3 tools/doctor.py --quiet || true`로 항상 0 종료. `.claude/settings.json`의 SessionStart 등록은 이미 존재하므로 수정 불필요.

---

### `tools/requirements.txt`

한 줄: `playwright==1.63.0`. 훅이 `sed -n 's/^playwright==//p'`로 파싱하므로 이 형식을 정확히 지킬 것 (주석/공백 금지). analog 없음(형식 참고로 `.claude/skills/mcp-builder/scripts/requirements.txt`가 있으나 무관).

---

### `tools/specprobe.py` 계열 / `tools/tests/*` / fonts / `.gitignore` / manifest

저장소에 analog 없음 - RESEARCH를 직접 사용:
- specprobe: 항목표 L431-441, faststart는 MP4 최상위 atom 8바이트 헤더 순회(size==1 64비트, size==0 파일 끝). stdlib + ffprobe `-show_streams -show_format -of json`만.
- 테스트: `unittest`(pytest 없음), Pillow/numpy 사용 금지. 경계 검출/SSIM 명령은 RESEARCH L277-286. 실행: `python3 -m unittest discover -s tools/tests -v`. 출력은 `tempfile.mkdtemp()`, `2026/reels/`에 쓰지 않음. 임계값: 프레임 수/duration/경계 정확 일치, 프레임별 SSIM >= 0.98.
- 원고 없는 MP4(`2026/reels/2026-10-19-savings-interest.mp4`)는 manifest에 `"status": "not-reproducible"`, 보고서에 "재현 불가" 출력, ENV-06 검사는 수행.
- 폰트: sha256/URL은 RESEARCH L298-310 표. 무수정 벤더링.
- `.gitignore`: RESEARCH L456-461 항목 (현재 파일 없음).

## Shared Patterns

### 한국어 주석/docstring + 한 줄 요약 출력
**Source:** `tools/reel.py` L1-10, L38; `tools/README.md`
**Apply to:** 모든 신규 모듈/CLI. 사용자 대면 메시지는 한국어, 경고 형식은 `scene N line M: <kind> (<value>)`.

### 오류 처리 (최소주의)
**Source:** `tools/reel.py` L36-37 (`subprocess.run(..., check=True)`), 그 외 try/except 없음.
**Apply to:** encode/render. 예외는 전파하고, 원인 메시지 변환은 doctor와 CLI 최상단 한 곳에서만. 레이아웃 경고(ENV-05)는 렌더를 중단하지 않고 stderr/보고로 (RESEARCH L423).

### 임시 산출물은 시스템 tmp
**Source:** `tools/reel.py` L28 `d=tempfile.mkdtemp()`
**Apply to:** render, 시험. 저장소 안 경로(`2026/reels/drafts/`, `.render-work/`)는 `.gitignore` 대상 (D-08).

### 출력 경로/원고 위치 규칙
**Source:** `2026/reels/<게시일>-<영문-슬러그>.mp4`, `2026/reels/specs/<같은 이름>.json`
**Apply to:** 시험의 spec<->MP4 짝짓기 (파일명 stem 일치).

### 상수 한 곳
**Source:** `tools/reel.py` L13 -> `tools/reelkit/constants.py`
**Apply to:** layout, render, 측정. 안전영역 숫자는 이 파일 외 하드코딩 금지 (D-03).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tools/reelkit/specprobe.py` | utility | transform | ffprobe/atom 검사 코드 없음 |
| `tools/tests/**` | test | batch | 저장소에 테스트 전무 |
| `tools/fonts/*` | asset | - | 벤더링 폰트 없음 |
| `.gitignore` | config | - | 파일 없음 |
| `tools/reelkit/layout.py` 측정부(JS) | utility | transform | 브라우저 내 측정 코드 없음 |

플래너는 위 파일에 RESEARCH.md의 spike 코드와 표를 사용한다.

## Metadata

**Analog search scope:** `tools/`, `.claude/hooks/`, `.claude/settings.json`, `2026/reels/specs/`, 저장소 전체 `git ls-files` (파이썬 파일은 tools/ 두 개뿐)
**Files scanned:** reel.py, cards.py(헤더), session-start.sh, settings.json, specs 1편, git ls-files 전체. RESEARCH.md는 L1-462만 읽음(L463 이후 미확인: Open Questions, Pitfalls 등)
**Pattern extraction date:** 2026-10-28
