"""게시된 릴스 10편의 golden 회귀: 원고를 legacy 배치로 다시 그려 게시된 MP4 와 비교한다.
사용: python3 tools/golden.py [--only STEM] [--jobs N] [--rebuild-manifest]   (4개 동시 렌더로 약 1분)
  (기본)             기준 목록(tools/tests/golden/manifest.json)의 모든 릴스를 판정하고 릴스마다 한 줄 보고
  --only STEM        그 이름만 판정 (여러 번 쓸 수 있음)
  --jobs N           동시에 렌더할 수 (기본 4)
  --rebuild-manifest 커밋된 MP4·원고에서 기준 목록만 다시 만든다 (렌더하지 않음, 보통 쓸 일 없음)
판정: 프레임 수, 비디오/오디오 길이, 장면 경계 프레임, cover_ms, 출력 한 줄, 프레임별 SSIM >= 0.98, 업로드 규격.
원고가 없는 2026-10-19-savings-interest 는 '재현 불가'로 보고하고 규격만 본다. 기준 목록에 없는 MP4 는 판정하지 않고 알린다.
마지막 줄: `golden: PASS 10/10 (재현 불가 1)`. 종료 코드 0 모두 통과, 1 릴스 FAIL 있음, 2 사용·환경 오류(playwright 미설치, Chromium·폰트·인코딩 실패).
렌더 결과는 임시 폴더에만 쓰고 2026/reels 아래는 건드리지 않는다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reelkit.golden import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
