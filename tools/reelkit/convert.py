"""카드뉴스 원고 -> 릴스 골격, 그리고 카드 대조 (표준 라이브러리만 사용, DRAFT-02).

카드 원고 모양: `{"series": str, "cards": [{"title", "lines", "emph", "note", "dark"}]}`.
골격은 Claude 가 압축·재작성하기 전의 재료다. 카드에서 읽는 값만 담고 문구를 지어내지 않는다:
- 시리즈명·회차·다음 편 (카드 `series` 의 끝 "N편", 카드 줄 "다음 편: X")
- 장면 역할(hook/body/conclusion/caution/cta)과 카드 번호, 카드 제목·줄(`<br>` 는 공백으로, 강조는 `<g>`)
- 카드 note 와 카드에 있던 숫자 목록
대조 함수는 릴스 원고의 숫자 중 카드에 없던 것(new_number_warnings)과 릴스에 옮겨지지 않은 카드 note(dropped_notes)를 찾는다.
릴스 원고는 읽기만 한다 (게시된 원고를 고치지 않음).
"""
import json
import re
from decimal import Decimal
from pathlib import Path

from . import numscan

CAUTION_TOP = "단, 꼭 알아둘 것"
CAUTION_KEYWORDS = ("세무사", "보장", "손실", "권유", "예시", "가정")
CTA_MATERIAL = ["저장해두고", "", "", "<s>프로필 링크 · 1분 노후자금 계산기</s>"]
_EPISODE_RE = re.compile(r"^(.*?)\s*(\d+)편$")
_NEXT_RE = re.compile(r"^다음 편:\s*(.+)$")
_BR_RE = re.compile(r"<br\s*/?>")
_STRIP_RE = re.compile(r"</?[gs]>|<br\s*/?>|\s+")


class ConvertError(ValueError):
    """카드 원고를 읽을 수 없거나 모양이 틀렸을 때. 메시지는 한국어이며 위치를 밝힌다."""


def load_card(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ConvertError(f"카드 원고를 열 수 없음: {path} ({getattr(e, 'strerror', None) or e})") from None
    try:
        card = json.loads(text)
    except json.JSONDecodeError as e:
        raise ConvertError(f"카드 원고 JSON 형식 오류: {path} 줄 {e.lineno} 열 {e.colno}") from None
    if not isinstance(card, dict):
        raise ConvertError(f"카드 원고 최상위는 JSON 객체여야 함: {path}")
    cards = card.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ConvertError(f"cards: 비어 있지 않은 목록이어야 함: {path}")
    for n, c in enumerate(cards, 1):
        if not isinstance(c, dict):
            raise ConvertError(f"card {n}: 객체여야 함")
        if not isinstance(c.get("title"), str):
            raise ConvertError(f"card {n} title: 문자열이어야 함")
        for key in ("lines", "emph"):
            val = c.get(key, [])
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                raise ConvertError(f"card {n} {key}: 문자열 목록이어야 함")
        if c.get("note") is not None and not isinstance(c["note"], str):
            raise ConvertError(f"card {n} note: 문자열 또는 null 이어야 함")
    if "series" in card and not isinstance(card["series"], str):
        raise ConvertError("series: 문자열이어야 함")
    return card


def _flat(text):
    """`<br>` 를 공백 하나로."""
    return " ".join(_BR_RE.sub(" ", text).split())


def _norm(d):
    return "0" if d == 0 else format(d.normalize(), "f")


def _series(card, cards):
    raw = (card.get("series") or "").strip()
    out = {}
    m = _EPISODE_RE.match(raw)
    if m and m.group(1):
        out["name"] = m.group(1)
        if 1 <= int(m.group(2)) <= 10:
            out["episode"] = int(m.group(2))
    elif raw:
        out["name"] = raw
    for c in cards:
        for line in c.get("lines", []):
            nm = _NEXT_RE.match(line.strip())
            if nm:
                out["next"] = nm.group(1).strip()
                return out
    return out


def _is_dropped_line(line):
    return line.strip().startswith("저장해두고") or _NEXT_RE.match(line.strip()) is not None


def _material(c, *, last=False):
    emph = set(c.get("emph", []))
    out = []
    for line in c.get("lines", []):
        if last and _is_dropped_line(line):
            continue
        flat = _flat(line)
        out.append(f"<g>{flat}</g>" if line in emph or flat in {_flat(e) for e in emph} else flat)
    return out


def card_skeleton(card, source):
    cards = card["cards"]
    last_i = len(cards) - 1
    scenes = []
    for i, c in enumerate(cards):
        title = _flat(c["title"])
        note = c.get("note")
        if i == 0 and last_i > 0:
            role, top, material = "hook", "", [title] + _material(c)
        elif i == last_i and last_i > 0:
            role, top, material = "conclusion", title, _material(c, last=True)
        else:
            role, top, material = "body", title, _material(c)
        scenes.append({"role": role, "cards": [i + 1], "top": top, "material": material,
                       "notes": [note] if note else []})
    cautions = [c["note"] for c in cards if c.get("note") and any(k in c["note"] for k in CAUTION_KEYWORDS)]
    scenes.append({"role": "caution", "cards": [], "top": CAUTION_TOP, "material": cautions, "notes": []})
    scenes.append({"role": "cta", "cards": [], "top": "", "material": list(CTA_MATERIAL), "notes": []})
    return {
        "source": str(source),
        "series": _series(card, cards),
        "scenes": scenes,
        "notes": [{"card": i + 1, "text": c["note"]} for i, c in enumerate(cards) if c.get("note")],
        "source_numbers": [
            {"card": n, "raw": t.raw, "cls": t.cls, "value": _norm(t.value)}
            for n, text in _card_texts(card) for t in numscan.figure_tokens(text)],
    }


def _card_texts(card):
    """(카드 번호, 글) 을 카드 순서로: 제목, 줄들, note."""
    for n, c in enumerate(card["cards"], 1):
        yield n, _flat(c["title"])
        for line in c.get("lines", []):
            yield n, _flat(line)
        if c.get("note"):
            yield n, _flat(c["note"])


def _spec_fields(spec):
    for n, sc in enumerate(spec["scenes"], 1):
        yield f"scene {n} top", n, sc["top"]
        for m, line in enumerate(sc["lines"], 1):
            yield f"scene {n} line {m}", n, line
    if isinstance(spec.get("basis"), str):
        yield "basis", None, spec["basis"]


def new_number_warnings(card, spec):
    """릴스 원고의 수치 숫자 중 카드에 없던 것. 무단위 숫자는 값 또는 값 x 10^4 가 카드의 어떤 숫자 값과 같으면 같은 숫자로 본다."""
    tokens = [t for _, text in _card_texts(card) for t in numscan.figure_tokens(text)]
    known = {(t.cls, t.value) for t in tokens}
    values = {t.value for t in tokens}
    out = []
    for where, scene, text in _spec_fields(spec):
        for tok in numscan.figure_tokens(text):
            if (tok.cls, tok.value) in known:
                continue
            if tok.cls == "bare" and (tok.value in values or tok.value * Decimal(10) ** 4 in values):
                continue
            out.append({"where": where, "scene": scene, "raw": tok.raw, "text": text})
    return out


def _squash(text):
    return _STRIP_RE.sub("", text)


def dropped_notes(card, spec):
    """릴스 글에 어떤 조각(" · " 구분)도 옮겨지지 않은 카드 note. 태그와 공백은 무시하고 비교한다."""
    reel = _squash("".join(text for _, _, text in _spec_fields(spec)))
    out = []
    for n, c in enumerate(card["cards"], 1):
        note = c.get("note")
        if not note:
            continue
        parts = [_squash(p) for p in note.split(" · ")]
        if not any(p and p in reel for p in parts):
            out.append({"card": n, "note": note})
    return out
