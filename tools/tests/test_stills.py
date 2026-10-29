"""stills.py: 표지 크롭 검사와 장면 모음 이미지 (ffmpeg 만 사용, Chromium 없음, stdlib unittest 전용)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(TOOLS))

from reelkit import expand, figures, stills  # noqa: E402


def make_png(path, boxes=()):
    """1080x1920 배경 PNG 에 채운 상자(y1~y2, 가로 전체 중 일부)를 그린다."""
    vf = ",".join([f"drawbox=x=100:y={a}:w=800:h={b - a + 1}:color=black:t=fill" for a, b in boxes] or ["null"])
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xDEE9E0:s=1080x1920,format=rgb24",
                        "-vf", vf, "-frames:v", "1", str(path)], capture_output=True)
    assert r.returncode == 0, r.stderr


def size(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return r.stdout.strip()


class CropAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_constants(self):
        self.assertEqual((stills.CROP_TOP, stills.CROP_BOTTOM, stills.BAR_ROWS), (240, 1680, 14))

    def test_inside_box_and_progress_bar_are_clean(self):
        p = self.t / "ok.png"
        make_png(p, [(0, 13), (500, 600)])
        self.assertEqual(stills.ink_rows_outside_crop(p), [])
        self.assertEqual(stills.cover_crop_warnings(p), [])

    def test_box_above_window(self):
        p = self.t / "top.png"
        make_png(p, [(100, 150)])
        self.assertEqual(stills.ink_rows_outside_crop(p), list(range(100, 151)))
        w = stills.cover_crop_warnings(p)
        self.assertEqual(len(w), 1)
        self.assertIn("COVER_CROP", w[0])
        self.assertIn("y 100~150", w[0])

    def test_box_below_window(self):
        p = self.t / "bottom.png"
        make_png(p, [(1700, 1750)])
        w = stills.cover_crop_warnings(p)
        self.assertEqual(len(w), 1)
        self.assertIn("y 1700~1750", w[0])

    def test_two_ranges_two_warnings(self):
        p = self.t / "both.png"
        make_png(p, [(100, 120), (1800, 1810)])
        self.assertEqual(len(stills.cover_crop_warnings(p)), 2)

    def test_wrong_size_is_error(self):
        p = self.t / "small.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xDEE9E0:s=100x100",
                        "-frames:v", "1", str(p)], capture_output=True, check=True)
        with self.assertRaises(stills.StillsError):
            stills.ink_rows_outside_crop(p)


class Sheet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.frames = []
        for i in range(7):
            p = self.t / f"f{i}.png"
            make_png(p, [(500 + i * 20, 600 + i * 20)])
            self.frames.append(p)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seven_frames(self):
        out = stills.contact_sheet(self.frames, self.t / "sheet.png")
        self.assertEqual(size(out), "1500,1316")
        self.assertEqual(list(self.t.glob("*.part")), [])

    def test_three_frames(self):
        out = stills.contact_sheet(self.frames[:3], self.t / "three.png")
        self.assertEqual(size(out), "1128,664")

    def test_empty_is_error(self):
        with self.assertRaises(stills.StillsError):
            stills.contact_sheet([], self.t / "none.png")


class SceneTimes(unittest.TestCase):
    def test_pension_fixture(self):
        src = json.loads((FIX / "draft-pension.src.json").read_text(encoding="utf-8"))
        spec = expand.expand_source(src, figures.load_registry(figures.REGISTRY_PATH))
        times = stills.scene_times(spec)
        self.assertEqual(len(times), 7)
        from reelkit import timeline
        self.assertAlmostEqual(times[0], timeline.cover_ms(spec) / 1000, places=2)
        self.assertEqual(times, sorted(times))


if __name__ == "__main__":
    unittest.main()
