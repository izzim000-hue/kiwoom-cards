"""reelkit.convert / check --card / draft.py convert 시험 (stdlib unittest 전용). 게시된 2026/ 파일은 읽기만 한다."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from reelkit import check, convert  # noqa: E402
from reelkit.spec import load_spec  # noqa: E402

DRAFT = TOOLS / "draft.py"
PAIRS = {
    "tax": ("02-tax-deduction", "2026-10-26-tax-deduction"),
    "s1": ("03-salary-two-owners-1", "2026-10-28-salary-two-owners-1"),
    "s2": ("04-salary-two-owners-2", "2026-10-31-salary-two-owners-2"),
    "s3": ("05-salary-two-owners-3", "2026-11-02-salary-two-owners-3"),
    "s4": ("06-salary-two-owners-4", "2026-11-04-salary-two-owners-4"),
    "s5": ("07-salary-two-owners-5", "2026-11-07-salary-two-owners-5"),
    "ebook": ("08-ebook-event", "2026-10-29-ebook-event"),
}
EXPECTED_NEW = {
    "tax": [("scene 6 line 2", "0원")],
    "s1": [("scene 1 line 1", "25년")],
    "s2": [("scene 4 top", "4%"), ("scene 4 line 1", "72만"), ("scene 4 line 2", "151만"), ("scene 4 line 3", "329만")],
    "s3": [],
    "s4": [("scene 2 line 3", "8만")],
    "s5": [],
    "ebook": [],
}


def card_path(key):
    return REPO / "2026" / PAIRS[key][0] / "spec.json"


def reel_path(key):
    return REPO / "2026" / "reels" / "specs" / f"{PAIRS[key][1]}.json"


class Skeletons(unittest.TestCase):
    def test_tax_skeleton(self):
        sk = convert.card_skeleton(convert.load_card(card_path("tax")), "src")
        self.assertEqual(sk["series"], {"name": "연말정산 바로 알기"})
        self.assertEqual([s["role"] for s in sk["scenes"]],
                         ["hook", "body", "body", "body", "body", "conclusion", "caution", "cta"])
        hook = sk["scenes"][0]
        self.assertEqual(hook["top"], "")
        self.assertEqual(hook["material"][0], "소득공제 vs 세액공제")
        self.assertIn("<g>누가 더 돌려받을까?</g>", hook["material"])
        caution = sk["scenes"][-2]
        self.assertEqual(caution["top"], "단, 꼭 알아둘 것")
        self.assertIn("일반 정보 · 세무 판단은 세무사 확인", caution["material"])
        self.assertEqual(sk["scenes"][-1]["material"],
                         ["저장해두고", "", "", "<s>프로필 링크 · 1분 노후자금 계산기</s>"])
        self.assertEqual(len(sk["notes"]), 6)
        self.assertNotIn("<br>", json.dumps(sk, ensure_ascii=False))
        self.assertEqual(sk["source"], "src")
        self.assertTrue(all(set(n) == {"card", "raw", "cls", "value"} for n in sk["source_numbers"]))

    def test_salary1_series_and_dropped_lines(self):
        sk = convert.card_skeleton(convert.load_card(card_path("s1")), "src")
        self.assertEqual(sk["series"], {"name": "내 월급의 두 주인", "episode": 1, "next": "미래 몫부터 떼는 순서"})
        for sc in sk["scenes"]:
            for line in sc["material"]:
                if sc["role"] != "cta":
                    self.assertFalse(line.startswith("다음 편:"), line)
                    self.assertFalse(line.startswith("저장해두고"), line)
        conclusion = next(s for s in sk["scenes"] if s["role"] == "conclusion")
        self.assertEqual(conclusion["material"], ["가장 가까운 '오늘'에", "<g>먼저 쓰입니다</g>"])

    def test_episode_out_of_range_dropped(self):
        tmp = Path(tempfile.mkdtemp(prefix="test-convert-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        p = tmp / "c.json"
        p.write_text(json.dumps({"series": "긴 시리즈 12편", "cards": [{"title": "가<br>나", "lines": ["다"]}]},
                                ensure_ascii=False), encoding="utf-8")
        sk = convert.card_skeleton(convert.load_card(p), "x")
        self.assertEqual(sk["series"], {"name": "긴 시리즈"})
        self.assertEqual([s["role"] for s in sk["scenes"]], ["body", "caution", "cta"])

    def test_all_seven_cards_convert(self):
        for key in PAIRS:
            sk = convert.card_skeleton(convert.load_card(card_path(key)), "x")
            self.assertEqual(sk["scenes"][-1]["role"], "cta", key)
            self.assertNotIn("<br>", json.dumps(sk, ensure_ascii=False), key)


class Comparison(unittest.TestCase):
    def test_new_numbers_exact_per_pair(self):
        total = 0
        for key, expected in EXPECTED_NEW.items():
            got = [(w["where"], w["raw"]) for w in
                   convert.new_number_warnings(convert.load_card(card_path(key)), load_spec(reel_path(key)))]
            self.assertEqual(got, expected, key)
            total += len(got)
        self.assertEqual(total, 7)

    def test_dropped_notes_tax(self):
        notes = [d["note"] for d in
                 convert.dropped_notes(convert.load_card(card_path("tax")), load_spec(reel_path("tax")))]
        self.assertIn("종합소득자는 4,500만 원 기준", notes)
        self.assertNotIn("지방소득세 포함 · 같은 구간 가정", notes)
        self.assertNotIn("일반 정보 · 세무 판단은 세무사 확인", notes)

    def test_card_warnings_kinds(self):
        issues = check.card_warnings(convert.load_card(card_path("tax")), load_spec(reel_path("tax")))
        kinds = {i.kind for i in issues}
        self.assertEqual(kinds, {"NOT_IN_CARD", "CARD_NOTE_DROPPED"})
        drop = next(i for i in issues if i.detail == "종합소득자는 4,500만 원 기준")
        self.assertEqual(drop.where, "card 4 note")


class BadCards(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-convert-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, obj, raw=None):
        p = self.tmp / "card.json"
        p.write_text(raw if raw is not None else json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return p

    def test_shape_errors(self):
        for obj in ({"series": "a"}, {"cards": []}, {"cards": [{"lines": ["x"]}]}, {"cards": ["x"]},
                    {"cards": [{"title": "t", "lines": "x"}]}, {"cards": [{"title": "t", "note": 3}]}, [1]):
            with self.assertRaises(convert.ConvertError, msg=str(obj)):
                convert.load_card(self.write(obj))

    def test_broken_and_missing(self):
        with self.assertRaises(convert.ConvertError):
            convert.load_card(self.write(None, raw="{"))
        with self.assertRaises(convert.ConvertError):
            convert.load_card(self.tmp / "nope.json")


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-convert-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_draft(self, *args):
        return subprocess.run([sys.executable, str(DRAFT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8")

    def test_convert_stdout_all_seven(self):
        for key in PAIRS:
            r = self.run_draft("convert", card_path(key))
            self.assertEqual(r.returncode, 0, f"{key}: {r.stderr}")
            self.assertEqual(json.loads(r.stdout)["scenes"][-1]["role"], "cta")
            self.assertIn("convert: 카드", r.stderr)

    def test_convert_out_file(self):
        out = self.tmp / "sk.json"
        r = self.run_draft("convert", card_path("tax"), "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["series"], {"name": "연말정산 바로 알기"})

    def test_convert_bad_card_exit_1(self):
        bad = self.tmp / "bad.json"
        bad.write_text("{", encoding="utf-8")
        r = self.run_draft("convert", bad)
        self.assertEqual(r.returncode, 1)
        self.assertIn("초안 오류", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_check_legacy_card(self):
        out = self.tmp / "c.json"
        r = self.run_draft("check", reel_path("tax"), "--legacy", "--card", card_path("tax"), "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("scene 6 line 2: NOT_IN_CARD (0원)", r.stderr)
        self.assertIn("CARD_NOTE_DROPPED (종합소득자는 4,500만 원 기준)", r.stderr)
        block = json.loads(out.read_text(encoding="utf-8"))["card"]
        self.assertEqual([n["detail"] for n in block["new_numbers"]], ["0원"])
        self.assertTrue(any(d["detail"] == "종합소득자는 4,500만 원 기준" for d in block["dropped_notes"]))

    def test_check_legacy_card_strict_exits_3(self):
        r = self.run_draft("check", reel_path("tax"), "--legacy", "--card", card_path("tax"), "--strict")
        self.assertEqual(r.returncode, 3)

    def test_check_card_with_expanded_draft(self):
        spec = self.tmp / "spec.json"
        src = TOOLS / "tests" / "fixtures" / "draft-tax.src.json"
        self.assertEqual(self.run_draft("expand", src, spec).returncode, 0)
        out = self.tmp / "c.json"
        r = self.run_draft("check", spec, "--card", card_path("tax"), "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("card", json.loads(out.read_text(encoding="utf-8")))

    def test_check_without_card_has_no_card_block(self):
        out = self.tmp / "c.json"
        r = self.run_draft("check", reel_path("tax"), "--legacy", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("card", json.loads(out.read_text(encoding="utf-8")))

    def test_check_bad_card_exit_1(self):
        r = self.run_draft("check", reel_path("tax"), "--legacy", "--card", self.tmp / "nope.json")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
