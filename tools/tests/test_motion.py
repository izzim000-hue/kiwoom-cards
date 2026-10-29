"""basic 모션 시험: none 기준선 보호, 시간표, 트레이서 릴스 (stdlib unittest 전용)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
TOOLS = TESTS.parent
FIX = TESTS / "fixtures"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TESTS))

import none_guard  # noqa: E402
from reelkit import motion, render  # noqa: E402
from reelkit.spec import SpecError  # noqa: E402


def two_scene_spec(**extra):
    spec = {"scenes": [{"top": "AB", "lines": ["abcd", "efgh"]}, {"top": "", "lines": ["xyz"]}]}
    spec.update(extra)
    return spec


class NoneUnchanged(unittest.TestCase):
    """소스 수정 전 HEAD 에서 찍은 기준선과 none 새 배치 렌더를 항목별로 비교한다 (기준선이 없으면 실패)."""

    @classmethod
    def setUpClass(cls):
        if not none_guard.GOLDEN.is_file():
            raise AssertionError(f"none 기준선이 없음: {none_guard.GOLDEN}")
        cls.base = json.loads(none_guard.GOLDEN.read_text(encoding="utf-8"))

    def check_spec(self, name):
        want = self.base["specs"][name]
        got = none_guard.capture(FIX / name)
        for key in ("states", "total", "cover_ms", "warnings", "overlays", "new_inner_html", "argv"):
            self.assertEqual(got[key], want[key], f"{name}: {key} 가 기준선과 다름")

    def test_ok_layout(self):
        self.check_spec("ok-layout.json")

    def test_bad_layout(self):
        self.check_spec("bad-layout.json")


class Schedule(unittest.TestCase):
    def test_two_scene_numbers(self):
        s = motion.schedule(two_scene_spec())
        a, b = s.scenes
        # 장면 1: 줄 2개 -> settle = 0.12 + 0.30, 글자 2+4+4=10 -> read = 0.6 + 10/16, 끝 크로스페이드 0.3 포함
        self.assertAlmostEqual(a.settle, 0.42)
        self.assertAlmostEqual(a.read, 1.225)
        self.assertAlmostEqual(a.dur, 1.945)
        self.assertEqual(a.chars, 10)
        self.assertEqual(a.final_frame, 14)
        self.assertAlmostEqual(a.final_t, 14 / 30)
        # 장면 2(마지막): 줄 1개, 글자 3, 크로스페이드 없음
        self.assertAlmostEqual(b.start, 1.945)
        self.assertAlmostEqual(b.settle, 0.30)
        self.assertAlmostEqual(b.dur, 0.30 + 0.6 + 3 / 16)
        self.assertEqual(b.final_frame, 68)
        self.assertAlmostEqual(s.raw_total, 3.0325)
        self.assertEqual(s.nframes, 91)
        self.assertAlmostEqual(s.total, 91 / 30)

    def test_countup_raises_settle(self):
        ledger = [{"where": "scene 1 line 2", "countup": True}, {"where": "scene 1 line 1"}]
        s = motion.schedule(two_scene_spec(figures=ledger))
        self.assertEqual(s.scenes[0].countup_lines, (1,))
        self.assertAlmostEqual(s.scenes[0].settle, 1 * motion.STAGGER + motion.COUNT)
        self.assertEqual(s.scenes[1].countup_lines, ())

    def test_final_frame_between_settle_and_fade(self):
        for sc in motion.schedule(two_scene_spec()).scenes:
            self.assertGreater(sc.final_t, sc.start + sc.settle)
            self.assertLess(sc.final_t, sc.end - (motion.CROSS if sc.index == 0 else 0))

    def test_total_is_frame_multiple(self):
        s = motion.schedule(two_scene_spec())
        self.assertAlmostEqual(s.total * motion.FPS, round(s.total * motion.FPS))

    def test_resolve(self):
        self.assertEqual(motion.resolve({}), "none")
        self.assertEqual(motion.resolve({"motion": "basic"}), "basic")
        self.assertEqual(motion.resolve({"motion": "basic"}, "none"), "none")
        self.assertEqual(motion.resolve({}, "basic"), "basic")
        for bad in ("calm", {"preset": "calm"}, 3):
            with self.assertRaises(SpecError):
                motion.resolve({"motion": bad})
        with self.assertRaises(SpecError):
            motion.resolve({}, "calm")


def run_reel(*args):
    return subprocess.run([sys.executable, str(TOOLS / "reel.py"), *map(str, args)],
                          capture_output=True, text=True)


def ffprobe_packets(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


class TracerReel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-motion-"))
        spec = json.loads((FIX / "ok-layout.json").read_text(encoding="utf-8"))
        spec["motion"] = "basic"
        cls.spec_path = cls.tmp / "spec.json"
        cls.spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        cls.sched = motion.schedule(spec)
        cls.out = cls.tmp / "out.mp4"
        cls.proc = run_reel(cls.spec_path, cls.out, "--layout", "new")
        cls.sunk = []
        cls.lib_out = cls.tmp / "lib.mp4"
        render.render_reel(cls.spec_path, cls.lib_out, layout="new",
                           frame_sink=lambda i, p: cls.sunk.append((i, Path(p).read_bytes())))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_cli_exit_and_spec(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertIn("spec: PASS 9/9", self.proc.stderr)

    def test_duration_and_frames(self):
        line = self.proc.stdout.splitlines()[0]
        self.assertIn(f"duration={self.sched.total:.1f}s", line)
        self.assertEqual(ffprobe_packets(self.out), self.sched.nframes)

    def test_frame_sink_one_per_scene(self):
        self.assertEqual([i for i, _ in self.sunk], list(range(len(self.sched.scenes))))
        for _i, data in self.sunk:
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
