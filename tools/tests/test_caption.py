"""reelkit.caption / expand series / draft.py caption 시험 (stdlib unittest 전용)."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from reelkit import caption, check, figures  # noqa: E402
from reelkit.expand import ExpandError, expand_source, next_line, series_top  # noqa: E402

FIX = TOOLS / "tests" / "fixtures"
SRC = FIX / "draft-pension.src.json"
CAP = FIX / "draft-pension.caption.src.json"
DRAFT = TOOLS / "draft.py"
TEASER = "<s>다음 편: IRP 세액공제 개정안</s>"
CTA_LINE = "<s>프로필 링크 · 1분 노후자금 계산기</s>"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()
        cls.src = load(SRC)
        cls.spec = expand_source(cls.src, cls.registry)
        cls.cap_src = load(CAP)
        cls.config = caption.load_config()

    def build(self, spec=None, cap_src=None, config=None):
        return caption.build_caption(spec or self.spec, cap_src or self.cap_src, config or self.config)


class SeriesExpand(Base):
    def test_scene1_top_and_cta_lines(self):
        s = self.spec
        self.assertEqual(s["series"], {"name": "연말정산 바로 알기", "episode": 2, "next": "IRP 세액공제 개정안"})
        self.assertEqual(s["scenes"][0]["top"], "연말정산 바로 알기 ②")
        self.assertEqual(s["scenes"][-1]["lines"], ["저장해두고", "내 납입액부터", "확인해 보세요", TEASER, CTA_LINE])

    def test_series_follows_version(self):
        self.assertEqual(list(self.spec)[:2], ["version", "series"])

    def test_ledger_spans_match_text(self):
        for entry in self.spec["figures"]:
            where = entry["where"]
            if where == "basis":
                text = self.spec["basis"]
            else:
                parts = where.split()
                sc = self.spec["scenes"][int(parts[1]) - 1]
                text = sc["top"] if parts[2] == "top" else sc["lines"][int(parts[3]) - 1]
            self.assertEqual(text[entry["start"]:entry["end"]], entry["text"], where)

    def test_check_clean(self):
        rep = check.check_spec(self.spec, self.registry)
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])

    def test_formatters(self):
        series = {"name": "가나", "episode": 10, "next": "다음"}
        self.assertEqual(series_top(series), "가나 ⑩")
        self.assertEqual(series_top({"name": "가나"}), "가나")
        self.assertEqual(next_line(series), "<s>다음 편: 다음</s>")
        self.assertIsNone(next_line({"name": "가나"}))

    def mutated(self, fn):
        src = copy.deepcopy(self.src)
        fn(src)
        return src

    def test_conflicting_scene1_top(self):
        src = self.mutated(lambda s: s["scenes"][0].update(top="다른 제목"))
        with self.assertRaisesRegex(ExpandError, "scene 1 top"):
            expand_source(src, self.registry)

    def test_equal_scene1_top_kept(self):
        src = self.mutated(lambda s: s["scenes"][0].update(top="연말정산 바로 알기 ②"))
        self.assertEqual(expand_source(src, self.registry)["scenes"][0]["top"], "연말정산 바로 알기 ②")

    def test_episode_out_of_range(self):
        for ep in (11, 0, True, "2"):
            src = self.mutated(lambda s, ep=ep: s["series"].update(episode=ep))
            with self.assertRaisesRegex(ExpandError, "series.episode"):
                expand_source(src, self.registry)

    def test_series_bad_fields(self):
        for key, val in (("name", ""), ("next", "<b>"), ("name", "{{x}}"), ("extra", 1)):
            src = self.mutated(lambda s, key=key, val=val: s["series"].update({key: val}))
            with self.assertRaises(ExpandError, msg=key):
                expand_source(src, self.registry)

    def test_different_existing_teaser(self):
        src = self.mutated(lambda s: s["scenes"][-1]["lines"].insert(3, "<s>다음 편: 다른 주제</s>"))
        with self.assertRaisesRegex(ExpandError, "다음 편"):
            expand_source(src, self.registry)

    def test_identical_existing_teaser_not_duplicated(self):
        src = self.mutated(lambda s: s["scenes"][-1]["lines"].insert(3, TEASER))
        lines = expand_source(src, self.registry)["scenes"][-1]["lines"]
        self.assertEqual(lines.count(TEASER), 1)

    def test_teaser_appended_without_profile_line(self):
        src = self.mutated(lambda s: s["scenes"][-1]["lines"].pop())
        self.assertEqual(expand_source(src, self.registry)["scenes"][-1]["lines"][-1], TEASER)

    def test_no_series_leaves_scene1_alone(self):
        src = self.mutated(lambda s: s.pop("series"))
        spec = expand_source(src, self.registry)
        self.assertNotIn("series", spec)
        self.assertEqual(spec["scenes"][0]["top"], "")


class BuildCaption(Base):
    def test_layout(self):
        text, warns = self.build()
        lines = text.splitlines()
        self.assertEqual(warns, [])
        self.assertEqual(lines[0], "연말정산 바로 알기 ② | 연금계좌 세액공제, 한도가 얼마일까?")
        self.assertEqual(lines[1], "")
        self.assertEqual([ln[:2] for ln in lines[2:5]], ["• "] * 3)
        self.assertIn("근거 · 기준: 900만 원 납입 예시 · 지방소득세 포함 (2026년 10월 기준)", lines)
        self.assertIn(self.config["disclaimer"], lines)
        self.assertIn(self.config["cta"], lines)
        self.assertIn("다음 편: IRP 세액공제 개정안", lines)
        self.assertEqual(lines[-1], "#연금저축 #IRP #세액공제 #연말정산")
        self.assertTrue(text.endswith("\n"))
        order = [lines.index(x) for x in (self.config["disclaimer"], self.config["cta"],
                                           "다음 편: IRP 세액공제 개정안", lines[-1])]
        self.assertEqual(order, sorted(order))

    def test_config_defaults(self):
        self.assertEqual(self.config["brand_hashtags"], [])
        self.assertEqual(self.config["max_hashtags"], 5)
        for word in ("보장", "확정", "무조건", "반드시"):
            self.assertNotIn(word, self.config["disclaimer"] + self.config["cta"])

    def test_brand_tags_first_and_counted(self):
        cfg = dict(self.config, brand_hashtags=["#키움멘토"])
        text, _ = self.build(config=cfg)
        self.assertEqual(text.splitlines()[-1], "#키움멘토 #연금저축 #IRP #세액공제 #연말정산")
        too_many = dict(self.cap_src, hashtags=self.cap_src["hashtags"] + ["#노후"])
        with self.assertRaisesRegex(caption.CaptionError, "최대 5개"):
            self.build(cap_src=too_many, config=cfg)

    def cap(self, **kw):
        return dict(copy.deepcopy(self.cap_src), **kw)

    def test_six_tags(self):
        with self.assertRaisesRegex(caption.CaptionError, "6개"):
            self.build(cap_src=self.cap(hashtags=["#가", "#나", "#다", "#라", "#마", "#바"]))

    def test_duplicate_tag(self):
        with self.assertRaisesRegex(caption.CaptionError, "중복"):
            self.build(cap_src=self.cap(hashtags=["#IRP", "#irp", "#세액공제"]))

    def test_malformed_tag(self):
        for tag in ("#연금 저축", "연금저축", "#", "##a"):
            with self.assertRaisesRegex(caption.CaptionError, "해시태그 형식"):
                self.build(cap_src=self.cap(hashtags=[tag, "#a", "#b"]))

    def test_few_topic_tags_warns(self):
        _, warns = self.build(cap_src=self.cap(hashtags=["#IRP", "#세액공제"]))
        self.assertTrue(any("해시태그" in w for w in warns))

    def test_series_keys_refused(self):
        for key in ("next", "series", "episode"):
            with self.assertRaisesRegex(caption.CaptionError, "D-10"):
                self.build(cap_src=self.cap(**{key: "x"}))

    def test_unknown_and_missing_keys(self):
        with self.assertRaisesRegex(caption.CaptionError, "알 수 없는 키"):
            self.build(cap_src=self.cap(extra=1))
        bad = self.cap()
        del bad["hook"]
        with self.assertRaisesRegex(caption.CaptionError, "필요한 키"):
            self.build(cap_src=bad)

    def test_summary_shape_and_markup(self):
        with self.assertRaisesRegex(caption.CaptionError, "3개"):
            self.build(cap_src=self.cap(summary=["하나", "둘"]))
        for bad in ("<g>강조</g>", "줄\n바꿈", "{{x}}"):
            with self.assertRaises(caption.CaptionError):
                self.build(cap_src=self.cap(hook=bad))

    def test_number_not_in_spec(self):
        s = self.cap()["summary"]
        s[0] = "연금저축만 넣으면 연 200만 원까지"
        with self.assertRaisesRegex(caption.CaptionError, "'200만 원' 는 원고에 없음"):
            self.build(cap_src=self.cap(summary=s))

    def test_hangul_number_not_in_spec(self):
        # CR-04 회귀: 게시글의 '두 배', '천만 원' 도 원고에 없는 숫자다
        for text in ("세액공제가 두 배", "천만 원 모으기"):
            s = self.cap()["summary"]
            s[0] = text
            with self.subTest(text=text):
                with self.assertRaisesRegex(caption.CaptionError, "원고에 없음"):
                    self.build(cap_src=self.cap(summary=s))

    def test_spec_top_altered(self):
        spec = copy.deepcopy(self.spec)
        spec["scenes"][0]["top"] = "다른 제목"
        with self.assertRaisesRegex(caption.CaptionError, "scene 1 top"):
            self.build(spec=spec)

    def test_spec_teaser_missing(self):
        spec = copy.deepcopy(self.spec)
        spec["scenes"][-1]["lines"].remove(TEASER)
        with self.assertRaisesRegex(caption.CaptionError, "series.next"):
            self.build(spec=spec)

    def test_too_long(self):
        cfg = dict(self.config, disclaimer="가" * 2200)
        with self.assertRaisesRegex(caption.CaptionError, "2200자"):
            self.build(config=cfg)

    def test_spec_without_series(self):
        spec = copy.deepcopy(self.spec)
        del spec["series"]
        text, _ = self.build(spec=spec)
        self.assertEqual(text.splitlines()[0], self.cap_src["hook"])
        self.assertNotIn("다음 편:", text)

    def test_long_first_line_warns(self):
        _, warns = self.build(cap_src=self.cap(hook="연금계좌 세액공제 한도가 얼마인지 쉽게 알려드립니다 지금 바로 확인해 보세요 오늘"))
        self.assertTrue(any("첫 줄" in w for w in warns))

    def test_config_validation(self):
        tmp = Path(tempfile.mkdtemp(prefix="test-cap-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for patch in ({"max_hashtags": 6}, {"brand_hashtags": ["브랜드"]}, {"disclaimer": ""}):
            p = tmp / "c.json"
            p.write_text(json.dumps(dict(self.config, **patch), ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(caption.CaptionError, msg=str(patch)):
                caption.load_config(p)


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-cap-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_draft(self, *args):
        return subprocess.run([sys.executable, str(DRAFT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8")

    def expanded(self):
        spec = self.tmp / "spec.json"
        r = self.run_draft("expand", SRC, spec)
        self.assertEqual(r.returncode, 0, r.stderr)
        return spec

    def test_caption_writes_file(self):
        out = self.tmp / "sub" / "caption.txt"
        r = self.run_draft("caption", self.expanded(), CAP, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("해시태그 4개", r.stdout)
        self.assertTrue(out.read_text(encoding="utf-8").startswith("연말정산 바로 알기 ② | "))

    def test_bad_src_exits_1_without_traceback(self):
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps({"hook": "a", "summary": ["a", "b", "c"], "hashtags": [], "next": "x"}),
                       encoding="utf-8")
        out = self.tmp / "caption.txt"
        r = self.run_draft("caption", self.expanded(), bad, "--out", out)
        self.assertEqual(r.returncode, 1)
        self.assertIn("초안 오류", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse(out.exists())

    def test_missing_and_broken_files(self):
        spec = self.expanded()
        for src in (self.tmp / "nope.json",):
            r = self.run_draft("caption", spec, src, "--out", self.tmp / "o.txt")
            self.assertEqual(r.returncode, 1)
            self.assertNotIn("Traceback", r.stderr)
        broken = self.tmp / "broken.json"
        broken.write_text("{", encoding="utf-8")
        r = self.run_draft("caption", spec, broken, "--out", self.tmp / "o.txt")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
