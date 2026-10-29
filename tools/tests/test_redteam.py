"""레드팀 보고서(COMP-04) 테스트: 말뭉치 검증, 표본 기준 회귀 한계, 보고서 형식.

한계값은 표본(corpus.json)에만 단언한다. 암시적 문장과 따로 쓴 문장(heldout.json)은 숫자를 단언하지 않고 보고서가 찍히는지만 본다.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from reelkit import compliance, redteam   # noqa: E402

DRAFT = [sys.executable, str(TOOLS / "draft.py")]
CORPUS = TOOLS / "tests" / "redteam" / "corpus.json"
HELDOUT = TOOLS / "tests" / "redteam" / "heldout.json"
LAST_LINE = re.compile(r"^redteam: 표본 내 탐지 \d+/41 · 오탐 \d+/21 · 따로 쓴 문장 탐지 \d+/\d+ · 오탐 \d+/\d+ · 기존 10편 수정 필요 \d+건$")

BAD_OK = {"id": "X01", "label": "bad", "category": "단정·보장", "tier": "explicit", "lines": ["원금 보장"]}
GOOD_OK = {"id": "X02", "label": "good", "lines": ["안녕하세요"]}


def write_tmp(entries):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(entries, f, ensure_ascii=False)
    f.close()
    return Path(f.name)


class LoadCorpus(unittest.TestCase):
    def reject(self, entries, needle):
        p = write_tmp(entries)
        self.addCleanup(p.unlink)
        with self.assertRaises(redteam.CorpusError) as cm:
            redteam.load_corpus(p)
        self.assertIn(needle, str(cm.exception))
        return str(cm.exception)

    def test_ok(self):
        p = write_tmp([BAD_OK, GOOD_OK])
        self.addCleanup(p.unlink)
        self.assertEqual(len(redteam.load_corpus(p)), 2)

    def test_duplicate_id(self):
        self.reject([BAD_OK, dict(GOOD_OK, id="X01")], "X01")

    def test_bad_label(self):
        self.reject([dict(BAD_OK, label="maybe")], "X01")

    def test_unknown_category(self):
        self.reject([dict(BAD_OK, category="기타")], "X01")

    def test_missing_category_or_tier(self):
        bad = dict(BAD_OK)
        del bad["category"]
        self.reject([bad], "X01")
        bad = dict(BAD_OK)
        del bad["tier"]
        self.reject([bad], "X01")
        self.reject([dict(BAD_OK, tier="hidden")], "X01")

    def test_empty_lines(self):
        self.reject([dict(BAD_OK, lines=[])], "X01")

    def test_non_string_line(self):
        self.reject([dict(BAD_OK, lines=["가", 3])], "X01")

    def test_expect_severity_outside_set(self):
        self.reject([dict(BAD_OK, expect_severity="통과")], "X01")

    def test_file_errors(self):
        with self.assertRaises(redteam.CorpusError):
            redteam.load_corpus(TOOLS / "tests" / "redteam" / "없는파일.json")
        p = write_tmp([])
        self.addCleanup(p.unlink)
        p.write_text("{", encoding="utf-8")
        with self.assertRaises(redteam.CorpusError):
            redteam.load_corpus(p)

    def test_entry_spec_is_one_scene_reel(self):
        spec = redteam.entry_spec(dict(BAD_OK, basis="근거"))
        self.assertEqual(spec, {"basis": "근거", "scenes": [{"top": "", "lines": ["원금 보장"]}]})
        self.assertEqual(redteam.entry_spec(BAD_OK)["basis"], "")


class Counts(unittest.TestCase):
    def test_seed_and_heldout_sizes(self):
        seed = redteam.load_corpus(CORPUS)
        self.assertEqual(sum(e["label"] == "bad" for e in seed), 41)
        self.assertEqual(sum(e["label"] == "good" for e in seed), 21)
        held = redteam.load_corpus(HELDOUT)
        self.assertGreaterEqual(sum(e["label"] == "bad" for e in held), 12)
        self.assertGreaterEqual(sum(e["label"] == "good" for e in held), 6)
        self.assertFalse({e["id"] for e in seed} & {e["id"] for e in held})


class Evaluate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = compliance.load_rules()

    def ev(self, *entries):
        return redteam.evaluate(list(entries), self.rules)

    def test_detected_needs_category_and_severity(self):
        r = self.ev(dict(BAD_OK, lines=["이 적금은 원금 보장이에요"]))
        self.assertEqual((r["bad_detected"], r["bad_total"]), (1, 1))
        self.assertTrue(r["entries"][0]["detected"])

    def test_wrong_category_is_mismatch_not_detected(self):
        r = self.ev(dict(BAD_OK, category="개인정보", lines=["이 적금은 원금 보장이에요"]))
        self.assertEqual(r["bad_detected"], 0)
        e = r["entries"][0]
        self.assertTrue(e["mismatch"])
        self.assertIn("단정·보장", e["actual"])

    def test_lower_severity_is_mismatch(self):
        # B22 는 확인 필요로 잡히는 문장이다. 수정 필요를 기대하면 등급 불일치로 센다.
        r = self.ev({"id": "X03", "label": "bad", "category": "상품 권유", "tier": "explicit",
                     "lines": ["놓치면 후회하는 상품", "마감 임박!"], "expect_severity": "수정 필요"})
        self.assertEqual(r["bad_detected"], 0)
        self.assertTrue(r["entries"][0]["mismatch"])

    def test_miss_has_no_findings(self):
        r = self.ev(dict(BAD_OK, lines=["오늘 날씨가 좋네요"]))
        e = r["entries"][0]
        self.assertFalse(e["detected"])
        self.assertFalse(e["mismatch"])
        self.assertEqual(e["findings"], [])

    def test_false_positive_counts(self):
        r = self.ev(dict(GOOD_OK, lines=["무조건 오르는 종목"]))
        self.assertEqual((r["good_fp"], r["good_fp_fix"]), (1, 1))
        r = self.ev(GOOD_OK)
        self.assertEqual((r["good_fp"], r["good_fp_fix"]), (0, 0))

    def test_tallies_and_timing(self):
        r = self.ev(BAD_OK, dict(BAD_OK, id="X09", tier="implicit", lines=["오늘 날씨가 좋네요"]))
        self.assertEqual(r["by_tier"]["explicit"], [1, 1])
        self.assertEqual(r["by_tier"]["implicit"], [0, 1])
        self.assertEqual(r["by_category"]["단정·보장"], [1, 2])
        self.assertTrue(r["rule_ms"])
        self.assertTrue(all(v >= 0 for v in r["rule_ms"].values()))


class SeedThresholds(unittest.TestCase):
    """표본 기준 회귀 한계. 암시적 문장과 따로 쓴 문장은 단언하지 않는다."""

    @classmethod
    def setUpClass(cls):
        cls.rules = compliance.load_rules()
        cls.seed = redteam.evaluate(redteam.load_corpus(CORPUS), cls.rules)
        cls.published = redteam.published_counts(cls.rules)

    def test_published_ten_have_no_fix_needed(self):
        self.assertEqual(self.published["수정 필요"], 0, self.published["findings"])
        self.assertEqual(self.published["reels"], 10)

    def test_explicit_and_obfuscated_all_detected(self):
        d = sum(self.seed["by_tier"][t][0] for t in ("explicit", "obfuscated"))
        n = sum(self.seed["by_tier"][t][1] for t in ("explicit", "obfuscated"))
        self.assertEqual((d, n), (38, 38), [e["id"] for e in self.seed["entries"]
                                           if e["label"] == "bad" and e["tier"] != "implicit" and not e["detected"]])

    def test_good_set_has_no_fix_needed_false_positive(self):
        self.assertEqual((self.seed["good_fp_fix"], self.seed["good_total"]), (0, 21),
                         [e["id"] for e in self.seed["entries"] if e["label"] == "good" and e["findings"]])


class Report(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = compliance.load_rules()
        cls.lines, cls.data = redteam.report(cls.rules, redteam.load_corpus(CORPUS), redteam.load_corpus(HELDOUT))
        cls.text = "\n".join(cls.lines)

    def test_labels(self):
        self.assertIn("표본 내", self.text)
        self.assertIn("따로 쓴 문장", self.text)
        self.assertIn("규칙 조정에 쓰지 않음", self.text)
        self.assertIn("[기존 10편]", self.text)
        self.assertIn("[예외 처리로 제외]", self.text)
        self.assertIn("[규칙 시간]", self.text)

    def test_caveat_and_limits(self):
        self.assertIn("주의: 표본 내 수치는 규칙을 쓴 쪽이 같은 문장을 보고 맞춘 결과라 실제보다 높게 나옵니다. 따로 쓴 문장 줄을 함께 보세요.",
                      self.lines)
        self.assertIn("한계: 키워드·패턴 방식이라 암시적 표현은 잡지 못합니다 (AI 의미 점검은 v2)", self.lines)

    def test_last_line_form(self):
        self.assertRegex(self.lines[-1], LAST_LINE)

    def test_header_has_version_and_as_of(self):
        self.assertTrue(self.lines[0].startswith(f"규칙 v{self.rules.version}"))
        self.assertIn(f"기준일 {self.rules.as_of}", self.lines[0])

    def test_forbidden_words_absent(self):
        self.assertNotIn("통과", self.text)
        self.assertIsNone(re.search(r"제\s*\d+\s*조", self.text))

    def test_data_matches_last_line(self):
        m = re.match(r"^redteam: 표본 내 탐지 (\d+)/(\d+) · 오탐 (\d+)/(\d+) · 따로 쓴 문장 탐지 (\d+)/(\d+) · 오탐 (\d+)/(\d+) · 기존 10편 수정 필요 (\d+)건$",
                     self.lines[-1])
        got = tuple(int(x) for x in m.groups())
        d = self.data
        want = (d["seed"]["bad_detected"], d["seed"]["bad_total"], d["seed"]["good_fp"], d["seed"]["good_total"],
                d["heldout"]["bad_detected"], d["heldout"]["bad_total"], d["heldout"]["good_fp"], d["heldout"]["good_total"],
                d["published"]["수정 필요"])
        self.assertEqual(got, want)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(DRAFT + ["redteam", *args], capture_output=True, text=True, encoding="utf-8")

    def test_report_and_json_agree(self):
        text = self.run_cli()
        self.assertEqual(text.returncode, 0, text.stderr)
        last = text.stdout.rstrip("\n").split("\n")[-1]
        self.assertRegex(last, LAST_LINE)
        js = self.run_cli("--json")
        self.assertEqual(js.returncode, 0, js.stderr)
        data = json.loads(js.stdout)
        self.assertEqual(data["last_line"], last)
        self.assertEqual(data["seed"]["bad_total"], 41)

    def test_bad_corpus_exits_one(self):
        p = write_tmp([BAD_OK, BAD_OK])
        self.addCleanup(p.unlink)
        r = self.run_cli("--corpus", str(p))
        self.assertEqual(r.returncode, 1)
        self.assertIn("X01", r.stderr)

    def test_bad_rules_exits_one(self):
        p = write_tmp({"schema": 1})
        self.addCleanup(p.unlink)
        r = self.run_cli("--rules", str(p))
        self.assertEqual(r.returncode, 1)

    def test_help(self):
        self.assertEqual(self.run_cli("--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
