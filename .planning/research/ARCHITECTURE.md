# Architecture Patterns

**Domain:** Automated subtitle-style Instagram Reels production (Korean financial education content, human-reviewed draft bundles)
**Researched:** 2026-10-28
**Overall confidence:** HIGH for boundaries and data flow (derived from the actual code and the 10 specs). MEDIUM for motion-rendering performance (measured only 120 ms per full-frame screenshot in the research sandbox, which has no Korean font). MEDIUM for Instagram platform rules (secondary sources).

## What the existing code tells us (facts the design is built on)

| Fact | Evidence | Consequence |
|------|----------|-------------|
| Reel spec v1 is exactly `{basis, scenes:[{top, lines[]}]}`; inline markup is only `<g>` and `<s>`. All 10 specs use no other keys, always 7 scenes, 1-4 lines per scene, last scene is the CTA with 4 lines. | Scan of `2026/reels/specs/*.json` | v1 is a very small, regular contract. It can be accepted forever by an in-memory normalizer with no migration of files. |
| Rendering is "one PNG per reveal step, held via ffmpeg concat durations". Pacing constants `LINE=0.85`, `HOLD=1.9` are module globals, and the progress bar width comes from cumulative time. | `tools/reel.py` | There is no timeline object. Cover time, duration, progress bar and frames are all computed inline. Motion cannot be added cleanly until a timeline exists. |
| `cover_ms` is printed, but nothing extracts a cover. The only cover PNG (`2026-10-19-savings-interest-cover.png`) was made by hand. | `reel.py` line 38, `ls 2026/reels` | A cover step is a new component, not a change. |
| `reel.py` has no overflow or wrap check. `cards.py` has one (`OVERFLOW`). At 100 px with -0.03em tracking, a 888 px content width holds about 9 Hangul glyphs per line, so some existing lines probably wrap. | `reel.py` CSS, `cards.py` line 30 | A layout check belongs in the renderer. It is the cheapest deterministic quality gate available. |
| Card specs are `{series, cards:[{title(with <br>), lines[], emph[], note, dark?}]}`. Only `02`-`08` have `spec.json`; `01-net-worth` has none. Card lines are long sentences, reel lines are short fragments. | `2026/02-tax-deduction/spec.json`, `ls 2026/*/` | A card-to-reel converter can carry facts, provenance and scaffolding. It cannot do the condensing, because that needs judgment. |
| Directory naming in `tools/README.md` (`2026/<date>-<slug>/`) differs from the real layout (`2026/<NN>-<slug>/`). | README vs `ls 2026` | Write the real convention into the skill. Do not rely on the README. |
| In the research sandbox, `pw.chromium.launch()` fails (Playwright 1.64 expects another Chromium revision). Launching with `executable_path="/opt/pw-browsers/chromium"` works. The SessionStart hook already exports `AGENT_BROWSER_EXECUTABLE_PATH` for that binary. The sandbox also has no Noto Sans CJK KR font. | Run during this research | Add a `doctor` preflight (browser launch, Korean font, ffmpeg). Make the renderer pick `executable_path` from the environment when set. |

## Recommended Architecture

Principle: **Claude authors exactly two creative inputs (reel spec, caption). Everything else is deterministic Python invoked through one command.** The skill is thin orchestration plus judgment. All rules and all rendering live in testable code under `tools/`.

```
                    CREATIVE (Claude, in session)                    DETERMINISTIC (tools/reelkit)
                    ---------------------------------                --------------------------------------
 topic line  ─┐
              ├─► [Skill: make-reel] ─► drafts/<date>-<slug>/reel.json ──► spec.py  normalize + validate (v1|v2 → canonical)
 card spec ──►│        ▲                   (Claude-authored)                    │
   │          │        │                                                         ▼
   └─► convert.py ─────┘ (skeleton + provenance)                           lint.py  text rules → lint.json   ◄── rules/*.json
                                                                                  │
              Claude: compliance review of plain text + lint.json                 ▼
              writes review-claude.md  (stale if reel.json hash changed)    timeline.py  spec → timed events (single source of truth)
                                                                                  │
 Claude writes caption.json ─────────────────────────────────────────────►  caption.py  assemble + footer + hashtag pool + lint
                                                                                  │
                                                                                  ▼
                                                                            render.py  layout (HTML) + motion (seek) + layout check
                                                                                  │  frames
                                                                                  ▼
                                                                            encode.py  ffmpeg concat → reel.mp4 (+ optional audio)
                                                                            cover.py   settled still → cover.png ; contact.png
                                                                                  │
                                                                                  ▼
                                                                            bundle.py  REVIEW.md + manifest.json (hashes, status)
                                                                                  │
                                              human reviews drafts/<date>-<slug>/ ─┴─► promote → canonical paths
```

### Component Boundaries

| Component | Path | Responsibility | Inputs → Outputs | Talks to | Must NOT |
|-----------|------|---------------|------------------|----------|----------|
| Skill `make-reel` | `.claude/skills/make-reel/SKILL.md` (+ `references/`) | Intake (topic or card spec), derive date and slug, write `reel.json` and `caption.json`, run `reelkit build`, run compliance review, report bundle summary | user request → draft folder | `reelkit` CLI, `compliance-review` skill (if present), Read tool for `cover.png` and `contact.png` | Contain rules, timings, or colors. It points at code and data files. |
| `reelkit` CLI | `tools/reelkit.py` (thin dispatcher; subcommands `doctor`, `validate`, `lint`, `convert`, `build`, `promote`) | Single stable entry point so the skill never composes ad-hoc python | argv → exit code + JSON on stdout | all modules below | Hold logic |
| `spec` (schema) | `tools/reelkit/spec.py` | Detect version, upgrade v1 → canonical v2 **in memory**, validate, strip markup (`plain_text()`), tag parser shared by all consumers | json file → canonical dict | used by every other module | Rewrite spec files on disk |
| `timeline` | `tools/reelkit/timeline.py` | Compile canonical spec into timed events: scene start/end, per-line reveal, hold, transition windows, count-up windows, cover time, total duration, progress fraction | canonical spec → `Timeline` | `render`, `cover`, `lint` (reading speed), `bundle` (duration) | Touch the browser |
| `render` (layout + motion) | `tools/reelkit/render.py`, `layout.py`, `motion.py` | Build page HTML (identical to today's `frame()` for motion=none), seek the page to time `t`, screenshot, emit layout warnings (wrap count, overflow, safe-area) | `Timeline` → frame PNG list + `layout.json` | Playwright | Know about ffmpeg or captions |
| `encode` | `tools/reelkit/encode.py` | Frame list + durations → MP4 via concat; optional audio mix; ffprobe duration check against the timeline | frames → `reel.mp4` | ffmpeg/ffprobe | Decide pacing |
| `cover` | `tools/reelkit/cover.py` | Choose the cover scene (default: hook scene, fully revealed, motion settled, no progress bar), render still, check the central 3:4 safe area; build `contact.png` (tiled frames for quick visual review) | `Timeline` → `cover.png`, `contact.png` | `render` | Seek into the MP4 by `cover_ms` |
| `convert` | `tools/reelkit/convert.py` | Card spec → **skeleton** reel spec: title → hook scene, `emph` → `<g>`, `note` → `basis` / `<s>` caveat, dark last card → standard CTA scene, `meta.source_card`, per-scene `src` card index, flag lines too long for one reel line | card spec → `reel.json` draft | `spec` | Pretend to condense. Claude rewrites the skeleton. |
| `lint` | `tools/reelkit/lint.py` + `tools/reelkit/rules/compliance_ko.json` | Deterministic checks over plain text of reel + caption + basis (see Compliance section) | canonical spec + caption → `lint.json` (findings with id, severity, where, matched text, suggestion) | `spec` | Decide pass/fail on judgment cases. It flags, Claude and the human judge. |
| `caption` | `tools/reelkit/caption.py` + `tools/data/hashtags.json` | Assemble `caption.txt` from Claude's `caption.json` plus mandatory footer (education-only disclaimer, CTA line); validate hashtags against pool, banned list and count cap; lint the result | `caption.json` → `caption.txt` | `lint` | Write creative copy |
| `bundle` | `tools/reelkit/bundle.py` | Run the pipeline in order, write `REVIEW.md` and `manifest.json`, compute overall status (`ready-for-review` / `needs-fix`), `promote` copies approved files to canonical paths | draft folder → bundle | all | Auto-publish or auto-approve |
| Legacy shims | `tools/reel.py`, `tools/cards.py` | Keep `python3 tools/reel.py spec.json out.mp4` working unchanged (prints `duration=... cover_ms=...`), delegating to `reelkit` | argv | `reelkit` | Gain new flags that diverge from `reelkit` |

Dependency direction (no cycles): `spec` ← `timeline` ← `render` ← `encode`/`cover` ← `bundle` ← `reelkit` ← skill. `lint` and `caption` depend only on `spec`. `convert` depends only on `spec`.

Keep it stdlib plus Playwright plus ffmpeg. The project forbids paid services and no `jsonschema` is guaranteed, so validation is hand-written.

### Data Flow

1. **Intake (Claude).** Topic line: Claude reads two or three reference specs (see Skill section), writes `drafts/<date>-<slug>/reel.json`. Card spec: `reelkit convert <card spec>` writes a skeleton, Claude condenses it in place. Date and slug are derived by Claude (slug lower-case English, kebab-case; date asked or inferred from the series cadence).
2. **Fast text loop (cheap, before any render).** `reelkit validate` then `reelkit lint`. Claude fixes `block` findings and addresses `warn` findings. Claude then runs the compliance review over plain text and writes `review-claude.md`.
3. **Caption.** Claude writes `caption.json` (`hook`, `body[]`, `hashtags[]`). `reelkit caption` assembles `caption.txt` and lints it.
4. **Build (slow, once).** `reelkit build <draft dir>` runs: validate → lint (re-run as gate) → timeline → render frames → encode → cover → contact sheet → layout report → bundle files. About 30-60 s with motion (estimate in Scalability).
5. **Visual self-check (Claude).** Claude reads `cover.png`, `contact.png`, `layout.json` and fixes wraps or overflow by editing `reel.json` and re-running build. Cap at two automatic fix iterations, then hand to the human with the open issues listed.
6. **Human gate.** The human opens `REVIEW.md`, watches `reel.mp4`, ticks the checklist.
7. **Promote.** `reelkit promote <draft dir>` copies to canonical locations. It refuses if `manifest.status != ready-for-review` or if the reel spec changed after the last build (hash mismatch).

Direction is strictly one-way: spec → timeline → frames → video, and spec + caption → lint → review. Rendered artifacts are never read back to make decisions, except `layout.json` (measured in the browser) and the images Claude looks at.

## File Layout

```
tools/
  reel.py                 # shim, CLI unchanged
  cards.py                # unchanged
  reelkit.py              # dispatcher
  reelkit/
    spec.py  timeline.py  render.py  layout.py  motion.py  encode.py
    cover.py convert.py   lint.py    caption.py bundle.py
    rules/compliance_ko.json      # lint rules as data
    rules/review_rubric_ko.md     # fallback rubric if compliance-review skill is unavailable
  data/
    hashtags.json         # curated pools: brand (fixed), topics, banned
    caption_footer.txt    # mandatory disclaimer + CTA line
  tests/                  # golden + unit tests (see Build Order)
  README.md               # update: real folder naming, new commands
.claude/skills/make-reel/
  SKILL.md                # workflow only
  references/
    scene-patterns.md     # hook → analogy → numbers → conclusion → caution → CTA, with excerpts from 3 specs
    voice.md              # tone, forbidden phrasing, how to write basis
    spec-schema.md        # human-readable v1/v2 schema
    caption-template.md
2026/reels/
  <date>-<slug>.mp4               # canonical (existing convention, unchanged)
  <date>-<slug>-cover.png         # canonical (existing hand-made cover naming, now generated)
  specs/<date>-<slug>.json        # canonical (existing)
  captions/<date>-<slug>.txt      # NEW canonical, for later reference
  drafts/<date>-<slug>/           # NEW staging area = the review bundle
    reel.json  caption.json  review-claude.md      # inputs (Claude-authored)
    reel.mp4   cover.png     contact.png           # rendered
    caption.txt lint.json    layout.json           # derived
    REVIEW.md  manifest.json                       # review surface + provenance
```

**Why a `drafts/` staging folder instead of writing straight to canonical paths:** the repo is public-facing content, and the project rule is that nothing is publishable without human review. Staging keeps unreviewed output out of the folders that count as published, and `promote` becomes an explicit human-triggered step. It also lets rebuilds overwrite freely. Decision to confirm with the user: whether `drafts/<...>` is committed or gitignored (recommend committed after promote, deleted or left as an audit trail, never auto-committed).

## Spec Schema Versioning

**Rule: additive, optional, explicit.** Never rewrite the 10 published specs; they are records.

- **v1 (implicit):** no `version` key. `{basis, scenes:[{top, lines}]}`.
- **v2:** `version: 2` plus optional fields. Everything v1 had keeps its meaning.

```json
{
  "version": 2,
  "basis": "100만 원 공제 예시 · 지방소득세 포함",
  "meta": {"slug": "tax-deduction", "date": "2026-10-26", "topic": "소득공제 vs 세액공제",
           "source_card": "2026/02-tax-deduction/spec.json", "as_of": "2026-10"},
  "motion": {"preset": "rise", "transition": "fade"},
  "audio": {"file": "assets/audio/x.mp3", "license_note": "...", "volume": 0.25},
  "scenes": [
    {"top": "비유하면", "lines": ["소득공제는", "<g>가격표 깎기</g>"],
     "src": 1, "hold": 1.9, "cover": false}
  ]
}
```

- `spec.normalize()` maps v1 to canonical v2 with `motion.preset = "none"` and global default pacing (0.85 / 1.9). This is what guarantees old specs re-render exactly as today. New specs written by the skill set `motion` explicitly; the *renderer* default stays `none`. Explicit beats implicit, so a future default change cannot silently alter old videos.
- Unknown keys: warn, do not fail (forward compatibility). Unknown `version` greater than supported: fail with a clear message.
- Markup stays inside strings so v1 consumers and plain-text consumers (lint, caption, review) need no schema knowledge: `<g>`, `<s>` (existing) plus `<n>` (count-up, new). `<n>38.5</n>만` means "animate the numeric part from 0, final text identical to the static text". `spec.plain_text()` strips all tags, so lint and the provenance check always see the final text.
- Do not add a separate `caption` block to the reel spec. Caption has a different lifecycle (different lint scope, different reviewer concerns) and lives in `caption.json`.
- Bump `version` only for a breaking change. Additive fields do not bump.

## Patterns to Follow

### Pattern 1: Timeline as single source of truth
**What:** One function compiles the spec into events with absolute times. Renderer, cover selection, progress bar, reading-speed lint and duration reporting all read it.
**When:** Always. It replaces `total`, `t` and the `cover_ms` formula scattered in `reel.py`.
**Example:**
```python
@dataclass
class Event:  # one per visible state change
    scene: int; line: int | None; kind: str   # "enter" | "hold" | "transition" | "count"
    t0: float; t1: float
class Timeline:
    events: list[Event]; total: float
    def settled_time(self, scene: int) -> float: ...   # for cover
```

### Pattern 2: Seekable page, not CSS-timed animation
**What:** Build the scene DOM once, expose `window.__seek(t)` that sets inline style (opacity, translateY, per-grapheme opacity, counter text) from pure motion functions of progress. The renderer calls `__seek` then `screenshot`. Motion presets are small JS functions in `motion.py` (string constants) with an eased progress parameter.
**When:** All motion (line entry, per-character stagger, transitions, count-up).
**Why:** Deterministic frames, no wall-clock timing, no `wait_for_timeout` guesses. Same output on every run.
**Cost control:** Render only frames inside motion windows at 30 fps; render each *hold* once and give it a duration through the existing concat mechanism. Estimated 250-350 animated frames per reel.

### Pattern 3: Lint rules as data, review as judgment
**What:** Rules live in `rules/compliance_ko.json` (id, regex, severity, scope, message, suggestion). The Python only loads and matches. Claude's compliance review is a separate, recorded step.
**When:** Compliance. Compliance reviewers can edit rules without touching code, and every finding is traceable.

### Pattern 4: Provenance and staleness via hashes
**What:** `manifest.json` stores sha256 of `reel.json`, `caption.json`, `review-claude.md`, the rules file, and the tool version at build time. `REVIEW.md` shows "Claude review STALE" if `reel.json` changed after it.
**When:** Every build. This is what keeps "reviewed" honest in an iterative edit loop.

### Pattern 5: Number provenance check
**What:** For reels from card specs, every numeric token in the reel plain text should appear in the source card spec text (or in `basis`). Unmatched numbers become `warn` findings: "number not in source".
**When:** Card-sourced reels. It catches invented or mis-rounded figures, the single most dangerous failure for finance content. For topic-sourced reels there is no source, so every number is flagged for human fact check (see Pitfalls note).

## Compliance Linter Design

Deterministic layer (`lint.py`, rules JSON), scopes: reel text (scene `top` and `lines`), `basis`, caption, hashtags.

| Rule family | Severity | Examples (keep list in JSON, not in code) |
|-------------|----------|------------------------------------------|
| Assertive / guarantee | block | 원금 보장, 확정 수익, 무조건, 100%, 손실 없, 반드시 (오른|받), 안전한 투자 |
| Tax/legal assertion | block or warn | 절세 100%, 무조건 절세, 세금 안 내, 합법이니, "~하면 됩니다" on tax outcomes without a "세무사 확인" caveat nearby |
| Superlative / comparison | warn | 최고, 1위, 가장, 타사 / named competitors, "~보다 낫다" |
| Solicitation | warn | 가입하세요, 지금 사, 특정 상품명 |
| Number without basis | warn | digits with %, 만 원, 억 and empty or non-matching `basis`; per-scene list for Claude to review |
| Tax figure without as-of | warn | 세율/공제/한도 words and no "기준" date in `basis` or `meta.as_of` |
| Required elements | block | `basis` non-empty; a caution scene or `<s>` containing "확인" when tax words appear; CTA scene present; caption contains the footer disclaimer |
| Personal info | block | phone/email patterns, name-like patterns near 고객/사례, real-case wording |
| Hashtags | warn | count over cap, banned tags (e.g., guarantee-style), tags not in pool flagged `new` |
| Readability (not compliance, same engine) | warn | line wraps more than 2 rows, chars-per-second over a threshold given `hold` (hold is a fixed 1.9 s today, so dense scenes may be unreadable) |

Claude layer: uses the user-level `compliance-review` skill when available. **Dependency risk:** that skill is user-level, so it may be absent in some sessions. The skill therefore falls back to `rules/review_rubric_ko.md`, a short rubric in the repo (personal info, assertive wording, explanation duty, comparison advertising). Output is `review-claude.md` with findings and proposed replacement wording.

Gate semantics: any `block` finding makes `manifest.status = needs-fix` and puts a red banner at the top of `REVIEW.md`. The bundle is still produced so the human can see it, but `promote` refuses. Findings are never silently waived; a waiver is a human edit in `REVIEW.md` recorded in the manifest.

## Bundle Review Surface (`REVIEW.md`)

Generated, human-facing, Korean, short. Sections in order: status banner; one-screen summary (topic, date, duration, scene count, source); links to `reel.mp4`, `cover.png`, `contact.png`; compliance findings table (block first) with suggested replacements; Claude review summary and staleness flag; caption preview with hashtag count; **manual checklist** the tool cannot decide: figures re-verified against current law/rates and `basis` correct, `as_of` date current, no 단정 phrasing in caption, cover legible in the grid crop, audio licence (if any), no customer data, safe to post. Checkboxes are unticked by default.

## Motion Layer Details

- Line entry presets: `none` (today's hard cut), `fade`, `rise` (translateY + opacity), `type` (per-grapheme stagger; use `Intl.Segmenter` and walk text nodes so `<g>`/`<s>` spans survive).
- Scene transitions: start with sequential out-then-in (fade or slide) inside one page. Overlapping crossfade needs two stage layers; defer unless it looks poor.
- Count-up: `<n>` span animates 0 → target with easing, formatting preserved (thousands separators, decimals, trailing units stay static). The span has a fixed width equal to the final text width so neighbouring text does not jitter. Final frame text must equal static text exactly (tested).
- Pacing: motion consumes time from the existing `LINE` slot, not extra time, so total duration of a v1-shaped spec stays comparable. Make `hold` per-scene overridable.
- Progress bar: becomes continuous (timeline fraction) when motion is on; stays stepped for `none`.
- Audio: `encode.py` replaces the `anullsrc` input with the user-supplied file (trim, fade-out, volume), only when `audio.file` exists on disk. The manifest records filename and `license_note`; `REVIEW.md` makes the licence a mandatory checkbox. Keep the silent track otherwise (current behavior).

## Anti-Patterns to Avoid

### Anti-Pattern 1: Logic in the SKILL.md
**What:** Putting pacing numbers, regex lists or ffmpeg commands in the skill prose.
**Why bad:** Unversioned, untestable, drifts from code, and Claude re-derives it each run.
**Instead:** Skill calls `reelkit` subcommands and reads reference files for style only.

### Anti-Pattern 2: Rewriting or migrating the 10 existing specs
**Why bad:** They are the record of what was published and the regression corpus.
**Instead:** In-memory normalization; golden render test against them.

### Anti-Pattern 3: Using `cover_ms` to grab a frame from the MP4
**Why bad:** Video frames are lossy, include the progress bar, and the number changes once motion exists.
**Instead:** Render the cover as a still from the same page at the settled time, with the bar hidden.

### Anti-Pattern 4: Treating regex lint as "compliant"
**Why bad:** Regex catches known phrases only. Finance reviewers still need to read it.
**Instead:** Present lint as "known risky patterns found / not found", never as approval. Wording in `REVIEW.md` must say so.

### Anti-Pattern 5: One monolithic `reel.py` that grows flags
**Why bad:** Motion, cover, caption and lint would all land in one 40-line-dense file that is already hard to test.
**Instead:** Module split above, with `reel.py` as a shim.

### Anti-Pattern 6: Time-based Playwright animation capture
**Why bad:** Non-deterministic frame timing, flaky in cloud sessions.
**Instead:** Pattern 2.

## Scalability Considerations

This is a single-operator tool, so "scale" means reels per day and session limits.

| Concern | One reel | A series of 5 in one session | Maintenance over a year |
|---------|----------|------------------------------|------------------------|
| Render time | Static: 30-45 screenshots, a few seconds. Motion: about 300 frames at about 0.12 s each (measured full-frame PNG in sandbox) is about 35-60 s. | Run builds sequentially; reuse one browser instance per `build` | Reuse a single `launch()` per command |
| Rule growth | Dozens of rules in JSON | Same | Add a rules test file with one positive and one negative example per rule so edits don't regress |
| Spec drift | v1 + v2 | Same | Golden test on all 10 specs on every change |
| Token cost per reel | Skill reads 3 reference specs + guidance | Do not re-read references per reel in a batch | Keep references short; link rather than inline |

## Suggested Build Order (with dependencies)

Priority from PROJECT.md: automation first, motion second. Motion hooks (timeline, seekable renderer interface) are part of the foundation so motion does not force a second refactor.

| # | Step | Depends on | Delivers | Verifiable by |
|---|------|-----------|----------|---------------|
| 0 | `doctor` preflight and renderer launch fix (`executable_path` from `AGENT_BROWSER_EXECUTABLE_PATH`, Korean font check, ffmpeg check) | none | Reliable cloud-session start | `reelkit doctor` exits 0 |
| 1 | `spec.py`: version detect, normalize, validate, markup parser, `plain_text()` | none | Contract for all consumers | All 10 specs load and normalize; unit tests |
| 2 | `timeline.py` | 1 | Single timing source; reproduces current durations and `cover_ms` | Equality test against `reel.py` output for all 10 specs |
| 3 | Refactor renderer into `layout/render/encode` with `motion=none` identical to today; `reel.py` becomes shim; add layout check | 1, 2 | No behavior change, plus wrap/overflow report | **Golden test**: frame hashes (or per-frame pixel diff) and duration equal old output on all 10 specs |
| 4 | `cover.py` and `contact.png` | 3 | Generated cover PNG, safe-area check | Visual check against the one existing hand-made cover |
| 5a | `lint.py` + `rules/compliance_ko.json` + rule tests | 1 (parallel with 2-4) | `lint.json` | Run on the 10 specs: expect few false positives; tune rules |
| 5b | `caption.py` + `hashtags.json` + footer | 1, 5a (parallel with 3-4) | `caption.txt` | Unit tests; lint covers caption |
| 6 | `convert.py` (card → reel skeleton + provenance + number check) | 1, 5a | Skeleton for the 7 card specs | Convert `02-tax-deduction`, compare scene shape against `2026-10-26-tax-deduction.json` |
| 7 | `bundle.py`: `build`, `REVIEW.md`, `manifest.json`, hashes, `promote` | 3, 4, 5a, 5b | One-command bundle | End-to-end run on an existing spec; promote refuses on `needs-fix` or stale hash |
| 8 | Skill `make-reel` + references | 7 (draft early, finalize last) | The one-request flow | Dry-run with a topic and with a card spec; time it against the 10-minute goal |
| **Milestone: automation complete** | | | | |
| 9 | Motion engine: seekable page, `fade`/`rise`, per-scene `hold`, continuous progress | 3 (timeline + renderer interface) | First visible upgrade | Compare against `none`; duration within tolerance |
| 10 | Count-up `<n>` and `type` preset (grapheme stagger) | 9 | Number emphasis | Final-frame text equals static text |
| 11 | Scene transitions | 9 | Polish | Visual review via `contact.png` |
| 12 | Optional audio mix and licence checkbox | 3 (encode) | Background music option | `ffprobe` shows audio stream, manifest records licence note |
| 13 | Readability lint: dynamic hold from character count | 2, 5a | Fewer unreadable scenes | Lint warnings on dense scenes |

Steps 5a, 5b, 6 can run in parallel with 2-4 once 1 is done. If the roadmap needs phases: Phase 1 = steps 0-4 (foundation, no behavior change), Phase 2 = steps 5-8 (draft bundle), Phase 3 = steps 9-11 (motion), Phase 4 = steps 12-13 (audio, polish).

## Roadmap Implications and Research Flags

- Phase 1 (foundation): standard refactor. Risk is regression, so the golden test is the phase's exit criterion. Needs a decision on how to compare frames (hash vs. pixel diff tolerance across Chromium builds).
- Phase 2 (draft bundle): the rule list and the Korean compliance wording need a domain pass with the owner's standards (더원자산관리 지침, 금소법). That is content research, not engineering. Flag for deeper research.
- Phase 3 (motion): needs a short spike on Korean grapheme splitting and text-wrap stability under per-character opacity, and on real frame-rate/render time on the actual cloud environment.
- Phase 4: standard.

## Open Questions

- Should `drafts/` be committed? (Recommend yes after promote, or delete; never auto-commit.)
- Date selection: who sets the publish date and slug, the user or Claude from the series cadence? Skill should ask when ambiguous.
- Hook scene vs. dedicated cover design: is the hook scene frame acceptable as a cover, or does the brand want a different cover layout? The 1 existing cover is hand-made; compare before locking `cover.py`.
- Does the real cloud environment have Noto Sans CJK KR and a Playwright version matching Chromium? Not true in the research sandbox. `doctor` must settle this early.

## Sources

- Local code and data (HIGH): `/home/user/kiwoom-cards/tools/reel.py`, `tools/cards.py`, `tools/README.md`, `2026/reels/specs/*.json`, `2026/02-tax-deduction/spec.json`, `.claude/hooks/session-start.sh`, `.planning/PROJECT.md`.
- Local measurement (MEDIUM): 120 ms per full-frame 1080x1920 screenshot via Playwright 1.64.1 with `executable_path=/opt/pw-browsers/chromium`; default `launch()` failed; no Korean font in sandbox.
- Instagram grid crop (MEDIUM, secondary sources that disagree on exact numbers): profile grid shows a centered 3:4 crop of the 9:16 cover, so keep key text in the central 1080x1440 (top and bottom 240 px cropped). [Hopper HQ Reel size and safe zones](https://www.hopperhq.com/blog/instagram-reel-size/), [Planoly guide to the vertical grid](https://www.planoly.com/blog/guide-to-instagrams-new-vertical-grid.md), [PostEverywhere reels aspect ratio](https://posteverywhere.ai/blog/instagram-reels-aspect-ratio).
- Instagram hashtag cap (MEDIUM, news coverage, one dissenting blog): Instagram announced a gradual cap of 5 hashtags per post or reel. Recommend the linter default to a configurable cap of 5. [Social Samosa](https://www.socialsamosa.com/news-2/instagram-hashtags-five-per-post-10923075), [Social Media Today](https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/).
