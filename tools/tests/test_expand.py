"""expand_source / draft.py expand 시험: 게시된 tax-deduction 편 재현, 장부, 부정 시험 (stdlib unittest 전용)."""
import copy
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
sys.path.insert(0, str(TOOLS))

from reelkit import figures  # noqa: E402
from reelkit.expand import PLACEHOLDER, ExpandError, expand_source  # noqa: E402

FIXTURE = TOOLS / "tests" / "fixtures" / "draft-tax.src.json"
PUBLISHED = REPO / "2026" / "reels" / "specs" / "2026-10-26-tax-deduction.json"
SEEDED_IDS = {
    "income_tax_rate_b1", "income_tax_rate_b4", "local_income_tax_ratio",
    "pension_credit_rate_low", "pension_credit_rate_high", "pension_credit_wage_threshold",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def field_of(spec, entry):
    if entry["where"] == "basis":
        return spec["basis"]
    m = re.fullmatch(r"scene (\d+) (top|line (\d+))", entry["where"])
    sc = spec["scenes"][int(m.group(1)) - 1]
    return sc["top"] if m.group(2) == "top" else sc["lines"][int(m.group(3)) - 1]


def mini(**over):
    src = {
        "inputs": {"amt": {"value": "1000000", "unit": "원", "label": "100만 원 공제 예시"}},
        "derive": {"r": {"fn": "with_local", "args": ["fig.income_tax_rate_b1", "fig.local_income_tax_ratio"]}},
        "scenes": [{"top": "t", "lines": ["{{r|pct}}"]}],
    }
    src.update(over)
    return src


class TaxDeductionReproduction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()
        cls.src = load(FIXTURE)
        cls.src_before = copy.deepcopy(cls.src)
        cls.out = expand_source(cls.src, cls.registry)
        cls.published = load(PUBLISHED)

    def test_scenes_and_basis_equal_published_spec(self):
        self.assertEqual(self.out["scenes"], self.published["scenes"])
        self.assertEqual(self.out["basis"], self.published["basis"])
        self.assertEqual(self.out["version"], 2)
        self.assertEqual(list(self.out), ["version", "basis", "scenes", "inputs", "derive", "figures", "basis_items"])
        self.assertEqual(self.out["derive"], self.src["derive"])   # check 가 다시 계산할 수 있게 남김 (CR-01)

    def test_ledger_offsets_point_at_the_rendered_text(self):
        ledger = self.out["figures"]
        self.assertEqual(len(ledger), 11)
        for e in ledger:
            self.assertEqual(field_of(self.out, e)[e["start"]:e["end"]], e["text"], e)
            self.assertTrue(e["exact"], e)
        by_ref = {(e["where"], e["ref"]): e for e in ledger}
        e = by_ref[("scene 3 line 3", "e_b4")]
        self.assertEqual((e["text"], e["value"], e["fmt"]), ("38.5만", "385000", "man1"))
        self.assertEqual(e["sources"], ["fig.income_tax_rate_b4", "fig.local_income_tax_ratio", "inputs.amt"])
        self.assertEqual(by_ref[("basis", "inputs.amt")]["sources"], ["inputs.amt"])

    def test_basis_items_cover_exactly_the_used_registry_ids_once(self):
        items = self.out["basis_items"]
        ids = [i["fig"] for i in items]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), SEEDED_IDS)
        first = items[0]
        self.assertEqual(set(first), {"fig", "label", "source", "as_of", "verified", "legal_status"})
        self.assertEqual((first["verified"], first["legal_status"]), ("미확인", "시행"))

    def test_source_has_no_digit_outside_placeholders_and_inputs(self):
        texts = [self.src["basis"]]
        for sc in self.src["scenes"]:
            texts.append(sc["top"])
            texts.extend(sc["lines"])
        for t in texts:
            rest = PLACEHOLDER.sub("", t).replace("1분 노후자금 계산기", "")
            self.assertIsNone(re.search(r"\d", rest), t)

    def test_input_dict_is_not_mutated(self):
        self.assertEqual(self.src, self.src_before)


class NegativeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()

    def expect_error(self, src, *needles):
        with self.assertRaises(ExpandError) as cm:
            expand_source(src, self.registry)
        for n in needles:
            self.assertIn(n, str(cm.exception))

    def test_minimal_source_expands(self):
        out = expand_source(mini(), self.registry)
        self.assertEqual(out["scenes"][0]["lines"], ["6.6%"])

    def test_unknown_fig_id_suggests_close_match(self):
        src = mini(scenes=[{"top": "t", "lines": ["{{fig.income_tax_rate_b11|pct}}"]}])
        self.expect_error(src, "scene 1 line 1", "income_tax_rate_b11", "비슷한 id", "income_tax_rate_b1")

    def test_unknown_format(self):
        self.expect_error(mini(scenes=[{"top": "t", "lines": ["{{r|nope}}"]}]), "scene 1 line 1", "nope")

    def test_forward_derive_reference(self):
        derive = {"a": {"fn": "pct_of", "args": ["inputs.amt", "b"]},
                  "b": {"fn": "with_local", "args": ["fig.income_tax_rate_b1", "fig.local_income_tax_ratio"]}}
        self.expect_error(mini(derive=derive), "derive.a", "b")

    def test_unknown_function(self):
        self.expect_error(mini(derive={"a": {"fn": "eval", "args": []}}), "derive.a", "eval", "pct_of")

    def test_wrong_arity(self):
        self.expect_error(mini(derive={"a": {"fn": "pct_of", "args": ["inputs.amt"]}}), "derive.a", "2")

    def test_input_label_needs_example_mark(self):
        src = mini(inputs={"amt": {"value": "1000000", "unit": "원", "label": "100만 원 공제"}})
        self.expect_error(src, "inputs.amt", "예시/가정/가상")

    def test_leftover_braces(self):
        self.expect_error(mini(scenes=[{"top": "t", "lines": ["{{r}} 남음"]}]), "scene 1 line 1", "자리표시자")

    def test_unknown_top_level_key(self):
        self.expect_error(mini(motion="x"), "motion")

    def test_non_finite_input_value_rejected(self):
        src = mini(inputs={"amt": {"value": "NaN", "unit": "원", "label": "예시"}})
        self.expect_error(src, "inputs.amt")


class MotionField(unittest.TestCase):
    """motion 소스 필드(D-05): none/basic 만 확장되고 원고에 그대로 실린다."""

    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()

    def test_allowed_values_carry_over(self):
        for mode in ("none", "basic"):
            self.assertEqual(expand_source(mini(motion=mode), self.registry)["motion"], mode)

    def test_absent_key_stays_absent(self):
        self.assertNotIn("motion", expand_source(mini(), self.registry))

    def test_other_values_are_errors_naming_motion(self):
        for bad in ("calm", {"preset": "calm"}, 1):
            with self.assertRaises(ExpandError) as cm:
                expand_source(mini(motion=bad), self.registry)
            self.assertIn("motion", str(cm.exception))
            self.assertIn("basic", str(cm.exception))


class UnitsAndFormats(unittest.TestCase):
    """CR-03 회귀: 서식과 단위가 안 맞거나 단위를 글자로 붙이면 확장이 거부한다."""

    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()

    def expand_lines(self, lines, derive=None):
        src = {"scenes": [{"top": "t", "lines": lines}]}
        if derive:
            src["derive"] = derive
        return expand_source(src, self.registry)

    def expect_unit_error(self, lines, *needles, derive=None):
        with self.assertRaises(ExpandError) as cm:
            self.expand_lines(lines, derive)
        self.assertEqual(cm.exception.kind, "UNIT", str(cm.exception))
        for n in needles:
            self.assertIn(n, str(cm.exception))

    def test_money_with_num_and_literal_unit_is_rejected(self):
        # 리뷰 재현: "한도 9,000,000만 원" (900만 원이 900억 원으로 보임)
        self.expect_unit_error(["한도 {{fig.pension_credit_limit_total|num}}만 원"], "num", "man_won")

    def test_rate_with_money_format_is_rejected(self):
        # 리뷰 재현: "세율 0만 원"
        self.expect_unit_error(["세율 {{fig.income_tax_rate_b1|man_won}}"], "man_won", "pct")

    def test_literal_unit_after_placeholder_is_rejected(self):
        for line in ("{{fig.pension_credit_limit_total|man}}원", "{{fig.pension_credit_limit_total|man}} 원",
                     "<g>{{fig.pension_credit_limit_total|man}}</g> 원", "{{fig.rule_of_72|num}}%",
                     "{{fig.rule_of_72|num}}만"):
            with self.subTest(line=line):
                self.expect_unit_error([line], "단위")

    def test_particles_after_units_are_fine(self):
        out = self.expand_lines(["연 {{fig.pension_credit_limit_savings|man_won}}까지", "{{fig.rule_of_72|num}}의 법칙",
                                 "{{y|nyeon}} 만에 두 배 예시"],
                                derive={"y": {"fn": "div", "args": ["fig.rule_of_72", "fig.cpi_yoy_2026_09"]}})
        self.assertEqual(out["scenes"][0]["lines"], ["연 600만 원까지", "72의 법칙", "25년 만에 두 배 예시"])

    def test_derive_unit_rules(self):
        self.expect_unit_error(["{{x|man_won}}"], "add",
                               derive={"x": {"fn": "add", "args": ["fig.income_tax_rate_b1", "fig.pension_credit_limit_total"]}})
        self.expect_unit_error(["{{x|man_won}}"], "rate_pct",
                               derive={"x": {"fn": "pct_of", "args": ["fig.income_tax_rate_b1", "fig.pension_credit_limit_total"]}})
        # 결과 단위가 서식을 고른다: 세율 × 지방소득세 = %, 금액의 % = 원
        out = self.expand_lines(["{{r|pct}} → {{e|man1}}"], derive={
            "r": {"fn": "with_local", "args": ["fig.income_tax_rate_b1", "fig.local_income_tax_ratio"]},
            "e": {"fn": "pct_of", "args": ["fig.pension_credit_limit_total", "r"]}})
        self.assertEqual(out["scenes"][0]["lines"], ["6.6% → 59.4만"])

    def test_every_format_has_a_unit_rule(self):
        from reelkit import calc
        self.assertEqual(set(calc.FORMAT_UNITS), set(calc.FORMATS))


LEDGER_KEYS = {"where", "scene", "start", "end", "text", "ref", "fmt", "value", "exact", "sources"}


class CountUpSyntax(unittest.TestCase):
    """{{ref|fmt|up}}: 장면 줄에서만, 장부 항목에 countup true 하나만 더한다 (D-04)."""

    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()
        cls.plain = load(TOOLS / "tests" / "fixtures" / "draft-pension.src.json")

    def with_up(self, src_line=("c_low", "man1")):
        src = copy.deepcopy(self.plain)
        ref, fmt = src_line
        src["scenes"][4]["lines"][0] = src["scenes"][4]["lines"][0].replace(f"{{{{{ref}|{fmt}}}}}",
                                                                           f"{{{{{ref}|{fmt}|up}}}}")
        return src

    def test_up_marks_only_that_entry(self):
        base = expand_source(self.plain, self.registry)
        up = expand_source(self.with_up(), self.registry)
        self.assertEqual(up["scenes"], base["scenes"])
        marked = [e for e in up["figures"] if e.get("countup")]
        self.assertEqual([e["where"] for e in marked], ["scene 5 line 1"])
        for a, b in zip(base["figures"], up["figures"]):
            self.assertEqual({k: v for k, v in b.items() if k != "countup"}, a)

    def test_plain_ledger_has_exact_keys(self):
        for e in expand_source(self.plain, self.registry)["figures"]:
            self.assertEqual(set(e), LEDGER_KEYS)

    def test_up_outside_scene_line_refused(self):
        for key, where in (("top", "scene 5 top"), ("basis", "basis")):
            src = copy.deepcopy(self.plain)
            if key == "top":
                src["scenes"][4]["top"] = "{{fig.pension_credit_limit_total|man_won|up}} 채우면"
            else:
                src["basis"] = "{{fig.pension_credit_limit_total|man_won|up}} 납입 예시 · 지방소득세 포함"
            with self.assertRaises(ExpandError) as cm:
                expand_source(src, self.registry)
            self.assertIn(where, str(cm.exception))
            self.assertIn("|up", str(cm.exception))

    def test_other_third_piece_refused(self):
        src = copy.deepcopy(self.plain)
        src["scenes"][4]["lines"][0] = "최대 {{c_low|man1|down}}"
        with self.assertRaises(ExpandError) as cm:
            expand_source(src, self.registry)
        self.assertIn("자리표시자", str(cm.exception))

    def test_check_accepts_up_source(self):
        from reelkit import check
        src = self.with_up()
        spec = expand_source(src, self.registry)
        self.assertEqual(check.compare_source(spec, src, self.registry), [])
        base = check.check_spec(expand_source(self.plain, self.registry), self.registry)
        rep = check.check_spec(spec, self.registry)
        self.assertEqual([str(i) for i in rep.errors], [str(i) for i in base.errors])
        self.assertEqual([i.kind for i in rep.warnings], [i.kind for i in base.warnings])


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-expand-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(TOOLS / "draft.py"), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8")

    def test_expand_writes_parseable_spec(self):
        out = self.tmp / "sub" / "spec.json"
        r = self.run_cli("expand", FIXTURE, out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), f"expand: {out} 숫자 11개 · 등록부 id 6개")
        spec = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(spec["version"], 2)

    def test_missing_source_exits_1_without_traceback(self):
        r = self.run_cli("expand", self.tmp / "nope.json", self.tmp / "o.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("초안 오류", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_bad_source_content_exits_1_without_traceback(self):
        bad = self.tmp / "bad.json"
        bad.write_text('{"scenes": [{"top": "t", "lines": ["{{fig.zzz|pct}}"]}]}', encoding="utf-8")
        r = self.run_cli("expand", bad, self.tmp / "o.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("초안 오류", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse((self.tmp / "o.json").exists())


if __name__ == "__main__":
    unittest.main()
