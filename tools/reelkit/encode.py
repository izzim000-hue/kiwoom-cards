"""PNG 시퀀스를 기존과 같은 ffmpeg concat + fps=30 경로로 MP4 인코딩한다.

장면 경계 프레임이 ffmpeg fps 필터의 반올림에 의존하므로 인자를 바꾸지 않는다.
"""
import subprocess
from pathlib import Path


def encode_concat(files, total, out, work_dir):
    """files: [(png 경로, 지속 시간(초)), ...]. 셸을 쓰지 않고 인자 목록으로만 실행한다."""
    seq = Path(work_dir) / "seq.txt"
    seq.write_text("".join(f"file '{f}'\nduration {du}\n" for f, du in files)
                   + f"file '{files[-1][0]}'\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(seq),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", "-c:a", "aac",
                    "-shortest", "-t", f"{total:.2f}", "-movflags", "+faststart", str(out)], check=True)
