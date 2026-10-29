"""PNG 시퀀스를 기존과 같은 ffmpeg concat + fps=30 경로로 MP4 인코딩한다.

장면 경계 프레임이 ffmpeg fps 필터의 반올림에 의존하므로 인자를 바꾸지 않는다.
"""
import os
import subprocess
import tempfile
from pathlib import Path

from . import bgm as bgm_mod


class EncodeError(RuntimeError):
    """ffmpeg 를 실행하지 못했거나 인코딩에 실패했다 (환경 오류). 메시지는 한국어."""


def _last_line(text):
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def encode_concat(files, total, out, work_dir, bgm=None):
    """files: [(png 경로, 지속 시간(초)), ...]. 셸을 쓰지 않고 인자 목록으로만 실행한다.

    bgm 이 None 이면 인자 목록이 예전과 똑같다(무음 트랙, golden 장면 경계 보호). 경로를 주면 무음 입력과 `-vf` 대신
    `-i <bgm>` 과 필터 그래프(반복·자르기, 1초 페이드, 음량 정규화)로 섞는다.

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
            if bgm is None:
                inputs = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-vf", "fps=30,format=yuv420p"]
            else:
                inputs = ["-i", str(bgm), "-filter_complex", "[0:v]fps=30,format=yuv420p[v];" + bgm_mod.filter_graph(total),
                          "-map", "[v]", "-map", "[a]"]
            r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(seq),
                                *inputs, "-c:v", "libx264", "-crf", "20", "-c:a", "aac",
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


class PipeEncoder:
    """PNG 프레임을 ffmpeg 표준입력으로 흘려 보내 MP4 를 만든다 (motion basic 경로).

    encode_concat 처럼 `<출력>.part.mp4` 에 먼저 쓰고 종료 코드 0 일 때만 출력 경로로 교체한다.
    stderr 는 임시 파일로 받아(읽지 않는 파이프로 인한 교착 방지) 실패 시 마지막 줄만 메시지에 쓴다.
    """

    def __init__(self, out, *, bgm=None, total=None):
        self.out = Path(out)
        self.tmp = self.out.with_name(self.out.name + ".part.mp4")
        self._err = tempfile.TemporaryFile()
        self._proc = None
        self._done = False
        if bgm is None:
            inputs = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-vf", "format=yuv420p"]
        else:
            if total is None:
                raise ValueError("bgm 을 섞으려면 영상 길이(total)가 필요함")
            inputs = ["-i", str(bgm), "-filter_complex", "[0:v]format=yuv420p[v];" + bgm_mod.filter_graph(total),
                      "-map", "[v]", "-map", "[a]"]
        argv = ["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", "30", "-c:v", "png",
                "-i", "-", *inputs,
                "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-shortest", "-movflags", "+faststart",
                str(self.tmp)]
        try:
            self._proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self._err)
        except OSError as e:
            self._err.close()
            raise EncodeError(f"ffmpeg 를 실행하지 못했습니다: {e}") from e

    def _stderr_tail(self):
        try:
            self._err.seek(0)
            return _last_line(self._err.read().decode("utf-8", "replace"))
        except (OSError, ValueError):
            return ""

    def write(self, png):
        try:
            self._proc.stdin.write(png)
        except (BrokenPipeError, OSError) as e:
            tail = self._stderr_tail()
            self.abort()
            raise EncodeError(f"ffmpeg 인코딩 실패 (입력 파이프 끊김): {tail or e}") from e

    def close(self):
        """입력을 닫고 ffmpeg 가 끝나길 기다린 뒤 성공했을 때만 출력 경로로 교체한다."""
        try:
            try:
                self._proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            rc = self._proc.wait()
            if rc != 0:
                raise EncodeError(f"ffmpeg 인코딩 실패 (종료 코드 {rc}): {self._stderr_tail() or '오류 메시지 없음'}")
            try:
                os.replace(self.tmp, self.out)
            except OSError as e:
                raise EncodeError(f"출력 파일을 쓸 수 없습니다: {self.out} ({e.strerror or e})") from e
            self._done = True
        finally:
            self._cleanup()

    def abort(self):
        if self._proc is not None and self._proc.poll() is None:
            self._proc.kill()
        if self._proc is not None:
            try:
                self._proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            self._proc.wait()
        self._cleanup()

    def _cleanup(self):
        try:
            self._err.close()
        except OSError:
            pass
        if not self._done:
            try:
                self.tmp.unlink()
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.abort()
        return False
