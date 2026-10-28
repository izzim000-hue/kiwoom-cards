"""새 배치(layout.py)·측정 경고·오버레이·--strict 시험 (stdlib unittest 전용, 픽셀은 ffmpeg 로 읽는다)."""
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(TOOLS))

from reelkit import constants, layout, render  # noqa: E402

LT, GT, AMP = chr(60), chr(62), chr(38)
WARN_RE = re.compile(r"scene \d+ line (\d+|top|basis|account): [A-Z_]+ \(")


def el(n=1, l=100, r=500, t=500, b=600, fs=100, text="x"):
    return {"n": n, "l": l, "r": r, "t": t, "b": b, "fs": fs, "text": text}


def measure(**over):
    m = {"top": el(fs=50, t=420, b=480), "lines": [el()], "basis": el(fs=36, t=700, b=740),
         "acct": el(fs=36, t=780, b=820)}
    m.update(over)
    return m


def kinds(ws):
    return [w.kind for w in ws]


def pixel(path, x, y, t=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(t)] if t is not None else []) + [
        "-i", str(path), "-frames:v", "1", "-vf", f"format=rgb24,crop=1:1:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return tuple(out[:3])


def png_size(path):
    head = Path(path).read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n", "PNG 시그니처가 아님"
    return struct.unpack(">II", head[16:24])


class EvaluateLayout(unittest.TestCase):
    def test_clean_measurement_has_no_warning(self):
        self.assertEqual(layout.evaluate_layout(measure(), 1), [])

    def test_wrap(self):
        ws = layout.evaluate_layout(measure(lines=[el(), el(n=2)]), 3)
        self.assertEqual(kinds(ws), ["WRAP"])
        self.assertEqual((ws[0].scene, ws[0].line, ws[0].value), (3, "2", "2 lines"))

    def test_right_edge(self):
        ws = layout.evaluate_layout(measure(lines=[el(r=960)]), 1)
        self.assertEqual(kinds(ws), ["RIGHT"])
        self.assertEqual(ws[0].line, "1")

    def test_top_intrusion(self):
        ws = layout.evaluate_layout(measure(top=el(fs=50, t=200, b=260)), 1)
        self.assertEqual((kinds(ws), ws[0].line), (["TOP"], "top"))

    def test_bottom_warn_line(self):
        ws = layout.evaluate_layout(measure(lines=[el(t=1200, b=1300)]), 1)
        self.assertEqual(kinds(ws), ["WARN_Y"])

    def test_ui_zone_is_not_also_warn_y(self):
        ws = layout.evaluate_layout(measure(acct=el(fs=36, t=1450, b=1500)), 1)
        self.assertEqual((kinds(ws), ws[0].line), (["UI_ZONE"], "account"))

    def test_basis_over_two_lines(self):
        ws = layout.evaluate_layout(measure(basis=el(n=3, fs=36, t=700, b=800)), 1)
        self.assertEqual((kinds(ws), ws[0].line), (["BASIS_LINES"], "basis"))
        self.assertEqual(ws[0].value, "3 lines > 2")

    def test_small_basis_and_account(self):
        ws = layout.evaluate_layout(measure(basis=el(fs=30, t=700, b=740), acct=el(fs=30, t=780, b=820)), 1)
        self.assertEqual(kinds(ws), ["SMALL", "SMALL"])
        self.assertEqual(ws[0].value, "30px < 36px")

    def test_missing_basis_is_allowed(self):
        self.assertEqual(layout.evaluate_layout(measure(basis=None), 1), [])

    def test_str_format(self):
        w = layout.LayoutWarning(2, "basis", "BASIS_LINES", "3 lines > 2", "근거")
        self.assertEqual(str(w), 'scene 2 line basis: BASIS_LINES (3 lines > 2) "근거"')


class Markup(unittest.TestCase):
    def test_markup_new_escapes_and_restores_only_four_tags(self):
        out = layout.markup_new(f"S{AMP}P500 {LT}g{GT}금{LT}/g{GT} {LT}i{GT}x")
        self.assertIn("S" + AMP + "amp;P500", out)
        self.assertIn(constants.GOLD, out)
        self.assertRegex(out, r"<span[^>]*>금</span>")
        self.assertIn(AMP + "lt;i" + AMP + "gt;", out)
        self.assertNotIn(LT + "i" + GT, out)

    def test_keep_all_only_in_new_layout(self):
        a = layout.legacy_inner_html("t", ["x"], 1, 0.5, "b")
        b = layout.new_inner_html("t", ["x"], 1, 0.5, "b")
        self.assertNotIn("keep-all", a)
        self.assertIn("keep-all", b)

    def test_registered(self):
        self.assertIs(layout.LAYOUTS["new"], layout.new_inner_html)

    def test_text_is_never_truncated_or_shrunk(self):
        basis = "근거 " * 40
        html = layout.new_inner_html("상단", ["가나다"], 1, 0.5, basis)
        self.assertIn(basis.strip(), html)
        self.assertIn(f"font-size:{constants.BASIS_PX}px", html)
        self.assertIn(constants.ACCOUNT, html)

    def test_empty_basis_omits_block_but_keeps_account_and_top_slot(self):
        for empty in ("", "   "):
            html = layout.new_inner_html("", ["가나다"], 1, 0.5, empty)
            self.assertNotIn("rk-basis", html)
            self.assertIn("rk-acct", html)
            self.assertIn("rk-top", html)
            self.assertIn("min-height:60px", html)

    def test_lines_stay_in_layout_with_opacity(self):
        html = layout.new_inner_html("t", ["a", "b", "c"], 2, 0.5, "b")
        self.assertEqual(len(re.findall(r'class="rk-ln"', html)), 3)
        self.assertEqual(re.findall(r"opacity:(\d)", html), ["1", "1", "0"])

    def test_overlay_uses_constants(self):
        html = layout.overlay_html()
        self.assertIn(f"y={constants.SAFE['top']} top", html)
        self.assertIn(f"y={constants.SAFE['warn_y']} warn", html)
        self.assertIn(f"y={constants.H - constants.SAFE['bottom_ui']} UI zone", html)


class BrowserChecks(unittest.TestCase):
    def test_ok_fixture_has_no_warning(self):
        self.assertEqual(render.check_layout(FIX / "ok-layout.json", "new"), [])

    def test_bad_fixture_kinds_and_format(self):
        ws = render.check_layout(FIX / "bad-layout.json", "new")
        got = set(kinds(ws))
        for k in ("WRAP", "RIGHT", "TOP", "BASIS_LINES", "FONT_FALLBACK"):
            self.assertIn(k, got)
        self.assertTrue(got & {"WARN_Y", "UI_ZONE"})
        for w in ws:
            self.assertRegex(str(w), WARN_RE)
        self.assertTrue(all(w.scene == 1 for w in ws))

    def test_committed_specs_never_warn_about_basis_or_account(self):
        files = sorted((REPO / "2026" / "reels" / "specs").glob("*.json"))
        self.assertEqual(len(files), 10)
        counts = {}
        for f in files:
            with self.subTest(spec=f.name):
                ws = render.check_layout(f, "new")
                counts[f.name] = {k: kinds(ws).count(k) for k in sorted(set(kinds(ws)))}
                self.assertEqual([str(w) for w in ws if w.line in ("basis", "account")], [])
        print("\n새 배치 경고 집계:", json.dumps(counts, ensure_ascii=False), file=sys.stderr)

    def test_legacy_layout_emits_no_measurement_warnings(self):
        ws = render.check_layout(REPO / "2026" / "reels" / "specs" / "2026-10-26-tax-deduction.json", "legacy")
        self.assertLessEqual(set(kinds(ws)), {"FONT_FALLBACK"})


class Cli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-layout-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_reel(self, spec, out, *flags):
        return subprocess.run([sys.executable, str(TOOLS / "reel.py"), str(spec), str(out), *flags],
                              capture_output=True, text=True)

    def test_ok_new_layout_render_and_overlay(self):
        out = self.tmp / "ok.mp4"
        r = self.run_reel(FIX / "ok-layout.json", out, "--layout", "new")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse([l for l in r.stderr.splitlines() if l.startswith("scene ")], r.stderr)
        ov = self.tmp / "ok.safe-s01.png"
        self.assertEqual(png_size(ov), (1080, 1920))
        sage = (0xDE, 0xE9, 0xE0)
        px = pixel(out, 5, 1900, t=2.5)
        self.assertTrue(all(abs(a - b) <= 10 for a, b in zip(px, sage)), px)   # 오버레이가 영상 프레임에 없다
        o = pixel(ov, 5, 1900)
        self.assertGreaterEqual(o[0] - o[1], 40, o)
        self.assertIn("spec: PASS 9/9", r.stderr)

    def test_strict_bad_fixture_exit_3_and_mp4_written(self):
        out = self.tmp / "bad.mp4"
        r = self.run_reel(FIX / "bad-layout.json", out, "--layout", "new", "--strict")
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertTrue(out.stat().st_size > 0)
        self.assertTrue([l for l in r.stderr.splitlines() if l.startswith("scene 1 line")])

    def test_bad_fixture_without_strict_exits_0(self):
        out = self.tmp / "bad2.mp4"
        r = self.run_reel(FIX / "bad-layout.json", out, "--layout", "new")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("레이아웃 경고", r.stderr)

    def test_overlay_all_writes_one_per_scene(self):
        out = self.tmp / "all.mp4"
        r = self.run_reel(FIX / "ok-layout.json", out, "--layout", "new", "--overlay-all")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.tmp / "all.safe-s01.png").exists())
        self.assertTrue((self.tmp / "all.safe-s02.png").exists())


if __name__ == "__main__":
    unittest.main()
