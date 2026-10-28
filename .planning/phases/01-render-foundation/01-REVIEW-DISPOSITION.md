---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "ffmpeg / runtime failures escape `reel.py` as tracebacks with exit code 1"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`reel.py` import guard reports any ImportError as \"playwright not installed\""
  - id: WR-03
    severity: warning
    disposition: open
    title: "One failing reel aborts the entire golden run"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`cover_ms` truncates a float and is off by 1 ms for 4-line and 10-line first scenes"
  - id: WR-05
    severity: warning
    disposition: open
    title: "SessionStart hook can run a slow failing pip install on every session"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Doctor/hook subprocesses have no timeout"
  - id: IN-01
    severity: info
    disposition: open
    title: "Legacy markup check does not require balanced tags"
  - id: IN-02
    severity: info
    disposition: open
    title: "Spec loader reports a UTF-8 BOM as a JSON syntax error at line 1 column 1"
  - id: IN-03
    severity: info
    disposition: open
    title: "Chromium fallback path selection sorts lexicographically"
  - id: IN-04
    severity: info
    disposition: open
    title: "`SMALL` font-size checks can never fire"
  - id: IN-05
    severity: info
    disposition: open
    title: "Doctor's ffmpeg probe does not exercise the features the render uses"
  - id: IN-06
    severity: info
    disposition: open
    title: "Hook installs unpinned `@opengsd/gsd-core@latest` and `agent-browser`"
open: 12
total: 12
recorded: 2026-10-28T21:28:13.840Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
