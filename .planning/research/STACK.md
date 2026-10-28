# Technology Stack

**Project:** 키움멘토 릴스 제작 자동화 (milestone: draft-bundle automation + subtitle motion upgrade)
**Researched:** 2026-10-28
**Scope:** only what must be ADDED to the existing Python + Playwright + ffmpeg pipeline. The existing system is not re-researched.
**Overall confidence:** HIGH for render/audio stack (benchmarked in this container), MEDIUM for Instagram-side specs (third-party sources only)

## Verdict in one paragraph

Keep the pipeline. Change ONE thing about how frames are made: stop writing a new HTML string per state and instead load **one HTML page once** that exposes a pure function `renderAt(t)` (spec JSON embedded, all motion defined as CSS/Web-Animations seeked to time `t`, count-up done in JS from `t`). Python steps `t` at 30 fps, grabs a PNG per frame with `page.screenshot`, and **pipes the PNG bytes straight into one ffmpeg process** that also mixes the optional BGM. Measured here: a 25 s / 750-frame 1080x1920 reel with motion and BGM renders end-to-end in **~43 s** (screenshots ~25-40 s, x264 encode ~9 s), so the whole bundle fits in the 10-minute budget with a >10x margin. No new heavy dependency is needed: the new Python deps are zero beyond Playwright itself (already required), and caption / checklist generation uses stdlib only.

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

**Frame rate: 30 fps, not 60.** Instagram re-encodes Reels and its guidance converges on 30 fps (23-60 accepted). 60 fps doubles render and encode time for no visible gain on text slides. The existing files are already 30 fps.

**Measured numbers (this container, 1080x1920, one Chromium, Korean text + 3 animated lines + count-up):**

| Capture method | ms/frame | 750 frames | Verdict |
|----------------|----------|------------|---------|
| `page.screenshot(type="png")` | 54 | ~40 s | **Use this** (simple, lossless, only 1.6x slower than the fastest) |
| `page.screenshot(type="jpeg", q=95)` | 36 | ~27 s | Don't: chroma-subsampled JPEG edges on thin Hangul strokes get re-compressed by x264 |
| CDP `Page.captureScreenshot` (png, optimizeForSpeed) | 34 | ~25 s | Optional later optimisation if render time ever matters; needs `new_cdp_session` |
| End-to-end: seek + PNG pipe + x264 `medium` crf 18 + BGM mix + faststart | - | **42.6 s total** | Whole reel; budget is 600 s |
| x264 encode of 750 PNG frames, `medium` crf 20 | - | ~9 s | `veryfast` ~6 s; not worth the quality loss |

Reel + cover PNG + checks together are < 1 minute of compute; the real time cost in the 10-minute budget is Claude writing the script/caption, not rendering.

### Output encoding settings (keep identical for every reel)

```
-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -profile:v high
-vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
-colorspace bt709 -color_primaries bt709 -color_trc bt709
-c:a aac -b:a 160k -ar 44100 -movflags +faststart -r 30
```

Why: H.264 + AAC + 1080x1920 + 30 fps is the consistent Instagram recommendation (MEDIUM: third-party spec guides, Meta docs not fetchable). Tagging BT.709 explicitly is cheap and removes the colour ambiguity: existing untagged reels decode the sage background #DEE9E0 as (220,233,221); tagged encode gives (221,232,223). Both are within 1-3 levels, so this is polish, not a blocker (MEDIUM; measured with ffmpeg's own decoder, not a phone). `crf 18` (vs existing 20) costs only ~1.5x file size on flat-colour content (627 KB for 25 s incl. audio) and keeps thin text crisp after Instagram's re-encode.

### Audio (optional user-supplied BGM)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ffmpeg `filter_complex` (`aloop`/`atrim`, `afade`, `loudnorm`/`volume`) | 6.1.1 | Trim/loop BGM to reel length, fade in/out, level-set | Single tool, no Python audio lib, ~1.7 s on a 25 s reel when video is stream-copied; verified for BGM shorter than video (loops), longer (trims), mp3 and m4a | HIGH (verified) |
| `ffprobe` | 6.1.1 | Read BGM duration / validate file is audio | Already installed with ffmpeg | HIGH |
| `anullsrc` silent track | existing | Keep silent AAC track when no BGM | Existing behaviour; keep so all reels share the same container layout | HIGH |

Recommended BGM filter chain (BGM file path passed as an argument; reel length `T` known from the spec):

```
[1:a]aloop=loop=-1:size=2000000000,atrim=0:T,aresample=44100,aformat=channel_layouts=stereo,
     volume=0.5,afade=t=in:d=0.8,afade=t=out:st=T-1.5:d=1.5,alimiter=limit=0.89[a]
```

Notes:
- Loop with `aloop=loop=-1:size=2e9` + `atrim` (verified, exact `T` duration, no gap issues). `-stream_loop -1` on the input also works; either is fine.
- Level: there is no voice to protect, so BGM is the only audio; target roughly **-16 to -18 LUFS integrated, true peak <= -1.5 dBTP**. Verified `loudnorm=I=-16:TP=-1.5:LRA=11` followed by fades and `volume=0.8` lands at -18.1 LUFS (measured with `ebur128`). Prefer: fades first, `loudnorm` last, no extra `volume`, so the target is what you get. Single-pass `loudnorm` is acceptable for a 25 s clip; use two-pass only if levels look off (LOW need).
- If a future v2 adds voice: use `sidechaincompress` ducking (already in this ffmpeg). Not needed now.
- Validation (do in Python, stdlib): file exists, `ffprobe` reports an audio stream, duration >= 3 s. **Never** fetch, search for, or default to any music; BGM only when the user passes a path (copyright constraint in PROJECT.md). Record the BGM filename in the bundle's checklist so the human reviewer confirms the licence.

### Fonts (new, required)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Noto Sans KR (Subset OTF: Regular, Bold, Black)**, SIL OFL 1.1 | notofonts/noto-cjk main (`Sans/SubsetOTF/KR/NotoSansKR-{Regular,Bold,Black}.otf`, ~4.6/4.8/5.0 MB) | Guarantee brand glyphs regardless of what the session image has installed | Same design as the "Noto Sans CJK KR" used by the existing reels (weights 400/700/900 are what `reel.py` uses; `cards.py` also uses 500, so add Medium ~4.7 MB if cards are migrated). OFL allows redistribution in-repo. Download verified reachable via `raw.githubusercontent.com` | HIGH (download + render verified for Black) |

Commit the files under `tools/fonts/` and declare `@font-face{font-family:"KiwoomSans"; src:url("fonts/NotoSansKR-Black.otf"); font-weight:900}` etc. **Pitfall verified:** `page.set_content()` pages are `about:blank`, so `file://` font URLs fail (`document.fonts` status = `error`, silent fallback). Write the template to disk (or use `page.goto("file:///.../template.html")`) so relative font URLs load (status = `loaded`). Then always `await document.fonts.ready` (`page.evaluate("document.fonts.ready")`) and assert every font status is `loaded` before the first screenshot; this replaces the existing fragile `wait_for_timeout(60)`.

### Caption / hashtag / compliance checklist generation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Claude itself (in-session) | - | Writes reel script JSON, caption, hashtags, proposes replacement wording | Project constraint: no external LLM API. The skill prompt carries the style rules (existing 10 specs as few-shot, scene pattern hook -> analogy -> numbers -> conclusion -> caveat -> CTA) | HIGH |
| Python stdlib only: `re`, `json`, `dataclasses`, `pathlib`, `argparse` | 3.13 | Deterministic spec validator + 금소법 expression linter + bundle writer | The lint is a lexicon + regex pass over `top`/`lines`/`basis`/caption; it needs no NLP. Reproducible, unit-testable, zero install. | HIGH |
| Lexicon as data file (`tools/compliance_terms.json`) | - | Banned/flagged phrases with category and suggested replacement | Lets the user/Claude extend rules without code changes. Categories from PROJECT.md: 단정 수익/원금 보장, 무조건 절세·세무 단정, 근거 없는 수치, 타사 비방, 개인정보 | HIGH (structure), MEDIUM (term coverage - needs legal-minded review) |
| Existing `compliance-review` skill (anthropic-skills:compliance-review) | - | Second-pass human-readable judgement of the same draft (단정 표현, 설명의무, 비교광고) | Already available in the session; use it as the *judgement* layer on top of the *deterministic* lint, not a replacement | MEDIUM (not exercised here) |
| Jinja2 | 3.1.6 (already installed) | Optional: render the Markdown checklist / caption file | Only if Markdown templating gets non-trivial; f-strings/`str.format` suffice otherwise. Do NOT use Jinja2 for the video HTML (see architecture note) | MEDIUM |

Checks the linter should implement (all regex, all stdlib):
1. Banned/flagged phrase list ("원금 보장", "확정 수익", "무조건", "100% 환급/절세", "반드시 오릅니다", "손해 없는", "최고 수익", etc.) with Korean particle tolerance (`원금\s*보장(됩|이|을|은)?`).
2. Numbers with units (`%`, `원`, `만 원`, `배`, `년`) in `lines` -> must have non-empty `basis` and either an example/assumption marker ("예시", "가정", "기준", "추정") in `basis` or flag as "근거·기준 미표기".
3. Tax/legal 단정 patterns ("~하면 세금 0원", "누구나 공제") -> suggest "세무사 확인 필요" wording; confirm the caveat scene (세무사 확인) exists.
4. CTA scene present, handle `@kiwoom.mentor` present, no customer names/case markers (simple heuristics only; flag, don't decide).
5. Caption: length <= 2,200 chars (Instagram limit, MEDIUM), hashtag count within a configurable cap (default keep modest, ~5-10; LOW confidence on Instagram's current hashtag cap - verify before hard-coding), disclaimer line present.
6. Output is a Markdown checklist (`[ ]` items with line reference + suggested replacement). It must state "초안, 사람 검수 필요". The linter flags; it never auto-fixes published wording.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | 12.3.0 (preinstalled) | Contact sheet / sanity checks (e.g. composite 4 frames into one PNG for quick review), pixel-colour assertions in tests | Only for QA helpers, never for text layout |
| `ffprobe` JSON output | system | Post-render verification (duration, fps=30, 1080x1920, audio present, has +faststart) | Always, as the last step of the bundle; fail loudly |
| pytest | latest via pip (not installed) | Unit tests for the linter and spec validator | Optional; stdlib `unittest` works with zero install and is enough |
| Playwright `launch(args=[...])` flags | n/a | `--font-render-hinting=none` for stable glyph rendering across machines | Add if text edge differences appear between runs; not required now (LOW) |

## Architecture note that drives the stack (for roadmap)

Today `frame()` rebuilds an f-string per state and calls `set_content` ~48 times; motion would need many more states. Replace with:
1. `tools/reel_template.html` (+ `tools/fonts/`): loaded once via `goto(file://...)`; spec injected with `page.evaluate("spec=>window.init(spec)", spec)`.
2. `window.renderAt(t)`: computes visible lines, per-line entrance progress (translateY 60 px -> 0 + opacity 0 -> 1, ease-out ~0.45 s), scene transition (outgoing fade/slide over ~0.35 s, incoming staggered), count-up (`Math.round(from + (to-from) * easeOutCubic(p))` formatted with `toLocaleString("ko-KR")`), progress bar width. Everything derives from `t` only.
3. Python loop: `for i in range(n): page.evaluate("t=>renderAt(t)", i/30); ffmpeg.stdin.write(page.screenshot(type="png"))`.
4. Cover PNG = one `renderAt(cover_t)` screenshot saved as PNG (keep headline inside the central ~1080x1440 area; the grid now crops Reels covers to ~3:4 per most sources, but one source says 1:1, so confirm in Instagram's cover editor - MEDIUM/LOW).
5. Timing model stays in the spec/Python (per-line start times, scene hold), computed once and passed to the page, so duration and `cover_ms` stay consistent with the existing output.

Keep the existing `<g>` / `<s>` markup contract; add one new inline marker for count-up (e.g. `<c from="0" to="1,200">` ... decide in requirements) so existing 10 specs render unchanged with the new engine (regression check: render old specs with motion disabled and compare against current MP4s).

Count-up pitfalls to design for: reserve the final-width box (render the final number invisibly, overlay the animated one) so lines do not reflow each frame; format with thousands separators; hold the exact final value for the whole hold period so the number readers screenshot is the stated number.

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

```bash
# Bootstrap (idempotent; put in a SessionStart hook or the skill's first step)
python3 -m pip install --quiet "playwright==1.63.0"      # matches preinstalled chromium-1243
export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers          # already set in cloud sessions
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1                 # already set; never run `playwright install`

# Fonts (one-time, commit results to tools/fonts/; OFL)
mkdir -p tools/fonts && cd tools/fonts
for w in Regular Bold Black; do
  curl -sSLO "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/KR/NotoSansKR-$w.otf"
done

# No other Python packages. ffmpeg/ffprobe, Pillow, Jinja2 already present.
# Launch safeguard in code:
#   try: pw.chromium.launch()
#   except Exception: pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
```

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
