"""게시글 문구(caption.txt) 조립·점검 (표준 라이브러리만 사용, D-11 ~ D-13).

Claude 가 쓰는 `caption.src.json` 은 `{hook, summary[3], hashtags[]}` 뿐이다. 시리즈명·회차·다음 편은 원고의
`series` 한 곳에서만 가져온다 (D-10): 장면 1 top, CTA 장면의 다음 편 줄, 게시글 첫 줄과 다음 편 줄이 같은 서식 함수
(expand.series_top / expand.next_line)를 쓴다. 게시글의 숫자는 원고 장부에 있는 숫자여야 하고 원고에서의 상태(미확인,
발의, 가정)를 그대로 진다 (D-07 정신, WR-01). draft.py caption 은 원고 점검에 오류가 있으면 조립하지 않는다.
면책·CTA 문구는 초안이며 준법 검토 전이다 (config 의 status). 브랜드 해시태그는 비어 있고 만들어 넣지 않는다 (D-12).
"""
import json
import re
from pathlib import Path

from . import constants, numscan
from .check import PROPOSAL_MARK_RE
from .expand import LABEL_MARK_RE, next_line, series_top

CONFIG_PATH = constants.TOOLS_DIR / "data" / "caption_config.json"
HASHTAG_RE = re.compile(r"^#[0-9A-Za-z_가-힣]+$")
SRC_KEYS = ("hook", "summary", "hashtags")
SERIES_KEYS = ("series", "episode", "next")
MIN_TOPIC_TAGS = 3
HARD_MAX_HASHTAGS = 5
_TAG_RE = re.compile(r"</?[gs]>")
_AS_OF_RE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-\d{2})?)?$")


class CaptionError(ValueError):
    """게시글 문구 원본·설정·원고가 규칙에 어긋날 때. 메시지는 한국어이며 위치를 밝힌다."""


def load_config(path=CONFIG_PATH):
    try:
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        raise CaptionError(f"게시글 설정을 열 수 없음: {path} ({getattr(e, 'strerror', None) or e})") from None
    except json.JSONDecodeError as e:
        raise CaptionError(f"게시글 설정 JSON 형식 오류: {path} 줄 {e.lineno} 열 {e.colno}") from None
    if not isinstance(cfg, dict):
        raise CaptionError("게시글 설정 최상위는 JSON 객체여야 함")
    for key in ("status", "disclaimer", "cta"):
        if not isinstance(cfg.get(key), str) or not cfg[key].strip():
            raise CaptionError(f"게시글 설정 {key}: 비어 있지 않은 문자열이어야 함")
    for key in ("max_hashtags", "max_chars", "first_line_warn"):
        v = cfg.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise CaptionError(f"게시글 설정 {key}: 1 이상의 정수여야 함")
    if cfg["max_hashtags"] > HARD_MAX_HASHTAGS:
        raise CaptionError(f"게시글 설정 max_hashtags: {HARD_MAX_HASHTAGS} 를 넘을 수 없음 (D-12)")
    brand = cfg.get("brand_hashtags")
    if not isinstance(brand, list) or not all(isinstance(t, str) and HASHTAG_RE.match(t) for t in brand):
        raise CaptionError("게시글 설정 brand_hashtags: '#태그' 형식 문자열 목록이어야 함")
    return cfg


def _plain(text):
    return _TAG_RE.sub("", text)


def _spec_texts(spec):
    out = []
    for sc in spec["scenes"]:
        out.append(sc["top"])
        out.extend(sc["lines"])
    if isinstance(spec.get("basis"), str):
        out.append(spec["basis"])
    return out


def _check_src(src):
    if not isinstance(src, dict):
        raise CaptionError("게시글 문구 원본 최상위는 JSON 객체여야 함")
    if any(k in src for k in SERIES_KEYS):
        raise CaptionError("시리즈·회차·다음 편은 원고의 series 에서만 가져옴 (D-10)")
    unknown = [k for k in src if k not in SRC_KEYS]
    if unknown:
        raise CaptionError(f"알 수 없는 키: {', '.join(map(str, unknown))} (허용: {', '.join(SRC_KEYS)})")
    missing = [k for k in SRC_KEYS if k not in src]
    if missing:
        raise CaptionError(f"필요한 키가 없음: {', '.join(missing)}")
    summary = src["summary"]
    if not isinstance(summary, list) or len(summary) != 3:
        raise CaptionError("summary: 문자열 3개의 목록이어야 함")
    for where, text in [("hook", src["hook"])] + [(f"summary[{i + 1}]", t) for i, t in enumerate(summary)]:
        if not isinstance(text, str) or not text.strip():
            raise CaptionError(f"{where}: 비어 있지 않은 문자열이어야 함")
        for bad in ("<", ">", "{{", "}}", "\n", "\r"):
            if bad in text:
                raise CaptionError(f"{where}: {bad!r} 는 쓸 수 없음")
    tags = src["hashtags"]
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise CaptionError("hashtags: 문자열 목록이어야 함")


def _check_series_consistency(spec):
    series = spec.get("series")
    if series is None:
        return None
    want = series_top(series)
    top = spec["scenes"][0]["top"]
    if top != want:
        raise CaptionError(f"원고 scene 1 top {top!r} 이 series 의 {want!r} 와 다름")
    teaser = next_line(series)
    if teaser is not None and teaser not in spec["scenes"][-1]["lines"]:
        raise CaptionError(f"원고 마지막 장면에 series.next 줄 {teaser!r} 이 없음")
    return series


def _ledger_numbers(spec):
    """원고 장부의 숫자 (cls, value) -> 근거 리프 집합. 장부 밖 숫자는 넣지 않는다 (WR-01)."""
    known = {}
    for entry in spec.get("figures") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("text"), str):
            continue
        leaves = {s for s in entry.get("sources") or [] if isinstance(s, str)}
        for tok in numscan.figure_tokens(entry["text"]):
            if tok.value is not None:
                known.setdefault((tok.cls, tok.value), set()).update(leaves)
    return known


def _fig_status(spec, registry):
    """등록부 id -> (verified, legal_status). 등록부가 없으면 원고의 basis_items 를 쓴다."""
    if registry is not None:
        return {fid: (e["verified"], e["legal_status"]) for fid, e in registry["figures"].items()}
    return {i["fig"]: (i.get("verified"), i.get("legal_status"))
            for i in spec.get("basis_items") or [] if isinstance(i, dict) and isinstance(i.get("fig"), str)}


def _check_numbers(spec, src, registry=None):
    """게시글 숫자는 원고 장부에 있는 숫자여야 하고, 원고에서의 상태를 그대로 진다 (WR-01).

    미확인 수치를 쓴 줄은 `확인 필요` 경고, 발의 수치를 같은 줄의 발의안·개정안·정부안 표기 없이 쓰면 오류,
    inputs(가정) 숫자를 같은 줄이나 원고 basis 의 예시·가정·가상 표기 없이 쓰면 오류다. 돌려주는 값은 경고 목록.
    """
    known = _ledger_numbers(spec)
    status = _fig_status(spec, registry)
    basis = spec.get("basis") if isinstance(spec.get("basis"), str) else ""
    warnings = []
    for where, text in [("hook", src["hook"])] + [(f"summary[{i + 1}]", t) for i, t in enumerate(src["summary"])]:
        leaves = set()
        for tok in numscan.figure_tokens(text):
            key = (tok.cls, tok.value)
            if tok.value is None or key not in known:
                raise CaptionError(f"{where}: 게시글 문구의 숫자 '{tok.raw}' 는 원고에 없음")
            leaves |= known[key]
        figs = sorted(leaf[4:] for leaf in leaves if leaf.startswith("fig."))
        unverified = [f for f in figs if status.get(f, ("미확인", None))[0] != "확인"]
        proposed = [f for f in figs if status.get(f, (None, None))[1] == "발의"]
        if proposed and not PROPOSAL_MARK_RE.search(text):
            raise CaptionError(f"{where}: 발의 수치({', '.join(proposed)})를 사실처럼 씀 — 같은 줄에 발의안·개정안·정부안 표기 필요")
        if any(leaf.startswith("inputs.") for leaf in leaves) and not (
                LABEL_MARK_RE.search(text) or LABEL_MARK_RE.search(basis)):
            raise CaptionError(f"{where}: 가정(inputs) 숫자 — 같은 줄이나 원고 basis 에 예시·가정·가상 표기 필요")
        if unverified:
            warnings.append(f'확인 필요: {where} [{", ".join(unverified)}] "{text}"')
    return warnings


def _check_hashtags(src, config):
    seen = set()
    for tag in src["hashtags"]:
        if not HASHTAG_RE.match(tag):
            raise CaptionError(f"해시태그 형식 오류: {tag!r} ('#' 뒤에 공백 없이 한글·영문·숫자·밑줄만)")
        key = tag.lower()
        if key in seen:
            raise CaptionError(f"해시태그 중복: {tag}")
        seen.add(key)
    brand = config["brand_hashtags"]
    for tag in brand:
        if tag.lower() in seen:
            raise CaptionError(f"해시태그 중복(브랜드 태그와 겹침): {tag}")
    total = len(brand) + len(src["hashtags"])
    if total > config["max_hashtags"]:
        raise CaptionError(f"해시태그 {total}개 — 브랜드 태그 포함 최대 {config['max_hashtags']}개 (D-12)")


def _as_of_phrase(spec, basis):
    """쓰인 등록부 수치의 기준 시점이 모두 같을 때만 ' (YYYY년 M월 기준)' (WR-02).

    기준 시점이 서로 다르거나 하나라도 없으면(as_of null) 한 날짜로 묶어 말할 수 없으므로 붙이지 않는다.
    basis 에 이미 '기준' 이 있으면 겹쳐 쓰지 않는다.
    """
    if "기준" in basis:
        return ""
    keys = set()
    for item in spec.get("basis_items") or []:
        m = _AS_OF_RE.match(item.get("as_of") or "") if isinstance(item, dict) else None
        if not m:
            return ""
        keys.add((int(m.group(1)), int(m.group(2) or 0)))
    if len(keys) != 1:
        return ""
    year, month = keys.pop()
    return f" ({year}년 {month}월 기준)" if month else f" ({year}년 기준)"


def build_caption(spec, src, config, registry=None):
    """(게시글 텍스트, 경고 목록). 규칙 위반은 CaptionError. registry 를 주면 수치 상태를 등록부에서 읽는다."""
    _check_src(src)
    series = _check_series_consistency(spec)
    warnings = _check_numbers(spec, src, registry)
    _check_hashtags(src, config)
    topic = src["hashtags"]
    if len(topic) < MIN_TOPIC_TAGS:
        warnings.append(f"주제 해시태그 {len(topic)}개 — {MIN_TOPIC_TAGS}개 이상 권장")

    first = f"{series_top(series)} | {src['hook']}" if series else src["hook"]
    basis = _plain(spec["basis"]).strip() if isinstance(spec.get("basis"), str) else ""
    lines = [first, ""]
    lines += [f"• {s}" for s in src["summary"]]
    lines += ["", f"근거 · 기준: {basis}{_as_of_phrase(spec, basis)}" if basis else "근거 · 기준: (원고 basis 없음)",
              config["disclaimer"], "", config["cta"]]
    if series and "next" in series:
        lines.append(f"다음 편: {series['next']}")
    lines += ["", " ".join(config["brand_hashtags"] + topic)]
    text = "\n".join(lines) + "\n"

    if len(text) > config["max_chars"]:
        raise CaptionError(f"게시글 {len(text)}자 — 최대 {config['max_chars']}자")
    if len(first) > config["first_line_warn"]:
        warnings.append(f"첫 줄 {len(first)}자 — {config['first_line_warn']}자 넘으면 더보기에 가려질 수 있음")
    if not basis:
        warnings.append("원고에 basis 가 없어 근거 줄이 비어 있음")
    return text, warnings
