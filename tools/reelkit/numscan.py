"""원고 문장 속 숫자 탐지·분류 (표준 라이브러리만 사용, D-07).

숫자를 두 종류로 나눈다.
- structure(구조 숫자): 원문자 ①, `#3`, 날짜(2026년, 26년 9월, 9월), 구성 숫자(3권, 4개, 2층 ...).
  예외로 취급하며 오류가 아니다.
- figure(수치): 그 밖의 모든 숫자. 금액·비율·나이·연·개월·배수·무단위 숫자. 등록부·입력·계산에서 온 것이어야 한다.

규칙 순서(research "Number detection"): 태그 제거 -> 상수 문구 가림 -> 구조 -> 범위 전개 -> 복합 금액 -> 일반 토큰.
가린 자리는 같은 길이의 `¤` 로 바꿔 위치를 유지하므로 토큰은 글 순서대로 돌려준다.
"""
import re
from decimal import Decimal
from typing import NamedTuple, Optional

MASK = "¤"
CONSTANT_PHRASES = ("1분 노후자금 계산기", "S&P500", "4대보험", "72의 법칙")


class Token(NamedTuple):
    kind: str                 # "figure" | "structure"
    cls: str                  # won pct age birth_year year month times time people bare | circled hash date count
    value: Optional[Decimal]  # structure 는 None
    raw: str


_TAG_RE = re.compile(r"</?[gs]>|<br\s*/?>")
_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_NO_DIGIT_BEFORE = r"(?<![\d,.])"

_CIRCLED_RE = re.compile("[①-⑳]")
_HASH_RE = re.compile(r"#\d+")
_DATE_RES = (
    re.compile(_NO_DIGIT_BEFORE + r"(?:19|20)\d{2}년(?!생)(?: \d{1,2}월)?"),
    re.compile(_NO_DIGIT_BEFORE + r"\d{2}년 \d{1,2}월"),
    re.compile(_NO_DIGIT_BEFORE + r"\d{1,2}월"),
)
_COUNT_RE = re.compile(_NO_DIGIT_BEFORE + r"\d+\s?(?:가지|개(?!월)|권|편|쪽|장|층|단계|대)")

_RANGE_RE = re.compile(
    r"(?P<a>" + _NO_DIGIT_BEFORE + r"(?:" + _NUM + r"))\s?[~∼]\s?(?P<b>(?:" + _NUM + r"))\s?"
    r"(?P<unit>세|년|개월|%|만\s?원|만|원)")
_COMPOUND_RE = re.compile(
    r"(?P<sign>(?<![\dA-Za-z])[+\-−])?" + _NO_DIGIT_BEFORE +
    r"(?P<eok>" + _NUM + r")억(?:\s*(?P<man>" + _NUM + r")만)?(?:\s?원)?")
_GENERAL_RE = re.compile(
    r"(?P<sign>(?<![\dA-Za-z])[+\-−])?" + _NO_DIGIT_BEFORE +
    r"(?P<num>" + _NUM + r")"
    r"(?P<unit>만\s?원|억\s?원|만|억|원|%|세|년생|년|개월|달|배|시간|분|일|주|명)?")

# 단위 -> (cls, 곱할 값)
_UNITS = {
    "만 원": ("won", Decimal(10) ** 4), "억 원": ("won", Decimal(10) ** 8),
    "만": ("won", Decimal(10) ** 4), "억": ("won", Decimal(10) ** 8), "원": ("won", Decimal(1)),
    "%": ("pct", Decimal(1)), "세": ("age", Decimal(1)), "년생": ("birth_year", Decimal(1)),
    "년": ("year", Decimal(1)), "개월": ("month", Decimal(1)), "달": ("month", Decimal(1)),
    "배": ("times", Decimal(1)), "시간": ("time", Decimal(1)), "분": ("time", Decimal(1)),
    "일": ("time", Decimal(1)), "주": ("time", Decimal(1)), "명": ("people", Decimal(1)),
    "": ("bare", Decimal(1)),
}


def strip_tags(text):
    """`<g>`, `</g>`, `<s>`, `</s>`, `<br>` 를 공백 하나로 바꾼다."""
    return _TAG_RE.sub(" ", text)


def _dec(num):
    return Decimal(num.replace(",", ""))


def _unit_key(unit):
    return re.sub(r"\s+", " ", unit) if unit else ""


def _sub(regex, text, found, make):
    """regex 일치를 가리고 (위치, Token 들)을 found 에 모은다. 가린 문자열을 돌려준다."""
    def repl(m):
        for tok in make(m):
            found.append((m.start(), tok))
        return MASK * (m.end() - m.start())
    return regex.sub(repl, text)


def scan(text):
    """text 의 숫자 토큰을 글 순서대로 돌려준다."""
    work = strip_tags(text)
    for phrase in CONSTANT_PHRASES:
        work = work.replace(phrase, MASK * len(phrase))
    found = []

    def structure(cls):
        return lambda m: [Token("structure", cls, None, m.group(0))]

    work = _sub(_CIRCLED_RE, work, found, structure("circled"))
    work = _sub(_HASH_RE, work, found, structure("hash"))
    for rx in _DATE_RES:
        work = _sub(rx, work, found, structure("date"))
    work = _sub(_COUNT_RE, work, found, structure("count"))

    def range_tokens(m):
        key = _unit_key(m.group("unit"))
        cls, mult = _UNITS[key]
        unit = m.group("unit")
        return [Token("figure", cls, _dec(m.group(g)) * mult, m.group(g) + unit) for g in ("a", "b")]
    work = _sub(_RANGE_RE, work, found, range_tokens)

    def compound(m):
        value = _dec(m.group("eok")) * Decimal(10) ** 8
        if m.group("man"):
            value += _dec(m.group("man")) * Decimal(10) ** 4
        if m.group("sign") in ("-", "−"):
            value = -value
        return [Token("figure", "won", value, m.group(0))]
    work = _sub(_COMPOUND_RE, work, found, compound)

    def general(m):
        cls, mult = _UNITS[_unit_key(m.group("unit"))]
        value = _dec(m.group("num")) * mult
        if m.group("sign") in ("-", "−"):
            value = -value
        return [Token("figure", cls, value, m.group(0))]
    work = _sub(_GENERAL_RE, work, found, general)

    found.sort(key=lambda item: item[0])
    return [tok for _, tok in found]


def figure_tokens(text):
    return [t for t in scan(text) if t.kind == "figure"]
