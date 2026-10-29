# Phase 4 API Coverage

No external API integration: local CLI and ffmpeg only; no music is searched or downloaded.

- Motion (line entry, cross-fade, count-up) is rendered locally by the pinned Playwright 1.63.0 driving the preinstalled Chromium on a file:// page whose http/https requests are aborted, and encoded by the system ffmpeg 6.1.1 through a PNG pipe.
- Background music is read only from a file path the user passes together with a license memo. `tools/reelkit/bgm.py` checks it with ffprobe, copies it into the gitignored draft folder and mixes it with an ffmpeg filter graph. No tool searches for, downloads, suggests or defaults to any music, and tests use ffmpeg-generated sine tones only.
- No LLM API, no paid service and no network call is added; Instagram stays the manual publish target, not an integrated API.
