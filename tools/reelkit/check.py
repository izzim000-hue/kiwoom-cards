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
from . import numscan

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

    def summary(self):
        return f"오류 {len(self.errors)}건 · 경고 {len(self.warnings)}건 · 확인 필요 {len(self.needs_check)}줄"

    def to_json(self, spec_path, registry_path):
        return {
            "spec": str(spec_path), "mode": self.mode, "checked_on": self.checked_on,
            "registry": {"path": str(registry_path), "schema": SCHEMA},
            "summary": self.summary(),
            "errors": [i.to_dict() for i in self.errors],
            "warnings": [i.to_dict() for i in self.warnings],
            "needs_check": list(self.needs_check),
            "figures_used": list(self.figures_used),
        }


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


def check_spec(spec, registry, *, publish_date=None):
    report = CheckReport(mode="draft", checked_on=date.today().isoformat())
    version = spec.get("version")
    if isinstance(version, bool) or version != 2:
        report.errors.append(CheckIssue("spec", None, "NOT_EXPANDED", HINTS["NOT_EXPANDED"], ""))
        return report

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
    for where, scene, text in fields:
        entries = by_where.get(where, [])
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
        for tok in numscan.figure_tokens("".join(masked)):
            report.errors.append(CheckIssue(where, scene, "UNREGISTERED", tok.raw, text))

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for src in entry.get("sources", []) if isinstance(entry.get("sources"), list) else []:
                if not (isinstance(src, str) and src.startswith("fig.")):
                    continue
                fid = src[4:]
                try:
                    fig = figreg.get_figure(registry, fid)
                except figreg.RegistryError:
                    report.errors.append(CheckIssue(where, scene, "UNKNOWN_FIG", fid, text))
                    continue
                used.add(fid)
                if fig["verified"] == "미확인":
                    slot = needs.setdefault(where, {"where": where, "scene": scene, "text": text,
                                                    "ids": [], "reason": "미확인 수치"})
                    if fid not in slot["ids"]:
                        slot["ids"].append(fid)

    for where, entries in by_where.items():
        if where not in known_wheres:
            report.errors.append(CheckIssue(
                str(where), None, "LEDGER_MISMATCH", "장부가 가리키는 위치가 원고에 없음", ""))

    report.needs_check = [needs[w] for w, _, _ in fields if w in needs]
    report.figures_used = sorted(used)
    return report
