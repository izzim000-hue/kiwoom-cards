"""PNG 시퀀스를 기존과 같은 ffmpeg concat + fps=30 경로로 MP4 인코딩한다.

장면 경계 프레임이 ffmpeg fps 필터의 반올림에 의존하므로 인자를 바꾸지 않는다.
"""
import os
import subprocess
from pathlib import Path


class EncodeError(RuntimeError):
    """ffmpeg 를 실행하지 못했거나 인코딩에 실패했다 (환경 오류). 메시지는 한국어."""


def _last_line(text):
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def encode_concat(files, total, out, work_dir):
    """files: [(png 경로, 지속 시간(초)), ...]. 셸을 쓰지 않고 인자 목록으로만 실행한다.

    임시 파일(`<출력>.part.mp4`)에 먼저 쓰고 성공했을 때만 출력 경로로 교체한다.
    그래서 인코딩이 중간에 실패해도 이미 있던 MP4 는 잘리거나 지워지지 않는다.
    """
    out = Path(out)
    seq = Path(work_dir) / "seq.txt"
    seq.write_text("".join(f"file '{f}'\nduration {du}\n" for f, du in files)
                   + f"file '{files[-1][0]}'\n")
    tmp = out.with_name(out.name + ".part.mp4")
    try:
        try:
            r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(seq),
                                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                                "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", "-c:a", "aac",
                                "-shortest", "-t", f"{total:.2f}", "-movflags", "+faststart", str(tmp)],
                               capture_output=True, text=True)
        except OSError as e:  # ffmpeg 없음(FileNotFoundError), 실행 권한 없음 등
            raise EncodeError(f"ffmpeg 를 실행하지 못했습니다: {e}") from e
        if r.returncode != 0:
            raise EncodeError(f"ffmpeg 인코딩 실패 (종료 코드 {r.returncode}): "
                              f"{_last_line(r.stderr) or '오류 메시지 없음'}")
        try:
            os.replace(tmp, out)
        except OSError as e:
            raise EncodeError(f"출력 파일을 쓸 수 없습니다: {out} ({e.strerror or e})") from e
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
