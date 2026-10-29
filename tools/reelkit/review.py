"""검수 요약 review.md 와 사람 기록 record.json (표준 라이브러리만 사용, D-01 D-02 D-13, COMP-06).

review.md 는 묶음 명령이 돌 때마다 새로 쓰는 읽기용 문서다. 사람이 적는 값(광고 해당 여부, 키움 브랜드 관계, 심의 상태,
심의번호)은 여기에 두면 다시 만들 때 사라지므로 record.json 에 두고, record.json 은 없을 때만 만들며 다시 쓰지 않는다.
이 문서에는 점검이 끝났다는 뜻의 말을 쓰지 않는다: 머리말은 위험 표현 건수 또는 사람 검수 필요 문구뿐이다.
"""
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from . import motion

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


CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")


def _safe_text(text):
    """사용자가 준 음원 이름·라이선스 메모를 한 줄 안전한 글자로: 제어 문자(줄바꿈 포함)는 공백, 백틱은 ', | 는 이스케이프 (T-04-11)."""
    return _cell(CONTROL_RE.sub(" ", str(text)).replace("`", "'"))


def _findings_table(findings):
    if not findings:
        return ["(없음)", ""]
    rows = ["| 위치 | 문제 표현 | 사유 | 대체 표현 제안 | 규칙 |", "|---|---|---|---|---|"]
    for f in findings:
        rows.append(f"| {_cell(f['where'])} | {_cell(f['text'])} | {_cell(f['reason'])} | {_cell(f['suggest'])} | "
                    f"{_cell(', '.join(f['rule']))} |")
    rows.append("")
    return rows


TAG_RE = re.compile(r"</?[a-z]+>")


def _strip_tags(text):
    return TAG_RE.sub("", str(text))


def upload_spec_line(ok, total, fail, warn):
    """업로드 규격 줄. 충족은 PASS 만 세므로 모자란 수를 실패·경고로 나눠 밝힌다 (IN-05: 경고를 말없이 미충족으로 두지 않음)."""
    notes = [f"실패 {fail}"] * bool(fail) + [f"경고 {warn}"] * bool(warn)
    return f"- 업로드 규격 검사: {ok}/{total} 항목 충족" + (f" ({', '.join(notes)})" if notes else "")


def _crop_lines(cover_warnings):
    if not cover_warnings:
        return ["- 표지 크롭 검사: 그리드 크롭(가운데 1080×1440) 밖 글자 없음 — 최종 크롭은 인스타 그리드 미리보기에서 사람이 확인"]
    return [f"- 표지 크롭 검사: {_cell(w)}" for w in cover_warnings] + [
        "  - 최종 크롭은 인스타 그리드 미리보기에서 사람이 확인"]


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


def _compliance_section(result):
    """1. 점검 결과 (결과가 없으면 못 돌렸다고 적는다: 깨끗하다는 뜻으로 읽히면 안 된다)."""
    if result is None:
        return ["## 1. 점검 결과", "", "표현 점검을 돌리지 못함 — 원고 오류를 먼저 고친 뒤 다시 만드세요. 사람 검수 필요", ""]
    by_sev = {s: [f for f in result.findings if f["severity"] == s] for s in ("수정 필요", "확인 필요")}
    out = ["## 1. 점검 결과", "",
           f"**{result.headline}**", "", result.counts_line, "", result.to_json()["limits"], "",
           "### 수정 필요", ""]
    out += _findings_table(by_sev["수정 필요"])
    out += ["### 확인 필요", ""]
    out += _findings_table(by_sev["확인 필요"])
    out += ["### 예외 처리로 제외된 표현 (사람 확인)", ""]
    if result.suppressed:
        out += ["| 위치 | 표현 | 규칙 | 사유: 부정·인용·예외 |", "|---|---|---|---|"]
        for s in result.suppressed:
            rule = s.get("rule", "")
            rule = ", ".join(rule) if isinstance(rule, list) else rule
            out.append(f"| {_cell(s.get('where', ''))} | {_cell(s.get('text', ''))} | {_cell(rule)} | "
                       f"{_cell(s.get('by', ''))} |")
        out.append("")
    else:
        out += ["없음", ""]
    return out


def _motion_line(ctx):
    """## 2 의 모션 줄: 어떤 모션으로 만들었는지, 카운트업이 몇 곳인지, 중간 숫자는 연출이라는 안내 (D-05, D-07)."""
    if ctx.get("motion") == "basic":
        return (f"- 모션: basic — 줄 진입·장면 전환 {motion.CROSS:g}초 · 카운트업 {ctx.get('countups') or 0}곳 "
                "(중간 숫자는 연출, 최종값만 장부 값)")
    return "- 모션: none (기존 형식)"


def _bgm_overview_line(bgm):
    if not bgm:
        return "- 배경음: 없음 (무음 트랙)"
    return f"- 배경음: `{_safe_text(bgm['file'])}` — 페이드 인·아웃 1초, 음량 정규화"


def _license_lines(bgm):
    """음원 라이선스 확인 줄(들). 배경음이 없으면 예전 문구 그대로 (D-11)."""
    if not bgm:
        return ["- [ ] 음원 라이선스 — 배경음 없음 = 무음 (음원을 넣었다면 이용 권리 확인)"]
    return [f"- [ ] 음원 라이선스 — 파일 `{_safe_text(bgm['file'])}` (sha256 {str(bgm['sha256'])[:12]}) · "
            f"메모: {_safe_text(bgm['license'])} — 사업자 계정 상업 사용 권리를 사람이 확인",
            "- [ ] 배경음 음량 — 영상을 들어 보고 너무 크거나 작지 않은지 확인 (목표 약 -16 LUFS, 실제 음악은 다를 수 있음)"]


def _checklist_section(check, countups=0, bgm=None):
    out = ["## 3. 사람 확인 목록", "",
           "- [ ] 수치 재확인 — 등록부 수치를 1차 출처로 다시 확인 (확인 처리는 사람만)"]
    out += _figure_lines(check)
    if countups:
        out.append("- [ ] 카운트업 — 영상 마지막 프레임의 숫자가 원고 숫자와 같은지 확인")
    out += ["- [ ] 기준일 — basis 의 기준 시점과 등록부 valid_until 이 게시일에도 맞는지",
            "- [ ] 표지 크롭 — 인스타 프로필 그리드 미리보기에서 글자가 잘리지 않는지 확인",
            *_license_lines(bgm),
            "- [ ] 개인정보 — 고객 실명·연락처·계좌 등이 영상·게시글에 없는지",
            "- [ ] 대체 표현 반영 여부 — 위 제안은 참고용이며 원고 수정은 사람이 결정", ""]
    return out


def _record_section(record, record_problem, caption_status):
    out = ["## 4. 광고·심의 기록", ""]
    if record_problem:
        out += [f"> {record_problem}", ""]
    out += ["| 광고 해당 여부 | 키움 브랜드 관계 | 심의 상태 (초안/내부 검수/승인) | 심의번호 | 검수자 | 메모 |",
            "|---|---|---|---|---|---|",
            f"| {_cell(record['ad_applicable'])} | {_cell(record['brand_relation'])} | {_cell(record['review_stage'])} | "
            f"{_cell(record['review_no'])} | {_cell(record['reviewer'])} | {_cell(record['note'])} |", "",
            "값을 바꾸려면 이 문서가 아니라 `record.json` 을 고치세요 (review.md 는 묶음을 다시 만들 때마다 새로 써집니다).", ""]
    if caption_status:
        out.append(f"- 게시글 고지 문구 상태: {caption_status}")
    out += ["- 영상 고지: basis 와 주의 장면",
            "- 고지 문구·위치·심의 절차: 초안 — 준법 검토 전", ""]
    return out


def _timing_section(ctx):
    """5. 걸린 시간: 묶음 시작·끝, 단계별 초, 요청부터 걸린 시간과 10분 이내 여부 (BNDL-07)."""
    out = ["## 5. 걸린 시간", ""]
    if ctx.get("started_at"):
        out += [f"- 묶음 시작: {ctx['started_at']}", f"- 묶음 끝: {ctx['finished_at']} (검수 요약을 쓴 시점)"]
    out += [f"- 걸린 시간 (초): {ctx.get('elapsed_s', 0):.1f}"]
    out += [f"  - {s['name']}: {s['seconds']:.1f}초" for s in ctx.get("steps") or []]
    since = ctx.get("elapsed_since_request_s")
    if since is None:
        out += ["- 요청 시각 없음 — 묶음 시간만 기록"]
    else:
        source = ctx.get("request_source") or ""
        out += [f"- 요청 시각: {ctx['request_started_at']} (출처: {source})",
                f"- 요청부터 (초): {since:.1f}",
                f"- 10분 이내 여부: {'예' if ctx.get('within_10_min') else '아니오'}"]
    out += ["- 사용자 확인을 기다린 시간(`slot --create` 이전)은 포함되지 않음", ""]
    return out


def _write_atomic(draft_dir, out):
    draft_dir = Path(draft_dir)
    path = draft_dir / "review.md"
    fd, tmp = tempfile.mkstemp(prefix=".review-", suffix=".part", dir=draft_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def write_review(draft_dir, ctx):
    """review.md 를 임시 파일에 쓴 뒤 바꿔 넣는다. ctx 키는 bundle.py 가 채운다."""
    result = ctx["result"]
    rules = result.rules
    now = datetime.now().isoformat(timespec="seconds")
    out = [f"# 릴스 검수 요약 — {ctx['name']}", "",
           f"> **{BANNER}**", "",
           f"자동 생성 {now} · 규칙 v{rules.version} — {rules.status}", ""]
    out += _compliance_section(result)

    out += ["## 2. 한눈에 보기", "",
            f"- 영상: `{ctx['mp4_name']}` ({ctx['duration']:.1f}초)",
            _motion_line(ctx),
            _bgm_overview_line(ctx.get("bgm")),
            f"- 표지: ![표지]({ctx['cover_name']})",
            f"- 장면 모음: ![장면 모음]({ctx['scenes_name']})",
            *_crop_lines(ctx["cover_warnings"]),
            upload_spec_line(ctx["spec_ok"], ctx["spec_total"], ctx["spec_fail"], ctx.get("spec_warn", 0)),
            "- " + (f"레이아웃 경고 {len(ctx['layout_warnings'])}건" if ctx["layout_warnings"] else "레이아웃 경고 없음")]
    out += [f"  - {_cell(w)}" for w in ctx["layout_warnings"]]
    out.append("")
    out += ["| 장면 | 시점(초) | 첫 줄 |", "|---|---|---|"]
    for i, (t, first) in enumerate(zip(ctx["scene_times"], ctx["scene_firsts"]), 1):
        out.append(f"| {i} | {t:.2f} | {_cell(_strip_tags(first))} |")
    out.append("")

    out += _checklist_section(ctx.get("check") or {}, ctx.get("countups") or 0, ctx.get("bgm"))
    out += _record_section(ctx["record"], ctx.get("record_problem"), ctx["caption_status"])
    out += _timing_section(ctx)
    return _write_atomic(draft_dir, out)


def write_failure_review(draft_dir, ctx):
    """실패한 실행의 review.md: 어떤 오류인지, 표현 점검 결과가 있으면 그것, 확인 목록과 기록란은 그대로 (D-11)."""
    result = ctx.get("result")
    now = datetime.now().isoformat(timespec="seconds")
    out = [f"# 릴스 검수 요약 — {ctx['name']}", "",
           f"> **{BANNER}**", ""]
    if result is not None:
        out += [f"자동 생성 {now} · 규칙 v{result.rules.version} — {result.rules.status}", ""]
    else:
        out += [f"자동 생성 {now}", ""]
    out += [f"## {ctx['heading']}", "",
            "이번 실행은 끝까지 가지 못했습니다. 이전 실행의 영상·표지·게시글 문구는 지웠으니 남은 파일을 쓰지 마세요.", ""]
    out += [f"- {_cell(e)}" for e in ctx["errors"]]
    out.append("")
    out += _compliance_section(result)
    out += _checklist_section(ctx.get("check") or {}, 0, ctx.get("bgm"))
    out += _record_section(ctx["record"], ctx.get("record_problem"), None)
    out += _timing_section(ctx)
    return _write_atomic(draft_dir, out)
