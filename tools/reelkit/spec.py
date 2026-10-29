"""원고 로더(v1/v2)와 legacy 마크업 허용 목록 (표준 라이브러리만 사용).

게시된 원고는 읽기만 한다 (D-05). 파싱한 dict 를 그대로 돌려주며 정규화하거나 디스크에 다시 쓰지 않는다.

v1 원고: `version` 이 없는 원고(게시된 10편). `scenes`(필수), 각 장면 `top`·`lines`, `basis`(선택)만 검사하며
이 검사와 오류 메시지는 바뀌지 않는다 (DRAFT-06, D-17).
v2 원고: `python3 tools/draft.py expand` 가 쓰는 초안. v1 필드에 아래 선택 필드가 더해지며, 각 필드는 있을 때만 검사한다.
  version      정수 2
  series       {name(비어 있지 않은 문자열), episode(정수 1..10, 선택), next(비어 있지 않은 문자열, 선택)}
  inputs       {이름: {value, unit, label}} 모두 문자열 (이 릴스 한정 시나리오 가정)
  derive       {이름: {fn, args}} 원고 소스의 계산식 그대로 (check 가 장부를 다시 계산할 때 씀, 형식 검사는 check)
  figures      [{where, text, ref, sources[...]...}] 숫자마다 출처를 적은 장부
  basis_items  [{fig, ...}] 쓰인 등록부 항목
  motion       문자열 또는 객체 (의미는 4단계에서 정의)
확장되지 않은 소스(`{{` 또는 `}}` 가 남은 원고)는 렌더하지 않도록 거부한다.
legacy 배치는 원고 문자열을 HTML 에 그대로 끼워 넣으므로(게시된 영상과 출력을 같게 유지하려는 선택),
렌더 전에 `<` 로 시작하는 모든 곳이 허용된 네 태그인지 검사한다 (research Pitfall 8).
"""
import json
from pathlib import Path

ALLOWED_TAGS = ("<g>", "</g>", "<s>", "</s>")


class SpecError(ValueError):
    """원고 파일을 읽을 수 없거나 형식이 틀렸을 때. 메시지는 한국어이며 장면/줄 번호는 1부터 센다."""


def load_spec(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        reason = getattr(e, "strerror", None) or str(e)
        raise SpecError(f"원고 파일을 열 수 없음: {path} ({reason})") from e
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as e:
        raise SpecError(f"원고 JSON 형식 오류: {path} 줄 {e.lineno} 열 {e.colno}") from e

    if not isinstance(spec, dict):
        raise SpecError(f"원고 최상위는 JSON 객체여야 함: {path}")
    scenes = spec.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SpecError("scenes: 비어 있지 않은 목록이어야 함")
    for n, sc in enumerate(scenes, 1):
        if not isinstance(sc, dict):
            raise SpecError(f"scene {n}: 객체여야 함")
        if not isinstance(sc.get("top"), str):
            raise SpecError(f"scene {n} top: 문자열이어야 함 (빈 문자열 가능)")
        lines = sc.get("lines")
        if not isinstance(lines, list) or not lines:
            raise SpecError(f"scene {n}: lines 는 비어 있지 않은 목록이어야 함")
        for m, line in enumerate(lines, 1):
            if not isinstance(line, str):
                raise SpecError(f"scene {n} line {m}: 문자열이어야 함")
    if "basis" in spec and not isinstance(spec["basis"], str):
        raise SpecError("basis: 문자열이어야 함")
    _check_optional(spec)
    _check_unexpanded(spec)
    return spec


SERIES_KEYS = ("name", "episode", "next")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def _check_optional(spec):
    """선택 필드(v2)는 있을 때만 형식을 검사한다. 기본값을 채우거나 정규화하지 않는다."""
    if "version" in spec and not (_is_int(spec["version"]) and spec["version"] == 2):
        raise SpecError(f"version: 지원하지 않는 원고 버전 {spec['version']!r} (정수 2 만 가능)")
    if "series" in spec:
        series = spec["series"]
        if not isinstance(series, dict):
            raise SpecError("series: 객체여야 함")
        unknown = [k for k in series if k not in SERIES_KEYS]
        if unknown:
            raise SpecError(f"series: 알 수 없는 키 {', '.join(map(str, unknown))} (허용: {', '.join(SERIES_KEYS)})")
        if not _nonempty_str(series.get("name")):
            raise SpecError("series.name: 비어 있지 않은 문자열이어야 함")
        if "episode" in series and not (_is_int(series["episode"]) and 1 <= series["episode"] <= 10):
            raise SpecError(f"series.episode: 1~10 정수여야 함 (원문자 ①~⑩) — {series['episode']!r}")
        if "next" in series and not _nonempty_str(series["next"]):
            raise SpecError("series.next: 비어 있지 않은 문자열이어야 함")
    if "inputs" in spec:
        inputs = spec["inputs"]
        if not isinstance(inputs, dict):
            raise SpecError("inputs: 객체여야 함")
        for name, item in inputs.items():
            if not isinstance(item, dict):
                raise SpecError(f"inputs.{name}: value, unit, label 을 가진 객체여야 함")
            for key in ("value", "unit", "label"):
                if not isinstance(item.get(key), str):
                    raise SpecError(f"inputs.{name}.{key}: 문자열이어야 함")
    if "figures" in spec:
        ledger = spec["figures"]
        if not isinstance(ledger, list):
            raise SpecError("figures: 목록이어야 함")
        for i, entry in enumerate(ledger, 1):
            if not isinstance(entry, dict):
                raise SpecError(f"figures[{i}]: 객체여야 함")
            for key in ("where", "text", "ref"):
                if not isinstance(entry.get(key), str):
                    raise SpecError(f"figures[{i}].{key}: 문자열이어야 함")
            if not isinstance(entry.get("sources"), list):
                raise SpecError(f"figures[{i}].sources: 목록이어야 함")
    if "basis_items" in spec:
        items = spec["basis_items"]
        if not isinstance(items, list):
            raise SpecError("basis_items: 목록이어야 함")
        for i, item in enumerate(items, 1):
            if not isinstance(item, dict) or not isinstance(item.get("fig"), str):
                raise SpecError(f"basis_items[{i}].fig: 문자열이 있는 객체여야 함")
    if "motion" in spec and not isinstance(spec["motion"], (str, dict)):
        raise SpecError("motion: 문자열 또는 객체여야 함")


def _check_unexpanded(spec):
    """`{{`, `}}` 가 남은 원고는 확장 전 소스다. 렌더하면 자리표시자가 화면에 찍히므로 거부한다."""
    hint = "확장 전 소스 원고 — 먼저 python3 tools/draft.py expand SRC OUT 로 확장하세요"
    for n, sc in enumerate(spec["scenes"], 1):
        fields = [(f"scene {n} top", sc["top"])] + [(f"scene {n} line {m}", ln) for m, ln in enumerate(sc["lines"], 1)]
        for where, text in fields:
            if "{{" in text or "}}" in text:
                raise SpecError(f"{where}: {hint}")
    basis = spec.get("basis", "")
    if "{{" in basis or "}}" in basis:
        raise SpecError(f"basis: {hint}")


def _check_text(text, where):
    i = text.find("<")
    while i != -1:
        if not text.startswith(ALLOWED_TAGS, i):
            snippet = text[i:i + 12]
            raise SpecError(
                f"{where}: 허용되지 않은 마크업 {snippet!r} — legacy 원고에는 <g>, </g>, <s>, </s> 만 쓸 수 있음")
        i = text.find("<", i + 1)


def check_legacy_markup(spec):
    """legacy 배치의 원문 삽입 보호: top/lines/basis 의 모든 `<` 는 허용 태그 네 가지 중 하나로 시작해야 한다."""
    for n, sc in enumerate(spec["scenes"], 1):
        _check_text(sc["top"], f"scene {n} top")
        for m, line in enumerate(sc["lines"], 1):
            _check_text(line, f"scene {n} line {m}")
    _check_text(spec.get("basis", ""), "basis")
