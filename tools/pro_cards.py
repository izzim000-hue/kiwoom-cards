#!/usr/bin/env python3
"""전문가 톤 카드뉴스 생성기 (2026-11-16, 상담 후기 시리즈).

캐릭터·손글씨 없이 여백, Noto Sans KR, 얇은 선 도식으로 절제된 신뢰감을 낸다.

    python3 tools/pro_cards.py SPEC.json OUT_DIR

SPEC
{
  "series": "상담 노트",            # 왼쪽 위 작은 표시
  "brand": "키움멘토",              # 오른쪽 아래 서명
  "foot": "기본 하단 문구",
  "cards": [
    {"kicker": "01", "head": "줄1|**강조**", "sub": "보조 문장|두 번째 줄",
     "diagram": {"type": "boxes", ...}, "foot": true | "문구"}
  ]
}
head·sub 의 | 는 줄바꿈, **글자** 는 딥그린 강조(밑줄).
도식 type: boxes, cycle, split, tags, steps, form, cover (아래 DIAGRAMS 참고)
"""

import argparse
import html
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reelkit import browser  # noqa: E402

W, H = 1080, 1350
FONTS = Path(__file__).resolve().parent / "fonts"

# ---------------------------------------------------------------- 색
BG = "#CFE0EC"        # 채도 낮춘 하늘색
PAPER = "#FFFFFF"
INK = "#1F2A33"
SUB = "#5B6670"
LINE = "#9AA7B1"
FAINT = "#EEF3F6"
GREEN = "#2F4F3E"
GOLD = "#B8975A"      # 아주 적게


def esc(s):
    return html.escape(str(s))


def rich(s):
    out = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", s)):
        out.append(f'<em>{esc(part)}</em>' if i % 2 else esc(part))
    return "".join(out).replace("|", "<br>")


def T(x, y, s, size=30, fill=INK, weight=500, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{esc(s)}</text>')


def R(x, y, w, h, fill=PAPER, stroke=LINE, sw=2, rx=6, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def A(x1, y1, x2, y2, color=LINE, sw=2):
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - 14 * math.cos(ang - 0.45), y2 - 14 * math.sin(ang - 0.45))
    p2 = (x2 - 14 * math.cos(ang + 0.45), y2 - 14 * math.sin(ang + 0.45))
    return (f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{color}" stroke-width="{sw}" fill="none"/>'
            f'<path d="M{p1[0]:.1f} {p1[1]:.1f} L{x2} {y2} L{p2[0]:.1f} {p2[1]:.1f}" stroke="{color}" stroke-width="{sw}" fill="none"/>')


# 도식 영역: 880 x 520
def d_boxes(d):
    """같은 크기 상자 n개. items: [{"title","note","muted"}], caption."""
    items = d["items"]
    n = len(items)
    gap = 28
    bw = (880 - gap * (n - 1)) / n
    out = []
    for i, it in enumerate(items):
        x = i * (bw + gap)
        muted = it.get("muted")
        out.append(R(x, 60, bw, 300, FAINT if muted else PAPER, LINE, 2))
        out.append(T(x + bw / 2, 175, it["title"], 40, SUB if muted else INK, 700))
        if it.get("note"):
            out.append(f'<line x1="{x + 40}" y1="215" x2="{x + bw - 40}" y2="215" stroke="{FAINT if not muted else "#D9E2E8"}" stroke-width="2"/>')
            out.append(T(x + bw / 2, 262, it["note"], 26, SUB, 400))
        if it.get("tag") is not None:
            out.append(R(x + 30, 300, bw - 60, 44, PAPER, LINE, 1.5, 22, "6 6"))
            out.append(T(x + bw / 2, 331, it["tag"], 24, SUB, 400))
    if d.get("caption"):
        out.append(T(440, 460, d["caption"], 28, SUB, 400))
    return out


def d_cycle(d):
    """원 위에 단계가 돌아가는 고리. steps, caption."""
    import math
    steps = d["steps"]
    cx, cy, r = 440, 245, 175
    out = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{LINE}" stroke-width="2" stroke-dasharray="4 10"/>']
    n = len(steps)
    for i, s in enumerate(steps):
        a = -math.pi / 2 + 2 * math.pi * i / n
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append(R(x - 95, y - 38, 190, 76, PAPER, INK if i == 0 else LINE, 2, 38))
        out.append(T(x, y + 11, s, 30, INK, 600))
    out.append(T(cx, cy + 12, d.get("center", ""), 30, SUB, 400))
    if d.get("caption"):
        out.append(T(440, 505, d["caption"], 28, SUB, 400))
    return out


def d_split(d):
    """한 줄기에서 두 갈래. top, left{title,note}, right{title,note}, caption."""
    out = [R(330, 20, 220, 70, PAPER, INK, 2, 35), T(440, 66, d["top"], 30, INK, 700),
           f'<path d="M440 90 L440 140 M215 140 L665 140 M215 140 L215 175 M665 140 L665 175" stroke="{LINE}" stroke-width="2" fill="none"/>']
    for x, side, hi in ((40, d["left"], True), (490, d["right"], False)):
        out.append(R(x, 180, 350, 220, PAPER, GREEN if hi else LINE, 3 if hi else 2, 8))
        out.append(T(x + 175, 260, side["title"], 40, GREEN if hi else INK, 700))
        out.append(f'<line x1="{x + 50}" y1="295" x2="{x + 300}" y2="295" stroke="{FAINT}" stroke-width="2"/>')
        for k, line in enumerate(side.get("note", "").split("|")):
            out.append(T(x + 175, 340 + k * 36, line, 26, SUB, 400))
    if d.get("caption"):
        out.append(T(440, 480, d["caption"], 28, SUB, 400))
    return out


def d_tags(d):
    """통장에 목표 이름표. items: [[통장, 목표], ...]"""
    out = []
    for i, (acct, goal) in enumerate(d["items"]):
        y = 30 + i * 150
        out.append(R(60, y, 300, 110, PAPER, LINE, 2, 8))
        out.append(T(210, y + 66, acct, 30, SUB, 500))
        out.append(f'<path d="M360 {y + 55} L470 {y + 55}" stroke="{LINE}" stroke-width="2" stroke-dasharray="6 6"/>')
        out.append(f'<path d="M480 {y + 15} L780 {y + 15} L820 {y + 55} L780 {y + 95} L480 {y + 95} Z" fill="{PAPER}" stroke="{GREEN}" stroke-width="2.5" stroke-linejoin="round"/>')
        out.append(f'<circle cx="782" cy="{y + 55}" r="7" fill="none" stroke="{GREEN}" stroke-width="2"/>')
        out.append(T(625, y + 67, goal, 32, GREEN, 700))
    return out


def d_steps(d):
    """계단 n칸. steps, caption."""
    steps = d["steps"]
    n = len(steps)
    bw = 240
    gap = 20
    out = [f'<line x1="0" y1="440" x2="880" y2="440" stroke="{LINE}" stroke-width="2"/>']
    for i, s in enumerate(steps):
        x = 40 + i * (bw + gap)
        h = 120 + i * 110
        last = i == n - 1
        out.append(R(x, 440 - h, bw, h, PAPER, GREEN if last else LINE, 3 if last else 2, 4))
        out.append(T(x + 30, 440 - h + 48, f"0{i + 1}", 22, GOLD, 700, "start"))
        out.append(T(x + bw / 2, 440 - h / 2 + 22, s, 34, GREEN if last else INK, 700))
    if d.get("caption"):
        out.append(T(440, 505, d["caption"], 28, SUB, 400))
    return out


def d_form(d):
    """적어 보는 양식. rows: [통장 이름 예시...], heads: [왼쪽, 오른쪽]"""
    heads = d.get("heads", ["내 통장", "이 돈의 목적"])
    out = [R(40, 20, 800, 460, PAPER, LINE, 2, 8),
           T(90, 80, heads[0], 26, SUB, 500, "start"), T(470, 80, heads[1], 26, SUB, 500, "start"),
           f'<line x1="70" y1="104" x2="810" y2="104" stroke="{INK}" stroke-width="2"/>']
    for i, row in enumerate(d["rows"]):
        y = 104 + (i + 1) * 88
        out.append(T(90, y - 30, row, 30, INK, 500, "start"))
        out.append(f'<line x1="470" y1="{y - 22}" x2="790" y2="{y - 22}" stroke="{LINE}" stroke-width="2" stroke-dasharray="3 7"/>')
        out.append(f'<line x1="70" y1="{y}" x2="810" y2="{y}" stroke="{FAINT}" stroke-width="2"/>')
    return out


def d_cover(d):
    """표지: 이름표가 빈 통장 세 개."""
    out = []
    for i in range(3):
        x = 70 + i * 260
        out.append(R(x, 90, 220, 280, PAPER, LINE, 2, 8))
        out.append(f'<line x1="{x + 30}" y1="150" x2="{x + 190}" y2="150" stroke="{FAINT}" stroke-width="10" stroke-linecap="round"/>')
        out.append(f'<line x1="{x + 30}" y1="185" x2="{x + 150}" y2="185" stroke="{FAINT}" stroke-width="10" stroke-linecap="round"/>')
        out.append(f'<path d="M{x + 110} 370 L{x + 110} 410" stroke="{LINE}" stroke-width="2"/>')
        out.append(R(x + 40, 410, 140, 54, PAPER, GREEN, 2, 27, "6 6"))
        out.append(T(x + 110, 446, "?", 28, GREEN, 700))
    return out


DIAGRAMS = {"boxes": d_boxes, "cycle": d_cycle, "split": d_split, "tags": d_tags,
            "steps": d_steps, "form": d_form, "cover": d_cover}

CSS = """
@font-face{font-family:K;src:url('FONTS/NotoSansKR-Regular.otf');font-weight:400}
@font-face{font-family:K;src:url('FONTS/NotoSansKR-Regular.otf');font-weight:500}
@font-face{font-family:K;src:url('FONTS/NotoSansKR-Bold.otf');font-weight:600 700}
@font-face{font-family:K;src:url('FONTS/NotoSansKR-Black.otf');font-weight:900}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;background:BG;font-family:K;color:INK;-webkit-font-smoothing:antialiased}
.card{position:absolute;inset:0;display:none}
.paper{position:absolute;left:56px;right:56px;top:56px;bottom:56px;background:PAPER;border-radius:4px}
.top{position:absolute;left:100px;right:100px;top:108px;display:flex;justify-content:space-between;align-items:center;
     font-size:24px;font-weight:500;color:SUB;letter-spacing:1px}
.top .series{display:flex;align-items:center;gap:14px}
.top .series:before{content:"";width:28px;height:3px;background:GREEN}
.top .num{font-weight:700;color:INK}
.top .num span{color:LINE;font-weight:400}
.head{position:absolute;left:100px;right:100px;top:205px;font-size:58px;line-height:1.38;font-weight:700;letter-spacing:-1.5px;word-break:keep-all}
.head em{font-style:normal;color:GREEN;box-shadow:inset 0 -14px 0 rgba(47,79,62,.12)}
.sub{position:absolute;left:100px;right:100px;font-size:31px;line-height:1.6;font-weight:400;color:SUB;word-break:keep-all}
.sub em{font-style:normal;color:INK;font-weight:700}
svg.dg{position:absolute;left:100px;width:880px;height:520px;font-family:K}
.foot{position:absolute;left:100px;right:280px;bottom:100px;font-size:20px;line-height:1.5;color:#8A949C}
.brand{position:absolute;right:100px;bottom:100px;font-size:22px;font-weight:700;color:GREEN;letter-spacing:1px}
.rule{position:absolute;left:100px;right:100px;bottom:150px;height:1px;background:#E3E8EC}
.cover .head{top:300px;font-size:92px;line-height:1.25;letter-spacing:-3px}
.cover .sub{font-size:34px}
"""


def page_html(spec):
    css = CSS.replace("FONTS", FONTS.as_uri())
    for k, v in dict(BG=BG, PAPER=PAPER, INK=INK, SUB=SUB, GREEN=GREEN, LINE=LINE).items():
        css = css.replace(k, v)
    n = len(spec["cards"])
    cards = []
    for i, c in enumerate(spec["cards"]):
        cover = c.get("cover")
        head_lines = c["head"].count("|") + 1
        head_h = head_lines * (92 * 1.25 if cover else 58 * 1.38)
        head_top = 300 if cover else 205
        sub_top = head_top + head_h + (40 if cover else 30)
        sub_lines = c.get("sub", "").count("|") + 1 if c.get("sub") else 0
        dg_top = c.get("dg_top") or int(sub_top + sub_lines * 31 * 1.6 + 50)
        dg = c.get("diagram")
        svg = ""
        if dg:
            if dg["type"] not in DIAGRAMS:
                raise SystemExit(f"도식 '{dg['type']}' 이 없습니다: {', '.join(DIAGRAMS)}")
            svg = (f'<svg class="dg" style="top:{dg_top}px" viewBox="0 0 880 520">'
                   + "".join(DIAGRAMS[dg["type"]](dg)) + "</svg>")
        foot = c.get("foot")
        foot = spec.get("foot", "") if foot is True else (foot or "")
        cards.append(
            f'<div class="card{" cover" if cover else ""}" data-i="{i}"><div class="paper"></div>'
            f'<div class="top"><div class="series">{esc(spec.get("series", ""))}</div>'
            f'<div class="num">{i + 1:02d} <span>/ {n:02d}</span></div></div>'
            f'<div class="head">{rich(c["head"])}</div>'
            + (f'<div class="sub" style="top:{sub_top:.0f}px">{rich(c["sub"])}</div>' if c.get("sub") else "")
            + svg
            + '<div class="rule"></div>'
            + (f'<div class="foot">{esc(foot)}</div>' if foot else "")
            + f'<div class="brand">{esc(spec.get("brand", "키움멘토"))}</div></div>')
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{"".join(cards)}</body></html>'


def render(spec, out_dir):
    from playwright.sync_api import sync_playwright
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with tempfile.TemporaryDirectory(prefix="procards-") as work, sync_playwright() as pw:
        b, _ = browser.launch(pw)
        try:
            page = b.new_page(viewport={"width": W, "height": H})
            f = Path(work) / "page.html"
            f.write_text(page_html(spec), encoding="utf-8")
            page.goto(f.as_uri())
            page.evaluate("document.fonts.ready")
            for i in range(len(spec["cards"])):
                page.evaluate("i => document.querySelectorAll('.card').forEach((c, k) => c.style.display = k === i ? 'block' : 'none')", i)
                p = out_dir / f"card_{i + 1}.png"
                page.screenshot(path=str(p))
                paths.append(p)
        finally:
            b.close()
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    for p in render(spec, a.out):
        print(p)


if __name__ == "__main__":
    main()
