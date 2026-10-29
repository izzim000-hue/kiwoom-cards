"""파생 수치 계산과 표시 서식 (표준 라이브러리 decimal 만 사용, D-05).

규칙 (02-RESEARCH "Derived figures"):
- 모든 계산은 Decimal (정밀도 34자리). 이진 부동소수점이나 내장 반올림 함수는 쓰지 않는다
  (6*1.1 이 6.6000000000000005 가 되고, 내장 반올림은 동점을 짝수로 보내 386.5 가 386 이 된다).
- 중간 결과는 반올림하지 않는다. 반올림은 표시 서식에서 한 번만, 사사오입(ROUND_HALF_UP: 동점은 올림)으로 한다.
- 서식 함수는 `(text, shown)` 을 돌려준다. `shown` 은 화면에 적힌 값을 다시 기본 단위로 바꾼 것이라
  정확값과 같은지(`exact`) 장부에 기록할 수 있다.

FUNCTIONS = {이름: (함수, 인자 수)}, FORMATS = {이름: 서식 함수}. expand 는 이 두 사전에 있는 이름만 쓴다.
"""
import functools
from decimal import ROUND_HALF_UP, Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext

MINUS = "−"
PREC = 34


class CalcError(ValueError):
    """계산 인자나 결과가 잘못되었을 때. 메시지는 한국어."""


def _d(x):
    """인자를 유한한 Decimal 로. 부동소수점(float)과 bool 은 받지 않는다."""
    if isinstance(x, bool) or not isinstance(x, (Decimal, int, str)):
        raise CalcError(f"숫자 인자는 Decimal 이어야 함: {x!r}")
    try:
        d = x if isinstance(x, Decimal) else Decimal(x)
    except InvalidOperation:
        raise CalcError(f"숫자로 읽을 수 없음: {x!r}") from None
    if not d.is_finite():
        raise CalcError(f"유한한 숫자여야 함: {x!r}")
    return d


def _calc(fn):
    """Decimal 정밀도 고정, 인자 검사, 0 나눗셈·무효 연산을 CalcError 로 바꾼다."""
    @functools.wraps(fn)
    def wrapper(*args):
        with localcontext() as ctx:
            ctx.prec = PREC
            try:
                result = fn(*[_d(a) for a in args])
            except DivisionByZero:
                raise CalcError(f"{fn.__name__}: 0 으로 나눌 수 없음") from None
            except (InvalidOperation, Overflow):
                raise CalcError(f"{fn.__name__}: 계산할 수 없는 값 {args!r}") from None
            if not result.is_finite():
                raise CalcError(f"{fn.__name__}: 유한하지 않은 결과")
            return result
    return wrapper


@_calc
def pct_of(amount, rate_pct):
    """amount 의 rate_pct 퍼센트."""
    return amount * rate_pct / 100


@_calc
def with_local(rate_pct, local_ratio_pct):
    """소득세율에 개인지방소득세(소득세의 ratio %)를 더한 실효율: rate × (1 + ratio/100)."""
    return rate_pct * (1 + local_ratio_pct / 100)


FUNCTIONS = {
    "pct_of": (pct_of, 2),
    "with_local": (with_local, 2),
}


# ---- 표시 서식 -------------------------------------------------------------------------------

def _group_plain(q, group, keep_decimals):
    """부호 없는 양자화 값 q 를 문자열로. 정수부 천 단위 쉼표, 끝의 '.0' 은 keep_decimals 가 아니면 생략."""
    s = format(q, "f")
    whole, _, frac = s.partition(".")
    if not keep_decimals:
        frac = frac.rstrip("0")
    if group:
        whole = f"{int(whole):,}"
    return whole + ("." + frac if frac else "")


def _make_format(scale, places, suffix, *, group=False, plus=False, keep_decimals=False):
    scale = Decimal(scale)
    step = Decimal(places)

    def fmt(value):
        with localcontext() as ctx:
            ctx.prec = PREC
            q = (_d(value) / scale).quantize(step, rounding=ROUND_HALF_UP)
            body = _group_plain(abs(q), group, keep_decimals) + suffix
            if q < 0:
                text = MINUS + body
            elif plus and q > 0:
                text = "+" + body
            else:
                text = body
            return text, q * scale
    return fmt


FORMATS = {
    "pct": _make_format(1, "0.1", "%"),
    "man1": _make_format(10000, "0.1", "만", group=True),
    "man_won": _make_format(10000, "1", "만 원", group=True),
    "won": _make_format(1, "1", "원", group=True),
}
