# Phase 3: 점검과 검수 묶음 (Compliance & Review Bundle) - Research

**Researched:** 2026-10-29
**Domain:** Data-file expression linter (Korean ad-wording risk) + one-command review bundle + human-approval/promote gate, on top of the existing stdlib Python + Playwright + ffmpeg pipeline
**Confidence:** MEDIUM overall. HIGH for the bundle/cover/contact-sheet/approval mechanics (executed in this session). MEDIUM-LOW for the legal substance of the rule list (primary Korean legal sources not reachable; rules stay "초안 규칙 — 준법 검토 전" per D-05).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

진행 방식: 사용자가 "추천대로"로 답해 온 방식에 따라 추천안으로 정했다(2026-10-29 재개 작업, 사용자는 앱을 보지 않는 중). 아래 오너 게이트는 ROADMAP의 기본값을 따르고, 모두 나중에 바꿀 수 있게 "미확인" 칸으로 둔다.

**오너 게이트 (ROADMAP 기본값 채택)**
- **D-01:** 금소법 광고 해당 여부는 **광고 후보로 간주**한다. 검수 요약 문서에 "광고 해당 여부: 미확인" 칸을 두고 사람이 기록한다. 키움 브랜드 관계도 같은 문서에 "미확인" 칸으로 둔다. — **Reversibility:** reversible — 문서 칸 값만 바뀜
- **D-02:** 필수 고지 문구는 Phase 2의 초안 고지(`tools/data/caption_config.json`)를 게시글에 쓰고, 영상에는 기존처럼 `basis`와 주의 장면으로 둔다. 문구·위치·내부 심의 절차는 "초안 — 준법 검토 전"으로 표시한다. 심의 상태(초안/내부 검수/승인)와 심의번호는 자유 입력 칸이며 기본값 "미확인".
- **D-03:** 표지는 **훅 장면 정지 화면**(렌더러의 `cover_ms` 시점)으로 만든다. 글자가 중앙 1080×1440 영역 안에 있는지 측정해 벗어나면 경고한다. 전용 표지 레이아웃은 만들지 않는다.

**금소법 표현 점검 (COMP)**
- **D-04:** 점검 규칙은 데이터 파일 `tools/data/compliance_rules.json`에 둔다(COMP-05). 규칙마다 id, 분류(단정·보장/세무 단정/상품 권유/비교·비방/개인정보/근거 누락 등), 패턴, 결과 등급("수정 필요"/"확인 필요"), 사유, 대체 표현 제안을 적는다. 파일에 규칙 버전과 기준일을 둔다.
- **D-05:** 규칙에는 "초안 규칙 — 준법 검토 전"을 표시하고, 금소법 조문 번호를 점검 메시지에 인용하지 않는다(ROADMAP Research flag).
- **D-06:** 점검 대상은 원고 장면 top·lines, basis, 게시글 문구(hook·요약·고정 고지 포함), 해시태그 전부(COMP-01). 결과 항목마다 위치(장면·줄 또는 게시글 줄), 문제 표현, 사유, 대체 표현 제안을 붙인다.
- **D-07:** "확인 필요" 항목(COMP-02)은 Phase 2 `check.json`의 확인 필요·가정 수치 결과를 그대로 가져오고, 여기에 세무 수치 장면의 "세무사 확인" 누락, 과거 성과 언급 시 "미래 보장 아님" 누락 같은 규칙을 더한다. 중복 판정 로직을 새로 만들지 않는다.
- **D-08:** 결과 머리말은 "위험 표현 n건 발견" 또는 "패턴상 발견 없음 — 사람 검수 필요" 둘 중 하나만, 규칙 버전·기준일과 함께 나온다(COMP-03). "통과"라는 말은 어디에도 쓰지 않는다.
- **D-09:** 탐지율·오탐 보고서(COMP-04)는 기존 10편 원고와 레드팀 사례(부적절 30건 이상, 적절 15건 이상)를 저장소의 테스트 데이터로 두고 명령 하나로 만든다. 레드팀 문장은 공개용 가상 문장만 쓴다(고객 사례 금지).
- **D-10:** 대체 표현은 제안만 하고 원고를 자동으로 고치지 않는다(REQUIREMENTS Out of Scope).

**검수 묶음 (BNDL)**
- **D-11:** 명령 하나(`draft.py bundle <dir>`)가 확장 → 점검 → 표현 점검 → 게시글 → 렌더 → 표지 → 장면 모음 → 검수 요약을 차례로 다시 만든다. 원고 수정 후에도 같은 명령으로 전부 다시 만든다(BNDL-05). `make-reel` 스킬은 이 명령을 쓰도록 바꾼다.
- **D-12:** 장면 모음 이미지(BNDL-03)는 장면마다 정지 화면 한 장씩을 한 이미지에 모은다. 새 패키지 없이 ffmpeg(또는 이미 설치된 Pillow)로 만든다.
- **D-13:** 검수 요약 문서(BNDL-04, COMP-06)는 초안 폴더의 Markdown 한 장(`review.md`): 상태 배너(초안 — 사람 검수 후 게시) → 점검 결과 → 사람 확인 목록(수치 재확인, 기준일, 표지 크롭, 음원 라이선스, 개인정보) → 광고 해당 여부·심의 상태·심의번호 기록 칸(기본 "미확인").
- **D-14:** 걸린 시간은 묶음 명령이 시작·끝 시각을 기록해 검수 요약과 별도 기록 파일에 남긴다(BNDL-07). 10분 기준은 주제 입력부터 묶음 완성까지의 실측으로 확인한다.

**승인과 옮기기 (BNDL-06)**
- **D-15:** 승인은 사람 전용이다. 승인 명령은 Phase 2의 `figures confirm`처럼 대화형 터미널과 재입력을 요구하고, 승인 시점의 파일 지문(sha256)을 초안 폴더에 기록한다. Claude는 승인 명령을 실행하지 않는다. — **Reversibility:** costly — 승인 기록 형식이 옮기기 판정의 기준이 됨
- **D-16:** 옮기기 명령은 승인 기록이 있고, "수정 필요"가 0건이고, 승인 뒤 파일 지문이 그대로일 때만 `2026/reels/<게시일>-<슬러그>.mp4`, `2026/reels/specs/<게시일>-<슬러그>.json`, `2026/reels/captions/<게시일>-<슬러그>.txt`(표지는 `2026/reels/<게시일>-<슬러그>-cover.png`)로 복사한다. 하나라도 어긋나면 거부한다. 이미 있는 게시 파일은 덮어쓰지 않는다.

**이어지는 결정**
- 새 릴스는 `--layout new`, 기존 10편과 게시된 파일은 건드리지 않는다(Phase 1·2).
- 등록부 수치는 사람만 "확인" 처리한다. 국민연금 평균 같은 통계 수치는 정확한 값을 쓰지 않고 필요할 때 조사한다(STATE.md).
- 사용량 절약: 계획 검토·재리뷰 없이 코드 리뷰 1회, 최종 검증 1회.

### Claude's Discretion
- 규칙 패턴 문법(정규식·조사 허용 방식), 규칙 파일 세부 스키마.
- 레드팀 문장 구성, 보고서 형식.
- 장면 모음 이미지의 배치·크기, 검수 요약 문서의 세부 문구.
- 승인 기록 파일 이름과 형식.

### Deferred Ideas (OUT OF SCOPE)
- AI 의미 점검(암시적 보장 표현) — v2 (COMP-V2-01)
- 표지 후보 2~3안·3:4 그리드 미리보기 — v2 (BNDL-V2-01)
- 등록부 직접 편집을 막는 작업 환경 차단 규칙(PreToolUse) — 사용자 결정 대기 (Phase 2 남은 위험)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMP-01 | 수정 필요 항목 (단정·보장, 세무 단정, 상품 권유, 비교·비방, 개인정보) with location, text, reason, suggestion | Rule schema + seed rules G/T/S/C/P (Appendix A), engine algorithm (§Compliance Engine) |
| COMP-02 | 확인 필요 (근거·기준일, 예시·가정, 세무사 확인, 미래 보장 아님 누락) | `requires` / `basis_required` rule types R-01..R-05 + lift of `check.json` needs_check/assumptions/warnings (D-07) |
| COMP-03 | No "통과"; headline is one of two strings + rule version/date | Headline contract + unit test that greps every generated string for "통과" |
| COMP-04 | Detection/false-positive report over 10 published specs + red-team (≥30 bad, ≥15 good) | Seed corpus 41 bad / 21 good (Appendix B), measured numbers, report format, `draft.py redteam` |
| COMP-05 | Rules are data, user can edit | `tools/data/compliance_rules.json`, strict loader with Korean errors, per-rule examples self-test |
| COMP-06 | 광고 해당 여부 / 심의 상태 / 심의번호 fields, default "미확인" | `record.json` (never overwritten by rebuild) rendered into `review.md` |
| BNDL-01 | One request -> folder with spec, MP4, cover, caption, check table | `draft.py bundle DIR` orchestration (§Bundle) |
| BNDL-02 | Cover from first scene, text inside central 1080×1440 | Renderer frame-sink copy of scene-1 final frame + stdlib pixel audit (rows 240..1679) |
| BNDL-03 | Scene still-frame contact sheet | Per-scene final frames -> ffmpeg `drawtext`+`tile` (no Pillow) |
| BNDL-04 | Review summary with banner, results, human checklist | `review.md` template (§Bundle) |
| BNDL-05 | Edit -> rerun regenerates everything incl. check | Idempotent bundle, stale-artifact purge, approval invalidation |
| BNDL-06 | Promote only after approval; refuse on 수정 필요>0 / hash drift / existing target | `approval.json` + `promote` (§Approval) |
| BNDL-07 | ≤10 min, measured | `bundle.json` timing; measured machine time ≈ 17 s (§Bundle) |
</phase_requirements>

## Summary

The whole phase can be built with **no new packages**: stdlib `re/json/hashlib/unicodedata`, the already-pinned Playwright renderer, and ffmpeg 6.1.1 (which has `drawtext`, `tile`, `hstack` here). Pillow is installed in this image but is not used anywhere in `tools/` today and is not in `tools/requirements.txt`, so adding it would be a new dependency for a job ffmpeg + 20 lines of bytes comparison already does. [VERIFIED: grep of tools/*.py tools/reelkit/*.py found no `PIL`/`numpy` import; `tools/requirements.txt` contains only `playwright==1.63.0`]

The compliance linter is a **data-driven regex engine with clause-window negation handling**. A 28-rule / 6-category seed (Appendix A) was prototyped and measured in this session: 0 "수정 필요" findings and 2 "확인 필요" findings across the 10 published specs; 0 findings on the Phase 2 caption config and draft caption (except one not-applicable basis rule); on a 41-bad / 21-good fictional corpus the first untuned pass found 36/41 (88%) with 2/18 good sentences flagged, and the tuned seed finds 41/41 with 0/21 flagged. **The tuned numbers are overfit** (rules and corpus written by the same author, implicit-tier rules written after seeing the misses); the plan must add a held-out batch and report it separately. Rules are keyword/pattern heuristics: implicit guarantees stay a v2 (COMP-V2-01) problem, and the report must say so.

The bundle is cheap in machine time (measured on the existing Phase 2 draft: expand 0.29 s, check 0.09 s, caption 0.08 s, render 14.8 s for a 23.5 s reel, cover+sheet ≈ 1.5 s; ≈ 17 s total) so BNDL-07's 10 minutes is consumed almost entirely by Claude authoring `spec.src.json`/`caption.src.json`. Cover and contact sheet should come from a **frame sink hook inside `render_reel`** (lossless PNGs the encoder already consumes), not from decoding the MP4. Approval/promote are small and mostly a matter of getting invariants right: hash everything, invalidate on rebuild, recheck rules live at promote, link-not-overwrite.

**Primary recommendation:** Build `compliance.py` (rules engine + `compliance.json`), `bundle.py` (orchestrator in order expand → check → **caption → compliance** → render+frame-sink → cover audit → contact sheet → review → timing), and `approve.py` (approve/promote) as stdlib modules wired into `draft.py`; ship Appendix A/B as the seed rules file and corpus; extend `render_reel` with one optional keyword-only `frame_sink` callback; fix the four tests that hard-code `len(specs) == 10` in Wave 0.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Rule storage and edits (COMP-05) | Data file (`tools/data/compliance_rules.json`) | Loader/validator module | Users edit data, never code; loader rejects bad regex with the rule id |
| Pattern scan, negation, dedupe, headline | CLI/library (`reelkit/compliance.py`) | — | Pure function of (doc text, rules); unit-testable without browser |
| 확인 필요 lift (check.json, layout/caption warnings) | CLI/library (`compliance.py` reads existing outputs) | — | D-07: no duplicated judgement logic |
| Final-state frames, cover, scene stills | Renderer (Chromium via `render_reel`) | ffmpeg (tile/drawtext) | Frames already exist as PNGs at the moment of render; copy is free and lossless |
| Cover crop verification | Stdlib bytes audit on the cover PNG (ffmpeg rawvideo decode) | In-browser `MEASURE_JS` rects (optional, gives line number) | Renderer-independent, authoritative; measured rects only to name the offending line |
| Orchestration, idempotence, timing | CLI (`bundle.py`) | Filesystem | Order, purge-stale, atomic writes, `bundle.json` |
| Human record fields (광고 여부 등) | Filesystem (`record.json`, never regenerated) | `review.md` (generated view) | Rebuild must not erase human input |
| Approval and promote | CLI (TTY gate) + Filesystem (sha256 record, no-overwrite link) | Compliance live recheck | Gate lives in code and in file hashes, not in Claude's behaviour |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`re`, `json`, `hashlib`, `unicodedata`, `dataclasses`, `os`, `time`) | 3.13 | Engine, hashing, normalization, timing | Project convention "stdlib만"; zero install [VERIFIED: 03-CONTEXT.md Established Patterns] |
| Playwright (pinned) | 1.63.0 (system may carry 1.64.1 + preinstalled Chromium via path fallback) | Existing renderer; add `frame_sink` hook | Already proven; render of the Phase 2 draft succeeded this session |
| ffmpeg / ffprobe | 6.1.1 | Contact sheet (`drawtext`, `tile`), raw RGB decode for cover audit | Filters present: `drawtext`, `tile`, `hstack`, `xstack` [VERIFIED: `ffmpeg -filters` run this session] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bundled Noto Sans KR Bold | `tools/fonts/NotoSansKR-Bold.otf` | `drawtext fontfile=` for contact-sheet labels (Hangul verified rendering) | Labels only |
| `unittest` | stdlib | Tests (402 existing) | All new tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ffmpeg tile + drawtext | Pillow `ImageDraw` sheet (verified working: 0.11 s, per-tile labels with time) | Nicer labels, but new un-pinned dependency not in `requirements.txt`; D-12 allows it only because it is "already installed" in this image. Use ffmpeg; put per-scene times in `review.md` table |
| Frame sink in `render_reel` | `ffmpeg -ss <cover_ms> -i mp4 -frames:v 1` (verified 0.25 s) | Decoupled from renderer but lossy (x264 chroma noise; pixel audit needs a tolerance). Keep as fallback for "re-cover an existing MP4" only |
| Regex engine | Morphological analyser (Kiwi/KoNLPy) | Rejected in project STACK; closed phrase set does not need it |

**Installation:** none. `tools/requirements.txt` unchanged.

## Package Legitimacy Audit

No external packages are installed or recommended by this phase. Audit not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 spec.src.json + caption.src.json (Claude-authored, in drafts/<date>-<slug>/)
            │
            ▼
   draft.py bundle DIR ───────────────► bundle.json (steps, seconds, status)
            │   purge stale outputs + approval.json at start
            ▼
   1 expand ──► spec.json ──► 2 check ──► check.json ──(errors?)──► STOP: review.md says
            │                                                     "원고 오류 — 영상 미생성"
            ▼
   3 caption ──► caption.txt ─┐
            │                 ▼
            │        4 compliance(spec fields + caption lines + hashtags)
            │                 │  rules ◄── tools/data/compliance_rules.json
            │                 ▼
            │        compliance.json {headline, findings, suppressed, lifted 확인 필요}
            ▼
   5 render_reel(frame_sink) ─► <slug>.mp4 + per-scene final PNGs (temp)
            │                         │
            │      ┌──────────────────┴─────────────────┐
            │      ▼                                    ▼
            │  6 cover = scene-1 PNG ─► pixel audit   7 ffmpeg tile ─► <slug>-scenes.png
            │      │  (rows 240..1679 only)
            ▼      ▼
   8 review.md  ◄── compliance.json + check.json + layout/caption warnings + record.json
                    (record.json = human fields, create-if-missing, never overwritten)

 human, TTY:  draft.py approve DIR ─► approval.json (sha256 of every promoted + provenance file)
 then:        draft.py promote DIR ─► recheck rules live, verify hashes, link-not-overwrite into
              2026/reels/<slug>.mp4, <slug>-cover.png, specs/<slug>.json, captions/<slug>.txt
```

### Recommended Project Structure
```
tools/
├── data/compliance_rules.json        # NEW seed = Appendix A
├── reelkit/
│   ├── compliance.py                 # load_rules, scan, requires, dedupe, lift, headline, to_json
│   ├── redteam.py                    # corpus runner + report
│   ├── bundle.py                     # orchestrator + timing + stale purge
│   ├── review.py                     # review.md + record.json defaults
│   ├── stills.py                     # cover audit (stdlib), contact sheet (ffmpeg), scene times
│   └── approve.py                    # approve record, promote
├── draft.py                          # + bundle, compliance, redteam, approve, promote subcommands
└── tests/
    ├── redteam/corpus.json           # NEW seed = Appendix B
    └── test_compliance.py test_redteam.py test_bundle.py test_stills.py test_approve.py
.claude/skills/make-reel/SKILL.md     # steps 6-9 collapse into `draft.py bundle`
2026/reels/captions/                  # created by promote (does not exist yet)
```

### Compliance Engine (COMP-01/02/03/05)

**Rule schema** (strict loader; unknown keys, duplicate ids, bad severity, bad regex, empty-matching regex, pattern containing a statute-number shape `제\s*\d+\s*조` all rejected with Korean messages naming the rule id):

```
file:  {schema:1, version:"0.1", status:"초안 규칙 — 준법 검토 전", as_of:"2026-10-29",
        macros:{J:<particle group>, S:"\s*"}, negators:<regex>, mention_markers:<regex>,
        compact_terms:[...], rules:[...]}
rule:  {id:"G-01", category, severity:"수정 필요"|"확인 필요", reason, suggest,
        type: "pattern"(default) | "requires" | "basis_required",
        pattern|when|when_scene|must_have : regex strings (macros {J}/{S} expanded by plain str.replace),
        negatable: bool (default true), except:[regex], applies_to:["reel","caption"], scope:"reel",
        examples:{hit:[..], miss:[..]}   # recommended: executed by the loader self-test}
```

- Macro `{J}` = optional Korean particle group `(?:은|는|이|가|을|를|도|만|의|에|에는|으로|로|이라|라)?`; `{S}` = `\s*` (matches the line break between wrapped reel lines, so "원금 / 보장" is caught). Macros are substituted with `str.replace("{J}", ...)` only for those exact names, so regex quantifiers like `{2,3}` are untouched. [VERIFIED: executed in prototype]
- **Text model.** Normalize each field (NFKC, strip zero-width U+200B/C/D, U+2060, U+00AD, U+FEFF, remove `<g></g><s></s>` tags). Join fields of one scene with `"\n"` and scenes (and `basis`) with `"\n\n"`; run all `pattern` rules on the joined reel text; same for the caption (one "scene" = caption lines, hashtags tokenized as separate fields). Location = field containing match start (`scene 3 line 2`, `scene 2 top`, `basis`, `caption line 4`, `hashtag #3`).
- **Negation/exception.** For `negatable` rules, take the *after-window* = up to 22 chars after the match, cut at `[.!?;]`, `\n\n` or 지만/하지만/그러나/다만/그런데; suppress when the window matches `negators` (않, 아님, 아니, 아닙, 안 됩, 수 없, 불가, 지 마, 보장 없, 뜻이 아, 오해, `다는 보장은 어디에도 없` …) or `mention_markers` (`라는 말/표현/문구`). `except` regexes are tested against the whole clause (clause start = previous sentence delimiter). Line breaks inside a scene must **not** end the window ("손실이 없다는 보장은 / 어디에도 없어요" is one sentence) but scene boundaries must (otherwise a "않" in the next scene would suppress a claim). Two real bugs hit while prototyping: ending the window at `\n`, and an off-by-one that chopped the first char of the clause (made `except` silently stop working). Both need regression tests.
- **Suppressed is never silent.** Every suppressed match goes to `compliance.json.suppressed` and into a `review.md` section "예외 처리로 제외된 표현 (사람 확인)". This is what makes the heuristic safe: a wrong suppression is visible. [VERIFIED: design, tested on adversarial strings below]
- **Compact pass** (catches "원 금 보 장", zero-width splitting): for fields with **zero** pattern findings **and zero** suppressions, remove all whitespace after normalization and substring-match `compact_terms`; report as 수정 필요 with rule id `X-compact`. (Restricting to clean fields avoids re-flagging negated sentences like "원금 보장 아님".)
- **Dedupe.** Overlapping matches in the same field become one finding; keep the more specific category (T/S/P/C before G) and list all rule ids. Otherwise "무조건 절세" double counts and inflates "위험 표현 n건".
- **`requires` rules** (R-01 past performance → "미래 보장 아님", R-02 tax figure → 세무사 확인, R-03 rate figure → 예시/가정, R-04 investment mention → 손실 가능): if any field matches `when`, the whole reel text (or caption doc) must match `must_have`, else one 확인 필요 finding located at the first trigger. `basis_required` (R-05): digits+unit in scenes but `basis` lacks 기준/예시/가정/출처/…/`\d{4}년` → 확인 필요. R-05 applies to the reel only (on the caption doc it fires "basis 없음" wrongly — observed).
- **Lift (D-07).** Convert `check.json` `needs_check` (reason 미확인 수치/발의 수치), `assumptions`, `warnings`, the renderer's layout warnings (WRAP etc.) and caption warnings into 확인 필요 entries with `rule:"CHK-*"` and the original text verbatim. No new judgement logic.
- **Headline (COMP-03).** Exactly one of `위험 표현 {n}건 발견 · 규칙 v{version}(초안) · 기준일 {as_of}` or `패턴상 발견 없음 — 사람 검수 필요 · 규칙 v{version}(초안) · 기준일 {as_of}`. Recommended `n` = number of **pattern-rule** findings of both severities (expression risks); 확인 필요 from `requires`/`basis_required`/CHK-* are shown on a second line ("확인 필요 m건") so a "발견 없음" headline can never read as clean. Promote gate keys on 수정 필요 only. (Open Question 1.)
- **Statute numbers.** Rule text must not cite article numbers (D-05); add a unit test: no match of `제\s*\d+\s*조` in rules file or any generated output; a second test: no "통과" in rules file, `compliance.json`, `review.md`, headline strings (existing precedent: `test_check.py:81` `assertNotIn("통과", rep.summary())`).

**Severity policy (important for promote):** D-16 makes any 수정 필요 block promotion and nothing in the decisions allows a waiver. So **only precise patterns may be 수정 필요**; broad or context-dependent patterns (최대/가장, 세금 없이, 반드시, 고수익, 훨씬 유리, 회사명) are 확인 필요. A false positive at 수정 필요 forces a reword; at 확인 필요 it costs one glance.

**Seed rule set summary** (full JSON in Appendix A; 28 rules + 12 compact terms):

| Category | Rule ids | Severity | Notes |
|----------|----------|----------|-------|
| 단정·보장 | G-01 원금 보장, G-02 수익 확정/보장, G-03 무조건/절대/100%, G-04 반드시 오른다류, G-05 손실·위험 없음/제로, G-09 영문 guarantee | 수정 필요 | negatable |
| | G-06 고수익/대박/확정금리, G-07 반드시(일반), G-08 암시적("걱정 끝", "알아서 불어") | 확인 필요 | G-08 is the only implicit-tier heuristic; tuned after seeing misses |
| 세무 단정 | T-01 누구나 환급/세금 낼 필요 없/탈세/세무조사 안 걸/무조건 절세, T-02 세무사 확인 없이/합법 단정 | 수정 필요 | |
| | T-03 세금 없이/비과세입니다 | 확인 필요 | hits published ebook-event "세금 없이 얼마까지?" (a question) |
| 상품 권유 | S-01 가입하세요/사세요, S-02 X를 추천/강추 | 수정 필요 | |
| | S-03 회사·종목명, S-04 놓치면 후회/마감 임박 | 확인 필요 | S-03 list is illustrative, user-extensible |
| 비교·비방 | C-01 업계/국내 최고·1위·유일, C-03 타사 비방/"은행은 절대 안 알려주는" | 수정 필요 | |
| | C-02 훨씬 유리, C-04 가장/최대 + 형용 | 확인 필요 | "최대 148.5만" (Phase 2 draft) must not flag: `최대` only with 유리/좋/… |
| 개인정보 | P-01 phone/주민번호/카드/계좌/email, P-02 이름+님/씨, 김OO 마스킹, `…고객님` | 수정 필요 | P-02 has surname whitelist + exception list (어머님, 선생님 …); `@kiwoom.mentor` does not match the email pattern (needs a local part) |
| | P-03 실제 고객/상담 사례 | 확인 필요 | |
| 근거 누락 | R-01..R-05 | 확인 필요 | structural, see above |

**Measured on repo data (prototype, this session):**
- 10 published specs: **수정 필요 0** for all 10; 확인 필요: `2026-10-19-rate-secret-1` R-02 (이자소득세 15.4% with no 세무사 line), `2026-10-29-ebook-event` T-03 ("세금 없이"). Suppressed: 0. [VERIFIED: executed]
- `tools/data/caption_config.json` disclaimer+CTA: 0 findings. Draft caption `2026/reels/drafts/2026-11-08-pension-credit-limit/caption.txt`: 0 findings (R-05 fired only because the caption doc has no basis → set `applies_to:["reel"]`). [VERIFIED: executed]
- Adversarial strings: "원금 보장되며 위험하지 않습니다" → G-05 still flags the second claim but G-01 is suppressed by the "않" in the same clause (a miss for G-01, caught by G-05 — visible in `suppressed`); "원금 보장 상품이에요. 손실은 걱정하지 않아도 돼요" → flagged (sentence stop works); "원 금 보 장" → caught only by compact pass; "원금 손실 제로", "guaranteed" → caught after adding G-05 제로 alt and G-09. [VERIFIED: executed]

### Red-team corpus and report (COMP-04)

**Corpus file** `tools/tests/redteam/corpus.json` (seed in Appendix B, 41 bad + 21 good): each entry `{id, label:"bad"|"good", category, tier:"explicit"|"obfuscated"|"implicit", lines:[...], basis?, expect_severity?, note?}`. Entries are mini reel docs (so cross-line and basis-dependent rules are testable). `tier` separates what regex can catch from what it cannot; 3 implicit entries are deliberate. Good set includes the hard negatives: "원금 보장 아님", "수익을 보장하지 않습니다", "무조건 절세는 아니에요", "'확정 수익'이라는 말은 조심해서 보세요", "반드시 세무사에게 확인", "손실이 없다는 보장은 어디에도 없어요", 어머님/고객센터/전체 고객, and compliant 예시/가정/세무사 확인 scenes. Fictional only; no customer data.

**Command:** `python3 tools/draft.py redteam [--rules PATH] [--corpus PATH] [--json]`. Output format (Korean, no "통과"):
```
규칙 v0.1(초안) · 기준일 2026-10-29 · 규칙 28개
[기존 10편] 수정 필요 0건 · 확인 필요 2건 (목록)         ← 수정 필요가 있으면 오탐 후보로 표시
[레드팀 부적절 41건]  탐지 N/41 (xx%)   tier: explicit a/b · obfuscated a/b · implicit a/b
   분류별: 단정·보장 a/b · 세무 단정 … · 개인정보 …
   놓친 문장: id + 문장      분류/등급 불일치: id (기대 수정 필요, 실제 확인 필요)
[레드팀 적절 21건]    오탐 N/21 (수정 필요 오탐 M)       오탐 문장: id + 규칙 id + 걸린 표현
[예외 처리로 제외] 건수와 규칙별 (정상 문장이 예외로 빠진 수 = 예외 규칙 작동 확인)
한계: 키워드·패턴 방식이라 암시적 표현은 못 잡습니다 (AI 의미 점검은 v2)
```
Definitions: **탐지** = bad entry with ≥1 finding whose category equals the entry's and whose severity ≥ `expect_severity` (default 수정 필요); **오탐** = good entry with ≥1 finding of any severity (also report the 수정 필요-only count); published-10 "수정 필요" counts as false positives (none are inappropriate by construction).

**Measured (seed corpus, this session):**

| Pass | explicit | obfuscated | implicit | good flagged (any / 수정 필요) |
|------|----------|-----------|----------|--------------------------------|
| First pass (before tuning) | 34/36 | 2/2 | 0/3 | 2/18 / 1/18 |
| Tuned seed (Appendix A) | 36/36 | 2/2 | 3/3 | 0/21 / 0/21 |

Per category (explicit+obfuscated, tuned): 단정·보장 12/12, 세무 단정 6/6, 상품 권유 5/5, 비교·비방 5/5, 개인정보 6/6, 근거 누락 4/4. **Caveat to carry into the plan:** the tuned figures are in-sample. Add a **held-out** set (≥ 10 bad, ≥ 5 good) written without looking at the rules (user, or a separate Claude pass given only the category list) and report its rate on its own line; do not tune rules on it. Regression-test thresholds should be: published-10 수정 필요 = 0, explicit+obfuscated recall = 100% on the seed, good-set 수정 필요 FP = 0 — and nothing on implicit/held-out beyond "report prints".

### Cover PNG and crop verification (BNDL-02)

- **Source of the frame.** `render_reel` already writes `v{n:03d}.png` for every state and measures at each scene's final state (`if st.k == len(st.lines):  # 장면 최종 상태 …` at `tools/reelkit/render.py:122`). Add one optional keyword-only parameter `frame_sink=None` to `render_reel` (def at `render.py:92`), called there as `frame_sink(st.scene, f)`; the bundle copies scene-0's PNG to `<slug>-cover.png` and all scene PNGs to a temp dir for the contact sheet. Default `None` keeps output byte-identical, so golden (10/10) is unaffected.
- **Is the final state the frame at `cover_ms`?** `cover_ms` is `round((LINE * (first - 1) + 0.4) * 1000)` [VERIFIED: tools/reelkit/timeline.py:40-41], with `LINE = 0.85` and `HOLD = 1.9` [VERIFIED: tools/reelkit/constants.py:11-12]. Scene 1's final state starts at `LINE*(first-1)` and lasts `HOLD`, so `cover_ms` (+0.4 s) lies inside it. Verified on the Phase 2 draft: `cover_ms=1250`, scene-1 final state starts at 0.85 s.
- **Crop window.** Grid crop of a 1080×1920 cover to 3:4 → 1080×1440 centered → rows **240 … 1679**, full width (`(1920−1440)/2 = 240`). Because it is full width, only vertical bounds matter. The current new layout already keeps text at `top=270` … `bottom_ui=450` [VERIFIED: tools/reelkit/constants.py:21,23 `top=270,` `bottom_ui=450,   # …`] i.e. y 270..1470, inside 240..1680, so a layout-clean scene 1 is crop-clean by construction; the audit is a defence against layout changes (Phase 4 motion) and gives the explicit BNDL-02 evidence.
- **Authoritative check (stdlib, verified):** decode the PNG with `ffmpeg -i cover.png -f rawvideo -pix_fmt rgb24 -` (6.2 MB, 0.45 s incl. scan), compare each 3240-byte row with a flat background row built from `SAGE = "#DEE9E0"` [VERIFIED: tools/reelkit/constants.py:5]; a row that differs (renderer PNG is exact; use tolerance 24 only if auditing an MP4-derived frame) is "ink". Ink rows allowed: 0–13 (the 14 px progress bar, `#rk-bar` height 14px) and 240–1679. Any other ink row → `COVER_CROP` warning with first/last offending y. Measured on the draft's cover: ink rows 0–1031, 0 violations outside the crop.
- **Naming the offending line** (optional): `new_inner_html` + `MEASURE_JS` already return per-element rects; `evaluate_layout`-style helper `cover_crop_warnings(measure)` can list elements with `t < 240` or `b > 1680`. In `render_reel` the scene-1 `measured` dict is available for free. Only for message quality; the pixel audit decides.
- **Cosmetic note for the human checklist:** the text stack is centered in y 270–1250 (center ≈ 760) while the grid crop is centered at 960, so thumbnails look top-heavy; this is expected, not a fault.

### Contact sheet (BNDL-03)

- Frames: the per-scene final-state PNGs from the same `frame_sink` (lossless, no time math). If re-making from an MP4 is ever needed: scene final-state start times from `timeline.build_states` (sum of `dur` until `st.k == len(st.lines)`) plus 0.4 s, frame number `round(t*30)`; `ffmpeg -i x.mp4 -vf "select='eq(n\,37)+eq(n\,…)',scale=360:640" -fps_mode passthrough sc%02d.png` took 1.2 s for 7 frames on the draft. [VERIFIED: executed]
- Sheet command (verified; 1500×1316 for 7 scenes): copy frames to `sc01.png…`, then
  `ffmpeg -y -framerate 1 -i sc%02d.png -vf "scale=360:640,drawtext=fontfile=<tools/fonts/NotoSansKR-Bold.otf>:text='장면 %{expr\:n+1}':x=10:y=10:fontsize=28:fontcolor=black:box=1:boxcolor=white@0.8,tile=4x2:padding=12:margin=12:color=white" -frames:v 1 <slug>-scenes.png`.
  Pass the font path as an argument list (no shell). `tile=4x2` columns/rows must be computed from the scene count (`cols=4`, `rows=ceil(n/4)`). `%{n}` is zero-based; use `expr:n+1`. Hangul glyphs render with the bundled font.
- Put the per-scene time (final-state start +0.4 s) and the scene's first line in a `review.md` table next to the image link; per-tile time labels would need one drawtext per input (not worth it).

### Bundle command (BNDL-01/05/07)

**Interface:** `python3 tools/draft.py bundle DIR [--date YYYY-MM-DD] [--card CARD] [--request-start EPOCH]`. DIR must be a direct child of `2026/reels/drafts/` named `<date>-<slug>` (reuse `slot.check_slug/check_date`). Inputs required in DIR: `spec.src.json`, `caption.src.json`.

**Order (one deviation from D-11, recommended):** expand → check → **caption → compliance** → render(+frame sink) → cover audit → contact sheet → review → timing. D-11 lists 표현 점검 before 게시글, but D-06 requires scanning the assembled caption (hook, summary, fixed disclaimer, hashtags), which only exists after `caption`. `caption` already refuses to assemble when check has errors, which fits.

**Semantics:**
1. *Start:* delete stale generated outputs (`spec.json`, `check.json`, `compliance.json`, `caption.txt`, `<slug>.mp4`, `<slug>-cover.png`, `<slug>-scenes.png`, `*.safe-s*.png`, `review.md`) **and `approval.json`** so a failed rerun can never leave fresh files next to stale ones that look complete, and no approval outlives a rebuild. Never delete `*.src.json`, `skeleton.json`, `record.json`.
2. *Failure policy:* expand error → stop (exit 1), write `review.md` with the error. check errors → stop before render (exit 1; saves ~15 s), still run compliance on whatever exists and write `review.md`. Render env errors → exit 2 using the same exception mapping as `reel.py` (`FontLoadError, BrowserLaunchError, EncodeError`, Playwright `Error`, `OSError`, `SubprocessError`); import `render_reel` in-process (not a subprocess) so the frame sink works; factor the error mapping out of `reel.py:main` rather than copying it. Layout warnings under strict → exit 3 after writing everything; upload-spec FAIL → 4 (4 wins), matching `reel.py`. **Compliance findings never fail the bundle** (they are the product; counts go on the last stdout line and in `review.md`); optional `--fail-on-risk` → exit 5 if the plan wants it.
3. *Atomicity:* each artifact written via temp + `os.replace` (the encoder already does this for the MP4). `bundle.json` gets `status:"complete"|"failed"`, `failed_step`.
4. *Timing (BNDL-07/D-14):* `time.monotonic()` per step and wall-clock start/end in `bundle.json` `{started_at, finished_at, elapsed_s, steps:[{name, seconds, status}], request_started_at?, elapsed_since_request_s?, within_10_min}`. `slot --create` should stamp `created_at` in the new folder (small change) so the skill can report "folder created → bundle done" without a separate input; the user's confirmation wait before `--create` is excluded by design (document it). Pass `--request-start` if the skill wants to include its own start.
5. *Measured machine time* on the existing Phase 2 draft (7 scenes, 23.5 s): expand 0.29 s, check 0.09 s, caption 0.08 s, **render 14.8 s** (`real`), PNG-based cover audit 0.45 s, contact sheet ≈ 1 s → **≈ 17 s**. [VERIFIED: executed, `time` output]. A fresh container additionally pays the SessionStart pip install of Playwright (not part of the bundle). The 10-minute budget is therefore dominated by authoring; the plan's measurement task should time a full "topic → bundle" run with a real draft, not just the bundle.

**`review.md` template** (generated every run; Korean; contains no "통과"):
```
# 릴스 검수 요약 — <slug>
> **초안 — 사람 검수 후 게시**   (자동 생성 <시각> · 규칙 v0.1 초안 — 준법 검토 전)
## 1. 점검 결과
<headline line>            확인 필요 m건 · 예외 처리로 제외 k건
### 수정 필요 / 확인 필요 / 예외 처리로 제외됨(사람 확인) — tables: 위치 | 문제 표현 | 사유 | 대체 표현 제안
## 2. 한눈에 보기   표지·장면 모음 링크, 길이, 규격 검사 9/9 충족, 표지 크롭 검사 결과, 레이아웃 경고
## 3. 사람 확인 목록 (체크박스): 수치 재확인(등록부 id·상태) / 기준일 / 표지 크롭(그리드 미리보기) / 음원 라이선스(없음=무음) / 개인정보
## 4. 광고·심의 기록 (record.json 에 직접 기록)  광고 해당 여부 | 키움 브랜드 관계 | 심의 상태 | 심의번호 — 기본 "미확인"
## 5. 걸린 시간   bundle.json 요약
```
- `record.json` is created on the first bundle with `{ad_applicable:"미확인", brand_relation:"미확인", review_stage:"미확인", review_no:"미확인", reviewer:"", note:""}` and **never rewritten**; `review.md` renders its current values. Putting the human fields in `review.md` itself would lose them on every rebuild (BNDL-05) — this is the main trap in D-13.

### Approval and promote (BNDL-06)

**`draft.py approve DIR`** (human only, mirrors `figures confirm`): refuse when `not sys.stdin.isatty()` [VERIFIED: tools/draft.py:367 `if not sys.stdin.isatty():`]; require `--by NAME` and reject AI-looking names with the existing `figures.is_ai_name` (`AI_NAME_RE` at tools/reelkit/figures.py:39); print headline, counts, `record.json` values, file list; require the user to retype the slug; refuse when 수정 필요 > 0 (a human should not approve what promote will refuse); then write `approval.json`:

```
{"schema":1,"slug":"<date>-<slug>","approved_by":"…","approved_at":"<ISO local>",
 "rules":{"version":"0.1","sha256":"<rules file sha256>"},
 "counts":{"수정 필요":0,"확인 필요":7},
 "record":{…copy of record.json…},
 "files":{"<slug>.mp4":"<sha256>","<slug>-cover.png":"…","spec.json":"…","caption.txt":"…",
          "spec.src.json":"…","caption.src.json":"…","check.json":"…","compliance.json":"…"}}
```
Hash the four promoted files plus the provenance files; **do not hash `review.md`** (generated, carries timestamps) or `record.json` (human-editable after approval is fine; its snapshot is stored in the record).

**`draft.py promote DIR`** — in order, all-or-nothing: (1) `approval.json` exists and parses; slug equals the folder name and passes `slot.check_slug/check_date` (path-traversal guard); (2) recompute sha256 of every listed file and compare → any difference = refuse naming the file ("승인 뒤 바뀜"); (3) **re-run the compliance scan live** on `spec.json` + `caption.txt` with the *current* rules and refuse if 수정 필요 > 0 (do not trust the stored count; rules may have been tightened since). A changed rules hash alone → notice, not refusal; (4) preflight that all four targets do not exist (`2026/reels/<slug>.mp4`, `…/<slug>-cover.png`, `…/specs/<slug>.json`, `…/captions/<slug>.txt`; create `captions/`); (5) copy each to `.<name>.part` in the target directory, verify sha256 equals the approved hash, then `os.link(part, target)` (raises `FileExistsError` instead of overwriting, unlike `os.replace`) and unlink the part; on any failure remove the targets already linked in this run. Promote prints `git add` hints and **never runs git**. It needs no TTY (the gate is the approval record), so Claude may run it after the human has approved; flag in the plan if the user wants it human-only too.

**Residual (same as Phase 2 `figures confirm`):** `isatty` can be defeated by a pty wrapper, and the name filter is a slip guard only [VERIFIED: tools/draft.py:365-366 comment "pty 를 흉내 내는 우회는 막지 못한다 — REVIEW-FIX 참고"]. The real hardening is the *deferred* permission/PreToolUse rule (deny `Bash(python3 tools/draft.py approve:*)` and Edit/Write on `drafts/**/approval.json` and `record.json`); it needs the user's decision and is out of scope here, but SKILL.md must say "Claude never runs `approve` and never writes `record.json` values other than 미확인".

### Instagram profile-grid crop (confidence MEDIUM)

Search summaries of several third-party guides agree that the profile grid now shows a **3:4 vertical** crop and a 9:16 (1080×1920) cover is cropped to the centered **1080×1440** window; some older guides still say 1:1, and some list inconsistent cover sizes; no official Instagram specification was reachable. [CITED: hopperhq.com/blog/instagram-reel-size, planoly.com guide to Instagram's vertical grid, postfa.st cover safe zones — via WebSearch summary; official page not fetched (planoly host not resolvable from this session)]. Project research (CLAUDE.md "Version / source status") already marks grid/safe-zone numbers MEDIUM/LOW for the same disagreement. Treat 240..1679 as the working standard (D-03), keep the number in one constant, and keep "표지 크롭 — 인스타 프로필 그리드 미리보기에서 확인" as a **mandatory human checklist item** (Instagram's cover editor has a grid preview). If a 1:1 fallback is wanted later: the centered square is rows 420..1499, and the sample draft's ink (rows 500–1031) fits both; this is v2 (BNDL-V2-01), not Phase 3.

### Anti-Patterns to Avoid
- **Putting human-entered fields only in generated `review.md`:** rebuild erases them → `record.json`.
- **Trusting the stored 수정 필요 count at promote:** recompute live.
- **`os.replace`/`shutil.copy` onto the published path:** silently overwrites; use link-or-exclusive-create.
- **Hashing files that contain timestamps** (`review.md`, `bundle.json`): approval would drift on every harmless rerun.
- **A wide 수정 필요 pattern:** blocks promote with no waiver; keep wide patterns at 확인 필요.
- **Ending the negation window at a line break:** wrapped reel lines are one sentence.
- **Calling the result "통과", or letting "발견 없음" stand alone:** always print 확인 필요 count and the limits sentence.
- **Re-judging numbers in compliance:** read `check.json`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Contact sheet layout and labels | Custom image compositor | ffmpeg `tile` + `drawtext` | Verified; no dependency; Hangul via bundled font |
| Row-wise "is there ink outside the crop" | Image library, edge detection | ffmpeg rawvideo + flat-row bytes compare | 20 lines, exact on renderer PNGs |
| Frame capture for cover/sheet | MP4 decode + timestamp math | `frame_sink` in `render_reel` | Frames already exist; lossless |
| Atomic no-overwrite publish | `exists()` then `copy` (race) | `os.link` / `open(..., "xb")` | `FileExistsError` is the guard |
| Number judgement in compliance | A second number scanner | `check.json` + numscan results | D-07 forbids duplicate logic |
| TTY + retype human gate | New mechanism | Reuse `figures confirm` pattern and `is_ai_name` | Consistency, tested |
| AI-name filter, slug/date validation | New regexes | `figures.is_ai_name`, `slot.check_slug/check_date` | Already hardened by Phase 2 review |
| Korean morphology | Kiwi/KoNLPy | Particle macro `{J}` + clause windows | Closed phrase set; dependency-free |

**Key insight:** this phase is glue plus invariants. The risky parts are semantic (what gets flagged, what survives a rebuild, what a hash covers), not algorithmic.

## Runtime State Inventory

Not a rename/refactor phase — omitted. (Note one state hazard: promote creates the first file under `2026/reels/captions/`, and adds an 11th spec under `2026/reels/specs/`; see Pitfall 1.)

## Common Pitfalls

### Pitfall 1: Promote breaks the test suite and golden assumptions
**What goes wrong:** four tests assert exactly 10 published specs: `tools/tests/test_check.py:619` `self.assertEqual(len(specs), 10)`, `test_layout.py:156` `self.assertEqual(len(files), 10)`, `test_numscan.py:133` `self.assertEqual(len(SPECS), 10)`, `test_spec.py:41` `self.assertEqual(len(files), 10)`. The first real promote adds an 11th spec (v2, with ledger) and they fail; some of them also treat every file in `specs/` as v1/legacy.
**How to avoid:** Wave 0 task: pin the published set by the 10 stems in `tools/tests/golden/manifest.json` (or a constant list), not by directory glob. Golden itself is safe: the manifest is a fixed list and extra MP4s are only reported as `기준 목록 밖 … (판정 안 함)` [VERIFIED: tools/reelkit/golden.py:284-289].
**Warning signs:** green suite today, red right after the first promote.

### Pitfall 2: Rebuild erases human input / leaves stale approval
**What goes wrong:** BNDL-05 reruns regenerate `review.md`; an approval from before the rebuild would still "match" if only the MP4 hash was checked.
**How to avoid:** `record.json` separate and preserved; bundle deletes `approval.json`; approval hashes spec.src/caption.src/check/compliance too.

### Pitfall 3: Heuristic negation hides real violations
**What goes wrong:** "원금 보장되며 위험하지 않습니다" suppresses G-01 because of "않".
**How to avoid:** show every suppression in `review.md`; keep suppression windows clause-scoped; test adversarial strings (listed above) and keep expected outputs in the test file.

### Pitfall 4: Overfit measurement presented as detection rate
**What goes wrong:** report says 100% because rules were written looking at the corpus.
**How to avoid:** report tiers separately, add held-out set, print the in-sample caveat in the report.

### Pitfall 5: `\b`/`\w` and Korean
**What goes wrong:** Python `\b` does not separate Hangul particles from words (`씨가`), so boundary-based patterns misfire.
**How to avoid:** use `(?![가-힣])` / `(?<![가-힣])` as in P-02; never `\b` between Hangul.

### Pitfall 6: Review-time false positives blocking promote
**What goes wrong:** a 수정 필요 rule fires on a legitimate sentence and promote refuses with no override.
**How to avoid:** severity policy above; the only fix path is rewording or editing the rule (rules are data); say so in the refusal message.

### Pitfall 7: Draft folder in this container is not a fixture
`2026/reels/drafts/2026-11-08-pension-credit-limit/` exists here but `drafts/` is gitignored [VERIFIED: .gitignore:1 `2026/reels/drafts/`]; tests must build from `tools/tests/fixtures/draft-pension.src.json` + `draft-pension.caption.src.json` (existing, used by `test_draft_e2e.py`), not read that folder. Render tests need Chromium; keep them in the e2e file like Phase 2 did.

### Pitfall 8: ffmpeg quoting
`drawtext` `text=` and `%{expr\:n+1}` colons need escaping; build the filter string in Python and pass argv (no shell). Frame sequence names must be contiguous (`sc01..scNN`).

## Code Examples

### Cover crop audit (stdlib + ffmpeg; verified on the draft)
```python
# Source: executed in this session (scratchpad), constants from tools/reelkit/constants.py:5,13,14
import subprocess
W, H, BG = 1080, 1920, bytes.fromhex("DEE9E0")        # SAGE = "#DEE9E0"
CROP_TOP, CROP_BOTTOM, BAR_ROWS = 240, 1680, 14        # (1920-1440)/2 ; progress bar height

def cover_crop_violations(png_path, tol=0):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png_path), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    assert len(raw) == W * H * 3
    flat = BG * W
    def ink(y):
        row = raw[y * W * 3:(y + 1) * W * 3]
        return row != flat and (tol == 0 or max(abs(a - b) for a, b in zip(row, flat)) > tol)
    return [y for y in range(H) if ink(y) and not (y < BAR_ROWS or CROP_TOP <= y < CROP_BOTTOM)]
```

### No-overwrite publish
```python
# Source: stdlib docs os.link — raises FileExistsError if dst exists
import os, hashlib, shutil
def publish(src, dst, want_sha):
    part = dst.with_name("." + dst.name + ".part")
    shutil.copyfile(src, part)
    if hashlib.sha256(part.read_bytes()).hexdigest() != want_sha:
        part.unlink(); raise RuntimeError("복사본 지문 불일치")
    try:
        os.link(part, dst)          # never replaces an existing published file
    finally:
        part.unlink(missing_ok=True)
```

### Frame-sink hook (the only renderer change)
```python
# render.py:92 signature -> add `frame_sink=None`; at the final-state branch (render.py:122)
if st.k == len(st.lines):
    if frame_sink:
        frame_sink(st.scene, f)     # f = the PNG just written for this state
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Keyword blocklist only | Pattern + negation + requires-rules + visible suppression list | this phase design | Fewer false alarms without silent misses |
| 1:1 profile grid | 3:4 (1080×1440) center crop | reported across 2025–2026 guides (MEDIUM) | Cover text window is 1440 tall |
| FSS/KOFIA ad scrutiny | 2026-04 reports of an ad-improvement TF focusing on missing loss-risk notices, false/exaggerated wording, unsupported superlatives, wording that implies guaranteed profit/loss compensation; proposal expected 2026 Q3 | 2026-04 news | Matches rule categories; stay ready to change the rule file when guidance is published |

**Deprecated/outdated:** none relevant.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The six rule categories and the expression lists reflect common 금소법/보험업법-style ad-wording risks, derived from the user's own prohibited list (CONTEXT specifics), `house-style.md`, and news summaries — not from statute text or the 금융광고 가이드라인 원문 (unreachable) | Compliance Engine | Rule gaps or over-flagging; mitigated by "초안 규칙 — 준법 검토 전" labelling and the compliance owner review |
| A2 | `n` in the headline should count pattern-rule findings of both severities | Compliance Engine | Wording of COMP-03 could be read as 수정 필요 only; trivial to change (Open Question 1) |
| A3 | Profile grid is 3:4 center crop of a 9:16 cover | Instagram grid | Text could still be cropped on older clients; human checklist item remains |
| A4 | Surname list/exception list in P-02 is adequate for names | Seed rules | Some names missed or some honorific words flagged; P-02 is data and extendable |
| A5 | `drawtext` in the sandbox ffmpeg exists in future sessions (same image) | Contact sheet | If missing, sheet fails; doctor could check `ffmpeg -filters` for `drawtext`/`tile` |
| A6 | x264 output not needed to be deterministic because rebuild always invalidates approval | Approval | None expected |
| A7 | News items (FSS/KOFIA TF, 2026-04) are accurately summarized by the search tool; originals not opened | State of the Art | Only context; no rule depends on them |

## Open Questions

1. **What exactly is "위험 표현 n건"?** Recommendation: count pattern-rule findings (수정 필요 + expression-level 확인 필요), show 근거 누락/확인 필요 separately. Planner/user may prefer 수정 필요 only.
2. **Waiver for a false-positive 수정 필요 at promote?** D-16 gives none. Recommended v1: none (reword or edit the rule); revisit if it bites.
3. **Should `promote` be human-only?** Recommended: no TTY needed (gates are the approval record + hashes); user may want it human-only too.
4. **Held-out corpus authorship** — who writes ≥10 bad / ≥5 good without seeing the rules.
5. **Slot timestamp:** accept a small `slot --create` change to stamp `created_at`?
6. **`record.json` hardening** — only the deferred permission rule can stop Claude from editing it; user decision pending (CONTEXT Deferred).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | everything | ✓ | 3.13 | — |
| ffmpeg + `drawtext`, `tile` | contact sheet, cover audit | ✓ | 6.1.1 | Pillow sheet (installed 12.3.0, undeclared) |
| Playwright + Chromium | render, frame sink | ✓ (render ran, 14.8 s) | launcher fallback in `browser.launch` | `doctor.py` |
| Bundled Noto Sans KR Bold | sheet labels | ✓ | `tools/fonts/` | omit labels |
| Pillow | not required | ✓ (undeclared) | 12.3.0 | — |
| Primary Korean legal sites (law.go.kr, fss.or.kr) | rule substance | ✗ (not attempted at length per user instruction) | — | rules stay 초안; compliance owner review |

**Missing dependencies with no fallback:** none. **With fallback:** legal source access (process fallback = draft labelling).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest` (402 tests baseline) |
| Config file | none (`discover -s tools/tests`) |
| Quick run command | `python3 -m unittest tools.tests.test_compliance tools.tests.test_redteam tools.tests.test_stills tools.tests.test_approve -v` (run from repo root; adjust to the project's import style as existing tests do) |
| Full suite command | `python3 -m unittest discover -s tools/tests -p 'test_*.py'` and `python3 tools/golden.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01/02 | each seed rule hits its `examples.hit`, misses `examples.miss`; location strings correct | unit | `unittest test_compliance` | ❌ Wave 0 |
| COMP-03 | headline is one of two strings; no "통과"; no `제N조` anywhere | unit | same | ❌ Wave 0 |
| COMP-04 | published-10 수정 필요 = 0; seed recall/FP thresholds; report prints tiers | unit | `unittest test_redteam` | ❌ Wave 0 |
| COMP-05 | bad rules file → Korean error with rule id; edit data → behaviour changes with no code change | unit | `test_compliance` | ❌ Wave 0 |
| BNDL-02 | audit passes on clean cover, fails when ink drawn at y=100/1700 (synthetic PNG via ffmpeg) | unit | `test_stills` | ❌ Wave 0 |
| BNDL-03 | sheet has expected size for N scenes | e2e (ffmpeg only) | `test_stills` | ❌ Wave 0 |
| BNDL-01/05/07 | bundle on `draft-pension` fixtures: all artifacts exist, rerun purges approval, `bundle.json` seconds < 600 | e2e (Chromium) | `test_bundle` | ❌ Wave 0 |
| BNDL-06 | approve refuses non-TTY; promote refuses on 수정 필요, hash drift, existing target, bad slug; success links 4 files | unit/e2e in temp reels dir | `test_approve` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the relevant new test module
- **Per wave merge:** full suite + `python3 tools/golden.py`
- **Phase gate:** full suite green, golden PASS 10/10, `draft.py redteam` report captured in the phase VERIFICATION

### Wave 0 Gaps
- [ ] Replace the four `len(...) == 10` directory-glob assertions with a pinned list of the 10 published stems
- [ ] `tools/tests/redteam/corpus.json` (Appendix B) and `tools/data/compliance_rules.json` (Appendix A)
- [ ] New test modules listed above; reuse `tools/tests/fixtures/draft-pension.*.json`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (local CLI) | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (approval gate) | TTY + retype + `is_ai_name` + hash record; optional permission-deny rules (deferred) |
| V5 Input Validation | yes | slug/date validators, DIR must resolve under `drafts/`, strict rules-file loader, `json.load` only |
| V6 Cryptography | yes (integrity only) | `hashlib.sha256`; no custom crypto |
| V12 Files | yes | no-overwrite link, temp+replace, no symlink following for approve/promote sources (`os.path.realpath` containment) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via slug/DIR in promote | Tampering | `slot.check_slug`, containment check with `is_relative_to` |
| Overwrite of a published file | Tampering | preflight + `os.link` |
| File swapped between approve and promote | Tampering | sha256 recheck immediately before copy and on the copy |
| TOCTOU between preflight and link | Tampering | `FileExistsError` from `os.link` is the real guard |
| Regex DoS from user-edited rules | DoS | bounded quantifiers, small inputs; optional per-rule timing in `redteam` |
| Claude approving itself | Elevation | no TTY; residual pty bypass documented; deny-rule hardening deferred |
| Personal data in published output | Info disclosure | P-01/P-02 patterns; human checklist item |

## Sources

### Primary (HIGH confidence)
- Repo files read this session: `03-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `ROADMAP.md` §Phase 3, `02-0[1-4]-SUMMARY.md`, `02-REVIEW-FIX.md`, `tools/draft.py`, `tools/reelkit/{render,layout,timeline,constants,check,figures,slot,spec,caption,encode,golden}.py`, `tools/reel.py`, `tools/data/caption_config.json`, `.claude/skills/make-reel/SKILL.md` + `references/house-style.md`, the 10 `2026/reels/specs/*.json`, `.gitignore`.
- Executed in this session: prototype rule engine on 10 specs/caption/corpus; render + timing of the Phase 2 draft; cover grab and pixel audit; ffmpeg `select`/`tile`/`drawtext` sheet; Pillow sheet comparison.

### Secondary (MEDIUM confidence)
- WebSearch summaries (news.bizwatch.co.kr/article/market/2026/04/22/0042, dealsite.co.kr/articles/149202, imaeil.com/page/view/2026042314511296562, hwawoo.com newsletter 2025-09 PDF): FSS/KOFIA ad-improvement TF themes (loss-risk notice, false/exaggerated wording, unsupported superlatives, profit-guarantee/loss-compensation impressions); 2021 ad-regulation guideline requires internal review before ads. Statute/guideline text not seen.
- WebSearch summaries (hopperhq.com/blog/instagram-reel-size, help.hopperhq.com vertical grid, planoly.com vertical-grid guide, postfa.st cover safe zones): 3:4 grid, 1080×1440 center window.

### Tertiary (LOW confidence)
- Seed lists of company/ticker names and the surname whitelist are illustrative, from training knowledge.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; capabilities executed
- Architecture (bundle, stills, approval): HIGH for mechanics, MEDIUM for policy choices (open questions)
- Compliance rule substance: MEDIUM-LOW — heuristic, in-sample measurement, no primary legal text
- Pitfalls: HIGH for the repo-specific ones (test-count assertions, rebuild vs record, window bugs)

**Research date:** 2026-10-29
**Valid until:** 2026-11-28 for mechanics; rule substance should be re-validated whenever the FSS/KOFIA guideline update (reported for 2026 Q3) or the compliance owner's review lands.

---

## Appendix A: Seed `tools/data/compliance_rules.json` (measured prototype)

Measured result with this exact file: published-10 수정 필요 0 / 확인 필요 2; seed corpus 41/41 detected, 0/21 false positives (in-sample). Keep `status`/`version`/`as_of`; `examples` fields are recommended additions (not in the measured prototype).

```json
{
 "schema": 1,
 "version": "0.1",
 "status": "초안 규칙 — 준법 검토 전",
 "as_of": "2026-10-29",
 "macros": {"J": "(?:은|는|이|가|을|를|도|만|의|에|에는|으로|로|이라|라)?", "S": "\\s*"},
 "negators": "(?:않|아님|아니|아닙|아냐|안\\s*됩|안됩|안\\s*돼|못\\s*합|못\\s*해|수\\s*없|불가|지\\s*마|하지\\s*말|보장\\s*없|뜻이\\s*아|의미가\\s*아|오해|다는\\s*보장(?:은|이)?\\s*(?:어디에도\\s*)?(?:없|못|아니))",
 "mention_markers": "^['\"’”」』]*\\s*(?:이?라는|라고|이란|같은)\\s*(?:말|표현|문구|광고|문장|단어)",
 "compact_terms": ["원금보장", "수익보장", "이익보장", "확정수익", "확정이익", "무조건", "손실제로", "손실없", "무위험", "100%안전", "100%보장", "절대안전"],
 "rules": [
  {"id": "G-01", "category": "단정·보장", "severity": "수정 필요", "negatable": true, "pattern": "원금{J}{S}(?:100\\s*%\\s*)?(?:보장|보전|안전)", "reason": "원금 보장·보전으로 읽히는 단정 표현", "suggest": "원금 손실이 생길 수 있음을 함께 밝히세요 (예: '원금 손실 가능')"},
  {"id": "G-09", "category": "단정·보장", "severity": "수정 필요", "negatable": true, "pattern": "(?i)guarantee[ds]?|risk[- ]?free|no[- ]risk", "reason": "영문 보장·무위험 표현", "suggest": "한국어 광고 문구에서도 같은 기준으로 고치세요"},
  {"id": "G-02", "category": "단정·보장", "severity": "수정 필요", "negatable": true, "pattern": "(?:수익|이익|이자|수익률|배당){J}{S}(?:을|를)?{S}(?:100\\s*%\\s*)?(?:보장|확정|약속)|확정{S}(?:적\\s*)?(?:수익|이익|수익률)", "reason": "수익·이익을 확정하거나 보장하는 표현", "suggest": "'과거 평균일 뿐, 미래 수익을 보장하지 않아요' 또는 예시 가정으로 바꾸세요"},
  {"id": "G-03", "category": "단정·보장", "severity": "수정 필요", "negatable": true, "pattern": "무조건|절대로?{S}(?:손해|손실|안전|걱정|실패|망)|틀림없이|100\\s*%{S}(?:안전|확실|보장|성공|환급|가능|돌려|이득)|백\\s*프로|확실히{S}(?:오른|오릅|벌|받|이득|돌려)|100\\s*프로", "reason": "결과를 단정하는 표현 (무조건·절대·100%)", "suggest": "'조건에 따라 달라질 수 있어요'처럼 조건과 예외를 밝히세요"},
  {"id": "G-04", "category": "단정·보장", "severity": "수정 필요", "negatable": true, "pattern": "반드시{S}(?:오른|오릅|올라|받|돌려|환급|이득|유리|절세|벌|수익|성공)", "reason": "미래 결과를 단정하는 표현", "suggest": "'~할 수 있어요'로 바꾸고 근거·조건을 적으세요"},
  {"id": "G-05", "category": "단정·보장", "severity": "수정 필요", "negatable": true, "pattern": "(?:손실|손해|리스크|위험){J}{S}(?:이|가)?{S}(?:전혀\\s*|하나도\\s*)?없|(?:손실|손해){S}볼{S}(?:일|걱정|염려){S}없|무\\s*위험|(?:원금\\s*)?손실{S}걱정{S}없|위험{S}(?:하지|하진){S}않|(?:손실|손해|리스크|위험){J}{S}(?:제로|0\\s*%)", "reason": "위험이 없다고 하는 표현", "suggest": "투자·금융상품에는 손실 위험이 있다는 점을 밝히세요"},
  {"id": "G-06", "category": "단정·보장", "severity": "확인 필요", "negatable": true, "pattern": "고\\s*수익|초\\s*고\\s*수익|대박|수익{S}극대화|큰{S}수익|확정{S}금리|이자{S}폭탄", "reason": "수익 기대를 키우는 표현, 확정금리는 상품 조건 확인 필요", "suggest": "구체 조건·기간·세전/세후를 밝히거나 표현을 낮추세요"},
  {"id": "G-07", "category": "단정·보장", "severity": "확인 필요", "negatable": true, "pattern": "반드시", "except": ["반드시{S}(?:확인|상담|문의|비교|읽|알아|체크|점검|참고|전문가|세무사|확인해)"], "reason": "'반드시'가 결과·권유 단정으로 읽힐 수 있음", "suggest": "'~하는 편이 좋아요' 또는 조건을 붙이세요"},
  {"id": "T-01", "category": "세무 단정", "severity": "수정 필요", "negatable": true, "pattern": "(?:누구나|모두|전부|다){S}(?:세금{S})?(?:환급|공제|절세|면제)|(?:세금|세액){J}{S}(?:낼{S}필요{S}(?:가\\s*)?없|안{S}내|0\\s*원|면제|공짜)|탈세|세무조사{J}{S}(?:절대\\s*)?(?:안|걸리지)|세금{S}(?:피하|회피)|(?:무조건|반드시|100\\s*%){S}(?:절세|환급|공제|돌려)|절세{S}(?:확정|보장)", "reason": "세금 면제·환급을 단정하거나 탈세로 읽힐 수 있는 표현", "suggest": "'조건에 따라 달라질 수 있어요. 세무 판단은 세무사 확인'으로 바꾸세요"},
  {"id": "T-02", "category": "세무 단정", "severity": "수정 필요", "negatable": true, "pattern": "(?:세무사|세무|법률|법적){S}(?:판단|확인|상담){S}(?:없이|필요{S}없|불필요)|(?:합법|불법|위법|문제){J}{S}(?:이|가)?{S}(?:아닙|없습|없어요|입니다|이에요)|세금{S}(?:문제|걱정){S}(?:없|끝)|합법(?:이니까|이라|이므로|입니다|이에요|적이)", "reason": "세무·법률 판단을 단정하는 표현", "suggest": "판단 표현을 빼고 '일반 정보이며 세무사·전문가 확인 필요'로 바꾸세요"},
  {"id": "T-03", "category": "세무 단정", "severity": "확인 필요", "negatable": true, "pattern": "세금{S}(?:없이|0\\s*원)|비과세{S}(?:입니다|예요|이에요|돼요|됩니다|혜택)", "reason": "비과세·세금 없음은 한도·조건이 함께 있어야 함", "suggest": "한도·요건·기준 시점을 같은 장면이나 근거에 적으세요"},
  {"id": "S-01", "category": "상품 권유", "severity": "수정 필요", "negatable": true, "pattern": "(?:가입|투자|매수|구매|신청|납입|갈아타){S}(?:하세요|해{S}보세요|해보세요|하십시오|하셔야|해야{S}(?:합|해|돼|됩)|추천)|(?:사세요|담으세요|지금{S}(?:사|가입|담))", "reason": "특정 상품 가입·매수를 권하는 표현", "suggest": "일반 정보로만 쓰고 '내 상황에 맞는지 비교·상담해 보세요'로 바꾸세요"},
  {"id": "S-02", "category": "상품 권유", "severity": "수정 필요", "negatable": true, "pattern": "(?:펀드|ETF|주식|종목|보험|변액|연금보험|적금|예금|IRP|연금저축|채권|코인|비트코인){J}{S}(?:을|를)?{S}(?:추천|강추|1순위)|(?:추천|강추){S}(?:상품|종목|펀드|ETF|드립니다|드려요)|이것만{S}(?:사|가입|하)", "reason": "특정 상품·종목 추천", "suggest": "상품 이름과 추천 표현을 빼고 점검 기준(수수료·기간·세제)만 안내하세요"},
  {"id": "S-03", "category": "상품 권유", "severity": "확인 필요", "negatable": true, "pattern": "(?:삼성|미래에셋|신한|하나|우리|NH|농협|한화|교보|메리츠|흥국|현대|DB|카카오|토스|KB|키움){S}(?:생명|화재|증권|은행|자산운용|카드|손해보험|투자증권|페이|뱅크)|(?:TIGER|KODEX|ACE|SOL|ARIRANG|KBSTAR)\\s*[A-Za-z0-9가-힣&]+|테슬라|엔비디아|삼성전자", "reason": "특정 회사·상품·종목 이름 언급", "suggest": "권유가 아닌 일반 사례인지, 브랜드 관계 표시가 필요한지 확인하세요"},
  {"id": "S-04", "category": "상품 권유", "severity": "확인 필요", "negatable": true, "pattern": "놓치면{S}(?:손해|후회)|안{S}하면{S}(?:손해|바보|후회|큰일)|모르면{S}(?:손해|바보)|서두르세요|마감{S}임박|선착순", "reason": "불안·조급함을 부추겨 가입을 재촉하는 표현", "suggest": "재촉 표현을 빼고 판단 기준을 알려 주세요 (이벤트 안내는 조건을 분명히)"},
  {"id": "C-01", "category": "비교·비방", "severity": "수정 필요", "negatable": false, "pattern": "(?:업계|국내|대한민국|시중|전국){S}(?:최고|최초|유일|1\\s*위|1\\s*등|넘버원)|(?:최고|최상|1\\s*위|일등|제일){S}(?:의{S})?(?:수익|금리|이율|혜택|상품|안전|저렴)", "reason": "객관적 근거 없는 최상급·1위 표현 (허위·과장 광고 위험)", "suggest": "근거(조사 기관·기준일)를 밝히거나 '~한 편' 등으로 낮추세요"},
  {"id": "C-04", "category": "비교·비방", "severity": "확인 필요", "negatable": false, "pattern": "(?:가장|최대|최저|최고){S}(?:유리|좋|안전|저렴|높은|낮은|많이|빠른)", "reason": "근거 없는 최상급 가능성 (근거·기준이 같은 장면이나 basis 에 있는지 확인)", "suggest": "근거를 밝히거나 '~한 편'으로 낮추세요"},
  {"id": "G-08", "category": "단정·보장", "severity": "확인 필요", "negatable": true, "pattern": "걱정{J}{S}(?:이제\\s*)?(?:끝|제로|없이|안녕)|알아서{S}(?:불어|늘|쌓|벌)|저절로{S}(?:불|늘|쌓|벌)|가만히{S}(?:있|두)어?도", "reason": "암시적 보장으로 읽힐 수 있는 표현", "suggest": "결과가 보장되지 않음을 밝히거나 표현을 낮추세요"},
  {"id": "C-02", "category": "비교·비방", "severity": "확인 필요", "negatable": true, "pattern": "(?:훨씬|월등히|압도적으로|확실히){S}(?:더{S})?(?:낫|유리|좋|이득|높|많)|(?:[A-Za-z가-힣0-9]+){S}(?:보다){S}(?:무조건|항상){S}(?:낫|유리|좋)", "reason": "단점을 빼고 한쪽이 낫다고 하는 비교", "suggest": "비교 기준과 상대의 장점·조건도 함께 적으세요"},
  {"id": "C-03", "category": "비교·비방", "severity": "수정 필요", "negatable": true, "pattern": "(?:타사|경쟁사|다른{S}(?:회사|은행|증권사|보험사|금융사|설계사)){J}{S}(?:는|은|보다)?{S}(?:손해|위험|나쁘|형편없|사기|바가지|비싸|엉터리|못)|(?:은행|보험사|증권사|금융사|설계사|보험사){J}{S}(?:이|가|들이|들은)?{S}(?:절대\\s*)?(?:안{S}알려|알려주지{S}않|숨기|속이|속여|감추)|사기|바가지", "reason": "타사·업계를 깎아내리거나 속인다고 하는 표현", "suggest": "특정 회사·업권을 비난하지 말고 확인할 점만 안내하세요"},
  {"id": "P-01", "category": "개인정보", "severity": "수정 필요", "negatable": false, "pattern": "01[016789][-\\s.]?\\d{3,4}[-\\s.]?\\d{4}|\\b0(?:2|[3-6]\\d)[-\\s.]\\d{3,4}[-\\s.]\\d{4}\\b|\\b\\d{6}[-\\s]?[1-8]\\d{6}\\b|\\b\\d{4}[-\\s]\\d{4}[-\\s]\\d{4}[-\\s]\\d{4}\\b|\\b\\d{3,6}-\\d{2,6}-\\d{3,8}(?:-\\d{1,4})?\\b|[A-Za-z0-9._+-]+@[A-Za-z0-9-]+\\.[A-Za-z.]+", "reason": "전화번호·주민번호·카드/계좌번호·이메일 형태의 개인정보", "suggest": "삭제하세요. 연락 안내는 프로필 링크로만"},
  {"id": "P-02", "category": "개인정보", "severity": "수정 필요", "negatable": false, "pattern": "[가-힣][O○◯ㅇ*Xx]{1,2}\\s*(?:고객|님|씨)|(?<![가-힣])[김이박최정강조윤장임한오서신권황안송류홍전고문양손배백허유남심노][가-힣]{1,2}\\s*(?:님|씨)(?![가-힣])|(?<![가-힣])[가-힣]{2,3}{S}고객님", "except": ["어머님|아버님|할머님|할아버님|선생님|사장님|회원님|고객님께|저희|우리|이런|모든|여러분|부모님|어르신|이사님|대리님|부장님|과장님"], "reason": "고객 실명·가명 사례로 읽히는 표현", "suggest": "실제 고객 사례는 쓰지 말고 '가상 예시 A씨'처럼 가상임을 밝히세요"},
  {"id": "P-03", "category": "개인정보", "severity": "확인 필요", "negatable": false, "pattern": "실제{S}(?:고객|상담|가입자|사례)|(?:상담|고객){S}사례|후기{S}(?:공개|소개)|제{S}고객", "reason": "실제 고객·상담 사례를 암시하는 표현", "suggest": "공개용 가상 사례인지 확인하고 '가상 예시'를 표시하세요"},
  {"id": "R-01", "category": "근거 누락", "severity": "확인 필요", "type": "requires", "scope": "reel", "when": "(?:과거|지난|최근|역대|장기){S}(?:\\d+{S}년{S})?(?:평균|수익률|성과|상승|하락)|연평균|S&P{S}500.{0,12}평균|역대{S}최고", "must_have": "보장{S}아님|보장하지|보장되지|보장은{S}아|미래{S}(?:수익|결과)?.{0,6}(?:보장|다를|달라)|과거.{0,12}(?:일{S}뿐|참고)", "reason": "과거 성과를 말하는데 '미래 보장 아님' 고지가 없음", "suggest": "'과거 평균일 뿐, 미래 보장 아님'을 주의 장면에 추가하세요"},
  {"id": "R-02", "category": "근거 누락", "severity": "확인 필요", "type": "requires", "scope": "reel", "when_scene": "(?:세액공제|소득공제|공제율|세율|과세|비과세|양도세|증여세|상속세|종합소득세|이자소득세|배당소득세|소득세|연말정산|환급|지방소득세|연금소득세|퇴직소득세).*\\d|\\d.*(?:세액공제|소득공제|공제율|세율|과세|비과세|양도세|증여세|상속세|종합소득세|이자소득세|배당소득세|소득세|연말정산|환급|지방소득세|연금소득세|퇴직소득세)", "must_have": "세무사|세무{S}판단|전문가{S}(?:상담|확인)|국세청|홈택스", "reason": "세금 수치 장면이 있는데 세무사·전문가 확인 안내가 없음", "suggest": "주의 장면에 '<s>세무 판단은 세무사 확인</s>' 줄을 넣으세요"},
  {"id": "R-03", "category": "근거 누락", "severity": "확인 필요", "type": "requires", "scope": "reel", "when": "(?:연|수익률|이율|금리){S}\\d+(?:\\.\\d+)?{S}%|\\d+(?:\\.\\d+)?{S}%{S}(?:로|수익|굴|복리|적금|예금)", "must_have": "예시|가정|가상|기준|시뮬레이션", "reason": "수익률·금리 수치가 있는데 예시·가정·기준 표기가 없음", "suggest": "basis 나 해당 줄에 '예시'·'가정'을 표기하세요"},
  {"id": "R-04", "category": "근거 누락", "severity": "확인 필요", "type": "requires", "scope": "reel", "when": "(?:주식|ETF|펀드|투자|채권형|S&P{S}500|코인)", "must_have": "원금{S}손실|손실{S}(?:가능|위험|날|이{S}날)|투자{S}위험|변동", "reason": "투자 언급이 있는데 손실 가능성 고지가 없음", "suggest": "주의 장면에 '원금 손실 가능'을 넣으세요"},
  {"id": "R-05", "category": "근거 누락", "severity": "확인 필요", "type": "basis_required", "when": "\\d[\\d,.]*{S}(?:%|만{S}원|억|원|세|년|개월|달)", "must_have": "기준|예시|가정|가상|출처|공단|통계|국가데이터처|시행|\\d{4}년", "reason": "수치가 있는데 basis 에 기준·출처·예시 표기가 없음", "suggest": "basis 에 기준일과 출처 또는 '예시' 조건을 적으세요", "applies_to": ["reel"]}
 ]
}
```

## Appendix B: Seed `tools/tests/redteam/corpus.json` (fictional, public-safe)

```json
[
 {"id": "B01", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["이 적금은 원금 보장이에요"]},
 {"id": "B02", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["원금이 보장되니까", "안심하고 넣으세요"]},
 {"id": "B03", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["연 8% 확정 수익을", "받을 수 있어요"]},
 {"id": "B04", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["수익을 보장해 드립니다"]},
 {"id": "B05", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["무조건 오르는 종목"]},
 {"id": "B06", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["이 방법이면 절대 손해 볼 일 없어요"]},
 {"id": "B07", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["손실 없이 불리는 법"]},
 {"id": "B08", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["100% 안전한 투자"]},
 {"id": "B09", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["반드시 오릅니다"]},
 {"id": "B10", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["무위험 고수익 상품"]},
 {"id": "B11", "label": "bad", "category": "단정·보장", "tier": "obfuscated", "lines": ["원금보장형이라 마음 편해요"]},
 {"id": "B12", "label": "bad", "category": "단정·보장", "tier": "obfuscated", "lines": ["확정수익 연 7%"]},
 {"id": "B13", "label": "bad", "category": "세무 단정", "tier": "explicit", "lines": ["이렇게 하면 무조건 절세예요"]},
 {"id": "B14", "label": "bad", "category": "세무 단정", "tier": "explicit", "lines": ["누구나 세금 환급받아요"]},
 {"id": "B15", "label": "bad", "category": "세무 단정", "tier": "explicit", "lines": ["세금 낼 필요 없습니다"]},
 {"id": "B16", "label": "bad", "category": "세무 단정", "tier": "explicit", "lines": ["세무사 확인 없이", "신고해도 문제없습니다"]},
 {"id": "B17", "label": "bad", "category": "세무 단정", "tier": "explicit", "lines": ["세무조사는 절대 안 걸려요"]},
 {"id": "B18", "label": "bad", "category": "세무 단정", "tier": "explicit", "lines": ["합법이니까 걱정 말고 하세요"]},
 {"id": "B19", "label": "bad", "category": "상품 권유", "tier": "explicit", "lines": ["지금 연금보험 가입하세요"]},
 {"id": "B20", "label": "bad", "category": "상품 권유", "tier": "explicit", "lines": ["이 펀드를 추천합니다"]},
 {"id": "B21", "label": "bad", "category": "상품 권유", "tier": "explicit", "lines": ["ETF는 이것만 사세요"]},
 {"id": "B22", "label": "bad", "category": "상품 권유", "tier": "explicit", "lines": ["놓치면 후회하는 상품", "마감 임박!"], "expect_severity": "확인 필요"},
 {"id": "B23", "label": "bad", "category": "상품 권유", "tier": "explicit", "lines": ["강추 종목 3개 공개"]},
 {"id": "B24", "label": "bad", "category": "비교·비방", "tier": "explicit", "lines": ["업계 최고 수익률"]},
 {"id": "B25", "label": "bad", "category": "비교·비방", "tier": "explicit", "lines": ["국내 1위 금리 상품"]},
 {"id": "B26", "label": "bad", "category": "비교·비방", "tier": "explicit", "lines": ["타사는 수수료가 바가지예요"]},
 {"id": "B27", "label": "bad", "category": "비교·비방", "tier": "explicit", "lines": ["은행은 절대 안 알려주는", "진짜 이유"]},
 {"id": "B28", "label": "bad", "category": "비교·비방", "tier": "explicit", "lines": ["연금저축이 IRA보다", "훨씬 유리합니다"], "expect_severity": "확인 필요"},
 {"id": "B29", "label": "bad", "category": "개인정보", "tier": "explicit", "lines": ["상담은 010-1234-5678로"]},
 {"id": "B30", "label": "bad", "category": "개인정보", "tier": "explicit", "lines": ["문의 test.user@example.com"]},
 {"id": "B31", "label": "bad", "category": "개인정보", "tier": "explicit", "lines": ["입금 계좌 123-456-789012"]},
 {"id": "B32", "label": "bad", "category": "개인정보", "tier": "explicit", "lines": ["주민번호 900101-1234567 로 조회"]},
 {"id": "B33", "label": "bad", "category": "개인정보", "tier": "explicit", "lines": ["김철수 고객님 사례를 소개합니다"]},
 {"id": "B34", "label": "bad", "category": "개인정보", "tier": "explicit", "lines": ["박OO 씨는 3억을 모았습니다"]},
 {"id": "B35", "label": "bad", "category": "근거 누락", "tier": "explicit", "expect_severity": "확인 필요", "lines": ["과거 10년 평균 12%", "그대로 모으면 됩니다"], "basis": "예시 수익률"},
 {"id": "B36", "label": "bad", "category": "근거 누락", "tier": "explicit", "expect_severity": "확인 필요", "lines": ["연 5% 수익률로", "20년 모으면 2배"], "basis": ""},
 {"id": "B37", "label": "bad", "category": "근거 누락", "tier": "explicit", "expect_severity": "확인 필요", "lines": ["세액공제 16.5%", "돌려받아요"], "basis": "2026년 기준"},
 {"id": "B38", "label": "bad", "category": "근거 누락", "tier": "explicit", "expect_severity": "확인 필요", "lines": ["ETF에 투자하면", "연 7%가 쌓입니다"], "basis": "가정 수익률"},
 {"id": "B39", "label": "bad", "category": "단정·보장", "tier": "implicit", "lines": ["돈이 줄어들 걱정은", "이제 안녕이에요"], "expect_severity": "확인 필요"},
 {"id": "B40", "label": "bad", "category": "단정·보장", "tier": "implicit", "lines": ["이 상품이면 노후 걱정 끝"], "expect_severity": "확인 필요"},
 {"id": "B41", "label": "bad", "category": "단정·보장", "tier": "implicit", "lines": ["넣어두기만 하면", "알아서 불어납니다"], "expect_severity": "확인 필요"},
 {"id": "G01", "label": "good", "lines": ["원금 보장 아님", "원금 손실 가능"], "basis": "예시"},
 {"id": "G02", "label": "good", "lines": ["수익을 보장하지 않습니다"]},
 {"id": "G03", "label": "good", "lines": ["원금이 보장되지 않는", "상품도 있어요"]},
 {"id": "G04", "label": "good", "lines": ["무조건 절세는 아니에요", "조건을 확인하세요"]},
 {"id": "G05", "label": "good", "lines": ["'확정 수익'이라는 말은", "조심해서 보세요"]},
 {"id": "G06", "label": "good", "lines": ["반드시 세무사에게", "확인해 보세요"]},
 {"id": "G07", "label": "good", "lines": ["과거 평균일 뿐", "미래 보장 아님"], "basis": "예시"},
 {"id": "G08", "label": "good", "lines": ["월 100만 원을", "연 4%로 굴린다면 (예시)"], "basis": "가정 수익률 4% · 세금 미반영"},
 {"id": "G09", "label": "good", "lines": ["세액공제 한도는", "연 900만 원 기준", "<s>세무 판단은 세무사 확인</s>"], "basis": "2026년 기준 · 예시"},
 {"id": "G10", "label": "good", "lines": ["저장해두고", "내 숫자로", "계산해 보세요", "<s>프로필 링크 · 1분 노후자금 계산기</s>"], "basis": ""},
 {"id": "G11", "label": "good", "lines": ["IRP와 연금저축은", "무엇이 다를까?"], "basis": "일반 정보"},
 {"id": "G12", "label": "good", "lines": ["가입 전에는", "약관을 꼭 읽어 보세요"]},
 {"id": "G13", "label": "good", "lines": ["최대 한도는", "합산 연 900만 원"], "basis": "2026년 기준 · 예시"},
 {"id": "G14", "label": "good", "lines": ["물가가 더 오르면", "실질금리는 마이너스"], "basis": "예시 · 물가 가정"},
 {"id": "G15", "label": "good", "lines": ["가상 예시 A씨는", "월급 400만 원이라면"], "basis": "가상 예시"},
 {"id": "G16", "label": "good", "lines": ["일반 정보이며", "특정 상품 권유가 아닙니다"]},
 {"id": "G17", "label": "good", "lines": ["안전하게 모으려면?", "위험과 수익을 비교해 보세요"]},
 {"id": "G18", "label": "good", "lines": ["손실이 없다는 보장은", "어디에도 없어요"]},
 {"id": "G19", "label": "good", "lines": ["어머님 노후 준비", "어떻게 시작할까?"]},
 {"id": "G20", "label": "good", "lines": ["궁금한 점은", "고객센터에서 확인하세요"]},
 {"id": "G21", "label": "good", "lines": ["전체 고객이 아니라", "내 상황이 기준이에요"]}
]
```
