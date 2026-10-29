"""수치 등록부 로더와 검증 (표준 라이브러리만 사용).

등록부는 `tools/data/figures.json` (커밋되는 데이터 파일, schema 1) 이다. 항목 필드 이름은 원고가 id 로
참조하므로 바꾸지 않는다 (D-01). 값은 Decimal 로 읽히는 문자열이며 돈은 원, 비율은 퍼센트 단위다.
확인 상태 `확인` 은 사람이 확인일과 확인자를 적었을 때만 허용한다 (D-02). Claude 나 AI 이름은 확인자가 될 수 없다.
"""
import difflib
import json
import os
import re
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .constants import TOOLS_DIR

REGISTRY_PATH = TOOLS_DIR / "data" / "figures.json"

SCHEMA = 1
KINDS = ("law", "stat", "market", "constant")
UNITS = ("%", "원", "세", "년", "개월", "")
LEGAL_STATUSES = ("시행", "발의", "폐지")
VERIFIED_STATES = ("미확인", "확인")
ENTRY_KEYS = (
    "label", "kind", "value", "unit", "includes_local", "source", "candidate_sources", "as_of",
    "valid_until", "found_on", "checked_on", "checked_by", "legal_status", "verified", "notes",
)
SOURCE_KEYS = ("name", "url", "locator")
UNSOURCED_KEYS = ("text", "seen_in", "reason")

ID_RE = re.compile(r"^[a-z0-9_]+$")
AS_OF_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PROPOSAL_RE = re.compile(r"발의|개정안|정부안")
# Claude, AI, assistant, bot 등 사람이 아닌 확인자 이름 (대소문자 무시)
AI_NAME_RE = re.compile(
    r"claude|anthropic|클로드|어시스턴트|(?<![a-z])(ai|assistant|bot|llm|gpt)(?![a-z])", re.IGNORECASE)


class RegistryError(ValueError):
    """등록부 파일을 읽을 수 없거나 항목이 규칙에 어긋날 때. 메시지는 한국어이며 id 와 필드를 밝힌다."""


def is_ai_name(name):
    return bool(AI_NAME_RE.search(name))


def _valid_date(text):
    if not isinstance(text, str) or not DATE_RE.match(text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def parse_value(raw, where):
    """등록부·입력 값 문자열을 유한한 Decimal 로. float 은 받지 않는다."""
    if not isinstance(raw, str) or not raw.strip():
        raise RegistryError(f"{where}: 값은 비어 있지 않은 문자열이어야 함")
    try:
        d = Decimal(raw.strip())
    except InvalidOperation:
        raise RegistryError(f"{where}: 숫자로 읽을 수 없는 값 {raw!r}") from None
    if not d.is_finite():
        raise RegistryError(f"{where}: 유한한 숫자여야 함 {raw!r}")
    return d


def validate_entry(fid, entry):
    if not isinstance(fid, str) or not ID_RE.match(fid):
        raise RegistryError(f"id {fid!r}: 영문 소문자·숫자·밑줄만 쓸 수 있음 (^[a-z0-9_]+$)")
    if not isinstance(entry, dict):
        raise RegistryError(f"{fid}: 항목은 객체여야 함")
    unknown = [k for k in entry if k not in ENTRY_KEYS]
    if unknown:
        raise RegistryError(f"{fid}: 알 수 없는 필드 {', '.join(map(str, unknown))}")
    missing = [k for k in ENTRY_KEYS if k not in entry]
    if missing:
        raise RegistryError(f"{fid}: 빠진 필드 {', '.join(missing)}")
    if not isinstance(entry["label"], str) or not entry["label"].strip():
        raise RegistryError(f"{fid}.label: 비어 있지 않은 문자열이어야 함")
    if entry["kind"] not in KINDS:
        raise RegistryError(f"{fid}.kind: {entry['kind']!r} — 허용: {', '.join(KINDS)}")
    parse_value(entry["value"], f"{fid}.value")
    if entry["unit"] not in UNITS:
        raise RegistryError(f"{fid}.unit: {entry['unit']!r} — 허용: {', '.join(repr(u) for u in UNITS)}")
    if not isinstance(entry["includes_local"], bool):
        raise RegistryError(f"{fid}.includes_local: true/false 여야 함")
    src = entry["source"]
    if not isinstance(src, dict):
        raise RegistryError(f"{fid}.source: 객체여야 함")
    bad = [k for k in src if k not in SOURCE_KEYS]
    if bad or any(k not in src for k in SOURCE_KEYS):
        raise RegistryError(f"{fid}.source: 필드는 {', '.join(SOURCE_KEYS)} 이어야 함")
    if not isinstance(src["name"], str) or not src["name"].strip():
        raise RegistryError(f"{fid}.source.name: 비어 있지 않은 문자열이어야 함")
    for k in ("url", "locator"):
        if src[k] is not None and not isinstance(src[k], str):
            raise RegistryError(f"{fid}.source.{k}: 문자열 또는 null 이어야 함")
    cands = entry["candidate_sources"]
    if not isinstance(cands, list) or not all(isinstance(c, str) for c in cands):
        raise RegistryError(f"{fid}.candidate_sources: 문자열 목록이어야 함")
    if entry["as_of"] is not None and (not isinstance(entry["as_of"], str) or not AS_OF_RE.match(entry["as_of"])):
        raise RegistryError(f"{fid}.as_of: YYYY, YYYY-MM, YYYY-MM-DD 또는 null 이어야 함 ({entry['as_of']!r})")
    if not _valid_date(entry["found_on"]):
        raise RegistryError(f"{fid}.found_on: YYYY-MM-DD 날짜여야 함 ({entry['found_on']!r})")
    for k in ("valid_until", "checked_on"):
        if entry[k] is not None and not _valid_date(entry[k]):
            raise RegistryError(f"{fid}.{k}: YYYY-MM-DD 날짜 또는 null 이어야 함 ({entry[k]!r})")
    if entry["checked_by"] is not None and not isinstance(entry["checked_by"], str):
        raise RegistryError(f"{fid}.checked_by: 문자열 또는 null 이어야 함")
    if entry["legal_status"] not in LEGAL_STATUSES:
        raise RegistryError(f"{fid}.legal_status: {entry['legal_status']!r} — 허용: {', '.join(LEGAL_STATUSES)}")
    if entry["verified"] not in VERIFIED_STATES:
        raise RegistryError(f"{fid}.verified: {entry['verified']!r} — 허용: {', '.join(VERIFIED_STATES)}")
    if not isinstance(entry["notes"], str):
        raise RegistryError(f"{fid}.notes: 문자열이어야 함")
    if entry["verified"] == "확인":
        by = entry["checked_by"]
        if not entry["checked_on"] or not by or not by.strip():
            raise RegistryError(f"{fid}: 확인 상태에는 checked_on 과 checked_by 가 필요함")
        if is_ai_name(by):
            raise RegistryError(f"{fid}.checked_by: {by!r} — Claude/AI 는 확인자가 될 수 없음 (사람이 확인해야 함)")
    if entry["legal_status"] == "발의" and not PROPOSAL_RE.search(src["name"]):
        raise RegistryError(f"{fid}: 발의 상태는 source.name 에 발의/개정안/정부안 표기가 필요함")


def validate_registry(data):
    if not isinstance(data, dict):
        raise RegistryError("등록부 최상위는 JSON 객체여야 함")
    unknown = [k for k in data if k not in ("schema", "figures", "unsourced")]
    if unknown:
        raise RegistryError(f"등록부: 알 수 없는 최상위 키 {', '.join(map(str, unknown))}")
    if isinstance(data.get("schema"), bool) or data.get("schema") != SCHEMA:
        raise RegistryError(f"등록부: schema 는 {SCHEMA} 이어야 함 (현재 {data.get('schema')!r})")
    figs = data.get("figures")
    if not isinstance(figs, dict):
        raise RegistryError("등록부: figures 는 객체여야 함")
    for fid, entry in figs.items():
        validate_entry(fid, entry)
    unsourced = data.get("unsourced", [])
    if not isinstance(unsourced, list):
        raise RegistryError("등록부: unsourced 는 목록이어야 함")
    for n, item in enumerate(unsourced, 1):
        if (not isinstance(item, dict) or set(item) != set(UNSOURCED_KEYS)
                or not all(isinstance(item[k], str) for k in UNSOURCED_KEYS)):
            raise RegistryError(f"unsourced[{n}]: {', '.join(UNSOURCED_KEYS)} 문자열 세 개를 가진 객체여야 함")


def load_registry(path=REGISTRY_PATH):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        reason = getattr(e, "strerror", None) or str(e)
        raise RegistryError(f"등록부 파일을 열 수 없음: {path} ({reason})") from e
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RegistryError(f"등록부 JSON 형식 오류: {path} 줄 {e.lineno} 열 {e.colno}") from e
    try:
        validate_registry(data)
    except RegistryError as e:
        raise RegistryError(f"{e} ({path})") from e
    return data


def get_figure(registry, fid):
    figs = registry["figures"]
    if fid in figs:
        return figs[fid]
    near = difflib.get_close_matches(str(fid), list(figs), n=3, cutoff=0.6)
    hint = f" — 비슷한 id: {', '.join(near)}" if near else ""
    raise RegistryError(f"등록부에 없는 id: {fid}{hint}")


def figure_value(registry, fid):
    entry = get_figure(registry, fid)
    return parse_value(entry["value"], f"{fid}.value")
