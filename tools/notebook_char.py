#!/usr/bin/env python3
"""스프링 노트 + 키움멘토 캐릭터 시안(2026-11-04) 릴스·카드뉴스 생성기.

기존 tools/notebook.py(진한 초록 배경 스프링 노트, Poor Story 굵게, 형광펜)를 그대로 쓰고,
노트 아래쪽에 오리지널 캐릭터 '새싹 멘토'가 나와 그림을 가리키며 설명하는 형식을 더한다.
매일 자동 카드뉴스는 여전히 notebook.py 를 쓴다(이 시안은 사용자 승인 전까지 일정에 넣지 않는다).

    python3 tools/notebook_char.py reel  SPEC.json OUT.mp4
    python3 tools/notebook_char.py cards SPEC.json OUT_DIR

SPEC 은 notebook.py 와 같고, 장면마다 두 칸을 더 받는다.
    "pose": "point" | "think" | "cheer" | "worry"     (캐릭터 표정·손동작)
    "art":  ART 사전의 그림 이름                        (상황을 떠올리게 하는 간단한 그림)
"""

import argparse
import html
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notebook as nb  # noqa: E402
from reelkit import browser, constants  # noqa: E402
from reelkit.encode import EncodeError, PipeEncoder  # noqa: E402

FPS = nb.FPS
MIN_SCENE_S = 4.6      # 장면당 최소 4초 이상 (2026-10 사용자 피드백)

# ---------------------------------------------------------------- 캐릭터
INK = "#333"
SKIN = "#FFF3E4"
GREEN = "#2F4F3E"
LEAF = "#8CC56E"


def _arm(points, hand):
    """두꺼운 선 두 겹(외곽선+옷)으로 팔을 그리고 끝에 손을 단다."""
    d = "M" + " L".join(f"{x} {y}" for x, y in points)
    hx, hy = points[-1]
    return (f'<path d="{d}" stroke="{INK}" stroke-width="40" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" stroke="{GREEN}" stroke-width="28" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<g transform="translate({hx} {hy})">{hand}</g>')


HAND_OPEN = (f'<circle r="19" fill="{SKIN}" stroke="{INK}" stroke-width="5"/>'
             f'<path d="M10 -14 L24 -30" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>'
             f'<path d="M10 -14 L24 -30" stroke="{SKIN}" stroke-width="4" stroke-linecap="round"/>')
HAND_FIST = f'<circle r="19" fill="{SKIN}" stroke="{INK}" stroke-width="5"/>'
HAND_THUMB = (f'<circle r="19" fill="{SKIN}" stroke="{INK}" stroke-width="5"/>'
              f'<rect x="-7" y="-46" width="15" height="30" rx="7" fill="{SKIN}" stroke="{INK}" stroke-width="5"/>')

ARMS = {
    "point": _arm([(232, 300), (290, 262), (330, 236)], HAND_OPEN),
    "think": _arm([(232, 305), (262, 360), (206, 268)], HAND_FIST),
    "cheer": _arm([(232, 300), (282, 230), (296, 168)], HAND_THUMB),
    "worry": _arm([(232, 305), (286, 240), (262, 128)], HAND_FIST),
}
MOUTHS = {
    "point": f'<path d="M142 214 Q160 232 178 214" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>',
    "think": f'<path d="M148 218 L174 214" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>',
    "cheer": f'<path d="M138 208 Q160 246 182 208 Z" fill="#C8574F" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>',
    "worry": f'<path d="M140 220 Q150 210 160 220 Q170 230 180 220" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>',
}
EXTRAS = {
    "think": f'<text x="252" y="96" font-size="64" font-weight="700" fill="{INK}" font-family="Hand">?</text>',
    "worry": f'<path d="M58 118 Q46 140 58 150 Q70 140 58 118 Z" fill="#9CC9EE" stroke="{INK}" stroke-width="4"/>',
    "cheer": (f'<path d="M40 120 l10 -22 M22 150 l-22 -6 M30 186 l-20 10" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'),
    "point": "",
}


def character(pose):
    pose = pose if pose in ARMS else "point"
    left_arm = _arm([(88, 300), (70, 370), (84, 430)], HAND_FIST)
    return f'''<svg class="chr" viewBox="0 0 360 470" overflow="visible">
<g class="bob">
 <path d="M66 470 L76 312 Q86 258 160 252 Q234 258 244 312 L254 470 Z" fill="{GREEN}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
 <path d="M132 256 L160 330 L188 256 Z" fill="#fff" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
 <circle cx="150" cy="362" r="6" fill="#E9DFC6"/><circle cx="150" cy="402" r="6" fill="#E9DFC6"/><circle cx="150" cy="442" r="6" fill="#E9DFC6"/>
 {left_arm}
 <g class="head">
  <path d="M160 82 L160 46" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>
  <path d="M160 56 Q138 28 112 38 Q128 66 160 56 Z" fill="{LEAF}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
  <path d="M160 50 Q186 18 214 30 Q196 62 160 50 Z" fill="{LEAF}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
  <circle cx="160" cy="164" r="84" fill="{SKIN}" stroke="{INK}" stroke-width="6"/>
  <path d="M78 156 Q72 82 160 78 Q248 82 242 156 Q230 116 186 110 Q150 132 92 132 Z" fill="#3B3B3B" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
  <g class="eyes"><circle cx="128" cy="170" r="7" fill="{INK}"/><circle cx="192" cy="170" r="7" fill="{INK}"/></g>
  <circle cx="128" cy="168" r="24" fill="none" stroke="{INK}" stroke-width="5"/>
  <circle cx="192" cy="168" r="24" fill="none" stroke="{INK}" stroke-width="5"/>
  <path d="M152 166 Q160 160 168 166" fill="none" stroke="{INK}" stroke-width="5"/>
  <ellipse cx="104" cy="204" rx="11" ry="7" fill="#F2AE9C" opacity=".75"/>
  <ellipse cx="216" cy="204" rx="11" ry="7" fill="#F2AE9C" opacity=".75"/>
  {MOUTHS[pose]}
 </g>
 {ARMS[pose]}
 {EXTRAS[pose]}
</g></svg>'''


# ---------------------------------------------------------------- 상황 그림
# 그림 요소는 class="pp" 단위로 하나씩 '톡' 나타난다. viewBox 600x520.
def T(x, y, s, size=34, fill=INK, anchor="middle", weight=700):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" font-family="Hand">{html.escape(s)}</text>')


def box(x, y, w, h, fill="#fff", rx=16, sw=5):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>'


def coin(x, y, rx=34, ry=13):
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="#F4CF4C" stroke="{INK}" stroke-width="4"/>'


def arrow(x1, y1, x2, y2, color=GREEN, w=7):
    ang = math.atan2(y2 - y1, x2 - x1)
    a1 = (x2 - 22 * math.cos(ang - 0.5), y2 - 22 * math.sin(ang - 0.5))
    a2 = (x2 - 22 * math.cos(ang + 0.5), y2 - 22 * math.sin(ang + 0.5))
    return (f'<path d="M{x1} {y1} L{x2} {y2} M{a1[0]:.0f} {a1[1]:.0f} L{x2} {y2} L{a2[0]:.0f} {a2[1]:.0f}" '
            f'stroke="{color}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')


def g(*parts):
    return f'<g class="pp">{"".join(parts)}</g>'


def _jar(coins, label):
    out = [g(f'<path d="M170 120 L170 90 L430 90 L430 120 Q470 140 470 190 L470 450 Q470 480 440 480 L160 480 '
             f'Q130 480 130 450 L130 190 Q130 140 170 120 Z" fill="#EAF4F8" stroke="{INK}" stroke-width="6"/>',
             box(160, 70, 280, 40, "#C9D7CF", 10), box(215, 150, 170, 70, "#fff", 10), T(300, 197, label, 38))]
    for k in range(coins):
        out.append(g(coin(300 + (k % 2) * 40 - 20, 455 - k * 22, 90, 18)))
    return out


def _calendar(months, stacks, head=GREEN):
    out = [g(box(40, 70, 520, 380, "#fff", 10, 6), f'<rect x="40" y="70" width="520" height="62" fill="{head}" stroke="{INK}" stroke-width="6"/>',
             *[f'<path d="M{x} 52 L{x} 92" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>' for x in (150, 300, 450)])]
    w = 520 / len(months)
    for i, (m, n) in enumerate(zip(months, stacks)):
        x0 = 40 + i * w
        cx = x0 + w / 2
        out.append(g(f'<rect x="{x0 + 6:.0f}" y="140" width="{w - 12:.0f}" height="300" rx="6" fill="#F3F6FA" stroke="{INK}" stroke-width="4"/>',
                     T(cx, 182, m, 30), *[coin(cx, 420 - k * 26, w / 2 - 18, 12) for k in range(n)]))
    return out


ART = {
    # ---- 릴스: 월급이 사라지는 이유
    "empty": [g(box(180, 30, 240, 440, "#fff", 38, 6), box(200, 70, 200, 340, "#F3F6FA", 12, 4), f'<circle cx="300" cy="440" r="12" fill="none" stroke="{INK}" stroke-width="4"/>'),
              g(T(300, 120, "내 통장 잔액", 30, "#666")),
              g(T(300, 250, "텅~", 96, "#9A9A9A")),
              g('<circle cx="236" cy="340" r="14" fill="#ddd"/><circle cx="262" cy="350" r="10" fill="#ddd"/><circle cx="352" cy="336" r="12" fill="#ddd"/>'),
              g(T(500, 120, "!", 90, "#C8574F"), T(470, 200, "!", 60, "#C8574F"))],
    "outflow": [g(box(170, 20, 260, 110, "#E8F2EA", 18, 6), T(300, 90, "월급 통장", 44)),
                g(arrow(230, 140, 110, 300, "#C8574F"), arrow(300, 140, 300, 300, "#C8574F"), arrow(370, 140, 490, 300, "#C8574F")),
                g(box(20, 320, 180, 90, "#fff"), T(110, 378, "카드값", 38)),
                g(box(210, 320, 180, 90, "#fff"), T(300, 378, "관리비", 38)),
                g(box(400, 320, 180, 90, "#fff"), T(490, 378, "보험료", 38)),
                g(coin(160, 200, 22, 9), coin(440, 210, 22, 9), coin(330, 240, 22, 9))],
    "jar_low": _jar(1, "저축") + [g(T(520, 170, "?", 110, "#888")), g(T(70, 240, "?", 80, "#aaa"))],
    "order": [g(box(160, 10, 280, 96, "#E8F2EA", 18, 6), T(300, 72, "월급 입금", 44)),
              g(arrow(300, 116, 300, 180)),
              g(box(90, 190, 420, 120, "#FFF1A8", 20, 6), T(150, 264, "1", 54, GREEN), T(330, 266, "저축 통장 먼저", 48)),
              g(arrow(300, 320, 300, 384)),
              g(box(90, 394, 420, 110, "#fff", 20, 6), T(150, 462, "2", 54, "#888"), T(330, 464, "남은 돈으로 생활", 42))],
    "calendar": [g(T(300, 30, "자동이체 → 저축 통장", 34, GREEN))] + _calendar(["1월", "2월", "3월", "4월", "5월", "6월"], [1, 2, 3, 4, 5, 6]),
    "jar_full": _jar(9, "1년 뒤") + [g(box(380, 20, 210, 90, "#FFF1A8", 45, 5), T(485, 78, "360만 원", 40))],
    "sheet_reel": [g(box(110, 20, 380, 470, "#fff", 12, 6), T(300, 90, "내 월급 순서표", 42, GREEN)),
                   g(box(150, 140, 46, 46, "#fff", 8), T(340, 178, "월급 들어오는 날", 34, INK)),
                   g(box(150, 230, 46, 46, "#fff", 8), T(340, 268, "먼저 떼어 둘 돈", 34, INK)),
                   g(box(150, 320, 46, 46, "#fff", 8), T(340, 358, "한 달 생활비", 34, INK)),
                   g(f'<path d="M158 160 l14 16 l26 -34 M158 250 l14 16 l26 -34" stroke="{GREEN}" stroke-width="8" fill="none" stroke-linecap="round"/>'),
                   g(T(300, 450, "댓글로 받아 가세요", 32, "#888"))],
    # ---- 카드뉴스: 통장, 이렇게 나눠요
    "calendar_x": _calendar(["1월", "2월", "3월", "4월"], [0, 0, 0, 0], "#7C8E84")
                  + [g(*[f'<path d="M{x - 34} 260 L{x + 34} 330 M{x + 34} 260 L{x - 34} 330" stroke="#C8574F" stroke-width="9" stroke-linecap="round"/>' for x in (105, 235, 365)]),
                     g(box(425, 260, 130, 70, "#FFF1A8", 10), T(490, 306, "이번엔 꼭", 28))],
    "mixed": [g(box(70, 40, 460, 420, "#E8F2EA", 24, 6), T(300, 104, "통장 하나", 46)),
              g(box(110, 150, 150, 70, "#fff", 12), T(185, 196, "월세", 32)),
              g(box(320, 140, 170, 70, "#fff", 12), T(405, 186, "카드값", 32)),
              g(box(140, 270, 170, 70, "#fff", 12), T(225, 316, "저축?", 32)),
              g(box(350, 290, 150, 70, "#fff", 12), T(425, 336, "비상금", 32)),
              g(coin(270, 400, 26, 10), coin(380, 410, 26, 10), coin(180, 405, 26, 10)),
              g(T(560, 90, "?", 90, "#888"), T(40, 330, "?", 70, "#aaa"))],
    "four": [g(box(30, 40, 260, 200, "#E8F2EA", 22, 6), T(160, 130, "월급", 46), T(160, 190, "들어오는 곳", 30, "#666")),
             g(box(310, 40, 260, 200, "#FFF1A8", 22, 6), T(440, 130, "저축", 46), T(440, 190, "먼저 떼어 둠", 30, "#666")),
             g(box(30, 270, 260, 200, "#fff", 22, 6), T(160, 360, "생활비", 46), T(160, 420, "한 달 쓸 만큼", 30, "#666")),
             g(box(310, 270, 260, 200, "#E5EEF8", 22, 6), T(440, 360, "비상금", 46), T(440, 420, "갑자기 쓸 돈", 30, "#666"))],
    "station": [g(box(170, 20, 260, 130, "#E8F2EA", 18, 6), T(300, 80, "월급 통장", 44), T(300, 128, "잠깐 머무는 정거장", 28, "#666")),
                g(arrow(230, 160, 110, 320), arrow(300, 160, 300, 320), arrow(370, 160, 490, 320)),
                g(box(20, 340, 180, 90, "#FFF1A8"), T(110, 398, "저축", 40)),
                g(box(210, 340, 180, 90, "#fff"), T(300, 398, "생활비", 40)),
                g(box(400, 340, 180, 90, "#E5EEF8"), T(490, 398, "비상금", 40)),
                g(T(300, 490, "월급날 바로 나눠 보내기", 30, GREEN))],
    "card_gauge": [g(box(60, 40, 330, 210, "#5E8C74", 24, 6), box(90, 100, 64, 48, "#F4CF4C", 8, 4), T(330, 220, "체크카드", 30, "#fff", "end")),
                   g(T(300, 330, "이번 달 남은 생활비", 34, INK)),
                   g(box(60, 360, 480, 70, "#fff", 35, 6), f'<rect x="66" y="366" width="250" height="58" rx="29" fill="{LEAF}"/>'),
                   g(T(470, 480, "한눈에 보여요", 32, GREEN))],
    "umbrella": [g(*[f'<path d="M{x} {y} l-8 22" stroke="#9CC9EE" stroke-width="7" stroke-linecap="round"/>' for x, y in ((60, 40), (130, 90), (480, 50), (550, 110), (90, 170), (520, 180))]),
                 g(f'<path d="M110 230 Q300 20 490 230 Q440 200 395 230 Q350 200 300 230 Q250 200 205 230 Q160 200 110 230 Z" fill="{GREEN}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>',
                   f'<path d="M300 230 L300 420 Q300 450 270 450" stroke="{INK}" stroke-width="8" fill="none" stroke-linecap="round"/>'),
                 g(coin(400, 440, 50, 15), coin(400, 412, 50, 15), coin(400, 384, 50, 15), coin(400, 356, 50, 15)),
                 g(T(400, 320, "비상금", 34, INK)),
                 g(box(30, 300, 190, 70, "#fff", 12), T(125, 346, "갑자기!", 34, "#C8574F"))],
    "sheet_card": [g(box(110, 20, 380, 470, "#fff", 12, 6), T(300, 90, "통장 나누기 표", 42, GREEN)),
                   g(box(150, 140, 46, 46, "#fff", 8), T(340, 178, "월급 통장 정하기", 34)),
                   g(box(150, 230, 46, 46, "#fff", 8), T(340, 268, "저축 먼저 떼기", 34)),
                   g(box(150, 320, 46, 46, "#fff", 8), T(340, 358, "생활비 · 비상금", 34)),
                   g(f'<path d="M158 160 l14 16 l26 -34 M158 250 l14 16 l26 -34" stroke="{GREEN}" stroke-width="8" fill="none" stroke-linecap="round"/>'),
                   g(T(300, 450, "댓글로 받아 가세요", 32, "#888"))],
}

# ---------------------------------------------------------------- 레이아웃
LAYOUT = {
    "reel": dict(nb.LAYOUT["reel"], SY=104, TY=178, BY=318, BF=74, LH=1.45, TF=54,
                 AX=250, AY=500, AW=700, AH=607, CX=-10, CB=40, CW=470, FB=40),
    "card": dict(nb.LAYOUT["card"], SY=84, TY=150, BY=262, BF=60, LH=1.45, TF=56,
                 AX=320, AY=440, AW=560, AH=486, CX=-6, CB=30, CW=340, FB=26),
}

EXTRA_CSS = """
.body{right:60px}
.art{position:absolute;left:{AX}px;top:{AY}px;width:{AW}px;height:{AH}px;overflow:visible}
.chr{position:absolute;left:{CX}px;bottom:{CB}px;width:{CW}px;height:auto;overflow:visible}
.pp{transform-box:fill-box;transform-origin:center;opacity:0}
.foot{left:auto;right:130px}
"""


def page_html(spec, mode):
    L = LAYOUT[mode]
    base_layout = nb.LAYOUT[mode]
    nb.LAYOUT[mode] = L
    try:
        doc = nb.page_html(spec, mode)
    finally:
        nb.LAYOUT[mode] = base_layout
    css = EXTRA_CSS
    for k, v in L.items():
        css = css.replace("{" + k + "}", str(v))
    doc = doc.replace("</style>", css + "</style>")
    # 장면마다 그림·캐릭터를 끼워 넣는다 (장면 div 의 끝 바로 앞).
    for si, sc in enumerate(spec["scenes"]):
        art = sc.get("art")
        if art and art not in ART:
            raise nb.SpecError(f"그림 '{art}' 이 없습니다. 쓸 수 있는 그림: {', '.join(ART)}")
        art_svg = f'<svg class="art" viewBox="0 0 600 520">{"".join(ART[art])}</svg>' if art else ""
        marker = f'<div class="scene" data-s="{si}" style="display:none">'
        doc = doc.replace(marker, marker + art_svg + character(sc.get("pose", "point")), 1)
    return doc


SEEK_JS = nb.SEEK_JS.rstrip()[:-1] + """
  const el = args[3], t = args[4];
  sc.querySelectorAll('.pp').forEach((p, k) => {
    const f = Math.max(0, Math.min(1, (el - 0.25 - 0.32 * k) / 0.3));
    p.style.opacity = f;
    p.style.transform = 'scale(' + (0.8 + 0.2 * f) + ')';
  });
  const bob = sc.querySelector('.bob');
  if (bob) bob.setAttribute('transform', 'translate(0 ' + (Math.sin(t * 2.6) * 5).toFixed(2) + ')');
  const eyes = sc.querySelector('.eyes');
  if (eyes) { const ph = t % 3.4; eyes.setAttribute('transform', ph < 0.12 ? 'translate(0 152) scale(1 0.1)' : ''); }
}"""


def schedule(spec):
    out, t = [], 0.4
    base = nb.schedule(spec)
    for i, (s, te, me, e) in enumerate(base):
        dur = max(e - s, MIN_SCENE_S + (1.0 if i == len(base) - 1 else 0))
        out.append((t, t + (te - s), t + (me - s), t + dur))
        t = t + dur + nb.GAP_S
    return out


def _state(sch, t):
    si, typed, mark_p = nb._state(sch, t)
    el = t - sch[si][0] if si >= 0 else 0
    return [si, typed, mark_p, el, t]


def _open(pw, spec, mode, work):
    b, _ = browser.launch(pw)
    page = b.new_page(viewport={"width": 1080, "height": LAYOUT[mode]["H"]})
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
    with tempfile.TemporaryDirectory(prefix="nbchar-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, "reel", work)
        enc = PipeEncoder(out)
        try:
            for i in range(int(round(total * FPS))):
                page.evaluate(SEEK_JS, _state(sch, i / FPS))
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
    with tempfile.TemporaryDirectory(prefix="nbchar-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, "card", work)
        try:
            for si, _ in enumerate(spec["scenes"]):
                page.evaluate(SEEK_JS, [si, 10 ** 6, 99, 99, 0.6])
                p = out_dir / f"card_{si + 1}.png"
                page.screenshot(path=str(p))
                paths.append(p)
        finally:
            b.close()
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description="스프링 노트 + 캐릭터 시안 릴스(음악 없음)·카드뉴스 생성")
    ap.add_argument("mode", choices=["reel", "cards"])
    ap.add_argument("spec")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    try:
        spec = nb.load(a.spec)
        if a.mode == "reel":
            print(f"duration={render_reel(spec, a.out):.1f}s")
        else:
            for p in render_cards(spec, a.out):
                print(p)
    except nb.SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    except (browser.BrowserLaunchError, browser.FontLoadError, EncodeError) as e:
        print(f"환경 오류: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
