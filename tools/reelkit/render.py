"""원고 -> 프레임 스크린샷 -> MP4 전체 흐름, 장면별 레이아웃 측정과 안전영역 미리보기."""
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import browser, specprobe, timeline
from . import motion as motion_mod
from .constants import FPS
from .encode import EncodeError, PipeEncoder, encode_concat
from .layout import LAYOUTS, MEASURE_JS, TAG_JS, LayoutWarning, evaluate_layout, new_inner_html, overlay_html
from .spec import SpecError, check_legacy_markup, load_spec


PLAYWRIGHT_MISSING = "playwright 미설치: python3 -m pip install --user -r tools/requirements.txt"


def playwright_error_types():
    """렌더 중 Playwright 가 던지는 오류 형식. Playwright 가 없으면 빈 튜플(아무것도 잡지 않음)."""
    try:
        from playwright.sync_api import Error
    except ImportError:
        return ()
    return (Error,)


def env_error_message(exc):
    """렌더 환경 오류(종료 코드 2)의 한국어 안내문. 환경 오류가 아니면 None (원고 오류나 코드 결함은 가리지 않는다).

    reel.py 와 draft.py bundle 이 같은 매핑을 쓴다: playwright 미설치, 번들 폰트·Chromium·ffmpeg 실패,
    Playwright 오류, 파일·하위 프로세스 오류.
    """
    if isinstance(exc, ImportError):
        # 이 패키지 자체의 결함(잘못된 import 등)을 "playwright 미설치" 로 가리지 않는다
        if (getattr(exc, "name", None) or "").split(".")[0] == "playwright":
            return PLAYWRIGHT_MISSING
        return None
    if isinstance(exc, (browser.FontLoadError, browser.BrowserLaunchError, EncodeError)):
        return f"렌더 환경 오류: {exc}"
    if isinstance(exc, (*playwright_error_types(), OSError, subprocess.SubprocessError)):
        # ffmpeg/ffprobe 실행, 파일 쓰기, Chromium 실행 중 오류는 원고 오류(1)가 아니라 환경 오류(2)
        return f"렌더 환경 오류: {exc.__class__.__name__}: {exc}"
    return None


@dataclass
class RenderResult:
    out: Path
    total: float
    cover_ms: int
    launch: str
    warnings: list = field(default_factory=list)
    overlays: list = field(default_factory=list)
    spec_checks: list = field(default_factory=list)
    motion: str = "none"
    countups: int = 0


def _read_spec(spec_path):
    """원고 JSON 을 읽고 형식을 검사한다. 형식 오류는 SpecError."""
    return load_spec(spec_path)


def _check_layout_name(layout):
    if layout not in LAYOUTS:
        raise ValueError(f"알 수 없는 배치 '{layout}'. 사용 가능: {', '.join(LAYOUTS)}")


def _open_checked_page(b, work):
    page = browser.open_page(b, work)
    problems = browser.font_problems(page)
    if problems:
        raise browser.FontLoadError(
            "; ".join(problems)
            + ". 시스템 폰트로 대체하지 않고 중단합니다. python3 tools/doctor.py 로 점검하세요")
    return page


def _scene_checks(page, layout, scene_number):
    """장면의 최종 상태가 떠 있는 page 에서 경고를 모은다. (warnings, 측정값 또는 None) 을 돌려준다.

    새 배치만 위치·줄 수를 측정한다. legacy 는 근거·계정명이 항상 아래쪽 UI 영역이라
    측정하면 게시된 릴스가 전부 경고가 되므로 일부러 건너뛴다. 글꼴 대체 검사는 둘 다 한다.
    """
    warnings, measured = [], None
    if layout == "new":
        measured = page.evaluate(MEASURE_JS)
        warnings.extend(evaluate_layout(measured, scene_number))
    page.evaluate(TAG_JS[layout])
    labels = page.evaluate(
        "[...document.querySelectorAll('[data-rk]')].map(e=>[e.dataset.rk, e.textContent.trim().slice(0,30)])")
    fonts = browser.platform_fonts(page, "[data-rk]")
    seen = set()
    for (label, text), used in zip(labels, fonts):
        if label in seen:
            continue
        fallback = [f for f in used if not f.get("isCustomFont")]
        if fallback:
            seen.add(label)
            warnings.append(LayoutWarning(scene_number, label, "FONT_FALLBACK",
                                          str(fallback[0].get("familyName", "?")), text))
    return warnings, measured


def _tallest_scene(measures):
    """측정값 중 위 라벨 윗끝에서 계정명 아랫끝까지가 가장 긴 장면 번호(1부터)."""
    best, best_span = None, -1.0
    for n, m in measures.items():
        if not m or not m.get("acct"):
            continue
        tops = [e["t"] for e in [m.get("top")] + list(m.get("lines") or []) if e]
        span = m["acct"]["b"] - (min(tops) if tops else m["acct"]["t"])
        if span > best_span:
            best, best_span = n, span
    return best


def _write_overlay(page, make_html, basis, st, prog, path):
    page.evaluate("h=>{document.body.innerHTML=h}", make_html(st.top, st.lines, st.k, prog, basis))
    page.evaluate("document.fonts.ready.then(()=>0)")
    page.evaluate("h=>{document.getElementById('rk-root').insertAdjacentHTML('beforeend', h)}", overlay_html())
    page.screenshot(path=str(path))
    page.evaluate("()=>{const o=document.getElementById('rk-ov'); if(o) o.remove()}")


def _render_motion(spec, out_path, *, keep_work, overlay_all, frame_sink):
    """motion basic: 장면 최종 상태 정적 검사 -> 모션 레이어 -> 프레임마다 시간 탐색·스크린샷 -> PNG 파이프 인코딩.

    측정과 경고는 정적 새 배치 그대로 하고 (모션 DOM 에서는 측정하지 않는다), 모션 DOM 이 그 배치와 같다는 것은 시험이 지킨다.
    """
    basis = spec.get("basis", "")
    states = timeline.build_states(spec)
    progs = timeline.progress_values(states)
    sched = motion_mod.schedule(spec)
    cu_items = motion_mod.countup_entries(spec)   # Chromium 을 띄우기 전에 장부를 검사한다 (T-04-06)
    finals_at = {sc.final_frame: sc.index for sc in sched.scenes}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright  # 미설치 시 ImportError 는 CLI 가 안내한다

    work = tempfile.mkdtemp(prefix="reelkit-")
    warnings, overlays = [], []
    try:
        with sync_playwright() as pw:
            b, used = browser.launch(pw)
            try:
                page = _open_checked_page(b, work)
                finals, measures = {}, {}
                for st, prog in zip(states, progs):
                    if st.k != len(st.lines):
                        continue
                    page.evaluate("h=>{document.body.innerHTML=h}", new_inner_html(st.top, st.lines, st.k, prog, basis))
                    page.evaluate("document.fonts.ready.then(()=>0)")
                    scene = st.scene + 1
                    ws, measured = _scene_checks(page, "new", scene)
                    warnings.extend(ws)
                    finals[scene] = (st, prog)
                    measures[scene] = measured
                wanted = sorted(finals) if overlay_all else sorted({1, _tallest_scene(measures) or 1} & set(finals))
                for scene in wanted:
                    st, prog = finals[scene]
                    path = out_path.with_name(out_path.stem + f".safe-s{scene:02d}.png")
                    _write_overlay(page, new_inner_html, basis, st, prog, path)
                    overlays.append(path)
                cu_lines = motion_mod.build(page, spec, sched)
                for c in cu_lines:
                    static = (measures.get(c["s"] + 1) or {}).get("lines") or []
                    want = static[c["j"]] if c["j"] < len(static) else None
                    if want is not None and want["n"] != c["n"]:
                        text = motion_mod.TAG_RE.sub("", spec["scenes"][c["s"]]["lines"][c["j"]])[:30]
                        warnings.append(LayoutWarning(c["s"] + 1, str(c["j"] + 1), "COUNTUP_WRAP",
                                                      f"{want['n']}줄 -> {c['n']}줄", text))
                warnings.extend(motion_mod.dwell_warnings(spec, sched))
                with PipeEncoder(out_path) as enc:
                    for f in range(sched.nframes):
                        motion_mod.seek(page, sched, f / FPS, motion_mod.countup_texts(sched, cu_items, f / FPS))
                        png = page.screenshot(type="png")
                        idx = finals_at.get(f)
                        if idx is not None:
                            still = Path(work) / f"s{idx:02d}.png"
                            still.write_bytes(png)
                            if frame_sink is not None:
                                frame_sink(idx, str(still))
                        enc.write(png)
                    enc.close()
            finally:
                b.close()
        spec_checks = specprobe.probe(out_path)  # 읽기 전용: 파일을 다시 인코딩하거나 고치지 않는다
    finally:
        if keep_work:
            print(f"작업 폴더 보존: {work}", file=sys.stderr)
        else:
            shutil.rmtree(work, ignore_errors=True)
    return RenderResult(out=out_path, total=sched.total, cover_ms=round(sched.scenes[0].final_t * 1000),
                        launch=used, warnings=warnings, overlays=overlays, spec_checks=spec_checks, motion="basic",
                        countups=len(cu_items))


def render_reel(spec_path, out_path, *, layout="legacy", keep_work=False, overlay_all=False, frame_sink=None,
                motion=None):
    """frame_sink(장면 번호 0부터, PNG 경로): 장면 최종 상태 프레임을 쓴 직후 한 번 부른다. 작업 폴더는 끝나면 지워지므로 바로 복사한다.

    motion: None 이면 원고의 motion 필드(없으면 none), 'none'/'basic' 이면 그 값. basic 은 새 배치에서만 쓸 수 있다.
    """
    _check_layout_name(layout)
    spec = _read_spec(spec_path)
    mode = motion_mod.resolve(spec, motion)
    if mode == "basic":
        if layout != "new":
            raise SpecError("motion basic 은 --layout new 에서만 쓸 수 있음")
        return _render_motion(spec, out_path, keep_work=keep_work, overlay_all=overlay_all, frame_sink=frame_sink)
    if layout == "legacy":
        check_legacy_markup(spec)  # 작업 폴더·Chromium 보다 먼저: 거부된 원고는 브라우저도 MP4도 만들지 않는다
    basis = spec.get("basis", "")
    states = timeline.build_states(spec)
    total = timeline.total_duration(states)
    progs = timeline.progress_values(states)
    make_html = LAYOUTS[layout]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright  # 미설치 시 ImportError 는 CLI 가 안내한다

    work = tempfile.mkdtemp(prefix="reelkit-")
    warnings, overlays = [], []
    try:
        files = []
        with sync_playwright() as pw:
            b, used = browser.launch(pw)
            try:
                page = _open_checked_page(b, work)
                finals, measures = {}, {}
                for n, (st, prog) in enumerate(zip(states, progs)):
                    page.evaluate("h=>{document.body.innerHTML=h}", make_html(st.top, st.lines, st.k, prog, basis))
                    page.evaluate("document.fonts.ready.then(()=>0)")
                    f = f"{work}/v{n:03d}.png"
                    page.screenshot(path=f)
                    files.append((f, st.dur))
                    if st.k == len(st.lines):  # 장면 최종 상태: 스크린샷 뒤에 측정하므로 라벨이 프레임에 남지 않는다
                        if frame_sink is not None:
                            frame_sink(st.scene, f)
                        scene = st.scene + 1
                        ws, measured = _scene_checks(page, layout, scene)
                        warnings.extend(ws)
                        finals[scene] = (st, prog)
                        measures[scene] = measured
                if layout == "new":
                    wanted = sorted(finals) if overlay_all else sorted(
                        {1, _tallest_scene(measures) or 1} & set(finals))
                    for scene in wanted:
                        st, prog = finals[scene]
                        path = out_path.with_name(out_path.stem + f".safe-s{scene:02d}.png")
                        _write_overlay(page, make_html, basis, st, prog, path)
                        overlays.append(path)
            finally:
                b.close()
        encode_concat(files, total, out_path, work)
        spec_checks = specprobe.probe(out_path)  # 읽기 전용: 파일을 다시 인코딩하거나 고치지 않는다
    finally:
        if keep_work:
            print(f"작업 폴더 보존: {work}", file=sys.stderr)
        else:
            shutil.rmtree(work, ignore_errors=True)
    return RenderResult(out=out_path, total=total, cover_ms=timeline.cover_ms(spec), launch=used,
                        warnings=warnings, overlays=overlays, spec_checks=spec_checks)


def check_layout(spec_path, layout="new"):
    """MP4 를 만들지 않고 장면별 레이아웃 경고만 돌려준다 (Phase 2 가 초안 점검에 재사용)."""
    _check_layout_name(layout)
    spec = _read_spec(spec_path)
    if layout == "legacy":
        check_legacy_markup(spec)
    basis = spec.get("basis", "")
    states = timeline.build_states(spec)
    progs = timeline.progress_values(states)
    make_html = LAYOUTS[layout]

    from playwright.sync_api import sync_playwright

    work = tempfile.mkdtemp(prefix="reelkit-check-")
    warnings = []
    try:
        with sync_playwright() as pw:
            b, _used = browser.launch(pw)
            try:
                page = _open_checked_page(b, work)
                for st, prog in zip(states, progs):
                    if st.k != len(st.lines):
                        continue
                    page.evaluate("h=>{document.body.innerHTML=h}", make_html(st.top, st.lines, st.k, prog, basis))
                    page.evaluate("document.fonts.ready.then(()=>0)")
                    ws, _m = _scene_checks(page, layout, st.scene + 1)
                    warnings.extend(ws)
            finally:
                b.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return warnings
