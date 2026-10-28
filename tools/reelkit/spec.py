"""v1 원고 로더와 legacy 마크업 허용 목록 (표준 라이브러리만 사용).

게시된 원고는 읽기만 한다 (D-05). 파싱한 dict 를 그대로 돌려주며 정규화하거나 디스크에 다시 쓰지 않는다.
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
    return spec


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
