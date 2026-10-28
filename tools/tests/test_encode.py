"""encode_concat 와 reel.py 종료 코드 계약 시험: ffmpeg/런타임 실패는 환경 오류(2), 기존 MP4 는 보존 (stdlib unittest 전용)."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import reel  # noqa: E402
from reelkit.encode import EncodeError, encode_concat  # noqa: E402


def make_png(path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xDEE9E0:s=108x192:d=1",
                    "-frames:v", "1", str(path)], check=True)


class EncodeConcat(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-encode-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.png = self.tmp / "a.png"
        make_png(self.png)
        self.files = [(str(self.png), 1.0)]

    def leftovers(self):
        return sorted(p.name for p in self.tmp.glob("*.part.mp4"))

    def test_success_writes_output_and_no_part_file(self):
        out = self.tmp / "out.mp4"
        encode_concat(self.files, 1.0, out, self.tmp)
        self.assertGreater(out.stat().st_size, 0)
        self.assertEqual(self.leftovers(), [])

    def test_failed_encode_keeps_existing_output(self):
        out = self.tmp / "out.mp4"
        out.write_bytes(b"GOOD-MP4")
        bad = [(str(self.tmp / "missing.png"), 1.0)]
        with self.assertRaises(EncodeError) as cm:
            encode_concat(bad, 1.0, out, self.tmp)
        self.assertEqual(out.read_bytes(), b"GOOD-MP4")
        self.assertEqual(self.leftovers(), [])
        self.assertIn("ffmpeg", str(cm.exception))

    def test_missing_ffmpeg_is_encode_error(self):
        with mock.patch.dict(os.environ, {"PATH": str(self.tmp)}):
            with self.assertRaises(EncodeError):
                encode_concat(self.files, 1.0, self.tmp / "out.mp4", self.tmp)

    def test_output_is_directory_is_encode_error(self):
        out = self.tmp / "outdir"
        out.mkdir()
        with self.assertRaises(EncodeError):
            encode_concat(self.files, 1.0, out, self.tmp)
        self.assertTrue(out.is_dir())
        self.assertEqual(self.leftovers(), [])


class CliExitCodes(unittest.TestCase):
    def run_main(self, exc):
        err = io.StringIO()
        with mock.patch.object(reel, "render_reel", side_effect=exc), redirect_stderr(err):
            code = reel.main(["spec.json", "out.mp4"])
        return code, err.getvalue()

    def test_encode_error_is_environment_error(self):
        code, msg = self.run_main(EncodeError("ffmpeg 인코딩 실패"))
        self.assertEqual(code, 2)
        self.assertIn("렌더 환경 오류", msg)

    def test_oserror_is_environment_error(self):
        code, msg = self.run_main(FileNotFoundError("ffprobe"))
        self.assertEqual(code, 2)
        self.assertIn("렌더 환경 오류", msg)

    def test_subprocess_error_is_environment_error(self):
        code, _ = self.run_main(subprocess.CalledProcessError(1, ["ffmpeg"]))
        self.assertEqual(code, 2)

    def test_playwright_error_is_environment_error(self):
        from playwright.sync_api import Error
        code, _ = self.run_main(Error("Target closed"))
        self.assertEqual(code, 2)

    def test_missing_playwright_is_exit_2_with_install_hint(self):
        code, msg = self.run_main(ModuleNotFoundError("No module named 'playwright'", name="playwright"))
        self.assertEqual(code, 2)
        self.assertIn("playwright 미설치", msg)

    def test_internal_import_bug_is_not_reported_as_missing_playwright(self):
        with self.assertRaises(ImportError):
            self.run_main(ImportError("cannot import name 'x' from 'reelkit.layout'", name="reelkit.layout"))

    def test_spec_error_stays_exit_1(self):
        code, msg = self.run_main(reel.SpecError("scenes: 비어 있음"))
        self.assertEqual(code, 1)
        self.assertIn("원고 오류", msg)


if __name__ == "__main__":
    unittest.main()
