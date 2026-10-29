"""검수 묶음 만들기: 초안 폴더 하나를 확장 -> 점검 -> 게시글 -> 표현 점검 -> 렌더 -> 표지 -> 검수 요약 순서로 만든다 (BNDL-01, D-11).

초안 폴더(`2026/reels/drafts/<게시일>-<슬러그>/`)에 Claude 가 쓴 spec.src.json 과 caption.src.json 이 있으면
`draft.py bundle DIR` 한 번으로 spec.json, check.json, caption.txt, compliance.json, MP4, 표지 PNG, review.md,
record.json, bundle.json 이 생긴다. 표현 점검(D-06)이 완성된 게시글을 읽어야 하므로 게시글을 먼저 만든다.
각 단계는 라이브러리 함수를 같은 프로세스에서 부르며 점검 로직을 다시 만들지 않는다.
표현 점검의 발견은 종료 코드를 바꾸지 않는다 (발견이 이 도구의 산출물이다).
종료 코드: 0 완료, 1 초안·원고·규칙 입력 오류, 2 렌더·파일 환경 오류, 3 레이아웃 경고(항상 엄격), 4 업로드 규격 FAIL (4 가 우선).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from . import calc, caption, check, compliance, convert, expand, figures, review, slot, stills
from .browser import BrowserLaunchError, FontLoadError
from .encode import EncodeError
from .spec import SpecError, load_spec

STEPS = ("expand", "check", "caption", "compliance", "render", "cover", "scenes", "review")
TEN_MINUTES = 600
PLAYWRIGHT_MISSING = "playwright 미설치: python3 -m pip install --user -r tools/requirements.txt"


class BundleError(ValueError):
    """초안 폴더가 규칙에 어긋날 때. 메시지는 한국어."""


def validate_draft_dir(path):
    """(해석된 Path, 게시일 문자열, 이름). drafts 폴더 바로 아래의 `<YYYY-MM-DD>-<슬러그>` 폴더만 받는다."""
    p = Path(path)
    if not p.is_dir():
        raise BundleError(f"초안 폴더가 아님: {path}")
    p = p.resolve()
    if p.parent.name != "drafts":
        raise BundleError(f"초안 폴더는 drafts/ 바로 아래여야 함: {p}")
    name = p.name
    date_text, slug = name[:10], name[11:]
    if len(name) < 12 or name[10] != "-":
        raise BundleError(f"폴더 이름은 <YYYY-MM-DD>-<슬러그> 형식이어야 함: {name}")
    try:
        slot.check_date(date_text)
        slot.check_slug(slug)
    except slot.SlotError as e:
        raise BundleError(f"폴더 이름 오류: {e}") from None
    for need in ("spec.src.json", "caption.src.json"):
        if not (p / need).is_file():
            raise BundleError(f"{need} 가 없음: {p}")
    return p, date_text, name


def draft_paths(draft_dir):
    d = Path(draft_dir)
    name = d.name
    return {
        "spec_src": d / "spec.src.json", "spec": d / "spec.json", "check": d / "check.json",
        "caption_src": d / "caption.src.json", "caption": d / "caption.txt",
        "compliance": d / "compliance.json", "mp4": d / f"{name}.mp4", "cover": d / f"{name}-cover.png", "scenes": d / f"{name}-scenes.png",
        "review": d / "review.md", "record": d / "record.json", "bundle": d / "bundle.json",
        "approval": d / "approval.json",
    }


def _read_json(path, label):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"{label} 파일을 열 수 없음: {path} ({getattr(e, 'strerror', None) or e})") from None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"{label} JSON 형식 오류: {path} 줄 {e.lineno} 열 {e.colno}") from None


def _atomic_write(path, text):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
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


def _json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _playwright_error_types():
    try:
        from playwright.sync_api import Error
    except ImportError:
        return ()
    return (Error,)


def _iso(epoch):
    return datetime.fromtimestamp(epoch).isoformat(timespec="seconds")


class _Stop(Exception):
    def __init__(self, code):
        self.code = code


def run_cli(draft_dir, *, card=None, request_start=None, rules=None, registry=None, config=None):
    """묶음을 만들고 종료 코드를 돌려준다. 메시지는 이 함수가 직접 stdout/stderr 에 낸다."""
    try:
        d, date_text, name = validate_draft_dir(draft_dir)
    except BundleError as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    paths = draft_paths(d)
    started = time.time()
    t_start = time.monotonic()
    steps, state = [], {"failed": None}
    frames = Path(tempfile.mkdtemp(prefix="reel-frames-"))
    exit_code = 0
    try:
        exit_code = _build(d, date_text, name, paths, frames, steps, state, started, t_start,
                           card, request_start, rules, registry, config)
    except _Stop as stop:
        exit_code = stop.code
    finally:
        shutil.rmtree(frames, ignore_errors=True)
        _write_bundle_json(paths, name, steps, state, started, t_start, request_start, exit_code)
    return exit_code


def _write_bundle_json(paths, name, steps, state, started, t_start, request_start, exit_code):
    finished = time.time()
    elapsed = round(time.monotonic() - t_start, 2)
    since = None if request_start is None else round(finished - request_start, 2)
    data = {
        "schema": 1, "name": name, "status": "failed" if state["failed"] else "complete",
        "failed_step": state["failed"], "exit_code": exit_code,
        "started_at": _iso(started), "finished_at": _iso(finished), "elapsed_s": elapsed,
        "steps": steps,
        "request_started_at": None if request_start is None else _iso(request_start),
        "elapsed_since_request_s": since,
        "within_10_min": (since if since is not None else elapsed) <= TEN_MINUTES,
    }
    try:
        _atomic_write(paths["bundle"], _json_text(data))
    except OSError as e:
        print(f"환경 오류: bundle.json 을 쓸 수 없음: {e}", file=sys.stderr)


def _timed(steps, state, name, fn):
    t = time.monotonic()
    try:
        out = fn()
    except BaseException:
        steps.append({"name": name, "seconds": round(time.monotonic() - t, 2), "status": "failed"})
        state["failed"] = name
        raise
    steps.append({"name": name, "seconds": round(time.monotonic() - t, 2), "status": "ok"})
    return out


def _build(d, date_text, name, paths, frames, steps, state, started, t_start,
           card, request_start, rules_path, registry_path, config_path):
    registry_path = registry_path or figures.REGISTRY_PATH
    try:
        registry = figures.load_registry(registry_path)
    except figures.RegistryError as e:
        print(f"등록부 오류: {e}", file=sys.stderr)
        raise _Stop(1) from None

    ctx = {}

    # 1 expand
    def do_expand():
        src = _read_json(paths["spec_src"], "원고 소스")
        spec = expand.expand_source(src, registry)
        expand.write_spec(spec, paths["spec"])
        return spec

    # 2 check
    def do_check():
        spec = load_spec(paths["spec"])
        report = check.check_spec(spec, registry, publish_date=datetime.strptime(date_text, "%Y-%m-%d").date())
        src = _read_json(paths["spec_src"], "원고 소스")
        report.source = str(paths["spec_src"])
        report.errors.extend(check.compare_source(spec, src, registry))
        if card:
            check.apply_card(report, convert.load_card(card), spec, card)
        data = report.to_json(paths["spec"], registry_path)
        _atomic_write(paths["check"], _json_text(data))
        return spec, report, data

    # 3 caption
    def do_caption(spec):
        cfg = caption.load_config(config_path or caption.CONFIG_PATH)
        text, warnings = caption.build_caption(spec, _read_json(paths["caption_src"], "게시글 문구 원본"), cfg, registry)
        _atomic_write(paths["caption"], text)
        return text, warnings, cfg

    # 4 compliance
    def do_compliance(spec, text, warnings, check_data):
        loaded = compliance.load_rules(rules_path or compliance.RULES_PATH)
        result = compliance.run(spec, text, loaded, check_json=check_data, caption_warnings=warnings)
        _atomic_write(paths["compliance"], _json_text(result.to_json()))
        return result

    # 5 render
    def do_render():
        from .render import render_reel   # playwright 는 render_reel 안에서 늦게 읽는다

        def sink(scene, png):
            shutil.copyfile(png, frames / f"s{scene + 1:02d}.png")

        return render_reel(paths["spec"], paths["mp4"], layout="new", frame_sink=sink)

    # 6 cover
    def do_cover():
        src = frames / "s01.png"
        tmp = paths["cover"].with_name(paths["cover"].name + ".part")
        shutil.copyfile(src, tmp)
        os.replace(tmp, paths["cover"])
        return stills.cover_crop_warnings(paths["cover"])

    # 7 scenes
    def do_scenes():
        found = sorted(frames.glob("s[0-9][0-9].png"))
        stills.contact_sheet(found, paths["scenes"])
        return len(found)

    try:
        spec = _timed(steps, state, "expand", do_expand)
        spec, report, check_data = _timed(steps, state, "check", do_check)
        for issue in report.errors + report.warnings:
            print(str(issue), file=sys.stderr)
            if issue.kind in check.HINTS and issue.kind != "NOT_EXPANDED":
                print(f"  -> {check.HINTS[issue.kind]}", file=sys.stderr)
        if report.errors:
            state["failed"] = "check"
            steps[-1]["status"] = "failed"
            print(f"원고 오류: 점검 오류 {len(report.errors)}건 — 영상을 만들지 않음 ({report.summary()})", file=sys.stderr)
            raise _Stop(1)
        text, cap_warnings, cap_cfg = _timed(steps, state, "caption", lambda: do_caption(spec))
        for w in cap_warnings:
            print(f"경고: {w}", file=sys.stderr)
        result = _timed(steps, state, "compliance", lambda: do_compliance(spec, text, cap_warnings, check_data))
    except (SpecError,) as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        raise _Stop(1) from None
    except (BundleError, expand.ExpandError, calc.CalcError, figures.RegistryError, caption.CaptionError,
            compliance.RuleError, convert.ConvertError, ValueError) as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        raise _Stop(1) from None
    except OSError as e:
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        raise _Stop(2) from None

    try:
        r = _timed(steps, state, "render", do_render)
        cover_warnings = _timed(steps, state, "cover", do_cover)
        _timed(steps, state, "scenes", do_scenes)
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        raise _Stop(1) from None
    except ImportError as e:
        if (getattr(e, "name", None) or "").split(".")[0] != "playwright":
            raise
        print(PLAYWRIGHT_MISSING, file=sys.stderr)
        raise _Stop(2) from None
    except (FontLoadError, BrowserLaunchError, EncodeError, stills.StillsError) as e:
        print(f"렌더 환경 오류: {e}", file=sys.stderr)
        raise _Stop(2) from None
    except (*_playwright_error_types(), OSError, subprocess.SubprocessError) as e:
        print(f"렌더 환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        raise _Stop(2) from None

    print(f"duration={r.total:.1f}s cover_ms={r.cover_ms}")
    for w in r.warnings:
        print(str(w), file=sys.stderr)
    if r.warnings:
        print(f"레이아웃 경고 {len(r.warnings)}건", file=sys.stderr)
    for w in cover_warnings:
        print(w, file=sys.stderr)
    for path in r.overlays:
        print(f"안전영역 미리보기: {path}", file=sys.stderr)
    from .specprobe import format_report
    for line in format_report(r.out, r.spec_checks):
        print(line, file=sys.stderr)

    def do_review():
        record, problem = review.ensure_record(d)
        spec_fail = sum(1 for c in r.spec_checks if c.status == "FAIL")
        ctx.update({
            "name": name, "result": result, "check": check_data, "record": record, "record_problem": problem,
            "mp4_name": paths["mp4"].name, "cover_name": paths["cover"].name, "scenes_name": paths["scenes"].name,
            "cover_warnings": list(cover_warnings), "scene_times": stills.scene_times(spec),
            "scene_firsts": [sc["lines"][0] for sc in spec["scenes"]], "duration": r.total,
            "spec_total": len(r.spec_checks), "spec_ok": sum(1 for c in r.spec_checks if c.status == "PASS"),
            "spec_fail": spec_fail, "layout_warnings": [str(w) for w in r.warnings],
            "caption_status": cap_cfg["status"], "steps": list(steps),
            "elapsed_s": round(time.monotonic() - t_start, 2),
        })
        review.write_review(d, ctx)

    try:
        _timed(steps, state, "review", do_review)
    except OSError as e:
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        raise _Stop(2) from None

    elapsed = time.monotonic() - t_start
    print(f"bundle: {name} · {result.headline} · 확인 필요 {result.counts['확인 필요']}건 · {elapsed:.1f}초")
    if any(c.status == "FAIL" for c in r.spec_checks):
        return 4
    if r.warnings or cover_warnings:
        return 3
    return 0
