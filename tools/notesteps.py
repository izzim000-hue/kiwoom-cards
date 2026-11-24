#!/usr/bin/env python3
"""장면별 손글씨 노트 릴스(2026-11-24, 사용자 피드백 '리스트 한 장은 내용이 없다').

위쪽 제목은 처음부터 끝까지 고정되고, 아래 종이가 장면마다 한 장씩 넘어간다.
장면마다 항목 하나 + 손글씨 예시 몇 줄 + 설계사의 판단 한마디. 음악 없이 무음 트랙.

    python3 tools/notesteps.py reel  SPEC.json OUT.mp4
    python3 tools/notesteps.py cover SPEC.json OUT.png    # 마지막 직전(정리) 장면 완성 화면

SPEC.json
  {"brand": "...", "kicker": "50대라면,", "title": "은퇴 후 ==매달 들어올 돈==",
   "scenes": [{"dur": 4.5, "step": "①", "head": "매달 들어올 돈", "tag": "가상 예시",
               "lines": ["국민연금 | 110만", "월세 | 40만"], "judge": "통장에 ==매달== 들어오는 것만",
               "note": "작은 주석(선택)", "caption": "녹음 자막"}], "foot": "..."}
  lines 의 'a | b' 는 왼쪽 항목·오른쪽 값. ==글자== 는 형광펜.
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
CPS = 36
START = 0.35        # 페이지가 넘어온 뒤 쓰기 시작
MARK_S = 0.3
MARK_RE = re.compile(r"(==.+?==)")

CSS = """
@font-face{font-family:Hand;src:url("{F}/PoorStory-Regular.ttf")}
@font-face{font-family:Noto;src:url("{F}/NotoSansKR-Bold.otf");font-weight:700}
@font-face{font-family:Noto;src:url("{F}/NotoSansKR-Regular.otf");font-weight:400}
:root{--desk:#EAE4D6;--paper:#FFFDF7;--rule:#E3E6EA;--ink:#2B2B2B;--sub:#7A7A72;--green:#2F4F3E;
 --yel:rgba(255,222,89,.85);--red:#B5473A}
html,body{margin:0;width:1080px;height:1920px;overflow:hidden}
body{background:radial-gradient(circle at 30% 15%,#F2EDE2 0,var(--desk) 60%)}
.brand{position:absolute;left:0;right:0;top:120px;text-align:center;font:400 28px Noto;color:#8c8777}
.kicker{position:absolute;left:84px;top:200px;font:700 52px Hand;color:var(--green)}
.title{position:absolute;left:84px;top:268px;font:700 80px/1.2 Hand;color:var(--ink);white-space:nowrap}
.page{position:absolute;left:58px;width:964px;top:440px;height:1010px;background:var(--paper);opacity:0;
 box-shadow:0 2px 0 #ddd8cc,0 22px 44px rgba(60,50,30,.22);
 background-image:repeating-linear-gradient(to bottom,transparent 0,transparent 110px,var(--rule) 110px,var(--rule) 112px);
 background-position:0 40px}
.tape{position:absolute;top:-22px;left:50%;width:190px;height:46px;margin-left:-95px;background:rgba(214,226,214,.85);
 transform:rotate(2deg)}
.in{position:absolute;left:66px;right:62px;top:0;bottom:0}
.head{position:absolute;top:58px;left:0;font:700 74px Hand;color:var(--ink);white-space:nowrap}
.head b{color:var(--green);margin-right:14px}
.tag{position:absolute;top:70px;right:0;font:700 26px Noto;color:var(--red);border:3px solid var(--red);
 border-radius:8px;padding:2px 14px;transform:rotate(4deg);opacity:.85}
.ln{position:absolute;left:0;right:0;height:112px;font:700 62px Hand;color:#333;white-space:nowrap}
.ln .a{position:absolute;left:0;bottom:8px}
.ln .b{position:absolute;right:0;bottom:8px;color:var(--green)}
.judge{position:absolute;left:0;right:0;top:{JY}px;font:700 50px/1.45 Noto;color:var(--green);word-break:keep-all}
.note{position:absolute;left:0;right:0;bottom:30px;font:400 25px Noto;color:#9a9a92}
.dots{position:absolute;right:0;bottom:30px;font:700 26px Noto;color:#b5b0a2}
.cap{position:absolute;left:60px;right:60px;top:1500px;text-align:center;font:700 44px/1.4 Noto;color:#22302A;
 letter-spacing:-0.5px;word-break:keep-all;opacity:0}
.foot{position:absolute;left:0;right:0;bottom:70px;text-align:center;font:400 24px Noto;color:#9a9a92}
.c{opacity:0}.c.on{opacity:1}
.mk{position:relative;display:inline-block}
.mk::before{content:"";position:absolute;left:-6px;right:-6px;top:52%;bottom:2px;border-radius:10px;
 transform-origin:left center;transform:scaleX(var(--p,0));background:var(--yel)}
.title .mk::before{transform:scaleX(1)}
.mk>span{position:relative}
"""

LINE_Y0 = 236
LINE_H = 112


class SpecError(ValueError):
    pass


def load(path):
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SpecError(f"원고를 읽지 못했습니다: {e}") from e
    for k in ("kicker", "title", "scenes"):
        if k not in spec:
            raise SpecError(f"원고에 '{k}' 가 없습니다")
    for sc in spec["scenes"]:
        if float(sc.get("dur", 0)) < 3.5 or "head" not in sc:
            raise SpecError(f"장면 오류(head 없음 또는 3.5초 미만): {sc}")
        if len(sc.get("lines", [])) > 6:
            raise SpecError(f"장면 줄 수는 6줄 이하: {sc['head']}")
    return spec


class Typer:
    """장면 하나의 글자에 순번을 매긴다. 형광펜은 끝 글자 순번을 기억한다."""

    def __init__(self):
        self.i = 0

    def text(self, t, typed=True):
        out = []
        for piece in MARK_RE.split(t):
            if not piece:
                continue
            hl = piece.startswith("==") and piece.endswith("==")
            inner = piece[2:-2] if hl else piece
            cs = []
            for ch in inner:
                if ch == "\n":
                    cs.append("<br>")
                    continue
                if typed:
                    cs.append(f'<span class="c" data-i="{self.i}">{html.escape(ch)}</span>')
                    self.i += 1
                else:
                    cs.append(html.escape(ch))
            cs = "".join(cs)
            out.append(f'<span class="mk" data-end="{self.i}"><span>{cs}</span></span>' if hl else cs)
        return "".join(out)


def page_html(spec):
    css = CSS.replace("{F}", constants.FONTS_DIR.resolve().as_uri())
    n = len(spec["scenes"])
    pages, caps = [], []
    for k, sc in enumerate(spec["scenes"]):
        ty = Typer()
        step = f"<b>{html.escape(sc['step'])}</b>" if sc.get("step") else ""
        head = f'<div class="head">{step}{ty.text(sc["head"], typed=False)}</div>'
        tag = f'<div class="tag">{html.escape(sc["tag"])}</div>' if sc.get("tag") else ""
        lines = []
        for j, ln in enumerate(sc.get("lines", [])):
            a, _, b = ln.partition("|")
            top = LINE_Y0 + j * LINE_H
            body = f'<span class="a">{ty.text(a.strip())}</span>'
            if b:
                body += f'<span class="b">{ty.text(b.strip())}</span>'
            lines.append(f'<div class="ln" style="top:{top}px">{body}</div>')
        jy = LINE_Y0 + max(len(sc.get("lines", [])), 1) * LINE_H + 70
        judge = f'<div class="judge" style="top:{jy}px">{ty.text(sc.get("judge", ""))}</div>'
        note = f'<div class="note">{html.escape(sc["note"])}</div>' if sc.get("note") else ""
        dots = f'<div class="dots">{k + 1} / {n}</div>' if not sc.get("note") else ""
        pages.append(f'<div class="page" data-k="{k}"><div class="tape"></div><div class="in">'
                     f'{head}{tag}{"".join(lines)}{judge}{note}{dots}</div></div>')
        caps.append(f'<div class="cap" data-k="{k}">{html.escape(sc.get("caption", ""))}</div>')
    title = Typer().text(spec["title"], typed=False)
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>'
            f'<div class="brand">{html.escape(spec.get("brand", ""))}</div>'
            f'<div class="kicker">{html.escape(spec["kicker"])}</div><div class="title">{title}</div>'
            f'{"".join(pages)}{"".join(caps)}<div class="foot">{html.escape(spec.get("foot", ""))}</div>'
            '</body></html>')


SEEK_JS = """(st) => {
  const [k, enter, n, cap] = st;
  document.querySelectorAll('.page').forEach(p => {
    const on = +p.dataset.k === k;
    p.style.opacity = on ? Math.min(1, enter * 1.4) : 0;
    p.style.transform = on ? `translateX(${(1 - enter) * 70}px) rotate(-0.6deg)` : 'none';
    if (!on) return;
    p.querySelectorAll('.c').forEach(c => c.classList.toggle('on', +c.dataset.i < n));
    p.querySelectorAll('.mk').forEach(m =>
      m.style.setProperty('--p', Math.max(0, Math.min(1, (n - +m.dataset.end) / %MARKN%))));
  });
  document.querySelectorAll('.cap').forEach(c => c.style.opacity = (+c.dataset.k === k) ? cap : 0);
}""".replace("%MARKN%", str(CPS * MARK_S))


def schedule(spec):
    out, t = [], 0.0
    for sc in spec["scenes"]:
        d = float(sc["dur"])
        out.append((t, t + d))
        t += d
    return out, t


def state_at(sch, t):
    for k, (s, e) in enumerate(sch):
        if s <= t < e or k == len(sch) - 1:
            local = t - s
            enter = min(1.0, local / 0.3)
            n = max(0, int((local - START) * CPS))
            return [k, enter, n, min(1.0, local / 0.2)]


def _open(pw, spec, work):
    b, _ = browser.launch(pw)
    page = b.new_page(viewport={"width": 1080, "height": 1920})
    f = Path(work) / "page.html"
    f.write_text(page_html(spec), encoding="utf-8")
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
    with tempfile.TemporaryDirectory(prefix="notesteps-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, work)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png",
               "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for i in range(frames):
                page.evaluate(SEEK_JS, state_at(sch, i / FPS))
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


def render_still(spec, out, k):
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory(prefix="notesteps-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, work)
        try:
            page.evaluate(SEEK_JS, [k, 1, 10 ** 6, 1])
            page.screenshot(path=str(out))
        finally:
            b.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="장면별 손글씨 노트 릴스(음악 없음)·표지")
    ap.add_argument("mode", choices=["reel", "cover", "still"])
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--scene", type=int, help="still 모드: 장면 번호(0부터)")
    a = ap.parse_args(argv)
    try:
        spec = load(a.spec)
        if a.mode == "reel":
            print(f"duration={render_reel(spec, a.out):.1f}s")
        else:
            k = a.scene if a.mode == "still" else spec.get("cover_scene", len(spec["scenes"]) - 2)
            render_still(spec, a.out, k)
            print(a.out)
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
