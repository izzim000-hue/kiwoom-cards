# Phase 4: 자막 연출 + 선택 배경음 (Motion & BGM) - Research

**Researched:** 2026-10-29
**Domain:** Python + Playwright(Chromium) 결정적 시간 탐색 렌더, ffmpeg 이미지 파이프 인코딩·오디오 필터, 기존 reelkit 파이프라인(expand/check/render/bundle/review/approve) 확장
**Confidence:** HIGH (렌더·줄바꿈·카운트업·BGM 필터 모두 이 컨테이너에서 실측), MEDIUM (체류 시간 계수는 게시된 10편에 맞춘 값이라 사람 판단이 필요)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 렌더는 Phase 1의 결정적 시간 탐색 방식(Web Animations 일시정지 + `currentTime` 설정, 프레임마다 PNG)을 그대로 쓴다. 실시간 녹화(`record_video`)는 쓰지 않는다.
- **D-02:** 줄 진입: 각 줄이 약 300ms 동안 투명도 0→1, 아래에서 약 24px 위로 올라오며 나타난다. 줄 사이 간격은 약 120ms. 줄 단위 애니메이션으로 하고 글자(자소) 단위 분리는 하지 않는다 — 한글 줄바꿈 위치가 흔들리지 않게 하기 위해서다. 줄바꿈은 모션 없이 측정한 배치를 기준으로 고정한다.
- **D-03:** 장면 전환 1종: 약 0.3초 크로스페이드(이전 장면 페이드아웃과 다음 장면 페이드인 겹침). 슬라이드·와이프는 넣지 않는다.
- **D-04:** 카운트업: 원고의 등록부 수치 자리(`spec.json` 장부)에 선택 표시를 하면 0(또는 지정 시작값)에서 최종값까지 약 0.8초 동안 올라간다. 숫자 상자는 최종값 기준 고정 너비로 잡아 줄이 흔들리지 않게 한다. 마지막 프레임의 글자는 원고 표시 문자열과 한 글자까지 같아야 한다(테스트). 중간 값은 표시 서식(만, %, 원)을 따르고 반올림은 표시에서만 한다.
- **D-05:** 모션 선택은 원고 선택 필드 `motion`(Phase 2에서 예약됨)과 렌더 옵션으로 한다. 값은 `none`(기본, 기존 결과와 동일)과 `basic`(D-02~D-04) 둘. 기존 10편과 기존 초안은 `none`으로 렌더되어 golden이 바뀌지 않는다. — **Reversibility:** reversible
- **D-06:** 장면 체류 시간(MOTN-05): `basic`일 때 글자 수 기준으로 자동 계산한다(줄 진입·카운트업 시간 + 읽기 시간). 너무 짧거나(예: 1.5초 미만) 긴(예: 6초 초과) 장면은 렌더 시 경고한다. 기준값은 상수 한 곳에 둔다. `none`은 기존 timeline 규칙을 그대로 쓴다.
- **D-07:** 표지(cover_ms)와 장면 모음 정지 화면은 모션이 끝난 장면의 마지막 상태를 쓴다(Phase 3 frame_sink 유지).
- **D-08:** 오너 게이트(음원·라이선스)는 미결정이다. 배경음은 **기본 비활성**이며, 사용자가 음원 파일 경로와 라이선스 메모를 함께 줄 때만 켜진다. 라이선스 메모가 없거나 비어 있으면 렌더를 거부한다(종료 코드 1).
- **D-09:** 음원은 절대 검색·다운로드·기본값으로 넣지 않는다. 음원 파일은 저장소에 커밋되지 않게 `.gitignore`로 막고, 초안 폴더 안이나 저장소 밖 경로만 받는다. 테스트는 ffmpeg로 만든 합성 음(사인파)만 쓴다.
- **D-10:** 믹싱: ffmpeg 필터로 영상 길이에 맞춰 반복·자르기, 페이드인·아웃(약 1초), 음량 정규화(목표 약 −16 LUFS, 피크 −1.5 dBTP). 배경음이 있어도 업로드 규격 검사(AAC 포함)를 통과해야 한다. 없으면 기존 무음 트랙 유지.
- **D-11:** 검수 요약(`review.md`)의 "음원 라이선스" 확인 항목에 음원 파일 이름과 라이선스 메모를 그대로 적고 사람 확인 대상으로 둔다. 승인 지문에 음원 파일 해시를 포함한다.
- 새 릴스는 `--layout new`, 기존 게시 파일은 건드리지 않음, golden 10/10 유지.
- 사용량 절약: 계획 검토·재리뷰 없이 코드 리뷰 1회, 최종 검증 1회.

### Claude's Discretion
- 정확한 이징 곡선, 줄 간 지연, 카운트업 표시 방식(원고 문법 또는 장부 플래그).
- 체류 시간 공식의 계수, 경고 기준값.
- 배경음 옵션 이름과 라이선스 메모 저장 형식.

### Deferred Ideas (OUT OF SCOPE)
- 배경음 실제 음원·라이선스 증빙 형식 — 오너 게이트, 사용자 결정 대기
- 미니 그래프, AI 내레이션 — v2
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOTN-01 | 각 줄 페이드+살짝 떠오름(250~350ms) | 줄 단위 `el.animate()` 300ms/24px/120ms 간격 — 실측: 줄 사각형·줄 수가 모션 없는 배치와 동일 (Pattern 2, 3) |
| MOTN-02 | 장면 전환 1종 0.3초 | 장면별 레이어 + 불투명도 크로스페이드 0.3초 (Pattern 2) |
| MOTN-03 | 카운트업, 마지막 값 = 원고 숫자 | 원고 소스 `{{ref\|fmt\|up}}` → 장부 `countup:true`, 고정 너비 상자, `calc.FORMATS` 로 중간 글자 (Pattern 4) |
| MOTN-04 | `none` 은 기존과 같은 결과 | `none` 경로 코드·인자 무변경, 모션은 별도 함수·인코더 (Architecture) |
| MOTN-05 | 체류 시간 자동 + 경고 | 글자 수 공식 `dur = settle + 0.6 + chars/16 (+0.3)`, 경고 <1.5s / >6s (Pattern 5) |
| MOTN-06 | 음원+라이선스 메모, 거부, 커밋 금지 | `bgm.py` 검증·복사, ffmpeg 필터 그래프, .gitignore, approve 지문 (Pattern 6) |
</phase_requirements>

## Summary

짧은 spike 결과(스크래치패드에서만 실행, 소스 무변경) 세 가지 위험은 모두 해소됐다. (1) 줄 단위 투명도+`translateY` 는 레이아웃에 참여하지 않아서, 7장면(줄바꿈 3줄 짜리 줄 포함 8장면) 시험에서 모션 DOM 의 줄 사각형(`n,l,r,t,b`)이 모션 없는 `new_inner_html` 배치와 **전부 일치**했고, 진입 중간(+0.15s)에도 줄 수·너비가 같고 세로 이동만 0~24px 이었다. 자소 단위 분리(`Intl.Segmenter`)는 필요 없다. (2) 카운트업 상자는 "최종 글자 너비를 `getBoundingClientRect` 로 한 번 재서 `inline-block; width` 로 고정"하는 방식으로 30프레임 내내 상자 너비·왼쪽 위치·줄 높이가 상수였고, 마지막 프레임의 줄 `textContent` 가 원고 글자와 같았다. (3) 740프레임(24.7초) 7장면 릴스는 렌더+인코딩 **72.8초**(4코어, ffmpeg 동시 실행)로 10분 예산의 8분의 1이다. 단 장면 7개 레이어를 모두 켜 두면 프레임당 160ms 로 2.5배 느려지므로 **보이는 시간대가 아닌 레이어는 `display:none`** 해야 한다.

설계의 핵심: 모션은 `none` 경로를 건드리지 않는 별도 경로(`render_motion`, `motion.py`, 파이프 인코더)로 추가하고, 장면마다 하나의 레이어(`new_inner_html` 과 같은 스택 마크업)를 쌓아 `document` 전체 시간 `t` 의 순수 함수로 렌더한다. 줄바꿈 측정·안전영역 경고·오버레이는 기존 정적 최종 상태 경로를 그대로 재사용한다. 체류 시간은 게시된 10편(21.8~26.1초)에 맞춰 `읽기 = 0.6 + 글자수/16` 으로 잡으면 10편 모두 21.5~26.7초(하우스 패턴 21~27초 안), 장면별 2.0~5.3초라 경고 0건이다.

**Primary recommendation:** `motion: basic` 은 `layout=new` 전용 별도 렌더 경로로 구현하고(레거시+basic 은 입력 오류 1), 카운트업은 원고 소스 문법 `{{ref|fmt|up}}` 로 표시해 장부에 `countup:true` 를 남기며, 배경음은 `bgm.py` 가 검증·복사·`bgm.json` 기록 후 같은 ffmpeg 호출의 필터 그래프로 섞고 approve 지문에 오디오 해시를 넣는다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 모션 원고 필드·카운트업 표시 | 원고 소스 → expand(Python) | check(재계산 검증) | 숫자는 expand 만 만든다 (장부가 유일한 출처) |
| 시간표(체류·전환·카운트업) | Python `motion.py` (순수 계산) | — | 브라우저 없이 시험 가능, review·cover_ms·check 가 같은 값을 써야 함 |
| 프레임 합성(진입·전환·카운트업) | Chromium(Web Animations, `t` 탐색) | Python(프레임 루프, 카운트업 글자) | 결정적 탐색, 중간 글자 서식은 `calc.FORMATS` 권위 유지 |
| 줄바꿈·안전영역 경고 | 기존 정적 최종 상태 측정(`_scene_checks`) | — | 모션 없는 배치가 줄바꿈 기준 (D-02) |
| 인코딩·BGM 믹스 | ffmpeg 한 프로세스(stdin PNG 파이프) | Python `encode.py` | 영상·오디오 필터 그래프 한 번에 |
| 음원 검증·라이선스 기록·해시 | Python `bgm.py` (stdlib+ffprobe) | approve/bundle | 승인 지문 체계에 편입 |
| 업로드 규격 검사 | 기존 `specprobe.probe` | — | 변경 없음, 9/9 실측 |

## Standard Stack

신규 패키지 없음. 이 세션에서 설치·동작을 확인한 것만 쓴다.

| Library / Tool | Version | Purpose | Provenance |
|----------------|---------|---------|------------|
| Playwright (Python) | 1.63.0 (설치됨) | Chromium 구동, 스크린샷 | [VERIFIED: `pip list` → `playwright 1.63.0`] |
| Chromium | `/opt/pw-browsers/chromium-1243` (launch 는 `browser.launch` 폴백으로 `/opt/pw-browsers/chromium` 사용) | 렌더 | [VERIFIED: spike 출력 `launch /opt/pw-browsers/chromium`] |
| ffmpeg / ffprobe | 6.1.1-3ubuntu5, libmp3lame·aac·loudnorm·aloop·afade 사용 가능 | 인코딩, BGM 믹스, 음원 검증 | [VERIFIED: `ffmpeg -version`; 필터 그래프 실행] |
| Pillow, numpy | 설치됨 | 시험용 픽셀 비교만 (렌더 경로에는 쓰지 않음) | [VERIFIED: spike 실행] |
| Python stdlib (`decimal`, `re`, `hashlib`, `subprocess`) | 3.13 | 시간표·카운트업 글자·해시 | [VERIFIED: 기존 코드가 같은 방식] |

**Package Legitimacy Audit:** 이 단계는 외부 패키지를 설치하지 않는다 (Playwright 1.63.0 은 Phase 1 에서 고정·설치됨). 해당 없음.

**Alternatives (CLAUDE.md 에서 이미 기각):** `record_video`, MoviePy/pydub, Remotion, `xfade`(전환은 브라우저 안에서), Pillow 텍스트 렌더, 외부 음원 검색 — 쓰지 않는다. [CITED: .claude/CLAUDE.md "What NOT to use"]

## Architecture Patterns

### 결정: `none` 은 건드리지 않고 `basic` 은 옆에 추가

현재 `render_reel` 은 상태(줄 수 k)마다 스크린샷 → `encode_concat`(concat+fps=30) 이다. [VERIFIED: tools/reelkit/render.py:124-181, encode.py:19-50]
`none` 경로의 코드·ffmpeg 인자(`-vf fps=30,format=yuv420p -c:v libx264 -crf 20 ... anullsrc`)는 golden 장면 경계 프레임이 `fps` 필터 반올림에 의존한다고 encode.py 머리말이 밝힌다 — **절대 바꾸지 않는다.** BGM 은 `none` 에도 붙을 수 있으니 `encode_concat` 에 `bgm=None` 선택 인자를 더하되 `bgm is None` 이면 현재와 **같은 인자 목록**을 만든다(시험: 인자 리스트 동일성).

```
spec.json(motion=basic) ──► render_reel(layout=new)
                               │ motion.resolve(spec) → "none" | "basic" (그 밖은 SpecError → 종료 1; legacy+basic 은 입력 오류 1)
                               ├─ none ──► 기존 상태 루프 + encode_concat  (무변경)
                               └─ basic ─► [정적 패스] 장면 최종 상태마다 _scene_checks/오버레이 (스크린샷 없음)
                                           [모션 패스] 한 페이지에 장면 레이어 N개 + Web Animations
                                             for f in 0..nframes-1:
                                               t=f/30 → SEEK_JS(t, 카운트업 글자) → page.screenshot(png)
                                               ├─ f == 장면 i 최종 프레임 → frame_sink(i, png 파일)   (D-07)
                                               └─ ffmpeg stdin.write(png)
                                           ffmpeg: image2pipe -framerate 30 + (anullsrc | bgm 필터 그래프)
                                         ──► specprobe.probe(out)  (9항목, 변경 없음)
```

### 권장 파일 변경 (신규는 ★)

```
tools/reelkit/
├── motion.py ★   상수(ENTER/STAGGER/RISE/CROSS/COUNT/읽기 계수/경고 기준) + schedule(spec) + resolve(spec) + dwell_warnings + SEEK/BUILD JS
├── bgm.py ★      validate_bgm(path, memo, draft_dir) → BgmInfo, filter_graph(T), 예외 BgmError(→ 종료 1)
├── layout.py     new_inner_html 의 스택 부분을 stack_inner_html() 로 추출(출력 바이트 동일) + 카운트업 span 지원 (모션 DOM 이 같은 마크업 재사용)
├── render.py     render_reel(..., motion=None, bgm=None): none 은 무변경, basic 은 _render_motion()
├── encode.py     encode_concat(bgm=None) 무변경 보장 + encode_pipe() ★ (Popen, image2pipe)
├── expand.py     ALLOWED_KEYS += "motion"; PLACEHOLDER 에 선택 3번째 조각 |up; 장부 항목에 countup:true
├── check.py      SOURCE_KEYS += "motion"; DURATION 경고는 basic 이면 motion.total 사용
├── stills.py     scene_times(spec): basic 이면 motion.schedule 의 final_t
├── timeline.py   무변경 (cover_ms 는 render 가 motion 이면 schedule 값으로 대체)
├── bundle.py     --bgm/--bgm-license, PURGE/OUTPUT/ctx 확장, bundle.json 에 motion·bgm 기록
├── review.py     음원 라이선스 줄, 모션 요약 줄
├── approve.py    HASHED/check_outputs 에 선택 파일(bgm 오디오·bgm.json) 편입
└── layout.py/LayoutWarning  DWELL_SHORT / DWELL_LONG 종류 추가 (str 만 line 비면 " line" 생략)
.gitignore        *.mp3 *.m4a *.wav *.aac *.ogg *.opus *.flac  (drafts/ 는 이미 무시)
tools/reel.py     --motion {none,basic}, --bgm PATH, --bgm-license TEXT
tools/draft.py    bundle --bgm PATH --bgm-license TEXT
```

`motion` 은 spec.src.json 에 `"motion": "basic"` 로 적는 것을 **유일한 선택 경로**로 한다. bundle 에 `--motion` 덮어쓰기는 두지 않는다: 덮어쓰면 spec.json 과 spec.src.json 이 어긋나 `compare_source`(SOURCE_KEYS 대조)가 SOURCE_MISMATCH 를 낸다. `reel.py --motion` 은 단독 렌더용으로만 둔다(spec 필드보다 우선, 기록은 stdout). [VERIFIED: check.py:311 `SOURCE_KEYS = ("version", "series", "basis", "scenes", "inputs", "derive", "figures", "basis_items")` — motion 없음, expand.py:21 `ALLOWED_KEYS = ("basis", "inputs", "derive", "series", "scenes")` — motion 이 지금은 소스에서 거부됨]

### Pattern 1: 결정적 시간 탐색 (실측 구조)

페이지는 `browser.open_page` 로 연 번들 폰트 템플릿 하나. 장면마다 레이어(`.rk-layer`) 안에 `new_inner_html` 과 같은 `#rk-stack` 마크업(줄 `opacity:0` 로 시작). 모든 애니메이션은 `el.animate(kf, {fill:'both', ...})` 로 만든 뒤 즉시 `pause()` 하고 배열 `window.A` 에 보관, 프레임마다 `a.currentTime = t*1000` 으로 전역 시간 설정(애니메이션 `delay` 는 전역 시간 기준). `document.getAnimations()` 에 의존하지 않는다.

```js
// Source: 이 세션 spike (scratchpad spike.py), Chromium 153 / Playwright 1.63.0 에서 실행 확인
const add = (el, kf, o) => { const a = el.animate(kf, {fill:'both', ...o}); a.pause(); a.currentTime = 0; window.A.push(a); };
add(bar, [{transform:'scaleX(0)'},{transform:'scaleX(1)'}], {duration: total*1000, easing:'linear'});
// 장면 i>0 레이어: 전환 구간 [C_i - X, C_i] 에서 0→1, 이전 레이어는 같은 구간에서 1→0 (마지막 장면은 페이드아웃 없음)
add(layer, [{opacity:0},{opacity:1}], {duration: X*1000, delay: (C_i - X)*1000, easing:'linear'});
add(layer, [{opacity:1},{opacity:0}], {duration: X*1000, delay: (B_i - X)*1000, easing:'linear'});
// 줄 j: 300ms, 24px, 120ms 간격
add(ln, [{opacity:0, transform:'translateY(24px)'},{opacity:1, transform:'translateY(0)'}],
    {duration: 300, delay: (C_i + j*120)*1000, easing:'cubic-bezier(.2,.7,.2,1)'});
```
```js
// 프레임마다 (page.evaluate 한 번, 약 4ms)
for (const a of window.A) a.currentTime = t*1000;
layers.forEach((L,i)=>{ L.style.display = (t >= W[i][0] && t <= W[i][1]) ? '' : 'none'; });  // 필수: 성능 2.5배
for (const [id, txt] of cu) { /* 카운트업 span.textContent = txt */ }
```

- **레이어 `display` 토글은 필수.** opacity 0 레이어도 그려져서 프레임당 160ms → 토글 후 약 78ms (실측: 정적 `none` 페이지 64.6ms, 모션 7레이어 160.4ms, 1레이어만 표시 77.9ms). [VERIFIED: scratchpad prof2.py]
- 진입 애니메이션은 `transform`/`opacity` 만 → 레이아웃 불변. 장면 첫 레이어는 `opacity:1` 로 시작(첫 프레임이 빈 배경이 아니게 줄만 진입).
- 진행 막대: `scaleX` 애니메이션(연속). `none` 은 상태별 계단식이므로 막대는 표지와 픽셀이 달라진다(아래 Pitfall 5).
- 결정성 실측: 같은 `t` 를 두 번째 실행·역순 방문에서도 PNG md5 동일. [VERIFIED: scratchpad det.py — 같은 프레임 해시가 두 번의 별도 브라우저 실행에서 일치]

### Pattern 2: 시간표 (`motion.schedule(spec)` 순수 함수)

상수(한 곳, `motion.py`):

| 상수 | 값 | 근거 |
|------|----|------|
| `ENTER` | 0.30 s | D-02, MOTN-01(250~350ms) |
| `STAGGER` | 0.12 s | D-02 |
| `RISE_PX` | 24 | D-02 |
| `CROSS` | 0.30 s | D-03 |
| `COUNT` | 0.80 s | D-04 |
| `READ_BASE` | 0.6 s | 게시된 10편 보정 (Pattern 5) |
| `READ_CPS` | 16 자/초 | 게시된 10편 보정 |
| `DWELL_MIN` / `DWELL_MAX` | 1.5 / 6.0 s | D-06 |

장면 i (n 줄): 장면 시작 `C_i = B_{i-1}`(첫 장면 0), 줄 j 진입 시작 `C_i + j*STAGGER`, 카운트업 줄은 진입 시작과 같이 `COUNT` 동안 진행.
`settle_i = max((n-1)*STAGGER + ENTER, max_j(j*STAGGER + COUNT))`, `read_i = READ_BASE + chars_i/READ_CPS`,
`dur_i = settle_i + read_i + (CROSS if i < N-1 else 0)`, `B_i = C_i + dur_i`, **`final_t_i = C_i + settle_i + 1/FPS`** (모든 애니메이션이 끝난 첫 프레임, 다음 장면 페이드아웃 전).
`total = Σ dur_i`, `nframes = round(total*FPS)`, 반환할 영상 길이 `total = nframes/FPS`.

전환 모양: 장면 경계 `B_i` 직전 `[B_i - CROSS, B_i]` 에 이전 레이어 1→0, 다음 레이어 0→1 이 **같은 구간**에서 겹치고, 다음 장면의 줄 진입은 `B_i` 에서 시작한다(레이어 페이드와 줄 페이드가 곱해져 두 번 흐려지는 것을 피함). 육안 확인: 전환 중간 프레임에서 이전 장면 글자가 옅어지고 새 장면 라벨이 겹쳐 나타나며, 새 줄이 이어서 떠오른다. 이전·다음 레이어의 근거(basis)·계정명이 세로 위치가 달라 전환 0.3초 동안 겹쳐 두 번 보인다 — `none` 의 장면 점프와 같은 위치 차이를 페이드로 이은 것이라 수용(Pitfall 6).
- `cover_ms` = `round(final_t_0*1000)` (모션일 때 `RenderResult.cover_ms`), `stills.scene_times` = `round(final_t_i, 2)`. `none` 은 기존 `timeline` 함수 그대로. 표지·장면 모음은 **`final_t_i` 프레임을 파이프에 쓰는 그 PNG** 를 `frame_sink(i, path)` 로 넘긴다(추가 스크린샷 없음).

### Pattern 3: 줄바꿈 안정성 (spike 결과)

`.rk-ln` 은 `display:flex` 열 안의 블록이고 애니메이션은 `opacity`/`transform` 뿐이라 박스 크기·위치가 바뀌지 않는다. 8장면(3줄로 줄바꿈되는 100px 줄 포함) 시험:

| 검사 | 결과 |
|------|------|
| `MEASURE_JS` 측정값(`n,l,r,t,b` 소수 둘째자리) 모션 최종 프레임 vs 정적 `new_inner_html` | 8장면 **전부 일치** (줄 수 `[3,3,1]` 포함) |
| 진입 중간(+0.15s) 줄 수·너비 | 일치, 세로 이동 `[1.7, 15.4, 24.0]`px (≤24) |
| 최종 프레임 픽셀 비교(행 ≥14, 정적 `none` 프레임 대비) | 장면 3~7: 0픽셀. 장면 1·2: 막대 가장자리 `y 14~25` 의 204/130픽셀뿐(글자 아님). 장면 8: 5픽셀·채널차 1 |

[VERIFIED: scratchpad verify.py / verify2.py 출력]
→ **측정은 기존 정적 경로 그대로** 쓰고(`_scene_checks`는 `.rk-top` 등 전역 `querySelector` 를 쓰므로 모션 DOM 에서는 쓰지 말 것), 모션 DOM 이 그 배치와 같다는 것은 **픽셀 비교 시험**(최종 프레임 vs 정적 프레임, 막대 행 `<30` 제외, 채널차 ≤1)으로 영구 보증한다. 자소 분리·`Intl.Segmenter` 는 도입하지 않는다 (ROADMAP research flag 의 해당 부분 해소).

### Pattern 4: 카운트업 표시 방식 (결정: 원고 소스 문법 + 장부 플래그)

- **원고 소스:** `{{c_low|man1|up}}` — `PLACEHOLDER` 정규식에 선택 세 번째 조각 `(?:\|\s*(up)\s*)?` 추가. 현재 정규식: `PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\|\s*([a-z0-9_]+)\s*\}\}")`. [VERIFIED: expand.py:26] `test_expand.py:92` 가 `PLACEHOLDER.sub("", t)` 를 쓰므로 그룹이 늘어도 영향 없음.
- **장부:** `_expand_field` 가 `up` 이 붙은 자리의 장부 항목에만 `"countup": true` 를 더한다(그 외 항목의 키 집합 불변 → 기존 초안 `compare_source` 동일). `check._verify_entry` 는 `ref/fmt/text/value/sources/exact` 만 읽어 추가 키를 무시한다. [VERIFIED: check.py:153-181]
- **위치 제한:** `up` 은 `scene N line M` 필드에서만 허용(basis·top 은 `ExpandError`). 장부 `start/end` 는 **태그 포함 원문 기준 인덱스**이므로(예 `최대 <g>148.5만</g>` 의 start=6) 모션 마크업은 `markup_new(text[:s]) + '<span class="rk-cu" data-k="k">' + html.escape(entry.text) + '</span>' + markup_new(text[e:])` 로 조각 이어 붙이기 — 항목이 태그 경계를 걸치지 않으므로 `<g>…</g>` 짝이 유지된다(실측 확인).
- **고정 너비:** 빌드 직후(글자가 최종값일 때) `getBoundingClientRect().width` 를 재서 `display:inline-block; width:<w>px; white-space:nowrap` 로 고정, 왼쪽 정렬. 실측(30프레임): 상자 너비 `[352.7]`, 왼쪽 `[293.91]`, 줄 높이 `[130]` 각각 단일 값. 최종 프레임 `textContent` `['최대 148.5만','또는 118.8만','총급여 5,500만 원 기준']` = 원고 글자. [VERIFIED: scratchpad verify.py]
- **중간 글자:** Python 에서 `calc.FORMATS[fmt](Decimal(entry["value"]) * Decimal(eased))[0]` (`eased = 1-(1-p)^3`, ease-out), `p>=1` 이면 **`entry["text"]` 를 그대로** 쓴다(서식 재계산에 의존하지 않음). 반올림은 서식 함수 안에서만(ROUND_HALF_UP). 서식 함수가 `(text, shown)` 을 돌려주므로 `[0]`. [VERIFIED: calc.py:296-301 `"man1": _make_format(10000, "0.1", "만", group=True)`] 실측 프레임: `0만, 49만, 85.9만, 112.2만, 129.9만, 140.7만, 146.2만, 148.2만, 148.5만` (※ `man1` 은 `.0` 을 생략하므로 중간 값이 `0만`·`49만` 으로 나온다 — CONTEXT 예시의 "0.0만" 과 다름. 상자가 고정이라 흔들리지 않으므로 수용, 바꾸려면 서식에 `keep_decimals` 변형 추가.)
- **시작값 지정(선택):** 기본 0. 지정 시작값은 소스 문법을 더 늘려야 하므로 이번에는 미지원이 최소안(D-04 "0(또는 지정 시작값)" 중 0).
- **시험(필수):** (a) 모든 `countup` 장부 항목에 대해 `final_text == entry["text"]` (b) 최종 프레임 줄 `textContent == strip_tags(원고 줄)` (c) 카운트업 구간 프레임들에서 상자 너비 단일값.

### Pattern 5: 체류 시간·경고

`chars_i = len(strip_tags(top)) + Σ len(strip_tags(line))` (`check._visible` 과 같은 태그 제거). 게시된 10편 원고에 `READ_BASE=0.6, READ_CPS=16` 적용 결과(모션 총길이 vs `none` 총길이): 21.5/24.3, 21.8/23.5, 24.1/23.5, 26.7/26.0, 21.8/21.8, 23.4/23.5, 25.8/25.2, 23.8/25.2, 24.2/24.3, 22.3/21.8 — **10편 모두 하우스 패턴 21~27초 안**(check.py 의 `DUR_MIN, DUR_MAX = 21.0, 27.0`, [VERIFIED: check.py:26]), 장면별 최소 2.0초·최대 5.3초라 경고 0건. 후보 `(0.8, 11)`·`(0.8, 12)` 는 28~36초로 길어 기각. [VERIFIED: scratchpad calib.py 출력] 계수는 "사람이 읽는 속도" 판단이라 MEDIUM — 상수 한 곳에서 조정.

- 경고: `dur_i < 1.5` → `DWELL_SHORT`, `dur_i > 6.0` → `DWELL_LONG`. 클램프는 하지 않는다(경고가 정직한 수치를 보여 줌). `LayoutWarning(scene, line, kind, value, text)` 를 재사용하고 line 은 `""`, `__str__` 은 line 이 비면 `line ` 조각을 뺀다(`none` 출력은 line 이 항상 있어 불변). [VERIFIED: layout.py:132-133 `__str__`] 경고는 `r.warnings` 로 들어가 `bundle.final_code` 가 종료 코드 3 으로 올린다 — approve 는 `APPROVABLE_EXIT = (0, 3)` 이라 승인 가능. [VERIFIED: approve.py:95]
- `check._house_pattern` 의 `DURATION` 경고는 `timeline.total_duration(build_states(spec))`(=`none` 기준)로 계산한다. basic 이면 `motion.schedule(spec).total` 을 쓰도록 분기(그렇지 않으면 모션 릴스의 길이 경고가 엉뚱한 값을 기준으로 함).

### Pattern 6: BGM

**ffmpeg (실측, 사인파 8초 mp3·60초 m4a → 24.67초 영상):**
```
ffmpeg -loglevel error -y -f image2pipe -framerate 30 -c:v png -i -  -i <bgm_copy> \
  -filter_complex "[0:v]format=yuv420p[v];[1:a]aloop=loop=-1:size=2e9,atrim=0:T,asetpts=PTS-STARTPTS,\
afade=t=in:st=0:d=1,afade=t=out:st=T-1:d=1,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100,aformat=channel_layouts=stereo[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 20 -c:a aac -shortest -movflags +faststart <out>.part.mp4
```
`T = nframes/30`(소수 둘째 자리까지 문자열). `loudnorm` 은 내부에서 192kHz 로 올리므로 **`aresample=44100` 필수**. 결과(사인파): 8초 mp3 → −15.8 LUFS, 60초 m4a → −15.9 LUFS, LRA 0.5, True peak −14.2 dBFS(≤ −1.5), 영상·오디오 길이 24.70초, `specprobe` 9/9 PASS(fps `r=30/1 avg=30/1`, audio `aac` 44100Hz 2ch). [VERIFIED: scratchpad bgm/ 실행 출력] 실제 음악은 사인파보다 동적이라 ±1~2 LU 편차가 날 수 있다 — 시험은 사인파 −16±1.5 LUFS 로만 단언하고, 실제 음원 음량은 사람 검수 몫으로 review.md 에 둔다. 무음(BGM 없음): 현행 `anullsrc` 그대로.

**입력 검증 (`bgm.validate`, 모두 ffmpeg 실행 전에 종료 코드 1):**
1. `--bgm` 과 `--bgm-license` 는 **함께** 있어야 한다. 메모가 `None`/공백뿐이면 거부(D-08). 메모만 있고 음원이 없어도 거부(조용히 무시하지 않음).
2. 경로 해석 후: 일반 파일(심볼릭 링크 거부), 확장자 허용 목록(`.mp3 .m4a .wav .aac .ogg .opus .flac`), `ffprobe -select_streams a:0` 가 성공하고 오디오 스트림이 있고 길이 ≥ 3초(깨진 파일: `ffprobe` 종료 1 — 실측 확인). 영상 스트림이 있는 파일(예: MP4)은 거부.
3. D-09: 해석된 경로가 `REPO_ROOT` 안이면 **그 초안 폴더 안**일 때만 허용, 저장소 안 다른 곳은 거부. 저장소 밖은 허용.
4. 통과하면 초안 폴더에 `bgm<확장자>` 로 **복사**(원자적 `.part` → `os.replace`)하고 `bgm.json` 을 쓴다: `{"schema":1,"file":"<원본 파일 이름>","copy":"bgm.mp3","sha256":"<복사본>","license":"<메모 원문>","duration_s":..}`. 믹스는 복사본에서 하고 해시도 복사본의 것 → 승인 뒤 원본이 바뀌어도 지문과 영상이 어긋나지 않는다. 라이선스 메모는 `strip()` 만 하고 원문 보존(줄바꿈은 review 출력에서만 공백으로).
5. **재생성 시 낡은 BGM 이월 금지:** `bundle.PURGE_FIXED` 에 `bgm.json` 을, `purge_outputs` 에 `bgm.*` 복사본을 추가해 `--bgm` 없이 다시 묶으면 BGM 이 사라지게 한다. [VERIFIED: bundle.py:32 `PURGE_FIXED = ("approval.json", "spec.json", "check.json", "caption.txt", "compliance.json", "review.md", "bundle.json")`]

**승인 지문(D-11):** `OUTPUT_KEYS` 와 `approve.check_outputs` 는 현재 "정확히 이 이름 집합"만 허용한다. [VERIFIED: bundle.py:35 `OUTPUT_KEYS = ("spec_src", "caption_src", "spec", "check", "caption", "compliance", "mp4", "cover", "scenes", "review")`; approve.py:22-23 `PROVENANCE_KEYS = ("spec_src", "caption_src", "check", "compliance", "review", "bundle")`, `HASHED = PROMOTED_KEYS + PROVENANCE_KEYS`] 선택 파일을 위해: `draft_paths` 에 `bgm_meta`(`bgm.json`)와 `bgm_audio`(복사본 이름은 `bgm.json` 에서 읽음)를 추가하고, bundle.json 에 `"bgm": {...}|null` 을 기록, `output_hashes`/`check_outputs`/`file_hashes` 는 "기본 이름 집합 + (bundle.json `bgm` 이 있으면 두 파일)" 을 기대 집합으로 쓴다. 기대 집합을 bundle.json 의 `bgm` 값 하나로만 정하지 말고, **디스크에 `bgm.json` 이 있는데 bundle.json 에 `bgm` 이 없으면 거부**(양방향 대조)해서 손으로 BGM 을 끼워 넣거나 빼는 것을 막는다. promote 는 영상(오디오 포함)만 옮기므로 오디오·메모 파일은 옮기지 않는다(저장소 커밋 방지).

**review.md:** `_checklist_section` 의 현재 줄 `"- [ ] 음원 라이선스 — 배경음 없음 = 무음 (음원을 넣었다면 이용 권리 확인)"` [VERIFIED: review.py:125] 을 BGM 이 있을 때 `- [ ] 음원 라이선스 — 파일 \`<원본 이름>\` (sha256 <앞 12자>) · 메모: <원문> — 사업자 계정 상업 사용 권리를 사람이 확인` 으로 바꾼다. 없으면 현행 문구 유지(`test_bundle.py:124` 가 "음원 라이선스" 문구를 확인하므로 유지). 한눈에 보기에 `- 모션: basic (카운트업 N곳)` 줄과 BGM 사용 여부 줄 추가. 이 줄들은 `write_review` ctx 키를 늘리는 것이므로 `write_failure_review` 경로(ctx 에 키 없음)에서 `ctx.get` 을 쓴다.

**.gitignore:** 오디오 확장자 패턴 추가. 저장소에 이미 추적되는 오디오 파일은 없다. [VERIFIED: `git ls-files | grep -Ei '\.(mp3|m4a|wav|aac|ogg|flac|opus)$'` → 출력 없음] `2026/reels/drafts/` 는 이미 무시되지만 저장소 밖→초안 폴더 복사 외의 경로(예: tools/tests 임시)에서 실수로 커밋되지 않게 패턴도 둔다.

### Anti-Patterns to Avoid
- **`none` 경로 인자·루프 수정:** golden 장면 경계가 `fps=30` 반올림에 의존. BGM 추가도 `bgm is None` 일 때 인자 동일.
- **모든 레이어를 항상 표시:** 프레임당 160ms (위 실측).
- **JS 에서 카운트업 서식 재구현:** `calc.FORMATS` 가 유일한 서식 권위. 프레임 문자열은 Python 이 만든다.
- **`page.screenshot(animations="disabled")`:** 유한 애니메이션을 끝 상태로 빨리 감아 탐색을 무력화 (CLAUDE.md).
- **`getAnimations()` 에 의존:** `fill` 로 남는 애니메이션도 `window.A` 로 직접 관리.
- **모션 DOM 에서 `_scene_checks`/`MEASURE_JS` 호출:** 전역 `querySelector('.rk-top')` 가 첫 레이어만 잡는다. 정적 경로를 쓰거나 측정할 레이어만 남기고 나머지를 DOM 에서 떼어 측정(검증용).
- **ffmpeg stderr 를 파이프로 받고 읽지 않기:** 교착 위험. `-loglevel error` + stderr 를 임시 파일로 보내고 실패 시 마지막 줄을 `EncodeError` 에.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 프레임 보간/이징 | Python 으로 위치·투명도 계산 후 합성 | Web Animations(`el.animate`) + `currentTime` | 브라우저가 서브픽셀·이징·합성을 정확히 처리 |
| 숫자 서식·반올림 | JS 서식기 | `calc.FORMATS[fmt]` | ROUND_HALF_UP·단위·천 단위 쉼표가 이미 시험됨 |
| 장면 전환 | ffmpeg `xfade` 장면별 클립 | 레이어 불투명도 크로스페이드 | 줄 진입·카운트업과 같은 시계 |
| 음량·페이드·반복 | pydub/librosa | ffmpeg `aloop,atrim,afade,loudnorm` | 실측 완료 |
| 승인 지문 | 새 해시 체계 | `bundle.sha256_file` + `approve.HASHED` 확장 | 기존 WR-02/IN-02 보증 재사용 |
| 업로드 규격 | 새 검사 | `specprobe.probe` | 모션·BGM 모두 9/9 실측 |

## Runtime State Inventory

해당 없음(이름 변경·이전 단계가 아님). 다만 **낡은 상태 이월** 위험 하나: 이전 bundle 이 남긴 `bgm.json`/복사본 — 위 Pattern 6 5번으로 purge. `.render-work/`·`__pycache__` 는 기존 무시 대상.

## Common Pitfalls

### Pitfall 1: 7개 레이어를 항상 표시 → 렌더 2.5배 느려짐
**원인:** opacity 0 레이어도 레이어 합성·래스터. **대책:** 시간창 밖 `display:none`(Pattern 1). **신호:** 프레임당 >120ms.

### Pitfall 2: 카운트업 자리가 줄바꿈 위치를 바꿈
**원인:** `inline-block` 은 원자적이라 상자 안 공백에서 줄이 못 꺾임(`5,500만 원` 처럼 공백 든 서식). 정적 배치에서 그 공백에서 줄이 꺾이던 줄은 달라질 수 있다. **대책:** 이런 줄은 이미 `WRAP` 경고 대상이므로 `up` 은 한 줄에 들어가는 숫자에만 쓰도록 check 경고(`COUNTUP_WRAP`)로 안내하거나 정적 측정과 모션 최종 프레임 픽셀 비교 시험이 잡게 한다. 카운트업 후보는 `man1`·`pct` 같이 공백 없는 서식이 안전.

### Pitfall 3: 중간 숫자가 장부에 없는 숫자로 보임 (컴플라이언스)
카운트업 중 0.8초간 `49만`, `85.9만` 같은 값이 화면에 뜬다. 최종값만 원고·장부 수치이고 중간은 연출이다. **대책:** review.md 한눈에 보기에 "카운트업 N곳 — 중간 숫자는 연출, 최종값만 장부 값" 한 줄을 넣고 사람 확인 목록에 둔다. 컴플라이언스·numscan 은 spec 문자열(최종값)만 본다 — 변경 없음.

### Pitfall 4: 프레임 수·길이 불일치
`total` 이 소수라 `nframes=round(total*30)` 과 어긋나면 BGM `atrim`/페이드아웃 위치가 영상과 0.03초 어긋난다. **대책:** `total = nframes/FPS` 로 확정하고 `T` 도 그 값에서 만든다. specprobe 는 `r_frame_rate=30/1`, `avg=30/1` 을 요구(실측 PASS).

### Pitfall 5: 표지가 `none` 과 막대만 다름
`none` 막대는 상태별 계단, 모션은 연속. 표지 PNG 의 막대 폭이 다르다(위 픽셀 비교에서 막대 행만 차이). 표지 크롭 검사는 막대 행(0~13)을 제외하므로 영향 없음. 시험의 픽셀 비교는 행 `>=30` 로.

### Pitfall 6: 전환 중 basis·계정명 겹침
장면마다 스택이 세로 가운데 정렬이라 basis/계정명 y 가 달라 전환 0.3초간 두 벌이 보인다(스크린샷 확인). D-03 의 "겹침" 범위로 수용. 거슬리면 재량으로 basis/acct 를 레이어 밖 고정 요소로 빼는 것은 배치 변경이라 이번 단계 범위 밖.

### Pitfall 7: 승인 흐름 회귀
`check_outputs` 가 정확한 이름 집합을 요구하므로 BGM 파일만 추가하고 기대 집합을 안 고치면 BGM 묶음은 영원히 승인 거부, 반대로 집합을 느슨하게 만들면 WR-02 보증이 약해진다. 양방향 대조(Pattern 6)와 시험 두 개(BGM 있음 승인 성공 / bgm.json 위조·삭제 거부).

### Pitfall 8: `motion` 값 검증 위치
`spec.py` 는 `motion` 을 문자열 또는 객체로 느슨히 허용하고 시험도 `"calm"`, `{"preset":"calm"}` 을 통과로 단언한다(`tools/tests/test_spec.py:179-184`), `test_expand.py:140` 은 `motion="x"` 가 expand 에서 오류임을 단언. **대책:** `spec.py` 는 건드리지 않고(기존 시험 유지) `expand` 에서 `none|basic` 만 허용, 렌더 시 `motion.resolve` 가 그 밖의 값을 `SpecError` 로 거부. [VERIFIED: grep tools/tests — test_spec.py:179-184, test_expand.py:140]

## Code Examples

### 프레임 루프와 파이프 인코딩 (실측 구조)
```python
# Source: 이 세션 spike (scratchpad spike.py) — 740프레임 72.8s, specprobe 9/9
ff = subprocess.Popen(["ffmpeg","-loglevel","error","-y","-f","image2pipe","-framerate","30","-c:v","png","-i","-",
                       *audio_inputs_and_graph, "-c:v","libx264","-crf","20","-c:a","aac","-shortest",
                       "-movflags","+faststart", str(tmp)], stdin=subprocess.PIPE, stderr=errfile)
try:
    for f in range(nframes):
        t = f / FPS
        page.evaluate(SEEK_JS, {"t": t, "cu": cu_strings(spec, sched, t)})
        png = page.screenshot(type="png")
        if f in final_frames:                  # {장면 번호: f}
            path = work / f"s{final_frames[f]:02d}.png"; path.write_bytes(png)
            frame_sink(final_frames[f], str(path))
        ff.stdin.write(png)
finally:
    try: ff.stdin.close()
    except BrokenPipeError: pass
    rc = ff.wait()
# rc != 0 → EncodeError(마지막 stderr 줄), 성공 시 os.replace(tmp, out) (encode_concat 와 같은 .part.mp4 원자 교체)
```

### 카운트업 중간 글자
```python
# 장부 항목 e: {"text":"148.5만","fmt":"man1","value":"1485000","countup":True,...}
def cu_text(e, p):                     # p: 0..1 진행도 (줄 진입 시작 기준 COUNT 초)
    if p >= 1: return e["text"]        # 최종값은 장부 글자 그대로 (한 글자까지 같음)
    eased = 1 - (1 - max(p, 0.0)) ** 3
    return calc.FORMATS[e["fmt"]](Decimal(e["value"]) * Decimal(eased))[0]
```

### 한글 라벨 없이 BGM 거부 (종료 코드 1)
`bgm.validate(...)` 가 `BgmError` 를 던지면 bundle 은 `print(f"음원 오류: {e}", file=sys.stderr); return 1` (원고·입력 오류와 같은 코드). `run_cli` 에서 승인 파일 삭제 직후, `purge_outputs` 이전에 검증한다(실패해도 이전 산출물은 그대로 — 기존 `--request-start` 오류와 같은 위치).

## State of the Art

| Old | Current | Impact |
|-----|---------|--------|
| 상태별 정지 화면 + concat | 프레임 단위 시간 탐색 + PNG 파이프 (motion 만) | `none` 은 기존 유지 |
| 자소 단위 분리 애니메이션 | 줄 단위 `opacity`/`transform` (레이아웃 불변) | ROADMAP 의 `Intl.Segmenter` spike 불필요 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `READ_BASE=0.6`, `READ_CPS=16` 이 사람에게 적절한 읽기 속도 (게시된 10편 총길이에 맞춘 값일 뿐, 읽기 속도 연구가 아님) | Pattern 5 | 모션 릴스가 너무 빠르거나 느림. 상수 한 곳 조정, 사용자 검수에서 확인 |
| A2 | 실제 음악에서 단일 패스 `loudnorm` 이 −16 LUFS 에 ±1~2 LU 로 수렴 (사인파만 실측) | Pattern 6 | 음량이 목표와 다소 다름 — 사람 검수 항목으로 둠, 필요 시 2패스 |
| A3 | Instagram 이 H.264 `-crf 20` 영상+AAC 44.1kHz 스테레오를 문제없이 받음 (기존 `none` 과 같은 설정이라 동일 위험) | Pattern 6 | 낮음 |
| A4 | 전환 중 basis·계정명 두 벌 겹침을 사용자가 수용 | Pitfall 6 | 시각 불만 → 후속 배치 변경 |
| A5 | 라이선스 메모 저장 형식을 `bgm.json` 의 자유 문자열로 충분하다고 봄 (증빙 형식은 오너 게이트로 미결정) | Pattern 6 | 오너가 증빙 형식을 정하면 `bgm.json` 스키마 확장 필요 |

## Open Questions

1. **카운트업 시작값 지정(D-04 "또는 지정 시작값")** — 지금은 0 만. 필요해지면 `{{ref|fmt|up:100}}` 같은 문법 확장. 권고: 이번 단계는 0 만 (재량 범위).
2. **`up` 을 `top` 에도 허용할지** — 현재 줄만. 장면 5 의 top `900만 원 채우면 …` 같은 곳은 카운트업이 어색하므로 줄만 권고.
3. **BGM 이 `none` 모션과도 가능한가** — 가능하게 두는 것을 권고(인코더 인자만 다름). 오너 게이트가 음원을 정하기 전이라 사용자 검증은 사인파로만.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Playwright (Python) | 렌더 | ✓ | 1.63.0 | — |
| Chromium | 렌더 | ✓ | rev 1243 (`browser.launch` 가 `/opt/pw-browsers/chromium` 폴백) | — |
| ffmpeg/ffprobe | 인코딩·BGM·검증 | ✓ | 6.1.1 (libmp3lame, aac, loudnorm, aloop, afade) | — |
| Pillow, numpy | 시험 픽셀 비교 | ✓ | 설치됨 | 시험에서 ffmpeg `psnr`/해시로 대체 가능 |

차단 의존성 없음. 시험용 음원은 `ffmpeg -f lavfi -i sine=...` 로 런타임 생성(저장소에 오디오 파일 없음).

## Security Domain

### Applicable ASVS Categories (L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `--bgm` 경로(심볼릭 링크·저장소 안 경로·확장자·ffprobe 로 오디오 확인), 라이선스 메모(길이 상한·제어문자 제거), `motion` 값 허용 목록, 원고 문자열은 `markup_new`/`html.escape` 로 이스케이프(카운트업 span 도 `html.escape`) |
| V12 Files | yes | 복사는 `.part` + `os.replace`, 초안 폴더 안으로만 쓰기, 승인 지문(sha256) |
| V14 Config | yes | 외부 네트워크 차단(`page.route` 로 http/https abort, 기존), 음원 다운로드·검색 코드 없음 |
| V2/V3/V4/V6 | no | 인증·세션·접근제어·암호화 없음 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 명령 주입(파일명·메모를 셸로) | Tampering | `subprocess` 인자 리스트만, 셸 미사용 (기존 방침). ffmpeg 필터 문자열에는 숫자 `T` 만 삽입, 파일 경로는 `-i` 인자로만 |
| 경로 탈출/심볼릭 링크로 저장소 파일 읽기·쓰기 | Tampering/Info disclosure | `Path.resolve()` 후 검사, 링크 거부, 복사 대상은 초안 폴더 고정 이름 |
| 라이선스 메모의 마크다운/제어문자 삽입 → review.md 위조 | Tampering | 줄바꿈·제어문자 공백 치환, 백틱·`|` 이스케이프(`review._cell`), 길이 상한 |
| 승인 뒤 음원 교체 | Tampering | 복사본 sha256 을 bundle.json·approval.json 에 포함, 원본이 아니라 복사본을 믹스 |
| 저작권 음원 커밋 | Legal | `.gitignore` 패턴 + 초안 폴더 외 저장소 경로 거부 + promote 가 오디오를 옮기지 않음 |

## Verification Recipes (nyquist_validation=false 이므로 섹션 대신 요약)

- 빠른 시험: `python3 -m unittest discover -s tools/tests -p 'test_motion.py' -v` (신규), `test_bgm.py`(신규), `test_stills.py`·`test_layout.py`·`test_expand.py`·`test_approve.py`·`test_bundle.py`.
- 전체: `python3 -m unittest discover -s tools/tests -v` (3~4분, [CITED: tools/README.md:193]) + `python3 tools/golden.py` 10/10.
- 시험 목록: (1) 시간표 순수 시험(10편 총길이 21~27, 경고 0, 극단 장면 DWELL_SHORT/LONG) (2) 모션 렌더 7장면 → 길이·프레임 수·specprobe 9/9 (3) 최종 프레임 vs 정적 프레임 픽셀 일치(행 ≥30, 채널차 ≤1) (4) 줄 사각형·줄 수 일치(줄바꿈 줄 포함) (5) 카운트업 최종 글자=장부 `text`, 상자 너비 상수 (6) `none` 인자 리스트·frame 수 불변 + golden 10/10 (7) BGM: 사인 mp3(짧음)·m4a(김)·메모 없음 거부(종료 1)·메모 공백 거부·저장소 안 경로 거부·비오디오 거부·−16±1.5 LUFS·specprobe 9/9 (8) 승인: BGM 묶음 승인 성공, bgm.json 위조/삭제/추가 거부, BGM 없이 재묶음 시 bgm.json 삭제 (9) review.md 음원 줄에 파일 이름·메모 원문.
- 렌더 시간 단언은 하지 않는다(장비 의존). 대신 bundle.json 단계별 초를 기록(기존)하고 7장면 ≈ 25초 영상 렌더가 이 컨테이너에서 약 73초임을 참고 기록.

## Sources

### Primary (HIGH — 이 세션에서 직접 실행·열람)
- `/home/user/kiwoom-cards/tools/reelkit/{render,timeline,layout,encode,bundle,review,approve,expand,calc,spec,specprobe,check,constants,browser,stills}.py` — 위 라인 인용
- `/home/user/kiwoom-cards/.planning/{ROADMAP,REQUIREMENTS}.md`, `04-CONTEXT.md`, `.claude/CLAUDE.md`
- Spike 스크립트·출력(스크래치패드, 소스 무변경): `/tmp/claude-0/-home-user-kiwoom-cards/4de16945-3f5f-566a-ae8a-809ea3b681f7/scratchpad/{spike,verify,verify2,prof,prof2,det,calib,shots}.py`, `bgm/`(사인파 mp3·m4a 와 믹스 결과), `frames.png`

### Secondary / Tertiary
- 없음 (웹 검색 불필요: 모든 주장이 로컬 실측)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 신규 패키지 없음, 설치된 버전 확인
- Architecture: HIGH — 모션 경로·줄바꿈·카운트업·BGM 필터를 실측, 기존 코드 라인 확인
- 체류 계수: MEDIUM — 게시된 10편 기반 보정, 사람 판단 필요
- Pitfalls: HIGH — 대부분 실측 또는 코드 근거

**Research date:** 2026-10-29
**Valid until:** 2026-11-28 (스택 고정 — Playwright 1.63.0 / Chromium 1243 / ffmpeg 6.1.1 이 바뀌면 재확인)
