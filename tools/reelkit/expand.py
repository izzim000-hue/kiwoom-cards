"""원고 소스(자리표시자 포함) -> v1 호환 원고 + 수치 장부 (표준 라이브러리만 사용, D-05).

소스는 `basis`(선택), `inputs`(선택), `derive`(선택), `series`(선택), `scenes` 만 가진다. 숫자는 글자로 적지 않고
`{{이름|서식}}` 으로 쓴다. 이름은 등록부 id (`fig.<id>`), 이 릴스 한정 시나리오 가정 (`inputs.<name>`),
또는 앞서 정의한 `derive` 이름이다. 값 계산은 calc.FUNCTIONS, 표시는 calc.FORMATS 만 쓴다 (eval/exec 없음).

결과에는 숫자마다 한 줄씩 `figures` 장부(어느 장면·줄의 어느 글자가 어떤 등록부/입력에서 왔는지)와
쓰인 등록부 항목의 `basis_items`, 그리고 소스의 `derive` 가 그대로 들어간다 (check 가 장부를 믿지 않고 다시 계산하는 데
쓴다). 렌더러는 완성된 평문 문자열만 본다.
"""
import copy
import json
import os
import re
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from . import calc, figures

ALLOWED_KEYS = ("basis", "inputs", "derive", "series", "scenes")
SERIES_KEYS = ("name", "episode", "next")
# 원문자는 ⑩ 까지만 쓴다 (⑪ 이상은 번들 폰트에서 확인되지 않음, research 가정 A3)
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
NEXT_PREFIX = "<s>다음 편:"
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\|\s*([a-z0-9_]+)\s*\}\}")
NAME_RE = re.compile(r"^[a-z0-9_]+$")
LABEL_MARKS = ("예시", "가정", "가상")
LABEL_MARK_RE = re.compile("|".join(LABEL_MARKS))
SPEC_VERSION = 2


class ExpandError(ValueError):
    """소스가 규칙에 어긋나 확장할 수 없을 때. 메시지는 한국어이며 위치(where)를 밝힌다.

    `kind` 는 check 가 같은 규칙을 다시 적용할 때 쓰는 분류다 (UNKNOWN_FIG, UNKNOWN_REF, FORMAT, UNIT, CALC, SOURCE).
    """

    def __init__(self, message, kind="SOURCE"):
        super().__init__(message)
        self.kind = kind


def norm(d):
    """Decimal 을 지수 표기 없는 정규화 문자열로."""
    if d == 0:
        return "0"
    return format(d.normalize(), "f")


class _Values:
    """이름 -> (정확값 Decimal, 근거 리프 집합, 단위). 등록부 조회는 get_figure 를 거친다."""

    def __init__(self, registry, inputs):
        self.registry = registry
        self.inputs = inputs      # name -> (Decimal, 단위)
        self.derived = {}         # name -> (Decimal, frozenset, 단위)
        self.declared = set()     # 선언된 derive 이름 (정의 순서 위반 구분용)

    def lookup(self, ref, where):
        if ref.startswith("fig."):
            fid = ref[4:]
            try:
                entry = figures.get_figure(self.registry, fid)  # 없는 id 는 비슷한 id 제안을 담아 던진다
                value = figures.parse_value(entry["value"], f"{fid}.value")
            except figures.RegistryError as e:
                raise ExpandError(f"{where}: {e}", kind="UNKNOWN_FIG") from None
            return value, frozenset({ref}), entry["unit"]
        if ref.startswith("inputs."):
            name = ref[7:]
            if name not in self.inputs:
                raise ExpandError(f"{where}: 선언되지 않은 입력 {ref} (선언된 입력: {', '.join(self.inputs) or '없음'})",
                                  kind="UNKNOWN_REF")
            value, unit = self.inputs[name]
            return value, frozenset({ref}), unit
        if "." in ref:
            raise ExpandError(f"{where}: 알 수 없는 참조 {ref} — fig.<id>, inputs.<name>, derive 이름만 쓸 수 있음",
                              kind="UNKNOWN_REF")
        if ref in self.derived:
            return self.derived[ref]
        if ref in self.declared:
            raise ExpandError(f"{where}: derive {ref} 는 아직 정의되기 전에 참조됨 (derive 는 선언 순서대로 계산)",
                              kind="UNKNOWN_REF")
        raise ExpandError(f"{where}: 알 수 없는 이름 {ref} (derive 에 선언하거나 fig./inputs. 를 붙여야 함)",
                          kind="UNKNOWN_REF")


def _check_inputs(raw):
    if not isinstance(raw, dict):
        raise ExpandError("inputs: 객체여야 함")
    values = {}
    for name, item in raw.items():
        where = f"inputs.{name}"
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise ExpandError(f"{where}: 이름은 영문 소문자·숫자·밑줄만 쓸 수 있음")
        if not isinstance(item, dict) or set(item) != {"value", "unit", "label"}:
            raise ExpandError(f"{where}: value, unit, label 세 필드를 가진 객체여야 함")
        if not isinstance(item["value"], str):
            raise ExpandError(f"{where}: value 는 문자열이어야 함")
        try:
            d = Decimal(item["value"].strip())
        except InvalidOperation:
            raise ExpandError(f"{where}: value 를 숫자로 읽을 수 없음 {item['value']!r}") from None
        if not d.is_finite():
            raise ExpandError(f"{where}: value 는 유한한 숫자여야 함 {item['value']!r}")
        if item["unit"] not in figures.UNITS:
            raise ExpandError(f"{where}: unit {item['unit']!r} — 허용: {', '.join(repr(u) for u in figures.UNITS)}")
        if item["unit"] == calc.PCT:
            raise ExpandError(f"{where}: 비율(%)은 inputs 로 쓸 수 없음 — 세율·요율·수익률은 등록부(fig.)에서 가져온다 "
                              f"(시나리오 수익률이면 사용자 승인 뒤 figures add 로 market/constant 항목 추가)", kind="UNIT")
        label = item["label"]
        if not isinstance(label, str) or not any(m in label for m in LABEL_MARKS):
            raise ExpandError(f"{where}: label 에 예시/가정/가상 표기가 필요함")
        values[name] = (d, item["unit"])
    return values


def _eval_derive(raw, vals):
    if not isinstance(raw, dict):
        raise ExpandError("derive: 객체여야 함")
    vals.declared = set(raw)
    for name, item in raw.items():
        where = f"derive.{name}"
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise ExpandError(f"{where}: 이름은 영문 소문자·숫자·밑줄만 쓸 수 있음")
        if not isinstance(item, dict) or set(item) != {"fn", "args"}:
            raise ExpandError(f"{where}: fn 과 args 두 필드를 가진 객체여야 함")
        fn_name, args = item["fn"], item["args"]
        if fn_name not in calc.FUNCTIONS:
            raise ExpandError(f"{where}: 알 수 없는 함수 {fn_name!r} (사용 가능: {', '.join(calc.FUNCTIONS)})")
        func, arity = calc.FUNCTIONS[fn_name]
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ExpandError(f"{where}: args 는 참조 문자열 목록이어야 함")
        if len(args) != arity:
            raise ExpandError(f"{where}: {fn_name} 는 인자 {arity}개가 필요한데 {len(args)}개를 받음")
        resolved = [vals.lookup(a, where) for a in args]
        leaves = frozenset().union(*(r[1] for r in resolved)) if resolved else frozenset()
        try:
            unit = calc.result_unit(fn_name, [r[2] for r in resolved])
        except calc.UnitError as e:
            raise ExpandError(f"{where}: 단위 오류 — {e}", kind="UNIT") from None
        try:
            value = func(*[r[0] for r in resolved])
        except (calc.CalcError, ZeroDivisionError, InvalidOperation) as e:
            raise ExpandError(f"{where}: 계산 오류 — {e}", kind="CALC") from None
        vals.derived[name] = (value, leaves, unit)


# 자리표시자 바로 뒤에 글자로 붙인 단위 (CR-03). 서식이 단위를 찍으므로 원고에 단위를 따로 쓰면
# "{{한도|num}}만 원" -> "9,000,000만 원" 처럼 자릿수가 틀린 숫자가 장부 출처를 단 채 화면에 나간다.
_LEADING_TAGS = re.compile(r"^(?:</?[gs]>)+")
_UNIT_AFTER_DIGITS = re.compile(r"^\s?(?:[만억천백십]|원|%|퍼센트|프로|세(?!대)|년|개월|달)")
_UNIT_AFTER_SUFFIX = re.compile(r"^\s?(?:원|[만억천백]\s?원|(?:만|억)(?![가-힣])|%|퍼센트)")


def unit_after_problem(rendered, rest):
    """서식으로 찍은 글자(rendered) 뒤의 원고 글자(rest)가 단위로 시작하면 그 단위 글자, 아니면 None."""
    rest = _LEADING_TAGS.sub("", rest)
    rx = _UNIT_AFTER_DIGITS if rendered[-1:].isdigit() else _UNIT_AFTER_SUFFIX
    m = rx.match(rest)
    return m.group(0).strip() if m else None


def render_ref(vals, ref, fmt, where):
    """참조 ref 를 서식 fmt 로 찍는다: (글자, 화면값, 정확값, 근거 리프, 단위). 서식·단위가 안 맞으면 ExpandError.

    expand 와 check 가 같은 함수를 써서, check 가 장부를 믿지 않고 다시 계산할 수 있다 (CR-01).
    """
    if not isinstance(fmt, str) or fmt not in calc.FORMATS:
        raise ExpandError(f"{where}: 알 수 없는 서식 {fmt!r} (사용 가능: {', '.join(calc.FORMATS)})", kind="FORMAT")
    if not isinstance(ref, str) or not ref:
        raise ExpandError(f"{where}: 참조 이름이 없음", kind="UNKNOWN_REF")
    value, leaves, unit = vals.lookup(ref, where)
    if unit == calc.PCT and not any(leaf.startswith("fig.") for leaf in leaves):
        raise ExpandError(f"{where}: {ref} — 비율(%) 값은 등록부 수치(fig.)에서 와야 함 (inputs 만으로 만든 비율은 쓸 수 없음)",
                          kind="UNIT")
    try:
        calc.check_format_unit(fmt, unit)
    except calc.UnitError as e:
        raise ExpandError(f"{where}: {ref} — {e}", kind="UNIT") from None
    try:
        rendered, shown = calc.FORMATS[fmt](value)
    except (calc.CalcError, InvalidOperation) as e:
        raise ExpandError(f"{where}: 서식 오류 — {e}", kind="CALC") from None
    return rendered, shown, value, leaves, unit


def _expand_field(text, where, scene, vals, ledger):
    parts, cur, pos = [], 0, 0
    for m in PLACEHOLDER.finditer(text):
        literal = text[pos:m.start()]
        parts.append(literal)
        cur += len(literal)
        ref, fmt = m.group(1), m.group(2)
        rendered, shown, value, leaves, _unit = render_ref(vals, ref, fmt, where)
        bad = unit_after_problem(rendered, text[m.end():])
        if bad:
            raise ExpandError(f"{where}: 자리표시자 {{{{{ref}|{fmt}}}}} 뒤에 단위 {bad!r} 를 글자로 쓸 수 없음 "
                              f"— 단위가 든 서식(man_won, pct, se ...)을 쓰세요", kind="UNIT")
        ledger.append({
            "where": where, "scene": scene, "start": cur, "end": cur + len(rendered), "text": rendered,
            "ref": ref, "fmt": fmt, "value": norm(value), "exact": shown == value, "sources": sorted(leaves),
        })
        parts.append(rendered)
        cur += len(rendered)
        pos = m.end()
    parts.append(text[pos:])
    out = "".join(parts)
    if "{{" in out or "}}" in out:
        raise ExpandError(f"{where}: 해석되지 않은 자리표시자가 남음 — {{{{이름|서식}}}} 형식이어야 함: {out!r}")
    return out


def _series_text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ExpandError(f"{where}: 비어 있지 않은 문자열이어야 함")
    for bad in ("{{", "}}", "<"):
        if bad in value:
            raise ExpandError(f"{where}: {bad!r} 는 쓸 수 없음")


def _check_series(series):
    if not isinstance(series, dict):
        raise ExpandError("series: 객체여야 함")
    unknown = [k for k in series if k not in SERIES_KEYS]
    if unknown:
        raise ExpandError(f"series: 알 수 없는 키 {', '.join(map(str, unknown))} (허용: {', '.join(SERIES_KEYS)})")
    _series_text(series.get("name"), "series.name")
    if "episode" in series:
        ep = series["episode"]
        if isinstance(ep, bool) or not isinstance(ep, int) or not 1 <= ep <= len(CIRCLED):
            raise ExpandError(f"series.episode: 1~{len(CIRCLED)} 정수여야 함 (원문자 ①~⑩) — {ep!r}")
    if "next" in series:
        _series_text(series["next"], "series.next")


def series_top(series):
    """장면 1 top 과 게시글 첫 줄에 쓰는 `시리즈명 ①` 문자열."""
    if "episode" in series:
        return f"{series['name']} {CIRCLED[series['episode'] - 1]}"
    return series["name"]


def next_line(series):
    """마지막(CTA) 장면에 넣는 `<s>다음 편: X</s>` 줄. next 가 없으면 None."""
    if "next" not in series:
        return None
    return f"{NEXT_PREFIX} {series['next']}</s>"


def _apply_series(scenes, series):
    """시리즈 값을 장면 1 top 과 마지막 장면 줄에 반영한다 (자리표시자 해석 전이라 장부 줄 번호가 확정된다)."""
    want = series_top(series)
    first = scenes[0]
    if first["top"] == "":
        first["top"] = want
    elif first["top"] != want:
        raise ExpandError(f"scene 1 top: 시리즈 지정 시 비워 두거나 {want!r} 와 같아야 함 (덮어쓰지 않음)")
    teaser = next_line(series)
    if teaser is None:
        return
    last = scenes[-1]
    for line in last["lines"]:
        if line == teaser:
            return
        if line.startswith(NEXT_PREFIX):
            raise ExpandError(f"scene {len(scenes)}: 다음 편 줄이 series.next 와 다름 — {line!r} (기대: {teaser!r})")
    at = next((i for i, line in enumerate(last["lines"]) if "프로필 링크" in line), len(last["lines"]))
    last["lines"].insert(at, teaser)


def _check_scenes(scenes):
    if not isinstance(scenes, list) or not scenes:
        raise ExpandError("scenes: 비어 있지 않은 목록이어야 함")
    for n, sc in enumerate(scenes, 1):
        if not isinstance(sc, dict):
            raise ExpandError(f"scene {n}: 객체여야 함")
        if not isinstance(sc.get("top"), str):
            raise ExpandError(f"scene {n} top: 문자열이어야 함 (빈 문자열 가능)")
        lines = sc.get("lines")
        if not isinstance(lines, list) or not lines:
            raise ExpandError(f"scene {n}: lines 는 비어 있지 않은 목록이어야 함")
        for m, line in enumerate(lines, 1):
            if not isinstance(line, str):
                raise ExpandError(f"scene {n} line {m}: 문자열이어야 함")


def expand_source(src, registry):
    """소스 dict 를 확장한 새 원고 dict 를 돌려준다. 입력 dict 는 바꾸지 않는다."""
    if not isinstance(src, dict):
        raise ExpandError("원고 소스 최상위는 JSON 객체여야 함")
    src = copy.deepcopy(src)
    unknown = [k for k in src if k not in ALLOWED_KEYS]
    if unknown:
        raise ExpandError(f"알 수 없는 최상위 키: {', '.join(map(str, unknown))} (허용: {', '.join(ALLOWED_KEYS)})")
    if "basis" in src and not isinstance(src["basis"], str):
        raise ExpandError("basis: 문자열이어야 함")
    _check_scenes(src.get("scenes"))
    series = None
    if "series" in src:
        _check_series(src["series"])
        series = src["series"]
        _apply_series(src["scenes"], series)

    inputs_raw = src.get("inputs", {})
    derive_raw = src.get("derive", {})
    vals = build_values(inputs_raw, derive_raw, registry)

    ledger = []
    out = {"version": SPEC_VERSION}
    if series is not None:
        out["series"] = dict(series)
    if "basis" in src:
        out["basis"] = _expand_field(src["basis"], "basis", None, vals, ledger)
    scenes = src["scenes"]
    for n, sc in enumerate(scenes, 1):
        sc["top"] = _expand_field(sc["top"], f"scene {n} top", n, vals, ledger)
        sc["lines"] = [_expand_field(line, f"scene {n} line {m}", n, vals, ledger)
                       for m, line in enumerate(sc["lines"], 1)]
    out["scenes"] = scenes
    if inputs_raw:
        out["inputs"] = inputs_raw
    if derive_raw:
        out["derive"] = derive_raw   # check 가 장부를 믿지 않고 다시 계산할 수 있게 남긴다 (CR-01)
    out["figures"] = ledger
    out["basis_items"] = basis_items([e["sources"] for e in ledger], registry)
    return out


def build_values(inputs_raw, derive_raw, registry):
    """inputs 와 derive 를 검사·계산한 값 표. expand 와 check(다시 계산)가 함께 쓴다."""
    vals = _Values(registry, _check_inputs(inputs_raw))
    _eval_derive(derive_raw, vals)
    return vals


def basis_items(leaf_lists, registry):
    """장부 순서대로 쓰인 등록부 항목 목록 (id 마다 한 번). leaf_lists 는 장부 항목마다의 근거 리프 목록."""
    seen, items = set(), []
    for leaves in leaf_lists:
        for leaf in leaves:
            if not leaf.startswith("fig.") or leaf in seen:
                continue
            seen.add(leaf)
            fid = leaf[4:]
            fig = figures.get_figure(registry, fid)
            items.append({
                "fig": fid, "label": fig["label"], "source": fig["source"]["name"], "as_of": fig["as_of"],
                "verified": fig["verified"], "legal_status": fig["legal_status"],
            })
    return items


def write_spec(spec, path):
    """임시 파일에 쓴 뒤 os.replace 로 바꿔 넣는다 (쓰다 만 원고를 남기지 않음)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
