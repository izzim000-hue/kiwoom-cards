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
  # 공백·CR(CRLF 체크아웃)·뒤따르는 주석을 무시한다: doctor.read_pin 과 같은 규칙
  PW_PIN=$(sed -n 's/^[[:space:]]*playwright[[:space:]]*==[[:space:]]*\([^[:space:]#;]*\).*/\1/p' "$REQ" | head -n 1 || true)
  PW_CUR=$(python3 -c 'import importlib.metadata as m; print(m.version("playwright"))' 2>/dev/null || true)
  # 같은 컨테이너에서 실패한 설치를 세션마다 되풀이하지 않도록 실패 표시 파일을 남긴다
  PW_STAMP="${TMPDIR:-/tmp}/.reelkit-pw-install-failed-${PW_PIN:-none}"
  if [ -n "$PW_PIN" ] && [ "$PW_PIN" != "$PW_CUR" ] && [ ! -e "$PW_STAMP" ]; then
    # 가상환경에서는 --user 가 거부되므로 뺀다
    PIP_USER_FLAG="--user"
    if python3 -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)' 2>/dev/null; then
      PIP_USER_FLAG=""
    fi
    # shellcheck disable=SC2086
    if ! python3 -m pip install --quiet $PIP_USER_FLAG --retries 1 --timeout 20 -r "$REQ" >&2 &&
       ! PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --quiet $PIP_USER_FLAG --retries 1 --timeout 20 -r "$REQ" >&2; then
      echo "playwright $PW_PIN 설치 실패 — python3 tools/doctor.py 로 원인을 확인하세요 (이 컨테이너에서는 다시 시도하지 않음)" >&2
      : > "$PW_STAMP" 2>/dev/null || true
    fi
  fi
  python3 "$PROJ"/tools/doctor.py --quiet || true
fi
