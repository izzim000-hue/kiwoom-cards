"""검수 묶음 만들기: 초안 폴더 하나를 확장 -> 점검 -> 게시글 -> 표현 점검 -> 렌더 -> 표지 -> 장면 모음 -> 검수 요약 순서로 만든다 (BNDL-01, D-11).

초안 폴더(`2026/reels/drafts/<게시일>-<슬러그>/`)에 Claude 가 쓴 spec.src.json 과 caption.src.json 이 있으면
`draft.py bundle DIR` 한 번으로 spec.json, check.json, caption.txt, compliance.json, MP4, 표지 PNG, review.md,
record.json, bundle.json 이 생긴다. 표현 점검(D-06)이 완성된 게시글을 읽어야 하므로 게시글을 먼저 만든다.
각 단계는 라이브러리 함수를 같은 프로세스에서 부르며 점검 로직을 다시 만들지 않는다.
표현 점검의 발견은 종료 코드를 바꾸지 않는다 (발견이 이 도구의 산출물이다).
음원은 `--bgm` 과 `--bgm-license` 를 함께 줄 때만 섞는다 (둘 중 하나만 있거나 메모가 비면 거부, 종료 코드 1, 아무것도 지우기 전).
종료 코드: 0 완료, 1 초안·원고·규칙·음원 입력 오류, 2 렌더·파일 환경 오류, 3 레이아웃 경고(항상 엄격), 4 업로드 규격 FAIL (4 가 우선).
"""
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from . import bgm as bgm_mod
from . import calc, caption, check, compliance, convert, expand, figures, review, slot, stills
from .render import PLAYWRIGHT_MISSING, env_error_message, render_reel  # noqa: F401 - render_reel 은 시험이 바꿔 끼운다
from .spec import SpecError, load_spec

STEPS = ("expand", "check", "caption", "compliance", "render", "cover", "scenes", "review")
TEN_MINUTES = 600
HEAD_SCRIPT = "원고 오류 — 영상 미생성"
HEAD_RENDER = "렌더 환경 오류"
HEAD_ENV = "환경 오류 — 영상 미생성"
HEAD_BGM = "음원 오류 — 영상 미생성"
# 묶음을 다시 만들 때 맨 처음 지우는 산출물 (D-11). 사람이 쓴 spec.src.json, caption.src.json, skeleton.json,
# record.json, created.json 과 그 밖의 파일은 건드리지 않는다. approval.json 이 맨 앞이다 (IN-02: 승인 무효가 먼저).
PURGE_FIXED = ("approval.json", "spec.json", "check.json", "caption.txt", "compliance.json", "review.md", "bundle.json")
# 묶음이 읽고 만든 파일 (draft_paths 의 키). 완료된 묶음은 bundle.json 의 outputs 에 sha256 을 남기고, approve 는
# 지금 파일이 그대로인지 대조한다 (WR-02: 묶음 뒤 손으로 고친 caption.txt·spec.json·review.md 를 승인하지 않음).
OUTPUT_KEYS = ("spec_src", "caption_src", "spec", "check", "caption", "compliance", "mp4", "cover", "scenes", "review")


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


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def output_hashes(paths, extra=()):
    """{파일 이름: sha256} — OUTPUT_KEYS 중 있는 보통 파일만 (심볼릭 링크 제외). extra: 초안 폴더 안의 배경음 파일 이름들."""
    out = {}
    for key in OUTPUT_KEYS:
        p = Path(paths[key])
        if p.is_file() and not p.is_symlink():
            out[p.name] = sha256_file(p)
    for n in extra:
        p = Path(paths["bundle"]).parent / n
        if p.is_file() and not p.is_symlink():
            out[n] = sha256_file(p)
    return out


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


def _iso(epoch):
    return datetime.fromtimestamp(epoch).isoformat(timespec="seconds")


def purge_outputs(d, name, keep=None):
    """이전 실행의 산출물과 승인 기록을 지운다. 이름은 검증된 폴더 이름에서만 만든다 (T-03-08, T-03-11).

    keep: 이번 실행의 음원 원본 경로. 무슨 일이 있어도 지우지 않는다 (CR-02).
    """
    victims = [d / n for n in PURGE_FIXED]
    victims += [d / f"{name}.mp4", d / f"{name}.mp4.part.mp4", d / f"{name}-cover.png", d / f"{name}-cover.png.part",
                d / f"{name}-scenes.png", d / f"{name}-scenes.png.part"]
    victims += sorted(d.glob(f"{name}.safe-s*.png"))
    # 배경음: --bgm 없이 다시 묶으면 낡은 음원 복사본이 이월되지 않는다 (D-09, T-04-15). 사용자 음원(song.mp3 등)은 건드리지 않는다.
    # 폴더 목록에 그 글자 그대로 있는 이름만 지운다: 대소문자를 가리지 않는 파일 시스템에서 d / "bgm.mp3" 는 사용자의 BGM.MP3 도 가리킨다 (CR-02)
    victims += [d / n for n in sorted(os.listdir(d)) if n in bgm_mod.TOOL_NAMES]
    for p in victims:
        if keep is not None and bgm_mod.same_file(p, keep):
            continue
        if p.is_file() or p.is_symlink():
            p.unlink()


def resolve_request(d, request_start, now=None):
    """(요청 시각 epoch 또는 None, 출처 또는 None). --request-start 가 우선이고, 없으면 slot --create 가 남긴 created.json."""
    now = time.time() if now is None else now
    if request_start is not None:
        if isinstance(request_start, str):
            try:
                request_start = float(request_start)
            except ValueError:
                raise BundleError(f"--request-start 는 epoch 초(숫자)여야 함: {request_start!r}") from None
        if isinstance(request_start, bool) or not isinstance(request_start, (int, float)) or not math.isfinite(request_start):
            raise BundleError(f"--request-start 는 epoch 초(숫자)여야 함: {request_start!r}")
        if request_start > now + 5:
            raise BundleError(f"--request-start 가 지금보다 늦음: {request_start} > {round(now)}")
        return float(request_start), "--request-start"
    try:
        epoch = json.loads((Path(d) / "created.json").read_text(encoding="utf-8"))["epoch"]
    except (OSError, ValueError, KeyError, TypeError):
        return None, None
    if isinstance(epoch, bool) or not isinstance(epoch, (int, float)) or not math.isfinite(epoch) or epoch > now + 5:
        return None, None
    return float(epoch), "created.json"


def timing_fields(started, t_start, request):
    """bundle.json 과 review.md 가 같이 쓰는 시간 기록. 요청 시각이 없으면 요청 관련 값은 모두 None."""
    finished = time.time()
    epoch, source = request
    since = None if epoch is None else round(finished - epoch, 1)
    return {
        "started_at": _iso(started), "finished_at": _iso(finished),
        "elapsed_s": round(time.monotonic() - t_start, 2),
        "request_started_at": None if epoch is None else _iso(epoch), "request_source": source,
        "elapsed_since_request_s": since,
        "within_10_min": None if since is None else since <= TEN_MINUTES,
    }


def final_code(layout_warnings, cover_warnings, spec_checks):
    """종료 코드: 업로드 규격 FAIL 4 (우선), 레이아웃·표지 경고 3, 그 밖 0. 표현 점검 발견은 코드를 바꾸지 않는다."""
    if any(c.status == "FAIL" for c in spec_checks):
        return 4
    if layout_warnings or cover_warnings:
        return 3
    return 0


class _Stop(Exception):
    def __init__(self, code):
        self.code = code


def run_cli(draft_dir, *, card=None, request_start=None, rules=None, registry=None, config=None,
            bgm=None, bgm_license=None):
    """묶음을 만들고 종료 코드를 돌려준다. 메시지는 이 함수가 직접 stdout/stderr 에 낸다."""
    try:
        d, date_text, name = validate_draft_dir(draft_dir)
    except BundleError as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    # 어떤 bundle 실행이든(인자 오류로 곧 멈추더라도) 시작하자마자 이전 승인을 무효로 한다 (IN-02)
    approval = draft_paths(d)["approval"]
    try:
        if approval.is_file() or approval.is_symlink():
            approval.unlink()
    except OSError as e:
        print(f"환경 오류: 이전 승인 기록(approval.json)을 지울 수 없음: {e}", file=sys.stderr)
        return 2
    try:
        request = resolve_request(d, request_start)
    except BundleError as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    # 음원은 아무것도 지우거나 렌더하기 전에 검사한다: 거부되면 이전 산출물이 그대로 남는다 (D-08, T-04-09)
    try:
        bgm_src = bgm_mod.validate(bgm, bgm_license, d)
    except bgm_mod.BgmError as e:
        print(f"음원 오류: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"환경 오류: 음원을 검사하지 못함: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 2
    paths = draft_paths(d)
    started = time.time()
    t_start = time.monotonic()
    steps, state = [], {"failed": None}
    frames = Path(tempfile.mkdtemp(prefix="reel-frames-"))
    exit_code = 0
    try:
        try:
            purge_outputs(d, name, keep=None if bgm_src is None else bgm_src.path)
        except OSError as e:
            print(f"환경 오류: 이전 산출물을 지울 수 없음: {e}", file=sys.stderr)
            state["failed"] = "purge"
            exit_code = 2
        else:
            exit_code = _build(d, date_text, name, paths, frames, steps, state, started, t_start,
                               card, request, rules, registry, config, bgm_src)
    except _Stop as stop:
        exit_code = stop.code
    except BaseException:
        state["failed"] = state["failed"] or "internal"
        raise
    finally:
        shutil.rmtree(frames, ignore_errors=True)
        _write_bundle_json(paths, name, steps, state, started, t_start, request, exit_code)
    return exit_code


def _write_bundle_json(paths, name, steps, state, started, t_start, request, exit_code):
    data = {"schema": 1, "name": name, "status": "failed" if state["failed"] else "complete",
            "failed_step": state["failed"], "exit_code": exit_code,
            "motion": state.get("motion"), "countups": state.get("countups"),   # 렌더 전에 멈췄으면 null
            "bgm": state.get("bgm")}
    data.update(timing_fields(started, t_start, request))
    data["steps"] = steps
    try:
        if data["status"] == "complete":
            bgm_meta = state.get("bgm")
            data["outputs"] = output_hashes(paths, (bgm_mod.META, bgm_meta["copy"]) if bgm_meta else ())
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
           card, request, rules_path, registry_path, config_path, bgm_src=None):
    registry_path = registry_path or figures.REGISTRY_PATH
    memo = {"spec": None, "result": None}

    def fail(heading, errors, code, step=None):
        """실패 검수 요약을 쓰고 멈춘다. 이전 실행의 MP4·표지·게시글은 시작할 때 이미 지웠다."""
        state["failed"] = state["failed"] or step or "expand"
        try:
            record, problem = review.ensure_record(d)
            review.write_failure_review(d, {
                "name": name, "heading": heading, "errors": list(errors), "result": memo["result"],
                "record": record, "record_problem": problem, "check": memo.get("check") or {},
                "steps": list(steps), **timing_fields(started, t_start, request),
            })
        except OSError as e:
            print(f"환경 오류: review.md 를 쓸 수 없음: {e}", file=sys.stderr)
        raise _Stop(code)

    def fallback_compliance(text=None):
        """원고가 읽히면 표현 점검만이라도 돌려 compliance.json 을 남긴다 (게시글이 없으면 원고만)."""
        try:
            spec = memo["spec"] or load_spec(paths["spec"])
            loaded = compliance.load_rules(rules_path or compliance.RULES_PATH)
            result = compliance.run(spec, text, loaded, check_json=memo.get("check"))
            _atomic_write(paths["compliance"], _json_text(result.to_json()))
            memo["result"] = result
        except (OSError, ValueError, compliance.RuleError, SpecError):
            memo["result"] = None

    try:
        registry = figures.load_registry(registry_path)
    except figures.RegistryError as e:
        print(f"등록부 오류: {e}", file=sys.stderr)
        fail(HEAD_SCRIPT, [f"등록부 오류: {e}"], 1, "registry")

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
        memo["check"] = data
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
        memo["result"] = result
        return result

    # 5 render
    def do_render():
        def sink(scene, png):
            shutil.copyfile(png, frames / f"s{scene + 1:02d}.png")

        extra = {} if bgm_src is None else {"bgm": d / state["bgm"]["copy"]}
        return render_reel(paths["spec"], paths["mp4"], layout="new", frame_sink=sink, **extra)

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

    text = None
    try:
        spec = _timed(steps, state, "expand", do_expand)
        memo["spec"] = spec
        spec, report, check_data = _timed(steps, state, "check", do_check)
        for issue in report.errors + report.warnings:
            print(str(issue), file=sys.stderr)
            if issue.kind in check.HINTS and issue.kind != "NOT_EXPANDED":
                print(f"  -> {check.HINTS[issue.kind]}", file=sys.stderr)
        if report.errors:
            state["failed"] = "check"
            steps[-1]["status"] = "failed"
            print(f"원고 오류: 점검 오류 {len(report.errors)}건 — 영상을 만들지 않음 ({report.summary()})", file=sys.stderr)
            fallback_compliance()
            fail(HEAD_SCRIPT, [str(i) for i in report.errors], 1, "check")
        text, cap_warnings, cap_cfg = _timed(steps, state, "caption", lambda: do_caption(spec))
        for w in cap_warnings:
            print(f"경고: {w}", file=sys.stderr)
        result = _timed(steps, state, "compliance", lambda: do_compliance(spec, text, cap_warnings, check_data))
    except _Stop:
        raise
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        if state["failed"] == "caption":
            fallback_compliance()
        fail(HEAD_SCRIPT, [str(e)], 1)
    except (BundleError, expand.ExpandError, calc.CalcError, figures.RegistryError, caption.CaptionError,
            compliance.RuleError, convert.ConvertError, ValueError) as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        if state["failed"] == "caption":
            fallback_compliance()
        fail(HEAD_SCRIPT, [str(e)], 1)
    except OSError as e:
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        fail(HEAD_ENV, [f"{e.__class__.__name__}: {e}"], 2)

    try:
        if bgm_src is not None:
            state["bgm"] = _timed(steps, state, "bgm", lambda: bgm_mod.install(bgm_src, d))
        r = _timed(steps, state, "render", do_render)
        state["motion"] = getattr(r, "motion", None)
        state["countups"] = getattr(r, "countups", 0)
        cover_warnings = _timed(steps, state, "cover", do_cover)
        _timed(steps, state, "scenes", do_scenes)
    except bgm_mod.BgmError as e:   # 복사본이 검사한 원본과 다름 (WR-04): 원고·환경 오류가 아니라 음원 오류(1)
        print(f"음원 오류: {e}", file=sys.stderr)
        fail(HEAD_BGM, [str(e)], 1)
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        fail(HEAD_SCRIPT, [str(e)], 1)
    except Exception as e:  # noqa: BLE001 - 환경 오류만 2 로 바꾸고 나머지는 그대로 다시 던진다
        msg = env_error_message(e)
        if msg is None and isinstance(e, stills.StillsError):
            msg = f"렌더 환경 오류: {e}"
        if msg is None:
            raise
        print(msg, file=sys.stderr)
        fail(HEAD_RENDER, [msg], 2)

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
            "spec_fail": spec_fail, "spec_warn": sum(1 for c in r.spec_checks if c.status == "WARN"),
            "layout_warnings": [str(w) for w in r.warnings],
            "motion": state["motion"], "countups": state["countups"], "bgm": state.get("bgm"),
            "caption_status": cap_cfg["status"], "steps": list(steps),
            **timing_fields(started, t_start, request),
        })
        review.write_review(d, ctx)

    try:
        _timed(steps, state, "review", do_review)
    except OSError as e:
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        raise _Stop(2) from None

    elapsed = time.monotonic() - t_start
    print(f"bundle: {name} · {result.headline} · 확인 필요 {result.counts['확인 필요']}건 · {elapsed:.1f}초")
    return final_code(r.warnings, cover_warnings, r.spec_checks)
