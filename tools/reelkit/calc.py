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
MAX_MONTHS = 1200


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


def _months(m, name):
    """개월 수는 1..1200 의 정수여야 한다 (거듭제곱 계산량 제한, T-02-04)."""
    if m != m.to_integral_value() or not 1 <= m <= MAX_MONTHS:
        raise CalcError(f"{name}: 개월 수는 1~{MAX_MONTHS} 의 정수여야 함 (받은 값 {m})")
    return m


@_calc
def add(a, b):
    return a + b


@_calc
def sub(a, b):
    return a - b


@_calc
def mul(a, b):
    return a * b


@_calc
def div(a, b):
    if b == 0:
        raise CalcError("div: 0 으로 나눌 수 없음")
    return a / b


@_calc
def neg(a):
    return -a


@_calc
def pct_of(amount, rate_pct):
    """amount 의 rate_pct 퍼센트."""
    return amount * rate_pct / 100


@_calc
def with_local(rate_pct, local_ratio_pct):
    """소득세율에 개인지방소득세(소득세의 ratio %)를 더한 실효율: rate × (1 + ratio/100)."""
    return rate_pct * (1 + local_ratio_pct / 100)


@_calc
def after_tax(value, tax_pct):
    """세금을 뗀 값: value × (1 − tax/100)."""
    return value * (1 - tax_pct / 100)


@_calc
def installment_simple_interest(monthly, annual_rate_pct, months):
    """월 납입 적금의 단리 이자 합계: 월 납입액 × 연이율/12 × (1+2+…+개월). 나눗셈은 마지막에 한 번."""
    n = _months(months, "installment_simple_interest")
    return monthly * annual_rate_pct * n * (n + 1) / (100 * 12 * 2)


@_calc
def yield_pct(gain, principal):
    """수익률(%): gain / principal × 100."""
    return gain / principal * 100


@_calc
def months_between_ages(from_age, to_age):
    """나이 구간의 개월 수: (to − from) × 12. to 가 from 보다 커야 한다."""
    if to_age <= from_age:
        raise CalcError("months_between_ages: 끝 나이가 시작 나이보다 커야 함")
    return (to_age - from_age) * 12


@_calc
def annuity_pmt(target, annual_rate_pct, months):
    """목표 금액을 월 납입(월말, 월복리)으로 모으는 데 필요한 월 납입액. 연이율 0 이면 target / 개월."""
    n = _months(months, "annuity_pmt")
    if annual_rate_pct == 0:
        return target / n
    r = annual_rate_pct / 100 / 12
    return target * r / ((1 + r) ** n - 1)


@_calc
def fv_monthly(pmt, annual_rate_pct, months):
    """월 납입(월말, 월복리)의 만기 금액. 연이율 0 이면 pmt × 개월."""
    n = _months(months, "fv_monthly")
    if annual_rate_pct == 0:
        return pmt * n
    r = annual_rate_pct / 100 / 12
    return pmt * ((1 + r) ** n - 1) / r


FUNCTIONS = {
    "add": (add, 2),
    "sub": (sub, 2),
    "mul": (mul, 2),
    "div": (div, 2),
    "neg": (neg, 1),
    "pct_of": (pct_of, 2),
    "with_local": (with_local, 2),
    "after_tax": (after_tax, 2),
    "installment_simple_interest": (installment_simple_interest, 3),
    "yield_pct": (yield_pct, 2),
    "months_between_ages": (months_between_ages, 2),
    "annuity_pmt": (annuity_pmt, 3),
    "fv_monthly": (fv_monthly, 3),
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


def eok_man_won(value):
    """1억 이상은 '3억 7,200만 원' (만 부분이 0 이면 '3억 원'), 미만은 man_won 과 같다."""
    with localcontext() as ctx:
        ctx.prec = PREC
        man = (_d(value) / 10000).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        eok, rest = divmod(abs(man), 10000)
        if eok:
            body = f"{int(eok):,}억" + (f" {int(rest):,}만" if rest else "") + " 원"
        else:
            body = f"{int(rest):,}만 원"
        return (MINUS + body if man < 0 else body), man * 10000


FORMATS = {
    "pct": _make_format(1, "0.1", "%"),
    "pct0": _make_format(1, "1", "%"),
    "pct1": _make_format(1, "0.1", "%", keep_decimals=True),
    "signed_pct": _make_format(1, "0.1", "%", plus=True),
    "man": _make_format(10000, "1", "만", group=True),
    "man1": _make_format(10000, "0.1", "만", group=True),
    "man_won": _make_format(10000, "1", "만 원", group=True),
    "eok_man_won": eok_man_won,
    "won": _make_format(1, "1", "원", group=True),
    "num": _make_format(1, "0.1", "", group=True),
    "se": _make_format(1, "0.1", "세"),
    "nyeon": _make_format(1, "1", "년"),
    "gaewol": _make_format(1, "1", "개월"),
    "dal": _make_format(1, "0.1", "달"),
}
