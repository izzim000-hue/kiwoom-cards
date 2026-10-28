---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "`golden.format_report` raises `KeyError` on the partial results the WR-03 fix now produces"
  - id: WR-07
    severity: warning
    disposition: open
    title: "golden reports render-time environment failures as reel FAILs (exit 1), contradicting its own exit-code contract"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Failed pip install leaves no stamp when pip succeeds but the version stays wrong, so the hook reinstalls every session"
  - id: WR-09
    severity: warning
    disposition: open
    title: "golden pre-render file reads and the render import run outside the per-reel guard"
  - id: IN-01
    severity: info
    disposition: open
    title: "Legacy markup check does not require balanced tags — OPEN (unchanged)"
  - id: IN-02
    severity: info
    disposition: open
    title: "Spec loader reports a UTF-8 BOM as a JSON syntax error at line 1 column 1 — OPEN (unchanged)"
  - id: IN-03
    severity: info
    disposition: open
    title: "Chromium fallback path selection sorts lexicographically — OPEN (unchanged)"
  - id: IN-04
    severity: info
    disposition: open
    title: "`SMALL` font-size checks can never fire — OPEN (unchanged)"
  - id: IN-05
    severity: info
    disposition: open
    title: "Doctor's ffmpeg probe does not exercise the features the render uses — OPEN (unchanged)"
  - id: IN-06
    severity: info
    disposition: open
    title: "Hook installs unpinned `@opengsd/gsd-core@latest` and `agent-browser` under `set -e` — OPEN (unchanged)"
  - id: IN-07
    severity: info
    disposition: open
    title: "reel.py docstring and tools/README exit-code text omit the new exit-2 causes"
  - id: IN-08
    severity: info
    disposition: open
    title: "The failure stamp is a predictable file in a shared temp directory"
  - id: IN-09
    severity: info
    disposition: open
    title: "New tests do not cover the integrated failure path they were written for"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "ffmpeg / runtime failures escape `reel.py` as tracebacks with exit code 1"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "`reel.py` import guard reports any ImportError as \"playwright not installed\""
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "One failing reel aborts the entire golden run"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "`cover_ms` truncates a float and is off by 1 ms for 4-line and 10-line first scenes"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "SessionStart hook can run a slow failing pip install on every session"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "Doctor/hook subprocesses have no timeout"
open: 13
total: 19
recorded: 2026-10-28T21:52:01.264Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| WR-09 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |
| WR-01 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |
| WR-04 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |
| WR-05 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |
| WR-06 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
