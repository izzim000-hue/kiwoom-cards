#!/usr/bin/env python3
"""스프링 노트 컨셉(2026-11, 샘플 reels14) 릴스·카드뉴스 생성기.

진한 딥그린 배경 위 아이보리 스프링 노트에 글자가 한 글자씩 써지고, 핵심 단어에
형광펜·동그라미가 칠해지는 형식. 릴스는 음악 없이 만든다(음원은 사람이 고른다).

    python3 tools/notebook.py reel  SPEC.json OUT.mp4
    python3 tools/notebook.py cards SPEC.json OUT_DIR      # 1080x1350 PNG, 장마다 1장

SPEC.json
    {"series": "돈의 구조 설계 #15", "title": "새는 돈부터",
     "foot": "예시는 가정에 따른 추정",            # 선택: 노트 아래 작은 글씨(기본값)
     "scenes": [{"lines": ["모으기 전에,", "==새는 돈==부터 막아요"], "foot": true}, ...]}

본문 표기: ==노랑 형광펜==, ++연두 형광펜++, ((동그라미)). 그 밖의 글자는 그대로 쓴다.
카드뉴스는 scenes 의 각 장면을 완성된 상태로 한 장씩 저장한다.
"""

import argparse
import html
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reelkit import browser, constants  # noqa: E402
from reelkit.encode import EncodeError, PipeEncoder  # noqa: E402

FPS = 30
TYPE_CPS = 14          # 초당 써지는 글자 수
MARK_S = 0.45          # 형광펜·동그라미가 칠해지는 시간
HOLD_S = 1.6           # 장면이 다 써진 뒤 머무는 시간
LAST_HOLD_S = 2.6
GAP_S = 0.25           # 장면 사이 빈 노트
DEFAULT_FOOT = "예시는 가정에 따른 추정"
TOKEN_RE = re.compile(r"(==.+?==|\+\+.+?\+\+|\(\(.+?\)\))")

CSS = """
@font-face{font-family:Hand;src:url("{FONTS}/GowunDodum-Regular.ttf")}
@font-face{font-family:Noto;src:url("{FONTS}/NotoSansKR-Regular.otf")}
:root{--bg:#1F3A2D;--paper:#FBF8F1;--rule:#C9D1DD;--margin:#E9A9A3;--ink:#333;--sub:#666;
 --yel:rgba(255,225,77,.75);--grn:rgba(182,240,156,.85)}
html,body{margin:0;width:1080px;height:{H}px;overflow:hidden;background:var(--bg)}
.paper{position:absolute;left:64px;right:64px;top:{PT}px;bottom:{PB}px;background:var(--paper);border-radius:14px;
 box-shadow:0 18px 40px rgba(0,0,0,.45);overflow:hidden;
 background-image:repeating-linear-gradient(to bottom,transparent 0,transparent {RG}px,var(--rule) {RG}px,var(--rule) {RG2}px);
 background-position:0 {RO}px}
.margin{position:absolute;left:96px;top:0;bottom:0;width:2px;background:var(--margin);opacity:.7}
.rings{position:absolute;left:110px;right:110px;top:{RT}px;display:flex;justify-content:space-between}
.ring{width:18px;height:74px;border:6px solid #3d3d3d;border-radius:12px;box-sizing:border-box;background:transparent}
.series{position:absolute;left:134px;top:{SY}px;font:32px Hand;color:var(--sub)}
.title{position:absolute;left:134px;top:{TY}px;font:{TF}px Hand;color:#444}
.body{position:absolute;left:134px;right:120px;top:{BY}px;font:{BF}px/{LH} Hand;color:var(--ink);white-space:nowrap}
.foot{position:absolute;left:130px;bottom:{FB}px;font:30px Noto;color:#8a8a8a}
.sprout{position:absolute;right:{SR}px;bottom:{SB}px;width:74px;height:78px}
.c{opacity:0}.c.on{opacity:1}
.mk{position:relative;display:inline-block}
.mk::before{content:"";position:absolute;left:-6px;right:-6px;top:52%;bottom:2%;border-radius:10px;
 transform-origin:left center;transform:scaleX(var(--p,0));z-index:0}
.mk.y::before{background:var(--yel)}.mk.g::before{background:var(--grn)}
.mk>span{position:relative;z-index:1}
.ci{position:relative;display:inline-block;margin:0 22px}
.ci svg{position:absolute;left:-40px;top:-12px;width:calc(100% + 80px);height:calc(100% + 24px);overflow:visible}
.ci ellipse{fill:none;stroke:#444;stroke-width:3;stroke-dasharray:var(--len);stroke-dashoffset:calc(var(--len) * (1 - var(--p,0)))}
"""

SPROUT = ('<svg class="sprout" viewBox="0 0 74 78" fill="none" stroke="#6b6b6b" stroke-width="5" stroke-linecap="round">'
          '<path d="M37 72V34"/><path d="M37 38C30 22 16 16 4 18c2 14 16 22 33 20"/>'
          '<path d="M37 38c6-16 20-24 33-22-2 14-15 22-33 22"/><path d="M24 74h26"/></svg>')

LAYOUT = {  # 1920 릴스 / 1350 카드
    "reel": dict(H=1920, PT=170, PB=152, RG=118, RO=118, RT=-42, SY=150, TY=262, BY=490, BF=78, TF=52, LH=1.48, FB=52, SR=46, SB=36),
    "card": dict(H=1350, PT=110, PB=70, RG=96, RO=92, RT=-40, SY=120, TY=200, BY=400, BF=64, TF=66, LH=1.62, FB=40, SR=40, SB=28),
}


class SpecError(ValueError):
    pass


def load(path):
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SpecError(f"원고를 읽지 못했습니다: {e}") from e
    for key in ("series", "title", "scenes"):
        if key not in spec:
            raise SpecError(f"원고에 '{key}' 가 없습니다")
    if not spec["scenes"] or not all(isinstance(s.get("lines"), list) and s["lines"] for s in spec["scenes"]):
        raise SpecError("scenes 의 각 장면에는 lines(1줄 이상)가 있어야 합니다")
    return spec


def _chars(text):
    """보이는 글자 수 (표기 기호 제외)."""
    return len(TOKEN_RE.sub(lambda m: m.group(0)[2:-2], text))


def schedule(spec):
    """장면별 (시작, 타이핑 끝, 표시 끝, 장면 끝) 초."""
    out, t = [], 0.4
    for i, sc in enumerate(spec["scenes"]):
        n = sum(_chars(l) for l in sc["lines"])
        type_end = t + n / TYPE_CPS
        marks = sum(len(TOKEN_RE.findall(l)) for l in sc["lines"])
        mark_end = type_end + (MARK_S + 0.1) * marks
        end = mark_end + (LAST_HOLD_S if i == len(spec["scenes"]) - 1 else HOLD_S)
        out.append((t, type_end, mark_end, end))
        t = end + GAP_S
    return out


def _line_html(text, counter):
    parts = []
    for piece in TOKEN_RE.split(text):
        if not piece:
            continue
        kind = None
        if piece.startswith("==") and piece.endswith("=="):
            kind, inner = "y", piece[2:-2]
        elif piece.startswith("++") and piece.endswith("++"):
            kind, inner = "g", piece[2:-2]
        elif piece.startswith("((") and piece.endswith("))"):
            kind, inner = "o", piece[2:-2]
        else:
            inner = piece
        chars = "".join(f'<span class="c" data-i="{next(counter)}">{html.escape(ch)}</span>' for ch in inner)
        if kind in ("y", "g"):
            parts.append(f'<span class="mk {kind}"><span>{chars}</span></span>')
        elif kind == "o":
            parts.append(f'<span class="ci">{chars}<svg preserveAspectRatio="none" viewBox="0 0 100 40">'
                         f'<ellipse cx="50" cy="20" rx="48" ry="18" pathLength="1" style="--len:1"/></svg></span>')
        else:
            parts.append(chars)
    return "".join(parts)


def page_html(spec, mode):
    L = LAYOUT[mode]
    css = CSS
    vals = dict(L, RG2=L["RG"] + 2, FONTS=constants.FONTS_DIR.resolve().as_uri())
    for k, v in vals.items():
        css = css.replace("{" + k + "}", str(v))
    scenes = []
    for si, sc in enumerate(spec["scenes"]):
        counter = iter(range(10 ** 6))
        lines = "<br>".join(_line_html(l, counter) for l in sc["lines"])
        foot = sc.get("foot")
        foot_txt = (spec.get("foot", DEFAULT_FOOT) if foot is True else foot) or ""
        title = html.escape(sc.get("title", spec["title"]))
        scenes.append(f'<div class="scene" data-s="{si}" style="display:none"><div class="title">{title}</div><div class="body">{lines}</div>'
                      f'<div class="foot">{html.escape(foot_txt)}</div></div>')
    rings = '<div class="ring"></div>' * 11
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>'
            f'<div class="paper"><div class="margin"></div>'
            f'<div class="series">{html.escape(spec["series"])}</div>'
            f'{"".join(scenes)}{SPROUT}</div><div class="rings">{rings}</div></body></html>'
            ).replace('<div class="rings">', f'<div class="rings" style="top:{L["PT"] + L["RT"]}px;left:174px;right:174px">')


SEEK_JS = """(args) => {
  const [si, typed, markP] = args;
  document.querySelectorAll('.scene').forEach(s => s.style.display = (+s.dataset.s === si) ? 'block' : 'none');
  if (si < 0) return;
  const sc = document.querySelector('.scene[data-s="' + si + '"]');
  sc.querySelectorAll('.c').forEach(c => c.classList.toggle('on', +c.dataset.i < typed));
  const marks = sc.querySelectorAll('.mk, .ci');
  marks.forEach((m, k) => m.style.setProperty('--p', Math.max(0, Math.min(1, markP - k))));
}"""


def _state(sch, t):
    for si, (s, te, me, e) in enumerate(sch):
        if s <= t < e or (si == len(sch) - 1 and t >= s):
            n_total = None
            typed = int((t - s) * TYPE_CPS) if t < te else 10 ** 6
            mark_p = 0.0 if t < te else (t - te) / (MARK_S + 0.1)
            return si, typed, mark_p
    return -1, 0, 0.0


def _open(pw, spec, mode, work):
    b, _used = browser.launch(pw)
    L = LAYOUT[mode]
    page = b.new_page(viewport={"width": 1080, "height": L["H"]})
    f = Path(work) / "page.html"
    f.write_text(page_html(spec, mode), encoding="utf-8")
    page.goto(f.as_uri())
    page.evaluate("document.fonts.ready")
    status = page.evaluate("[...document.fonts].map(f => f.family + ':' + f.status)")
    if any(not s.endswith("loaded") for s in status if s.startswith("Hand")):
        raise browser.FontLoadError(f"손글씨 폰트를 불러오지 못했습니다: {status}")
    return b, page


def render_reel(spec, out):
    from playwright.sync_api import sync_playwright
    sch = schedule(spec)
    total = sch[-1][3]
    frames = int(round(total * FPS))
    with tempfile.TemporaryDirectory(prefix="notebook-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, "reel", work)
        enc = PipeEncoder(out)
        try:
            for i in range(frames):
                page.evaluate(SEEK_JS, list(_state(sch, i / FPS)))
                enc.write(page.screenshot(type="png"))
            enc.close()
        except BaseException:
            enc.abort()
            raise
        finally:
            b.close()
    return total


def render_cards(spec, out_dir):
    from playwright.sync_api import sync_playwright
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with tempfile.TemporaryDirectory(prefix="notebook-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, "card", work)
        try:
            for si, _ in enumerate(spec["scenes"]):
                page.evaluate(SEEK_JS, [si, 10 ** 6, 99])
                p = out_dir / f"card_{si + 1}.png"
                page.screenshot(path=str(p))
                paths.append(p)
        finally:
            b.close()
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description="스프링 노트 컨셉 릴스(음악 없음)·카드뉴스 생성")
    ap.add_argument("mode", choices=["reel", "cards"])
    ap.add_argument("spec")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    try:
        spec = load(a.spec)
        if a.mode == "reel":
            total = render_reel(spec, a.out)
            print(f"duration={total:.1f}s")
        else:
            for p in render_cards(spec, a.out):
                print(p)
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    except (browser.BrowserLaunchError, browser.FontLoadError, EncodeError) as e:
        print(f"환경 오류: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
