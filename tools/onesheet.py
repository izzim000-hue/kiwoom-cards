#!/usr/bin/env python3
"""손글씨 낱장 노트 릴스(2026-11-22 시험 틀).

밝은 책상 위 종이 한 장에 손글씨가 차례로 써지며 쌓인다. 마지막에는 한 장에 모든 칸이 보여
'저장할 만한 한 장'이 된다. 스프링·링 없음. 음악 없이 무음 트랙으로 만든다.

    python3 tools/onesheet.py reel  SPEC.json OUT.mp4     # 1080x1920 릴스
    python3 tools/onesheet.py cover SPEC.json OUT.png     # 완성 화면 표지
    python3 tools/onesheet.py form  SPEC.json OUT.png     # 1080x1350 빈 양식(DM 용)

SPEC.json
    {"kicker": "50대라면,", "title": "종목보다 ==이 다섯 칸==이 먼저",
     "rows": [{"q": "은퇴까지 몇 년?", "note": "..."}, ...],
     "close": "...", "cta": "...", "foot": "...",
     "scenes": [{"dur": 5.0, "show": "title", "caption": "..."},
                {"dur": 5.5, "show": "row1", "caption": "..."}, ...]}

show: title | row1..rowN | close | cta. 본문 표기 ==형광펜== 만 쓴다.
"""
import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reelkit import browser, constants  # noqa: E402

FPS = 30
CPS = 16            # 초당 써지는 글자
MARK_S = 0.5        # 형광펜·칸 그리는 시간
MARK_RE = re.compile(r"(==.+?==)")
NUMS = "①②③④⑤⑥⑦"

CSS = """
@font-face{font-family:Hand;src:url("{FONTS}/PoorStory-Regular.ttf")}
@font-face{font-family:Noto;src:url("{FONTS}/NotoSansKR-Bold.otf");font-weight:700}
@font-face{font-family:Noto;src:url("{FONTS}/NotoSansKR-Regular.otf");font-weight:400}
:root{--desk:#EAE4D6;--paper:#FFFDF7;--rule:#E3E6EA;--ink:#2B2B2B;--sub:#7A7A72;--green:#2F4F3E;
 --yel:rgba(255,222,89,.8)}
html,body{margin:0;width:1080px;height:{H}px;overflow:hidden;background:var(--desk)}
body{background:radial-gradient(circle at 30% 20%,#F2EDE2 0,var(--desk) 60%)}
.paper{position:absolute;left:58px;width:964px;top:{PT}px;height:{PH}px;background:var(--paper);
 box-shadow:0 2px 0 #ddd8cc,0 22px 44px rgba(60,50,30,.22);transform:rotate(-0.6deg);
 background-image:repeating-linear-gradient(to bottom,transparent 0,transparent 63px,var(--rule) 63px,var(--rule) 65px);
 background-position:0 30px}
.tape{position:absolute;top:-22px;left:50%;width:190px;height:46px;margin-left:-95px;background:rgba(214,226,214,.85);
 transform:rotate(2deg);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.in{position:absolute;left:62px;right:58px;top:0;bottom:0}
.kicker{position:absolute;top:{KY}px;font:700 46px Hand;color:var(--green)}
.title{position:absolute;top:{TY}px;font:700 {TF}px/1.25 Hand;color:var(--ink);white-space:nowrap}
.row{position:absolute;left:0;right:0;height:{RH}px}
.num{position:absolute;left:0;top:0;font:700 {QF}px Hand;color:var(--green)}
.q{position:absolute;left:{QX}px;top:0;font:700 {QF}px Hand;color:var(--ink);white-space:nowrap}
.note{position:absolute;left:{QX}px;top:{NY}px;font:700 33px Hand;color:var(--sub);white-space:nowrap}
.box{position:absolute;right:0;top:-4px;width:118px;height:{BH}px;overflow:visible}
.box path{fill:none;stroke:#4a4a4a;stroke-width:3;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:calc(1 - var(--p,0))}
.lines{position:absolute;left:{QX}px;right:0;top:{NY}px}
.lines i{display:block;height:50px;border-bottom:2px dashed #b9b9b0}
.plain{background-image:none}
.close{position:absolute;top:{CY}px;font:700 48px Hand;color:var(--ink);white-space:nowrap}
.cta{position:absolute;top:{AY}px;font:700 36px Hand;color:var(--green);white-space:nowrap}
.foot{position:absolute;left:0;bottom:22px;font:400 24px Noto;color:#9a9a92}
.cap{position:absolute;left:60px;right:60px;top:{CAPY}px;text-align:center;font:700 44px/1.38 Noto;color:#22302A;
 letter-spacing:-0.5px;word-break:keep-all;opacity:0}
.brand{position:absolute;left:0;right:0;top:{BRY}px;text-align:center;font:400 28px Noto;color:#8c8777}
.c{opacity:0}.c.on{opacity:1}
.mk{position:relative;display:inline-block}
.mk::before{content:"";position:absolute;left:-6px;right:-6px;top:50%;bottom:0;border-radius:10px;
 transform-origin:left center;transform:scaleX(var(--p,0));background:var(--yel)}
.mk>span{position:relative}
"""

LAYOUT = {
    "reel": dict(H=1920, PT=226, PH=1210, KY=42, TY=96, TF=62, RY=232, RH=150, QF=54, QX=62, NY=66, BH=66,
                 CY=1000, AY=1070, CAPY=1468, BRY=140),
    "form": dict(H=1350, PT=70, PH=1220, KY=40, TY=92, TF=60, RY=226, RH=170, QF=52, QX=62, NY=62, BH=64,
                 CY=1110, AY=1160, CAPY=-999, BRY=-999),
}


class SpecError(ValueError):
    pass


def load(path):
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SpecError(f"원고를 읽지 못했습니다: {e}") from e
    for k in ("kicker", "title", "rows", "close", "cta", "scenes"):
        if k not in spec:
            raise SpecError(f"원고에 '{k}' 가 없습니다")
    valid = {"title", "close", "cta"} | {f"row{i + 1}" for i in range(len(spec["rows"]))}
    for sc in spec["scenes"]:
        if sc.get("show") not in valid or float(sc.get("dur", 0)) < 4:
            raise SpecError(f"장면 오류(show 값 또는 4초 미만): {sc}")
    return spec


def _text(t, group):
    """글자마다 span. ==..== 은 형광펜 묶음."""
    out = []
    for piece in MARK_RE.split(t):
        if not piece:
            continue
        hl = piece.startswith("==") and piece.endswith("==")
        inner = piece[2:-2] if hl else piece
        cs = "".join(f'<span class="c" data-g="{group}">{html.escape(ch)}</span>' for ch in inner)
        out.append(f'<span class="mk" data-g="{group}"><span>{cs}</span></span>' if hl else cs)
    return "".join(out)


BOX = ('<svg class="box" viewBox="0 0 118 {BH}" data-g="{g}"><path pathLength="1" '
       'd="M8 6 C40 3 80 5 112 7 C114 24 113 {B1} 110 {B2} C78 {B3} 40 {B2} 6 {B3} C5 {B1} 6 26 8 6"/></svg>')


def page_html(spec, mode):
    L = LAYOUT[mode]
    css = CSS
    for k, v in dict(L, FONTS=constants.FONTS_DIR.resolve().as_uri()).items():
        css = css.replace("{" + k + "}", str(v))
    form = mode == "form"
    parts = [f'<div class="kicker">{_text(spec["kicker"], "title")}</div>',
             f'<div class="title">{_text(spec["title"], "title")}</div>']
    bh = L["BH"]
    for i, r in enumerate(spec["rows"]):
        g = f"row{i + 1}"
        top = L["RY"] + i * L["RH"]
        box = BOX.format(BH=bh, g=g, B1=bh - 24, B2=bh - 6, B3=bh - 4)
        under = ('<div class="lines"><i></i><i></i></div>' if form
                 else f'<div class="note">{_text(r["note"], g)}</div>')
        q = r.get("form_q", r["q"]) if form else r["q"]
        parts.append(f'<div class="row" style="top:{top}px"><div class="num">{_text(NUMS[i], g)}</div>'
                     f'<div class="q">{_text(q, g)}</div>{"" if form else box}{under}</div>')
    if form:
        parts.append(f'<div class="close">{_text(spec.get("form_close", spec["close"]), "close")}</div>')
    else:
        parts.append(f'<div class="close">{_text(spec["close"], "close")}</div>')
        parts.append(f'<div class="cta">{_text(spec["cta"], "cta")}</div>')
    parts.append(f'<div class="foot">{html.escape(spec.get("foot", ""))}</div>')
    caps = "".join(f'<div class="cap" data-s="{i}">{html.escape(sc.get("caption", ""))}</div>'
                   for i, sc in enumerate(spec["scenes"])) if not form else ""
    brand = f'<div class="brand">{html.escape(spec.get("brand", ""))}</div>' if not form else ""
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{brand}'
            f'<div class="paper{" plain" if form else ""}"><div class="tape"></div><div class="in">{"".join(parts)}</div></div>{caps}'
            '</body></html>')


SEEK_JS = """(st) => {
  // st: {groups: {g: [typedChars, markP]}, cap: [index, opacity]}
  for (const [g, v] of Object.entries(st.groups)) {
    const cs = document.querySelectorAll('.c[data-g="' + g + '"]');
    cs.forEach((c, k) => c.classList.toggle('on', k < v[0]));
    document.querySelectorAll('.mk[data-g="' + g + '"], .box[data-g="' + g + '"]')
      .forEach(m => m.style.setProperty('--p', Math.max(0, Math.min(1, v[1]))));
  }
  document.querySelectorAll('.cap').forEach(c =>
    c.style.opacity = (+c.dataset.s === st.cap[0]) ? st.cap[1] : 0);
}"""


def _count(page, g):
    return page.evaluate(f"document.querySelectorAll('.c[data-g=\"{g}\"]').length")


def schedule(spec):
    out, t = [], 0.0
    for sc in spec["scenes"]:
        d = float(sc["dur"])
        out.append((t, t + d, sc["show"]))
        t += d
    return out, t


def state_at(sch, counts, t):
    groups, cap = {}, (-1, 0)
    for i, (s, e, g) in enumerate(sch):
        if t >= e:
            groups[g] = [10 ** 6, 1]
        elif t >= s:
            local = t - s - 0.25
            n = max(0, int(local * CPS))
            type_end = counts[g] / CPS
            groups[g] = [n, (local - type_end) / MARK_S if local > type_end else 0]
            fade = min(1, (t - s) / 0.3)
            cap = (i, fade)
        else:
            groups[g] = [0, 0]
    return {"groups": groups, "cap": list(cap)}


def _open(pw, spec, mode, work):
    b, _ = browser.launch(pw)
    page = b.new_page(viewport={"width": 1080, "height": LAYOUT[mode]["H"]})
    f = Path(work) / "page.html"
    f.write_text(page_html(spec, mode), encoding="utf-8")
    page.goto(f.as_uri())
    page.evaluate("document.fonts.ready")
    status = page.evaluate("[...document.fonts].map(f => f.family + ':' + f.status)")
    if any(not s.endswith("loaded") for s in status):
        raise browser.FontLoadError(f"폰트를 불러오지 못했습니다: {status}")
    return b, page


def render_reel(spec, out):
    from playwright.sync_api import sync_playwright
    sch, total = schedule(spec)
    frames = int(round(total * FPS))
    out = Path(out)
    tmp = out.with_name(out.name + ".part.mp4")
    with tempfile.TemporaryDirectory(prefix="onesheet-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, "reel", work)
        counts = {g: _count(page, g) for _, _, g in sch}
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png",
               "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for i in range(frames):
                page.evaluate(SEEK_JS, state_at(sch, counts, i / FPS))
                p.stdin.write(page.screenshot(type="png"))
            p.stdin.close()
            if p.wait() != 0:
                raise RuntimeError("ffmpeg 인코딩 실패")
        except BaseException:
            p.kill()
            tmp.unlink(missing_ok=True)
            raise
        finally:
            b.close()
    tmp.replace(out)
    return total


def render_still(spec, out, mode, show_caption=None):
    from playwright.sync_api import sync_playwright
    sch, total = schedule(spec)
    with tempfile.TemporaryDirectory(prefix="onesheet-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, mode, work)
        try:
            st = {"groups": {g: [10 ** 6, 1] for g in ["title", "close", "cta"] +
                             [f"row{i + 1}" for i in range(len(spec["rows"]))]},
                  "cap": [-1, 0] if show_caption is None else [show_caption, 1]}
            page.evaluate(SEEK_JS, st)
            page.screenshot(path=str(out))
        finally:
            b.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="손글씨 낱장 노트 릴스(음악 없음)·표지·빈 양식")
    ap.add_argument("mode", choices=["reel", "cover", "form"])
    ap.add_argument("spec")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    try:
        spec = load(a.spec)
        if a.mode == "reel":
            print(f"duration={render_reel(spec, a.out):.1f}s")
        elif a.mode == "cover":
            render_still(spec, a.out, "reel", show_caption=len(spec["scenes"]) - 1)
            print(a.out)
        else:
            render_still(spec, a.out, "form")
            print(a.out)
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
