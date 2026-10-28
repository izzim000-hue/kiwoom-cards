---
phase: "1"
slug: "render-foundation"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-28"
---

# Phase 1 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| spec JSON -> HTML in a file:// page | spec strings (Claude-written from Phase 2 on) are inserted into a page that can read local files | public reel copy (no customer data) |
| PyPI -> user site-packages / every new session | `pip install --user playwright==1.63.0`, also run by the SessionStart hook | third-party code |
| raw.githubusercontent.com -> tools/fonts/ | font binaries downloaded once from upstream | OFL font files |
| renderer -> ffmpeg subprocess | user-chosen output path passed as an argument | file paths, public frames |
| MP4 file -> specprobe parser | probe reads arbitrary user-supplied files | local files |
| hook stdout -> Claude session context | hook output is read by the model | version summary line |
| golden suite -> published reels | suite reads the canonical published MP4s/specs | published public files |
| working tree -> git | drafts and render intermediates could be committed | unreviewed draft content |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Information disclosure | browser.open_page | medium | mitigate | `page.route(^https?://)` aborts all requests (`tools/reelkit/browser.py:64`) | closed |
| T-01-02 | Tampering | tools/fonts/*.otf | medium | mitigate | `constants.FONT_SHA256` pinned, checked by doctor (`tools/reelkit/doctor.py:100`); digests in `tools/fonts/README.md` | closed |
| T-01-03 | Tampering | encode | low | mitigate | `subprocess.run` with a list, no shell (`tools/reelkit/encode.py:32`) | closed |
| T-01-04 | Repudiation / reliability | font check in render_reel | high | mitigate | FontFace status + CDP `isCustomFont` probe raises `FontLoadError` -> exit 2 (`browser.py:14,118`, `render.py:39`) | closed |
| T-01-05 | Information disclosure | mkdtemp work dir | low | accept | public frames only; removed with `shutil.rmtree` (`render.py:107,144`) | closed |
| T-01-SC | Tampering | playwright==1.63.0 install | high | mitigate | exact pin in `tools/requirements.txt`, `--user`, `playwright install` never called; human legitimacy checkpoint in Plan 01 | closed |
| T-01-18 | Tampering | legacy raw insertion | medium | mitigate | four-tag allowlist (`spec.py:10,59`) checked before work dir/Chromium (`render.py:96,154`) | closed |
| T-01-19 | Denial of service | load_spec | low | mitigate | malformed input -> `SpecError` (`spec.py:13`), exit 1, no traceback | closed |
| T-01-20 | Information disclosure | .gitignore | low | mitigate | `2026/reels/drafts/` and intermediates ignored (`.gitignore:1`) | closed |
| T-01-07 | Tampering / Information disclosure | layout.new_inner_html | medium | mitigate | `html.escape` on every spec string, four tags restored (`layout.py:34`) | closed |
| T-01-08 | Denial of service | huge specs | low | accept | local single-user tool, no network exposure | closed |
| T-01-09 | Tampering | specprobe atom walk | low | mitigate | loop bounded, breaks on size < 8 (`specprobe.py:38,45`) | closed |
| T-01-10 | Repudiation | specprobe reporting | medium | mitigate | unmeasurable -> FAIL "측정 불가" (`specprobe.py:69`, `tests/test_specprobe.py:107`) | closed |
| T-01-11 | Information disclosure | overlay PNG next to output | low | accept | public frame only; drafts/ gitignored | closed |
| T-01-12 | Elevation of privilege / Tampering | hook pip install | high | mitigate | install only on pin mismatch, `--user` (`session-start.sh:31-47`), no browser download, no `curl \| sh` | closed |
| T-01-13 | Denial of service | hook under `set -euo pipefail` | medium | mitigate | `if !` guard, `--retries 1 --timeout 20`, doctor `\|\| true` (`session-start.sh:46-59`) | closed |
| T-01-14 | Tampering | golden manifest | medium | mitigate | built from committed files, sha256 rechecked, `SSIM_MIN = 0.98` single constant (`golden.py:42,128,142`) | closed |
| T-01-15 | Tampering | golden renders | medium | mitigate | renders in `mkdtemp` (`golden.py:219`); `test_zz_published_reels_untouched` (`tests/test_golden.py:192`) | closed |
| T-01-16 | Information disclosure | hook stdout | low | accept | one version summary line, no secrets | closed |
| T-01-17 | Tampering | doctor --fonts-dir | low | accept | local test aid, read-only | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-05 | Temp render dir holds public reel frames only and is deleted after encode | plan-time threat model (Plan 01) | 2026-10-28 |
| AR-02 | T-01-08 | Oversized specs only slow a local single-user render; no network exposure | plan-time threat model (Plan 03) | 2026-10-28 |
| AR-03 | T-01-11 | Overlay PNG is a public frame; drafts/ is gitignored | plan-time threat model (Plan 03) | 2026-10-28 |
| AR-04 | T-01-16 | Hook prints versions only | plan-time threat model (Plan 04) | 2026-10-28 |
| AR-05 | T-01-17 | `--fonts-dir` is a read-only local test aid | plan-time threat model (Plan 04) | 2026-10-28 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-28 | 20 | 20 | 0 | gsd-secure-phase (L1 grep evidence, short-circuit: register authored at plan time, ASVS 1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-28
