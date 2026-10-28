"""golden 판정 중 ffmpeg/ffprobe 오류가 한 릴스의 FAIL 로 보고되고 전체 실행을 중단하지 않는지 시험 (렌더 없음)."""
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from reelkit import golden  # noqa: E402


def first_reproducible():
    return next(e for e in golden.load_manifest()["entries"] if e["status"] == "reproducible")


class CheckReelErrors(unittest.TestCase):
    def check_with(self, **patches):
        fake = SimpleNamespace(out=Path("/nonexistent/out.mp4"), cover_ms=0, total=0.0, spec_checks=[])
        with mock.patch("reelkit.render.render_reel", return_value=fake):
            with mock.patch.multiple(golden, **patches):
                return golden.check_reel(first_reproducible())

    def test_ffprobe_failure_is_fail_not_exception(self):
        err = subprocess.CalledProcessError(1, ["ffprobe"], stderr="boom")
        res = self.check_with(frame_count=mock.Mock(side_effect=err))
        self.assertEqual(res.verdict, golden.VERDICT_FAIL)
        self.assertTrue(any("CalledProcessError" in r for r in res.reasons), res.reasons)

    def test_empty_ffprobe_output_is_fail_not_exception(self):
        res = self.check_with(frame_count=mock.Mock(side_effect=ValueError("invalid literal for int()")))
        self.assertEqual(res.verdict, golden.VERDICT_FAIL)
        self.assertTrue(any("ValueError" in r for r in res.reasons), res.reasons)


class MainExitCodes(unittest.TestCase):
    def run_main(self, exc):
        err = io.StringIO()
        with mock.patch.object(golden, "run", side_effect=exc), redirect_stderr(err):
            return golden.main([]), err.getvalue()

    def test_subprocess_error_is_environment_error(self):
        code, msg = self.run_main(subprocess.CalledProcessError(1, ["ffmpeg"]))
        self.assertEqual(code, 2)
        self.assertIn("golden 환경 오류", msg)

    def test_broken_pool_is_environment_error(self):
        import concurrent.futures
        code, _ = self.run_main(concurrent.futures.BrokenExecutor("worker died"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
