"""원고 문장 속 숫자 탐지·분류 (표준 라이브러리만 사용, D-07).

숫자를 두 종류로 나눈다.
- structure(구조 숫자): 원문자 ①, `#3`, 날짜(2026년, 26년 9월, 9월), 구성 숫자(3권, 4개, 2층 ...).
  예외로 취급하며 오류가 아니다.
- figure(수치): 그 밖의 모든 숫자. 금액·비율·나이·연·개월·배수·무단위 숫자. 등록부·입력·계산에서 온 것이어야 한다.
  한글 수 표현(천만 원, 백만 원, 3천만 원, 두 배, 절반)과 전망·고갈 같은 수치로 쓰인 연도(2055년 기금 고갈,
  내년 다음 해보다 먼 연도)도 수치다 (CR-04). 값을 정할 수 없는 표현(수억 원, 몇 배)은 value 가 None 이다.

규칙 순서(research "Number detection"): 태그 제거 -> 상수 문구 가림 -> 구조(수치 연도 제외) -> 범위 전개 -> 복합 금액
-> 한글 수 표현 -> 일반 토큰.
가린 자리는 같은 길이의 `¤` 로 바꿔 위치를 유지하므로 토큰은 글 순서대로 돌려준다.
"""
import re
from datetime import date
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
_YEAR_RE = re.compile(_NO_DIGIT_BEFORE + r"(?P<year>(?:19|20)\d{2})년(?!생)(?: \d{1,2}월)?")
_DATE_RES = (
    re.compile(_NO_DIGIT_BEFORE + r"\d{2}년 \d{1,2}월"),
    re.compile(_NO_DIGIT_BEFORE + r"\d{1,2}월"),
)
# 연도가 날짜가 아니라 전망·통계 수치로 쓰인 경우 (2055년 기금 고갈, 2030년 적자 전환 예상)
_YEAR_FIGURE_CONTEXT = re.compile(r"^[^.·|,\n]{0,12}?(?:고갈|소진|바닥|적자|흑자|전망|예상|추정|추계|예측|목표|도달|돌파)")
# 대비(비교), 대출, 대금 의 '대' 는 세는 말이 아니다 (300 대비)
_COUNT_RE = re.compile(_NO_DIGIT_BEFORE + r"\d+\s?(?:가지|개(?!월)|권|편|쪽|장|층|단계|대(?!비|출|금))")

# 한글 수 표현 (CR-04). 숫자 없이 쓴 금액·배수는 일반 토큰 규칙에 걸리지 않으므로 따로 찾는다.
_HDIGITS = {c: i for i, c in enumerate("일이삼사오육칠팔구", 1)}
_HSMALL = {"십": 10, "백": 100, "천": 1000}
_HBIG = {"만": 10 ** 4, "억": 10 ** 8}
_HCHARS = "일이삼사오육칠팔구십백천만억"
_HNUM_RE = re.compile(
    r"(?<![가-힣\d.,])(?:(?P<lead>\d+(?:\.\d+)?)(?=[십백천]))?(?P<vague>수|몇)?"
    r"(?P<body>[" + _HCHARS + r"]+(?:\s[" + _HCHARS + r"]*만)?)"
    r"(?:(?P<won>\s?원)|(?![가-힣]))")
_HTIMES = {"두": 2, "세": 3, "네": 4, "다섯": 5, "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10, "몇": None,
           "수십": None, "수백": None}
_HTIMES_RE = re.compile(r"(?<![가-힣])(?P<w>두|세|네|다섯|여섯|일곱|여덟|아홉|열|몇|수십|수백)(?P<sp>\s?)배(?![추우달송꼽])")
_HALF_RE = re.compile(r"절반|반값|반토막")
_UNIT_LABEL_BEFORE = re.compile(r"단위\s*[:：]?\s*$")

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


def _this_year():
    return date.today().year


def _hangul_value(lead, body):
    """'삼천오백만', '천만', '일억 오천만', lead='3' + '천만' 을 Decimal 로. 올바른 수 표현이 아니면 None."""
    total, section = Decimal(0), Decimal(0)
    cur = Decimal(lead) if lead else None
    last_small, last_big = 10 ** 5, 10 ** 9
    for ch in body.replace(" ", ""):
        if ch in _HDIGITS:
            if cur is not None:
                return None
            cur = Decimal(_HDIGITS[ch])
        elif ch in _HSMALL:
            if _HSMALL[ch] >= last_small:
                return None
            last_small = _HSMALL[ch]
            section += (cur if cur is not None else 1) * _HSMALL[ch]
            cur = None
        else:
            if _HBIG[ch] >= last_big:
                return None
            last_big = _HBIG[ch]
            section += cur if cur is not None else 0
            total += (section or 1) * _HBIG[ch]
            section, cur, last_small = Decimal(0), None, 10 ** 5
    return total + section + (cur or 0)


def _hangul_number(m, work):
    """_HNUM_RE 일치가 수치이면 Token, 아니면 None (만 65세, 이만 가자, 천천히 같은 말은 수치가 아니다)."""
    lead, vague, body, won = m.group("lead"), m.group("vague"), m.group("body"), m.group("won")
    has_small = lead is not None or any(c in _HSMALL for c in body)
    has_big = any(c in _HBIG for c in body)
    if " " in body and not body.split(" ")[0].endswith("억"):
        return None
    value = _hangul_value(lead, body)
    if value is None:
        return None
    if won:
        if not (has_small or has_big or body[-1] in _HSMALL):
            return None
        if not has_small and not vague and _UNIT_LABEL_BEFORE.search(work[:m.start()]):
            return None       # "단위 만 원" 은 표의 단위 표시
    elif not (has_big and (has_small or vague)):
        return None           # 숫자 없는 '만', '이만', '오만', '천' 만으로는 수치로 보지 않는다
    return Token("figure", "won" if won else "bare", None if vague else value, m.group(0))


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
    def year(m):
        y = int(m.group("year"))
        if y > _this_year() + 1 or _YEAR_FIGURE_CONTEXT.match(work[m.end():]):
            return [Token("figure", "year", Decimal(y), m.group(0))]
        return [Token("structure", "date", None, m.group(0))]
    work = _sub(_YEAR_RE, work, found, year)
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

    def hangul(m):
        tok = _hangul_number(m, work)
        if tok is None:
            return m.group(0)
        found.append((m.start(), tok))
        return MASK * (m.end() - m.start())
    work = _HNUM_RE.sub(hangul, work)

    def times(m):
        if m.group("w") == "세" and not m.group("sp"):
            return m.group(0)     # 세배(새해 인사)
        found.append((m.start(), Token("figure", "times", _HTIMES[m.group("w")] and Decimal(_HTIMES[m.group("w")]),
                                       m.group(0))))
        return MASK * (m.end() - m.start())
    work = _HTIMES_RE.sub(times, work)
    work = _sub(_HALF_RE, work, found, lambda m: [Token("figure", "times", Decimal("0.5"), m.group(0))])

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
