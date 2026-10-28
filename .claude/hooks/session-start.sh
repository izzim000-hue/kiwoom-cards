#!/bin/bash
# 클라우드 세션 시작 시 GSD와 agent-browser 명령줄 도구를 설치한다.
# 이미 설치되어 있으면 건너뛴다. 설치 출력은 세션 컨텍스트에 섞이지 않도록 stderr로 보낸다.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# GSD: 전역(~/.claude)에 설치
if [ ! -d "$HOME/.claude/skills/gsd-help" ]; then
  npx --yes @opengsd/gsd-core@latest --claude --global >&2
fi

# agent-browser 명령줄 도구
if ! command -v agent-browser >/dev/null 2>&1; then
  npm install -g agent-browser >&2
fi

# Chrome 다운로드는 네트워크 정책에 막히므로 미리 설치된 Chromium을 쓰게 한다
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -x /opt/pw-browsers/chromium ]; then
  echo 'export AGENT_BROWSER_EXECUTABLE_PATH=/opt/pw-browsers/chromium' >> "$CLAUDE_ENV_FILE"
fi
