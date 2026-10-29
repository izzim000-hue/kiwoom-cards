# Phase 2 API Coverage

No external API integration: local CLI and in-session generation only; Instagram is the manual publish target, not an integrated API.

- Draft text, captions and hashtags are written by Claude inside the Claude Code session (no LLM API key, no paid service).
- `tools/draft.py` (slot, convert, figures, expand, check, caption) and `tools/reel.py` are local Python stdlib + Playwright/ffmpeg tools from Phase 1.
- Instagram caption/hashtag limits (2,200 chars, at most 5 hashtags) are local validation rules; nothing is posted or called.
- Tax and statistics sources (law.go.kr, nts.go.kr, 국가데이터처 and others) are not called by any tool; figures are added to `tools/data/figures.json` as 미확인 and confirmed by a human.
