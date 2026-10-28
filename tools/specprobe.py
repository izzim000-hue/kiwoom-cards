"""MP4 업로드 규격 검사기 (1080x1920, h264/yuv420p, 30fps, AAC, faststart, 길이)
사용: python3 tools/specprobe.py FILE.mp4 [...]
항목별 PASS/FAIL/WARN 과 실제 값을 출력하고, FAIL 이 하나라도 있으면 종료 코드 1.
측정할 수 없는 항목(읽을 수 없는 파일, ffprobe 없음)은 FAIL(측정 불가)이다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reelkit.specprobe import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
