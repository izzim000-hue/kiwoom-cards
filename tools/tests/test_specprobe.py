"""reelkit.specprobe 단위 시험: 샘플은 ffmpeg lavfi 로 만든다 (stdlib unittest 전용)."""
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from reelkit import golden, specprobe  # noqa: E402


def golden_mp4s():
    """게시된 11편의 MP4: 골든 기준표의 모든 항목."""
    return sorted(REPO / e["mp4"] for e in golden.load_manifest()["entries"])


ITEMS = ["video_stream", "codec", "size", "fps", "pix_fmt", "profile", "audio", "faststart", "duration"]


def box(kind, payload=b""):
    return struct.pack(">I4s", 8 + len(payload), kind) + payload


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


class Samples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-specprobe-"))
        t = cls.tmp
        cls.good = t / "good.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=0xDEE9E0:s=1080x1920:r=30:d=4",
               "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-movflags", "+faststart", str(cls.good))
        cls.nofast = t / "nofast.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=0xDEE9E0:s=1080x1920:r=30:d=1",
               "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.nofast))
        cls.bad = t / "bad.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=720x1280:r=24:d=1",
               "-c:v", "libx264", "-pix_fmt", "yuv444p", str(cls.bad))
        cls.text = t / "notvideo.mp4"
        cls.text.write_text("이것은 동영상이 아닙니다\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def statuses(self, path):
        return {c.item: c.status for c in specprobe.probe(path)}


class TopAtoms(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-atoms-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_64bit_and_to_eof_sizes(self):
        data = box(b"ftyp", b"isom" + b"\0" * 4)                      # 16 바이트
        data += struct.pack(">I4sQ", 1, b"moov", 16)                  # 64비트 크기 16
        data += struct.pack(">I4s", 0, b"mdat") + b"x" * 40           # 파일 끝까지
        p = self.tmp / "atoms.bin"
        p.write_bytes(data)
        self.assertEqual(specprobe.top_atoms(p), ["ftyp", "moov", "mdat"])

    def test_too_small_size_stops_without_raising(self):
        p = self.tmp / "tiny.bin"
        p.write_bytes(struct.pack(">I4s", 3, b"abcd") + b"\0" * 32)
        self.assertEqual(specprobe.top_atoms(p), ["abcd"])


class ProbeCommitted(Samples):
    def test_tax_deduction_has_nine_passing_checks(self):
        checks = specprobe.probe(REPO / "2026" / "reels" / "2026-10-26-tax-deduction.mp4")
        self.assertEqual([c.item for c in checks], ITEMS)
        self.assertEqual({c.status for c in checks}, {"PASS"})

    def test_no_committed_mp4_has_a_fail_item(self):
        files = golden_mp4s()
        self.assertEqual(len(files), 11)
        for f in files:
            with self.subTest(mp4=f.name):
                self.assertNotIn("FAIL", self.statuses(f).values())


class ProbeSamples(Samples):
    def test_good_sample_all_pass(self):
        self.assertEqual(set(self.statuses(self.good).values()), {"PASS"})

    def test_without_faststart_only_faststart_fails(self):
        st = self.statuses(self.nofast)
        self.assertEqual({k for k, v in st.items() if v == "FAIL"}, {"faststart"})
        self.assertEqual(st["duration"], "WARN")

    def test_bad_sample_fails_item_by_item(self):
        st = self.statuses(self.bad)
        failed = {k for k, v in st.items() if v == "FAIL"}
        for item in ("size", "fps", "pix_fmt", "profile", "audio", "faststart"):
            self.assertIn(item, failed)

    def test_unmeasurable_file_is_fail_with_reason_and_never_raises(self):
        checks = specprobe.probe(self.text)
        self.assertTrue(checks)
        self.assertNotIn("PASS", {c.status for c in checks})
        self.assertTrue(any("측정 불가" in c.actual for c in checks))

    def test_missing_file_is_fail(self):
        checks = specprobe.probe(self.tmp / "nope.mp4")
        self.assertNotIn("PASS", {c.status for c in checks})


class Cli(Samples):
    def run_cli(self, *paths):
        return subprocess.run([sys.executable, str(TOOLS / "specprobe.py"), *map(str, paths)],
                              capture_output=True, text=True)

    def test_good_exit_0_with_summary_line(self):
        r = self.run_cli(self.good)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"spec: PASS 9/9 — {self.good}", r.stdout)

    def test_text_file_exit_1(self):
        r = self.run_cli(self.text)
        self.assertEqual(r.returncode, 1)
        self.assertIn("측정 불가", r.stdout)

    def test_format_report_lines(self):
        lines = specprobe.format_report(self.bad, specprobe.probe(self.bad))
        self.assertTrue(lines[-1].startswith("spec: FAIL "))
        self.assertTrue(any(l.startswith("FAIL") and "size" in l for l in lines))


if __name__ == "__main__":
    unittest.main()
