"""golden 판정 중 ffmpeg/ffprobe 오류가 한 릴스의 FAIL 로 보고되고 전체 실행을 중단하지 않는지 시험 (렌더 없음)."""
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
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

    def check_with_prefix(self, **patches):
        """frame_count 는 기준 값으로 통과시키고 patches 만 실패시킨다."""
        entry = first_reproducible()
        patches.setdefault("frame_count", mock.Mock(return_value=entry["frames"]))
        return self.check_with(**patches)

    def test_ffprobe_failure_is_fail_not_exception(self):
        err = subprocess.CalledProcessError(1, ["ffprobe"], stderr="boom")
        res = self.check_with(frame_count=mock.Mock(side_effect=err))
        self.assertEqual(res.verdict, golden.VERDICT_FAIL)
        self.assertTrue(any("CalledProcessError" in r for r in res.reasons), res.reasons)

    def test_empty_ffprobe_output_is_fail_not_exception(self):
        res = self.check_with(frame_count=mock.Mock(side_effect=ValueError("invalid literal for int()")))
        self.assertEqual(res.verdict, golden.VERDICT_FAIL)
        self.assertTrue(any("ValueError" in r for r in res.reasons), res.reasons)


class PartialDetailsReport(unittest.TestCase):
    """check_reel 이 판정 도중 끊겨 details 가 일부만 채워져도 보고서가 죽지 않는다 (CR-01)."""

    FULL = {"frames": (1, 1), "boundaries": 3, "boundary_mismatch": None,
            "cover_ms": 2950, "ssim_min": 0.99, "spec": "PASS"}
    ORDER = ["frames", "boundaries", "cover_ms", "ssim_min", "spec"]

    def test_every_prefix_of_details_formats(self):
        for n in range(len(self.ORDER) + 1):
            d = {k: self.FULL[k] for k in self.ORDER[:n]}
            if "boundaries" in d:
                d["boundary_mismatch"] = None
            res = golden.ReelResult("x", golden.VERDICT_FAIL, d, ["판정 중 오류: boom"])
            lines = golden.format_report([res], [])
            self.assertTrue(lines[0].startswith("FAIL  x"), lines)
            self.assertEqual(lines[-1], "golden: FAIL 0/1 (재현 불가 0)")

    def test_mid_judging_failure_goes_through_format_report(self):
        res = CheckReelErrors().check_with_prefix(stream_durations=mock.Mock(side_effect=RuntimeError("boom")))
        self.assertEqual(list(res.details), ["frames"])
        lines = golden.format_report([res], [])
        self.assertIn("RuntimeError: boom", "\n".join(lines))

    def test_main_reports_failing_reel_and_the_others(self):
        """한 릴스가 판정 중 실패해도 main 이 그 릴스의 FAIL 줄과 나머지 릴스의 결과를 모두 낸다 (트레이스백 없음)."""
        import concurrent.futures
        e1 = first_reproducible()
        e2 = dict(next(e for e in golden.load_manifest()["entries"]
                       if e["status"] == "reproducible" and e["stem"] != e1["stem"]),
                  mp4_sha256="0" * 64)
        fake = SimpleNamespace(out=Path("/nonexistent/out.mp4"), cover_ms=0, total=0.0, spec_checks=[])
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(golden, "load_manifest", return_value={"entries": [e1, e2]}), \
                mock.patch.object(golden.concurrent.futures, "ProcessPoolExecutor",
                                  concurrent.futures.ThreadPoolExecutor), \
                mock.patch("reelkit.render.render_reel", return_value=fake), \
                mock.patch.object(golden, "frame_count", return_value=e1["frames"]), \
                mock.patch.object(golden, "stream_durations", side_effect=ValueError("empty ffprobe output")), \
                redirect_stdout(out), redirect_stderr(err):
            code = golden.main([])
        text = out.getvalue()
        self.assertEqual(code, 1, text)
        self.assertEqual(err.getvalue(), "")
        self.assertNotIn("Traceback", text)
        lines = text.splitlines()
        self.assertTrue(any(l.startswith("FAIL") and e1["stem"] in l for l in lines), text)
        self.assertIn("판정 중 오류: ValueError: empty ffprobe output", text)
        self.assertTrue(any(l.startswith("FAIL") and e2["stem"] in l for l in lines), text)
        self.assertIn("게시된 영상이 바뀜", text)
        self.assertEqual(lines[-1], "golden: FAIL 0/2 (재현 불가 0)")


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
