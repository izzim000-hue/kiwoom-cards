"""basic 모션 시험: none 기준선 보호, 시간표, 트레이서 릴스 (stdlib unittest 전용)."""
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
TOOLS = TESTS.parent
FIX = TESTS / "fixtures"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TESTS))

import none_guard  # noqa: E402
from reelkit import browser, calc, check, figures, golden, layout, motion, render, stills, timeline  # noqa: E402
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
        shutil.copy(FIX / "draft-pension-motion.src.json", cls.d / "spec.src.json")
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

    def test_review_and_bundle_record_motion(self):
        text = (self.d / "review.md").read_text(encoding="utf-8")
        self.assertIn("모션: basic", text)
        self.assertIn("카운트업 2곳", text)
        self.assertIn("중간 숫자는 연출, 최종값만 장부 값", text)
        self.assertIn("- [ ] 카운트업 — 영상 마지막 프레임의 숫자가 원고 숫자와 같은지 확인", text)
        b = json.loads((self.d / "bundle.json").read_text(encoding="utf-8"))
        self.assertEqual((b["motion"], b["countups"]), ("basic", 2))
        for kind in ("DWELL", "COUNTUP_WRAP"):
            self.assertNotIn(kind, self.r.stderr)
            self.assertNotIn(kind, text)

    def test_fixture_matches_helper_source(self):
        self.assertEqual(json.loads((FIX / "draft-pension-motion.src.json").read_text(encoding="utf-8")),
                         pension_countup_src())

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


def pension_countup_src():
    """연금 편 소스에서 장면 5 의 두 숫자에 |up 을 붙인 사본 (motion basic)."""
    src = json.loads((FIX / "draft-pension.src.json").read_text(encoding="utf-8"))
    lines = src["scenes"][4]["lines"]
    lines[0] = lines[0].replace("{{c_low|man1}}", "{{c_low|man1|up}}")
    lines[1] = lines[1].replace("{{c_high|man1}}", "{{c_high|man1|up}}")
    src["motion"] = "basic"
    return src


def pension_countup_spec():
    return expand_source(pension_countup_src(), figures.load_registry())


def strip_tags(text):
    return motion.TAG_RE.sub("", text)


class CountUpUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = pension_countup_spec()
        cls.items = motion.countup_entries(cls.spec)

    def test_two_entries_in_document_order(self):
        self.assertEqual([(si, li) for si, li, _e in self.items], [(4, 0), (4, 1)])
        for _si, _li, e in self.items:
            self.assertTrue(e["countup"])

    def test_final_text_is_ledger_text_object(self):
        e = self.items[0][2]
        for p in (1, 1.0, 1.7, 25):
            self.assertIs(motion.cu_text(e, p), e["text"])

    def test_start_is_zero_string_from_formats(self):
        for _si, _li, e in self.items:
            want = calc.FORMATS[e["fmt"]](Decimal(0))[0]
            self.assertEqual(motion.cu_text(e, 0), want)
            self.assertEqual(motion.cu_text(e, -0.5), want)
        self.assertEqual(motion.cu_text(self.items[0][2], 0), "0만")

    def test_intermediate_values_come_from_formats_and_never_decrease(self):
        e = self.items[0][2]
        shown = []
        for n in range(0, 21):
            p = n / 20
            text = motion.cu_text(e, p)
            if p < 1:
                eased = 1 - (1 - p) ** 3
                self.assertEqual(text, calc.FORMATS[e["fmt"]](Decimal(e["value"]) * Decimal(str(eased)))[0])
            shown.append(Decimal(text.replace(",", "").replace("만", "")))
        self.assertEqual(shown, sorted(shown))
        self.assertGreater(shown[-1], shown[0])

    def test_countup_texts_follow_line_start(self):
        sched = motion.schedule(self.spec)
        sc = sched.scenes[4]
        t_start = sc.start
        t_end = sc.start + motion.STAGGER + motion.COUNT
        first = motion.countup_texts(sched, self.items, t_start)
        self.assertEqual(first[0], "0만")
        self.assertEqual(first[1], "0만")                      # 두 번째 줄은 STAGGER 뒤에 시작
        late = motion.countup_texts(sched, self.items, t_start + motion.STAGGER)
        self.assertNotEqual(late[0], "0만")
        self.assertEqual(late[1], "0만")
        self.assertEqual(motion.countup_texts(sched, self.items, t_end),
                         [e["text"] for _s, _l, e in self.items])

    def test_schedule_settle_counts_countup(self):
        sc = motion.schedule(self.spec).scenes[4]
        self.assertEqual(sc.countup_lines, (0, 1))
        self.assertAlmostEqual(sc.settle, motion.STAGGER + motion.COUNT)

    def forged(self, **change):
        spec = copy.deepcopy(self.spec)
        for e in spec["figures"]:
            if e.get("countup") and e["where"] == "scene 5 line 1":
                e.update(change)
        return spec

    def test_forged_entries_refused(self):
        cases = {
            "text moved": dict(start=0, end=len(self.items[0][2]["text"])),
            "unknown fmt": dict(fmt="zzz"),
            "bad value": dict(value="abc"),
            "infinite value": dict(value="Infinity"),
            "not a scene line": dict(where="scene 5 top"),
            "line missing": dict(where="scene 5 line 9"),
            "countup not true": dict(countup="yes"),
        }
        for name, change in cases.items():
            with self.subTest(name), self.assertRaises(SpecError):
                motion.countup_entries(self.forged(**change))

    def test_overlapping_pair_refused(self):
        spec = copy.deepcopy(self.spec)
        twin = copy.deepcopy([e for e in spec["figures"] if e.get("countup")][0])
        spec["figures"].append(twin)
        with self.assertRaises(SpecError) as cm:
            motion.countup_entries(spec)
        self.assertIn("겹침", str(cm.exception))

    def test_no_countup_means_no_items(self):
        self.assertEqual(motion.countup_entries(two_scene_spec()), [])
        plain = expand_source(json.loads((FIX / "draft-pension.src.json").read_text(encoding="utf-8")),
                              figures.load_registry())
        self.assertEqual(motion.countup_entries(plain), [])


class CountUp(unittest.TestCase):
    """한 브라우저에서 모션 DOM 을 직접 본다 (인코딩 없음): 상자 폭·왼쪽·줄 높이가 프레임마다 같고 마지막은 원고와 같다."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-motion-cu-"))
        cls.pw = sync_playwright().start()
        cls.browser, _used = browser.launch(cls.pw)
        cls.page = render._open_checked_page(cls.browser, cls.tmp)
        cls.spec = pension_countup_spec()
        cls.sched = motion.schedule(cls.spec)
        cls.items = motion.countup_entries(cls.spec)
        cls.cu_lines = motion.build(cls.page, cls.spec, cls.sched)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def at(self, t, cu=None):
        motion.seek(self.page, self.sched, t, cu if cu is not None else motion.countup_texts(self.sched, self.items, t))

    def boxes(self):
        return self.page.evaluate(
            "()=>[...document.querySelectorAll('.rk-cu')].map(e=>{const r=e.getBoundingClientRect();"
            "const l=e.closest('.rk-ln').getBoundingClientRect();"
            "return {w:r.width,l:r.left,lh:l.height,text:e.textContent,kids:e.children.length}})")

    def test_build_reports_motion_line_counts(self):
        self.assertEqual([(c["s"], c["j"]) for c in self.cu_lines], [(4, 0), (4, 1)])
        self.assertTrue(all(c["n"] == 1 for c in self.cu_lines))
        self.assertFalse([c for c in self.cu_lines if c["moved"]], self.cu_lines)

    def test_box_is_one_width_one_left_one_height_over_the_count_window(self):
        sc = self.sched.scenes[4]
        seen = {0: [], 1: []}
        for n in range(10):
            t = sc.start + (sc.settle) * n / 9
            self.at(t)
            for k, b in enumerate(self.boxes()):
                seen[k].append((round(b["w"], 2), round(b["l"], 2), round(b["lh"], 2)))
        for k, rows in seen.items():
            self.assertEqual(len({r[0] for r in rows}), 1, f"count-up {k} width")
            self.assertEqual(len({r[1] for r in rows}), 1, f"count-up {k} left")
            self.assertEqual(len({r[2] for r in rows}), 1, f"count-up {k} line height")
            self.assertGreater(rows[0][0], 50)

    def test_text_changes_during_window_but_box_does_not(self):
        sc = self.sched.scenes[4]
        self.at(sc.start + 0.4)
        mid = [b["text"] for b in self.boxes()]
        self.at(sc.final_t)
        end = [b["text"] for b in self.boxes()]
        self.assertNotEqual(mid[0], end[0])
        self.assertEqual(end, [e["text"] for _s, _l, e in self.items])

    def test_window_start_shows_p0_string(self):
        for k, (si, li, e) in enumerate(self.items):
            t0 = self.sched.scenes[si].start + li * motion.STAGGER
            self.at(t0)
            self.assertEqual(self.boxes()[k]["text"], calc.FORMATS[e["fmt"]](Decimal(0))[0])

    def test_final_line_text_equals_script_line(self):
        for k, sc in enumerate(self.sched.scenes):
            self.at(sc.final_t)
            got = self.page.evaluate(
                "(s)=>[...document.querySelectorAll('.rk-layer')[s].querySelectorAll('.rk-ln')].map(e=>e.textContent)", k)
            want = [strip_tags(l) for l in self.spec["scenes"][k]["lines"]]
            self.assertEqual(got, want, f"scene {k + 1}")

    def test_frame_strings_are_text_not_markup(self):
        self.at(self.sched.scenes[4].start + 0.3, ["<b>x</b>", "<b>x</b>"])
        for b in self.boxes():
            self.assertEqual(b["kids"], 0)
            self.assertEqual(b["text"], "<b>x</b>")


# 최종 글자보다 넓은 중간 숫자가 나오던 서식들 (CR-01): man1 정수(98.6만 > 150만), pct 정수(6.6% > 10%),
# eok_man_won 억 단위(9,999만 원 > 1억 원)와 억+만, 그리고 소수점 있는 man1 (연금 편) — 숫자 뒤에 조사가 붙은 줄.
FIT_CASES = (("<g>", "150만", "</g>이면 충분", "man1", "1500000"),
             ("<g>", "10%", "</g>를 넘으면", "pct", "10"),
             ("<g>", "1억 원", "</g>까지 모아요", "eok_man_won", "100000000"),
             ("<g>", "3억 7,200만 원", "</g>", "eok_man_won", "372000000"),
             ("최대 <g>", "148.5만", "</g>까지", "man1", "1485000"))


def fit_spec(cases=FIT_CASES):
    """cases 를 장면마다 하나씩 첫 줄에 카운트업으로 둔 손 원고 (장부는 countup_entries 가 검사하는 키만)."""
    scenes, ledger = [], []
    for i, (pre, text, post, fmt, value) in enumerate(cases):
        scenes.append({"top": "", "lines": [pre + text + post, "다음 줄"]})
        ledger.append({"where": f"scene {i + 1} line 1", "start": len(pre), "end": len(pre) + len(text), "text": text,
                       "fmt": fmt, "value": value, "countup": True})
    return {"motion": "basic", "basis": "예시", "scenes": scenes, "figures": ledger}


class CountUpSteps(unittest.TestCase):
    """중간 숫자는 최종 글자의 표시 정밀도로 센다 (CR-01): 자릿수·소수점·단위가 최종 글자보다 많아지지 않는다."""

    def texts(self, k):
        e = motion.countup_entries(fit_spec())[k][2]
        return e, [motion.cu_text(e, n / 240) for n in range(240)]

    def test_integer_finals_count_in_integers(self):
        for k in (0, 1):
            e, texts = self.texts(k)
            with self.subTest(e["text"]):
                self.assertFalse([t for t in texts if "." in t])
                self.assertEqual(texts[0], calc.FORMATS[e["fmt"]](Decimal(0))[0])
                self.assertGreater(len(set(texts)), 5)            # 실제로 센다

    def test_eok_final_never_shows_wider_man_text(self):
        e, texts = self.texts(2)
        self.assertEqual(set(texts), {"0만 원"})                    # 1억 원: 억 단위로 센다 (9,999만 원 없음)
        e, texts = self.texts(3)
        self.assertTrue(all(len(t) <= len(e["text"]) for t in texts), texts)
        self.assertTrue(any(t.startswith("3억 ") for t in texts))

    def test_decimal_final_keeps_format_values(self):
        e, texts = self.texts(4)
        self.assertIsNone(motion.countup_step(e))
        self.assertTrue(any("." in t for t in texts))

    def test_variants_cover_every_frame(self):
        spec = fit_spec()
        sched, items = motion.schedule(spec), motion.countup_entries(spec)
        variants = motion.countup_variants(sched, items)
        for f in range(sched.nframes):
            for k, text in enumerate(motion.countup_texts(sched, items, f / motion.FPS)):
                self.assertIn(text, variants[k])
        self.assertEqual([v[-1] for v in variants], [e["text"] for _s, _l, e in items])


class CountUpFit(unittest.TestCase):
    """모든 렌더 프레임에서 카운트업 글자가 상자 안에 있다 (CR-01). 브라우저 한 번, 인코딩 없음."""

    OVER_JS = """() => [...document.querySelectorAll('.rk-cu')]
      .filter(e => e.closest('.rk-layer').style.display !== 'none')
      .map(e => { const b = e.getBoundingClientRect(); const r = document.createRange(); r.selectNodeContents(e);
                  const t = r.getBoundingClientRect();
                  return {k: +e.dataset.k, over: Math.max(t.right - b.right, b.left - t.left, e.scrollWidth - e.clientWidth),
                          w: b.width, text: e.textContent}; })"""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-motion-fit-"))
        cls.pw = sync_playwright().start()
        cls.browser, _used = browser.launch(cls.pw)
        cls.page = render._open_checked_page(cls.browser, cls.tmp)
        cls.spec = fit_spec()
        cls.sched = motion.schedule(cls.spec)
        cls.items = motion.countup_entries(cls.spec)
        # 정적 배치의 숫자 폭 (모션 레이어를 만들기 전, 줄 마크업 그대로)
        cls.page.evaluate("h=>{document.body.innerHTML=h}", layout.root_html(1.0, motion.layers_html(cls.spec, cls.items)))
        cls.page.evaluate("document.fonts.ready.then(()=>0)")
        cls.static_w = cls.page.evaluate("()=>[...document.querySelectorAll('.rk-cu')].map(e=>e.getBoundingClientRect().width)")
        cls.cu_lines = motion.build(cls.page, cls.spec, cls.sched)
        cls.worst = {}
        for f in range(cls.sched.nframes):
            t = f / motion.FPS
            motion.seek(cls.page, cls.sched, t, motion.countup_texts(cls.sched, cls.items, t))
            for m in cls.page.evaluate(cls.OVER_JS):
                if m["k"] not in cls.worst or m["over"] > cls.worst[m["k"]]["over"]:
                    cls.worst[m["k"]] = {**m, "f": f}

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_no_frame_overflows_the_box(self):
        self.assertEqual(sorted(self.worst), list(range(len(FIT_CASES))))
        for k, m in sorted(self.worst.items()):
            with self.subTest(FIT_CASES[k][1]):
                self.assertLessEqual(m["over"], 0.5, m)

    def test_box_keeps_the_static_width(self):
        # 중간 숫자가 최종 글자보다 넓지 않으므로 상자 = 최종 글자 폭 = 정적 배치 (마지막 프레임 배치가 바뀌지 않음)
        for k, m in sorted(self.worst.items()):
            with self.subTest(FIT_CASES[k][1]):
                self.assertAlmostEqual(m["w"], self.static_w[k], delta=0.01)

    def test_lines_do_not_rewrap(self):
        self.assertTrue(all(c["n"] == 1 for c in self.cu_lines), self.cu_lines)

    def static_measures(self, spec):
        out = {}
        for i, sc in enumerate(spec["scenes"], 1):
            self.page.evaluate("h=>{document.body.innerHTML=h}",
                               layout.new_inner_html(sc["top"], sc["lines"], len(sc["lines"]), 1.0, spec.get("basis", "")))
            self.page.evaluate("document.fonts.ready.then(()=>0)")
            out[i] = self.page.evaluate(layout.MEASURE_JS)
        return out

    def test_same_count_but_moved_break_warns(self):
        # WR-02: 정적 배치는 "최대 연금 / 148.5만까지 받아요", 숫자 상자가 생기면 "최대 연금 148.5만 / 까지 받아요" — 둘 다 2줄
        spec = fit_spec(FIT_CASES[:4] + (("최대 연금 <g>", "148.5만", "</g>까지 받아요", "man1", "1485000"),))
        static = self.static_measures(spec)
        cu_lines = motion.build(self.page, spec, motion.schedule(spec))
        row = [c for c in cu_lines if c["s"] == 4][0]
        self.assertEqual((row["n"], static[5]["lines"][0]["n"]), (2, 2))
        self.assertTrue(row["moved"], row)
        self.assertEqual(row["before"], "최대 연금 / 148.5만까지 받아요")
        self.assertEqual(row["after"], "최대 연금 148.5만 / 까지 받아요")
        ws = render.countup_wrap_warnings(spec, cu_lines, static)
        self.assertEqual([(w.scene, w.line, w.kind) for w in ws], [(5, "1", "COUNTUP_WRAP")])
        self.assertIn("줄바꿈 위치", ws[0].value)

    def test_unchanged_breaks_do_not_warn(self):
        spec = fit_spec()
        static = self.static_measures(spec)
        cu_lines = motion.build(self.page, spec, motion.schedule(spec))
        self.assertFalse([c for c in cu_lines if c["moved"]], cu_lines)
        self.assertEqual(render.countup_wrap_warnings(spec, cu_lines, static), [])

    def test_wider_intermediate_grows_the_box(self):
        # 넓은 중간 글자가 생겨도(예: 서식 규칙이 바뀌어) 상자가 그 글자에 맞춰 커진다: 측정이 마지막 방어선
        spec = fit_spec()
        sched, items = motion.schedule(spec), motion.countup_entries(spec)
        real = motion.countup_variants
        with mock.patch.object(motion, "countup_variants",
                               lambda s, it: [v + ["9,999만 원"] for v in real(s, it)]):
            motion.build(self.page, spec, sched)
        widths = self.page.evaluate("()=>[...document.querySelectorAll('.rk-cu')].map(e=>e.getBoundingClientRect().width)")
        self.assertGreater(widths[2], self.static_w[2] + 100)
        motion.seek(self.page, sched, sched.scenes[2].start + 0.3, ["9,999만 원"] * len(items))
        over = {m["k"]: m["over"] for m in self.page.evaluate(self.OVER_JS)}
        self.assertLessEqual(over[2], 0.5)


class CountUpRender(unittest.TestCase):
    """같은 원고를 reel.py 로 끝까지 렌더한다 (파일 한 번, 라이브러리 한 번)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-motion-curender-"))
        cls.spec = pension_countup_spec()
        cls.spec_path = cls.tmp / "spec.json"
        cls.spec_path.write_text(json.dumps(cls.spec, ensure_ascii=False), encoding="utf-8")
        cls.proc = run_reel(cls.spec_path, cls.tmp / "cu.mp4", "--layout", "new")
        cls.res = render.render_reel(cls.spec_path, cls.tmp / "lib.mp4", layout="new")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_reel_py_exit_and_spec(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertIn("spec: PASS 9/9", self.proc.stderr)
        self.assertNotIn("COUNTUP_WRAP", self.proc.stdout + self.proc.stderr)

    def test_library_result(self):
        self.assertEqual(self.res.countups, 2)
        self.assertEqual(self.res.motion, "basic")
        self.assertFalse([w for w in self.res.warnings if w.kind == "COUNTUP_WRAP"])

    def test_forged_ledger_stops_render_with_exit_1(self):
        bad = copy.deepcopy(self.spec)
        for e in bad["figures"]:
            if e.get("countup"):
                e["fmt"] = "zzz"
        p = self.tmp / "bad.json"
        p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        out = self.tmp / "bad.mp4"
        r = run_reel(p, out, "--layout", "new")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertFalse(out.exists())


REPO = TOOLS.parent


def published_specs():
    """게시된 10편 원고: 골든 기준표의 재현 가능 항목 (test_check.py 와 같은 방식)."""
    return sorted(REPO / e["spec"] for e in golden.load_manifest()["entries"] if e["status"] == "reproducible")


def uniform_spec(scenes, n_lines, chars):
    return {"scenes": [{"top": "t", "lines": ["가" * chars] * n_lines} for _ in range(scenes)]}


class Dwell(unittest.TestCase):
    def test_published_ten_land_in_house_range_without_warnings(self):
        specs = published_specs()
        self.assertEqual(len(specs), 10)
        for path in specs:
            spec = json.loads(path.read_text(encoding="utf-8"))
            spec["motion"] = "basic"
            sched = motion.schedule(spec)
            self.assertTrue(21.0 <= sched.total <= 27.0, f"{path.name}: {sched.total:.2f}초")
            self.assertEqual(motion.dwell_warnings(spec, sched), [], path.name)

    def test_short_middle_scene_warns(self):
        spec = {"scenes": [{"top": "", "lines": ["가나다라마바사아", "자차카타파하가나"]},
                           {"top": "", "lines": ["<g>ab</g>"]},
                           {"top": "", "lines": ["가나다라마바사아", "자차카타파하가나"]}]}
        sched = motion.schedule(spec)
        ws = motion.dwell_warnings(spec, sched)
        self.assertEqual([(w.scene, w.kind) for w in ws], [(2, "DWELL_SHORT")])
        w = ws[0]
        self.assertEqual(w.line, "")
        self.assertRegex(w.value, r"^1\.3\d초 < 1\.5초$")
        self.assertEqual(str(w), f'scene 2: DWELL_SHORT ({w.value}) "ab"')

    def test_long_scene_warns(self):
        spec = {"scenes": [{"top": "t", "lines": ["가" * 15] * 6}, {"top": "", "lines": ["가" * 12] * 2}]}
        ws = motion.dwell_warnings(spec, motion.schedule(spec))
        self.assertEqual([(w.scene, w.kind) for w in ws], [(1, "DWELL_LONG")])
        self.assertRegex(ws[0].value, r"^\d\.\d\d초 > 6초$")
        self.assertTrue(str(ws[0]).startswith("scene 1: DWELL_LONG ("))
        self.assertTrue(str(ws[0]).endswith('"' + "가" * 15 + '"'))

    def test_text_is_first_line_cut_to_30(self):
        spec = {"scenes": [{"top": "", "lines": ["<g>" + "가" * 40 + "</g>"] * 3}]}
        ws = motion.dwell_warnings(spec, motion.schedule(spec))
        self.assertEqual(ws[0].text, "가" * 30)

    def test_layout_warning_with_line_keeps_old_string(self):
        w = layout.LayoutWarning(3, "2", "WRAP", "2 lines", "abc")
        self.assertEqual(str(w), 'scene 3 line 2: WRAP (2 lines) "abc"')

    def test_constants_are_single_source(self):
        self.assertEqual((motion.DWELL_MIN, motion.DWELL_MAX, motion.READ_BASE, motion.READ_CPS), (1.5, 6.0, 0.6, 16))

    def test_basic_render_returns_dwell_warning_and_strict_exits_3(self):
        tmp = Path(tempfile.mkdtemp(prefix="test-motion-dwell-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        short = tmp / "short.json"
        short.write_text(json.dumps({**TINY, "motion": "basic"}, ensure_ascii=False), encoding="utf-8")
        res = render.render_reel(short, tmp / "short.mp4", layout="new")
        self.assertEqual([w.kind for w in res.warnings], ["DWELL_SHORT"])
        r = run_reel(short, tmp / "strict.mp4", "--layout", "new", "--strict")
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("DWELL_SHORT", r.stderr)
        # none 은 시간 경고를 계산하지 않는다
        none = tmp / "none.json"
        none.write_text(json.dumps(TINY, ensure_ascii=False), encoding="utf-8")
        res = render.render_reel(none, tmp / "none.mp4", layout="new")
        self.assertEqual(res.warnings, [])


class CheckDuration(unittest.TestCase):
    @staticmethod
    def house(spec):
        warns, errs = [], []
        check._house_pattern(spec, warns.append, errs.append)
        return [w.kind for w in warns], [e.kind for e in errs]

    def test_basic_uses_schedule_total(self):
        spec = uniform_spec(7, 3, 2)   # none 25.2초(범위 안), basic 12.8초(범위 밖)
        self.assertTrue(21.0 <= timeline.total_duration(timeline.build_states(spec)) <= 27.0)
        self.assertNotIn("DURATION", self.house(spec)[0])
        spec["motion"] = "basic"
        self.assertIn("DURATION", self.house(spec)[0])

    def test_basic_in_range_while_none_total_is_not(self):
        spec = uniform_spec(7, 2, 14)  # none 19.25초(범위 밖), basic 21.6초(범위 안)
        self.assertIn("DURATION", self.house(spec)[0])
        spec["motion"] = "basic"
        self.assertNotIn("DURATION", self.house(spec)[0])

    def test_unknown_motion_is_an_error_not_a_crash(self):
        spec = uniform_spec(7, 3, 2)
        spec["motion"] = "calm"
        warns, errs = self.house(spec)
        self.assertEqual(errs, ["MOTION"])
        self.assertNotIn("DURATION", warns)

    def test_check_spec_reports_motion_error(self):
        spec = pension_countup_spec()
        spec["motion"] = "calm"
        rep = check.check_spec(spec, figures.load_registry())
        motion_errs = [e for e in rep.errors if e.kind == "MOTION"]
        self.assertEqual([e.where for e in motion_errs], ["motion"])


if __name__ == "__main__":
    unittest.main()
