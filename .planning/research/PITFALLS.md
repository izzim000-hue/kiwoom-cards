# Pitfalls Research

**Domain:** Automated subtitle-style Instagram Reels production for Korean financial-education content (LLM-drafted scripts with tax/pension figures, captions, hashtags, compliance checklist; subtitle motion and BGM on an existing Python + Playwright + ffmpeg renderer, run in an ephemeral Claude Code cloud container with restricted network)
**Researched:** 2026-10-28
**Confidence:** MEDIUM overall (container/renderer findings HIGH because tested locally; Korean legal text and Instagram spec numbers MEDIUM-LOW because primary sources were unreachable, see "Verification status")

## Verification status (read first)

The cloud session's allowed-domain list blocked the primary sources: developers.facebook.com, law.go.kr article text, nts.go.kr, korea.kr, ko.wikisource.org and wikidocs.net all failed DNS resolution. Only WebSearch summaries (mostly blogs and vendor sites) were available. Tags used below:

- **[TESTED]** reproduced in this container on 2026-10-28 (HIGH confidence).
- **[CORROBORATED]** several independent secondary sources agree (MEDIUM).
- **[CONFLICTING]** sources disagree, so do not hard-code a number (LOW).
- **[UNVERIFIED]** from general knowledge or a single source. Re-check against the primary source before relying on it (LOW).

Legal and tax statements here are engineering inputs for a human reviewer. They are not legal advice, and the checklist this project builds must never present them as a compliance determination either.

---

## Critical Pitfalls

### Pitfall 1: The renderer silently falls back to a different Korean font in the cloud container (brand drift plus layout change)

**What goes wrong:**
`tools/reel.py` asks for `font-family:'Noto Sans CJK KR',sans-serif`. In this container `fc-match "Noto Sans CJK KR"` resolves to **Inter**, and Hangul comes from **WenQuanYi Zen Hei** [TESTED]. Only Noto Color Emoji, IPAGothic (no Hangul), WenQuanYi and Unifont are present. A test line at 100px/900 rendered without error, but in a different typeface from the 10 shipped reels. Because glyph widths differ, a line that fits in the original font wrapped onto a second line ("16.5 / 만 원") and the block moved vertically. Nothing fails. You get a plausible-looking MP4 with the wrong look, and a reviewer comparing to the previous episode may not notice. Weight 900 can also be synthesized (fake bold) when only a Bold face exists.

**Why it happens:**
The 10 existing reels were presumably rendered on a machine with Noto CJK installed. The SessionStart hook installs GSD and agent-browser but not fonts. Chromium never errors on missing `font-family`.

**How to avoid:**
- Vendor the brand font in the repo (`tools/fonts/`, OFL-licensed Noto Sans KR or Noto Sans CJK KR Black and Bold) and load it with `@font-face { src: url(file://...) }`. Subset it with fonttools `pyftsubset` to the KS X 1001 Hangul set plus Latin, digits and punctuation so the file stays small (a full CJK Black OTF is roughly 15 MB, which is unverified, so measure it).
- After `set_content`, `await document.fonts.ready` and assert `document.fonts.check("900 100px 'Noto Sans KR'")`. Abort the render with a clear error if the check fails, instead of waiting a fixed 60 ms.
- Add a render-time overflow guard (below, Pitfall 9) so a different font cannot silently reflow text.
- Golden-image test: render the first frame of one existing spec and compare to a stored reference PNG with a perceptual tolerance. If the font changed, this fails loudly.

**Warning signs:**
`fc-match "Noto Sans CJK KR"` does not print Noto. First-frame diff against an existing reel is non-zero. Lines wrap that did not wrap before. Letterforms of "g", "r" and digits look different.

**Phase to address:**
Phase 1 (renderer hardening, before any new feature). Everything visual depends on it.

---

### Pitfall 2: `pip install playwright` pulls a version whose expected Chromium build is not preinstalled

**What goes wrong:**
Playwright is not preinstalled here. A plain `pip install playwright` installed 1.64.1, which wants `/opt/pw-browsers/chromium_headless_shell-1248/...`. The container has build **1243** [TESTED]. `reel.py` crashes with "Executable doesn't exist". Downloads are disabled (`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`), and `playwright install` is blocked by network policy. Launching with `executable_path="/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"` works (Chrome 153) [TESTED].

**Why it happens:**
The browser image and PyPI move independently. The paths `/opt/pw-browsers/chromium` (a file or symlink) and `chromium-1243/` differ, and the SessionStart hook only exports `AGENT_BROWSER_EXECUTABLE_PATH` for agent-browser, not for Playwright. Note also that PyPI appears reachable while browser downloads are not.

**How to avoid:**
- Pin the Playwright Python version that matches build 1243 in a `tools/requirements.txt`, or make `reel.py` resolve a Chromium executable (env var, then glob `/opt/pw-browsers/chromium-*/chrome-linux64/chrome`) and pass `executable_path`. Keep both as a fallback chain.
- Add the install and smoke test (`python3 tools/reel.py --selftest`: launch, render one frame, `ffmpeg -version`, font check) to the SessionStart hook or the skill's first step, so failures show up in seconds rather than mid-bundle.
- The Chromium revision will change when the container image updates, so do not hard-code 1243 anywhere except a comment.

**Warning signs:**
"Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-NNNN". `ModuleNotFoundError: playwright` in a fresh session.

**Phase to address:**
Phase 1 (environment and self-test).

---

### Pitfall 3: LLM-written tax and pension figures that are stale, hallucinated, or conflate "proposed" with "in force"

**What goes wrong:**
The LLM writes 연금저축/IRP numbers from training memory, and training data lags legislative changes. Common failure modes:
1. **Wrong or old limit or rate.** Search summaries indicate current law (소득세법, effective 2026-01-01) is: 세액공제율 15% if 종합소득금액 ≤ 4,500만 원 (근로소득만 있으면 총급여 ≤ 5,500만 원), otherwise 12%. The limit is 연금저축 600만 원, and 연금저축 + IRP combined 900만 원 [CORROBORATED, mostly blogs, primary text not reachable]. With 지방소득세 the effective figures are 16.5% and 13.2%, which is what spec `2026-10-26-tax-deduction.json` uses. Older figures (400만/700만, 12%/15% swapped by income, 50세 이상 추가 한도 history) remain all over the web and in model memory. One search even surfaced a 지방세법 article still showing 400만/700만, which shows the same law text can appear in conflicting versions [UNVERIFIED which is current].
2. **Proposed law stated as law.** A member-sponsored bill to raise the IRP rate from 12% to 15% and give 17% to young earners (총급여 ≤ 5,500만) was circulating [CORROBORATED, bill status unknown]. An LLM will happily write "내년부터 17%".
3. **Boundary precision.** The existing spec says "총급여 5,500만 원 기준" with no 이하/초과 and ignores the 종합소득금액 4,500만 원 criterion. A pattern the LLM will copy.
4. **Time-sensitive statistics** (물가 2.9%(26년 9월), 국민연금 월평균 수령액, 평균 퇴직 연령 53세, 기관명 such as "국가데이터처", which is a 2025 rename of 통계청). The model will use whichever it remembers.
5. **Arithmetic done in prose.** Compounding, 15.4% 이자소득세, 단리 average-balance interest. The existing 5% 적금 example is internally correct (월 100만 × 5% × 78/12 = 32.5만 → 세전 2.7%, 세후 약 2.3%), but an LLM re-deriving it will sometimes be off.

**Why it happens:**
The "basis" field is free text, so the model can write a convincing source line that it did not actually check. Review fatigue means a plausible number passes.

**How to avoid:**
- Create a **figures registry** (`tools/facts.json` or `.planning` data file): each entry has `id`, `value`, `unit`, `as_of` (기준일), `source_name`, `source_url`, `verified_on`, `valid_until` (for example, end of the tax year or next 세법개정 date). The LLM may only reference registry IDs in specs (`{{fact:pension_credit_limit}}`), and the renderer or linter expands them. A number that is not in the registry is flagged "unsourced".
- Compute all derived numbers in Python (a small calc module with unit tests that reproduce the 10 existing specs' numbers), never in the LLM's head.
- Mark each fact's status: `in_force`, `proposed` (발의/개정안), `repealed`. Block `proposed` facts from unqualified phrasing and force "개정안, 확정 아님".
- Make the figure freshness check a hard gate: `verified_on` older than N days (suggest 90) or `valid_until` passed produces a blocking item in the review sheet. Registry updates are a human task, with the source URL opened from law.go.kr or nts.go.kr (add those domains to the session allowlist if possible; otherwise the human verifies outside the session).
- The review sheet lists every number in the reel with its registry ID, source and as-of date, so the reviewer checks 8 numbers rather than re-reading prose.

**Warning signs:**
A spec number with no registry ID. `basis` strings like "국세청 기준" with no year. A tax-year mismatch between the reel's publish date and the fact's `as_of`. Numbers that differ from the previous reel on the same topic.

**Phase to address:**
Phase 2 (script and draft generation) for the registry and calc module. Phase 3 (compliance review sheet) for the freshness gate.

---

### Pitfall 4: A deterministic keyword checklist produces false confidence ("점검표 통과 = 컴플라이언스 통과")

**What goes wrong:**
A regex list of "원금 보장", "확정 수익", "무조건 절세", "100% 환급" is easy to build and gives a green tick. It will:
- **Miss paraphrases and semantics:** "원금은 안 깎여요", "손해 볼 일 없어요", "누구나 13만 원 돌려받아요", "반드시 이득", "절세 효과 확실", "지금 안 하면 손해" (공포 유도), "~하세요" read as a direct 권유, implied guarantees in metaphors, a rate that implies an expected return with no scenario. These match zero keywords.
- **Over-flag negations**, such as "원금 보장이 아닙니다", which teaches reviewers to ignore the sheet (alert fatigue).
- **Pass the dangerous category entirely.** 단정 on 세무 ("세액공제도 0원" without conditions, "낮은 구간은 세액공제가 유리") is a judgment statement. The existing specs hedge it with "효과가 커지는 편" and "세무 판단은 세무사 확인", which a keyword list cannot distinguish from an unhedged version.
- **Output "PASS"**, and the human reviewer relaxes.

Legal frame, as far as verifiable: 금융소비자보호법 부당권유행위 금지 (제21조) includes providing **단정적 판단** or content that may mislead a consumer into thinking an uncertain matter is certain; 광고 규제 (제22조 and 시행령) prohibits wording that misleads people about 손실보전/이익보장 and requires specified items to be included and, for 금융상품판매업자등, **내부심의** (and, depending on the sector, association pre-review) [CORROBORATED via secondary sources; 조문 원문 not retrievable here, so cite 조문 and 시행령 numbers only after checking law.go.kr]. A 2026-04 report says 금감원 and 금융투자협회 launched a 광고 제도 개선 TF (필수 안내사항 누락 as a main problem type), with an improvement plan expected in Q3 2026 [CORROBORATED, one news source]. **The rules may be changing right now, so the checklist's rule set must be versioned and dated.** KOFIA has also said a 심사필 번호 reviews the display method, not the truthfulness of the content [CORROBORATED], so even an association-reviewed ad does not mean the numbers are right.

**Why it happens:**
The "checklist" is built to meet the requirement "표시된다", and "no flags" is naturally rendered as "OK".

**How to avoid:**
- **No PASS state.** The sheet's possible outputs are only: `FLAGGED (n)` or `NO PATTERN FLAGS - HUMAN REVIEW STILL REQUIRED`. Name it "금소법 표현 점검 보조", not "금소법 준수 확인". The title and footer say "자동 점검은 법무·준법 검토를 대체하지 않음".
- **Three layers, labeled separately:** (1) deterministic patterns with a versioned, dated rule file (단정어, 보장/확정/무조건/반드시/누구나/100%, 공포 유도, 상품명 + 권유 동사, 타사 비교·비방); (2) an LLM semantic read focused on 단정적 판단 and 권유 (clearly marked as model judgment with quoted evidence lines), which can miss things too; (3) a numeric ledger (every figure has a `basis`/registry ID, per Pitfall 3).
- **Structural checks beat keywords:** every scene with a number needs basis coverage; the final scene needs the disclaimer line; reels containing 세무/법률 claims need the "세무사 확인" line; a `확정`/`보장` word in any scene needs an explicit negation or a human-resolved flag.
- **Test the checker with a red-team corpus:** a `tests/compliance-cases.json` of at least 30 bad sentences (including paraphrases that the regexes are not tuned to) and 15 good sentences. Report recall honestly (the regex layer will not reach 100%), and keep adding every violation found in review.
- Provide replacement suggestions, but as text for the human to accept. Never auto-edit a spec to "clean".
- Confirm with the account owner and 준법감시인 whether this account falls under 금융상품판매업자등의 광고 (Pitfall 5) and what the 필수 고지 and 심의 steps are. Then encode them. Until confirmed, the sheet lists these as "미확인 - 담당자 확인 필요", never as satisfied.
- Reuse the existing `compliance-review` skill as one input to the human review, not as a certificate.

**Warning signs:**
The sheet has ever printed an all-clear. A reviewer's edits are never prompted by the sheet. The checker's rule file has no date or version. Zero entries in the red-team corpus came from real review findings.

**Phase to address:**
Phase 3 (compliance review sheet). The red-team corpus should be seeded in Phase 2.

---

### Pitfall 5: Treating "educational content" as outside 광고 rules, and missing who is advertising and what must be disclosed

**What goes wrong:**
The project's strategy is "교육적 중립성", and the flow ends in a CTA to 프로필 링크 → 상담. Whether regulators treat a given reel as a 광고 of the business (금융상품판매업자등의 업무에 관한 광고) depends on facts the pipeline cannot see (the account owner's registration type, whether products are named, the CTA). If it is an ad, then 필수 포함사항 (such as the 판매업자 정보 and 상품 위험 안내), 내부심의 and 광고 문구 규칙 apply, and a reel with only "세무사 확인" does not satisfy them. Related risks: the brand names ("키움멘토", repo `kiwoom-cards`) can be read as 키움증권 affiliation, and the 금소법 prohibits ads that make an agent or intermediary look like the direct seller (the "네이버통장" rule) [CORROBORATED]. The relationship between 키움멘토 and the 키움 brand and the actual 등록 status are not documented in the repo [UNVERIFIED, owner question].

**Why it happens:**
Developers encode "what the old reels did" as the compliance baseline, but those 10 reels passed (or not) a human process the code cannot see.

**How to avoid:**
- Put a **pre-implementation decision** in the roadmap: owner and 준법 contact answer (a) is this account's content a 광고 under 금소법/보험업법, (b) the exact 필수 고지 text and placement (video, caption, or both), (c) the internal 심의 process and any 심의필 number format, (d) allowed and forbidden 상품 mentions.
- Make the fixed disclosures **configuration** (`compliance.json`) rendered by the pipeline on every reel and caption (last-scene text, caption footer), not LLM-generated text.
- The draft bundle includes a **심의 slot** (`review_status: draft | internal_reviewed | approved`, reviewer, date, 심의번호 if any). The bundle is not marked publishable until a human fills it.
- Never add "저희 상품", "가입", or named products to prompts or templates by default.

**Warning signs:**
The caption template has no company or contact identification. The reel names a specific fund, insurer or ETF. The CTA changes from "계산기" to a direct sales pitch.

**Phase to address:**
Phase 0/2 (owner decision before design), Phase 3 (encode as configuration).

---

### Pitfall 6: Breaking the 10 existing specs and the existing output (regression of validated work)

**What goes wrong:**
Motion, new fields and the safe-zone fixes alter the shared renderer. Typical regressions: the timing constants `LINE=0.85; HOLD=1.9` get moved into per-spec defaults and change the lengths of old reels; `<g>`/`<s>` parsing changes (for example switching to a real HTML parser and breaking nested or unclosed tags in old specs); `cover_ms` is computed from old timing and no longer points at the right frame; a newly mandatory spec field (`format_version`, `fact_ids`) makes old specs fail validation; re-rendering an old spec to test it **overwrites a committed MP4** that was already published, creating a binary diff in git and a mismatch with what is live.

Also, `reel.py` accepts only `spec out` positionally, with no schema, and output names follow `2026/reels/<게시일>-<slug>.mp4`. The repo has 12 MP4s but only 10 specs (`2026-10-19-savings-interest.mp4` and one other have no spec file). Those two cannot be regression-tested at all.

**Why it happens:**
No tests exist. The renderer is a 39-line script, so every change feels safe.

**How to avoid:**
- Treat the 10 specs as a **golden corpus**: before changing the renderer, render all 10 to a scratch dir and store per-reel signatures (frame count, duration, scene-boundary timestamps, first frame, frame at `cover_ms`, mid-scene frames, hashed as downscaled PNG or SSIM thresholds). Every change must keep a **legacy mode** producing identical timing (`"motion": "none"` default for specs without a motion key).
- All new spec fields are **optional** with defaults that reproduce old behavior. Version the schema (`"v": 1` implied when absent). Validate with a schema and print warnings, not exceptions, for legacy specs.
- Make `--out` default to a scratch directory. Writing into `2026/reels/` requires an explicit `--publish-path`, and refuses to overwrite an existing MP4 unless `--force`. Keep scratch outputs out of git (`.gitignore`).
- Reverse-engineer the two missing specs, or mark them "legacy, unreproducible".
- Keep `cover_ms` semantics (print the same line format `duration=…s cover_ms=…`), because the skill or the user's habit may parse it.

**Warning signs:**
`git status` shows modified existing MP4s after a test run. Duration printed for an old spec differs from the old duration (24.35 s for rate-secret-1, for example). Old spec raises a KeyError.

**Phase to address:**
Phase 1 (golden corpus and legacy mode must exist before Phase 4 motion work).

---

### Pitfall 7: Final-scene and "basis" text hidden by Instagram's UI (safe zones) and the profile-grid crop

**What goes wrong:**
`reel.py` places the **basis line and @kiwoom.mentor at `bottom:150px`** (y ≈ 1740-1770 on a 1920 canvas). Instagram's caption, account name, audio ticker and CTA buttons overlay the bottom of a Reel. Secondary sources agree that the bottom roughly 25-35% and a right-side action column are unsafe; the quoted figures disagree [CONFLICTING]: Meta percentages relayed by Hopper/House of Marketers (about 14% top, 35% bottom, 6% sides, about 40% bottom right), versus pixel guides of 108-270 px top, 250-450 px bottom, 60 px left and 120 px right. So the 근거 표기, which is the compliance-relevant disclosure, is **likely covered while the reel plays**. The progress bar at y=0-14 sits in the top-UI zone too. In addition, the profile grid is now 3:4 and crops a 1080×1920 reel's cover to the center about 1080×1440 (240 px off the top and bottom) [CORROBORATED, exact start date and pixel numbers differ across sources], so cover text near the edges is cut in the grid.

Motion makes this worse: slide-in or scale effects move text through the unsafe regions, and count-up numbers placed low get hidden.

**Why it happens:**
The layout was designed for a clean 1080×1920 canvas, and no overlay was ever checked against the real app.

**How to avoid:**
- Define safe-zone constants in one place, conservative by default: keep all critical text inside roughly x 60-960 (right rail ≥ 120 px), y 270-1250 (top 14%, bottom 35%) [percentages from secondary sources; confirm once in Instagram's own composer preview with an actual upload as a private test, an irreducible human step].
- **Move the 근거 (basis) line up** into the safe area, or repeat it in the caption (and treat the caption as the legally important copy). Decide with the compliance owner whether the in-video basis is required or just helpful.
- The cover PNG must keep its title inside the central 1080×1440 band, and ideally inside the 3:4 crop with margin. The default `cover_ms` frame should be checked against that.
- Add a `--safe-overlay` debug mode that draws the zones over a frame for the review sheet.
- Do not move the whole layout for old reels if the human accepts the existing look, but track it as a known, documented deviation. Changing it alters brand consistency (Pitfall 8), so decide explicitly.

**Warning signs:**
In the app preview, the basis line sits under the caption text. The cover's top line is cropped in the grid view.

**Phase to address:**
Phase 1 for constants and decision; Phase 4 (motion) must respect them. Verify with a real private upload preview once.

---

### Pitfall 8: Brand drift when LLM scripts and new motion are added

**What goes wrong:**
Voice drift (formal "~입니다" vs. the existing short punchy lines, emoji, English loanwords, ad-style hype), structure drift (not following 훅 → 비유 → 수치 → 결론 → 주의사항 → CTA with 7 scenes, 17-22 lines), CTA drift (the final line `저장해두고… 프로필 링크 · 1분 노후자금 계산기` altered), series-numbering errors ("금리의 비밀 ③" duplicated), and visual drift: new easing, bounce, bright colors and glitch transitions that fit consumer apps but not a "교육적 중립성" brand. The font drift of Pitfall 1 is a visual cause too. Colors can also shift from the brand sage `#DEE9E0`: the current encode is **untagged BGR→YUV (color_space unknown)** [TESTED], so players may apply BT.709 to BT.601 data and shift the sage and deep green slightly. Adding any new gradient or fade transition between scenes will expose banding at the tiny existing bitrate (about 106 kbps total on a shipped reel) [TESTED].

**Why it happens:**
The LLM is shown a list of requirements instead of the 10 specs. Motion is added where it is easy, not where it fits.

**How to avoid:**
- Put **2-3 existing specs as few-shot exemplars** in the skill prompt, and state hard structural constraints as a validator: exactly 7 scenes (or the observed range), a final CTA scene identical to a stored template, ≤ N lines per scene, per-line length caps measured by rendering (Pitfall 9), `top` label conventions, and the series label pattern.
- Keep a **style budget for motion:** a single easing curve (ease-out, 250-350 ms), a fade or short slide only, with no motion on the disclosure and CTA lines. Include a `motion` preset name in the spec, and keep `"none"` the default.
- Tag colors explicitly: add `-colorspace bt709 -color_primaries bt709 -color_trc bt709` and a matching `scale=…:out_color_matrix=bt709:out_range=tv` so the brand color renders consistently [HIGH from ffmpeg behavior, UNVERIFIED on-device]. Change it only if the golden-corpus comparison tolerates it, as this alters existing look slightly.
- A "series continuity" check: next-episode teaser lines (`<s>다음 편: …</s>`) must match the next spec's `top`.

**Warning signs:**
Reviewer edits are mostly tone. A new reel looks "newer" next to the old ones in the grid. Colors on the phone differ from the PNG.

**Phase to address:**
Phase 2 (generation constraints), Phase 4 (motion style budget).

---

### Pitfall 9: Text overflow, wrapping and line-count blowups from LLM-written lines

**What goes wrong:**
`reel.py` uses fixed 100px type in an 888 px content width with `line-height:1.3` and a vertically centered column. Existing specs have lines of up to 20-22 characters (`<s>` lines are smaller at 52px). An LLM that produces a long line, or a scene with 5-6 lines, causes wrapping, overflow beyond the top or bottom, and collision with the basis line, but the renderer will not error. The last-scene or number-heavy scenes are most at risk. Wrapping is also font-dependent (Pitfall 1). Korean has no spaces mid-word. `word-break` default can split mid-word oddly: set `word-break: keep-all`, which the current CSS lacks.

**How to avoid:**
Measure in the browser: after laying out each frame, check `scrollWidth/scrollHeight`, each line's `getBoundingClientRect().height` against the single-line height (wrapping detected), and the block's bounding box against the safe zone. Fail with the scene and line number, and let the generator loop (LLM rewrites shorter) before the human sees it. Add `word-break: keep-all`. Keep a hard cap on lines per scene, and on total scenes and duration (existing 20.8-26.1 s).

**Warning signs:**
Rendered line count per scene differs from spec line count. Basis text overlapped.

**Phase to address:**
Phase 1 (measurement guard) and Phase 2 (generator loop).

---

### Pitfall 10: Per-frame motion rendering blows up time, memory, and artifacts in the container

**What goes wrong:**
Today's renderer takes one screenshot per *state* (about 20 per reel), then lets the concat demuxer hold frames. Motion needs a unique frame per 1/30 s. Measured here: a 1080×1920 PNG screenshot costs **about 0.14 s** (JPEG about 0.11 s) with a trivial page [TESTED]. A 25 s reel at 30 fps is 750 frames, so about 100-110 s for screenshots alone, and more with `set_content` on every frame and heavier DOM. Moderately fine for one reel, but it breaks in these situations: (a) the 10-minute target for the whole bundle (script + render + cover + caption + checks) loses its budget when someone re-renders after each edit; (b) the temp directory holds 750 PNGs at several hundred KB each (hundreds of MB; `tempfile.mkdtemp()` is never cleaned up in the current code, so repeated runs fill the container disk); (c) running 10 reels as a batch takes more than 15 minutes.

Wrong approaches that look attractive: recording Chromium video in real time (nondeterministic timing and dropped frames), CSS animations plus screenshot at wall-clock times (race conditions, frames that depend on machine speed), `wait_for_timeout` per frame (adds seconds), `setTimeout`-driven count-up in the page.

**How to avoid:**
- **Deterministic frame-indexed rendering:** drive all motion from a pure function `state(t = n/fps)` (set CSS variables or call `window.__setT(t)`), never from wall-clock. Use `page.clock` or the Web Animations API (`animation.currentTime = t; animation.pause()`) rather than timers.
- **Render only distinct frames:** during hold phases, reuse the same PNG (concat durations as today). Animate only the short transitions (about 8-12 frames per element-in, per transition). That keeps frames to roughly 150-300 per reel, not 750.
- Keep one page and update it (`page.evaluate`) rather than `set_content` per frame. Consider `clip` screenshots and JPEG quality ≥ 95 for intermediates, or pipe PNG bytes to ffmpeg's stdin with `-f image2pipe` instead of files.
- Alternative for pure transitions and count-ups that avoid per-frame browser work: render a few keyframe stills and use ffmpeg `xfade`/`overlay` expressions (xfade and drawtext exist in this ffmpeg 6.1.1 build [TESTED]). Caveat: `drawtext` needs a Hangul-capable font file path, and the font problem returns.
- Always use `try/finally` to delete temp dirs, and print timing per stage. Set a render time budget (for example, fail loudly past 5 min) and a `--fast` draft mode (lower fps, 540×960) for iteration, with final render at full quality.

**Warning signs:**
Render wall time over 3 minutes for a single reel. `/tmp` usage growing between runs. Motion looks slightly different on every run.

**Phase to address:**
Phase 4 (motion). Establish the timing budget in the plan.

---

### Pitfall 11: Frame-timing drift, last-frame and audio-length mismatches in the concat pipeline

**What goes wrong:**
Specific traps in the current approach and its extension:
- `LINE=0.85` s is 25.5 frames at 30 fps. The `fps=30` filter assigns frames by timestamp, so there is no cumulative drift, but each line's visible length jitters ±1 frame. Motion keyframes aligned to "0.85 s" will land on alternating frames. Choose durations in whole frames (for example, 0.8667 s = 26 frames, or 0.8 s = 24).
- The concat demuxer ignores the duration of the last entry unless the file is listed again (the current code does this), and mixing sequence-of-frames sections with long-hold sections in one concat list multiplies the number of entries and risks off-by-one at section joins.
- `-shortest -t total` combined with `anullsrc` (infinite) works, but **adding a BGM input changes which stream is shortest**: a BGM file shorter than the video truncates the video (a reel cut early), and a longer one is clipped abruptly at the end without a fade. If AAC priming adds delay, A/V can offset by about 20-50 ms (imperceptible for silent captions, relevant only once timed SFX arrive).
- Cover frame: `cover_ms` is computed from `LINE*(first-1)+0.4`, so any change in motion timing (an element animating in) leaves the cover at a half-animated state. Instagram's cover is chosen by the user in the app from a timestamp or an uploaded image, so the pipeline should output a **separate designed cover PNG**, not a timestamp.

**How to avoid:**
- Compute the whole timeline once as integer frame counts (`timeline = [(scene, line, start_frame, end_frame)]`), derive `total`, `cover frame`, and any audio fade points from it, and render frames by index.
- BGM: loop or trim with `-stream_loop -1`/`atrim`, apply `afade=t=out:st=<total-1.5>:d=1.5` and a fixed gain (see Pitfall 13), and keep `-t total` as the authority for duration (not `-shortest`), then assert with `ffprobe` that duration of video = audio within 50 ms.
- Add a post-render `ffprobe` check: `h264`, `yuv420p`, `1080x1920`, `r_frame_rate 30/1`, `aac`, duration within 0.1 s of the plan, and faststart.

**Warning signs:**
`ffprobe` duration ≠ printed `duration=`. Last line flashes. Fade-out cut by the end.

**Phase to address:**
Phase 4 (timeline refactor) and Phase 5 (BGM).

---

### Pitfall 12: Instagram upload specs held as folklore (and a few non-problems)

**What goes wrong:**
Secondary sources on Reels specs conflict heavily [CONFLICTING]: max length 3 min (in-app) versus up to 15 min (API reference as quoted), max file size 250 MB, 300 MB, 1 GB or 4 GB, bitrate guidance 3.5 Mbps minimum versus 8-12 Mbps, 4K supported or not. Consistently reported (and compatible with shipped files) [CORROBORATED]: 9:16 at 1080×1920, MP4/MOV, H.264 + AAC, 30 fps (higher accepted), Instagram re-encodes everything, so export at higher quality rather than pre-compressing. Meta's own developer documentation was **not reachable** in this session, so anything numeric should be re-checked there.
Relevance for this project is low on length and size (reels are 20-26 s, 0.2-0.35 MB) but:
- **Don't over-engineer to a spec number**, but also don't downgrade quality. The shipped files average about 106 kbps, which is very low. Static text is cheap, but motion with CRF 20 should be inspected. Instagram's second encode on top of an already-starved encode makes thin Hangul strokes blur. Consider `-crf 16-18`, `-preset slow`, and `-profile:v high -pix_fmt yuv420p`, with `-g 60`; the files stay under 1-2 MB, still trivial.
- Silent track: the current AAC silent track is fine and keeps the file uploadable. When BGM arrives, mono/stereo 44.1 versus 48 kHz is irrelevant to Instagram acceptance [UNVERIFIED]; use 48 kHz stereo to be conventional.
- Hashtags: Instagram announced a cap of **5 hashtags per post/Reel** in Dec 2025 (rollout and enforcement details differ by source: a hard composer limit or just a recommendation) [CORROBORATED]. A hashtag generator that emits 15-30 tags (older best-practice) will be wrong. Generate 3-5, with the Korean topical tags first. Caption-length limit not verified in this session [UNVERIFIED, commonly cited 2,200 characters].

**How to avoid:**
Keep all platform numbers in one `platform.json` with `verified_on` and source, with a human re-check date, and avoid asserting limits in code except sanity bounds (duration 3-90 s here). Run the one irreducible check manually: upload the first new-format reel as a private test or draft, and look at the real preview (safe zones, cover crop, audio attribution).

**Warning signs:**
The hashtag generator returns more than 5 tags. Prose in docs quotes "Instagram requires X" with no source.

**Phase to address:**
Phase 2 (caption/hashtag generator) and Phase 1 (post-render ffprobe validation).

---

### Pitfall 13: BGM: copyright, business-account restrictions, loudness, and "royalty-free" that isn't

**What goes wrong:**
- **User-supplied file has unknown license.** "Free" downloads, YouTube audio library items with attribution requirements, Pixabay/Uppbeat tier limits, tracks that later receive Content ID or Meta Rights Manager claims (the reel is muted or taken down). Korean-specific: music rights bodies such as KOMCA and 연예제작자협회 manage compositions or masters, and "저작권 free" labels in Korean blogs are not licenses [UNVERIFIED].
- **Business accounts** reportedly get only Meta's smaller "Sound Collection" (about 14,000 tracks cleared for commercial use) instead of the full library, and music in the standard library is licensed for personal non-commercial use. Whether a Creator account is treated as commercial is disputed [CORROBORATED by vendors and blogs, no official Meta document reached]. Therefore, "adding the trending sound in-app" is also a risk for @kiwoom.mentor, which does CTA-to-consultation promotion. Burning a file into the MP4 avoids Meta's library but doesn't solve licensing.
- **Loudness:** the BGM covers the (nonexistent) voice, but is too loud on phones in a quiet setting, or clips. Reels are mostly watched muted, so BGM is optional polish and must not create a new compliance surface.
- **Provenance lost:** nobody remembers the track's source three months later.

**How to avoid:**
- BGM stays **opt-in by explicit spec field**: `"bgm": {"file": "...", "license_note": "<source URL / license ID / purchase receipt>", "licensor": "...", "commercial_ok": true, "attribution_text": ""}`. The renderer **refuses** to mix a file whose `license_note` is empty, and writes the license block into the review sheet and the caption (attribution if the license requires it).
- Store BGM files **outside git** (or in a `bgm/` folder with sidecar license text) to avoid redistributing licensed audio in a public repository. The repo is public-facing content ("공개용"), so committing a licensed track can itself be a license breach.
- Fixed gain (for example -18 to -20 dB relative to full scale, `volume=` or `loudnorm` single-pass for known short music) and a 1.5 s fade-out, with an `astats`/`volumedetect` post-check against clipping. No auto-download or auto-search of music (already out of scope), and no "royalty-free" claims in generated copy.
- Document the decision that the in-app music alternative is also reviewed against the account type.

**Warning signs:**
A `bgm` field with a path but no `license_note`. Audio file committed in `2026/`. Reel got "audio muted" notice after upload.

**Phase to address:**
Phase 5 (BGM option); the license-field requirement is part of its acceptance criteria.

---

### Pitfall 14: Human review is skipped in practice (automation makes it a rubber stamp)

**What goes wrong:**
The core value is "10 minutes to a reviewable bundle", so pressure pushes toward "review = glance at the MP4". Failure modes: reviewers watch the video but never read the caption/hashtags (where 단정 words and untagged claims hide); the check sheet is long, so it is not read; bundle files look final (named like published ones, saved into `2026/reels/`), so the next person publishes them; no record of who reviewed what; an LLM edit after review silently changes the text (the sheet is stale).

**How to avoid:**
- Bundle goes to a **draft folder** (for example `drafts/<date>-<slug>/`, not `2026/reels/`), and moving it into `2026/reels/` is the human "approve" action (`approve` command writes `review.json` with reviewer, date, and a hash of spec + caption). Publishing (a git-tracked path) can then be checked against the hash: if spec changed after approval, the status is invalid.
- A **one-screen review sheet**, ordered by risk: (1) flagged expressions, (2) numbers + registry sources + as-of dates, (3) disclosures present/absent, (4) safe-zone preview image, (5) caption + hashtags, (6) BGM license. It is a short list the reviewer ticks off, not a report.
- Optionally watermark draft renders ("DRAFT - 검수 전"). Trade-off: this adds a second render path that must stay identical to the final one, so prefer a watermarked preview image or contact sheet and keep the MP4 itself clean.
- No auto-post (already out of scope). Keep it so.

**Warning signs:**
Reviewer never changes anything for 5 consecutive reels. A `review.json` hash mismatch. Caption text edited in Instagram app but not in repo.

**Phase to address:**
Phase 3 (review sheet and approval workflow); folder convention in Phase 1.

---

## Moderate Pitfalls

### Pitfall 15: Caption and hashtag drafts that carry their own compliance risk
**What goes wrong:** Captions are the least-reviewed text but are read by everyone: hashtags like #원금보장 #확정수익 #무조건 or specific product tags; the caption restating a number without the basis; emoji-heavy hype; "댓글에 남기면 상담" promotion, comparison hashtags naming competitors.
**Prevention:** Run the same checks (layers 1-3, Pitfall 4) on caption and hashtags; keep a **hashtag allowlist** (topic tags like #연금저축 #세액공제 #노후준비 #재테크기초) and a blocklist; ≤ 5 tags (Pitfall 12); caption footer from `compliance.json` (Pitfall 5); caption repeats the `basis` and "예시이며 개인별로 다를 수 있음" style note (wording to be set by the compliance owner).
**Phase:** 2-3.

### Pitfall 16: Card-news → reel conversion mismatches
**What goes wrong:** Converting a 6-card spec to 7 scenes by mechanical splitting leads to dropped caveats (the "단, 꼭 알아둘 것" card) or numbers detached from their basis; the same figure phrased differently in card vs. reel (a rate mismatch between channels); the reel and card published on different days after a law/number changes.
**Prevention:** Conversion maps each card's `basis` and caveat into a required scene or the basis line (validator: every source number appears in the output with the same registry ID); never summarise away a caveat; list "dropped content" in the review sheet.
**Phase:** 2.

### Pitfall 17: Output file size and repo growth
**What goes wrong:** Today 12 MP4s total 2.8 MB, repo about 7 MB. The risks are not the final MP4s (a motion reel at CRF 18 is likely 1-3 MB [UNVERIFIED estimate]) but: committing intermediate frame directories or draft/preview renders; re-rendering a reel after each tweak and committing each version (git keeps every binary blob); embedding BGM audio and font files. Non-determinism (x264 threading, timestamps) means identical inputs yield different bytes, so a "no-op" re-render shows as modified.
**Prevention:** `.gitignore` for scratch/draft output; commit only the approved MP4, cover PNG and spec; use `-fflags +bitexitexact`/`-map_metadata -1` and `-threads 1` for byte-reproducible output if re-render diffs matter [UNVERIFIED]; optionally mark MP4/PNG as `-diff` in `.gitattributes`; consider Git LFS only if count passes dozens (not needed at the current scale). Keep fonts subset and small.
**Phase:** 1 (gitignore and conventions), 4-5.

### Pitfall 18: Cloud-session ephemerality loses state
**What goes wrong:** The container is ephemeral. Anything not committed or in the response is lost: figures registry updates, red-team cases, fonts, license notes, installed Python packages (Playwright needs re-installing every session, Pitfall 2). Network restrictions block the very sources needed for verification (law.go.kr, nts.go.kr, Meta docs were all unreachable in this session), so the model **cannot self-verify** tax figures and will fall back to memory without saying so.
**Prevention:** Put everything the pipeline needs in the repo (fonts, requirements, registry, rule files). Have the skill state explicitly "법령·수치 출처는 이 세션에서 확인 불가 → registry 값만 사용, 신규 수치는 사람이 확인". Ask the owner to allow the key official domains if verification inside the session is desired, otherwise the human verifies outside.
**Phase:** 0-2.

### Pitfall 19: LLM prompt-injection or contamination from source material
**What goes wrong:** Card-news spec or a pasted article/topic text containing instructions or marketing superlatives gets echoed into the script; web-fetched tax pages are treated as authority. (Lower risk here because input is mostly the owner's own text, but "topic one-liner" may pull from web search.)
**Prevention:** Treat fetched content as data; only the registry can introduce numbers; the validator rejects any script number not in the registry or the user's input.
**Phase:** 2.

---

## Minor Pitfalls

### Pitfall 20: `wait_for_timeout(60)` instead of real readiness
**What goes wrong:** Fixed 60 ms wait after `set_content` may screenshot before font load on a cold or slow container, giving a frame in the fallback font mid-render.
**Prevention:** `await document.fonts.ready` plus `requestAnimationFrame` double-tick before capture.

### Pitfall 21: Untagged color, no `-pix_fmt` on the screenshot path
**What goes wrong:** See Pitfall 8, color tags. Minor visual shift; consider testing against the PNG.
**Prevention:** Tag BT.709 and compare mean color of a flat region before/after on a phone.

### Pitfall 22: Absolute-path and naming collisions
**What goes wrong:** Slug collisions (`salary-two-owners-1` vs. a re-run), date in filename vs. the actual publish date drifting when schedules move; the cover is named `2026-10-19-savings-interest-cover.png` but no cover for others, so the convention for covers is unclear.
**Prevention:** One `naming.py` function, and refuse overwrite. Document the cover naming rule.

### Pitfall 23: `<g>`/`<s>` markup injection from LLM output
**What goes wrong:** The renderer does string `.replace` on raw HTML, so an `&`, `<`, or `>` in an LLM line (e.g., "A < B", "세금 & 수수료", an unclosed `<g>`) breaks the layout or injects markup.
**Prevention:** Escape text first, then convert the whitelist tags; validator for balanced tags; reject other HTML.

### Pitfall 24: Number formatting inconsistency
**What goes wrong:** "16.5만", "16만 5천 원", "165,000원" mixed; ranges and units (만 원/억) vary between reels; count-up animation shows intermediate invalid values (e.g., "13.2" while counting up to "13.2만" reads like a rate).
**Prevention:** One formatter; for count-up, animate only the numeral and end exactly on the registry value; the count-up must land before the line's hold so the final frame is the cited number; avoid count-up on figures that are statutory limits or rates (a rapidly changing "tax rate" is misleading). Use it only on illustrative amounts labelled as 예시.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Let the LLM write `basis` free-text | Fast drafts | Hallucinated or stale sources look authoritative | Never (use registry IDs) |
| Keyword-only compliance check | 30 min to build | False confidence, alert fatigue | Only as layer 1, with the red-team corpus and no PASS state |
| Hard-code Chromium path `chromium-1243` | Works today | Breaks on next container image | Never; glob or env var with fallback |
| `set_content` per frame at 30 fps | Minimal code change | Minutes of render time, temp-disk growth | Prototype only; use hold-frame reuse |
| Overwrite output in `2026/reels/` | One less flag | Clobbers published, golden artifacts | Never |
| Skip golden-corpus regression test | Faster Phase 1 | Every later change risks the 10 shipped looks | Never |
| Keep `LINE=0.85` non-integer frames | No behavior change for legacy | Frame jitter and cover misalignment with motion | Acceptable in legacy mode only |
| Commit BGM files to the public repo | Reproducible | License breach, repo bloat | Never unless license permits redistribution (documented) |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Playwright/Chromium (cloud) | Unpinned `pip install playwright`, expects auto-downloaded browser | Pin to the preinstalled build or pass `executable_path`; selftest at session start |
| ffmpeg | Assume `drawtext` with a Korean font "just works" | Provide `fontfile=` explicitly; test Hangul; prefer rendering text in Chromium |
| ffmpeg concat demuxer | Mixing many short sequences and long holds in one list; ignoring last-duration quirk | Integer-frame timeline; relist last file; verify with ffprobe |
| Instagram (manual upload) | Trust blog specs; skip a real preview | `platform.json` with sources; one private test upload per format change |
| Instagram hashtags | Generate 15-30 tags | ≤ 5 tags (per Dec 2025 announcement; check current behavior) |
| Music source | "Royalty-free" label as the license | Require `license_note` with source URL/receipt; refuse otherwise |
| law.go.kr / nts.go.kr | Assume reachable from the session | Not reachable here; human-verified registry with source URLs |
| `compliance-review` skill | Treat its verdict as clearance | Feed as one input; human still decides |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Screenshot every frame | ~0.14 s/frame measured; 750 frames ≈ 105 s + overhead | Render distinct frames only; reuse holds; single page | Reels > 30 s, batch of 10, repeated re-renders |
| 4K or `deviceScaleFactor` 2 "for crispness" | 4× pixel cost, huge temp files | Stay 1080×1920 DPR 1 | Any time |
| Temp dir never cleaned | `/tmp` fills across runs | `try/finally` cleanup or a managed scratch dir | After several renders in one session |
| Unbounded LLM-rewrite loop on overflow | Long, expensive sessions | Cap at 2-3 retries, then flag for a human | Any batch |
| Fresh browser launch per reel | +1-2 s each | Reuse one browser across a batch | Batch mode |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Customer names, cases or consultation notes pasted as "topic" | 개인정보 in a public repo | Input validator warns on name/phone/account patterns; skill says "공개용만"; never commit drafts containing them |
| Committing licensed audio or fonts without checking the license | License breach in a public repo | Sidecar license files; OFL fonts only |
| Auto-publish or API tokens in the repo | Unreviewed financial content goes live | Keep out of scope; no tokens in the repo |
| Fetched web text treated as instructions | Prompt injection into scripts | Treat as data; numbers from the registry only |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Review sheet is long and flat | Gets skipped | One screen, risk-ordered, tick list |
| Draft and published files look identical | Wrong file posted | Draft folder + approve step |
| Motion on every line | Harder to read quickly; looks off-brand | Motion budget; none on disclosures/CTA |
| Count-up on statutory limits/rates | Misread as changing value | Count-up on illustrative amounts only |
| Text in unsafe zones | Hidden under caption or buttons | Safe-zone constants plus a preview overlay |
| Fast scene changes with long Korean lines | Unreadable in under 1 s | Reading-speed check (≥ ~0.1 s per character is a starting guess [UNVERIFIED]; existing lines are 0.85 s) |

## "Looks Done But Isn't" Checklist

- [ ] **Font:** the rendered frame uses the brand font. Verify `document.fonts.check` and a first-frame diff vs. an existing reel.
- [ ] **Legacy specs:** all 10 re-render with the same duration, scene boundaries and `cover_ms`. Verify via the golden corpus.
- [ ] **Figures:** every number has a registry ID, source URL, as-of date within the freshness window. Verify in the review sheet.
- [ ] **Proposed vs. in force:** any 개정안/발의 figure is labeled as not final. Verify by grep for the registry status.
- [ ] **Checklist honesty:** the sheet never says "통과/PASS/OK"; has the dated rule version and the human-review statement.
- [ ] **Disclosures:** 필수 고지 text (from `compliance.json`) present in the final scene and caption; owner confirmed requirements.
- [ ] **Safe zones:** basis line and CTA outside the bottom UI zone; cover title within the 3:4 grid crop. Verify with the overlay and one private upload.
- [ ] **Encode:** `ffprobe` says h264 / yuv420p / 1080×1920 / 30 fps / aac, and the duration matches the plan within 0.1 s, with BT.709 tags.
- [ ] **BGM:** license note present, gain and fade applied, not committed to git, no clipping.
- [ ] **Hashtags:** ≤ 5, no banned or product tags.
- [ ] **Draft vs. publish:** drafts not in `2026/reels/`; approval record exists with a matching hash.
- [ ] **Container reproducibility:** a fresh session runs the selftest and the full bundle with no manual steps.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong font shipped in a published reel | MEDIUM | Re-render with the vendored font; re-upload (Instagram cannot replace the video, so delete and repost, losing engagement) |
| Stale or wrong tax figure published | HIGH | Take down or pin a correction; fix the registry; audit other reels using the same fact ID (the registry makes this a query) |
| Prohibited wording published | HIGH | Take down, notify the compliance owner, add the sentence to the red-team corpus, widen the rule |
| Golden regression discovered late | MEDIUM | `git checkout` old renderer; bisect with the corpus; add a legacy-mode flag |
| BGM claim or mute after upload | MEDIUM | Swap audio (re-edit in-app or repost with another licensed track); record the licensor mistake |
| Overwritten published MP4 in git | LOW | `git checkout -- file` (the old blob is in history) |

## Pitfall-to-Phase Mapping

Suggested phase ordering (from the milestone scope): P0 owner decisions, P1 renderer hardening + golden corpus, P2 script/caption generation, P3 review sheet and compliance, P4 subtitle motion, P5 BGM.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1 Font fallback | P1 | Font check passes; golden first-frame diff within tolerance |
| 2 Playwright/Chromium mismatch | P1 | Selftest passes in a fresh session |
| 3 Stale/hallucinated figures | P2 (registry, calc), P3 (freshness gate) | Every number in 3 test reels traces to a registry ID; calc tests reproduce the 10 specs' numbers |
| 4 Keyword checklist false confidence | P3 | Red-team corpus recall reported; no PASS string anywhere in the output |
| 5 Ad status and 필수 고지 | P0, P3 | Written owner/준법 answer; `compliance.json` rendered in a sample bundle |
| 6 Breaking existing specs | P1 (before P4) | All 10 specs pass the golden corpus in legacy mode |
| 7 Safe zones and grid crop | P1 constants, P4 motion | Overlay image reviewed; one private upload preview |
| 8 Brand drift | P2, P4 | Structural validator on generated specs; motion preset reviewed side by side with the old reels |
| 9 Overflow/wrapping | P1, P2 | Renderer fails on a deliberately long line; generator loop shortens it |
| 10 Render blowup | P4 | Per-reel render time recorded, under budget; temp dir cleaned |
| 11 Timing drift, audio length | P4, P5 | ffprobe checks pass; video and audio duration equal within 50 ms |
| 12 Spec folklore, hashtag count | P1, P2 | `platform.json` with sources; ≤ 5 tags enforced |
| 13 BGM license and loudness | P5 | Refuses empty `license_note`; no audio in git; clipping check |
| 14 Review skipped | P3 | Approve step writes a hash; changing the spec invalidates it |
| 15-16 Caption risk, card→reel | P2-P3 | Same checker on captions; dropped-content list in the sheet |
| 17 Repo growth | P1 | `.gitignore` in place; repo size delta per reel tracked |
| 18 Ephemeral container | P0-P2 | Fresh-session end-to-end run documented |

## Sources

Local, tested in this container on 2026-10-28 (HIGH):
- `/home/user/kiwoom-cards/tools/reel.py` read in full (font-family, layout constants, concat/encode command).
- `fc-list`/`fc-match` output (no Noto CJK; Inter and WenQuanYi fallback); Playwright 1.64.1 install and launch failure (expected build 1248, installed 1243); screenshot timing probe (about 0.137 s PNG, 0.113 s JPEG, Chrome 153, ffmpeg 6.1.1 with xfade/drawtext/zoompan); `ffprobe` on shipped reels (h264 High, yuv420p, 30 fps, AAC 44.1 kHz stereo, color space unknown, about 106 kbps total); the 10 specs in `2026/reels/specs/`.

Web search summaries (secondary, MEDIUM unless noted; primary sources unreachable from this session):
- Reel size and safe zones: [Hopper HQ](https://www.hopperhq.com/blog/instagram-reel-size/), [House of Marketers](https://www.houseofmarketers.com/guide-to-safe-zones-tiktok-facebook-instagram-stories), [First Pier](https://www.firstpier.com/resources/instagram-ad-safe-zones). Pixel numbers [CONFLICTING].
- 3:4 grid and cover crop: [Planoly](https://planoly.com/blog/guide-to-instagrams-new-vertical-grid), [Hopper help article](https://help.hopperhq.com/en/articles/10907941-instagram-s-vertical-grid), [Oktopost](https://www.oktopost.com/blog/instagram-grid-size-guide/). Exact crop numbers differ; check the "Edit cover" preview.
- Reels length, size and codec: [Adaptlypost quoting Meta reference](https://adaptlypost.com/blog/instagram-reels-api-max-length-file-size), [Postpone](https://help.postpone.app/platforms/instagram/media-limits), [Instagram Help: Reels resolution and size](https://help.instagram.com/1038071743007909) (listed in results, not fetched). Length and size [CONFLICTING].
- Hashtag cap of 5: [BetaNews 2025-12-19](https://betanews.com/2025/12/19/instagram-puts-a-limit-on-hashtag-usage/), [Social Media Today](https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/). Rollout and enforcement details vary.
- Music licensing for business accounts: [Foxi Music guide](https://www.foximusic.com/blog/instagram-reels-music-copyright-legal-guide/), [Osborne Clarke](https://www.osborneclarke.com/insights/use-music-social-media-platforms-what-businesses-and-creators-need-know-about-usage), [Soundstripe](https://www.soundstripe.com/instagram). Vendor-influenced, no official Meta text reached.
- 금소법 광고 and 부당권유: [Citibank Korea 금소법 안내문](https://open.citibank.co.kr/download/cms/notice/210325_notice_customer.pdf) (단정적 판단 provision summary), [FSC press releases](https://www.fsc.go.kr/edu/news/84957), [KOFIA 광고심의 page](https://www.kofia.or.kr/wpge/m_169/sub04070103.do), [Herald 2025-12-14 on 금감원 오인광고 guidance](https://www.heraldk.com/article/2025121422234855840), [Maeil 2026-04-23 on 금감원/금투협 광고 TF](https://www.imaeil.com/page/view/2026042314511296562). The statute text of 제21조, 제22조 and its 시행령 was **not** retrieved; confirm at law.go.kr.
- 연금저축/IRP 세액공제: [국가법령정보센터 소득세법 search result](https://law.go.kr/lsLinkCommonInfo.do?ancYnChk=&chrClsCd=&lsJoLnkSeq=1021863203), [국세청 근로소득 연금계좌 세액공제](https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7875), [Korea.kr policy news](https://www.korea.kr/news/policyNewsView.do?newsId=148910222) (all surfaced by search, none fetchable here), plus blog posts on wikidocs.net. 600만/900만 and 15%/12% (16.5%/13.2% incl. 지방세) are [CORROBORATED] only. Bill status for the IRP 15%/17% proposal [UNVERIFIED].

Domain knowledge, not verified in this session (LOW): ffmpeg concat last-duration behavior, BT.601/BT.709 default conversion, x264 non-determinism, KOMCA/Content ID behavior for "free" music.

---
*Pitfalls research for: Korean financial-education Instagram Reels automation (LLM drafts + compliance sheet + subtitle motion/BGM on Python/Playwright/ffmpeg)*
*Researched: 2026-10-28*
