"""노트 배치(layout "note") 시험: 검증, expand 의 장면 유도·장부, 시간표, check, 폰트, 렌더(번들 한 번) (stdlib unittest 전용).

렌더가 필요한 시험(번들 end-to-end, 최종 프레임 기하, 폰트 로드)만 Chromium 을 띄우며, 그 밖은 순수 함수 시험이다.
"""
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
FIX = Path(__file__).resolve().parent / "fixtures"
DRAFT = [sys.executable, str(TOOLS / "draft.py")]
sys.path.insert(0, str(TOOLS))

from reelkit import check, constants, doctor, expand, figures, note, spec as spec_mod, stills  # noqa: E402
from reelkit.expand import ExpandError, expand_source  # noqa: E402

SRC = FIX / "draft-note.src.json"
CAPTION_SRC = FIX / "draft-note.caption.src.json"


def load_src():
    return json.loads(SRC.read_text(encoding="utf-8"))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


def note_src(**over):
    """고정 소스를 깊은 복사한 뒤 note 블록의 키를 바꾼다."""
    src = load_src()
    src["note"].update(over)
    return src


class Validation(unittest.TestCase):
    """note 블록 검사: 1~2 제목 줄, highlight 범위, 상자 1~2개, 항목 1~5개, 색, 알 수 없는 키 거부."""

    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()

    def bad(self, mutate, needle):
        src = load_src()
        mutate(src)
        with self.assertRaises(ExpandError) as cm:
            expand_source(src, self.registry)
        self.assertIn(needle, str(cm.exception))

    def test_fixture_is_valid(self):
        note.validate_note(load_src()["note"])

    def test_title_lines_1_to_2(self):
        self.bad(lambda s: s["note"].update(title=[]), "note.title")
        self.bad(lambda s: s["note"].update(title=["a", "b", "c"]), "note.title")
        self.bad(lambda s: s["note"].update(title=["a", ""]), "note.title[2]")
        self.bad(lambda s: s["note"].update(title="문자열"), "note.title")

    def test_highlight_index(self):
        self.bad(lambda s: s["note"].update(highlight=2), "note.highlight")
        self.bad(lambda s: s["note"].update(highlight=-1), "note.highlight")
        self.bad(lambda s: s["note"].update(highlight=True), "note.highlight")
        self.bad(lambda s: s["note"].update(highlight="1"), "note.highlight")

    def test_highlight_is_optional(self):
        src = load_src()
        del src["note"]["highlight"]
        out = expand_source(src, self.registry)
        self.assertNotIn("highlight", out["note"])

    def test_boxes_1_to_2(self):
        self.bad(lambda s: s["note"].update(boxes=[]), "note.boxes")
        box = load_src()["note"]["boxes"][0]
        self.bad(lambda s: s["note"].update(boxes=[box, box, box]), "note.boxes")
        src = load_src()
        src["note"]["boxes"] = [box]
        self.assertEqual(len(expand_source(src, self.registry)["note"]["boxes"]), 1)

    def test_items_1_to_5(self):
        self.bad(lambda s: s["note"]["boxes"][0].update(items=[]), "note.boxes[1].items")
        self.bad(lambda s: s["note"]["boxes"][1].update(items=list("abcdef")), "note.boxes[2].items")
        self.bad(lambda s: s["note"]["boxes"][0]["items"].append(""), "note.boxes[1].items[5]")
        src = load_src()
        src["note"]["boxes"][0]["items"] = list("abcde")
        self.assertEqual(len(expand_source(src, self.registry)["scenes"][1]["lines"]), 5)

    def test_color_only_green_or_gold(self):
        self.bad(lambda s: s["note"]["boxes"][0].update(color="red"), "note.boxes[1].color")
        self.bad(lambda s: s["note"]["boxes"][0].update(color=1), "note.boxes[1].color")

    def test_color_defaults_by_box_order(self):
        src = load_src()
        for box in src["note"]["boxes"]:
            del box["color"]
        out = expand_source(src, self.registry)
        self.assertEqual([b["color"] for b in out["note"]["boxes"]], ["green", "gold"])

    def test_unknown_keys_rejected(self):
        self.bad(lambda s: s["note"].update(extra=1), "note: 알 수 없는 키 extra")
        self.bad(lambda s: s["note"]["boxes"][0].update(icon="x"), "note.boxes[1]: 알 수 없는 키 icon")

    def test_text_must_be_plain(self):
        self.bad(lambda s: s["note"]["boxes"][0]["items"].__setitem__(0, "<g>카드</g>"), "note.boxes[1].items[1]")
        self.bad(lambda s: s["note"].update(footer="줄\n바꿈"), "note.footer")
        self.bad(lambda s: s["note"]["boxes"][0].update(head=5), "note.boxes[1].head")

    def test_layout_and_note_go_together(self):
        self.bad(lambda s: s.pop("layout"), "note 블록은")
        self.bad(lambda s: s.pop("note"), "note 블록이 필요")
        self.bad(lambda s: s.update(layout="grid"), "layout:")
        self.bad(lambda s: s.update(scenes=[{"top": "t", "lines": ["a"]}]), "scenes 를 직접 쓰지 않음")
        self.bad(lambda s: s.update(motion="basic"), "motion")

    def test_countup_marker_rejected_in_note_text(self):
        self.bad(lambda s: s["note"]["boxes"][0]["items"].__setitem__(0, "{{fig.income_tax_rate_b1|pct|up}}"), "|up")

    def test_spec_loader_rejects_note_without_layout_and_vice_versa(self):
        d = Path(tempfile.mkdtemp(prefix="test-note-"))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        good = expand_source(load_src(), self.registry)
        for name, mutate, needle in (
                ("nolayout", lambda s: s.pop("layout"), "함께"),
                ("nonote", lambda s: s.pop("note"), "함께"),
                ("badnote", lambda s: s["note"].update(title=[]), "note.title"),
                ("placeholder", lambda s: s["note"]["boxes"][0]["items"].__setitem__(0, "{{x|num}}"), "확장 전")):
            s = copy.deepcopy(good)
            mutate(s)
            p = d / f"{name}.json"
            p.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(spec_mod.SpecError, msg=name) as cm:
                spec_mod.load_spec(p)
            self.assertIn(needle, str(cm.exception), name)
        p = d / "good.json"
        p.write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(spec_mod.load_spec(p)["layout"], "note")


class ExpandCli(unittest.TestCase):
    """검증 오류는 draft.py expand 에서 종료 코드 1 (MP4·spec 을 만들지 않음)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-note-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def expand(self, src):
        p = self.tmp / "src.json"
        p.write_text(json.dumps(src, ensure_ascii=False), encoding="utf-8")
        out = self.tmp / "spec.json"
        return run(DRAFT + ["expand", str(p), str(out)]), out

    def test_valid_source_exits_0(self):
        r, out = self.expand(load_src())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(out.is_file())

    def test_validation_errors_exit_1_without_output(self):
        cases = [
            ("unknown note key", note_src(extra=1), "알 수 없는 키 extra"),
            ("three title lines", note_src(title=["a", "b", "c"]), "note.title"),
            ("six items", None, "note.boxes[1].items"),
            ("bad colour", None, "note.boxes[1].color"),
            ("bad highlight", note_src(highlight=5), "note.highlight"),
        ]
        cases[2] = (cases[2][0], self._with(lambda s: s["note"]["boxes"][0].update(items=list("abcdef"))), cases[2][2])
        cases[3] = (cases[3][0], self._with(lambda s: s["note"]["boxes"][0].update(color="blue")), cases[3][2])
        for name, src, needle in cases:
            with self.subTest(name):
                r, out = self.expand(src)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn(needle, r.stderr)
                self.assertFalse(out.exists())

    @staticmethod
    def _with(mutate):
        src = load_src()
        mutate(src)
        return src


class Derivation(unittest.TestCase):
    """expand 가 note 블록에서 표준 scenes 를 만들고 자리표시자를 장부에 남긴다."""

    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()
        cls.out = expand_source(load_src(), cls.registry)

    def test_scene_structure(self):
        scenes = self.out["scenes"]
        self.assertEqual(self.out["layout"], "note")
        self.assertEqual(len(scenes), 5)   # 제목 + 상자 2 + 꼭 알아둘 것 + CTA
        self.assertEqual(scenes[0], {"top": "", "lines": ["연말정산 공제,", "어디에 들어갈까?"]})
        self.assertEqual(scenes[1]["top"], "소득공제 · 가격표 깎기")
        self.assertEqual(scenes[1]["lines"], ["카드 사용액", "국민연금 보험료", "주택청약 납입액", "전세대출 원리금 상환"])
        self.assertEqual(scenes[2]["top"], "세액공제 · 계산대 쿠폰")
        self.assertEqual(scenes[3], {"top": "단, 꼭 알아둘 것", "lines": ["※ 세무 판단은 세무사 확인!"]})
        self.assertEqual(scenes[4]["top"], "")
        self.assertTrue(any("프로필 링크" in ln for ln in scenes[4]["lines"]))

    def test_note_block_is_kept_for_the_renderer(self):
        n = self.out["note"]
        self.assertEqual(n["title"], self.out["scenes"][0]["lines"])
        self.assertEqual(n["highlight"], 1)
        self.assertEqual([(b["head"], b["sub"], b["color"]) for b in n["boxes"]],
                         [("소득공제", "가격표 깎기", "green"), ("세액공제", "계산대 쿠폰", "gold")])
        self.assertEqual(n["footer"], "※ 세무 판단은 세무사 확인!")
        note.validate_note(n)

    def test_without_footer_there_is_no_caution_scene(self):
        src = load_src()
        del src["note"]["footer"]
        scenes = expand_source(src, self.registry)["scenes"]
        self.assertEqual(len(scenes), 4)
        self.assertNotIn("단, 꼭 알아둘 것", [s["top"] for s in scenes])

    def test_series_fills_title_scene_and_cta_teaser(self):
        src = load_src()
        src["series"] = {"name": "연말정산 바로 알기", "episode": 3, "next": "연금저축 세액공제 한도"}
        out = expand_source(src, self.registry)
        self.assertEqual(out["scenes"][0]["top"], "연말정산 바로 알기 ③")
        self.assertIn("<s>다음 편: 연금저축 세액공제 한도</s>", out["scenes"][-1]["lines"])
        self.assertEqual(out["note"]["title"], ["연말정산 공제,", "어디에 들어갈까?"])   # 시리즈는 note 글자를 바꾸지 않는다

    def test_placeholders_in_note_text_expand_and_are_ledgered(self):
        src = load_src()
        src["note"]["boxes"][0]["items"][0] = "기본세율 {{fig.income_tax_rate_b1|pct}}"
        src["note"]["boxes"][0]["sub"] = "상한 {{fig.pension_credit_wage_threshold|man_won}}"
        src["note"]["footer"] = "※ 지방소득세 {{fig.local_income_tax_ratio|pct}} 별도"
        out = expand_source(src, self.registry)
        self.assertEqual(out["note"]["boxes"][0]["items"][0], "기본세율 6%")
        self.assertEqual(out["scenes"][1]["lines"][0], "기본세율 6%")
        self.assertEqual(out["note"]["boxes"][0]["sub"], "상한 5,500만 원")
        self.assertEqual(out["note"]["boxes"][0]["head"], "소득공제")
        self.assertEqual(out["note"]["footer"], "※ 지방소득세 10% 별도")
        by_where = {e["where"]: e for e in out["figures"]}
        self.assertEqual(set(by_where), {"scene 2 line 1", "scene 2 top", "scene 4 line 1"})
        e = by_where["scene 2 line 1"]
        self.assertEqual((e["ref"], e["fmt"], e["text"]), ("fig.income_tax_rate_b1", "pct", "6%"))
        self.assertEqual(out["scenes"][1]["lines"][0][e["start"]:e["end"]], "6%")
        self.assertEqual({i["fig"] for i in out["basis_items"]},
                         {"income_tax_rate_b1", "pension_credit_wage_threshold", "local_income_tax_ratio"})
        self.assertNotIn("{{", json.dumps(out, ensure_ascii=False))

    def test_unknown_placeholder_in_note_is_an_expand_error(self):
        src = load_src()
        src["note"]["boxes"][0]["items"][0] = "{{fig.없는_id|pct}}"
        with self.assertRaises(ExpandError):
            expand_source(src, self.registry)

    def test_unit_after_placeholder_rule_applies_to_note_text(self):
        src = load_src()
        src["note"]["boxes"][0]["items"][0] = "{{fig.pension_credit_wage_threshold|man_won}}원"
        with self.assertRaises(ExpandError):
            expand_source(src, self.registry)

    def test_plain_specs_do_not_gain_layout_or_note(self):
        plain = json.loads((FIX / "draft-tax.src.json").read_text(encoding="utf-8"))
        out = expand_source(plain, self.registry)
        self.assertNotIn("layout", out)
        self.assertNotIn("note", out)
        self.assertEqual(len(out["scenes"]), 7)

    def test_source_with_layout_other_than_note_is_rejected(self):
        plain = json.loads((FIX / "draft-tax.src.json").read_text(encoding="utf-8"))
        plain["layout"] = "legacy"
        with self.assertRaises(ExpandError):
            expand_source(plain, self.registry)
        plain["layout"] = "note"   # note 블록 없이 layout 만
        with self.assertRaises(ExpandError):
            expand_source(plain, self.registry)


class CheckIntegration(unittest.TestCase):
    """기존 점검(장부, 하우스 패턴, 소스 대조)이 노트 원고에서 그대로 돌고 노트 기준을 쓴다."""

    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()
        cls.out = expand_source(load_src(), cls.registry)

    def test_fixture_has_no_errors_or_warnings(self):
        report = check.check_spec(self.out, self.registry)
        self.assertEqual([str(i) for i in report.errors], [])
        self.assertEqual([str(i) for i in report.warnings], [])

    def test_hand_edited_note_is_a_source_mismatch(self):
        edited = copy.deepcopy(self.out)
        edited["note"]["boxes"][0]["items"][0] = "손으로 고침"
        kinds = [i.kind for i in check.compare_source(edited, load_src(), self.registry)]
        self.assertEqual(kinds, ["SOURCE_MISMATCH"])
        self.assertEqual(check.compare_source(self.out, load_src(), self.registry), [])

    def test_hand_edited_scenes_are_a_source_mismatch(self):
        edited = copy.deepcopy(self.out)
        edited["scenes"][1]["lines"][0] = "손으로 고침"
        self.assertEqual([i.kind for i in check.compare_source(edited, load_src(), self.registry)], ["SOURCE_MISMATCH"])

    def test_numbers_in_note_text_are_ledger_checked(self):
        src = load_src()
        src["note"]["boxes"][0]["items"][0] = "세율 6%"
        report = check.check_spec(expand_source(src, self.registry), self.registry)
        self.assertIn("UNREGISTERED", [i.kind for i in report.errors])

    def test_short_note_warns_duration_with_note_bounds(self):
        src = load_src()
        src["note"]["boxes"] = [{"head": "소득공제", "items": ["카드 사용액"]}]
        src["note"]["title"] = ["공제"]
        del src["note"]["footer"], src["note"]["highlight"]
        report = check.check_spec(expand_source(src, self.registry), self.registry)
        kinds = [i.kind for i in report.warnings]
        self.assertIn("DURATION", kinds)
        self.assertIn("노트 하우스 패턴", [i for i in report.warnings if i.kind == "DURATION"][0].detail)
        self.assertNotIn("SCENES", kinds)
        self.assertNotIn("NO_EMPH", kinds)


class Schedule(unittest.TestCase):
    def test_fixture_schedule(self):
        s = note.schedule(load_src()["note"])
        self.assertGreaterEqual(s.hold, 6.0)
        self.assertGreaterEqual(s.total, note.DUR_MIN)
        self.assertLessEqual(s.total, note.DUR_MAX)
        self.assertAlmostEqual(s.total, s.nframes / constants.FPS)
        self.assertAlmostEqual(s.total - s.anim_end, s.hold, delta=1 / constants.FPS)
        self.assertGreaterEqual(s.cover_t, s.anim_end)
        # 순서: 제목 -> 상자 1 -> 항목 -> 상자 2 -> 항목 -> 꼭 알아둘 것 -> 근거·계정명
        order = [t[0] for t in s.title] + [s.boxes[0][0]] + [t[0] for t in s.items[0]] + [s.boxes[1][0]] \
            + [t[0] for t in s.items[1]] + [s.footer[0], s.foot[0]]
        self.assertEqual(order, sorted(order))
        self.assertGreater(s.title[1][0], s.title[0][0])
        self.assertGreaterEqual(s.boxes[0][0], s.title[1][0] + s.title[1][1])
        self.assertGreaterEqual(s.boxes[1][0], s.items[0][-1][0] + s.items[0][-1][1])

    def test_more_items_take_longer(self):
        n = load_src()["note"]
        short = copy.deepcopy(n)
        for box in short["boxes"]:
            box["items"] = box["items"][:2]
        longer = copy.deepcopy(n)
        for box in longer["boxes"]:
            box["items"] = box["items"] + ["다섯째 항목"]
        a, b, c = (note.schedule(x) for x in (short, n, longer))
        self.assertLess(a.anim_end, b.anim_end)
        self.assertLess(b.anim_end, c.anim_end)
        self.assertLessEqual(c.total, note.DUR_MAX)
        for s in (a, b, c):
            self.assertGreaterEqual(s.hold, 6.0)

    def test_short_notes_get_a_longer_hold_up_to_the_cap(self):
        tiny = {"title": ["공제"], "boxes": [{"head": "가", "items": ["나"]}]}
        s = note.schedule(tiny)
        self.assertLessEqual(s.hold, note.HOLD_MAX)
        self.assertGreater(s.hold, note.HOLD_MIN)

    def test_scene_times_match_derived_scenes(self):
        out = expand_source(load_src(), figures.load_registry())
        times = stills.scene_times(out)
        self.assertEqual(len(times), len(out["scenes"]))
        self.assertEqual(times, sorted(times))


class FontFiles(unittest.TestCase):
    def test_pinned_sha256_matches_vendored_file_and_readme(self):
        path = constants.FONTS_DIR / constants.NOTE_FONT_FILE
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), constants.NOTE_FONT_SHA256)
        readme = (constants.FONTS_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn(constants.NOTE_FONT_SHA256, readme)
        self.assertIn("raw.githubusercontent.com/google/fonts/main/ofl/gaegu/", readme)
        self.assertIn("OFL", (constants.FONTS_DIR / "OFL-Gaegu.txt").read_text(encoding="utf-8"))

    def test_doctor_reports_note_font_without_adding_a_check(self):
        self.assertEqual(doctor.check_note_font(), [])
        files = doctor.check_font_files()
        merged = doctor._with_note_font(files, constants.FONTS_DIR)
        self.assertEqual((merged.name, merged.level), ("font-files", "ok"))
        self.assertIn(constants.NOTE_FONT_FILE, merged.detail)
        self.assertTrue(merged.detail.startswith(files.detail))

    def test_doctor_warns_when_note_font_is_missing_or_changed(self):
        d = Path(tempfile.mkdtemp(prefix="test-note-fonts-"))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.assertIn("없음", doctor.check_note_font(d)[0])
        (d / constants.NOTE_FONT_FILE).write_bytes(b"garbage")
        self.assertIn("sha256", doctor.check_note_font(d)[0])
        ok = doctor.Check("font-files", "ok", "3/3 sha256 일치")
        warned = doctor._with_note_font(ok, d)
        self.assertEqual(warned.level, "warn")
        failed = doctor.Check("font-files", "fail", "x")
        self.assertIs(doctor._with_note_font(failed, d), failed)   # 기존 실패는 가리지 않는다


class RenderedPage(unittest.TestCase):
    """Chromium 으로 노트 페이지를 열어 폰트 로드와 최종 프레임 기하를 본다 (인코딩 없음)."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        from reelkit import browser
        cls.pw = sync_playwright().start()
        cls.browser, _used = browser.launch(cls.pw)
        cls.work = tempfile.mkdtemp(prefix="test-note-page-")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        shutil.rmtree(cls.work, ignore_errors=True)

    def open(self, n, basis="주요 항목 예시 · 요건·한도 별도 확인"):
        sched = note.schedule(n)
        page = note.open_page(self.browser, self.work, n, basis, sched)
        self.addCleanup(page.close)
        return page, sched

    def test_fonts_load(self):
        page, _ = self.open(load_src()["note"])
        self.assertEqual(note.font_statuses(page), {"Gaegu 700": "loaded", "Noto Sans KR 700": "loaded"})
        self.assertEqual(note.font_problems(page), [])
        # 손글씨 글자는 실제로 Gaegu 로 그려진다 (시스템 폰트로 대체되지 않음)
        from reelkit import browser
        _measure, warnings = note.final_state(page, load_src()["note"], note.schedule(load_src()["note"]))
        self.assertEqual([str(w) for w in warnings if w.kind == "FONT_FALLBACK"], [])
        used = browser.platform_fonts(page, '[data-nt="title|1"]')[0]
        self.assertEqual([f["familyName"] for f in used], ["Gaegu"])

    def test_final_frame_stays_in_safe_area_and_inside_boxes(self):
        n = load_src()["note"]
        page, sched = self.open(n)
        measure, warnings = note.final_state(page, n, sched)
        self.assertEqual([str(w) for w in warnings], [])
        for m in measure["items"]:
            self.assertGreaterEqual(m["t"], constants.SAFE["top"], m["nt"])
            self.assertLessEqual(m["r"], constants.W - constants.SAFE["right"], m["nt"])
            self.assertLessEqual(m["b"], constants.H - constants.SAFE["bottom_ui"], m["nt"])
            if m["lim"] is not None:
                self.assertLessEqual(m["r"], m["lim"] + 0.5, f"{m['nt']} 가 상자 밖으로 넘침")
        self.assertLessEqual(measure["flowBottom"], measure["footTop"])
        # 어떤 요소도 y 1470 아래로 내려가지 않는다 (배경 전체를 덮는 #nt-root 만 제외)
        lowest = page.evaluate("""() => Math.max(...[...document.querySelectorAll('#nt-root *')]
            .map(e => e.getBoundingClientRect().bottom))""")
        self.assertLessEqual(lowest, constants.H - constants.SAFE["bottom_ui"])
        # 항목마다 한 줄 (줄바꿈 없음), 글자는 전부 그려진 상태
        items = [m for m in measure["items"] if m["nt"].startswith("item|")]
        self.assertEqual(len(items), 8)
        self.assertTrue(all(m["n"] == 1 for m in items))
        self.assertEqual(note.crop_warnings(measure), [])

    def test_overflow_wrap_and_safe_area_are_reported_not_fixed(self):
        n = load_src()["note"]
        n["boxes"][0]["items"] = list("가나다라마")
        n["boxes"][1]["items"] = ["아주아주아주 길어서 상자 안에서 한 줄로 들어가지 않는 항목 문장입니다 정말로"] + list("가나다라")
        n["title"] = ["아주아주아주 아주아주 긴 제목 줄입니다"]
        page, sched = self.open(n)
        _measure, warnings = note.final_state(page, n, sched)
        kinds = {w.kind for w in warnings}
        self.assertIn("WRAP", kinds)
        self.assertIn("OVERFLOW", kinds)
        self.assertIn("RIGHT", kinds)
        wrapped = [w for w in warnings if w.kind == "WRAP"]
        self.assertTrue(any(w.scene == 3 and w.line == "1" for w in wrapped), [str(w) for w in wrapped])

    def test_missing_font_file_stops_instead_of_falling_back(self):
        from reelkit import browser
        n = load_src()["note"]
        sched = note.schedule(n)
        orig = note.page_html
        try:
            note.page_html = lambda *a, **k: orig(*a, **k).replace("Gaegu-Bold.ttf", "없는-폰트.ttf")
            with self.assertRaises(browser.FontLoadError):
                page = note.open_page(self.browser, self.work, n, "근거", sched)
                page.close()
        finally:
            note.page_html = orig


class BundleEndToEnd(unittest.TestCase):
    """draft.py bundle 이 노트 원고를 끝까지 만든다 (렌더 포함, 한 번만 돌린다)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-note-bundle-"))
        cls.draft = cls.tmp / "2026" / "reels" / "drafts" / "2026-11-12-note-deduction"
        cls.draft.mkdir(parents=True)
        shutil.copyfile(SRC, cls.draft / "spec.src.json")
        shutil.copyfile(CAPTION_SRC, cls.draft / "caption.src.json")
        cls.r = run(DRAFT + ["bundle", str(cls.draft)])
        cls.name = cls.draft.name

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_exit_0_and_specprobe_9_of_9(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)
        self.assertIn("spec: PASS 9/9", self.r.stderr)
        self.assertNotIn("FAIL", self.r.stderr)
        self.assertNotIn("레이아웃 경고", self.r.stderr)
        self.assertNotIn("COVER_CROP", self.r.stderr)

    def test_outputs_exist(self):
        for name in (f"{self.name}.mp4", f"{self.name}-cover.png", f"{self.name}-scenes.png", "review.md",
                     "spec.json", "check.json", "caption.txt", "compliance.json", "bundle.json",
                     f"{self.name}.safe-s01.png"):
            p = self.draft / name
            self.assertTrue(p.is_file() and p.stat().st_size > 0, name)
        for png in (f"{self.name}-cover.png", f"{self.name}-scenes.png"):
            self.assertEqual((self.draft / png).read_bytes()[:8], b"\x89PNG\r\n\x1a\n", png)

    def test_compliance_headline_and_review(self):
        review = (self.draft / "review.md").read_text(encoding="utf-8")
        result = json.loads((self.draft / "compliance.json").read_text(encoding="utf-8"))
        headline = result["headline"]
        self.assertTrue(headline)
        self.assertIn(headline, review)
        self.assertIn(headline, self.r.stdout)
        self.assertIn("사람 검수", headline)
        for text in (review, self.r.stdout, headline):
            self.assertNotIn("통과", text)
        self.assertIn("노트 형식", review)

    def test_bundle_json_records_note_layout_and_duration(self):
        data = json.loads((self.draft / "bundle.json").read_text(encoding="utf-8"))
        self.assertEqual((data["status"], data["exit_code"], data["motion"]), ("complete", 0, "note"))
        self.assertIn(f"{self.name}.mp4", data["outputs"])
        probe = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                     str(self.draft / f"{self.name}.mp4")])
        duration = float(probe.stdout.strip())
        s = note.schedule(load_src()["note"])
        self.assertAlmostEqual(duration, s.total, delta=0.2)
        self.assertGreaterEqual(duration, 18.0)
        self.assertLessEqual(duration, 27.0)

    def test_cover_is_the_finished_notebook(self):
        """표지는 모든 글이 써진 최종 프레임이다: 둘째 상자의 마지막 항목 자리와 아래쪽 근거 자리에 글자색 픽셀이 있다."""
        rows = {}
        proc = subprocess.run(["ffmpeg", "-v", "error", "-i", str(self.draft / f"{self.name}-cover.png"),
                               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        self.assertEqual(proc.returncode, 0)
        data = proc.stdout
        w, h = constants.W, constants.H
        self.assertEqual(len(data), w * h * 3)

        def dark_pixels(y0, y1):
            n = 0
            for y in range(y0, y1, 2):
                row = data[y * w * 3:(y + 1) * w * 3]
                n += sum(1 for x in range(150 * 3, 930 * 3, 12) if row[x] < 90 and row[x + 1] < 90 and row[x + 2] < 90)
            return n

        rows["title"] = dark_pixels(280, 380)
        rows["last_item"] = dark_pixels(1170, 1230)
        rows["account"] = dark_pixels(1410, 1460)
        for key, n in rows.items():
            self.assertGreater(n, 0, key)
        # 바깥 배경은 짙은 초록 (노트 배치의 색)
        self.assertEqual(tuple(data[(1600 * w + 10) * 3:(1600 * w + 10) * 3 + 3]), (0x2F, 0x4F, 0x3E))


if __name__ == "__main__":
    unittest.main()
