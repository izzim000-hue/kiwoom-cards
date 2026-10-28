<!-- GSD:project-start source:PROJECT.md -->

## Project

**키움멘토 릴스 제작 자동화**

키움멘토 인스타그램 릴스를 만드는 작업 흐름을 자동화하는 프로젝트다. 주제 한 줄이나 기존 카드뉴스 원고를 넣으면, 사람이 검수할 초안 묶음(릴스 원고 JSON · MP4 영상 · 표지 이미지 · 게시글 문구와 해시태그 · 금소법 표현 점검표)이 한 번에 나온다. 사용자는 Claude Code 세션에서 "이 주제로 릴스 만들어 줘"라고 요청하는 방식으로 쓴다. 1순위는 제작 자동화, 2순위는 자막 연출 강화(보는 맛)다.

**Core Value:** 주제 하나를 넣으면 기존 브랜드 형식을 지킨, 검수 가능한 릴스 초안 묶음이 10분 안에 나온다 — 그리고 단정 표현과 근거 없는 수치는 반드시 표시된다.

### Constraints

- **브랜드**: 기존 10편과 같은 색감·폰트·레이아웃 유지 — 시리즈 일관성
- **컴플라이언스**: "원금 보장", "확정 수익", "무조건 절세" 등 단정 표현 금지, 세무·법률 판단 단정 금지, 타사 비방 금지 — 금소법·보험업법
- **정확성**: 세법·요율·수치는 근거(기준·예시 조건)를 `basis`에 명시하고, 최신 여부를 확인해야 함 — 추정 수치는 추정임을 표시
- **개인정보**: 고객 실명·사례 사용 금지 — 공개용 콘텐츠만
- **검수**: 모든 산출물은 초안이며 사람 검수 후 게시
- **비용**: API 키·유료 서비스 없이 Claude Code 세션 안에서 동작
- **기술 스택**: 기존 Python + Playwright + ffmpeg 구조 확장 — 이미 검증된 파이프라인
- **환경**: 클라우드 네트워크 정책상 외부 다운로드가 제한될 수 있음 — 사전 설치된 Chromium 사용

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Verdict in one paragraph

## Environment facts verified in this container (they change the plan)

| Fact | Evidence | Consequence |
|------|----------|-------------|
| **Python `playwright` package is NOT installed** | `import playwright` -> ModuleNotFoundError | `tools/reel.py` cannot run in a fresh session as-is. Bootstrap step required (see Installation). |
| Preinstalled Chromium is revision **1243** (Chrome 153.0.8010.12, `/opt/pw-browsers/chromium-1243` + `chromium_headless_shell-1243`) | `ls /opt/pw-browsers`, `chrome --version` | `pip install playwright` (unpinned) gives **1.64.1**, which wants revision **1248** and fails with "Executable doesn't exist ... chromium_headless_shell-1248". **Pin `playwright==1.63.0`** (its `browsers.json` says chromium 1243; verified default `launch()` works). Fallback: `launch(executable_path="/opt/pw-browsers/chromium")` (verified works with 1.64.1 too). |
| PyPI, npm and `raw.githubusercontent.com` are reachable through the proxy; `github.com/.../raw/` returns 403; Google Fonts CSS returns a stub | curl tests | pip installs work; a font file can be fetched once from raw.githubusercontent.com. |
| **No Korean-capable brand font installed**: no Noto Sans CJK KR / Pretendard / Nanum. `fc-match "sans:lang=ko"` -> WenQuanYi Zen Hei | `fc-list`, `fc-match` | The existing reels were rendered where "Noto Sans CJK KR" existed. Here `font-family:'Noto Sans CJK KR'` silently falls back to a Chinese-style font (verified visually: glyph shapes differ). **Brand consistency risk: must vendor the font.** |
| ffmpeg **6.1.1** with libx264, aac, libmp3lame, `xfade`, `amix`, `afade`, `aloop`, `loudnorm`, `alimiter`, `sidechaincompress`, libass | `ffmpeg -filters/-encoders` | Everything audio/transition-related is already available; no extra binaries. |
| Python 3.13.17, Pillow 12.3.0, numpy 2.5.3, Jinja2 3.1.6 preinstalled; MoviePy, pydub, OpenCV, pytest are not | `pip list` | Don't add any of the missing ones unless unavoidable. |
| 4 CPU cores, 16 GB RAM | `nproc`, `free` | Single-process render is already fast enough; parallel workers are an optional optimisation, not a requirement. |

## Recommended Stack

### Core Rendering (motion)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.13 (system) | Orchestrator, spec -> bundle | Already the project language; stdlib covers JSON/regex/paths | HIGH |
| Playwright (Python) | **==1.63.0** (pin) | Drive Chromium, seek animation, screenshot | Matches preinstalled Chromium 1243 exactly, so no download needed. Already the proven renderer; HTML/CSS gives Korean text shaping, brand fonts, gradients, easing for free | HIGH (verified) |
| Chromium (preinstalled) | 153.0.8010.12 | Rendering engine | Already in `/opt/pw-browsers`; network policy blocks downloading another | HIGH |
| **Deterministic time-seek rendering** (Web Animations API + a JS `renderAt(t)`) | browser built-in | Slide/fade-in, scene transitions, count-up | Per frame: `document.getAnimations().forEach(a=>{a.pause(); a.currentTime=t*1000})` plus a JS call for count-up and progress bar. Pure function of `t` -> frame-exact, repeatable, no wall-clock jitter, no dropped frames. Verified: 750 frames, animation state correct at every sampled frame | HIGH (verified) |
| ffmpeg | 6.1.1 (system) | Encode, BGM mix, final mux | Already used; one process does video encode + audio filter graph | HIGH |
| `subprocess.Popen` + `-f image2pipe -c:v png` | stdlib | Stream PNG frames to ffmpeg stdin | No temp dir of 750 PNGs, no concat-demuxer text file, constant duration per frame at fixed `-framerate 30` (removes the existing `duration` bookkeeping and the extra final `file` line hack) | HIGH (verified) |
| Capture method | ms/frame | 750 frames | Verdict |
|----------------|----------|------------|---------|
| `page.screenshot(type="png")` | 54 | ~40 s | **Use this** (simple, lossless, only 1.6x slower than the fastest) |
| `page.screenshot(type="jpeg", q=95)` | 36 | ~27 s | Don't: chroma-subsampled JPEG edges on thin Hangul strokes get re-compressed by x264 |
| CDP `Page.captureScreenshot` (png, optimizeForSpeed) | 34 | ~25 s | Optional later optimisation if render time ever matters; needs `new_cdp_session` |
| End-to-end: seek + PNG pipe + x264 `medium` crf 18 + BGM mix + faststart | - | **42.6 s total** | Whole reel; budget is 600 s |
| x264 encode of 750 PNG frames, `medium` crf 20 | - | ~9 s | `veryfast` ~6 s; not worth the quality loss |

### Output encoding settings (keep identical for every reel)

### Audio (optional user-supplied BGM)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ffmpeg `filter_complex` (`aloop`/`atrim`, `afade`, `loudnorm`/`volume`) | 6.1.1 | Trim/loop BGM to reel length, fade in/out, level-set | Single tool, no Python audio lib, ~1.7 s on a 25 s reel when video is stream-copied; verified for BGM shorter than video (loops), longer (trims), mp3 and m4a | HIGH (verified) |
| `ffprobe` | 6.1.1 | Read BGM duration / validate file is audio | Already installed with ffmpeg | HIGH |
| `anullsrc` silent track | existing | Keep silent AAC track when no BGM | Existing behaviour; keep so all reels share the same container layout | HIGH |
- Loop with `aloop=loop=-1:size=2e9` + `atrim` (verified, exact `T` duration, no gap issues). `-stream_loop -1` on the input also works; either is fine.
- Level: there is no voice to protect, so BGM is the only audio; target roughly **-16 to -18 LUFS integrated, true peak <= -1.5 dBTP**. Verified `loudnorm=I=-16:TP=-1.5:LRA=11` followed by fades and `volume=0.8` lands at -18.1 LUFS (measured with `ebur128`). Prefer: fades first, `loudnorm` last, no extra `volume`, so the target is what you get. Single-pass `loudnorm` is acceptable for a 25 s clip; use two-pass only if levels look off (LOW need).
- If a future v2 adds voice: use `sidechaincompress` ducking (already in this ffmpeg). Not needed now.
- Validation (do in Python, stdlib): file exists, `ffprobe` reports an audio stream, duration >= 3 s. **Never** fetch, search for, or default to any music; BGM only when the user passes a path (copyright constraint in PROJECT.md). Record the BGM filename in the bundle's checklist so the human reviewer confirms the licence.

### Fonts (new, required)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Noto Sans KR (Subset OTF: Regular, Bold, Black)**, SIL OFL 1.1 | notofonts/noto-cjk main (`Sans/SubsetOTF/KR/NotoSansKR-{Regular,Bold,Black}.otf`, ~4.6/4.8/5.0 MB) | Guarantee brand glyphs regardless of what the session image has installed | Same design as the "Noto Sans CJK KR" used by the existing reels (weights 400/700/900 are what `reel.py` uses; `cards.py` also uses 500, so add Medium ~4.7 MB if cards are migrated). OFL allows redistribution in-repo. Download verified reachable via `raw.githubusercontent.com` | HIGH (download + render verified for Black) |

### Caption / hashtag / compliance checklist generation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Claude itself (in-session) | - | Writes reel script JSON, caption, hashtags, proposes replacement wording | Project constraint: no external LLM API. The skill prompt carries the style rules (existing 10 specs as few-shot, scene pattern hook -> analogy -> numbers -> conclusion -> caveat -> CTA) | HIGH |
| Python stdlib only: `re`, `json`, `dataclasses`, `pathlib`, `argparse` | 3.13 | Deterministic spec validator + 금소법 expression linter + bundle writer | The lint is a lexicon + regex pass over `top`/`lines`/`basis`/caption; it needs no NLP. Reproducible, unit-testable, zero install. | HIGH |
| Lexicon as data file (`tools/compliance_terms.json`) | - | Banned/flagged phrases with category and suggested replacement | Lets the user/Claude extend rules without code changes. Categories from PROJECT.md: 단정 수익/원금 보장, 무조건 절세·세무 단정, 근거 없는 수치, 타사 비방, 개인정보 | HIGH (structure), MEDIUM (term coverage - needs legal-minded review) |
| Existing `compliance-review` skill (anthropic-skills:compliance-review) | - | Second-pass human-readable judgement of the same draft (단정 표현, 설명의무, 비교광고) | Already available in the session; use it as the *judgement* layer on top of the *deterministic* lint, not a replacement | MEDIUM (not exercised here) |
| Jinja2 | 3.1.6 (already installed) | Optional: render the Markdown checklist / caption file | Only if Markdown templating gets non-trivial; f-strings/`str.format` suffice otherwise. Do NOT use Jinja2 for the video HTML (see architecture note) | MEDIUM |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | 12.3.0 (preinstalled) | Contact sheet / sanity checks (e.g. composite 4 frames into one PNG for quick review), pixel-colour assertions in tests | Only for QA helpers, never for text layout |
| `ffprobe` JSON output | system | Post-render verification (duration, fps=30, 1080x1920, audio present, has +faststart) | Always, as the last step of the bundle; fail loudly |
| pytest | latest via pip (not installed) | Unit tests for the linter and spec validator | Optional; stdlib `unittest` works with zero install and is enough |
| Playwright `launch(args=[...])` flags | n/a | `--font-render-hinting=none` for stable glyph rendering across machines | Add if text edge differences appear between runs; not required now (LOW) |

## Architecture note that drives the stack (for roadmap)

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Motion capture | Seek Web Animations + per-frame `page.screenshot` | **Playwright `record_video_dir`** | Records in real time (a 25 s reel takes 25+ s of wall clock and any slow frame drops), fixed ~25 fps VP8 `.webm`, low default bitrate, size scaled; no deterministic control of count-up or cover time; would need a lossy webm -> mp4 transcode. Quality and repeatability are worse in every dimension. |
| Motion capture | same | Pure CSS animation played live + CDP screencast | Same real-time/jitter problems; screencast frames are best-effort. |
| Motion capture | same | Playwright `page.clock` fake timers | Controls `setTimeout`/`rAF`/`Date` but NOT CSS animations/transitions; would not move the slide/fade. Web Animations seeking does. |
| Motion capture | same | Pillow frame drawing + numpy compositing | Loses Chromium text shaping, kerning, `letter-spacing`, font fallback, brand HTML already built; Hangul layout by hand is a rewrite and would visually drift from the 10 existing reels. Pillow stays as a QA helper only. |
| Compositor | ffmpeg directly | **MoviePy** | Adds MoviePy + imageio + decorator + proglog (+numpy) for functionality ffmpeg already has; MoviePy renders text with Pillow/ImageMagick (same Hangul problem) and is slower (Python per-frame callbacks). No benefit here. |
| Video framework | Python + Playwright | **Remotion** | Needs Node project + React rewrite of the whole look, downloads its own Chromium/ffmpeg (conflicts with restricted network and the preinstalled Chromium), and its licence is not free for companies above a small size (a commercial company licence applies; MEDIUM confidence, verify before any adoption). Throws away the validated pipeline for ~zero benefit at this scale. |
| Transitions | In-browser (CSS/JS driven by `t`) | ffmpeg `xfade` between per-scene clips | xfade works (available in 6.1.1) but forces per-scene encoding, re-timing math, and cannot coordinate with text stagger or count-up. Keep only as an emergency fallback for a hard-to-do transition (fade/slide/wipe variants only). |
| Frame handoff | PNG pipe to ffmpeg stdin | Temp dir + concat demuxer (current) | Concat needs per-frame `duration` files and a repeated last `file`; at 30 fps/750 frames it's slower and leaves GBs of temp data. Fine only for the old static mode. |
| Frame format | PNG | JPEG | See table above (artifact risk on Hangul). |
| BGM mixing | ffmpeg filter graph | pydub / librosa / soundfile | Extra deps (pydub shells out to ffmpeg anyway; librosa pulls numba/scipy). Needless. |
| Caption/compliance | Claude + stdlib lexicon linter | KoNLPy / Mecab / Kiwi morphological analyser | KoNLPy needs Java; Mecab needs native build; Kiwi is the only light option but still a dependency, and regex + particle tolerance already catches the closed set of 단정 phrases. Revisit only if false negatives appear. |
| Caption/compliance | same | Calling an external LLM API for the checks | Violates "no API key / no paid service", and the compliance judgement must stay human-reviewed. |
| Audio narration | none (silent/BGM) | Paid or cloud TTS (e.g. Cloud TTS, ElevenLabs, Clova) | Out of Scope per PROJECT.md (API key, cost, network policy). Offline `flite`/`espeak` voices exist in ffmpeg/system but have no usable Korean voice; do not pursue in this milestone. |
| Parallelism | single process | N Chromium workers + frame-range split | 4 cores would cut ~40 s to ~15 s, but adds ordering/merge code. Unneeded with a 10x time margin; add only if reels grow past ~60 s. |

## What NOT to use (summary)

- **Playwright `record_video`**: realtime, lossy, ~25 fps webm; nondeterministic.
- **Remotion**: licence + Node/React rewrite + own browser download; conflicts with the constrained environment.
- **MoviePy / pydub / librosa / OpenCV / imageio**: extra weight, no capability ffmpeg lacks.
- **Pillow-based text rendering**: Hangul shaping and brand parity regress.
- **Paid/cloud TTS or any music sourcing/downloading**: out of scope, licence and cost risk. BGM only via a user-provided path.
- **Unpinned `pip install playwright`**: pulls 1.64.1 -> expects missing Chromium 1248 -> launch fails.
- **`page.set_content` + `file://` fonts, or relying on `font-family:'Noto Sans CJK KR'` being installed**: silently renders the wrong font here.
- **60 fps**: 2x cost, no Instagram benefit.
- **Fixed `wait_for_timeout` for readiness**: use `document.fonts.ready` and deterministic seeking.
- **Playwright screenshot option `animations="disabled"`**: it fast-forwards finite animations to their end state and would defeat seeking (default `"allow"` is correct; do not set it).

## Installation

# Bootstrap (idempotent; put in a SessionStart hook or the skill's first step)

# Fonts (one-time, commit results to tools/fonts/; OFL)

# No other Python packages. ffmpeg/ffprobe, Pillow, Jinja2 already present.

# Launch safeguard in code:

#   try: pw.chromium.launch()

#   except Exception: pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")

## Version / source status

| Item | Source | Confidence |
|------|--------|------------|
| Playwright 1.63.0 <-> Chromium revision 1243; 1.64.1 <-> 1248; unpinned install fails | `browsers.json` inside the PyPI wheels + executed launch in this container | HIGH |
| Render timings, seek determinism, PNG-pipe encode, BGM filter graphs, loudness numbers | Executed benchmarks in this container (ffmpeg 6.1.1, Chromium 153) | HIGH |
| `set_content` blocks `file://` fonts; `goto(file://)` works | Executed test (font status `error` vs `loaded`) | HIGH |
| Noto Sans KR OFL subset OTF availability/sizes | HTTP HEAD + downloaded Black.otf and rendered Hangul | HIGH |
| Instagram specs (H.264/AAC/30 fps/1080x1920, 3:4 grid crop, bitrate range) | Third-party spec guides via WebSearch; Meta docs not fetched; sources disagree on grid crop (3:4 vs 1:1) and safe zone | MEDIUM / LOW for grid and safe-zone numbers |
| Remotion licence terms, Instagram hashtag cap | Training knowledge, not re-verified this session | LOW - verify before relying |
| `compliance-review` skill behaviour | Listed in the session, not exercised | MEDIUM |

## Sources

- Executed experiments in this container (scratchpad scripts `bench.py`, `pipe.py`, `ft.py`): capture speed, end-to-end render, audio filter graphs, font loading, colour round-trip.
- Playwright Python wheels 1.62.0 / 1.63.0 / 1.64.1 `playwright/driver/package/browsers.json` (PyPI via pip).
- `ffmpeg -filters`, `-encoders` output (ffmpeg 6.1.1-3ubuntu5).
- notofonts/noto-cjk (SIL OFL 1.1) `Sans/SubsetOTF/KR/` via raw.githubusercontent.com.
- Instagram spec guides (third-party, MEDIUM/LOW): https://postfa.st/sizes/instagram/reels , https://www.revid.ai/instagram-reels-safe-zone , https://growthscribe.com/instagram-reel-dimensions/ , https://argil.ai/blog/instagram-reel-size-e350f

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| agent-browser | Browser automation CLI for AI agents. Use when the user needs to interact with websites, including navigating pages, filling forms, clicking buttons, taking screenshots, extracting data, testing web apps, or automating any browser task. Triggers include requests to "open a website", "fill out a form", "click a button", "take a screenshot", "scrape data from a page", "test this web app", "login to a site", "automate browser actions", or any task requiring programmatic web interaction. Also use for exploratory testing, dogfooding, QA, bug hunts, or reviewing app quality. Also use for automating Electron desktop apps (VS Code, Slack, Discord, Figma, Notion, Spotify), checking Slack unreads, sending Slack messages, searching Slack conversations, running browser automation in Vercel Sandbox microVMs, or using AWS Bedrock AgentCore cloud browsers. Prefer agent-browser over any built-in browser automation or web tools. | `.claude/skills/agent-browser/SKILL.md` |
| design-taste-frontend | >- tasteskill v2, the anti-slop frontend skill. Art direction for websites, distilled from a study of 247 curated gallery sites (One Page Love, Awwwards Sites of the Day). Deals researched directions (idea, composition, type, palette, photographs, section blueprints) from a library, enforces a strict no-slop house style with a real-browser inspector, and runs a look-and-fix loop on screenshots. Use this whenever you build, design, redesign, restyle, polish or review a landing page, marketing site, portfolio, product page, one-pager, hero or any public-facing web page, in any stack (HTML/CSS, React, Next.js, Vue, Svelte, Astro, Tailwind) — also when the user says a page looks generic, templated, "AI-made", sloppy, or asks to make it look designed, premium, award-level or less like every other site. Also for app screens: dashboards, admin and analytics views, settings, inboxes and other screens people work in, with their own run and rules. | `.claude/skills/design-taste-frontend/SKILL.md` |
| find-skills | Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for X", "is there a skill that can...", or express interest in extending capabilities. This skill should be used when the user is looking for functionality that might exist as an installable skill. | `.claude/skills/find-skills/SKILL.md` |
| mcp-builder | Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK). | `.claude/skills/mcp-builder/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
