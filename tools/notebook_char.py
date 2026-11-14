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
HAIR = "#4A3A32"


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
    "wave": _arm([(232, 300), (284, 240), (300, 178)], HAND_OPEN),
}
MOUTHS = {
    "point": f'<path d="M142 214 Q160 232 178 214" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>',
    "think": f'<path d="M148 218 L174 214" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>',
    "cheer": f'<path d="M138 208 Q160 246 182 208 Z" fill="#C8574F" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>',
    "wave": f'<path d="M138 210 Q160 236 182 210" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>',
    "worry": f'<path d="M140 220 Q150 210 160 220 Q170 230 180 220" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>',
}
EXTRAS = {
    "think": f'<text x="252" y="96" font-size="64" font-weight="700" fill="{INK}" font-family="Hand">?</text>',
    "worry": f'<path d="M58 118 Q46 140 58 150 Q70 140 58 118 Z" fill="#9CC9EE" stroke="{INK}" stroke-width="4"/>',
    "cheer": (f'<path d="M40 120 l10 -22 M22 150 l-22 -6 M30 186 l-20 10" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'),
    "point": "",
    "wave": "",
}


def character(pose):
    pose = pose if pose in ARMS else "point"
    left_arm = _arm([(88, 300), (70, 370), (84, 430)], HAND_FIST)
    return f'''<svg class="chr" viewBox="0 0 360 470" overflow="visible">
<g class="bob">
 <path d="M66 176 Q54 72 160 64 Q266 72 254 176 Q262 236 270 262 Q236 276 206 258 L114 258 Q84 276 50 262 Q58 236 66 176 Z" fill="{HAIR}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
 <path d="M66 470 L76 312 Q86 258 160 252 Q234 258 244 312 L254 470 Z" fill="{GREEN}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
 <path d="M132 256 L160 330 L188 256 Z" fill="#fff" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
 <circle cx="150" cy="362" r="6" fill="#E9DFC6"/><circle cx="150" cy="402" r="6" fill="#E9DFC6"/><circle cx="150" cy="442" r="6" fill="#E9DFC6"/>
 {left_arm}
 <g class="head">
  <path d="M160 70 L160 40" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>
  <path d="M160 50 Q138 22 112 32 Q128 60 160 50 Z" fill="{LEAF}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
  <path d="M160 44 Q186 12 214 24 Q196 56 160 44 Z" fill="{LEAF}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
  <circle cx="160" cy="164" r="84" fill="{SKIN}" stroke="{INK}" stroke-width="6"/>
  <path d="M80 166 Q72 84 160 78 Q248 84 240 166 Q234 122 206 104 Q186 132 140 130 Q118 118 108 112 Q88 132 80 166 Z" fill="{HAIR}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>
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
    # ---- 카드뉴스: 연말 전 연금계좌 세액공제 (2026-11-05)
    "tax_back": [g(box(150, 20, 300, 470, "#fff", 10, 6), T(300, 86, "연말정산 결과", 40, GREEN)),
                 g(f'<path d="M180 120 L420 120" stroke="{INK}" stroke-width="4" stroke-dasharray="10 8"/>'),
                 g(T(300, 200, "환급?", 40, "#9A9A9A")),
                 g(box(180, 250, 240, 90, "#FBE3E0", 14, 5), T(300, 308, "추가 납부", 42, "#C8574F")),
                 g(T(300, 420, "토해냄...", 40, INK)),
                 g(T(520, 200, "!", 100, "#C8574F"))],
    "pension_zero": [g(box(40, 80, 240, 300, "#E8F2EA", 22, 6), T(160, 160, "연금저축", 42)),
                     g(box(320, 80, 240, 300, "#E5EEF8", 22, 6), T(440, 160, "IRP", 46)),
                     g(T(160, 290, "0원", 64, "#9A9A9A"), T(440, 290, "0원", 64, "#9A9A9A")),
                     g(T(300, 460, "1년 내내 비어 있었어요", 34, "#666"))],
    "refund": [g(box(150, 20, 300, 120, "#E8F2EA", 18, 6), T(300, 76, "연금저축·IRP", 40), T(300, 120, "내 노후로 넣은 돈", 28, "#666")),
               g(arrow(300, 150, 300, 260)),
               g(box(110, 270, 380, 120, "#FFF1A8", 20, 6), T(300, 345, "세금에서 돌려받기", 44)),
               g(coin(170, 450, 40, 14), coin(300, 460, 40, 14), coin(430, 450, 40, 14))],
    "rate": [g(T(300, 50, "총급여 기준 공제율", 36, GREEN)),
             g(box(40, 90, 250, 380, "#fff", 18, 6), f'<rect x="80" y="230" width="170" height="210" rx="10" fill="{LEAF}" stroke="{INK}" stroke-width="4"/>',
               T(165, 200, "16.5%", 56), T(165, 140, "5,500만 이하", 28, "#666")),
             g(box(310, 90, 250, 380, "#fff", 18, 6), f'<rect x="350" y="280" width="170" height="160" rx="10" fill="#C9D7CF" stroke="{INK}" stroke-width="4"/>',
               T(435, 250, "13.2%", 56), T(435, 140, "5,500만 초과", 28, "#666"))],
    "limit": [g(box(70, 300, 460, 150, "#E8F2EA", 18, 6), T(300, 385, "연금저축 600만", 44)),
              g(box(70, 160, 460, 120, "#E5EEF8", 18, 6), T(300, 232, "+ IRP 300만", 44)),
              g(box(120, 30, 360, 100, "#FFF1A8", 50, 6), T(300, 96, "합계 900만 원", 46)),
              g(T(300, 500, "1년 납입 기준", 30, "#666"))],
    "example": [g(box(50, 150, 220, 160, "#fff", 18, 6), T(160, 220, "넣은 돈", 32, "#666"), T(160, 280, "100만 원", 44)),
                g(arrow(285, 230, 345, 230)),
                g(box(355, 130, 210, 200, "#FFF1A8", 18, 6), T(460, 200, "돌려받는 돈", 30, "#666"), T(460, 270, "16.5만 원", 44)),
                g(coin(420, 400, 44, 15), coin(420, 372, 44, 15), coin(500, 410, 44, 15)),
                g(T(160, 420, "예시(가정)", 30, "#888"))],
    "deadline": [g(box(150, 40, 300, 340, "#fff", 14, 6), f'<rect x="150" y="40" width="300" height="80" fill="#C8574F" stroke="{INK}" stroke-width="6"/>',
                   T(300, 96, "12월", 44, "#fff")),
                 g(T(300, 290, "31", 150, INK)),
                 g(box(110, 410, 380, 80, "#FFF1A8", 40, 5), T(300, 464, "여기까지 넣은 돈만", 36))],
    "caution": [g(box(80, 40, 440, 140, "#E8F2EA", 18, 6), T(300, 100, "연금저축·IRP", 40), T(300, 150, "55세 전에 깨면?", 34, "#666")),
                g(arrow(300, 190, 300, 280, "#C8574F")),
                g(box(80, 290, 440, 130, "#FBE3E0", 18, 6), T(300, 368, "공제받은 세금 다시", 42, "#C8574F")),
                g(T(300, 480, "끝까지 둘 돈만 넣기", 34, GREEN))],
    "check_app": [g(box(190, 20, 220, 440, "#fff", 34, 6), box(208, 70, 184, 320, "#F3F6FA", 10, 4)),
                  g(T(300, 130, "올해 납입액", 30, GREEN)),
                  g(box(222, 160, 156, 60, "#E8F2EA", 10, 4), T(300, 200, "연금저축", 28)),
                  g(box(222, 240, 156, 60, "#E5EEF8", 10, 4), T(300, 280, "IRP", 30)),
                  g(f'<path d="M232 340 l18 20 l34 -44" stroke="{GREEN}" stroke-width="9" fill="none" stroke-linecap="round"/>'),
                  g(T(480, 180, "?", 90, "#888"))],

    # ---- 릴스: 2층 퇴직연금, 누가 굴리나 (2026-11-05)
    "app_open": [g(box(190, 20, 220, 440, "#fff", 34, 6), box(208, 70, 184, 320, "#F3F6FA", 10, 4)),
                 g(T(300, 130, "퇴직연금", 34, GREEN)),
                 g(box(222, 170, 156, 80, "#E8F2EA", 10, 4), T(300, 222, "적립금", 32)),
                 g(T(300, 320, "처음 열어 봄", 26, "#666")),
                 g(T(480, 160, "!", 90, "#C8574F"), T(110, 200, "7년차", 40, INK))],
    "db_dc_q": [g(box(50, 120, 220, 220, "#E8F2EA", 22, 6), T(160, 250, "DB형", 60)),
                g(box(330, 120, 220, 220, "#E5EEF8", 22, 6), T(440, 250, "DC형", 60)),
                g(T(300, 80, "내 건 뭐지?", 40, INK)),
                g(T(300, 450, "?", 120, "#888"))],
    "db": [g(box(150, 20, 300, 120, "#E8F2EA", 18, 6), T(300, 96, "회사", 54)),
           g(arrow(300, 150, 300, 240)),
           g(box(60, 250, 480, 120, "#fff", 18, 6), T(300, 300, "평균임금 30일분", 36), T(300, 348, "× 근속연수", 36)),
           g(box(170, 400, 260, 90, "#FFF1A8", 45, 5), T(300, 458, "받을 돈 정해짐", 32))],
    "dc": [g(box(150, 20, 300, 120, "#E5EEF8", 18, 6), T(300, 96, "나", 60)),
           g(arrow(300, 150, 300, 230)),
           g(box(100, 240, 400, 110, "#fff", 18, 6), T(300, 308, "어디에 굴릴지 선택", 36)),
           g(arrow(260, 360, 230, 440, GREEN), arrow(400, 360, 460, 440, "#C8574F")),
           g(T(230, 495, "늘 수도", 34, GREEN), T(470, 495, "줄 수도", 34, "#C8574F"))],
    "dc_idle": _calendar(["1년", "3년", "5년", "7년"], [2, 2, 2, 2], "#7C8E84")
               + [g(box(150, 230, 300, 80, "#FFF1A8", 40, 5), T(300, 284, "그대로...", 40)),
                  g(T(520, 40, "zZ", 48, "#888"))],
    "irp_move": [g(box(30, 60, 220, 120, "#E8F2EA", 18, 6), T(140, 136, "다니던 회사", 32)),
                 g(box(350, 60, 220, 120, "#fff", 18, 6), T(460, 136, "새 회사", 34)),
                 g(arrow(260, 120, 340, 120)),
                 g(arrow(140, 190, 300, 320)),
                 g(box(170, 330, 260, 120, "#FFF1A8", 22, 6), T(300, 405, "IRP 계좌", 46)),
                 g(T(300, 500, "55세 전 퇴직금은 여기로", 30, GREEN))],
    "check_type": [g(box(190, 20, 220, 440, "#fff", 34, 6), box(208, 70, 184, 320, "#F3F6FA", 10, 4)),
                   g(T(300, 130, "내 퇴직연금", 30, GREEN)),
                   g(box(222, 160, 156, 60, "#E8F2EA", 10, 4), T(300, 200, "DB형", 30)),
                   g(box(222, 240, 156, 60, "#E5EEF8", 10, 4), T(300, 280, "DC형", 30)),
                   g(f'<path d="M232 340 l18 20 l34 -44" stroke="{GREEN}" stroke-width="9" fill="none" stroke-linecap="round"/>'),
                   g(T(490, 170, "확인!", 40, GREEN))],

    # ---- 카드뉴스: 국민연금 당길까 미룰까 (2026-11-06)
    "friend_talk": [g(box(60, 40, 480, 170, "#fff", 40, 6), f'<path d="M150 205 L130 270 L220 208" fill="#fff" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>',
                      T(300, 115, "연금은 빨리", 44), T(300, 170, "받는 게 이득!", 44, "#C8574F")),
                    g(T(420, 380, "정말?", 70, GREEN)),
                    g(T(220, 400, "?", 100, "#888"))],
    "early": [g(T(300, 50, "앞당겨 받으면", 38, INK)),
              *[g(f'<rect x="{70 + i * 95}" y="{120 + i * 40}" width="70" height="{300 - i * 40}" rx="8" fill="#F4B9B2" stroke="{INK}" stroke-width="4"/>',
                  T(105 + i * 95, 465, f"{i}년", 28)) for i in range(6)],
              g(box(330, 70, 230, 80, "#FBE3E0", 40, 5), T(445, 124, "-30%", 46, "#C8574F"))],
    "late": [g(T(300, 50, "미뤄 받으면", 38, INK)),
             *[g(f'<rect x="{70 + i * 95}" y="{320 - i * 40}" width="70" height="{100 + i * 40}" rx="8" fill="{LEAF}" stroke="{INK}" stroke-width="4"/>',
                 T(105 + i * 95, 465, f"{i}년", 28)) for i in range(6)],
             g(box(40, 90, 230, 80, "#E8F2EA", 40, 5), T(155, 144, "+36%", 46, GREEN))],
    "lifetime": [g(box(40, 120, 520, 140, "#fff", 18, 6), T(300, 205, "매달 받는 금액", 42)),
                 g(arrow(80, 330, 520, 330, GREEN, 9)),
                 g(T(120, 400, "60대", 34), T(300, 400, "70대", 34), T(480, 400, "80대", 34)),
                 g(box(150, 440, 300, 70, "#FFF1A8", 35, 5), T(300, 488, "평생 그대로", 36))],
    "three_check": [g(box(60, 40, 480, 120, "#E8F2EA", 18, 6), T(140, 116, "①", 50, GREEN), T(340, 116, "내 건강", 44)),
                    g(box(60, 190, 480, 120, "#fff", 18, 6), T(140, 266, "②", 50, GREEN), T(340, 266, "다른 소득", 44)),
                    g(box(60, 340, 480, 120, "#E5EEF8", 18, 6), T(140, 416, "③", 50, GREEN), T(340, 416, "건보료", 44))],
    "calc": [g(box(150, 20, 300, 460, "#fff", 26, 6), box(175, 50, 250, 100, "#E8F2EA", 10, 4), T(400, 118, "내 예상액", 32, INK, "end")),
             g(box(175, 180, 115, 110, "#FBE3E0", 12, 4), T(232, 250, "×0.7", 38, "#C8574F")),
             g(box(310, 180, 115, 110, "#E8F2EA", 12, 4), T(367, 250, "×1.36", 34, GREEN)),
             g(T(232, 340, "당기면", 28, "#666"), T(367, 340, "미루면", 28, "#666")),
             g(T(300, 430, "직접 계산!", 36, GREEN))],

    "choose_time": [g(box(200, 60, 200, 130, "#FFF1A8", 18, 6), T(300, 120, "정해진", 36), T(300, 168, "나이", 36)),
                    g(arrow(190, 125, 70, 125, "#C8574F"), arrow(410, 125, 530, 125, GREEN)),
                    g(box(30, 240, 250, 150, "#FBE3E0", 18, 6), T(155, 305, "당기기", 42, "#C8574F"), T(155, 360, "최대 5년", 32)),
                    g(box(320, 240, 250, 150, "#E8F2EA", 18, 6), T(445, 305, "미루기", 42, GREEN), T(445, 360, "최대 5년", 32)),
                    g(T(300, 470, "내가 고를 수 있어요", 34, INK))],

    # ---- 릴스: 할부가 월급을 먼저 쓴다 (2026-11-06)
    "card_bills": [g(box(190, 80, 220, 420, "#fff", 34, 6), box(208, 120, 184, 350, "#F3F6FA", 10, 4), T(300, 160, "할부 내역", 30, GREEN)),
                   *[g(box(222, 180 + k * 46, 156, 36, "#FBE3E0", 8, 3), T(300, 206 + k * 46, f"할부 {k + 1}", 24, "#C8574F")) for k in range(6)],
                   g(T(490, 220, "6개?!", 46, "#C8574F"))],
    "installment_stack": [*[g(box(150, 420 - k * 62, 300, 52, ["#FBE3E0", "#FFF1A8", "#E5EEF8", "#E8F2EA", "#FBE3E0", "#FFF1A8"][k], 10, 4),
                             T(300, 456 - k * 62, ["폰", "가전", "옷", "여행", "운동", "선물"][k], 28)) for k in range(6)],
                          g(box(380, 20, 200, 80, "#FFF1A8", 40, 5), T(480, 72, "월 40만", 38))],
    "calendar_used": _calendar(["다음 달", "그다음", "또 다음"], [3, 2, 2], "#7C8E84")
                     + [g(box(130, 220, 340, 80, "#FBE3E0", 40, 5), T(300, 274, "이미 쓴 월급", 38, "#C8574F"))],
    "list_paper": [g(box(130, 80, 340, 420, "#fff", 10, 6), T(300, 136, "내 할부 목록", 40, GREEN)),
                   g(T(300, 200, "폰 · 남은 8개월", 32)),
                   g(T(300, 262, "가전 · 남은 5개월", 32)),
                   g(T(300, 324, "옷 · 남은 2개월", 32)),
                   g(T(300, 386, "여행 · 남은 3개월", 32)),
                   g(f'<path d="M170 420 L430 420" stroke="{GREEN}" stroke-width="6" stroke-dasharray="12 8"/>', T(300, 470, "끝나는 달 표시", 30, "#666"))],
    "stop_sign": [g(f'<polygon points="230,60 370,60 470,160 470,300 370,400 230,400 130,300 130,160" fill="#C8574F" stroke="{INK}" stroke-width="6"/>'),
                  g(T(300, 220, "새 할부", 50, "#fff"), T(300, 290, "멈춤", 58, "#fff")),
                  g(T(300, 480, "끝날 때까지만", 34, GREEN))],
    "to_savings": [g(box(40, 60, 230, 130, "#FBE3E0", 18, 6), T(155, 120, "끝난 할부", 36), T(155, 168, "월 10만", 30, "#666")),
                   g(arrow(280, 125, 340, 125)),
                   g(box(350, 60, 220, 130, "#FFF1A8", 18, 6), T(460, 120, "저축 통장", 36), T(460, 168, "월 10만", 30, "#666"))]
                  + [g(coin(460, 300, 70, 18), coin(460, 270, 70, 18)), g(coin(460, 240, 70, 18), coin(460, 210, 70, 18)),
                     g(box(120, 360, 360, 90, "#E8F2EA", 45, 5), T(300, 418, "다달이 차곡차곡", 38, GREEN))],
    "installment_app": [g(box(190, 20, 220, 440, "#fff", 34, 6), box(208, 70, 184, 320, "#F3F6FA", 10, 4)),
                        g(T(300, 130, "할부 내역", 32, GREEN)),
                        g(box(222, 160, 156, 60, "#E8F2EA", 10, 4), T(300, 200, "남은 개월", 30)),
                        g(box(222, 240, 156, 60, "#FFF1A8", 10, 4), T(300, 280, "월 합계", 30)),
                        g(f'<path d="M232 340 l18 20 l34 -44" stroke="{GREEN}" stroke-width="9" fill="none" stroke-linecap="round"/>'),
                        g(T(490, 170, "확인!", 40, GREEN))],

    # ---- 카드뉴스: 비상금 따로 두기 (2026-11-07)
    "sudden_bill": [g(box(100, 80, 400, 300, "#fff", 14, 6), T(300, 140, "수리 견적서", 40, GREEN)),
                    g(f'<path d="M140 170 L460 170" stroke="{INK}" stroke-width="4" stroke-dasharray="10 8"/>', T(300, 240, "차량 수리", 34, "#666")),
                    g(box(150, 280, 300, 80, "#FBE3E0", 12, 5), T(300, 334, "200만 원", 46, "#C8574F")),
                    g(T(530, 160, "!", 110, "#C8574F")),
                    g(T(300, 470, "갑자기...", 40, INK))],
    "broken_jar": [g(f'<path d="M170 140 Q130 160 130 210 L130 450 Q130 480 160 480 L440 480 Q470 480 470 450 L470 210 Q470 160 430 140 Z" fill="#EAF4F8" stroke="{INK}" stroke-width="6"/>',
                     box(215, 190, 170, 70, "#fff", 10), T(300, 237, "적금", 38)),
                   g(f'<path d="M300 140 L270 230 L320 300 L280 400" stroke="#C8574F" stroke-width="8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'),
                   g(coin(530, 440, 40, 14), coin(70, 450, 40, 14)),
                   g(box(360, 40, 220, 80, "#FBE3E0", 40, 5), T(470, 94, "이자 ↓", 40, "#C8574F"))],
    "months_box": [g(T(300, 50, "한 달 생활비 ×", 38, INK)),
                   *[g(box(30 + i * 92, 120, 80, 250, "#FFF1A8" if i < 3 else "#E8F2EA", 12, 5), T(70 + i * 92, 260, f"{i + 1}", 44)) for i in range(6)],
                   g(box(30, 400, 268, 80, "#FFF1A8", 40, 5), T(164, 454, "최소 3개월", 34)),
                   g(box(310, 400, 260, 80, "#E8F2EA", 40, 5), T(440, 454, "넉넉히 6개월", 34))],
    "free_account": [g(box(80, 60, 440, 220, "#E8F2EA", 24, 6), T(300, 140, "비상금 통장", 46), T(300, 210, "언제든 꺼내 쓰기", 32, "#666")),
                     g(arrow(180, 300, 180, 410, GREEN), arrow(420, 410, 420, 300, "#C8574F")),
                     g(T(180, 460, "넣고", 36, GREEN), T(420, 460, "빼고", 36, "#C8574F"))],
    "fill_steps": [*[g(box(60 + i * 125, 400 - i * 80, 110, 80 + i * 80, LEAF if i < 3 else "#C9D7CF", 10, 5), T(115 + i * 125, 475, f"{i + 1}달", 28)) for i in range(4)],
                   g(box(300, 40, 260, 80, "#FFF1A8", 40, 5), T(430, 94, "매달 조금씩", 36))],
    "calc_note": [g(box(130, 30, 340, 460, "#fff", 10, 6), T(300, 90, "우리 집 비상금", 38, GREEN)),
                  g(T(300, 180, "한 달 생활비", 32, "#666"), box(180, 200, 240, 60, "#F3F6FA", 8, 4), T(300, 242, "____만 원", 34)),
                  g(T(300, 320, "× 3 =", 46, INK)),
                  g(box(180, 350, 240, 70, "#FFF1A8", 10, 5), T(300, 398, "____만 원", 36)),
                  g(T(300, 465, "목표 금액", 30, GREEN))],

    # ---- 릴스: 연봉 오른 만큼 저축도 (2026-11-07)
    "raise_same": [g(box(40, 80, 240, 160, "#E8F2EA", 18, 6), T(160, 150, "연봉", 40), T(160, 210, "↑ 올랐다!", 34, GREEN)),
                   g(box(320, 80, 240, 160, "#fff", 18, 6), T(440, 150, "통장", 40), T(440, 210, "그대로...", 34, "#9A9A9A")),
                   g(T(300, 360, "?", 120, "#888"))],
    "raise_vanish": [g(box(150, 40, 300, 110, "#FFF1A8", 18, 6), T(300, 110, "월 +20만 원", 44)),
                     g(arrow(220, 170, 110, 300, "#C8574F"), arrow(300, 170, 300, 300, "#C8574F"), arrow(380, 170, 490, 300, "#C8574F")),
                     g(T(100, 350, "외식", 36), T(300, 350, "쇼핑", 36), T(500, 350, "구독", 36)),
                     g(T(300, 470, "어디 갔지?", 40, "#666"))],
    "lifestyle_up": [*[g(f'<rect x="{90 + i * 110}" y="{420 - h}" width="80" height="{h}" rx="8" fill="#F4B9B2" stroke="{INK}" stroke-width="4"/>') for i, h in enumerate((120, 180, 240, 300))],
                     g(arrow(90, 380, 500, 120, "#C8574F")),
                     g(T(300, 480, "버는 만큼 쓰는 생활", 34, INK))],
    "half_split": [g(box(150, 30, 300, 110, "#FFF1A8", 18, 6), T(300, 100, "인상분 20만", 42)),
                   g(arrow(240, 150, 140, 260), arrow(360, 150, 460, 260)),
                   g(box(30, 270, 240, 140, "#E8F2EA", 18, 6), T(150, 330, "먼저 저축", 36), T(150, 380, "10만", 40, GREEN)),
                   g(box(330, 270, 240, 140, "#fff", 18, 6), T(450, 330, "나머지", 36), T(450, 380, "10만", 40)),
                   g(T(300, 480, "반반으로", 36, GREEN))],
    "two_jars": _jar(3, "저축")[:1] + [g(coin(300, 455, 90, 18), coin(300, 433, 90, 18)),
                g(box(400, 20, 190, 80, "#E8F2EA", 40, 5), T(495, 72, "10만", 38, GREEN)),
                g(T(80, 120, "나를 위한", 28, "#666"), T(80, 160, "10만", 36))],
    "jar_120": _jar(6, "1년 뒤") + [g(box(380, 20, 210, 90, "#FFF1A8", 45, 5), T(485, 78, "120만 원", 40))],
    "auto_up": [g(box(190, 20, 220, 440, "#fff", 34, 6), box(208, 70, 184, 320, "#F3F6FA", 10, 4)),
                g(T(300, 130, "자동이체", 32, GREEN)),
                g(box(222, 160, 156, 60, "#fff", 10, 4), T(300, 200, "30만", 32, "#9A9A9A")),
                g(arrow(300, 230, 300, 270)),
                g(box(222, 280, 156, 60, "#FFF1A8", 10, 4), T(300, 320, "40만", 34)),
                g(T(490, 200, "+10만", 40, GREEN))],

    # 11/8 카드: 일요일 밤 10분 돈 점검
    "sunday_night": [g('<circle cx="470" cy="110" r="52" fill="#F4CF4C" stroke="#1F2A24" stroke-width="5"/>',
                       '<circle cx="492" cy="96" r="46" fill="#FBF7EC"/>', T(300, 120, "일요일 밤", 40, GREEN)),
                     g(box(220, 170, 190, 300, "#fff", 30, 6), box(238, 215, 154, 190, "#F3F6FA", 8, 4)),
                     g(T(315, 280, "잔액", 32, "#666"), T(315, 350, "???", 50, "#C8574F"))],
    "month_end": [g(box(150, 70, 360, 320, "#fff", 10, 6), '<rect x="150" y="70" width="360" height="62" fill="#C8574F" stroke="#1F2A24" stroke-width="6"/>',
                    T(330, 116, "월말", 36, "#fff")),
                  g(T(330, 270, "30일", 90, INK)),
                  g(T(330, 450, "이제야 확인...", 38, "#C8574F"))],
    "timer_10": [g('<circle cx="330" cy="250" r="170" fill="#fff" stroke="#1F2A24" stroke-width="7"/>',
                   '<path d="M330 250 L330 80 A170 170 0 0 1 477 165 Z" fill="#CFE8A9" stroke="#1F2A24" stroke-width="4"/>'),
                 g('<path d="M330 250 L330 120 M330 250 L420 200" stroke="#1F2A24" stroke-width="9" stroke-linecap="round"/>'),
                 g(box(250, 440, 160, 64, "#FFF1A8", 14, 5), T(330, 484, "딱 10분", 34))],
    "week_note": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 116, "지난주 쓴 돈", 36, GREEN)),
                  g(T(200, 190, "식비", 32, INK, "start"), T(460, 190, "△", 32, "#666", "end")),
                  g(T(200, 260, "배달", 32, INK, "start"), T(460, 260, "▲", 32, "#C8574F", "end")),
                  g(T(200, 330, "경조사", 32, INK, "start"), T(460, 330, "○", 32, GREEN, "end")),
                  g('<path d="M200 400 L460 400" stroke="#F4CF4C" stroke-width="22" stroke-linecap="round" opacity=".7"/>',
                    T(330, 412, "한 줄이면 충분", 32))],
    "week_mark": [g(box(60, 120, 520, 200, "#fff", 10, 6),
                    *[T(60 + 520 / 7 * (i + .5), 175, d, 32, GREEN) for i, d in enumerate("월화수목금토일")],
                    *[f'<path d="M{60 + 520 / 7 * i:.0f} 200 L{60 + 520 / 7 * i:.0f} 320" stroke="#1F2A24" stroke-width="3"/>' for i in range(1, 7)]),
                  g('<circle cx="357" cy="262" r="34" fill="none" stroke="#C8574F" stroke-width="7"/>'),
                  g(arrow(357, 380, 357, 304, "#C8574F"), box(250, 390, 214, 76, "#FBE3E0", 14, 5), T(357, 440, "결혼식 축의금", 30))],
    "week_budget": [g(box(150, 90, 360, 230, "#E8F2EA", 26, 6), T(330, 160, "이번 주 생활비", 36, GREEN)),
                    g(T(330, 260, "15만 원", 64, INK)),
                    g(box(170, 360, 320, 70, "#fff", 14, 5), '<rect x="174" y="364" width="190" height="62" rx="10" fill="#CFE8A9"/>',
                      T(330, 408, "남은 돈 보며 쓰기", 30))],
    "sunday_check": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "일요일 10분", 36, GREEN)),
                     *[g(box(200, 160 + i * 95, 48, 48, "#fff", 8, 5),
                         '<path d="M{0} {1} l12 14 l24 -30" stroke="#2F4F3E" stroke-width="7" fill="none" stroke-linecap="round"/>'.format(208, 186 + i * 95),
                         T(270, 197 + i * 95, t, 32, INK, "start")) for i, t in enumerate(["지난주 돌아보기", "큰 지출 표시", "주간 한도 정하기"])]],

    # 11/8 릴스: 내 보험, 뭐가 있는지 몰랐어요
    "ins_auto": [g(box(170, 70, 320, 400, "#fff", 10, 6), T(330, 126, "이번 달 출금", 36, GREEN)),
                 *[g(T(200, 200 + i * 70, f"보험료 {c}", 32, INK, "start"), T(460, 200 + i * 70, "-", 34, "#C8574F", "end"))
                   for i, c in enumerate("ABC")],
                 g(T(330, 430, "이게 다 뭐였지?", 34, "#C8574F"))],
    "ins_pile": [g(box(230, 300, 240, 150, "#fff", 8, 5), T(350, 385, "가입 안내서", 30)),
                 g(box(215, 210, 240, 150, "#F3F6FA", 8, 5), T(335, 295, "설명서", 30)),
                 g(box(200, 120, 240, 150, "#FFF1A8", 8, 5), T(320, 205, "\"꼭 필요해요\"", 30)),
                 g(T(470, 110, "?", 70, GREEN))],
    "ins_overlap": [g('<circle cx="270" cy="240" r="140" fill="#E5EEF8" fill-opacity=".85" stroke="#1F2A24" stroke-width="6"/>', T(220, 180, "보험 A", 32)),
                    g('<circle cx="420" cy="240" r="140" fill="#E8F2EA" fill-opacity=".85" stroke="#1F2A24" stroke-width="6"/>', T(470, 180, "보험 B", 32)),
                    g('<path d="M345 125 A140 140 0 0 1 345 355 A140 140 0 0 1 345 125 Z" fill="#FFF1A8" stroke="#1F2A24" stroke-width="4"/>', T(345, 250, "겹침", 34, "#C8574F")),
                    g(T(345, 450, "같은 보장, 두 번", 36))],
    "ins_gap": [g(box(170, 80, 320, 380, "#fff", 10, 6), T(330, 136, "내 보장 점검", 36, GREEN)),
                g(T(200, 210, "입원", 32, INK, "start"), T(460, 210, "✓ ✓", 32, GREEN, "end")),
                g(T(200, 290, "수술", 32, INK, "start"), T(460, 290, "✓ ✓", 32, GREEN, "end")),
                g(T(200, 370, "큰 병", 32, INK, "start"), box(370, 335, 90, 50, "#FBE3E0", 8, 4), T(415, 370, "?", 34, "#C8574F"))],
    "ins_one_page": [g(box(150, 70, 360, 400, "#fff", 10, 6), T(330, 126, "내 보험 한 장", 36, GREEN)),
                     g('<path d="M170 160 L490 160 M170 230 L490 230 M170 300 L490 300 M170 370 L490 370 M300 160 L300 370" stroke="#1F2A24" stroke-width="3"/>',
                       T(235, 202, "보장", 28, "#666"), T(395, 202, "보험료", 28, "#666")),
                     g(T(235, 272, "입원", 30), T(395, 272, "월 ○만", 30)),
                     g(T(235, 342, "수술", 30), T(395, 342, "월 ○만", 30)),
                     g('<path d="M180 412 L480 412" stroke="#CFE8A9" stroke-width="26" stroke-linecap="round"/>', T(330, 422, "겹침·빈칸 표시", 30))],
    "ins_careful": [g(box(150, 70, 360, 330, "#FBE3E0", 18, 6), T(330, 130, "해지 전에 확인", 36, "#C8574F")),
                    g(T(180, 210, "① 돌려받는 돈", 32, INK, "start")),
                    g(T(180, 280, "② 다시 가입 가능?", 32, INK, "start")),
                    g(T(180, 350, "③ 대신할 보장", 32, INK, "start")),
                    g(box(230, 420, 200, 64, "#FFF1A8", 14, 5), T(330, 464, "서두르지 않기", 30))],
    "ins_lookup": [g(box(210, 40, 220, 440, "#fff", 34, 6), box(228, 90, 184, 320, "#F3F6FA", 10, 4)),
                   g(box(242, 120, 156, 56, "#fff", 26, 4), T(320, 158, "내 보험 조회", 24, GREEN)),
                   g(box(242, 200, 156, 50, "#E8F2EA", 8, 3), T(320, 234, "보험 A", 26)),
                   g(box(242, 264, 156, 50, "#E5EEF8", 8, 3), T(320, 298, "보험 B", 26)),
                   g(box(242, 328, 156, 50, "#FFF1A8", 8, 3), T(320, 362, "보험 C", 26))],

    # 11/9 카드: 금리인하요구권
    "loan_same": [g(box(150, 80, 170, 160, "#E8F2EA", 16, 6), T(235, 145, "연봉", 34, GREEN), T(235, 205, "↑ 올랐다", 30)),
                  g(box(350, 80, 170, 160, "#fff", 16, 6), T(435, 145, "대출 이자", 30), T(435, 205, "그대로...", 30, "#9A9A9A")),
                  g(T(335, 330, "?", 90, "#C8574F"))],
    "bank_wait": [g('<path d="M190 170 L335 90 L480 170 Z" fill="#E5EEF8" stroke="#1F2A24" stroke-width="6" stroke-linejoin="round"/>',
                    box(190, 170, 290, 30, "#fff", 4, 5), T(335, 150, "은행", 34)),
                  g(*[box(x, 200, 34, 160, "#fff", 4, 5) for x in (215, 280, 345, 410)], box(180, 360, 310, 34, "#fff", 4, 5)),
                  g(box(250, 420, 170, 64, "#FFF1A8", 14, 5), T(335, 462, "알아서...?", 32))],
    "rate_request": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4)),
                     g(T(330, 150, "금리인하", 30, GREEN), T(330, 188, "요구", 30, GREEN)),
                     g(box(255, 230, 150, 50, "#fff", 8, 3), T(330, 264, "사유 선택", 24, "#666")),
                     g(box(255, 310, 150, 56, "#CFE8A9", 28, 4), T(330, 346, "신청하기", 28))],
    "rate_reasons": [g(box(170, 70, 320, 100, "#E8F2EA", 18, 6), T(330, 135, "승진·취업", 38)),
                     g(box(170, 200, 320, 100, "#fff", 18, 6), T(330, 265, "연봉 인상", 38)),
                     g(box(170, 330, 320, 100, "#FFF1A8", 18, 6), T(330, 395, "신용점수 상승", 36)),
                     g(T(330, 485, "내 형편이 나아졌다면", 30, GREEN))],
    "rate_result": [g(box(170, 120, 320, 220, "#fff", 12, 6), '<path d="M170 132 L330 250 L490 132" stroke="#1F2A24" stroke-width="6" fill="none" stroke-linejoin="round"/>'),
                    g(box(250, 290, 160, 64, "#CFE8A9", 14, 5), T(330, 333, "결과 통보", 32)),
                    g(T(330, 430, "수락? 거절?", 36, GREEN))],
    "rate_review": [g('<circle cx="320" cy="220" r="120" fill="#F3F6FA" stroke="#1F2A24" stroke-width="8"/>',
                      '<path d="M405 305 L480 380" stroke="#1F2A24" stroke-width="20" stroke-linecap="round"/>'),
                    g(T(320, 210, "은행", 36), T(320, 255, "심사", 36)),
                    g(T(330, 460, "안 될 수도 있어요", 32, "#C8574F"))],

    "rate_today": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "오늘 할 일", 36, GREEN)),
                   *[g(box(200, 160 + i * 95, 48, 48, "#fff", 8, 5),
                       '<path d="M{0} {1} l12 14 l24 -30" stroke="#2F4F3E" stroke-width="7" fill="none" stroke-linecap="round"/>'.format(208, 186 + i * 95),
                       T(270, 197 + i * 95, t, 32, INK, "start")) for i, t in enumerate(["대출 앱 열기", "메뉴 검색", "사유 고르기"])]],
    # 11/9 릴스: 잊고 있던 내 돈 찾기
    "old_bankbook": [g(box(200, 140, 260, 330, "#E5EEF8", 12, 6), '<path d="M200 200 L460 200" stroke="#1F2A24" stroke-width="4"/>', T(330, 182, "통장", 36)),
                     g(T(330, 280, "20XX년", 32, "#9A9A9A"), T(330, 340, "잔액 ?", 36, "#C8574F")),
                     g(T(330, 100, "서랍 속에서...", 34, GREEN))],
    "forgot_q": [g(box(170, 90, 140, 110, "#fff", 12, 5), T(240, 158, "통장1", 30)),
                 g(box(350, 90, 140, 110, "#fff", 12, 5), T(420, 158, "통장2", 30)),
                 g(box(260, 240, 140, 110, "#fff", 12, 5), T(330, 308, "통장3", 30)),
                 g(T(330, 450, "얼마씩 있었지?", 38, "#C8574F"))],
    "points_fade": [g(box(180, 90, 300, 180, "#FFF1A8", 18, 6), '<rect x="180" y="130" width="300" height="34" fill="#1F2A24"/>', T(330, 240, "카드 포인트", 32)),
                    g(T(250, 340, "P", 50, "#C9B76A"), T(330, 360, "P", 42, "#DCCF9A"), T(400, 380, "P", 34, "#EDE6C9")),
                    g(T(330, 460, "소멸 예정...", 36, "#C8574F"))],
    "acct_lookup": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4)),
                    g(box(252, 115, 156, 52, "#fff", 26, 4), T(330, 151, "계좌 한눈에", 24, GREEN)),
                    g(box(252, 185, 156, 46, "#E8F2EA", 8, 3), T(330, 216, "계좌 3개", 24)),
                    g(box(252, 245, 156, 46, "#FBE3E0", 8, 3), T(330, 276, "휴면 1개", 24)),
                    g(box(252, 305, 156, 46, "#FFF1A8", 8, 3), T(330, 336, "포인트", 24))],
    "gather_one": [g(*[box(x, 80, 110, 80, "#fff", 10, 5) for x in (150, 275, 400)], *[T(x + 55, 132, "조금", 26, "#666") for x in (150, 275, 400)]),
                   g(arrow(205, 175, 300, 290), arrow(330, 175, 330, 290), arrow(455, 175, 360, 290)),
                   g(box(220, 300, 220, 140, "#CFE8A9", 18, 6), T(330, 365, "한 통장", 38), T(330, 415, "으로", 30))],
    "points_cash": [g(box(140, 140, 180, 160, "#FFF1A8", 16, 6), T(230, 235, "P", 70, "#C9B76A")),
                    g(arrow(335, 220, 410, 220)),
                    g(box(420, 150, 140, 140, "#fff", 16, 6), coin(490, 250), coin(490, 230), coin(490, 210)),
                    g(T(350, 400, "현금으로 받기", 38, GREEN))],
    "found_check": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "오늘 5분", 36, GREEN)),
                    *[g(box(200, 160 + i * 95, 48, 48, "#fff", 8, 5),
                        '<path d="M{0} {1} l12 14 l24 -30" stroke="#2F4F3E" stroke-width="7" fill="none" stroke-linecap="round"/>'.format(208, 186 + i * 95),
                        T(270, 197 + i * 95, t, 32, INK, "start")) for i, t in enumerate(["내 계좌 조회", "휴면 계좌 확인", "카드 포인트"])]],

    # 11/10 카드: 퇴직금 일시금 vs 연금 (캐릭터판)
    "retire_form": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "퇴직금 신청서", 34, GREEN)),
                    g('<path d="M200 170 L460 170 M200 230 L400 230" stroke="#C9C9C9" stroke-width="10" stroke-linecap="round"/>'),
                    g(T(330, 300, "받는 방법", 32, "#666")),
                    g(box(205, 330, 40, 40, "#fff", 6, 4), T(260, 362, "한 번에", 30, INK, "start"),
                      box(205, 395, 40, 40, "#fff", 6, 4), T(260, 427, "나눠서", 30, INK, "start")),
                    g(T(440, 400, "?", 70, "#C8574F"))],
    "lump_tax": [g(f'<path d="M260 160 Q230 120 280 110 L380 110 Q430 120 400 160 Q500 230 470 380 Q460 450 330 450 Q200 450 190 380 Q160 230 260 160 Z" fill="#F4CF4C" stroke="{INK}" stroke-width="6"/>',
                   T(330, 320, "퇴직금", 40)),
                 g(arrow(470, 300, 550, 300, "#C8574F")),
                 g(box(420, 330, 160, 80, "#FBE3E0", 14, 5), T(500, 382, "세금 한 번에", 26, "#C8574F"))],
    "tax_cut": [g(box(160, 140, 130, 300, "#FBE3E0", 8, 6), T(225, 300, "100", 40), T(225, 480, "한 번에", 30, "#666")),
                g(box(370, 230, 130, 210, "#CFE8A9", 8, 6), T(435, 345, "70", 40), T(435, 480, "연금으로", 30, "#666")),
                g(arrow(300, 180, 370, 220), T(360, 150, "-30%", 40, GREEN))],
    "tax_cut2": [g(box(150, 140, 110, 300, "#FBE3E0", 8, 6), T(205, 300, "100", 36), T(205, 480, "한 번에", 26, "#666")),
                 g(box(285, 230, 110, 210, "#E8F2EA", 8, 6), T(340, 345, "70", 36), T(340, 480, "~10년차", 26, "#666")),
                 g(box(420, 260, 110, 180, "#CFE8A9", 8, 6), T(475, 360, "60", 36), T(475, 480, "11년차~", 26, "#666")),
                 g(T(475, 220, "-40%", 40, GREEN))],
    "tax_1000": [g(box(160, 80, 340, 130, "#fff", 18, 6), T(330, 130, "세금이 1,000만 원이면", 30, "#666"), T(330, 186, "한 번에 1,000만", 36)),
                 g(arrow(330, 220, 330, 290)),
                 g(box(160, 300, 340, 130, "#CFE8A9", 18, 6), T(330, 350, "연금으로 받으면", 30, "#666"), T(330, 406, "700만 원 비율", 38))],
    "irp_60": [g(box(150, 80, 200, 130, "#F4CF4C", 18, 6), T(250, 160, "받은 퇴직금", 30)),
               g(arrow(260, 220, 360, 320)),
               g(box(300, 320, 220, 120, "#E8F2EA", 18, 6), T(410, 395, "IRP 계좌", 40)),
               g(box(380, 110, 150, 90, "#FFF1A8", 14, 5), T(455, 168, "60일 안", 34, "#C8574F"))],
    "ret_app": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4)),
                g(T(330, 150, "내 퇴직연금", 28, GREEN)),
                g(box(252, 180, 156, 70, "#E8F2EA", 10, 3), T(330, 210, "적립금", 22, "#666"), T(330, 240, "○○○만", 30)),
                g(box(252, 275, 156, 100, "#FFF1A8", 10, 3), T(330, 310, "받는 방법", 24), T(330, 350, "메모!", 28, GREEN))],

    # 11/10 릴스: 학원비 먼저, 노후는 나중?
    "tuition_up": [g(*[box(150 + i * 60, 380 - h, 45, h, "#FBE3E0", 6, 5) for i, h in enumerate((90, 140, 190, 240))], T(255, 440, "학원비", 30, "#C8574F")),
                   g(*[box(410 + i * 55, 380 - h, 40, h, "#CFE8A9", 6, 5) for i, h in enumerate((150, 100, 60))], T(465, 440, "내 저축", 30, GREEN)),
                   g(arrow(440, 150, 520, 210, "#C8574F"))],
    "kid_first": [g('<path d="M330 420 C140 300 160 150 260 150 C300 150 330 190 330 210 C330 190 360 150 400 150 C500 150 520 300 330 420 Z" fill="#FBE3E0" stroke="#1F2A24" stroke-width="6"/>'),
                  g(T(330, 290, "아이가 먼저", 38))],
    "no_loan": [g(box(190, 90, 280, 330, "#F3F6FA", 10, 6), box(250, 190, 160, 230, "#fff", 6, 5), T(330, 150, "노후 자금", 34)),
                g(f'<path d="M260 210 L400 400 M400 210 L260 400" stroke="#C8574F" stroke-width="12" stroke-linecap="round"/>'),
                g(T(330, 480, "빌려주는 곳 없음", 34, "#C8574F"))],
    "order_swap": [g(box(170, 90, 320, 120, "#CFE8A9", 18, 6), T(220, 165, "①", 44, GREEN), T(360, 165, "노후 저축", 38)),
                   g(arrow(330, 220, 330, 290)),
                   g(box(170, 300, 320, 120, "#fff", 18, 6), T(220, 375, "②", 44, GREEN), T(360, 375, "학원비", 38))],
    "tuition_cap": [g(box(240, 70, 120, 380, "#fff", 12, 6), box(252, 230, 96, 208, "#FBE3E0", 6, 0)),
                    g('<path d="M200 200 L400 200" stroke="#2F4F3E" stroke-width="8" stroke-dasharray="18 10"/>', T(420, 210, "한도", 38, GREEN, "start")),
                    g(T(300, 500, "여기까지만", 32, "#666"))],
    "kept_jar": _jar(5, "내 노후"),
    "edu_check": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "이번 달 점검", 36, GREEN)),
                  *[g(box(200, 160 + i * 95, 48, 48, "#fff", 8, 5),
                      '<path d="M{0} {1} l12 14 l24 -30" stroke="#2F4F3E" stroke-width="7" fill="none" stroke-linecap="round"/>'.format(208, 186 + i * 95),
                      T(270, 197 + i * 95, t, 32, INK, "start")) for i, t in enumerate(["교육비 총액", "노후 저축 금액", "나가는 순서"])]],

    # 11/11 카드: 부부 돈 대화
    "couple_wall": [g(box(150, 140, 150, 200, "#E5EEF8", 14, 6), T(225, 250, "내 통장", 30)),
                    g(box(360, 140, 150, 200, "#E8F2EA", 14, 6), T(435, 250, "배우자", 30)),
                    g('<path d="M330 100 L330 380" stroke="#1F2A24" stroke-width="12" stroke-dasharray="4 14" stroke-linecap="round"/>'),
                    g(T(330, 450, "서로 얼마인지 몰라요", 32, "#C8574F"))],
    "talk_cloud": [g('<path d="M200 130 Q200 80 260 80 L420 80 Q480 80 480 130 L480 260 Q480 310 420 310 L300 310 L240 370 L250 310 Q200 310 200 260 Z" fill="#fff" stroke="#1F2A24" stroke-width="6"/>'),
                   g(T(340, 215, "돈 얘기 하면...", 34)),
                   g(T(340, 450, "괜히 싸울까 봐", 34, "#C8574F"))],
    "coffee_date": [g(box(160, 70, 340, 200, "#fff", 10, 6), '<rect x="160" y="70" width="340" height="50" fill="#2F4F3E" stroke="#1F2A24" stroke-width="6"/>', T(330, 108, "한 달에 한 번", 28, "#fff")),
                    g('<circle cx="330" cy="195" r="44" fill="none" stroke="#C8574F" stroke-width="7"/>', T(330, 210, "돈", 38)),
                    g(box(220, 320, 90, 110, "#FBF7EC", 12, 6), box(350, 320, 90, 110, "#FBF7EC", 12, 6), T(330, 480, "커피 한 잔", 32, GREEN))],
    "shared_sheet": [g(box(170, 70, 320, 400, "#fff", 10, 6), T(330, 126, "우리 집 한 장", 34, GREEN)),
                     g(T(200, 210, "들어온 돈", 32, INK, "start"), T(460, 210, "○○", 32, "#666", "end")),
                     g(T(200, 290, "나간 돈", 32, INK, "start"), T(460, 290, "○○", 32, "#666", "end")),
                     g(T(200, 370, "모은 돈", 32, INK, "start"), T(460, 370, "○○", 32, GREEN, "end")),
                     g('<path d="M190 420 L470 420" stroke="#F4CF4C" stroke-width="22" stroke-linecap="round" opacity=".7"/>', T(330, 432, "탓하지 않기", 30))],
    "one_goal": [g('<path d="M260 440 L260 90" stroke="#1F2A24" stroke-width="10" stroke-linecap="round"/>',
                   '<path d="M264 96 L470 140 L264 200 Z" fill="#CFE8A9" stroke="#1F2A24" stroke-width="6" stroke-linejoin="round"/>'),
                 g(T(350, 158, "우리 목표", 32)),
                 g(box(200, 440, 260, 50, "#FFF1A8", 12, 5), T(330, 475, "딱 하나만", 30))],
    "talk_easy": [g(box(150, 150, 150, 160, "#E5EEF8", 14, 6), T(225, 240, "나", 36)),
                  g(box(360, 150, 150, 160, "#E8F2EA", 14, 6), T(435, 240, "배우자", 32)),
                  g('<path d="M330 260 C290 220 300 190 318 190 C326 190 330 198 330 204 C330 198 334 190 342 190 C360 190 370 220 330 260 Z" fill="#F4A6A0" stroke="#1F2A24" stroke-width="4"/>'),
                  g(T(330, 420, "말이 편해졌어요", 36, GREEN))],
    "couple_check": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "주말 30분", 36, GREEN)),
                     *[g(box(200, 160 + i * 95, 48, 48, "#fff", 8, 5),
                         '<path d="M{0} {1} l12 14 l24 -30" stroke="#2F4F3E" stroke-width="7" fill="none" stroke-linecap="round"/>'.format(208, 186 + i * 95),
                         T(270, 197 + i * 95, t, 32, INK, "start")) for i, t in enumerate(["날짜 정하기", "숫자만 보기", "목표 하나"])]],

    # 11/11 릴스: 경력 쉬는 동안 국민연금 빈칸
    "pension_blank": [g('<path d="M140 250 L520 250" stroke="#1F2A24" stroke-width="6"/>', T(330, 150, "내 국민연금 기록", 34, GREEN)),
                      g(box(140, 220, 120, 60, "#CFE8A9", 8, 5), T(200, 320, "직장", 28, "#666")),
                      g(box(270, 220, 160, 60, "#fff", 8, 5), '<path d="M280 230 L420 270" stroke="#C8574F" stroke-width="5"/>', T(350, 320, "육아 10년", 28, "#C8574F")),
                      g(T(350, 420, "빈칸...", 40, "#C8574F"))],
    "no_income": [g(box(190, 130, 280, 200, "#F3F6FA", 24, 6), '<path d="M190 190 L470 190" stroke="#1F2A24" stroke-width="5"/>', T(330, 280, "소득 0", 46, "#9A9A9A")),
                  g(T(330, 420, "넣을 수 없는 줄", 36, "#C8574F"))],
    "voluntary_join": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "국민연금 신청", 34, GREEN)),
                       g(box(205, 170, 40, 40, "#fff", 6, 4), T(260, 202, "직장 가입", 30, "#9A9A9A", "start")),
                       g(box(205, 240, 40, 40, "#CFE8A9", 6, 4), '<path d="M211 260 l10 12 l20 -26" stroke="#2F4F3E" stroke-width="6" fill="none" stroke-linecap="round"/>', T(260, 272, "임의가입", 34, INK, "start")),
                       g('<path d="M200 360 L460 360" stroke="#F4CF4C" stroke-width="22" stroke-linecap="round" opacity=".7"/>', T(330, 372, "소득 없어도 가능", 30))],
    "fill_gap": [g('<path d="M140 250 L520 250" stroke="#1F2A24" stroke-width="6"/>', box(140, 220, 120, 60, "#CFE8A9", 8, 5), box(270, 220, 160, 60, "#fff", 8, 5)),
                 g(box(270, 220, 160, 60, "#FFF1A8", 8, 5), T(350, 260, "채우기", 30)),
                 g(T(330, 380, "빈 기간 추후납부", 34, GREEN))],
    "ten_years": [g(box(130, 220, 400, 60, "#fff", 10, 6), '<rect x="134" y="224" width="300" height="52" rx="8" fill="#CFE8A9"/>'),
                  g('<path d="M460 300 L460 140" stroke="#1F2A24" stroke-width="7"/>', '<path d="M463 144 L540 166 L463 190 Z" fill="#F4CF4C" stroke="#1F2A24" stroke-width="5"/>', T(505, 125, "10년", 34)),
                  g(T(330, 380, "여기부터 평생 연금", 34, GREEN))],
    "start_now": [g('<path d="M330 440 L330 280" stroke="#2F4F3E" stroke-width="10" stroke-linecap="round"/>',
                    '<path d="M330 300 C260 300 230 240 240 200 C300 200 330 250 330 300 Z" fill="#CFE8A9" stroke="#1F2A24" stroke-width="5"/>',
                    '<path d="M330 280 C400 280 430 220 420 180 C360 180 330 230 330 280 Z" fill="#CFE8A9" stroke="#1F2A24" stroke-width="5"/>'),
                  g(box(220, 440, 220, 60, "#FFF1A8", 14, 5), T(330, 482, "지금 시작", 34))],
    "pension_app": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4)),
                    g(T(330, 150, "내 곁에 국민연금", 22, GREEN)),
                    g(box(252, 180, 156, 70, "#E8F2EA", 10, 3), T(330, 210, "가입 기간", 22, "#666"), T(330, 240, "○년 ○개월", 26)),
                    g(box(252, 275, 156, 70, "#FFF1A8", 10, 3), T(330, 305, "빈 기간", 22, "#666"), T(330, 335, "확인!", 26, "#C8574F"))],

    # 11/12 카드: 차 바꾸고 싶을 때
    "car_old": [g(f'<path d="M160 330 L180 260 Q190 230 230 230 L420 230 Q460 230 475 260 L500 330 Z" fill="#E5EEF8" stroke="#1F2A24" stroke-width="6" stroke-linejoin="round"/>',
                   '<rect x="140" y="320" width="380" height="70" rx="20" fill="#E5EEF8" stroke="#1F2A24" stroke-width="6"/>',
                   '<circle cx="230" cy="395" r="34" fill="#1F2A24"/><circle cx="430" cy="395" r="34" fill="#1F2A24"/>', T(330, 300, "10년", 40)),
                g(T(330, 150, "새 차... 갖고 싶다", 36, GREEN))],
    "car_price": [g(box(200, 120, 260, 160, "#FFF1A8", 18, 6), T(330, 190, "차값", 36), T(330, 245, "할 만한데?", 32, "#666")),
                  g('<circle cx="230" cy="150" r="12" fill="#fff" stroke="#1F2A24" stroke-width="4"/>'),
                  g(T(330, 380, "처음엔 이것만 봤어요", 32, "#666"))],
    "car_costs": [g(f'<path d="M160 330 L180 260 Q190 230 230 230 L420 230 Q460 230 475 260 L500 330 Z" fill="#F3F6FA" stroke="#1F2A24" stroke-width="6" stroke-linejoin="round"/>',
                   '<rect x="140" y="320" width="380" height="70" rx="20" fill="#F3F6FA" stroke="#1F2A24" stroke-width="6"/>',
                   '<circle cx="230" cy="395" r="34" fill="#1F2A24"/><circle cx="430" cy="395" r="34" fill="#1F2A24"/>',),
                  g(box(130, 90, 120, 60, "#FBE3E0", 12, 5), T(190, 130, "보험", 30)),
                  g(box(270, 70, 120, 60, "#FBE3E0", 12, 5), T(330, 110, "세금", 30)),
                  g(box(410, 90, 120, 60, "#FBE3E0", 12, 5), T(470, 130, "기름값", 28))],
    "car_three": [g(box(130, 60, 400, 110, "#E8F2EA", 18, 6), T(180, 130, "①", 40, GREEN), T(350, 130, "수리비 vs 새 차", 34)),
                  g(box(130, 200, 400, 110, "#fff", 18, 6), T(180, 270, "②", 40, GREEN), T(350, 270, "한 달 총비용", 34)),
                  g(box(130, 340, 400, 110, "#E5EEF8", 18, 6), T(180, 410, "③", 40, GREEN), T(350, 410, "저축 목표 먼저", 34))],
    "car_more_year": [g(box(170, 80, 320, 300, "#fff", 10, 6), '<rect x="170" y="80" width="320" height="60" fill="#2F4F3E" stroke="#1F2A24" stroke-width="6"/>', T(330, 122, "내년", 32, "#fff")),
                      g(T(330, 280, "+1년", 80, GREEN)),
                      g(T(330, 450, "고쳐서 더 타기", 34))],
    "car_jar": _jar(3, "차 통장"),
    "car_check": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "바꾸기 전에", 34, GREEN)),
                  *[g(box(200, 160 + i * 95, 48, 48, "#fff", 8, 5),
                       '<path d="M{0} {1} l12 14 l24 -30" stroke="#2F4F3E" stroke-width="7" fill="none" stroke-linecap="round"/>'.format(208, 186 + i * 95),
                       T(270, 197 + i * 95, t, 30, INK, "start")) for i, t in enumerate(["보험·세금 합치기", "기름·주차 합치기", "한 달 총비용"])]],

    # 11/12 릴스: 적금에 이름 붙이기
    "break_three": [*[g(box(150 + i * 130, 160, 100, 180, "#EAF4F8", 16, 5), T(200 + i * 130, 220, "적금", 26),
                        f'<path d="M{200 + i * 130} 170 L{185 + i * 130} 250 L{215 + i * 130} 290 L{195 + i * 130} 335" stroke="#C8574F" stroke-width="6" fill="none" stroke-linecap="round"/>')
                      for i in range(3)],
                    g(T(330, 430, "세 번 깼어요", 38, "#C8574F"))],
    "plain_money": [g(box(200, 120, 260, 220, "#F3F6FA", 14, 6), T(330, 215, "그냥", 40, "#9A9A9A"), T(330, 270, "모은 돈", 36, "#9A9A9A")),
                    g(arrow(470, 230, 550, 230, "#C8574F"), T(500, 190, "급할 때", 26, "#C8574F")),
                    g(T(330, 430, "꺼내기 쉬웠어요", 34, "#C8574F"))],
    "named_accounts": [g(box(130, 70, 400, 100, "#FFF1A8", 16, 6), T(330, 135, "가족 여행", 38)),
                       g(box(130, 200, 400, 100, "#E5EEF8", 16, 6), T(330, 265, "아이 대학", 38)),
                       g(box(130, 330, 400, 100, "#CFE8A9", 16, 6), T(330, 395, "내 노후", 38))],
    "too_precious": [g(box(220, 120, 220, 260, "#FFF1A8", 18, 6), T(330, 200, "가족 여행", 32)),
                     g('<path d="M330 330 C290 300 300 270 318 270 C326 270 330 278 330 284 C330 278 334 270 342 270 C360 270 370 300 330 330 Z" fill="#F4A6A0" stroke="#1F2A24" stroke-width="4"/>'),
                     g(T(330, 450, "이건 못 깨겠다", 36, GREEN))],
    "suitcase": [g(box(200, 170, 260, 230, "#F4CF4C", 20, 6), '<path d="M280 170 L280 130 L380 130 L380 170" stroke="#1F2A24" stroke-width="7" fill="none"/>'),
                 g('<path d="M200 250 L460 250 M200 320 L460 320" stroke="#1F2A24" stroke-width="4"/>', T(330, 295, "여행!", 36)),
                 g(T(330, 470, "모은 돈으로 떠났어요", 32, GREEN))],
    "goal_hold": [g(box(150, 250, 110, 160, "#E8F2EA", 10, 5), T(205, 440, "1년", 28, "#666")),
                  g(box(275, 190, 110, 220, "#CFE8A9", 10, 5), T(330, 440, "2년", 28, "#666")),
                  g(box(400, 120, 110, 290, "#A9D58A", 10, 5), T(455, 440, "3년", 28, "#666")),
                  g(T(330, 90, "목표 있는 돈은 오래 가요", 32, GREEN))],
    "rename_app": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4)),
                   g(T(330, 150, "계좌 별명", 28, GREEN)),
                   g(box(252, 180, 156, 56, "#fff", 8, 3), T(330, 216, "적금 1", 24, "#9A9A9A")),
                   g(arrow(330, 245, 330, 285)),
                   g(box(252, 295, 156, 56, "#FFF1A8", 8, 3), T(330, 331, "가족 여행", 26))],

    # 11/13 카드: 12월 지출 미리 준비
    "dec_bill": [g(box(180, 70, 300, 380, "#fff", 10, 6), T(330, 126, "1월에 온 카드값", 30, GREEN)),
                 g(T(210, 200, "송년회", 30, INK, "start"), T(450, 200, "+", 34, "#C8574F", "end")),
                 g(T(210, 260, "선물", 30, INK, "start"), T(450, 260, "+", 34, "#C8574F", "end")),
                 g(T(210, 320, "경조사", 30, INK, "start"), T(450, 320, "+", 34, "#C8574F", "end")),
                 g(T(330, 410, "헉...", 44, "#C8574F"))],
    "dec_pile": [g(box(150, 300, 160, 110, "#FBE3E0", 12, 5), T(230, 365, "모임", 30)),
                 g(box(330, 300, 160, 110, "#FFF1A8", 12, 5), T(410, 365, "선물", 30)),
                 g(box(240, 170, 160, 110, "#E5EEF8", 12, 5), T(320, 235, "경조사", 30)),
                 g(T(330, 120, "한 달에 몰려요", 34, "#C8574F"))],
    "dec_envelope": [g(box(170, 140, 320, 220, "#fff", 12, 6), '<path d="M170 152 L330 270 L490 152" stroke="#1F2A24" stroke-width="6" fill="none" stroke-linejoin="round"/>'),
                     g(box(240, 300, 180, 70, "#CFE8A9", 14, 5), T(330, 346, "12월 봉투", 32)),
                     g(T(330, 450, "11월에 미리", 34, GREEN))],
    "dec_list": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "12월 일정", 34, GREEN)),
                 g(T(200, 200, "송년회 2번", 30, INK, "start"), T(460, 200, "○만", 30, "#666", "end")),
                 g(T(200, 270, "아이 선물", 30, INK, "start"), T(460, 270, "○만", 30, "#666", "end")),
                 g(T(200, 340, "부모님", 30, INK, "start"), T(460, 340, "○만", 30, "#666", "end")),
                 g('<path d="M200 410 L460 410" stroke="#F4CF4C" stroke-width="22" stroke-linecap="round" opacity=".7"/>', T(330, 421, "합계 = 12월 예산", 28))],
    "dec_split": [g(T(330, 90, "11·12월 나눠 모으기", 34, GREEN)),
                  g(box(150, 140, 160, 220, "#E8F2EA", 14, 6), T(230, 260, "11월", 36)),
                  g(box(350, 140, 160, 220, "#CFE8A9", 14, 6), T(430, 260, "12월", 36)),
                  g(T(330, 440, "한 번에 부담 줄이기", 32))],
    "jan_calm": [g(box(170, 80, 320, 300, "#fff", 10, 6), '<rect x="170" y="80" width="320" height="60" fill="#2F4F3E" stroke="#1F2A24" stroke-width="6"/>', T(330, 122, "1월", 32, "#fff")),
                 g('<circle cx="330" cy="260" r="70" fill="#CFE8A9" stroke="#1F2A24" stroke-width="5"/>', '<path d="M300 250 Q330 290 360 250" stroke="#1F2A24" stroke-width="6" fill="none" stroke-linecap="round"/>'),
                 g(T(330, 450, "카드값이 무섭지 않아요", 32, GREEN))],
    "dec_check": [g(box(170, 60, 320, 420, "#fff", 10, 6), T(330, 118, "오늘 10분", 34, GREEN)),
                  *[g(box(200, 160 + i * 95, 48, 48, "#fff", 8, 5),
                         '<path d="M{0} {1} l12 14 l24 -30" stroke="#2F4F3E" stroke-width="7" fill="none" stroke-linecap="round"/>'.format(208, 186 + i * 95),
                         T(270, 197 + i * 95, t, 30, INK, "start")) for i, t in enumerate(["12월 일정 적기", "금액 옆에 쓰기", "봉투 통장 만들기"])]],

    # 11/13 릴스: 친구가 돈 빌려 달라고 할 때
    "friend_msg": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4)),
                   g(box(250, 120, 160, 90, "#fff", 14, 3), T(330, 158, "오랜만이야", 22), T(330, 190, "부탁 하나만...", 22, "#C8574F")),
                   g(T(330, 300, "?", 70, "#C8574F"))],
    "lend_yes": [g(box(140, 170, 140, 110, "#F4CF4C", 14, 6), T(210, 235, "내 돈", 30)),
                 g(arrow(290, 225, 380, 225)),
                 g(box(390, 170, 140, 110, "#fff", 14, 6), T(460, 235, "친구", 30)),
                 g(T(330, 380, "거절을 못 했어요", 34, "#C8574F"))],
    "no_return": [g(box(170, 80, 320, 280, "#fff", 10, 6), '<rect x="170" y="80" width="320" height="56" fill="#C8574F" stroke="#1F2A24" stroke-width="6"/>', T(330, 120, "약속한 날", 30, "#fff")),
                  g(T(330, 250, "연락 없음", 40, "#9A9A9A")),
                  g(T(330, 440, "돈도 사이도 멀어졌어요", 32, "#C8574F"))],
    "lend_rule": [g(box(150, 70, 360, 380, "#E8F2EA", 18, 6), T(330, 130, "내 원칙", 38, GREEN)),
                  g(T(330, 230, "못 받아도", 36), T(330, 290, "괜찮은 만큼만", 36)),
                  g('<path d="M190 360 L470 360" stroke="#F4CF4C" stroke-width="22" stroke-linecap="round" opacity=".7"/>', T(330, 372, "보증은 서지 않기", 30))],
    "kind_no": [g('<path d="M200 130 Q200 80 260 80 L420 80 Q480 80 480 130 L480 260 Q480 310 420 310 L300 310 L240 370 L250 310 Q200 310 200 260 Z" fill="#fff" stroke="#1F2A24" stroke-width="6"/>'),
                g(T(340, 180, "이번엔 어렵지만", 30), T(340, 235, "다른 방법 같이", 30), T(340, 275, "찾아보자", 30)),
                g(T(330, 450, "정중하게 거절", 34, GREEN))],
    "peace_mind": [g('<circle cx="330" cy="240" r="130" fill="#CFE8A9" stroke="#1F2A24" stroke-width="6"/>',
                     '<path d="M280 220 Q295 205 310 220 M350 220 Q365 205 380 220" stroke="#1F2A24" stroke-width="6" fill="none" stroke-linecap="round"/>',
                     '<path d="M285 280 Q330 320 375 280" stroke="#1F2A24" stroke-width="6" fill="none" stroke-linecap="round"/>'),
                   g(T(330, 450, "마음이 편해졌어요", 34, GREEN))],
    "my_limit": [g(box(170, 70, 320, 380, "#fff", 10, 6), T(330, 126, "메모장", 34, GREEN)),
                 g(T(200, 220, "빌려줄 수 있는", 30, INK, "start")),
                 g(T(200, 280, "내 한도:", 30, INK, "start"), box(330, 245, 130, 52, "#FFF1A8", 8, 4), T(395, 282, "○○만", 30)),
                 g(T(330, 400, "미리 정해 두기", 32, GREEN))],

    # 11/13 릴스(교체): 놀고 있던 연금저축
    "pension_acct": [g(box(190, 110, 280, 300, "#E8F2EA", 18, 6), T(330, 180, "연금저축", 40)),
                     g(box(220, 230, 220, 60, "#fff", 10, 4), T(330, 270, "매달 입금 ✓", 30, GREEN)),
                     g(T(330, 470, "연말정산 때문에 만든", 30, "#666"))],
    "flat_line": [g('<path d="M140 400 L520 400 M140 400 L140 120" stroke="#1F2A24" stroke-width="5"/>'),
                  g('<path d="M150 300 L510 290" stroke="#9A9A9A" stroke-width="8" stroke-linecap="round"/>'),
                  g(T(330, 250, "거의 그대로...", 36, "#C8574F")),
                  g(T(330, 460, "몇 년을 넣었는데", 30, "#666"))],
    "idle_cash": [g(box(170, 120, 320, 260, "#F3F6FA", 18, 6), T(330, 180, "내 연금 계좌", 30, GREEN)),
                  g(box(210, 220, 240, 110, "#FFF1A8", 14, 5), T(330, 265, "대기 자금", 30), T(330, 310, "(현금)", 28, "#666")),
                  g(T(330, 460, "zZ 쉬는 중", 36, "#9A9A9A"))],
    "put_vs_run": [g(box(140, 140, 170, 160, "#fff", 16, 6), T(225, 210, "넣기", 40), T(225, 260, "입금", 28, "#666")),
                   g(T(330, 230, "≠", 60, "#C8574F")),
                   g(box(350, 140, 170, 160, "#CFE8A9", 16, 6), T(435, 210, "굴리기", 38), T(435, 260, "운용", 28, "#666"))],
    "choose_mix": [g(box(130, 100, 400, 90, "#E5EEF8", 14, 5), T(330, 158, "안정형", 34)),
                   g(box(130, 210, 400, 90, "#CFE8A9", 14, 5), T(330, 268, "중간형", 34),
                     '<path d="M470 240 l12 14 l24 -30" stroke="#2F4F3E" stroke-width="8" fill="none" stroke-linecap="round"/>'),
                   g(box(130, 320, 400, 90, "#FBE3E0", 14, 5), T(330, 378, "성장형", 34)),
                   g(T(330, 470, "내 성향에 맞게", 32, GREEN))],
    "monthly_peek": [g(box(170, 80, 320, 300, "#fff", 10, 6), '<rect x="170" y="80" width="320" height="60" fill="#2F4F3E" stroke="#1F2A24" stroke-width="6"/>', T(330, 122, "매달", 32, "#fff")),
                     g('<circle cx="330" cy="260" r="60" fill="none" stroke="#C8574F" stroke-width="8"/>', T(330, 275, "확인", 38)),
                     g(T(330, 450, "한 번만 들여다보기", 32, GREEN))],
    "idle_check_app": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4)),
                       g(T(330, 150, "연금저축 계좌", 24, GREEN)),
                       g(box(252, 180, 156, 70, "#FFF1A8", 10, 3), T(330, 210, "대기 자금", 22, "#666"), T(330, 240, "얼마?", 28, "#C8574F")),
                       g(box(252, 275, 156, 70, "#E8F2EA", 10, 3), T(330, 305, "운용 상품", 22, "#666"), T(330, 335, "있나?", 28))],

    "parents_q": [g('<circle cx="260" cy="170" r="44" fill="#FFF3E4" stroke="#333" stroke-width="5"/><path d="M216 164 Q260 100 304 164 Q280 140 260 142 Q236 140 216 164 Z" fill="#9A9A9A" stroke="#333" stroke-width="4"/><circle cx="245" cy="174" r="5" fill="#333"/><circle cx="275" cy="174" r="5" fill="#333"/><path d="M248 192 Q260 202 272 192" stroke="#333" stroke-width="4" fill="none" stroke-linecap="round"/><circle cx="420" cy="170" r="44" fill="#FFF3E4" stroke="#333" stroke-width="5"/><path d="M376 164 Q420 100 464 164 Q440 140 420 142 Q396 140 376 164 Z" fill="#666" stroke="#333" stroke-width="4"/><circle cx="405" cy="174" r="5" fill="#333"/><circle cx="435" cy="174" r="5" fill="#333"/><path d="M408 192 Q420 202 432 192" stroke="#333" stroke-width="4" fill="none" stroke-linecap="round"/>', ''),
                  g(box(270, 260, 140, 100, "#fff", 8, 5), '<path d="M270 262 L340 312 L410 262" fill="none" stroke="#333" stroke-width="5"/>', T(340, 345, "용돈", 26)),
                  g(T(340, 450, "얼마가 맞을까?", 34, "#C8574F"), T(470, 250, "?", 70, "#C8574F"))],
    "plan_shake": [g(box(190, 70, 290, 330, "#fff", 10, 6), T(335, 122, "이번 달 계획", 30, GREEN)),
                   g(T(335, 190, "저축", 30), T(335, 250, "생활비", 30), T(335, 310, "용돈 +α", 30, "#C8574F")),
                   g('<path d="M160 120 l-24 -10 M160 200 l-28 0 M510 140 l24 -12 M510 230 l28 0" stroke="#333" stroke-width="5" stroke-linecap="round"/>'),
                   g(T(335, 460, "그때그때 달라졌어요", 32, "#C8574F"))],
    "sibling_rule": [g('<circle cx="230" cy="170" r="44" fill="#FFF3E4" stroke="#333" stroke-width="5"/><path d="M186 164 Q230 100 274 164 Q250 140 230 142 Q206 140 186 164 Z" fill="#4A3A32" stroke="#333" stroke-width="4"/><circle cx="215" cy="174" r="5" fill="#333"/><circle cx="245" cy="174" r="5" fill="#333"/><path d="M218 192 Q230 202 242 192" stroke="#333" stroke-width="4" fill="none" stroke-linecap="round"/>'), g('<circle cx="335" cy="150" r="44" fill="#FFF3E4" stroke="#333" stroke-width="5"/><path d="M291 144 Q335 80 379 144 Q355 120 335 122 Q311 120 291 144 Z" fill="#4A3A32" stroke="#333" stroke-width="4"/><circle cx="320" cy="154" r="5" fill="#333"/><circle cx="350" cy="154" r="5" fill="#333"/><path d="M323 172 Q335 182 347 172" stroke="#333" stroke-width="4" fill="none" stroke-linecap="round"/>'), g('<circle cx="440" cy="170" r="44" fill="#FFF3E4" stroke="#333" stroke-width="5"/><path d="M396 164 Q440 100 484 164 Q460 140 440 142 Q416 140 396 164 Z" fill="#4A3A32" stroke="#333" stroke-width="4"/><circle cx="425" cy="174" r="5" fill="#333"/><circle cx="455" cy="174" r="5" fill="#333"/><path d="M428 192 Q440 202 452 192" stroke="#333" stroke-width="4" fill="none" stroke-linecap="round"/>'),
                     g(box(200, 300, 270, 120, "#FFF1A8", 14, 6), T(335, 350, "우리 집 기준", 32), T(335, 395, "매달 · 같은 날", 28, "#555"))],
    "auto_transfer": [g(box(150, 80, 200, 300, "#fff", 30, 6), box(165, 120, 170, 200, "#F3F6FA", 8, 4), T(250, 200, "자동이체", 28, GREEN), T(250, 250, "매달 ○일", 28)),
                      g(arrow(370, 230, 440, 230)),
                      g(box(450, 180, 110, 100, "#fff", 8, 5), '<path d="M450 182 L505 228 L560 182" fill="none" stroke="#333" stroke-width="5"/>', T(505, 265, "부모님", 22)),
                      g(T(355, 450, "잊지 않고, 흔들리지 않게", 30, GREEN))],
    "event_jar": _jar(3, "명절·생신") + [g(box(390, 20, 200, 80, "#E8F2EA", 40, 5), T(490, 72, "따로 모으기", 30, GREEN))],
    "both_kept": [g(box(120, 150, 190, 230, "#FFF1A8", 16, 6), T(215, 250, "부모님", 32), T(215, 300, "용돈", 32)),
                  g(box(360, 150, 190, 230, "#E8F2EA", 16, 6), T(455, 250, "내 노후", 32), T(455, 300, "저축", 32)),
                  g(T(335, 460, "둘 다 지켜요", 36, GREEN))],
    "family_chat": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4), T(330, 75, "가족 단톡방", 20, "#666")),
                    g(box(250, 120, 150, 70, "#fff", 14, 3), T(325, 165, "용돈 기준", 24)),
                    g(box(262, 210, 150, 70, "#FFF1A8", 14, 3), T(337, 255, "같이 정해요", 24))],
    "payday_empty": [g(box(110, 140, 170, 220, "#fff", 14, 6), T(195, 120, "월급날", 32, GREEN),
                       coin(195, 330, 60, 14), coin(195, 306, 60, 14), coin(195, 282, 60, 14), coin(195, 258, 60, 14)),
                     g(arrow(300, 250, 370, 250)),
                     g(box(390, 140, 170, 220, "#fff", 14, 6), T(475, 120, "며칠 뒤", 32, "#C8574F"), T(475, 270, "텅...", 40, "#9A9A9A"))],
    "leftover_zero": [g(box(170, 90, 320, 150, "#fff", 14, 6), T(330, 150, "남으면", 36), T(330, 205, "저축할게요", 36)),
                      g('<path d="M160 80 L500 250" stroke="#C8574F" stroke-width="10" stroke-linecap="round"/>'),
                      g(T(330, 340, "그런데...", 36, "#666"), T(330, 410, "늘 안 남았어요", 38, "#C8574F"))],
    "save_first": [g(box(170, 70, 320, 120, "#CFE8A9", 18, 6), T(220, 145, "①", 44, GREEN), T(360, 145, "저축", 40)),
                   g(arrow(330, 200, 330, 260)),
                   g(box(170, 270, 320, 120, "#fff", 18, 6), T(220, 345, "②", 44, GREEN), T(360, 345, "생활비", 40)),
                   g(T(330, 460, "순서만 바꿨어요", 34, GREEN))],
    "payday_auto": [g(box(120, 90, 220, 230, "#fff", 10, 6), '<rect x="120" y="90" width="220" height="56" fill="#2F4F3E" stroke="#333" stroke-width="6"/>',
                      T(230, 130, "월급날", 30, "#fff"), T(230, 250, "당일", 52)),
                    g(arrow(355, 205, 425, 205)),
                    g(box(435, 140, 130, 130, "#FFF1A8", 14, 6), T(500, 198, "저축", 30), T(500, 238, "통장", 30)),
                    g(T(340, 420, "자동이체가 먼저 가져가요", 30, GREEN))],
    "live_within": [g(box(160, 110, 340, 210, "#fff", 22, 6), '<rect x="160" y="110" width="340" height="60" rx="22" fill="#E8F2EA" stroke="#333" stroke-width="6"/>',
                      T(330, 152, "남은 돈", 32), T(330, 250, "= 이번 달 생활비", 36)),
                    g(T(330, 420, "그 안에서 맞춰요", 34, GREEN))],
    "save_jar": _jar(8, "저축 통장") + [g(box(380, 20, 210, 90, "#FFF1A8", 45, 5), T(485, 78, "차곡차곡", 38))],
    "transfer_date_app": [g(box(220, 40, 220, 440, "#fff", 34, 6), box(238, 90, 184, 320, "#F3F6FA", 10, 4), T(330, 75, "자동이체 목록", 20, "#666")),
                          g(box(250, 120, 160, 90, "#fff", 14, 3), T(330, 158, "저축 이체일", 24), T(330, 192, "월급날?", 26, "#C8574F")),
                          g(box(250, 230, 160, 70, "#FFF1A8", 14, 3), T(330, 275, "당일로 옮기기", 22))],
}


# ---------------------------------------------------------------- 색감 · 캐릭터 시안 (2026-11-13)
# 원고에 "theme" 과 "character" 를 넣으면 바꿔 그린다. 없으면 지금까지와 같다(green / sprout).
THEMES = {
    "green":    dict(bg="#1F3A2D", paper="#FBF8F1", rule="#C9D1DD", accent=GREEN, hl2="rgba(182,240,156,.85)", ring="#3d3d3d", label="딥그린"),
    "butter":   dict(bg="#F5CB4E", paper="#FFFEF8", rule="#EDE3C6", accent="#34507A", hl2="rgba(150,200,255,.7)", ring="#4a4a4a", label="버터 옐로"),
    "sky":      dict(bg="#8FC3E6", paper="#FFFFFF", rule="#D8E5EF", accent="#E2725B", hl2="rgba(255,180,160,.75)", ring="#4a4a4a", label="스카이 블루"),
    "charcoal": dict(bg="#2A2D34", paper="#FAF7F0", rule="#D6D2C8", accent="#3B5B8C", hl2="rgba(232,198,110,.75)", ring="#c9a24a", label="차콜 + 골드"),
}


def _hands(skin):
    return dict(
        open=(f'<circle r="19" fill="{skin}" stroke="{INK}" stroke-width="5"/>'
              f'<path d="M10 -14 L24 -30" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>'
              f'<path d="M10 -14 L24 -30" stroke="{skin}" stroke-width="4" stroke-linecap="round"/>'),
        fist=f'<circle r="19" fill="{skin}" stroke="{INK}" stroke-width="5"/>',
        thumb=(f'<circle r="19" fill="{skin}" stroke="{INK}" stroke-width="5"/>'
               f'<rect x="-30" y="-40" width="16" height="30" rx="8" transform="rotate(-35)" fill="{skin}" stroke="{INK}" stroke-width="5"/>'
               f'<path d="M-8 -8 L12 -8 M-8 2 L12 2" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'))


def _arm2(points, hand, cloth):
    d = "M" + " L".join(f"{x} {y}" for x, y in points)
    hx, hy = points[-1]
    return (f'<path d="{d}" stroke="{INK}" stroke-width="40" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" stroke="{cloth}" stroke-width="28" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<g transform="translate({hx} {hy})">{hand}</g>')


def _arms2(pose, cloth, skin):
    h = _hands(skin)
    table = {
        "point": ([(232, 300), (290, 262), (330, 236)], h["open"]),
        "think": ([(232, 305), (262, 360), (206, 268)], h["fist"]),
        "cheer": ([(232, 300), (282, 230), (296, 168)], h["thumb"]),
        "worry": ([(232, 305), (286, 240), (262, 128)], h["fist"]),
        "wave": ([(232, 300), (284, 240), (300, 178)], h["open"]),
    }
    pts, hand = table[pose]
    return _arm2([(88, 300), (70, 370), (84, 430)], h["fist"], cloth), _arm2(pts, hand, cloth)


def _body(cloth, collar="#fff"):
    return (f'<path d="M66 470 L76 312 Q86 258 160 252 Q234 258 244 312 L254 470 Z" fill="{cloth}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M132 256 L160 330 L188 256 Z" fill="{collar}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
            f'<circle cx="150" cy="362" r="6" fill="#E9DFC6"/><circle cx="150" cy="402" r="6" fill="#E9DFC6"/><circle cx="150" cy="442" r="6" fill="#E9DFC6"/>')


def _glasses(y=168, r=24, dx=32, sw=5):
    return (f'<circle cx="{160-dx}" cy="{y}" r="{r}" fill="rgba(255,255,255,.25)" stroke="{INK}" stroke-width="{sw}"/>'
            f'<circle cx="{160+dx}" cy="{y}" r="{r}" fill="rgba(255,255,255,.25)" stroke="{INK}" stroke-width="{sw}"/>'
            f'<path d="M{160-dx+r} {y-2} Q160 {y-8} {160+dx-r} {y-2}" fill="none" stroke="{INK}" stroke-width="{sw}"/>')


def _eyes(y=170, dx=32, r=8):
    return (f'<g class="eyes"><circle cx="{160-dx}" cy="{y}" r="{r}" fill="{INK}"/><circle cx="{160+dx}" cy="{y}" r="{r}" fill="{INK}"/>'
            f'<circle cx="{160-dx+3}" cy="{y-3}" r="2.6" fill="#fff"/><circle cx="{160+dx+3}" cy="{y-3}" r="2.6" fill="#fff"/></g>')


def _wrap(pose, back, body, head, cloth, skin):
    la, ra = _arms2(pose, cloth, skin)
    return (f'<svg class="chr" viewBox="0 0 360 470" overflow="visible"><g class="bob">{back}{body}{la}'
            f'<g class="head">{head}</g>{ra}{EXTRAS[pose]}</g></svg>')


def char_squirrel(pose, cloth):
    """안경 쓴 다람쥐 '도토리 멘토' — 도토리를 모으듯 차곡차곡."""
    fur, cream = "#C98552", "#FFF1DD"
    tail = (f'<path d="M232 440 Q338 430 332 300 Q326 190 268 150 Q300 230 262 268 Q228 300 242 360 Z" '
            f'fill="{fur}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M290 200 Q318 260 300 330" fill="none" stroke="#A8693C" stroke-width="5" stroke-linecap="round"/>')
    head = (f'<circle cx="96" cy="96" r="28" fill="{fur}" stroke="{INK}" stroke-width="6"/><circle cx="96" cy="98" r="13" fill="#F2AE9C"/>'
            f'<circle cx="224" cy="96" r="28" fill="{fur}" stroke="{INK}" stroke-width="6"/><circle cx="224" cy="98" r="13" fill="#F2AE9C"/>'
            f'<circle cx="160" cy="164" r="86" fill="{fur}" stroke="{INK}" stroke-width="6"/>'
            f'<ellipse cx="160" cy="200" rx="58" ry="44" fill="{cream}"/>'
            f'<path d="M150 118 Q160 96 170 118" fill="none" stroke="#A8693C" stroke-width="5" stroke-linecap="round"/>'
            f'{_eyes(166)}{_glasses(164, 25)}'
            f'<path d="M152 190 L168 190 L160 199 Z" fill="{INK}"/>'
            f'<ellipse cx="102" cy="204" rx="11" ry="7" fill="#F2AE9C" opacity=".8"/><ellipse cx="218" cy="204" rx="11" ry="7" fill="#F2AE9C" opacity=".8"/>'
            f'<g transform="translate(0 6)">{MOUTHS[pose]}</g>'
            f'<g transform="translate(228 70) rotate(18)"><ellipse cx="0" cy="8" rx="13" ry="16" fill="#B5793F" stroke="{INK}" stroke-width="4"/>'
            f'<path d="M-15 0 Q0 -16 15 0 Z" fill="#7A5230" stroke="{INK}" stroke-width="4"/></g>')
    return _wrap(pose, tail, _body(cloth, cream), head, cloth, cream)


def char_owl(pose, cloth):
    """학사모 쓴 부엉이 '부엉 멘토' — 똑똑하게 짚어 주는 역할."""
    fur, face = "#8A6A52", "#F6E8D2"
    head = (f'<path d="M88 104 L80 52 L122 86 Z" fill="{fur}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M232 104 L240 52 L198 86 Z" fill="{fur}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
            f'<ellipse cx="160" cy="168" rx="94" ry="88" fill="{fur}" stroke="{INK}" stroke-width="6"/>'
            f'<circle cx="126" cy="166" r="40" fill="{face}"/><circle cx="194" cy="166" r="40" fill="{face}"/>'
            f'{_eyes(168, 34, 10)}{_glasses(166, 30, 34)}'
            f'<path d="M150 198 L170 198 L160 218 Z" fill="#F0A93B" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
            f'<ellipse cx="96" cy="214" rx="11" ry="7" fill="#F2AE9C" opacity=".8"/><ellipse cx="224" cy="214" rx="11" ry="7" fill="#F2AE9C" opacity=".8"/>'
            f'<g transform="rotate(-8 160 70)"><path d="M100 72 L160 46 L220 72 L160 98 Z" fill="#2E2E2E" stroke="{INK}" stroke-width="4"/>'
            f'<rect x="132" y="78" width="56" height="20" fill="#2E2E2E"/>'
            f'<path d="M160 72 L214 92 L214 118" stroke="#E2B640" stroke-width="5" fill="none"/><circle cx="214" cy="122" r="7" fill="#E2B640"/></g>')
    body = _body(cloth, face)
    return _wrap(pose, "", body, head, cloth, face)


def char_pony(pose, cloth):
    """포니테일 '똑똑 멘토' — 사각 안경, 귀에 꽂은 연필."""
    hair = "#3E2F28"
    back = (f'<path d="M226 96 Q312 92 300 210 Q292 272 252 290 Q276 220 236 150 Z" fill="{hair}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
            f'<circle cx="236" cy="100" r="12" fill="#E2B640" stroke="{INK}" stroke-width="4"/>')
    head = (f'<circle cx="160" cy="166" r="86" fill="{SKIN}" stroke="{INK}" stroke-width="6"/>'
            f'<path d="M74 170 Q62 74 160 72 Q256 74 246 170 Q236 116 196 104 Q150 142 92 128 Q80 146 74 170 Z" fill="{hair}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
            f'{_eyes(172, 34, 9)}'
            f'<rect x="96" y="148" width="58" height="46" rx="14" fill="rgba(255,255,255,.25)" stroke="{INK}" stroke-width="5"/>'
            f'<rect x="166" y="148" width="58" height="46" rx="14" fill="rgba(255,255,255,.25)" stroke="{INK}" stroke-width="5"/>'
            f'<path d="M154 166 L166 166" stroke="{INK}" stroke-width="5"/>'
            f'<ellipse cx="100" cy="212" rx="12" ry="7" fill="#F2AE9C" opacity=".8"/><ellipse cx="220" cy="212" rx="12" ry="7" fill="#F2AE9C" opacity=".8"/>'
            f'{MOUTHS[pose]}'
            f'<g transform="translate(70 150) rotate(-35)"><rect x="-6" y="-34" width="12" height="60" fill="#F4CF4C" stroke="{INK}" stroke-width="4"/>'
            f'<path d="M-6 26 L0 40 L6 26 Z" fill="#E9C9A0" stroke="{INK}" stroke-width="4"/></g>')
    return _wrap(pose, back, _body(cloth), head, cloth, SKIN)


CHARACTERS = {"squirrel": char_squirrel, "owl": char_owl, "pony": char_pony}


def theme_of(spec):
    name = spec.get("theme", "green")
    if name not in THEMES:
        raise nb.SpecError(f"색감 '{name}' 이 없습니다. 쓸 수 있는 색감: {', '.join(THEMES)}")
    return THEMES[name]


def draw_character(spec, pose):
    kind = spec.get("character", "sprout")
    pose = pose if pose in ARMS else "point"
    if kind == "sprout":
        svg = character(pose)
        th = theme_of(spec)
        return svg.replace(GREEN, th["accent"])
    if kind not in CHARACTERS:
        raise nb.SpecError(f"캐릭터 '{kind}' 가 없습니다. 쓸 수 있는 캐릭터: sprout, {', '.join(CHARACTERS)}")
    return CHARACTERS[kind](pose, theme_of(spec)["accent"])


def theme_css(spec):
    th = theme_of(spec)
    return (f":root{{--bg:{th['bg']};--paper:{th['paper']};--rule:{th['rule']};--grn:{th['hl2']}}}"
            f".ring{{border-color:{th['ring']}}}")


# 첫 화면 훅: 장면에 "big" 을 넣으면 큰 글씨가 첫 프레임부터 바로 보이고, lines 는 그 아래 작은 글씨로 써진다.
HOOK_CSS = """
.big{position:absolute;left:120px;right:90px;top:{HY}px;font:700 {HF}px/1.12 Hand;color:var(--ink);text-align:center;letter-spacing:-2px}
.big .hl{background:linear-gradient(transparent 55%, var(--yel) 55%, var(--yel) 96%, transparent 96%);padding:0 10px}
.big small{display:block;font-size:{HS}px;color:#555;letter-spacing:0;margin-top:14px}
.scene.hook .body{top:{HB}px;text-align:center;right:90px;left:120px;font-size:{HBF}px}
.scene.hook .art{top:{HA}px}
"""
HOOK_LAYOUT = {"reel": dict(HY=250, HF=170, HS=52, HB=760, HBF=66, HA=930),
               "card": dict(HY=170, HF=130, HS=42, HB=560, HBF=54, HA=720)}


def hook_html(sc):
    rows = [re_hl(row) for row in sc["big"].split("|")]
    sub = f'<small>{html.escape(sc["bigsub"])}</small>' if sc.get("bigsub") else ""
    return f'<div class="big">{"<br>".join(rows)}{sub}</div>'


def re_hl(row):
    out = []
    for piece in nb.TOKEN_RE.split(row):
        if not piece:
            continue
        if piece[:2] in ("==", "++", "((") and len(piece) > 4:
            out.append(f'<span class="hl">{html.escape(piece[2:-2])}</span>')
        else:
            out.append(html.escape(piece))
    return "".join(out)

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
    hook_css = HOOK_CSS
    for k, v in HOOK_LAYOUT[mode].items():
        hook_css = hook_css.replace("{" + k + "}", str(v))
    doc = doc.replace("</style>", css + hook_css + theme_css(spec) + "</style>")
    # 장면마다 그림·캐릭터를 끼워 넣는다 (장면 div 의 끝 바로 앞).
    for si, sc in enumerate(spec["scenes"]):
        art = sc.get("art")
        if art and art not in ART:
            raise nb.SpecError(f"그림 '{art}' 이 없습니다. 쓸 수 있는 그림: {', '.join(ART)}")
        accent = theme_of(spec)["accent"]
        art_svg = (f'<svg class="art" viewBox="0 0 600 520">{"".join(ART[art])}</svg>'.replace(GREEN, accent)) if art else ""
        marker = f'<div class="scene" data-s="{si}" style="display:none">'
        if sc.get("big"):
            new_marker = f'<div class="scene hook" data-s="{si}" data-hook="1" style="display:none">'
            doc = doc.replace(marker, new_marker + hook_html(sc) + art_svg + draw_character(spec, sc.get("pose", "point")), 1)
        else:
            doc = doc.replace(marker, marker + art_svg + draw_character(spec, sc.get("pose", "point")), 1)
    return doc


SEEK_JS = nb.SEEK_JS.rstrip()[:-1] + """
  const el = args[3], t = args[4];
  const gt = document.querySelector('.paper > .title');
  if (gt) gt.style.visibility = sc.dataset.hook ? 'hidden' : 'visible';
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
    if spec.get("timing"):
        return _timed_schedule(spec)
    out, t = [], (0.0 if spec["scenes"][0].get("big") else 0.4)
    base = nb.schedule(spec)
    for i, (s, te, me, e) in enumerate(base):
        dur = max(e - s, MIN_SCENE_S + (1.0 if i == len(base) - 1 else 0))
        out.append((t, t + (te - s), t + (me - s), t + dur))
        t = t + dur + nb.GAP_S
    return out


def _timed_schedule(spec):
    """녹음에 맞춘 장면 시간. spec["timing"] = [[시작, 끝], ...] (초, 영상 기준). 타이핑은 시작부터 같은 속도."""
    tm = spec["timing"]
    if len(tm) != len(spec["scenes"]):
        raise nb.SpecError("timing 개수가 장면 수와 다릅니다")
    out = []
    for sc, (s, e) in zip(spec["scenes"], tm):
        n = sum(nb._chars(l) for l in sc["lines"])
        marks = sum(len(nb.TOKEN_RE.findall(l)) for l in sc["lines"])
        te = min(s + n / nb.TYPE_CPS, e - 0.2)
        me = min(te + (nb.MARK_S + 0.1) * marks, e - 0.05)
        out.append((s, te, me, e))
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
