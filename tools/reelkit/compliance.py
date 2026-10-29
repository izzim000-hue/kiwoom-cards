"""금소법 표현 점검기: 규칙 데이터 파일(tools/data/compliance_rules.json)을 읽어 원고·근거·게시글·해시태그를 훑는다 (표준 라이브러리만 사용).

점검 규칙은 코드가 아니라 데이터 파일에 있다. 규칙을 고치거나 더하면 코드 변경 없이 다음 점검부터 바뀐다 (COMP-05).
결과 머리말은 두 가지뿐이다: `위험 표현 n건 발견 · ...` 또는 `패턴상 발견 없음 — 사람 검수 필요 · ...`.
이 점검은 키워드·패턴 방식이라 암시적 표현은 잡지 못한다. 대체 표현은 제안만 하고 원고는 고치지 않는다 (D-10).
규칙은 준법 검토 전 초안이며 조문 번호를 인용하지 않는다 (D-05).

점검 방식
- 글 모델: 필드(장면 top·줄, basis, 게시글 줄, 해시태그)를 NFKC 로 바꾸고 폭 없는 글자·서식 태그를 지운 뒤 한 글로 잇는다.
  한 장면의 필드는 줄바꿈 하나로, 장면 사이와 basis 앞은 빈 줄로 잇는다. 위치는 매치가 시작한 필드로 정한다.
- 부정·인용 예외: 매치 바로 뒤 글(최대 22자, 줄바꿈·문장 끝·쉼표·'지만' 류에서 끊음)이 부정 표현으로 *시작*하거나
  `라는 말` 같은 언급 표지로 시작하면 발견이 아니라 `suppressed` 에 남긴다. negators·mention_markers 는 창의 맨 앞에
  맞춰(match) 보므로, 부정은 매치한 서술어에 붙어 있어야 한다 (예: '보장하지 않', '보장 상품은 없'). 장면의 줄은 따로 읽히는
  문장이라 다음 줄의 '놓치지 마세요' 같은 부정은 앞 줄의 주장을 덮지 않는다 (CR-01).
- except 규칙은 따로 넓은 창(문장 끝·빈 줄·'지만' 류에서 끊음)으로 매치가 든 문장을 본다.
- 쪼갠 표현: 발견도 제외도 없는 필드에서 공백을 모두 지운 글로 compact_terms 를 찾는다 (규칙 id X-compact).
  표현의 첫 글자가 원래 글에서 낱말 첫머리일 때만 센다 ('근무 조건' 의 '무조건' 제외).
- 겹친 매치는 하나로 합치고 더 구체적인 분류를 남긴다.
- 확인 필요: requires/basis_required 규칙과 check.json·게시글 경고 옮기기(lift)로 만든다. 수치를 다시 판정하지 않는다 (D-07).
"""
import hashlib
import json
import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import NamedTuple

from . import constants

RULES_PATH = constants.TOOLS_DIR / "data" / "compliance_rules.json"
SCHEMA = 1
SEVERITIES = ("수정 필요", "확인 필요")
RULE_TYPES = ("pattern", "requires", "basis_required")
DOC_KINDS = ("reel", "caption")
LIMITS = "한계: 키워드·패턴 방식이라 암시적 표현은 잡지 못합니다 — 사람 검수 필요 (AI 의미 점검은 v2)"
WINDOW = 22

TOP_KEYS = {"schema", "version", "status", "as_of", "macros", "negators", "mention_markers", "compact_terms", "rules"}
RULE_KEYS = {"id", "category", "severity", "type", "pattern", "when", "when_scene", "must_have", "negatable", "except",
             "applies_to", "scope", "reason", "suggest", "examples"}
SPECIFIC_FIRST = "단정·보장"   # 다른 분류가 같은 자리에 겹치면 이 분류보다 구체적인 쪽을 남긴다

_ZERO_WIDTH_CHARS = "​‌‍⁠­﻿"
_ZERO_WIDTH = dict.fromkeys(map(ord, _ZERO_WIDTH_CHARS))
_MARKUP_RE = re.compile(r"</?[gs]>")
_HASHTAG_TOKEN_RE = re.compile(r"^#\S+$")
_STATUTE_RE = re.compile(r"제\s*\d+\s*조")
_NESTED_QUANTIFIER_RE = re.compile(r"(?<!\\)[+*]\)[+*{]")
# 부정 창: 장면의 줄 하나를 넘지 않는다 (줄바꿈 하나에서도 끊음, CR-01)
_CUT_RE = re.compile(r"[.!?;,]|\n|하지만|지만|그러나|다만|그런데")
# except 창: 문장 안(줄바꿈 하나로 이어 쓴 줄 포함)을 본다
_EXCEPT_CUT_RE = re.compile(r"[.!?;]|\n\n|하지만|지만|그러나|다만|그런데")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

COMPACT_REASON = "공백·숨은 글자로 쪼갠 금지 표현으로 읽힘"
COMPACT_SUGGEST = "표현을 쓰지 말고, 쓰려면 조건과 한계를 함께 밝히세요"


class RuleError(ValueError):
    """규칙 파일이 규칙에 어긋날 때. 메시지는 한국어이며 규칙 id 를 밝힌다."""


# ---------------------------------------------------------------- 글 모델

def normalize(text):
    """NFKC, 폭 없는 글자 제거, <g></g><s></s> 서식 제거."""
    text = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)
    return _MARKUP_RE.sub("", text)


class Span(NamedTuple):
    start: int
    end: int
    where: str
    scene: object    # int | None
    text: str
    hidden: bool     # 원문에 폭 없는 글자가 있었음


@dataclass
class Doc:
    """점검 대상 글. text 는 필드를 이어 붙인 글이고 spans 는 필드마다의 위치 정보."""
    kind: str                 # "reel" | "caption"
    text: str = ""
    spans: list = field(default_factory=list)
    starts: list = field(default_factory=list)

    def add(self, where, scene, raw, sep):
        norm = normalize(raw)
        if not norm.strip():
            return
        if self.text:
            self.text += sep
        start = len(self.text)
        self.text += norm
        hidden = any(c in raw for c in _ZERO_WIDTH_CHARS)
        self.spans.append(Span(start, len(self.text), where, scene, norm, hidden))
        self.starts.append(start)

    def span_at(self, pos):
        """pos 가 든 필드. 필드 사이 빈틈이면 다음 필드."""
        i = max(bisect_right(self.starts, pos) - 1, 0)
        span = self.spans[i]
        if pos >= span.end and i + 1 < len(self.spans):
            span = self.spans[i + 1]
        return span


def reel_doc(spec):
    """원고 문서: 한 장면의 필드는 줄바꿈 하나로, 장면 사이와 basis 앞은 빈 줄로 잇는다."""
    doc = Doc("reel")
    for n, sc in enumerate(spec.get("scenes") or [], 1):
        first = True
        fields = [(f"scene {n} top", sc.get("top", ""))] + [
            (f"scene {n} line {m}", v) for m, v in enumerate(sc.get("lines") or [], 1)]
        for where, value in fields:
            if not isinstance(value, str) or not normalize(value).strip():
                continue
            doc.add(where, n, value, "\n\n" if first else "\n")
            first = False
    if isinstance(spec.get("basis"), str):
        doc.add("basis", None, spec["basis"], "\n\n")
    return doc


def caption_doc(text):
    """게시글 문서: 비어 있지 않은 줄마다 한 필드(caption line N). 해시태그 줄은 # 토큰마다 한 필드(hashtag #K)."""
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
    applies_to: tuple = DOC_KINDS
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
    """정규식을 컴파일한다. 잘못된 정규식, 빈 글에 맞는 정규식, 중첩된 무한 반복은 거부한다 (T-03-02)."""
    if not isinstance(text, str):
        raise RuleError(f"규칙 {rid}: {label} 는 문자열이어야 함")
    source = _expand(text, macros)
    try:
        rx = re.compile(source)
    except re.error as e:
        raise RuleError(f"규칙 {rid}: {label} 정규식 오류 ({e})") from None
    if _NESTED_QUANTIFIER_RE.search(source):
        raise RuleError(f"규칙 {rid}: {label} 에 중첩된 무한 반복이 있어 거부함 (처리가 끝나지 않을 수 있음)")
    if rx.search(""):
        raise RuleError(f"규칙 {rid}: {label} 이(가) 빈 글에도 맞아 거부함")
    return rx


def _check_strings(value, rid):
    """어떤 글에도 '통과' 나 조문 번호 형태를 쓰지 않는다 (D-05, D-08)."""
    if isinstance(value, str):
        if "통과" in value:
            raise RuleError(f"규칙 {rid}: '통과' 라는 말은 쓸 수 없음")
        if _STATUTE_RE.search(value):
            raise RuleError(f"규칙 {rid}: 조문 번호 형태는 쓸 수 없음 (D-05)")
    elif isinstance(value, dict):
        for k, v in value.items():
            _check_strings(k, rid)
            _check_strings(v, rid)
    elif isinstance(value, list):
        for v in value:
            _check_strings(v, rid)


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
    unknown = sorted(set(data) - TOP_KEYS)
    if unknown:
        raise RuleError(f"규칙 파일에 알 수 없는 키: {', '.join(unknown)}")
    for key in ("schema", "version", "status", "as_of", "rules"):
        if key not in data:
            raise RuleError(f"규칙 파일에 '{key}' 가 없음")
    if data["schema"] != SCHEMA:
        raise RuleError(f"규칙 파일 schema {data['schema']!r} — {SCHEMA} 만 지원함")
    for key in ("version", "status", "as_of"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise RuleError(f"규칙 파일 '{key}': 비어 있지 않은 문자열이어야 함")
    if not _DATE_RE.fullmatch(data["as_of"]):
        raise RuleError(f"규칙 파일 as_of: YYYY-MM-DD 형식이어야 함: {data['as_of']!r}")
    try:
        date.fromisoformat(data["as_of"])
    except ValueError:
        raise RuleError(f"규칙 파일 as_of: 없는 날짜임: {data['as_of']!r}") from None
    macros = data.get("macros") or {}
    if not isinstance(macros, dict) or not all(isinstance(v, str) for v in macros.values()):
        raise RuleError("macros: 문자열 값의 객체여야 함")
    if not isinstance(data["rules"], list):
        raise RuleError("rules: 목록이어야 함")
    terms = data.get("compact_terms") or []
    if not isinstance(terms, list) or not all(isinstance(t, str) and t for t in terms):
        raise RuleError("compact_terms: 비어 있지 않은 문자열 목록이어야 함")
    for key in ("status", "version", "negators", "mention_markers", "macros", "compact_terms"):
        _check_strings(data.get(key), key)
    negators = _compile(data["negators"], macros, "negators", "negators") if data.get("negators") else None
    markers = (_compile(data["mention_markers"], macros, "mention_markers", "mention_markers")
               if data.get("mention_markers") else None)
    rules, seen = [], set()
    for item in data["rules"]:
        rule = _load_rule(item, macros)
        if rule.id in seen:
            raise RuleError(f"규칙 {rule.id}: id 가 겹침")
        seen.add(rule.id)
        rules.append(rule)
    loaded = Rules(path=path, sha256=hashlib.sha256(raw).hexdigest(), version=data["version"],
                   as_of=data["as_of"], status=data["status"], rules=rules, negators=negators,
                   mention_markers=markers, compact_terms=[normalize(t) for t in terms])
    for rule in rules:
        _run_examples(rule, loaded)
    return loaded


def _load_rule(item, macros):
    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
        raise RuleError("규칙에 id 가 없음")
    rid = item["id"]
    unknown = sorted(set(item) - RULE_KEYS)
    if unknown:
        raise RuleError(f"규칙 {rid}: 알 수 없는 키: {', '.join(unknown)}")
    _check_strings(item, rid)
    for key in ("category", "severity", "reason", "suggest"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise RuleError(f"규칙 {rid}: '{key}' 가 없음")
    if item["severity"] not in SEVERITIES:
        raise RuleError(f"규칙 {rid}: severity {item['severity']!r} — {' / '.join(SEVERITIES)} 중 하나여야 함")
    rtype = item.get("type", "pattern")
    if rtype not in RULE_TYPES:
        raise RuleError(f"규칙 {rid}: type {rtype!r} — {' / '.join(RULE_TYPES)} 중 하나여야 함")
    negatable = item.get("negatable", True)
    if not isinstance(negatable, bool):
        raise RuleError(f"규칙 {rid}: negatable 은 true/false 여야 함")
    applies = item.get("applies_to")
    scope = item.get("scope")
    if scope is not None and scope not in DOC_KINDS:
        raise RuleError(f"규칙 {rid}: scope {scope!r} — reel / caption 중 하나여야 함")
    if applies is None:
        applies = [scope] if scope else list(DOC_KINDS)
    if not isinstance(applies, list) or not applies or not all(a in DOC_KINDS for a in applies):
        raise RuleError(f"규칙 {rid}: applies_to 는 reel / caption 의 목록이어야 함")
    examples = item.get("examples") or {}
    if not isinstance(examples, dict) or set(examples) - {"hit", "miss"} or not all(
            isinstance(v, list) and all(isinstance(x, str) for x in v) for v in examples.values()):
        raise RuleError(f"규칙 {rid}: examples 는 {{hit: [글...], miss: [글...]}} 형식이어야 함")
    rule = Rule(id=rid, category=item["category"], severity=item["severity"], type=rtype, negatable=negatable,
                reason=item["reason"], suggest=item["suggest"], scope=scope, applies_to=tuple(applies),
                examples=examples)
    if rtype == "pattern":
        rule.regex = _compile(item.get("pattern"), macros, rid, "pattern")
        excepts = item.get("except") or []
        if not isinstance(excepts, list):
            raise RuleError(f"규칙 {rid}: except 는 정규식 목록이어야 함")
        rule.excepts = [_compile(x, macros, rid, "except") for x in excepts]
        return rule
    for key in ("when", "when_scene", "must_have"):
        if item.get(key) is not None:
            setattr(rule, key, _compile(item[key], macros, rid, key))
    if rule.must_have is None:
        raise RuleError(f"규칙 {rid}: 'must_have' 가 없음")
    if rtype == "requires" and rule.when is None and rule.when_scene is None:
        raise RuleError(f"규칙 {rid}: 'when' 또는 'when_scene' 이 없음")
    if rtype == "basis_required" and rule.when is None:
        raise RuleError(f"규칙 {rid}: 'when' 이 없음")
    return rule


def _run_examples(rule, loaded):
    """규칙의 hit/miss 예시를 한 줄짜리 원고로 이 규칙만 켜고 돌려 본다. 어긋나면 규칙 id 를 밝혀 거부한다."""
    if rule.type != "pattern":
        return
    solo = Rules(path=loaded.path, sha256="", version=loaded.version, as_of=loaded.as_of, status=loaded.status,
                 rules=[rule], negators=loaded.negators, mention_markers=loaded.mention_markers, compact_terms=[])
    for label, expect_hit in (("hit", True), ("miss", False)):
        for example in rule.examples.get(label) or []:
            if "reel" in rule.applies_to:
                doc = reel_doc({"scenes": [{"top": "", "lines": example.split("\n")}]})
            else:
                doc = caption_doc(example)
            findings, _sup = scan(doc, solo)
            if bool(findings) != expect_hit:
                state = "걸리지 않음" if expect_hit else "걸림"
                raise RuleError(f"규칙 {rule.id}: {label} 예시가 {state}: {example!r}")


# ---------------------------------------------------------------- 점검

class _Hit(NamedTuple):
    start: int
    end: int
    rule: Rule


def _window(text, end, cut=_CUT_RE):
    """매치 뒤 최대 22자. 부정 창은 줄바꿈·문장 끝·쉼표·'지만' 류에서 끊는다 (장면의 줄 하나를 넘지 않음)."""
    after = text[end:end + WINDOW]
    m = cut.search(after)
    return after[:m.start()] if m else after


def _clause_start(text, pos):
    """pos 가 든 문장의 시작. 앞 문장 끝 글자 바로 뒤(또는 빈 줄 뒤, 글 처음)이며 첫 글자를 자르지 않는다."""
    start = 0
    for ch in ".!?;":
        start = max(start, text.rfind(ch, 0, pos) + 1)
    blank = text.rfind("\n\n", 0, pos)
    if blank >= 0:
        start = max(start, blank + 2)
    return start


def _negated(rules, window):
    """부정·언급 표지가 창의 맨 앞에서 시작하면 그 이름, 아니면 None."""
    if rules.negators is not None and rules.negators.match(window):
        return "negator"
    if rules.mention_markers is not None and rules.mention_markers.match(window):
        return "mention"
    return None


def _suppressed_by(rule, rules, text, start, end, window):
    """부정(negator)·언급(mention)·예외(except) 중 걸린 이름, 없으면 None."""
    if rule.negatable:
        by = _negated(rules, window)
        if by:
            return by
    if rule.excepts:
        base = _clause_start(text, start)
        clause = text[base:end + len(_window(text, end, _EXCEPT_CUT_RE))]
        for rx in rule.excepts:
            for m in rx.finditer(clause):
                if m.start() < end - base and m.end() > start - base:
                    return "except"
    return None


def _one_line(text):
    return re.sub(r"\s*\n\s*", " ", text)


def _merge(doc, group):
    """겹친 매치 묶음 하나를 발견 하나로. 더 구체적인 분류와 더 높은 등급을 남긴다."""
    group.sort(key=lambda h: (h.start, h.end))
    start = group[0].start
    end = max(h.end for h in group)
    order = {}
    for h in group:
        order.setdefault(h.rule.id, h.rule)
    rules = list(order.values())
    primary = min(rules, key=lambda r: (r.category == SPECIFIC_FIRST, r.severity != "수정 필요"))
    severity = "수정 필요" if any(r.severity == "수정 필요" for r in rules) else "확인 필요"
    span = doc.span_at(start)
    reasons, suggests = [primary.reason], [primary.suggest]
    for r in rules:
        if r.reason not in reasons:
            reasons.append(r.reason)
        if r.suggest not in suggests:
            suggests.append(r.suggest)
    rule_ids = [r.id for r in rules]
    if span.hidden:
        rule_ids.append("X-compact")
    return start, {"rule": rule_ids, "category": primary.category, "severity": severity, "kind": "pattern",
                   "doc": doc.kind, "where": span.where, "text": _one_line(doc.text[start:end]), "line": span.text,
                   "reason": " / ".join(reasons), "suggest": " / ".join(suggests)}


def _scene_texts(doc):
    """장면 번호 -> [(필드 위치, 필드 글)] (basis 와 장면 없는 필드 제외)."""
    out = {}
    for span in doc.spans:
        if span.scene is not None:
            out.setdefault(span.scene, []).append(span)
    return out


def _first_scene_trigger(doc, rx):
    """장면 하나 안(필드를 공백으로 이은 글)에서 rx 가 처음 맞는 곳: (필드, 매치 글) 또는 None."""
    scenes = _scene_texts(doc)
    groups = [scenes[n] for n in sorted(scenes)] if scenes else [list(doc.spans)]
    for spans in groups:
        joined, offsets = "", []
        for sp in spans:
            joined += (" " if joined else "")
            offsets.append((len(joined), sp))
            joined += sp.text
        m = rx.search(joined)
        if m:
            owner = spans[0]
            for off, sp in offsets:
                if off <= m.start():
                    owner = sp
            return owner, m.group(0)
    return None


def _structural(doc, rule):
    """requires / basis_required 규칙 하나를 평가해 발견 하나 또는 None."""
    base = {"rule": [rule.id], "category": rule.category, "severity": rule.severity, "kind": rule.type,
            "doc": doc.kind, "reason": rule.reason, "suggest": rule.suggest}
    if rule.type == "requires":
        owner = trigger = None
        if rule.when is not None:
            m = rule.when.search(doc.text)
            if m:
                owner, trigger = doc.span_at(m.start()), m.group(0)
        if owner is None and rule.when_scene is not None:
            hit = _first_scene_trigger(doc, rule.when_scene)
            if hit:
                owner, trigger = hit
        if owner is None or rule.must_have.search(doc.text):
            return None
        return {**base, "where": owner.where, "text": _one_line(trigger), "line": owner.text}
    if doc.kind != "reel":
        return None
    body = "\n".join(sp.text for sp in doc.spans if sp.where != "basis")
    basis = next((sp for sp in doc.spans if sp.where == "basis"), None)
    m = rule.when.search(body)
    if not m or rule.must_have.search(basis.text if basis else ""):
        return None
    where = basis.where if basis else doc.span_at(doc.text.find(m.group(0))).where
    return {**base, "where": where, "text": _one_line(m.group(0)), "line": basis.text if basis else ""}


def _compact_matches(text, terms):
    """공백을 지운 글에서 찾은 쪼갠 표현 [(원래 글의 시작, 끝, 표현)]. 표현의 첫 글자가 원래 글에서 낱말 첫머리일 때만 센다
    (CR-02: '근무 조건'·'채무조건' 의 '무조건' 은 낱말 중간이라 제외)."""
    keep = [i for i, ch in enumerate(text) if not ch.isspace()]
    squeezed = "".join(text[i] for i in keep)
    out = []
    for term in terms:
        pos = squeezed.find(term) if term else -1
        while pos >= 0:
            o_start, o_end = keep[pos], keep[pos + len(term) - 1] + 1
            if o_start == 0 or not text[o_start - 1].isalnum():
                out.append((o_start, o_end, term))
            pos = squeezed.find(term, pos + 1)
    return out


def scan(doc, rules):
    """(findings, suppressed). 패턴 규칙 -> 쪼갠 표현 -> 근거 누락 규칙 순서이고 글 속 위치 순으로 돌려준다."""
    hits, suppressed = [], []
    for rule in rules.rules:
        if rule.type != "pattern" or doc.kind not in rule.applies_to:
            continue
        for m in rule.regex.finditer(doc.text):
            start, end = m.span()
            if not doc.text[start:end].strip():
                continue
            window = _window(doc.text, end)
            by = _suppressed_by(rule, rules, doc.text, start, end, window)
            if by:
                span = doc.span_at(start)
                suppressed.append({"rule": [rule.id], "where": span.where, "text": _one_line(m.group(0)),
                                   "by": by, "window": _one_line(window), "line": span.text})
                continue
            hits.append(_Hit(start, end, rule))
    # 겹친 매치 합치기
    hits.sort(key=lambda h: (h.start, h.end))
    groups, current, cur_end = [], [], -1
    for h in hits:
        if current and h.start < cur_end:
            current.append(h)
            cur_end = max(cur_end, h.end)
        else:
            if current:
                groups.append(current)
            current, cur_end = [h], h.end
    if current:
        groups.append(current)
    found = [_merge(doc, g) for g in groups]
    # 쪼갠 표현: 발견도 제외도 없는 필드만
    touched = {doc.span_at(pos).where for pos, _ in found} | {s["where"] for s in suppressed}
    for span in doc.spans:
        if span.where in touched or not rules.compact_terms:
            continue
        for _o_start, _o_end, term in _compact_matches(span.text, rules.compact_terms):
            found.append((span.start, {
                "rule": ["X-compact"], "category": SPECIFIC_FIRST, "severity": "수정 필요", "kind": "compact",
                "doc": doc.kind, "where": span.where, "text": term, "line": span.text,
                "reason": COMPACT_REASON, "suggest": COMPACT_SUGGEST}))
    found.sort(key=lambda p: p[0])
    findings = [f for _, f in found]
    for rule in rules.rules:
        if rule.type != "pattern" and doc.kind in rule.applies_to:
            f = _structural(doc, rule)
            if f:
                findings.append(f)
    return findings, suppressed


# ---------------------------------------------------------------- 확인 필요 옮기기 (D-07)

def lift(check_json=None, caption_warnings=None):
    """check.json 의 needs_check·assumptions·warnings 와 게시글 경고를 확인 필요 항목으로 그대로 옮긴다. 새 판정은 없다."""
    out = []

    def entry(rule, category, where, text, reason, line=None):
        out.append({"rule": [rule], "category": category, "severity": "확인 필요", "kind": "lift", "doc": "check",
                    "where": where, "text": text, "line": line if line is not None else text, "reason": reason,
                    "suggest": "사람이 원본 근거를 다시 확인하세요"})

    check_json = check_json or {}
    for item in check_json.get("needs_check") or []:
        ids = ", ".join(item.get("ids") or [])
        entry("CHK-NEEDS", "근거 누락", item.get("where", ""), item.get("text", ""),
              f"등록부에서 확인되지 않은 수치를 쓴 줄 [{ids}] (check.json)")
    for item in check_json.get("assumptions") or []:
        ids = ", ".join(item.get("inputs") or [])
        entry("CHK-ASSUME", "근거 누락", item.get("where", ""), item.get("text", ""),
              f"가정(inputs) 수치를 쓴 줄 [{ids}] — 화면에 예시·가정 표기 확인 (check.json)")
    for item in check_json.get("warnings") or []:
        entry("CHK-WARN", "점검 경고", item.get("where", ""), item.get("text", ""),
              f"{item.get('kind', '')} ({item.get('detail', '')}) (check.json 경고)")
    for text in caption_warnings or []:
        entry("CHK-CAPTION", "점검 경고", "caption", text, "게시글 조립 경고")
    return out


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
    """원고와 게시글을 점검해 Result 를 돌려준다. 원고·게시글 문서의 발견, 그다음 check.json·게시글 경고 옮기기 순서."""
    findings, suppressed = [], []
    docs = [reel_doc(spec)]
    if caption_text is not None:
        docs.append(caption_doc(caption_text))
    for doc in docs:
        f, s = scan(doc, rules)
        findings.extend(f)
        suppressed.extend(s)
    findings.extend(lift(check_json, caption_warnings))
    return Result(rules=rules, findings=findings, suppressed=suppressed)
