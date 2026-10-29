"""reelkit.numscan 시험: 게시된 10편에서 뽑은 분류 사례와 말뭉치 단언 (stdlib unittest 전용)."""
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from reelkit import numscan  # noqa: E402

SPECS = sorted((REPO / "2026" / "reels" / "specs").glob("*.json"))


def raws(text):
    toks = numscan.scan(text)
    return ([t.raw for t in toks if t.kind == "figure"], [t.raw for t in toks if t.kind == "structure"])


def spec_texts(path):
    spec = json.loads(path.read_text(encoding="utf-8"))
    for sc in spec["scenes"]:
        yield sc["top"]
        yield from sc["lines"]
    yield spec.get("basis", "")


class Cases(unittest.TestCase):
    def test_structure_only_cases(self):
        self.assertEqual(raws("내 월급의 두 주인 ⑤"), ([], ["⑤"]))
        self.assertEqual(raws("전자책 3권"), ([], ["3권"]))
        self.assertEqual(raws("통장 이름 <g>4개로 바꾸기</g>"), ([], ["4개"]))
        self.assertEqual(raws("2026년 기준 · 국민연금공단"), ([], ["2026년"]))
        self.assertEqual(raws("<s>다음 편: 2층 퇴직연금</s>"), ([], ["2층"]))

    def test_constant_phrases_are_masked(self):
        self.assertEqual(raws("<s>프로필 링크 · 1분 노후자금 계산기</s>"), ([], []))
        self.assertEqual(raws("세금·4대보험처럼"), ([], []))
        self.assertEqual(raws("<s>다음 편: 72의 법칙</s>"), ([], []))
        self.assertEqual(raws("S&P500 과거 장기 평균 약 10%"), (["10%"], []))

    def test_birth_year_is_a_figure(self):
        self.assertEqual(raws("1969년생 이후"), (["1969년생"], []))

    def test_date_inside_parentheses_is_structure(self):
        self.assertEqual(raws("예금 3.6% 예시 · 물가 2.9%(26년 9월)"), (["3.6%", "2.9%"], ["26년 9월"]))

    def test_compound_money_is_one_token(self):
        toks = numscan.figure_tokens("목표 3억 7,200만 원 가정 · 물가 미반영")
        self.assertEqual(len(toks), 1)
        self.assertEqual((toks[0].cls, toks[0].value), ("won", Decimal(372000000)))
        toks = numscan.figure_tokens("넣은 돈 1,200만 원 기준")
        self.assertEqual((toks[0].cls, toks[0].value), ("won", Decimal(12000000)))

    def test_ages_and_ranges(self):
        self.assertEqual(raws("28세부터 84세까지"), (["28세", "84세"], []))
        toks = numscan.figure_tokens("55~79세 월평균 연금")
        self.assertEqual([(t.cls, t.value) for t in toks], [("age", Decimal(55)), ("age", Decimal(79))])

    def test_negative_percent_uses_minus_sign(self):
        toks = numscan.figure_tokens("5년 당기면 −30%")
        self.assertEqual([t.raw for t in toks], ["5년", "−30%"])
        self.assertEqual((toks[1].cls, toks[1].value), ("pct", Decimal(-30)))

    def test_bare_numbers(self):
        toks = numscan.figure_tokens("60 · 150 · 30 · <g>160</g>")
        self.assertEqual([t.cls for t in toks], ["bare"] * 4)
        self.assertEqual([t.value for t in toks], [Decimal(60), Decimal(150), Decimal(30), Decimal(160)])

    def test_percent_and_man_in_one_line(self):
        toks = numscan.figure_tokens("6.6% → 6.6만")
        self.assertEqual([(t.cls, t.value) for t in toks], [("pct", Decimal("6.6")), ("won", Decimal(66000))])

    def test_months_are_not_counting_words(self):
        self.assertEqual(raws("3개월 뒤"), (["3개월"], []))

    def test_tags_never_become_tokens(self):
        self.assertEqual(raws("<g></g><s></s><br>"), ([], []))


class HangulAndYears(unittest.TestCase):
    """CR-04 회귀: 리뷰에서 figure_tokens(...) == [] 였던 문자열이 이제 수치로 잡힌다."""

    def figs(self, text):
        return [(t.cls, t.value, t.raw) for t in numscan.figure_tokens(text)]

    def test_review_strings_are_figures(self):
        self.assertEqual(self.figs("천만 원 모으기"), [("won", Decimal(10 ** 7), "천만 원")])
        self.assertEqual(self.figs("연 백만 원"), [("won", Decimal(10 ** 6), "백만 원")])
        self.assertEqual(self.figs("세금이 두 배"), [("times", Decimal(2), "두 배")])
        self.assertEqual(self.figs("절반으로 줄어요"), [("times", Decimal("0.5"), "절반")])
        self.assertEqual(self.figs("2055년 기금 고갈"), [("year", Decimal(2055), "2055년")])
        self.assertEqual(self.figs("300 대비 늘어"), [("bare", Decimal(300), "300")])

    def test_more_hangul_amounts(self):
        self.assertEqual(self.figs("3천만 원"), [("won", Decimal(3 * 10 ** 7), "3천만 원")])
        self.assertEqual(self.figs("일억 오천만 원"), [("won", Decimal(15 * 10 ** 7), "일억 오천만 원")])
        self.assertEqual(self.figs("만 원으로 시작"), [("won", Decimal(10 ** 4), "만 원")])
        self.assertEqual(self.figs("오천 원"), [("won", Decimal(5000), "오천 원")])
        self.assertEqual(self.figs("천만 관객"), [("bare", Decimal(10 ** 7), "천만")])
        self.assertEqual(self.figs("수억 원"), [("won", None, "수억 원")])     # 값을 정할 수 없어도 수치
        self.assertEqual(self.figs("몇 배"), [("times", None, "몇 배")])

    def test_ordinary_words_are_not_figures(self):
        for text in ("이만 가자", "천천히", "천만에요", "세배 받기", "삼천포로", "<s>단위 만 원 · 집마다 다름</s>",
                     "내 월급의 두 주인 ⑤"):
            with self.subTest(text=text):
                self.assertEqual(numscan.figure_tokens(text), [])
        self.assertEqual([t.raw for t in numscan.figure_tokens("만 65세부터")], ["65세"])   # '만 나이' 의 만

    def test_years(self):
        old = numscan._this_year
        numscan._this_year = lambda: 2026
        try:
            self.assertEqual(raws("2026년 기준 · 국민연금공단"), ([], ["2026년"]))
            self.assertEqual(raws("2027년부터 시행"), ([], ["2027년"]))           # 내년까지는 날짜
            self.assertEqual(raws("2030년 1월부터"), (["2030년 1월"], []))       # 그보다 먼 연도는 수치
            self.assertEqual(raws("2026년 적자 전환 예상"), (["2026년"], []))    # 전망 문맥이면 올해도 수치
            self.assertEqual(raws("2008년 −37% 같은 큰 하락"), (["−37%"], ["2008년"]))
        finally:
            numscan._this_year = old

    def test_daebi_is_not_a_counter_but_age_groups_are(self):
        self.assertEqual(raws("30대에"), ([], ["30대"]))
        self.assertEqual(raws("「2대 연금」"), ([], ["2대"]))
        self.assertEqual(raws("100 대출"), (["100"], []))


class Corpus(unittest.TestCase):
    def test_all_published_specs_scan(self):
        self.assertEqual(len(SPECS), 10)
        for path in SPECS:
            for text in spec_texts(path):
                numscan.scan(text)

    def test_new_rules_do_not_change_the_published_corpus(self):
        # CR-04 규칙을 더해도 게시된 10편의 토큰 개수는 그대로다 (기대 개수 변경 없음)
        counts = {p.name[11:-5]: sum(len(numscan.figure_tokens(t)) for t in spec_texts(p)) for p in SPECS}
        self.assertEqual(counts, {"rate-secret-1": 10, "rate-secret-2": 9, "rate-secret-3": 15, "tax-deduction": 11,
                                  "salary-two-owners-1": 14, "ebook-event": 0, "salary-two-owners-2": 16,
                                  "salary-two-owners-3": 6, "salary-two-owners-4": 10, "salary-two-owners-5": 11})

    def test_tax_deduction_has_eleven_figure_tokens(self):
        path = next(p for p in SPECS if p.name.endswith("tax-deduction.json"))
        n = sum(len(numscan.figure_tokens(t)) for t in spec_texts(path))
        self.assertEqual(n, 11)

    def test_ebook_event_has_no_figure_tokens(self):
        path = next(p for p in SPECS if p.name.endswith("ebook-event.json"))
        self.assertEqual(sum(len(numscan.figure_tokens(t)) for t in spec_texts(path)), 0)

    def test_every_circled_numeral_is_structure(self):
        seen = 0
        for path in SPECS:
            for text in spec_texts(path):
                for ch in text:
                    if "①" <= ch <= "⑳":
                        seen += 1
                        self.assertIn(ch, [t.raw for t in numscan.scan(text) if t.kind == "structure"])
                        self.assertNotIn(ch, "".join(t.raw for t in numscan.figure_tokens(text)))
        self.assertGreater(seen, 0)


if __name__ == "__main__":
    unittest.main()
