"""basic 모션 시험: none 기준선 보호, 시간표, 트레이서 릴스 (stdlib unittest 전용)."""
import copy
import json
import re
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
from reelkit import browser, check, figures, layout, motion, render, stills  # noqa: E402
from reelkit.expand import ExpandError, expand_source  # noqa: E402
from reelkit.spec import SpecError  # noqa: E402

DRAFT = [sys.executable, str(TOOLS / "draft.py")]
STATUTE_RE = re.compile(r"제\s*\d+\s*조")


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


def run_text(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


class SourceField(unittest.TestCase):
    """motion 은 원고 소스에서만 정한다: expand 가 검증하고 check 가 손으로 고친 값을 잡는다 (D-05)."""

    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()

    @staticmethod
    def src(**over):
        src = {"scenes": [{"top": "t", "lines": ["줄"]}]}
        src.update(over)
        return src

    def test_values_pass_through(self):
        for mode in ("basic", "none"):
            self.assertEqual(expand_source(self.src(motion=mode), self.registry)["motion"], mode)

    def test_absent_stays_absent(self):
        self.assertNotIn("motion", expand_source(self.src(), self.registry))

    def test_other_values_refused(self):
        for bad in ("calm", {"preset": "calm"}, 1, True):
            with self.assertRaises(ExpandError) as cm:
                expand_source(self.src(motion=bad), self.registry)
            self.assertIn("motion", str(cm.exception))
            self.assertIn("basic", str(cm.exception))

    def test_hand_edited_motion_is_source_mismatch(self):
        src = self.src()
        spec = expand_source(src, self.registry)
        self.assertEqual(check.compare_source(spec, src, self.registry), [])
        edited = copy.deepcopy(spec)
        edited["motion"] = "basic"
        issues = check.compare_source(edited, src, self.registry)
        self.assertEqual([i.kind for i in issues], ["SOURCE_MISMATCH"])
        self.assertIn("motion", str(issues[0]))
        same = self.src(motion="basic")
        self.assertEqual(check.compare_source(expand_source(same, self.registry), same, self.registry), [])

    def test_scene_times_follow_schedule(self):
        spec = two_scene_spec()
        self.assertEqual(stills.scene_times(spec), [1.25, 3.15])  # none 규칙: 마지막 상태 시작 + 0.4초
        spec["motion"] = "basic"
        self.assertEqual(stills.scene_times(spec), [round(sc.final_t, 2) for sc in motion.schedule(spec).scenes])


TINY = {"basis": "예시 · 가정 기준", "scenes": [{"top": "", "lines": ["끝"]}]}


class ReelFlag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-motion-flag-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def spec(self, name, **extra):
        p = self.tmp / name
        p.write_text(json.dumps({**TINY, **extra}, ensure_ascii=False), encoding="utf-8")
        return p

    def test_flag_enables_motion(self):
        out = self.tmp / "flag.mp4"
        r = run_reel(self.spec("plain.json"), out, "--layout", "new", "--motion", "basic")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[1], "motion=basic")
        self.assertRegex(r.stdout.splitlines()[0], r"^duration=\d+\.\ds cover_ms=\d+$")

    def test_flag_none_overrides_field(self):
        out = self.tmp / "none.mp4"
        r = run_reel(self.spec("basic.json", motion="basic"), out, "--layout", "new", "--motion", "none")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("motion=basic", r.stdout)

    def test_legacy_with_basic_field_refused(self):
        out = self.tmp / "legacy.mp4"
        r = run_reel(self.spec("basic2.json", motion="basic"), out)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("원고 오류", r.stderr)
        self.assertFalse(out.exists())

    def test_legacy_with_basic_flag_refused(self):
        out = self.tmp / "legacy2.mp4"
        r = run_reel(self.spec("plain2.json"), out, "--layout", "legacy", "--motion", "basic")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertFalse(out.exists())

    def test_unknown_field_value_refused(self):
        out = self.tmp / "calm.mp4"
        r = run_reel(self.spec("calm.json", motion="calm"), out, "--layout", "new")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("원고 오류", r.stderr)
        self.assertFalse(out.exists())


def ffprobe_stream(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return r.stdout.strip()


def decode_frame(mp4, n):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"select=eq(n\\,{n})", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return r.stdout


def sampled_mean_diff(a, b, step=97):
    assert len(a) == len(b)
    pairs = list(zip(a[::step], b[::step]))
    return sum(abs(x - y) for x, y in pairs) / len(pairs)


class BundleBasic(unittest.TestCase):
    """spec.src.json 의 motion 필드 하나로 모션 묶음이 만들어진다 (렌더 1회)."""

    DATE, SLUG = "2026-11-08", "pension-credit-limit"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        reels = Path(cls.tmp.name) / "reels"
        (reels / "specs").mkdir(parents=True)
        r = run_text(DRAFT + ["slot", "--reels-dir", str(reels), "--date", cls.DATE, "--slug", cls.SLUG, "--create"])
        assert r.returncode == 0, r.stderr
        cls.name = f"{cls.DATE}-{cls.SLUG}"
        cls.d = reels / "drafts" / cls.name
        src = json.loads((FIX / "draft-pension.src.json").read_text(encoding="utf-8"))
        src["motion"] = "basic"
        (cls.d / "spec.src.json").write_text(json.dumps(src, ensure_ascii=False, indent=1), encoding="utf-8")
        shutil.copy(FIX / "draft-pension.caption.src.json", cls.d / "caption.src.json")
        cls.r = run_text(DRAFT + ["bundle", str(cls.d)])
        cls.spec = json.loads((cls.d / "spec.json").read_text(encoding="utf-8")) if (cls.d / "spec.json").is_file() else {}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_bundle_ok_and_spec_9_of_9(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)
        self.assertEqual(self.spec.get("motion"), "basic")
        self.assertIn("spec: PASS 9/9", self.r.stderr)

    def test_review_times_are_schedule_values(self):
        text = (self.d / "review.md").read_text(encoding="utf-8")
        table = text.split("| 장면 | 시점(초) | 첫 줄 |", 1)[1].split("\n\n", 1)[0]
        got = [float(m.group(1)) for m in re.finditer(r"^\| \d+ \| ([\d.]+) \|", table, re.M)]
        self.assertEqual(got, stills.scene_times(self.spec))
        self.assertEqual(got, [round(sc.final_t, 2) for sc in motion.schedule(self.spec).scenes])

    def test_cover_is_scene_one_final_frame(self):
        cover = self.d / f"{self.name}-cover.png"
        self.assertEqual(ffprobe_stream(cover), "1080,1920")
        self.assertNotIn("COVER_CROP", self.r.stderr)
        sched = motion.schedule(self.spec)
        from_video = decode_frame(self.d / f"{self.name}.mp4", sched.scenes[0].final_frame)
        self.assertLess(sampled_mean_diff(stills._decode(cover), from_video), 3.0)
        self.assertIn(f"cover_ms={round(sched.scenes[0].final_t * 1000)}", self.r.stdout)

    def test_frame_count_matches_schedule(self):
        sched = motion.schedule(self.spec)
        self.assertEqual(ffprobe_packets(self.d / f"{self.name}.mp4"), sched.nframes)

    def test_no_forbidden_words(self):
        for n in ("review.md", "compliance.json", "bundle.json"):
            text = (self.d / n).read_text(encoding="utf-8")
            self.assertNotIn("통과", text, n)
            self.assertIsNone(STATUTE_RE.search(text), n)
        self.assertNotIn("통과", self.r.stdout)
        self.assertIsNone(STATUTE_RE.search(self.r.stdout))


def equivalence_spec():
    """연금 편 장면 1·5(확장 결과) + bad-layout 의 줄바꿈 긴 줄 장면."""
    registry = figures.load_registry()
    expanded = expand_source(json.loads((FIX / "draft-pension.src.json").read_text(encoding="utf-8")), registry)
    wrap = json.loads((FIX / "bad-layout.json").read_text(encoding="utf-8"))["scenes"][0]
    return {"basis": expanded["basis"],
            "scenes": [expanded["scenes"][0], expanded["scenes"][4],
                       {"top": wrap["top"], "lines": wrap["lines"][:3]}]}


def row_diffs_ok(a, b, first_row=30, width=1080, tol=1):
    stride = width * 3
    assert len(a) == len(b)
    worst = 0
    for y in range(first_row, len(a) // stride):
        ra, rb = a[y * stride:(y + 1) * stride], b[y * stride:(y + 1) * stride]
        if ra != rb:
            worst = max(worst, max(abs(x - z) for x, z in zip(ra, rb)))
    return worst <= tol, worst


class Equivalence(unittest.TestCase):
    """모션 최종 프레임이 정적(none) 프레임과 같다: 줄바꿈이 움직이지 않는다는 영구 보증 (막대 행 < 30 제외)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-motion-eq-"))
        spec = equivalence_spec()
        path = cls.tmp / "spec.json"
        path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        cls.frames = {}
        for mode in ("none", "basic"):
            got = {}
            render.render_reel(path, cls.tmp / f"{mode}.mp4", layout="new", motion=mode,
                               frame_sink=lambda i, p, got=got: got.__setitem__(i, stills._decode(p)))
            cls.frames[mode] = got

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_final_frames_match_static(self):
        self.assertEqual(sorted(self.frames["none"]), [0, 1, 2])
        self.assertEqual(sorted(self.frames["basic"]), [0, 1, 2])
        for i in range(3):
            ok, worst = row_diffs_ok(self.frames["none"][i], self.frames["basic"][i])
            self.assertTrue(ok, f"scene {i + 1}: 행 30 이후 채널 차이 {worst} > 1")


class Geometry(unittest.TestCase):
    """모션 DOM 의 줄 사각형·줄 수가 정적 새 배치와 같고, 진입 중에도 줄바꿈이 변하지 않는다 (브라우저 한 번, 인코딩 없음)."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-motion-geo-"))
        cls.pw = sync_playwright().start()
        cls.browser, _used = browser.launch(cls.pw)
        cls.page = render._open_checked_page(cls.browser, cls.tmp)
        cls.spec = equivalence_spec()
        cls.sched = motion.schedule(cls.spec)
        cls.static = []
        basis = cls.spec["basis"]
        for sc in cls.spec["scenes"]:
            cls.page.evaluate("h=>{document.body.innerHTML=h}",
                              layout.new_inner_html(sc["top"], sc["lines"], len(sc["lines"]), 1.0, basis))
            cls.page.evaluate("document.fonts.ready.then(()=>0)")
            cls.static.append(cls.page.evaluate(layout.MEASURE_JS))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def measure_alone(self, k, t):
        motion.build(self.page, self.spec, self.sched)
        motion.seek(self.page, self.sched, t)
        self.page.evaluate("k=>document.querySelectorAll('.rk-layer').forEach((L,i)=>{if(i!==k) L.remove()})", k)
        return self.page.evaluate(layout.MEASURE_JS)

    def assert_same_box(self, a, b, msg):
        self.assertIsNotNone(a, msg)
        self.assertEqual(a["n"], b["n"], msg)
        for key in ("l", "r", "t", "b"):
            self.assertAlmostEqual(a[key], b[key], delta=0.01, msg=f"{msg} {key}")

    def test_final_frame_geometry(self):
        for k, sc in enumerate(self.sched.scenes):
            got, want = self.measure_alone(k, sc.final_t), self.static[k]
            self.assertEqual(len(got["lines"]), len(want["lines"]))
            for key in ("top", "basis", "acct"):
                if want[key] is None:
                    self.assertIsNone(got[key])
                else:
                    self.assert_same_box(got[key], want[key], f"scene {k + 1} {key}")
            for j, (g, w) in enumerate(zip(got["lines"], want["lines"])):
                self.assert_same_box(g, w, f"scene {k + 1} line {j + 1}")

    def test_wrapping_scene_really_wraps(self):
        self.assertGreater(self.static[2]["lines"][0]["n"], 1)

    def test_entry_keeps_line_breaks(self):
        for k, sc in enumerate(self.sched.scenes):
            want = self.static[k]
            for j in range(sc.n_lines):
                t = sc.start + j * motion.STAGGER + 0.15
                got = self.measure_alone(k, t)["lines"][j]
                w = want["lines"][j]
                self.assertEqual(got["n"], w["n"], f"scene {k + 1} line {j + 1}")
                self.assertAlmostEqual(got["r"] - got["l"], w["r"] - w["l"], delta=0.01)
                offset = got["t"] - w["t"]
                self.assertGreaterEqual(offset, -0.01, f"scene {k + 1} line {j + 1} offset {offset}")
                self.assertLessEqual(offset, motion.RISE_PX + 0.01, f"scene {k + 1} line {j + 1} offset {offset}")


if __name__ == "__main__":
    unittest.main()
