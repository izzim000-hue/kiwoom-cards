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

# --- 릴스 렌더 환경 고정 (Phase 1, 여러 번 실행해도 안전) ---
# tools/requirements.txt 의 playwright 고정 버전과 설치된 버전이 다를 때만 pip 로 맞춘다.
# 설치가 안 돼도 세션을 막지 않는다: 실패 안내는 stderr 로, 원인은 doctor 가 다시 알려 준다.
# 설치 없이 쓰는 경로(미리 깔린 Chromium + 이미 import 되는 Playwright)도 doctor 가 정상으로 본다.
# doctor 요약 한 줄이 이 블록의 유일한 stdout 출력이며 세션 컨텍스트에 들어간다.
PROJ="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
REQ="$PROJ/tools/requirements.txt"
if [ -f "$REQ" ]; then
  PW_PIN=$(sed -n 's/^playwright==//p' "$REQ" | head -n 1 || true)
  PW_CUR=$(python3 -c 'import importlib.metadata as m; print(m.version("playwright"))' 2>/dev/null || true)
  if [ -n "$PW_PIN" ] && [ "$PW_PIN" != "$PW_CUR" ]; then
    if ! python3 -m pip install --quiet --user --retries 1 --timeout 20 -r "$REQ" >&2; then
      echo "playwright $PW_PIN 설치 실패 — python3 tools/doctor.py 로 원인을 확인하세요" >&2
    fi
  fi
  python3 "$PROJ"/tools/doctor.py --quiet || true
fi
