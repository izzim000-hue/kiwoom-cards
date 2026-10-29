"""레드팀 보고서 (COMP-04): 점검 규칙이 기존 10편과 가상 문장에서 얼마나 잡고 얼마나 잘못 잡는지 센다 (표준 라이브러리만 사용).

말뭉치 파일은 JSON 목록이고 항목 하나가 한 장면짜리 릴스다. 표본(corpus.json)은 규칙을 쓰면서 함께 본 문장이라 수치가 실제보다
높게 나온다. 따로 쓴 문장(heldout.json)은 규칙을 보지 않고 먼저 써서 커밋했고 규칙 조정에 쓰지 않는다 (사용자 지침 4).
회귀 한계는 표본에만 걸고, 암시적 문장과 따로 쓴 문장은 숫자를 보고만 한다.
보고서에는 `통과` 라는 말과 조문 번호를 쓰지 않는다 (D-05, D-08).
"""
import json
import time
from dataclasses import replace
from pathlib import Path

from . import compliance, constants

CATEGORIES = ("단정·보장", "세무 단정", "상품 권유", "비교·비방", "개인정보", "근거 누락")
TIERS = ("explicit", "obfuscated", "implicit")
LABELS = ("bad", "good")
CORPUS_PATH = constants.TOOLS_DIR / "tests" / "redteam" / "corpus.json"
HELDOUT_PATH = constants.TOOLS_DIR / "tests" / "redteam" / "heldout.json"

CAVEAT = "주의: 표본 내 수치는 규칙을 쓴 쪽이 같은 문장을 보고 맞춘 결과라 실제보다 높게 나옵니다. 따로 쓴 문장 줄을 함께 보세요."
LIMITS = "한계: 키워드·패턴 방식이라 암시적 표현은 잡지 못합니다 (AI 의미 점검은 v2)"


class CorpusError(ValueError):
    """말뭉치 파일을 읽을 수 없거나 항목이 틀렸을 때. 메시지는 한국어이고 항목 id 를 밝힌다."""


def _rank(severity):
    return compliance.SEVERITIES.index(severity)


def load_corpus(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise CorpusError(f"말뭉치 파일을 열 수 없음: {path} ({getattr(e, 'strerror', None) or e})") from None
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise CorpusError(f"말뭉치 파일 JSON 형식 오류: {path}") from None
    if not isinstance(data, list):
        raise CorpusError(f"말뭉치 파일 최상위는 목록이어야 함: {path}")
    seen = set()
    for n, e in enumerate(data, 1):
        if not isinstance(e, dict):
            raise CorpusError(f"말뭉치 {n}번째 항목이 객체가 아님")
        eid = e.get("id")
        if not isinstance(eid, str) or not eid:
            raise CorpusError(f"말뭉치 {n}번째 항목의 id 가 없음")
        if eid in seen:
            raise CorpusError(f"말뭉치 {eid}: id 가 겹침")
        seen.add(eid)
        if e.get("label") not in LABELS:
            raise CorpusError(f"말뭉치 {eid}: label 은 bad 또는 good 이어야 함")
        if e["label"] == "bad":
            if e.get("category") not in CATEGORIES:
                raise CorpusError(f"말뭉치 {eid}: 알 수 없는 category {e.get('category')!r}")
            if e.get("tier") not in TIERS:
                raise CorpusError(f"말뭉치 {eid}: tier 는 {', '.join(TIERS)} 중 하나여야 함")
        lines = e.get("lines")
        if not isinstance(lines, list) or not lines:
            raise CorpusError(f"말뭉치 {eid}: lines 가 비어 있음")
        if not all(isinstance(x, str) for x in lines):
            raise CorpusError(f"말뭉치 {eid}: lines 는 문자열만 담아야 함")
        if "basis" in e and not isinstance(e["basis"], str):
            raise CorpusError(f"말뭉치 {eid}: basis 는 문자열이어야 함")
        sev = e.get("expect_severity", "수정 필요")
        if sev not in compliance.SEVERITIES:
            raise CorpusError(f"말뭉치 {eid}: expect_severity 는 {' 또는 '.join(compliance.SEVERITIES)} 이어야 함")
    return data


def entry_spec(entry):
    return {"basis": entry.get("basis") or "", "scenes": [{"top": "", "lines": list(entry["lines"])}]}


def _quote(entry):
    return " / ".join(entry["lines"])


def _rule_ids(findings):
    out = []
    for f in findings:
        for i in f["rule"]:
            if i not in out:
                out.append(i)
    return out


def _tally(table, key, hit):
    cell = table.setdefault(key, [0, 0])
    cell[1] += 1
    cell[0] += 1 if hit else 0


def _count_suppressed(into, items):
    for s in items:
        for rid in s["rule"]:
            into[rid] = into.get(rid, 0) + 1


def evaluate(entries, rules):
    """항목마다 점검한 결과와 탐지·오탐·분류별 집계, 예외로 제외된 건수, 규칙별 최대 점검 시간(ms)을 돌려준다."""
    out = {"entries": [], "bad_total": 0, "bad_detected": 0, "good_total": 0, "good_fp": 0, "good_fp_fix": 0,
           "by_tier": {t: [0, 0] for t in TIERS}, "by_category": {c: [0, 0] for c in CATEGORIES},
           "suppressed": {}, "rule_ms": {}}
    for e in entries:
        spec = entry_spec(e)
        result = compliance.run(spec, None, rules)
        findings = result.findings
        row = {"id": e["id"], "label": e["label"], "lines": list(e["lines"]), "findings": findings,
               "detected": False, "mismatch": False, "false_positive": False, "false_positive_fix": False}
        _count_suppressed(out["suppressed"], result.suppressed)
        if e["label"] == "bad":
            expect = e.get("expect_severity", "수정 필요")
            row.update(category=e["category"], tier=e["tier"], expect=f'{e["category"]}/{expect}')
            row["detected"] = any(f["category"] == e["category"] and _rank(f["severity"]) <= _rank(expect)
                                  for f in findings)
            row["mismatch"] = bool(findings) and not row["detected"]
            row["actual"] = ", ".join(f'{f["category"]}/{f["severity"]}({"+".join(f["rule"])})' for f in findings)
            out["bad_total"] += 1
            out["bad_detected"] += 1 if row["detected"] else 0
            _tally(out["by_tier"], e["tier"], row["detected"])
            _tally(out["by_category"], e["category"], row["detected"])
        else:
            row["false_positive"] = bool(findings)
            row["false_positive_fix"] = any(f["severity"] == "수정 필요" for f in findings)
            out["good_total"] += 1
            out["good_fp"] += 1 if row["false_positive"] else 0
            out["good_fp_fix"] += 1 if row["false_positive_fix"] else 0
        out["entries"].append(row)
        _time_rules(out["rule_ms"], spec, rules)
    return out


def _time_rules(into, spec, rules):
    doc = compliance.reel_doc(spec)
    for rule in rules.rules:
        one = replace(rules, rules=[rule])
        t0 = time.perf_counter()
        compliance.scan(doc, one)
        ms = (time.perf_counter() - t0) * 1000
        if ms > into.get(rule.id, 0.0):
            into[rule.id] = ms


def published_counts(rules):
    """기존 10편: 골든 기준표에서 재현 가능한 항목의 원고만 읽는다 (디렉터리를 훑지 않는다)."""
    from . import golden
    out = {"reels": 0, "수정 필요": 0, "확인 필요": 0, "findings": [], "suppressed": []}
    for entry in golden.load_manifest()["entries"]:
        if entry.get("status") != "reproducible":
            continue
        path = constants.REPO_ROOT / entry["spec"]
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            raise CorpusError(f"기존 원고를 읽을 수 없음: {entry['spec']} ({e.__class__.__name__})") from None
        result = compliance.run(spec, None, rules)
        out["reels"] += 1
        out["수정 필요"] += result.counts["수정 필요"]
        out["확인 필요"] += result.counts["확인 필요"]
        out["suppressed"].extend(result.suppressed)
        for f in result.findings:
            out["findings"].append({"stem": entry["stem"], "severity": f["severity"], "where": f["where"],
                                    "rule": list(f["rule"]), "text": f["text"]})
        _time_rules(out.setdefault("rule_ms", {}), spec, rules)
    return out


def _summary(ev):
    bad = [r for r in ev["entries"] if r["label"] == "bad"]
    good = [r for r in ev["entries"] if r["label"] == "good"]
    return {
        "bad_total": ev["bad_total"], "bad_detected": ev["bad_detected"],
        "by_tier": ev["by_tier"], "by_category": ev["by_category"],
        "missed": [{"id": r["id"], "tier": r["tier"], "lines": r["lines"]} for r in bad
                   if not r["detected"] and not r["mismatch"]],
        "mismatch": [{"id": r["id"], "expect": r["expect"], "actual": r["actual"]} for r in bad if r["mismatch"]],
        "good_total": ev["good_total"], "good_fp": ev["good_fp"], "good_fp_fix": ev["good_fp_fix"],
        "false_positives": [{"id": r["id"], "rules": _rule_ids(r["findings"]),
                             "texts": [f["text"] for f in r["findings"]],
                             "severities": sorted({f["severity"] for f in r["findings"]})} for r in good
                            if r["false_positive"]],
    }


def _pct(n, total):
    return f"{round(100 * n / total)}%" if total else "-"


def _block(lines, s, bad_head, good_head):
    lines.append(f'{bad_head} 탐지 {s["bad_detected"]}/{s["bad_total"]} ({_pct(s["bad_detected"], s["bad_total"])}) · '
                 + " · ".join(f'{t} {a}/{b}' for t, (a, b) in s["by_tier"].items()))
    lines.append("  분류별: " + " · ".join(f"{c} {a}/{b}" for c, (a, b) in s["by_category"].items()))
    if s["missed"]:
        lines.append("  놓친 문장:")
        lines.extend(f'    {m["id"]} ({m["tier"]}) {" / ".join(m["lines"])}' for m in s["missed"])
    else:
        lines.append("  놓친 문장: 없음")
    if s["mismatch"]:
        lines.append("  분류/등급 불일치:")
        lines.extend(f'    {m["id"]} 기대 {m["expect"]} · 실제 {m["actual"]}' for m in s["mismatch"])
    else:
        lines.append("  분류/등급 불일치: 없음")
    lines.append(f'{good_head} 오탐 {s["good_fp"]}/{s["good_total"]} (수정 필요 오탐 {s["good_fp_fix"]})')
    if s["false_positives"]:
        lines.append("  오탐 문장:")
        lines.extend(f'    {f["id"]} {"+".join(f["rules"])} "{" · ".join(f["texts"])}"' for f in s["false_positives"])
    else:
        lines.append("  오탐 문장: 없음")


def report(rules, corpus, heldout):
    """(보고서 줄 목록, 같은 숫자를 담은 dict). 마지막 줄은 한 줄 요약이다."""
    pub = published_counts(rules)
    seed_ev = evaluate(corpus, rules)
    held_ev = evaluate(heldout, rules)
    seed, held = _summary(seed_ev), _summary(held_ev)

    suppressed = {}
    for src in (seed_ev["suppressed"], held_ev["suppressed"]):
        for rid, n in src.items():
            suppressed[rid] = suppressed.get(rid, 0) + n
    _count_suppressed(suppressed, pub["suppressed"])

    rule_ms = {}
    for src in (seed_ev["rule_ms"], held_ev["rule_ms"], pub.get("rule_ms", {})):
        for rid, ms in src.items():
            rule_ms[rid] = max(ms, rule_ms.get(rid, 0.0))
    slow_id, slow_ms = max(rule_ms.items(), key=lambda kv: kv[1]) if rule_ms else ("-", 0.0)

    stat = "초안" if "초안" in rules.status else rules.status
    lines = [f"규칙 v{rules.version}({stat}) · 기준일 {rules.as_of} · 규칙 {len(rules.rules)}개 · {rules.status}"]
    lines.append(f'[기존 10편] 수정 필요 {pub["수정 필요"]}건 · 확인 필요 {pub["확인 필요"]}건')
    for f in pub["findings"]:
        tag = " (오탐 후보)" if f["severity"] == "수정 필요" else ""
        lines.append(f'  {f["severity"]}{tag} · {f["stem"]} · {f["where"]} · {"+".join(f["rule"])} · "{f["text"]}"')
    _block(lines, seed, f'[레드팀 부적절 {seed["bad_total"]}건 · 표본 내]', f'[레드팀 적절 {seed["good_total"]}건 · 표본 내]')
    _block(lines, held, f'[따로 쓴 문장 부적절 {held["bad_total"]}건 — 규칙 조정에 쓰지 않음]',
           f'[따로 쓴 문장 적절 {held["good_total"]}건]')
    total_sup = sum(suppressed.values())
    detail = " · ".join(f"{rid} {n}건" for rid, n in sorted(suppressed.items())) or "없음"
    lines.append(f"[예외 처리로 제외] {total_sup}건 · {detail}")
    lines.append(f"[규칙 시간] 가장 느린 규칙 {slow_id} {slow_ms:.2f}ms (문장당 최대)")
    lines.append(CAVEAT)
    lines.append(LIMITS)
    last = (f'redteam: 표본 내 탐지 {seed["bad_detected"]}/{seed["bad_total"]} · 오탐 {seed["good_fp"]}/{seed["good_total"]}'
            f' · 따로 쓴 문장 탐지 {held["bad_detected"]}/{held["bad_total"]} · 오탐 {held["good_fp"]}/{held["good_total"]}'
            f' · 기존 10편 수정 필요 {pub["수정 필요"]}건')
    lines.append(last)

    data = {"rules": {"version": rules.version, "as_of": rules.as_of, "status": rules.status, "count": len(rules.rules)},
            "published": {k: pub[k] for k in ("reels", "수정 필요", "확인 필요", "findings")},
            "seed": seed, "heldout": held, "suppressed": suppressed,
            "slowest_rule": {"id": slow_id, "ms": round(slow_ms, 3)},
            "caveat": CAVEAT, "limits": LIMITS, "last_line": last}
    return lines, data
