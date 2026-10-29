# Phase 3 API Coverage

No external API integration: local CLI and in-session generation only.

- Reel and caption wording is written by Claude inside the Claude Code session (no LLM API key, no paid service). The 금소법 expression check is a local stdlib regex engine over `tools/data/compliance_rules.json`; the AI semantic check is v2 (COMP-V2-01).
- `tools/draft.py` (bundle, compliance, redteam, approve, promote) and `tools/reel.py` run locally with Python stdlib, the pinned Playwright + preinstalled Chromium, and ffmpeg 6.1.1 (cover crop audit, scene sheet).
- `promote` copies files inside the repository working tree only; it never runs git and never posts anywhere. Instagram stays the manual publish target, not an integrated API.
- Legal sources (금소법 text, 금융광고 가이드라인, law.go.kr, fss.or.kr) are not called by any tool; rules stay marked 초안 규칙 — 준법 검토 전.
