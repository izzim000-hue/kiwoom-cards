"""원고 -> 프레임 스크린샷 -> MP4 전체 흐름."""
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import browser, timeline
from .encode import encode_concat
from .layout import LAYOUTS


@dataclass
class RenderResult:
    out: Path
    total: float
    cover_ms: int
    launch: str
    warnings: list = field(default_factory=list)
    overlays: list = field(default_factory=list)


def _read_spec(spec_path):
    """원고 JSON 을 기존 reel.py 와 같은 방식으로 읽는다 (Plan 02 에서 spec.load_spec 으로 교체)."""
    return json.loads(Path(spec_path).read_text(encoding="utf-8"))


def render_reel(spec_path, out_path, *, layout="legacy", keep_work=False):
    if layout not in LAYOUTS:
        raise ValueError(f"알 수 없는 배치 '{layout}'. 사용 가능: {', '.join(LAYOUTS)}")
    spec = _read_spec(spec_path)
    basis = spec.get("basis", "")
    states = timeline.build_states(spec)
    total = timeline.total_duration(states)
    progs = timeline.progress_values(states)
    make_html = LAYOUTS[layout]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright  # 미설치 시 ImportError 는 CLI 가 안내한다

    work = tempfile.mkdtemp(prefix="reelkit-")
    try:
        files = []
        with sync_playwright() as pw:
            b, used = browser.launch(pw)
            try:
                page = browser.open_page(b, work)
                problems = browser.font_problems(page)
                if problems:
                    raise browser.FontLoadError(
                        "; ".join(problems)
                        + ". 시스템 폰트로 대체하지 않고 중단합니다. python3 tools/doctor.py 로 점검하세요")
                for n, (st, prog) in enumerate(zip(states, progs)):
                    page.evaluate("h=>{document.body.innerHTML=h}", make_html(st.top, st.lines, st.k, prog, basis))
                    page.evaluate("document.fonts.ready.then(()=>0)")
                    f = f"{work}/v{n:03d}.png"
                    page.screenshot(path=f)
                    files.append((f, st.dur))
            finally:
                b.close()
        encode_concat(files, total, out_path, work)
    finally:
        if keep_work:
            print(f"작업 폴더 보존: {work}", file=sys.stderr)
        else:
            shutil.rmtree(work, ignore_errors=True)
    return RenderResult(out=out_path, total=total, cover_ms=timeline.cover_ms(spec), launch=used)
