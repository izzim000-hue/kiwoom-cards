"""검수 요약 review.md 와 사람 기록 record.json (표준 라이브러리만 사용, D-01 D-02 D-13, COMP-06).

review.md 는 묶음 명령이 돌 때마다 새로 쓰는 읽기용 문서다. 사람이 적는 값(광고 해당 여부, 키움 브랜드 관계, 심의 상태,
심의번호)은 여기에 두면 다시 만들 때 사라지므로 record.json 에 두고, record.json 은 없을 때만 만들며 다시 쓰지 않는다.
이 문서에는 점검이 끝났다는 뜻의 말을 쓰지 않는다: 머리말은 위험 표현 건수 또는 사람 검수 필요 문구뿐이다.
"""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

RECORD_DEFAULTS = {"ad_applicable": "미확인", "brand_relation": "미확인", "review_stage": "미확인",
                   "review_no": "미확인", "reviewer": "", "note": ""}
RECORD_PROBLEM = "record.json 읽기 오류 — 미확인으로 표시, 파일은 고치지 않음"
BANNER = "초안 — 사람 검수 후 게시"


def ensure_record(draft_dir):
    """(값 dict, 문제 문구 또는 None). 없으면 기본값으로 만들고(배타 생성), 있으면 읽기만 한다."""
    path = Path(draft_dir) / "record.json"
    text = json.dumps(RECORD_DEFAULTS, ensure_ascii=False, indent=1) + "\n"
    try:
        with open(path, "x", encoding="utf-8") as f:
            f.write(text)
        return dict(RECORD_DEFAULTS), None
    except FileExistsError:
        pass
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return dict(RECORD_DEFAULTS), RECORD_PROBLEM
    if not isinstance(data, dict):
        return dict(RECORD_DEFAULTS), RECORD_PROBLEM
    values = dict(RECORD_DEFAULTS)
    values.update({k: v for k, v in data.items() if k in RECORD_DEFAULTS and isinstance(v, str)})
    return values, None


def _cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def _findings_table(findings):
    if not findings:
        return ["(없음)", ""]
    rows = ["| 위치 | 문제 표현 | 사유 | 대체 표현 제안 | 규칙 |", "|---|---|---|---|---|"]
    for f in findings:
        rows.append(f"| {_cell(f['where'])} | {_cell(f['text'])} | {_cell(f['reason'])} | {_cell(f['suggest'])} | "
                    f"{_cell(', '.join(f['rule']))} |")
    rows.append("")
    return rows


def _figure_lines(check):
    """수치 재확인 목록: check.json 의 figures_used/needs_check 에서 등록부 id 와 확인 상태를 읽는다."""
    unverified = []
    for item in check.get("needs_check") or []:
        for fid in item.get("ids") or []:
            fid = fid[4:] if fid.startswith("fig.") else fid
            if fid not in unverified:
                unverified.append(fid)
    used = []
    for fid in check.get("figures_used") or []:
        fid = fid[4:] if isinstance(fid, str) and fid.startswith("fig.") else fid
        if isinstance(fid, str) and fid not in used:
            used.append(fid)
    if not used and not unverified:
        return ["  - 등록부 수치 없음"]
    return [f"  - `{fid}` — {'미확인' if fid in unverified else '확인'}" for fid in sorted(set(used) | set(unverified))]


def write_review(draft_dir, ctx):
    """review.md 를 임시 파일에 쓴 뒤 바꿔 넣는다. ctx 키는 bundle.py 가 채운다."""
    draft_dir = Path(draft_dir)
    result = ctx["result"]
    rules = result.rules
    record, record_problem = ctx["record"], ctx.get("record_problem")
    check = ctx.get("check") or {}
    name = ctx["name"]
    stat = rules.status
    now = datetime.now().isoformat(timespec="seconds")
    by_sev = {s: [f for f in result.findings if f["severity"] == s] for s in ("수정 필요", "확인 필요")}

    out = [f"# 릴스 검수 요약 — {name}", "",
           f"> **{BANNER}**", "",
           f"자동 생성 {now} · 규칙 v{rules.version} — {stat}", "",
           "## 1. 점검 결과", "",
           f"**{result.headline}**", "", result.counts_line, "", result.to_json()["limits"], "",
           "### 수정 필요", ""]
    out += _findings_table(by_sev["수정 필요"])
    out += ["### 확인 필요", ""]
    out += _findings_table(by_sev["확인 필요"])
    if result.suppressed:
        out += ["### 예외 처리로 제외됨 (사람 확인)", "", "| 위치 | 표현 | 규칙 | 제외 사유 |", "|---|---|---|---|"]
        for s in result.suppressed:
            rule = s.get("rule", "")
            rule = ", ".join(rule) if isinstance(rule, list) else rule
            out.append(f"| {_cell(s.get('where', ''))} | {_cell(s.get('text', ''))} | {_cell(rule)} | "
                       f"{_cell(s.get('by', ''))} |")
        out.append("")

    out += ["## 2. 한눈에 보기", "",
            f"- 영상: `{ctx['mp4_name']}` ({ctx['duration']:.1f}초)",
            f"- 표지: ![표지]({ctx['cover_name']})",
            f"- 업로드 규격 검사: {ctx['spec_ok']}/{ctx['spec_total']} 항목 충족"
            + (f" (실패 {ctx['spec_fail']})" if ctx["spec_fail"] else ""),
            "- " + (f"레이아웃 경고 {len(ctx['layout_warnings'])}건" if ctx["layout_warnings"] else "레이아웃 경고 없음")]
    out += [f"  - {_cell(w)}" for w in ctx["layout_warnings"]]
    out.append("")

    out += ["## 3. 사람 확인 목록", "",
            "- [ ] 수치 재확인 — 등록부 수치를 1차 출처로 다시 확인 (확인 처리는 사람만)"]
    out += _figure_lines(check)
    out += ["- [ ] 기준일 — basis 의 기준 시점과 등록부 valid_until 이 게시일에도 맞는지",
            "- [ ] 표지 크롭 — 인스타 프로필 그리드 미리보기에서 글자가 잘리지 않는지 확인",
            "- [ ] 음원 라이선스 — 배경음 없음 = 무음 (음원을 넣었다면 이용 권리 확인)",
            "- [ ] 개인정보 — 고객 실명·연락처·계좌 등이 영상·게시글에 없는지",
            "- [ ] 대체 표현 반영 여부 — 위 제안은 참고용이며 원고 수정은 사람이 결정", ""]

    out += ["## 4. 광고·심의 기록", ""]
    if record_problem:
        out += [f"> {record_problem}", ""]
    out += ["| 광고 해당 여부 | 키움 브랜드 관계 | 심의 상태 (초안/내부 검수/승인) | 심의번호 | 검수자 | 메모 |",
            "|---|---|---|---|---|---|",
            f"| {_cell(record['ad_applicable'])} | {_cell(record['brand_relation'])} | {_cell(record['review_stage'])} | "
            f"{_cell(record['review_no'])} | {_cell(record['reviewer'])} | {_cell(record['note'])} |", "",
            "값을 바꾸려면 이 문서가 아니라 `record.json` 을 고치세요 (review.md 는 묶음을 다시 만들 때마다 새로 써집니다).", "",
            f"- 게시글 고지 문구 상태: {ctx['caption_status']}",
            "- 영상 고지: basis 와 주의 장면",
            "- 고지 문구·위치·심의 절차: 초안 — 준법 검토 전", ""]

    steps = ctx.get("steps") or []
    out += ["## 5. 걸린 시간", ""]
    out += [f"- {s['name']}: {s['seconds']:.1f}초" for s in steps]
    out += [f"- 합계(지금까지): {ctx.get('elapsed_s', 0):.1f}초", ""]

    text = "\n".join(out)
    path = draft_dir / "review.md"
    fd, tmp = tempfile.mkstemp(prefix=".review-", suffix=".part", dir=draft_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path
