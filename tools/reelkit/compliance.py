"""금소법 표현 점검기: 규칙 데이터 파일(tools/data/compliance_rules.json)을 읽어 원고·근거·게시글·해시태그를 훑는다 (표준 라이브러리만 사용).

점검 규칙은 코드가 아니라 데이터 파일에 있다. 규칙을 고치거나 더하면 코드 변경 없이 다음 점검부터 바뀐다 (COMP-05).
결과 머리말은 두 가지뿐이다: `위험 표현 n건 발견 · ...` 또는 `패턴상 발견 없음 — 사람 검수 필요 · ...`.
이 점검은 키워드·패턴 방식이라 암시적 표현은 잡지 못한다. 대체 표현은 제안만 하고 원고는 고치지 않는다 (D-10).
규칙은 준법 검토 전 초안이며 조문 번호를 인용하지 않는다 (D-05).
"""
import hashlib
import json
import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path

from . import constants

RULES_PATH = constants.TOOLS_DIR / "data" / "compliance_rules.json"
SCHEMA = 1
SEVERITIES = ("수정 필요", "확인 필요")
RULE_TYPES = ("pattern", "requires", "basis_required")
LIMITS = "한계: 키워드·패턴 방식이라 암시적 표현은 잡지 못합니다 — 사람 검수 필요 (AI 의미 점검은 v2)"

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠­﻿"))
_MARKUP_RE = re.compile(r"</?[gs]>")
_HASHTAG_TOKEN_RE = re.compile(r"^#\S+$")


class RuleError(ValueError):
    """규칙 파일이 규칙에 어긋날 때. 메시지는 한국어이며 규칙 id 를 밝힌다."""


# ---------------------------------------------------------------- 규칙 읽기

@dataclass
class Rule:
    id: str
    category: str
    severity: str
    type: str = "pattern"
    regex: object = None          # pattern 규칙의 컴파일된 정규식
    when: object = None
    when_scene: object = None
    must_have: object = None
    negatable: bool = True
    excepts: list = field(default_factory=list)
    applies_to: tuple = ("reel", "caption")
    scope: object = None
    reason: str = ""
    suggest: str = ""
    examples: dict = field(default_factory=dict)


@dataclass
class Rules:
    path: Path
    sha256: str
    version: str
    as_of: str
    status: str
    rules: list
    negators: object = None
    mention_markers: object = None
    compact_terms: list = field(default_factory=list)


def _expand(text, macros):
    """매크로 {J}, {S} 처럼 파일에 선언된 이름만 글자 그대로 바꾼다. {2,3} 같은 반복 표기는 건드리지 않는다."""
    for name, value in macros.items():
        text = text.replace("{" + name + "}", value)
    return text


def _compile(text, macros, rid, label):
    try:
        return re.compile(_expand(text, macros))
    except re.error as e:
        raise RuleError(f"규칙 {rid}: {label} 정규식 오류 ({e})") from None


def load_rules(path=RULES_PATH):
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise RuleError(f"규칙 파일을 열 수 없음: {path} ({getattr(e, 'strerror', None) or e})") from None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        where = f" 줄 {e.lineno} 열 {e.colno}" if isinstance(e, json.JSONDecodeError) else ""
        raise RuleError(f"규칙 파일 JSON 형식 오류: {path}{where}") from None
    if not isinstance(data, dict):
        raise RuleError("규칙 파일 최상위는 JSON 객체여야 함")
    for key in ("schema", "version", "status", "as_of", "rules"):
        if key not in data:
            raise RuleError(f"규칙 파일에 '{key}' 가 없음")
    macros = data.get("macros") or {}
    if not isinstance(macros, dict) or not all(isinstance(v, str) for v in macros.values()):
        raise RuleError("macros: 문자열 값의 객체여야 함")
    if not isinstance(data["rules"], list):
        raise RuleError("rules: 목록이어야 함")
    rules = []
    for item in data["rules"]:
        rules.append(_load_rule(item, macros))
    negators = _compile(data["negators"], macros, "negators", "negators") if data.get("negators") else None
    markers = (_compile(data["mention_markers"], macros, "mention_markers", "mention_markers")
               if data.get("mention_markers") else None)
    return Rules(path=path, sha256=hashlib.sha256(raw).hexdigest(), version=str(data["version"]),
                 as_of=str(data["as_of"]), status=str(data["status"]), rules=rules, negators=negators,
                 mention_markers=markers, compact_terms=list(data.get("compact_terms") or []))


def _load_rule(item, macros):
    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
        raise RuleError("규칙에 id 가 없음")
    rid = item["id"]
    for key in ("category", "severity", "reason", "suggest"):
        if not isinstance(item.get(key), str) or not item[key]:
            raise RuleError(f"규칙 {rid}: '{key}' 가 없음")
    rtype = item.get("type", "pattern")
    rule = Rule(id=rid, category=item["category"], severity=item["severity"], type=rtype,
                negatable=bool(item.get("negatable", True)), reason=item["reason"], suggest=item["suggest"],
                scope=item.get("scope"), applies_to=tuple(item.get("applies_to") or ("reel", "caption")),
                examples=item.get("examples") or {})
    if rtype == "pattern":
        if not isinstance(item.get("pattern"), str):
            raise RuleError(f"규칙 {rid}: 'pattern' 이 없음")
        rule.regex = _compile(item["pattern"], macros, rid, "pattern")
        rule.excepts = [_compile(x, macros, rid, "except") for x in item.get("except") or []]
    else:
        for key in ("when", "when_scene", "must_have"):
            if isinstance(item.get(key), str):
                setattr(rule, key, _compile(item[key], macros, rid, key))
        if rule.must_have is None:
            raise RuleError(f"규칙 {rid}: 'must_have' 가 없음")
    return rule


# ---------------------------------------------------------------- 글 모델

def normalize(text):
    """NFKC, 폭 없는 글자 제거, <g></g><s></s> 서식 제거."""
    text = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)
    return _MARKUP_RE.sub("", text)


@dataclass
class Doc:
    """점검 대상 글. text 는 필드를 이어 붙인 글이고 spans 는 필드마다 (시작, 끝, 위치, 장면 번호)."""
    kind: str                 # "reel" | "caption"
    text: str = ""
    spans: list = field(default_factory=list)
    starts: list = field(default_factory=list)

    def add(self, where, scene, field_text, sep):
        field_text = normalize(field_text)
        if not field_text.strip():
            return
        if self.text:
            self.text += sep
        start = len(self.text)
        self.text += field_text
        self.spans.append((start, len(self.text), where, scene, field_text))
        self.starts.append(start)

    def locate(self, pos):
        """pos 가 든 필드 (위치, 장면, 필드 글). 필드 사이 빈틈이면 다음 필드."""
        i = bisect_right(self.starts, pos) - 1
        if i < 0:
            i = 0
        _, end, where, scene, text = self.spans[i]
        if pos >= end and i + 1 < len(self.spans):
            _, _, where, scene, text = self.spans[i + 1]
        return where, scene, text


def reel_doc(spec):
    """원고 문서: 한 장면의 필드는 줄바꿈 하나로, 장면 사이와 basis 앞은 빈 줄로 잇는다."""
    doc = Doc("reel")
    for n, sc in enumerate(spec.get("scenes") or [], 1):
        first = True
        for where, value in [(f"scene {n} top", sc.get("top", ""))] + [
                (f"scene {n} line {m}", v) for m, v in enumerate(sc.get("lines") or [], 1)]:
            if not isinstance(value, str) or not normalize(value).strip():
                continue
            doc.add(where, n, value, "\n\n" if first else "\n")
            first = False
    if isinstance(spec.get("basis"), str):
        doc.add("basis", None, spec["basis"], "\n\n")
    return doc


def caption_doc(text):
    """게시글 문서: 비어 있지 않은 줄마다 한 필드(위치 caption line N). 해시태그 줄은 # 토큰마다 한 필드."""
    doc = Doc("caption")
    tag_no = 0
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        tokens = line.split()
        if all(_HASHTAG_TOKEN_RE.match(t) for t in tokens):
            for tok in tokens:
                tag_no += 1
                doc.add(f"hashtag #{tag_no}", None, tok, "\n\n")
        else:
            doc.add(f"caption line {n}", None, line, "\n\n")
    return doc


# ---------------------------------------------------------------- 점검

def _finding(rule, doc, m):
    where, _scene, line = doc.locate(m.start())
    return {"rule": [rule.id], "category": rule.category, "severity": rule.severity, "kind": "pattern",
            "doc": doc.kind, "where": where, "text": re.sub(r"\s*\n\s*", " ", m.group(0)), "line": line,
            "reason": rule.reason, "suggest": rule.suggest}


def scan(doc, rules):
    """(findings, suppressed). 이번 단계는 pattern 규칙만 평가한다."""
    findings, suppressed = [], []
    for rule in rules.rules:
        if rule.type != "pattern" or doc.kind not in rule.applies_to:
            continue
        for m in rule.regex.finditer(doc.text):
            if not m.group(0).strip():
                continue
            findings.append((m.start(), _finding(rule, doc, m)))
    findings.sort(key=lambda p: p[0])
    return [f for _, f in findings], suppressed


# ---------------------------------------------------------------- 결과

def headline(n, rules):
    stat = "초안" if "초안" in rules.status else rules.status
    tail = f"규칙 v{rules.version}({stat}) · 기준일 {rules.as_of}"
    if n > 0:
        return f"위험 표현 {n}건 발견 · {tail}"
    return f"패턴상 발견 없음 — 사람 검수 필요 · {tail}"


@dataclass
class Result:
    rules: Rules
    findings: list
    suppressed: list

    @property
    def counts(self):
        return {
            "수정 필요": sum(1 for f in self.findings if f["severity"] == "수정 필요"),
            "확인 필요": sum(1 for f in self.findings if f["severity"] == "확인 필요"),
            "위험 표현": sum(1 for f in self.findings if f["kind"] in ("pattern", "compact")),
            "예외 제외": len(self.suppressed),
        }

    @property
    def headline(self):
        return headline(self.counts["위험 표현"], self.rules)

    @property
    def counts_line(self):
        c = self.counts
        return f"수정 필요 {c['수정 필요']}건 · 확인 필요 {c['확인 필요']}건 · 예외 처리로 제외 {c['예외 제외']}건"

    def to_json(self):
        r = self.rules
        try:
            shown = str(r.path.resolve().relative_to(constants.REPO_ROOT))
        except ValueError:
            shown = str(r.path)
        return {"schema": SCHEMA,
                "rules": {"path": shown, "sha256": r.sha256, "version": r.version, "as_of": r.as_of,
                          "status": r.status},
                "headline": self.headline, "counts_line": self.counts_line, "counts": self.counts,
                "findings": self.findings, "suppressed": self.suppressed, "limits": LIMITS}


def run(spec, caption_text, rules, *, check_json=None, caption_warnings=None):
    """원고와 게시글을 점검해 Result 를 돌려준다. check_json·caption_warnings 의 확인 필요 옮기기는 다음 단계에서 붙는다."""
    findings, suppressed = [], []
    docs = [reel_doc(spec)]
    if caption_text is not None:
        docs.append(caption_doc(caption_text))
    for doc in docs:
        f, s = scan(doc, rules)
        findings.extend(f)
        suppressed.extend(s)
    return Result(rules=rules, findings=findings, suppressed=suppressed)
