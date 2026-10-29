"""초안 점검기: 숫자가 등록부·입력·계산에서 온 것인지 따라가고 결과를 check.json 으로 남긴다 (표준 라이브러리만 사용).

`draft.py expand` 가 쓴 v2 원고에는 숫자마다 출처를 적은 `figures` 장부가 있다. 장부는 점검 대상과 같은 파일에
있으므로 믿지 않는다 (CR-01). 점검기는
- 장부가 가리키는 글자 구간이 실제 글자와 같은지 확인하고 (다르면 LEDGER_MISMATCH),
- 장부의 ref·fmt 를 지금 등록부와 원고의 inputs·derive 로 다시 계산해 글자·value·sources·exact 가 같은지 보고
  (ref 가 없으면 LEDGER_FORGED, 값이 바뀌었으면 STALE_FIGURE), basis_items 도 다시 만들어 맞춰 보며,
- 장부 구간을 가린 나머지에서 수치 숫자를 찾아 (있으면 UNREGISTERED 오류, D-07),
- 장부의 등록부 id 가 미확인이면 그 줄을 `needs_check`(확인 필요)에 적는다 (D-03: 막지 않고 표시).
- inputs(시나리오 가정)를 쓴 줄은 `assumptions`(가정 수치)에 적고, 같은 줄이나 basis 에 예시·가정·가상 표기가
  없으면 ASSUMPTION_UNMARKED 오류다 (CR-02). 비율(%)은 inputs 로 쓸 수 없다 (expand 가 거부).
오류는 종료 코드 1, 경고는 `--strict` 일 때만 종료 코드 3 이다. 요약 문구에는 "통과" 를 쓰지 않는다.
"""
import re
from dataclasses import dataclass, field
from datetime import date

from . import figures as figreg
from . import convert, expand, motion, numscan, timeline
from .spec import ALLOWED_TAGS, SpecError

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
    "STALE_FIGURE": "등록부 값이나 계산이 장부와 달라짐 — python3 tools/draft.py expand 를 다시 실행",
    "LEDGER_FORGED": "expand 가 만든 장부가 아님 — 숫자는 원고 소스의 자리표시자로만 쓰고 expand 를 다시 실행",
    "LEDGER_REF": "장부의 참조를 원고의 inputs·derive 로 풀 수 없음 — expand 를 다시 실행",
    "BASIS_ITEMS": "basis_items 를 손으로 고치지 말고 expand 를 다시 실행",
    "SOURCE_MISMATCH": "spec.json 을 손으로 고치지 말고 spec.src.json 을 고쳐 expand 를 다시 실행",
    "REGISTRY_CONFIRM": "등록부의 확인 상태 기록이 잘못됨 — 확인은 사람이 터미널에서 figures confirm 으로만 (Claude 금지)",
    "ASSUMPTION_UNMARKED": "inputs(시나리오 가정) 숫자는 화면에 보여야 한다 — 같은 줄이나 basis 에 예시·가정·가상 표기",
    "UNIT_AFTER": "서식이 단위를 찍는다 — 자리표시자 뒤에 만/원/% 같은 단위를 글자로 쓰지 말고 man_won, pct 같은 서식을 쓰세요",
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
    assumptions: list = field(default_factory=list)   # inputs(시나리오 가정)를 쓴 줄 (CR-02)
    figures_used: list = field(default_factory=list)
    checked_on: str = ""
    legacy_count: int = 0
    card: object = None   # dict | None — `--card` 대조 결과 {path, new_numbers, dropped_notes}
    source: object = None  # str | None — 다시 확장해 대조한 원고 소스 경로

    def summary(self):
        if self.mode == "legacy":
            text = f"등록부 없음 {self.legacy_count}개 — 게시된 v1 원고는 고치지 않음"
            if self.card is not None:
                text += (f" · 카드 대조: 카드에 없는 숫자 {len(self.card['new_numbers'])}개"
                         f" · 옮기지 않은 note {len(self.card['dropped_notes'])}개")
            return text
        return (f"오류 {len(self.errors)}건 · 경고 {len(self.warnings)}건 · 확인 필요 {len(self.needs_check)}줄"
                f" · 가정 수치 {len(self.assumptions)}줄")

    def to_json(self, spec_path, registry_path):
        out = {
            "spec": str(spec_path), "mode": self.mode, "checked_on": self.checked_on,
            "registry": {"path": None if registry_path is None else str(registry_path), "schema": SCHEMA},
            "source": self.source,
            "summary": self.summary(),
            "errors": [i.to_dict() for i in self.errors],
            "warnings": [i.to_dict() for i in self.warnings],
            "needs_check": list(self.needs_check),
            "assumptions": list(self.assumptions),
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


def _rederive(spec, registry):
    """원고의 inputs·derive 를 지금 등록부로 다시 계산한 값 표. 계산할 수 없으면 (None, 오류 문구)."""
    try:
        return expand.build_values(spec.get("inputs", {}), spec.get("derive", {}), registry), None
    except expand.ExpandError as e:
        return None, str(e)


_REF_ERROR_KINDS = {"UNKNOWN_FIG": "UNKNOWN_FIG", "UNKNOWN_REF": "LEDGER_REF", "UNIT": "UNIT_FORMAT",
                    "FORMAT": "LEDGER_FORGED", "CALC": "LEDGER_REF"}


def _verify_entry(entry, vals, where, scene, text, err):
    """장부 항목을 믿지 않고 ref·fmt 로 다시 계산해 맞춰 본다 (CR-01).

    돌려주는 값: (근거 리프, 정확값 여부) — 글자 구간을 가려도 되는 항목. 다시 계산할 수 없는 항목(ref 없음,
    모르는 id, 서식·단위 불일치)은 None 이라 구간이 가려지지 않고 그 숫자는 UNREGISTERED 로도 잡힌다.
    값이 바뀐 항목(STALE_FIGURE)과 value/sources/exact 를 고친 항목은 오류를 남기고 다시 계산한 리프를 돌려준다.
    """
    ref, fmt = entry.get("ref"), entry.get("fmt")
    if vals is None:
        return None
    if not isinstance(ref, str) or not ref or not isinstance(fmt, str):
        err(CheckIssue(where, scene, "LEDGER_FORGED",
                       f"장부 {entry.get('text')!r} 에 ref·fmt 가 없음 — expand 가 만든 장부가 아님", text))
        return None
    try:
        rendered, shown, value, leaves, _unit = expand.render_ref(vals, ref, fmt, where)
    except expand.ExpandError as e:
        kind = _REF_ERROR_KINDS.get(e.kind, "LEDGER_FORGED")
        err(CheckIssue(where, scene, kind, ref[4:] if kind == "UNKNOWN_FIG" else str(e), text))
        return None
    exact = shown == value
    if rendered != entry["text"]:
        err(CheckIssue(where, scene, "STALE_FIGURE",
                       f"장부 {entry['text']!r} 를 지금 등록부·계산으로 찍으면 {rendered!r} ({ref}|{fmt})", text))
    elif (entry.get("value") != expand.norm(value) or entry.get("sources") != sorted(leaves)
          or entry.get("exact") is not exact):
        err(CheckIssue(where, scene, "LEDGER_MISMATCH",
                       f"장부 {entry['text']!r} 의 value·sources·exact 가 다시 계산한 값과 다름 ({ref})", text))
    return leaves, exact


def check_spec(spec, registry, *, publish_date=None):
    report = CheckReport(mode="draft", checked_on=date.today().isoformat())
    version = spec.get("version")
    if isinstance(version, bool) or version != 2:
        report.errors.append(CheckIssue("spec", None, "NOT_EXPANDED", HINTS["NOT_EXPANDED"], ""))
        return report
    publish_date = publish_date or date.today()
    basis_text = spec.get("basis") if isinstance(spec.get("basis"), str) else ""
    err = report.errors.append

    for fid, problem in figreg.confirmation_problems(registry):
        err(CheckIssue("registry", None, "REGISTRY_CONFIRM", f"{fid}: {problem}", ""))

    vals, derive_error = _rederive(spec, registry)
    if derive_error:
        err(CheckIssue("inputs/derive", None, "DERIVE", derive_error, ""))

    ledger = spec.get("figures")
    if not isinstance(ledger, list):
        ledger = []
    by_where = {}
    for entry in ledger:
        where = entry.get("where") if isinstance(entry, dict) else None
        by_where.setdefault(where, []).append(entry)

    used, needs = set(), {}
    fresh = {}   # id(장부 항목) -> 다시 계산한 근거 리프 (basis_items 대조용)
    fields = _fields(spec)
    known_wheres = {w for w, _, _ in fields}
    warn = report.warnings.append
    for where, scene, text in fields:
        entries = by_where.get(where, [])
        # 마크업·자리표시자 (new 배치는 허용 태그 네 가지 외에는 글자로 찍는다, research Pitfall 6)
        for i in (m.start() for m in re.finditer("<", text)):
            if not text.startswith(ALLOWED_TAGS, i):
                snippet = BAD_TAG_RE.match(text, i).group(0)
                err(CheckIssue(where, scene, "MARKUP", snippet, text))
        if "{{" in text or "}}" in text:
            err(CheckIssue(where, scene, "PLACEHOLDER", "{{ }}", text))

        masked = list(text)
        last_end = 0
        field_leaves = []
        for entry in sorted((e for e in entries if isinstance(e, dict)),
                            key=lambda e: e["start"] if isinstance(e.get("start"), int) else 0):
            if not _entry_ok(entry, text) or entry["start"] < last_end:
                err(CheckIssue(where, scene, "LEDGER_MISMATCH", f"장부 {entry.get('text')!r} 자리의 글자가 다름", text))
                continue
            verified = _verify_entry(entry, vals, where, scene, text, err)
            if verified is None:
                continue
            leaves, exact = verified
            fresh[id(entry)] = sorted(leaves)
            field_leaves.append(leaves)
            for i in range(entry["start"], entry["end"]):
                masked[i] = MASK
            last_end = entry["end"]
            unit = expand.unit_after_problem(entry["text"], text[entry["end"]:])
            if unit:
                err(CheckIssue(where, scene, "UNIT_AFTER",
                               f"{entry['text']} 뒤에 단위 {unit!r} 를 글자로 붙임 — 단위가 든 서식 필요", text))
            if not exact and not APPROX_BEFORE_RE.search(text[:entry["start"]]):
                warn(CheckIssue(where, scene, "APPROX",
                                f"{entry['text']} — 정확값이 아님, 앞에 '약' 표기 권장", text))
        for tok in numscan.figure_tokens("".join(masked)):
            err(CheckIssue(where, scene, "UNREGISTERED", tok.raw, text))

        input_leaves = sorted({leaf for leaves in field_leaves for leaf in leaves if leaf.startswith("inputs.")})
        if input_leaves:
            inputs = spec.get("inputs") if isinstance(spec.get("inputs"), dict) else {}
            report.assumptions.append({
                "where": where, "scene": scene, "text": text, "inputs": input_leaves,
                "labels": [str((inputs.get(leaf[7:]) or {}).get("label", "")) for leaf in input_leaves]})
            if not (expand.LABEL_MARK_RE.search(text) or expand.LABEL_MARK_RE.search(basis_text)):
                err(CheckIssue(where, scene, "ASSUMPTION_UNMARKED", ", ".join(input_leaves), text))

        seen, local_hit = set(), False
        for leaves in field_leaves:
            for src in sorted(leaves):
                if not src.startswith("fig."):
                    continue
                fid = src[4:]
                fig = figreg.get_figure(registry, fid)   # render_ref 가 이미 찾은 id
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
                    err(CheckIssue(where, scene, "REPEALED", fid, text))
                if fig["legal_status"] == "발의" and not (
                        PROPOSAL_MARK_RE.search(text) or PROPOSAL_MARK_RE.search(basis_text)):
                    err(CheckIssue(where, scene, "PROPOSED_AS_FACT", fid, text))
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
            err(CheckIssue(str(where), None, "LEDGER_MISMATCH", "장부가 가리키는 위치가 원고에 없음", ""))

    # basis_items(게시글 기준일·근거에 쓰임)도 장부를 다시 계산한 리프와 지금 등록부로 다시 만들어 맞춰 본다
    expected = expand.basis_items([fresh[id(e)] for e in ledger if id(e) in fresh], registry)
    if spec.get("basis_items", []) != expected:
        err(CheckIssue("basis_items", None, "BASIS_ITEMS",
                       "basis_items 가 장부·지금 등록부로 다시 만든 목록과 다름", ""))

    _input_shadows(spec, registry, warn)
    _house_pattern(spec, warn, err)

    report.needs_check = [needs[w] for w, _, _ in fields if w in needs]
    report.figures_used = sorted(used)
    return report


SOURCE_KEYS = ("version", "series", "basis", "scenes", "inputs", "derive", "figures", "basis_items", "motion")


def compare_source(spec, src, registry):
    """원고 소스(spec.src.json)를 지금 등록부로 다시 확장한 결과와 원고가 다르면 SOURCE_MISMATCH 오류 목록 (CR-01)."""
    try:
        again = expand.expand_source(src, registry)
    except expand.ExpandError as e:
        return [CheckIssue("source", None, "SOURCE_MISMATCH", f"원고 소스를 다시 확장할 수 없음 — {e}", "")]
    diff = [k for k in SOURCE_KEYS if again.get(k) != spec.get(k)]
    if not diff:
        return []
    return [CheckIssue("source", None, "SOURCE_MISMATCH",
                       f"원고 소스를 지금 등록부로 다시 확장한 결과와 다름: {', '.join(diff)}", "")]


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


def _house_pattern(spec, warn, err):
    scenes = spec["scenes"]
    n = len(scenes)
    if not SCENES_MIN <= n <= SCENES_MAX:
        warn(CheckIssue("scenes", None, "SCENES", f"{n}장면 — 하우스 패턴 {SCENES_MIN}~{SCENES_MAX}장면", ""))
    try:
        mode = motion.resolve(spec)
    except SpecError as e:
        err(CheckIssue("motion", None, "MOTION", str(e), ""))
        mode = None
    if mode is not None:
        # basic 은 글자 수로 정한 장면 시간표의 길이, none 은 기존 타임라인의 길이로 잰다 (MOTN-05)
        total = motion.schedule(spec).total if mode == "basic" else timeline.total_duration(timeline.build_states(spec))
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
