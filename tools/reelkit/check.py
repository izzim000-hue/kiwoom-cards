"""초안 점검기: 숫자가 등록부·입력·계산에서 온 것인지 따라가고 결과를 check.json 으로 남긴다 (표준 라이브러리만 사용).

`draft.py expand` 가 쓴 v2 원고에는 숫자마다 출처를 적은 `figures` 장부가 있다. 점검기는
- 장부가 가리키는 글자 구간이 실제 글자와 같은지 확인하고 (다르면 LEDGER_MISMATCH),
- 장부 구간을 가린 나머지에서 수치 숫자를 찾아 (있으면 UNREGISTERED 오류, D-07),
- 장부의 등록부 id 가 미확인이면 그 줄을 `needs_check`(확인 필요)에 적는다 (D-03: 막지 않고 표시).
오류는 종료 코드 1, 경고는 `--strict` 일 때만 종료 코드 3 이다. 요약 문구에는 "통과" 를 쓰지 않는다.
"""
import re
from dataclasses import dataclass, field
from datetime import date

from . import figures as figreg
from . import convert, numscan, timeline
from .spec import ALLOWED_TAGS

# 하우스 패턴 수치 (research "하우스 패턴 수치": 게시된 10편 실측 — 7장면, 21.8~26.05초, 줄 20~22자, top 최대 21자, 장면당 2~4줄).
# 경고 기준이며 오류가 아니다. 줄 길이는 렌더 전의 거친 신호일 뿐이고 줄바꿈 판정은 reel.py --layout new --strict 의
# WRAP 경고가 맡는다 (본문 100px Black 은 한 줄에 한글 9자 안팎에서 줄바꿈되어, 이 기준을 맞춰도 줄어들지 않는다).
SCENES_MIN, SCENES_MAX = 6, 8
DUR_MIN, DUR_MAX = 21.0, 27.0
LINE_MAX = 22
TOP_MAX = 21
LINES_MIN, LINES_MAX = 2, 5

PROPOSAL_MARK_RE = re.compile(r"발의|개정안|정부안|시행 전")
APPROX_BEFORE_RE = re.compile(r"약\s*(?:<g>\s*)?$")
TAG_RE = re.compile(r"</?[gs]>")
BAD_TAG_RE = re.compile(r"</?[A-Za-z][^<>\s]{0,19}>?|<")
CAUTION_WORDS = ("단,", "주의", "알아둘")

SCHEMA = 1
MASK = numscan.MASK

HINTS = {
    "NOT_EXPANDED": "expand 로 만든 원고가 아님 — python3 tools/draft.py expand 를 먼저 실행",
    "UNREGISTERED": "등록부·inputs·derive 자리표시자가 아닌 숫자 — 필요한 수치면 먼저 사용자에게 물으세요 (D-06)",
}

_WHERE_RE = re.compile(r"scene (\d+) (?:top|line (\d+))$")


@dataclass
class CheckIssue:
    where: str
    scene: object      # int | None
    kind: str
    detail: str
    text: str

    def __str__(self):
        return f'{self.where}: {self.kind} ({self.detail}) "{self.text}"'

    def to_dict(self):
        return {"where": self.where, "scene": self.scene, "kind": self.kind, "detail": self.detail, "text": self.text}


@dataclass
class CheckReport:
    mode: str = "draft"
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    needs_check: list = field(default_factory=list)
    figures_used: list = field(default_factory=list)
    checked_on: str = ""
    legacy_count: int = 0
    card: object = None   # dict | None — `--card` 대조 결과 {path, new_numbers, dropped_notes}

    def summary(self):
        if self.mode == "legacy":
            text = f"등록부 없음 {self.legacy_count}개 — 게시된 v1 원고는 고치지 않음"
            if self.card is not None:
                text += (f" · 카드 대조: 카드에 없는 숫자 {len(self.card['new_numbers'])}개"
                         f" · 옮기지 않은 note {len(self.card['dropped_notes'])}개")
            return text
        return f"오류 {len(self.errors)}건 · 경고 {len(self.warnings)}건 · 확인 필요 {len(self.needs_check)}줄"

    def to_json(self, spec_path, registry_path):
        out = {
            "spec": str(spec_path), "mode": self.mode, "checked_on": self.checked_on,
            "registry": {"path": None if registry_path is None else str(registry_path), "schema": SCHEMA},
            "summary": self.summary(),
            "errors": [i.to_dict() for i in self.errors],
            "warnings": [i.to_dict() for i in self.warnings],
            "needs_check": list(self.needs_check),
            "figures_used": list(self.figures_used),
        }
        if self.card is not None:
            out["card"] = self.card
        return out


def _fields(spec):
    """(where, scene, text) 를 문서 순서(장면 1 top, 줄..., 장면 2 ..., basis 마지막)로."""
    out = []
    for n, sc in enumerate(spec["scenes"], 1):
        out.append((f"scene {n} top", n, sc["top"]))
        for m, line in enumerate(sc["lines"], 1):
            out.append((f"scene {n} line {m}", n, line))
    if isinstance(spec.get("basis"), str):
        out.append(("basis", None, spec["basis"]))
    return out


def _entry_ok(entry, text):
    s, e = entry.get("start"), entry.get("end")
    if not (isinstance(s, int) and isinstance(e, int) and not isinstance(s, bool) and not isinstance(e, bool)):
        return False
    return 0 <= s <= e <= len(text) and text[s:e] == entry.get("text")


def _visible(text):
    return len(TAG_RE.sub("", text))


def _parse_date(text):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def check_spec(spec, registry, *, publish_date=None):
    report = CheckReport(mode="draft", checked_on=date.today().isoformat())
    version = spec.get("version")
    if isinstance(version, bool) or version != 2:
        report.errors.append(CheckIssue("spec", None, "NOT_EXPANDED", HINTS["NOT_EXPANDED"], ""))
        return report
    publish_date = publish_date or date.today()
    basis_text = spec.get("basis") if isinstance(spec.get("basis"), str) else ""

    ledger = spec.get("figures")
    if not isinstance(ledger, list):
        ledger = []
    by_where = {}
    for entry in ledger:
        where = entry.get("where") if isinstance(entry, dict) else None
        by_where.setdefault(where, []).append(entry)

    used, needs = set(), {}
    fields = _fields(spec)
    known_wheres = {w for w, _, _ in fields}
    warn = report.warnings.append
    for where, scene, text in fields:
        entries = by_where.get(where, [])
        # 마크업·자리표시자 (new 배치는 허용 태그 네 가지 외에는 글자로 찍는다, research Pitfall 6)
        for i in (m.start() for m in re.finditer("<", text)):
            if not text.startswith(ALLOWED_TAGS, i):
                snippet = BAD_TAG_RE.match(text, i).group(0)
                report.errors.append(CheckIssue(where, scene, "MARKUP", snippet, text))
        if "{{" in text or "}}" in text:
            report.errors.append(CheckIssue(where, scene, "PLACEHOLDER", "{{ }}", text))

        masked = list(text)
        last_end = 0
        for entry in sorted((e for e in entries if isinstance(e, dict)),
                            key=lambda e: e["start"] if isinstance(e.get("start"), int) else 0):
            if not _entry_ok(entry, text) or entry["start"] < last_end:
                report.errors.append(CheckIssue(
                    where, scene, "LEDGER_MISMATCH", f"장부 {entry.get('text')!r} 자리의 글자가 다름", text))
                continue
            for i in range(entry["start"], entry["end"]):
                masked[i] = MASK
            last_end = entry["end"]
            if entry.get("exact") is False and not APPROX_BEFORE_RE.search(text[:entry["start"]]):
                warn(CheckIssue(where, scene, "APPROX",
                                f"{entry['text']} — 정확값이 아님, 앞에 '약' 표기 권장", text))
        for tok in numscan.figure_tokens("".join(masked)):
            report.errors.append(CheckIssue(where, scene, "UNREGISTERED", tok.raw, text))

        seen, local_hit = set(), False
        for entry in entries:
            sources = entry.get("sources") if isinstance(entry, dict) else None
            for src in sources if isinstance(sources, list) else []:
                if not (isinstance(src, str) and src.startswith("fig.")):
                    continue
                fid = src[4:]
                try:
                    fig = figreg.get_figure(registry, fid)
                except figreg.RegistryError:
                    if ("unknown", fid) not in seen:
                        seen.add(("unknown", fid))
                        report.errors.append(CheckIssue(where, scene, "UNKNOWN_FIG", fid, text))
                    continue
                used.add(fid)
                if fid in seen:
                    continue
                seen.add(fid)
                slot = None
                if fig["verified"] == "미확인" or fig["legal_status"] == "발의":
                    slot = needs.setdefault(where, {"where": where, "scene": scene, "text": text,
                                                    "ids": [], "reason": "발의 수치"})
                    slot["ids"].append(fid)
                    if fig["verified"] == "미확인":
                        slot["reason"] = "미확인 수치"
                if fig["legal_status"] == "폐지":
                    report.errors.append(CheckIssue(where, scene, "REPEALED", fid, text))
                if fig["legal_status"] == "발의" and not (
                        PROPOSAL_MARK_RE.search(text) or PROPOSAL_MARK_RE.search(basis_text)):
                    report.errors.append(CheckIssue(where, scene, "PROPOSED_AS_FACT", fid, text))
                vu = _parse_date(fig.get("valid_until"))
                if vu is not None and vu < publish_date:
                    warn(CheckIssue(where, scene, "EXPIRED",
                                    f"{fid} valid_until {vu.isoformat()} < 게시일 {publish_date.isoformat()}", text))
                if fig.get("includes_local") or fid == "local_income_tax_ratio":
                    local_hit = True
        if local_hit and "지방소득세" not in text and "지방소득세" not in basis_text:
            warn(CheckIssue(where, scene, "LOCAL_TAX_NOTE",
                            "지방소득세 포함 값 — 같은 줄이나 basis 에 지방소득세 포함 표기 필요", text))

    for where in by_where:
        if where not in known_wheres:
            report.errors.append(CheckIssue(
                str(where), None, "LEDGER_MISMATCH", "장부가 가리키는 위치가 원고에 없음", ""))

    _input_shadows(spec, registry, warn)
    _house_pattern(spec, warn)

    report.needs_check = [needs[w] for w, _, _ in fields if w in needs]
    report.figures_used = sorted(used)
    return report


def _input_shadows(spec, registry, warn):
    inputs = spec.get("inputs")
    if not isinstance(inputs, dict):
        return
    for name, item in inputs.items():
        if not isinstance(item, dict):
            continue
        try:
            value = figreg.parse_value(item.get("value"), f"inputs.{name}")
        except figreg.RegistryError:
            continue
        same = [fid for fid, fig in registry["figures"].items()
                if fig["unit"] == item.get("unit") and figreg.parse_value(fig["value"], fid) == value]
        if same:
            warn(CheckIssue(f"inputs.{name}", None, "INPUT_SHADOWS_FIG",
                            f"등록부 id {', '.join(same)} 와 같은 값 — fig 참조 권장", str(item.get("label", ""))))


def _house_pattern(spec, warn):
    scenes = spec["scenes"]
    n = len(scenes)
    if not SCENES_MIN <= n <= SCENES_MAX:
        warn(CheckIssue("scenes", None, "SCENES", f"{n}장면 — 하우스 패턴 {SCENES_MIN}~{SCENES_MAX}장면", ""))
    total = timeline.total_duration(timeline.build_states(spec))
    if not DUR_MIN <= total <= DUR_MAX:
        warn(CheckIssue("scenes", None, "DURATION", f"{total:.1f}초 — 하우스 패턴 {DUR_MIN:g}~{DUR_MAX:g}초", ""))
    for i, sc in enumerate(scenes, 1):
        if _visible(sc["top"]) > TOP_MAX:
            warn(CheckIssue(f"scene {i} top", i, "TOP_LONG", f"{_visible(sc['top'])}자 > {TOP_MAX}", sc["top"]))
        for j, line in enumerate(sc["lines"], 1):
            if _visible(line) > LINE_MAX:
                warn(CheckIssue(f"scene {i} line {j}", i, "LINE_LONG", f"{_visible(line)}자 > {LINE_MAX}", line))
        if not LINES_MIN <= len(sc["lines"]) <= LINES_MAX:
            warn(CheckIssue(f"scene {i}", i, "LINES", f"{len(sc['lines'])}줄 — 장면당 {LINES_MIN}~{LINES_MAX}줄", sc["top"]))
    last = scenes[-1]
    if last["top"] != "" or not any("프로필 링크" in ln for ln in last["lines"]):
        warn(CheckIssue(f"scene {n}", n, "NO_CTA", "마지막 장면은 top 이 비고 '프로필 링크' 줄이 있어야 함", last["top"]))
    if not any(w in sc["top"] for sc in scenes for w in CAUTION_WORDS):
        warn(CheckIssue("scenes", None, "NO_CAUTION", "주의 장면(top 에 '단,' '주의' '알아둘') 없음", ""))
    if not any("<g>" in t for sc in scenes for t in [sc["top"], *sc["lines"]]):
        warn(CheckIssue("scenes", None, "NO_EMPH", "<g> 강조가 한 곳도 없음", ""))


def card_warnings(card, spec):
    """카드 원고와 릴스 원고 대조 경고: 카드에 없던 숫자(NOT_IN_CARD), 릴스에 옮겨지지 않은 카드 note(CARD_NOTE_DROPPED)."""
    issues = [CheckIssue(w["where"], w["scene"], "NOT_IN_CARD", w["raw"], w["text"])
              for w in convert.new_number_warnings(card, spec)]
    issues += [CheckIssue(f"card {d['card']} note", None, "CARD_NOTE_DROPPED", d["note"], "")
               for d in convert.dropped_notes(card, spec)]
    return issues


def apply_card(report, card, spec, card_path):
    """card_warnings 를 report.warnings 에 더하고 check.json 의 `card` 블록을 채운다."""
    issues = card_warnings(card, spec)
    report.warnings.extend(issues)
    report.card = {
        "path": str(card_path),
        "new_numbers": [i.to_dict() for i in issues if i.kind == "NOT_IN_CARD"],
        "dropped_notes": [i.to_dict() for i in issues if i.kind == "CARD_NOTE_DROPPED"],
    }
    return issues


def legacy_report(spec):
    """게시된 v1 원고용: 장부가 없으니 수치 숫자 개수만 센다. 구조·상태 규칙은 적용하지 않고 아무것도 고치지 않는다 (D-17)."""
    report = CheckReport(mode="legacy", checked_on=date.today().isoformat())
    report.legacy_count = sum(len(numscan.figure_tokens(text)) for _, _, text in _fields(spec))
    return report
