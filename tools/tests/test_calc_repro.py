"""게시된 릴스의 파생 수치를 calc 로 글자 그대로 재현하는 표 (D-05) 와 반올림·오류 규칙 시험 (stdlib unittest 전용)."""
import re
import sys
import unittest
from decimal import Decimal
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from reelkit import calc  # noqa: E402
from reelkit.calc import FORMATS, FUNCTIONS, CalcError  # noqa: E402

TOTAL = "372000000"
L = "with_local"


def ev(x):
    """표의 식을 계산한다: 문자열 = Decimal 값, 튜플 = (함수 이름, 인자...) 를 FUNCTIONS 로 호출."""
    if isinstance(x, tuple):
        return FUNCTIONS[x[0]][0](*[ev(a) for a in x[1:]])
    return Decimal(x)


def render(fmt, expr):
    return FORMATS[fmt](ev(expr))


def interest(months="12"):
    return ("installment_simple_interest", "1000000", "5", months)


# (기대 문자열, 서식, 식). 기대 문자열은 게시된 2026/reels/specs 의 글자다.
CASES = [
    ("6.6만", "man1", ("pct_of", "1000000", (L, "6", "10"))),
    ("38.5만", "man1", ("pct_of", "1000000", (L, "35", "10"))),
    ("16.5만", "man1", ("pct_of", "1000000", (L, "15", "10"))),
    ("13.2만", "man1", ("pct_of", "1000000", (L, "12", "10"))),
    ("6.6%", "pct", (L, "6", "10")),
    ("38.5%", "pct", (L, "35", "10")),
    ("2.7%", "pct1", ("yield_pct", interest(), ("mul", "1000000", "12"))),
    ("2.3%", "pct1", ("yield_pct", ("after_tax", interest(), "15.4"), ("mul", "1000000", "12"))),
    ("3.0%", "pct1", ("after_tax", "3.6", "15.4")),
    ("0.1%", "pct1", ("sub", ("after_tax", "3.6", "15.4"), "2.9")),
    ("24년", "nyeon", ("div", "72", "3")),
    ("14년", "nyeon", ("div", "72", "5")),
    ("7년", "nyeon", ("div", "72", "10")),
    ("300개월", "gaewol", ("months_between_ages", "28", "53")),
    ("672개월", "gaewol", ("months_between_ages", "28", "84")),
    ("2.2달", "dal", ("div", "672", "300")),
    ("25년", "nyeon", ("sub", "53", "28")),
    ("12년", "nyeon", ("sub", "65", "53")),
    ("124만", "man", ("div", TOTAL, "300")),
    ("207만", "man", ("div", TOTAL, "180")),
    ("388만", "man", ("div", TOTAL, "96")),
    ("72만", "man", ("annuity_pmt", TOTAL, "4", "300")),
    ("151만", "man", ("annuity_pmt", TOTAL, "4", "180")),
    ("329만", "man", ("annuity_pmt", TOTAL, "4", "96")),
    ("4,500만", "man", ("mul", "150000", "300")),
    ("7,712만", "man", ("fv_monthly", "150000", "4", "300")),
    ("8만", "man", ("add", "60000", "20000")),
    ("15만 원", "man_won", ("add", ("add", "30000", "30000"), ("add", "10000", "80000"))),
    ("−30%", "signed_pct", ("neg", ("mul", "6", "5"))),
    ("+36%", "signed_pct", ("mul", "7.2", "5")),
    ("117만", "man", "1166700"),
    ("70만 원", "man_won", "700000"),
    ("3억 7,200만 원", "eok_man_won", TOTAL),
    ("1,200만 원", "man_won", ("mul", "1000000", "12")),
    ("83.7세", "se", "83.7"),
    ("53세", "se", "53.0"),
]


class PublishedFigures(unittest.TestCase):
    def test_table_has_at_least_36_rows(self):
        self.assertGreaterEqual(len(CASES), 36)

    def test_every_row_reproduces_the_published_string(self):
        for expected, fmt, expr in CASES:
            with self.subTest(expected=expected):
                text, _ = render(fmt, expr)
                self.assertEqual(text, expected)

    def test_exact_flag_semantics(self):
        value = ev(("div", "72", "5"))
        text, shown = FORMATS["nyeon"](value)
        self.assertEqual((text, shown, value), ("14년", Decimal(14), Decimal("14.4")))
        self.assertNotEqual(shown, value)
        value = ev(("pct_of", "1000000", (L, "6", "10")))
        self.assertEqual(FORMATS["man1"](value)[1], value)

    def test_shown_is_the_displayed_value_in_base_units(self):
        text, shown = FORMATS["man1"](Decimal("723553"))
        self.assertEqual((text, shown), ("72.4만", Decimal("724000")))


class RoundingAndFormats(unittest.TestCase):
    def test_ties_round_up(self):
        self.assertEqual(FORMATS["man"](Decimal("3865000"))[0], "387만")
        self.assertEqual(FORMATS["man"](Decimal("3875000"))[0], "388만")

    def test_negative_uses_unicode_minus_and_zero_has_no_sign(self):
        self.assertEqual(FORMATS["pct"](Decimal("-6.6"))[0], "−6.6%")
        self.assertEqual(FORMATS["signed_pct"](Decimal("0"))[0], "0%")
        self.assertEqual(FORMATS["signed_pct"](Decimal("-0.04"))[0], "0%")
        self.assertEqual(FORMATS["won"](Decimal("0"))[0], "0원")

    def test_eok_man_won_edges(self):
        self.assertEqual(FORMATS["eok_man_won"](Decimal("300000000"))[0], "3억 원")
        self.assertEqual(FORMATS["eok_man_won"](Decimal("99990000"))[0], "9,999만 원")
        self.assertEqual(FORMATS["eok_man_won"](Decimal("100000000"))[0], "1억 원")

    def test_num_and_pct0(self):
        self.assertEqual(FORMATS["num"](Decimal("1234.56"))[0], "1,234.6")
        self.assertEqual(FORMATS["pct0"](Decimal("2.5"))[0], "3%")

    def test_zero_rate_special_cases(self):
        self.assertEqual(ev(("annuity_pmt", "1200", "0", "12")), Decimal(100))
        self.assertEqual(ev(("fv_monthly", "100", "0", "12")), Decimal(1200))


class Errors(unittest.TestCase):
    def test_month_arguments_must_be_integers_from_1_to_1200(self):
        for months in ("0", "-1", "1.5", "1201"):
            for fn, args in (
                ("installment_simple_interest", ("1000000", "5", months)),
                ("annuity_pmt", ("1000000", "4", months)),
                ("fv_monthly", ("100000", "4", months)),
            ):
                with self.subTest(fn=fn, months=months):
                    with self.assertRaises(CalcError):
                        ev((fn, *args))
        ev(("fv_monthly", "100000", "4", "1200"))

    def test_division_by_zero_is_a_calc_error(self):
        with self.assertRaises(CalcError):
            ev(("div", "1", "0"))
        with self.assertRaises(CalcError):
            ev(("yield_pct", "1", "0"))

    def test_ages_must_move_forward(self):
        with self.assertRaises(CalcError):
            ev(("months_between_ages", "53", "28"))

    def test_float_and_non_finite_inputs_rejected(self):
        with self.assertRaises(CalcError):
            FUNCTIONS["add"][0](1.5, Decimal(1))
        with self.assertRaises(CalcError):
            FUNCTIONS["add"][0](Decimal("NaN"), Decimal(1))
        with self.assertRaises(CalcError):
            FORMATS["man"](Decimal("Infinity"))


class Inventory(unittest.TestCase):
    def test_function_and_format_names_are_exactly_the_documented_set(self):
        self.assertEqual(set(FUNCTIONS), {
            "add", "sub", "mul", "div", "neg", "pct_of", "with_local", "after_tax",
            "installment_simple_interest", "yield_pct", "months_between_ages", "annuity_pmt", "fv_monthly"})
        self.assertEqual(set(FORMATS), {
            "pct", "pct0", "pct1", "signed_pct", "man", "man1", "man_won", "eok_man_won", "won",
            "num", "se", "nyeon", "gaewol", "dal"})

    def test_calc_source_has_no_binary_float_or_builtin_rounding(self):
        code = [ln for ln in Path(calc.__file__).read_text(encoding="utf-8").splitlines()
                if not ln.lstrip().startswith("#")]
        hits = [ln for ln in code if re.search(r"\bfloat\(|\bround\(", ln)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
