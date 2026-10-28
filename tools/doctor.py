"""릴스 렌더 환경 점검: Playwright 버전, Chromium, 번들 폰트(Noto Sans KR 400/700/900), ffmpeg, ffprobe.
사용: python3 tools/doctor.py [--quiet | --json] [--fonts-dir DIR]
  (기본)      점검 여섯 줄 + 요약 한 줄
  --quiet     요약 한 줄만 stdout (실패하면 자세한 줄은 stderr). 세션 시작 훅이 이 형태로 부른다
  --json      {"ok", "checks", "summary", "playwright", "launch"} 를 JSON 으로 출력
  --fonts-dir 시험용 폰트 폴더 (기본 tools/fonts)
종료 코드: 0 실패 없음(경고는 허용), 1 실패 있음. 실패 줄에 원인과 해결 방법이 한국어로 나온다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reelkit.doctor import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
