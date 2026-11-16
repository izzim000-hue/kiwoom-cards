#!/usr/bin/env python3
"""두 사람 비교 스토리 릴스 생성기 (2026-11-16).

노트 템플릿(notebook.py)이 '장면마다 새 페이지 + 글 + 캐릭터가 가리키기' 라서 강의처럼 보이는 문제를 풀려고 만든 형식.
조건이 같은 가상 인물 두 명을 좌우 화면에 세워 두고, 같은 화면 위에 요소가 하나씩 쌓이며 차이가 벌어지는 걸 보여 준다.
설명 대신 장면과 결과로 느끼게 하고, 결론은 끝에 한 번만 말한다.

    python3 tools/duo.py reel  SPEC.json OUT.mp4      # 음악 없는 MP4 (1080x1920, 30fps)
    python3 tools/duo.py still SPEC.json OUT_DIR      # 장면마다 끝 화면 PNG (점검용)

원고(SPEC) 형식은 sources/duo/README.md 참고.
"""

import argparse
import html
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notebook_char as nc  # noqa: E402  (새싹 멘토 캐릭터)
from reelkit import browser  # noqa: E402
from reelkit.encode import EncodeError, PipeEncoder  # noqa: E402

FPS = 30
W, H = 1080, 1920
FONTS = (Path(__file__).resolve().parent / "fonts").as_uri()
INK = "#333"
SKIN = "#FFE9D6"
HL = re.compile(r"==(.+?)==")


class SpecError(ValueError):
    pass


# ---------------------------------------------------------------- 사람 그림 (가상 인물 두 명)
LOOKS = {
    # 왼쪽: 짧은 머리, 회색 셔츠 / 오른쪽: 단발, 남색 니트 (새싹 멘토의 딥그린과 겹치지 않게)
    "a": dict(cloth="#8A95A3", hair="#2F2A28", style="short"),
    "b": dict(cloth="#3F5F8F", hair="#5A4034", style="bob"),
}

MOUTH = {
    "calm": '<path d="M144 218 Q160 230 176 218" stroke="#333" stroke-width="5" fill="none" stroke-linecap="round"/>',
    "smile": '<path d="M138 212 Q160 240 182 212 Z" fill="#C8574F" stroke="#333" stroke-width="5" stroke-linejoin="round"/>',
    "flat": '<path d="M146 222 L174 220" stroke="#333" stroke-width="5" stroke-linecap="round"/>',
    "worry": '<path d="M140 224 Q150 214 160 224 Q170 234 180 224" stroke="#333" stroke-width="5" fill="none" stroke-linecap="round"/>',
    "oh": '<ellipse cx="160" cy="222" rx="10" ry="13" fill="#7A3E39" stroke="#333" stroke-width="4"/>',
}
BROWS = {
    "worry": '<path d="M106 136 L142 146 M214 136 L178 146" stroke="#333" stroke-width="5" stroke-linecap="round"/>',
    "oh": '<path d="M108 132 Q126 120 144 130 M176 130 Q194 120 212 132" stroke="#333" stroke-width="5" fill="none" stroke-linecap="round"/>',
}

PHONE = ('<g transform="translate(-30 -58) rotate(-8)"><rect width="60" height="100" rx="10" fill="#2E2E2E" stroke="#333" stroke-width="4"/>'
         '<rect x="7" y="10" width="46" height="72" rx="4" fill="#BFE3FF"/></g>')
CARD = ('<g transform="translate(-6 -46) rotate(-14)"><rect width="86" height="56" rx="8" fill="#E86F5A" stroke="#333" stroke-width="4"/>'
        '<rect x="10" y="12" width="20" height="14" rx="3" fill="#F4CF4C"/></g>')
BOOK = ('<g transform="translate(-10 -60) rotate(6)"><rect width="64" height="86" rx="6" fill="#4E8F6E" stroke="#333" stroke-width="4"/>'
        '<path d="M12 24 H52 M12 40 H44" stroke="#fff" stroke-width="5" stroke-linecap="round"/></g>')
HAND = '<circle r="19" fill="{s}" stroke="#333" stroke-width="5"/>'

# 포즈: (오른팔 경로, 오른손에 든 것, 왼팔 경로, 입, 덧그림)
POSES = {
    "stand": ([(232, 300), (262, 380), (252, 440)], "", [(88, 300), (64, 380), (76, 440)], "calm", ""),
    "phone": ([(232, 300), (282, 300), (238, 214)], PHONE, [(88, 300), (64, 380), (76, 440)], "flat", ""),
    "card": ([(232, 300), (296, 300), (330, 262)], CARD, [(88, 300), (64, 380), (76, 440)], "calm", ""),
    "book": ([(232, 300), (296, 300), (330, 262)], BOOK, [(88, 300), (64, 380), (76, 440)], "smile", ""),
    "worry": ([(232, 305), (286, 240), (252, 120)], "", [(88, 305), (34, 240), (68, 120)], "worry",
              '<path d="M286 150 Q274 172 286 182 Q298 172 286 150 Z" fill="#9CC9EE" stroke="#333" stroke-width="4"/>'),
    "happy": ([(232, 300), (282, 230), (296, 168)], "", [(88, 300), (64, 380), (76, 440)], "smile",
              '<path d="M318 120 l14 -16 M330 156 l22 -4 M30 150 l-20 -8" stroke="#333" stroke-width="5" stroke-linecap="round"/>'),
    "sigh": ([(232, 300), (250, 380), (200, 420)], "", [(88, 300), (110, 380), (160, 420)], "worry",
             '<path d="M268 230 q22 -6 30 8 q8 14 30 6" stroke="#333" stroke-width="4" fill="none" stroke-linecap="round"/>'),
    "oh": ([(232, 300), (262, 380), (252, 440)], "", [(88, 300), (64, 380), (76, 440)], "oh",
           '<text x="276" y="120" font-size="70" font-weight="700" fill="#333" font-family="Hand">!</text>'),
}


def _arm(points, hand, cloth, held=""):
    d = "M" + " L".join(f"{x} {y}" for x, y in points)
    hx, hy = points[-1]
    return (f'<path d="{d}" stroke="#333" stroke-width="40" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" stroke="{cloth}" stroke-width="28" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<g transform="translate({hx} {hy})">{held}{hand}</g>')


def person(look, pose):
    lk = LOOKS[look]
    if pose not in POSES:
        raise SpecError(f"포즈 '{pose}' 가 없습니다. 쓸 수 있는 포즈: {', '.join(POSES)}")
    ra, held, la, mouth, extra = POSES[pose]
    hand = HAND.format(s=SKIN)
    hair, cloth = lk["hair"], lk["cloth"]
    if lk["style"] == "short":
        back = ""
        front = (f'<path d="M78 160 Q70 78 160 74 Q252 78 242 160 Q232 112 200 104 Q170 122 120 112 Q92 124 78 160 Z" '
                 f'fill="{hair}" stroke="#333" stroke-width="5" stroke-linejoin="round"/>')
    else:
        back = (f'<path d="M70 170 Q58 72 160 66 Q262 72 250 170 Q258 226 262 250 Q232 262 210 248 L110 248 Q88 262 58 250 Q62 226 70 170 Z" '
                f'fill="{hair}" stroke="#333" stroke-width="6" stroke-linejoin="round"/>')
        front = (f'<path d="M80 166 Q72 82 160 78 Q248 82 240 166 Q226 120 180 108 Q150 134 96 128 Q86 144 80 166 Z" '
                 f'fill="{hair}" stroke="#333" stroke-width="5" stroke-linejoin="round"/>')
    body = (f'<path d="M66 470 L76 312 Q86 258 160 252 Q234 258 244 312 L254 470 Z" fill="{cloth}" stroke="#333" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M136 256 Q160 290 184 256" fill="#fff" stroke="#333" stroke-width="5"/>')
    head = (f'<circle cx="160" cy="166" r="84" fill="{SKIN}" stroke="#333" stroke-width="6"/>{front}'
            f'<g class="eyes"><circle cx="128" cy="172" r="8" fill="#333"/><circle cx="192" cy="172" r="8" fill="#333"/></g>'
            f'{BROWS.get(mouth, "")}'
            f'<ellipse cx="104" cy="206" rx="11" ry="7" fill="#F2AE9C" opacity=".75"/>'
            f'<ellipse cx="216" cy="206" rx="11" ry="7" fill="#F2AE9C" opacity=".75"/>{MOUTH[mouth]}')
    return (f'<g class="bob">{back}{body}{_arm(la, hand, cloth)}<g class="head">{head}</g>'
            f'{_arm(ra, hand, cloth, held)}{extra}</g>')


# ---------------------------------------------------------------- 작은 아이콘 (태그 앞에 붙는다)
ICONS = {
    "cal": ('<rect x="6" y="12" width="52" height="46" rx="6" fill="#fff" stroke="#333" stroke-width="4"/>'
            '<rect x="6" y="12" width="52" height="14" rx="6" fill="#E86F5A" stroke="#333" stroke-width="4"/>'
            '<text x="32" y="53" font-size="24" text-anchor="middle" font-weight="700" fill="#333" font-family="Hand">25</text>'),
    "card": ('<rect x="4" y="16" width="56" height="36" rx="6" fill="#E86F5A" stroke="#333" stroke-width="4"/>'
             '<rect x="12" y="24" width="14" height="10" rx="2" fill="#F4CF4C"/>'),
    "bank": ('<rect x="10" y="6" width="44" height="54" rx="5" fill="#4E8F6E" stroke="#333" stroke-width="4"/>'
             '<path d="M18 22 H46 M18 34 H40" stroke="#fff" stroke-width="4" stroke-linecap="round"/>'),
    "wallet": ('<rect x="4" y="16" width="56" height="40" rx="8" fill="#C9A26B" stroke="#333" stroke-width="4"/>'
               '<rect x="38" y="28" width="22" height="16" rx="5" fill="#E8D2A8" stroke="#333" stroke-width="4"/>'),
    "car": ('<path d="M6 44 L10 30 Q14 20 24 20 L42 20 Q50 20 54 30 L58 44 Z" fill="#6A8CB8" stroke="#333" stroke-width="4" stroke-linejoin="round"/>'
            '<circle cx="18" cy="48" r="7" fill="#333"/><circle cx="46" cy="48" r="7" fill="#333"/>'),
    "arrow": '<path d="M8 32 H50 M36 18 L52 32 L36 46" stroke="#333" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
    "zero": ('<circle cx="32" cy="32" r="24" fill="#fff" stroke="#333" stroke-width="4"/>'
             '<text x="32" y="44" font-size="32" text-anchor="middle" font-weight="700" fill="#C8574F" font-family="Hand">0</text>'),
}


def icon(name):
    if not name:
        return ""
    if name not in ICONS:
        raise SpecError(f"아이콘 '{name}' 이 없습니다. 쓸 수 있는 아이콘: {', '.join(ICONS)}")
    return f'<svg class="ic" viewBox="0 0 64 64">{ICONS[name]}</svg>'


def rich(text):
    """==강조== 를 형광펜으로. 나머지는 이스케이프."""
    out, pos = [], 0
    for m in HL.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        out.append(f'<span class="hl">{html.escape(m.group(1))}</span>')
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return "".join(out).replace("|", "<br>")


# ---------------------------------------------------------------- 화면
CSS = """
@font-face{font-family:Hand;src:url("{FONTS}/PoorStory-Regular.ttf")}
@font-face{font-family:Noto;src:url("{FONTS}/NotoSansKR-Regular.otf")}
@font-face{font-family:NotoB;src:url("{FONTS}/NotoSansKR-Bold.otf")}
:root{--bg:#F5CB4E;--ink:#333;--navy:#34507A;--paper:#FFFEF8;--yel:rgba(255,214,60,.9);--red:#C8574F;--grn:#3E7C5B}
html,body{word-break:keep-all;margin:0;width:1080px;height:1920px;overflow:hidden;background:var(--bg);font-family:Hand;color:var(--ink)}
.dots{position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.28) 2.5px,transparent 3px);background-size:36px 36px}
.top{position:absolute;left:0;right:0;top:118px;text-align:center}
.badge{display:inline-block;font:26px NotoB;color:#6b5a1e;background:rgba(255,255,255,.55);border-radius:30px;padding:6px 20px}
.ttl{font:700 66px/1.1 Hand;margin-top:10px;letter-spacing:-1px}
.panel{position:absolute;top:290px;height:1010px;width:488px;background:var(--paper);border:5px solid var(--ink);border-radius:34px;box-sizing:border-box;
 box-shadow:0 10px 0 rgba(0,0,0,.12);transition:none}
.panel.L{left:36px}.panel.R{left:556px}
.panel .head{position:absolute;left:0;right:0;top:-34px;text-align:center}
.name{display:inline-block;font:700 46px Hand;background:#fff;border:5px solid var(--ink);border-radius:40px;padding:4px 28px}
.name small{font-size:32px;color:#666;margin-left:6px}
.fig{position:absolute;left:84px;bottom:14px;width:320px;height:418px;overflow:visible}
.it{position:absolute;left:0;right:0;text-align:center;opacity:0}
.tag{display:inline-flex;align-items:center;gap:10px;font:700 44px/1.15 Hand;background:#fff;border:4px solid var(--ink);border-radius:22px;padding:8px 18px;max-width:456px;box-sizing:border-box}
.tag.navy{background:var(--navy);color:#fff;border-color:var(--navy)}
.tag.red{border-color:var(--red);color:var(--red)}
.tag.grn{border-color:var(--grn);color:var(--grn)}
.tag.ghost{background:transparent;border-style:dashed;color:#555}
.ic{width:52px;height:52px;flex:none}
.src{font:22px/1.3 Noto;color:#7a7a7a;margin-top:6px}
.money .lab{font:700 34px Hand;color:#555}
.money .val{font:700 86px/1.05 Hand;letter-spacing:-1px}
.money .val.red{color:var(--red)}.money .val.grn{color:var(--grn)}
.jar{position:relative;display:inline-block;width:190px;height:196px;margin-top:22px}
.jar .glass{position:absolute;inset:0;border:5px solid var(--ink);border-radius:26px 26px 34px 34px;background:#fff;overflow:hidden}
.jar .fill{position:absolute;left:0;right:0;bottom:0;height:0;background:linear-gradient(#F7D560,#E9B93A)}
.jar .lid{position:absolute;left:30px;right:30px;top:-22px;height:22px;background:#C9A26B;border:5px solid var(--ink);border-radius:8px}
.jar .lbl{position:absolute;left:0;right:0;top:64px;font:700 50px Hand;text-align:center}
.eq{position:absolute;left:510px;top:390px;width:60px;height:60px;border-radius:50%;background:#fff;border:5px solid var(--ink);box-sizing:border-box;
 font:700 52px/46px Hand;text-align:center;opacity:0;z-index:3}
.vs{position:absolute;left:510px;top:390px;width:60px;height:60px;border-radius:50%;background:var(--red);color:#fff;border:5px solid var(--ink);box-sizing:border-box;
 font:700 40px/50px Hand;text-align:center;opacity:0;z-index:3}
.center{position:absolute;left:60px;right:60px;text-align:center;opacity:0;z-index:5}
.box{display:inline-block;background:#fff;border:5px solid var(--ink);border-radius:28px;padding:24px 38px;font:700 62px/1.3 Hand;box-shadow:0 10px 0 rgba(0,0,0,.15)}
.box.dark{background:#2B2B2B;color:#fff;border-color:#2B2B2B}
.hl{background:linear-gradient(transparent 52%,var(--yel) 52%,var(--yel) 94%,transparent 94%);padding:0 6px}
.box.dark .hl{background:none;color:#FFD84D}
.hook{position:absolute;left:40px;right:40px;top:300px;text-align:center;z-index:6}
.hook .big{display:inline-block;background:#fff;border:6px solid var(--ink);border-radius:36px;padding:30px 30px 26px;font:700 112px/1.12 Hand;letter-spacing:-3px;
 box-shadow:0 14px 0 rgba(0,0,0,.18)}
.hook .big small{display:block;font-size:46px;letter-spacing:0;color:#555;margin-top:10px}
.mentor{position:absolute;left:50%;top:0;width:250px;margin-left:-125px;overflow:visible}
.sub{position:absolute;left:30px;right:30px;top:1366px;text-align:center}
.sub span{display:inline-block;background:#2B2B2B;color:#fff;font:700 50px/1.32 Hand;border-radius:22px;padding:12px 30px;max-width:980px;box-sizing:border-box}
.sub .hl{background:none;color:#FFD84D;padding:0}
.foot{position:absolute;left:0;right:0;top:1314px;text-align:center;font:24px Noto;color:#6b5a1e}
"""


def item_html(it):
    kind = it.get("type", "tag")
    style = it.get("style", "")
    src = f'<div class="src">{html.escape(it["src"])}</div>' if it.get("src") else ""
    if kind == "tag":
        inner = f'<span class="tag {style}">{icon(it.get("icon"))}<span>{rich(it["text"])}</span></span>'
    elif kind == "money":
        cu = ' data-count="1"' if it.get("count") else ""
        inner = (f'<div class="money"><div class="lab">{html.escape(it.get("label", ""))}</div>'
                 f'<div class="val {style}"{cu} data-v="{html.escape(it["value"])}">{html.escape(it["value"])}</div></div>')
    elif kind == "jar":
        inner = (f'<div class="jar" data-fill="{float(it.get("fill", 0))}"><div class="lid"></div><div class="glass"><div class="fill"></div></div>'
                 f'<div class="lbl" data-count="1" data-v="{html.escape(it["value"])}">{html.escape(it["value"])}</div></div>'
                 f'<div class="money"><div class="lab">{html.escape(it.get("label", ""))}</div></div>')
    else:
        raise SpecError(f"항목 종류 '{kind}' 를 모릅니다 (tag / money / jar)")
    return inner + src


def page_html(spec):
    items = spec.get("items", {})
    beats = spec["beats"]
    css = CSS.replace("{FONTS}", FONTS)
    L, R = spec["left"], spec["right"]
    parts = [f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="dots"></div>',
             f'<div class="top"><span class="badge">{html.escape(spec.get("badge", "가상 인물 · 예시"))}</span>'
             f'<div class="ttl">{rich(spec["title"])}</div></div>']
    for side, p in (("L", L), ("R", R)):
        figs = "".join(f'<g class="pose" data-p="{po}" style="display:none">{person(p["look"], po)}</g>' for po in POSES)
        own = "".join(f'<div class="it" data-id="{iid}" style="top:{it["y"]}px">{item_html(it)}</div>'
                      for iid, it in items.items() if it.get("side") == side)
        parts.append(f'<div class="panel {side}" data-side="{side}"><div class="head"><span class="name">{html.escape(p["name"])}'
                     f'<small>{html.escape(p.get("age", ""))}</small></span></div>{own}'
                     f'<svg class="fig" viewBox="0 0 360 470" overflow="visible">{figs}</svg></div>')
    parts.append('<div class="eq" data-id="eq">=</div><div class="vs" data-id="vs">≠</div>')
    for iid, it in items.items():
        if it.get("side") != "C":
            continue
        mentor = ""
        if it.get("mentor"):
            mentor = f'<svg class="mentor" style="top:{it.get("mentor_y", -250)}px" viewBox="0 0 360 470" overflow="visible">{nc.character(it.get("mentor_pose", "wave"))}</svg>'
        cls = "box dark" if it.get("style") == "dark" else "box"
        parts.append(f'<div class="center it" data-id="{iid}" style="top:{it["y"]}px">{mentor}<div class="{cls}">{rich(it["text"])}</div>{("<div class=src>" + html.escape(it["src"]) + "</div>") if it.get("src") else ""}</div>')
    hook = spec.get("hook")
    if hook:
        sub = f'<small>{html.escape(hook["sub"])}</small>' if hook.get("sub") else ""
        parts.append(f'<div class="hook" data-id="hook"><div class="big">{rich(hook["big"])}{sub}</div></div>')
    for bi, b in enumerate(beats):
        parts.append(f'<div class="sub" data-b="{bi}" style="opacity:0"><span>{rich(b["say"])}</span></div>')
    parts.append(f'<div class="foot">{html.escape(spec.get("foot", ""))}</div></body></html>')
    return "".join(parts)


# ---------------------------------------------------------------- 시간표
def beat_len(b):
    if "d" in b:
        return float(b["d"])
    n = len(HL.sub(r"\1", b["say"]).replace(" ", ""))
    return max(3.4, round(n / 7.0 + 1.0, 2))  # 녹음 속도(초당 약 7자) + 여유


def timeline(spec):
    """beats -> [{start,end,show:set,hide:set,pose,focus}] 와 각 항목의 등장 시각."""
    t, out, appear = 0.0, [], {}
    visible = set()
    for b in spec["beats"]:
        d = beat_len(b)
        for iid in b.get("hide", []):
            visible.discard(iid)
        for k, iid in enumerate(b.get("show", [])):
            if iid not in spec.get("items", {}) and iid not in ("eq", "vs", "hook"):
                raise SpecError(f"show 에 없는 항목: {iid}")
            appear.setdefault(iid, (len(out), t + 0.25 + 0.35 * k))
            visible.add(iid)
        out.append(dict(start=t, end=t + d, vis=sorted(visible), pose=b.get("pose", {}), focus=b.get("focus")))
        t += d
    return out, appear


SEEK_JS = """(st) => {
  const ease = x => { x = Math.max(0, Math.min(1, x)); const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
  const lin = x => Math.max(0, Math.min(1, x));
  document.querySelectorAll('[data-id]').forEach(el => {
    const id = el.dataset.id, a = st.appear[id], h = st.hidden[id];
    if (a === undefined || st.t < a) { el.style.opacity = 0; return; }
    let p = (st.t - a) / 0.38, o = lin(p);
    if (h !== undefined && st.t >= h) o = 1 - lin((st.t - h) / 0.3);
    el.style.opacity = o;
    el.style.transform = 'translateY(' + ((1 - lin(p)) * 26).toFixed(1) + 'px) scale(' + (0.86 + 0.14 * ease(p)).toFixed(3) + ')';
    const fp = lin((st.t - a - 0.2) / 1.1);
    el.querySelectorAll('[data-count]').forEach(c => {
      const v = c.dataset.v, m = v.match(/[0-9][0-9,]*/);
      if (!m) return;
      const n = parseInt(m[0].replace(/,/g, ''), 10), k = Math.round(n * (1 - Math.pow(1 - fp, 3)));
      c.textContent = v.replace(m[0], k.toLocaleString('ko-KR'));
    });
    el.querySelectorAll('.jar').forEach(j => { j.querySelector('.fill').style.height = (parseFloat(j.dataset.fill) * 100 * (1 - Math.pow(1 - fp, 3))).toFixed(1) + '%'; });
  });
  document.querySelectorAll('.panel').forEach(pn => {
    const s = pn.dataset.side, pose = st.pose[s] || 'stand';
    pn.querySelectorAll('.pose').forEach(g => g.style.display = g.dataset.p === pose ? '' : 'none');
    const dim = st.focus && st.focus !== s;  // focus 'C' 는 두 칸 모두 흐리게
    pn.style.opacity = dim ? 0.5 : 1;
    pn.style.filter = dim ? 'saturate(.4)' : '';
    const bob = pn.querySelector('.pose[data-p="' + pose + '"] .bob');
    if (bob) bob.setAttribute('transform', 'translate(0 ' + (Math.sin(st.t * 2.4 + (s === 'L' ? 0 : 1.3)) * 4).toFixed(2) + ')');
    const ph = (st.t + (s === 'L' ? 0 : 1.7)) % 3.6;
    pn.querySelectorAll('.eyes').forEach(e => e.setAttribute('transform', ph < 0.12 ? 'translate(0 155) scale(1 0.1)' : ''));
  });
  document.querySelectorAll('.sub').forEach(s => {
    const b = +s.dataset.b; s.style.opacity = b === st.beat ? lin((st.t - st.bstart) / 0.15) : 0;
  });
  const mb = document.querySelector('.mentor .bob');
  if (mb) mb.setAttribute('transform', 'translate(0 ' + (Math.sin(st.t * 2.6) * 5).toFixed(2) + ')');
}"""


def state_at(spec, tl, appear, t):
    bi = next((i for i, b in enumerate(tl) if b["start"] <= t < b["end"]), len(tl) - 1)
    ap, hid = {}, {}
    for iid, (b, a) in appear.items():
        if b > bi:
            continue
        ap[iid] = a
        for j in range(b + 1, len(tl)):  # 다시 사라지는 첫 beat
            if iid not in tl[j]["vis"]:
                hid[iid] = tl[j]["start"]
                break
    pose = {}
    for j in range(bi + 1):
        pose.update(spec["beats"][j].get("pose", {}))
    if spec.get("hook"):  # 첫 화면 훅: 0초부터 보이고 첫 beat 끝에 사라진다
        ap["hook"] = -1
        hid["hook"] = tl[0]["end"] - 0.3
    return dict(t=t, beat=bi, bstart=tl[bi]["start"], appear=ap, hidden=hid, pose=pose, focus=tl[bi]["focus"])


def load(path):
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SpecError(f"원고를 읽지 못했습니다: {e}") from e
    for k in ("title", "left", "right", "beats"):
        if k not in spec:
            raise SpecError(f"원고에 '{k}' 가 없습니다")
    return spec


def _open(pw, spec, work):
    b, _ = browser.launch(pw)
    page = b.new_page(viewport={"width": W, "height": H})
    f = Path(work) / "page.html"
    f.write_text(page_html(spec), encoding="utf-8")
    page.goto(f.as_uri())
    page.evaluate("document.fonts.ready")
    status = page.evaluate("[...document.fonts].map(f => f.family + ':' + f.status)")
    if any(not s.endswith("loaded") for s in status if s.startswith("Hand")):
        raise browser.FontLoadError(f"손글씨 폰트를 불러오지 못했습니다: {status}")
    return b, page


def render_reel(spec, out):
    from playwright.sync_api import sync_playwright
    tl, appear = timeline(spec)
    total = tl[-1]["end"]
    with tempfile.TemporaryDirectory(prefix="duo-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, work)
        enc = PipeEncoder(out)
        try:
            for i in range(int(round(total * FPS))):
                page.evaluate(SEEK_JS, state_at(spec, tl, appear, i / FPS))
                enc.write(page.screenshot(type="png"))
            enc.close()
        except BaseException:
            enc.abort()
            raise
        finally:
            b.close()
    return total, tl


def render_stills(spec, out_dir):
    from playwright.sync_api import sync_playwright
    tl, appear = timeline(spec)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with tempfile.TemporaryDirectory(prefix="duo-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, work)
        try:
            for i, bt in enumerate(tl):
                for tag, t in (("a", bt["start"] + 0.02), ("z", bt["end"] - 0.05)):
                    if tag == "a" and i:
                        continue
                    page.evaluate(SEEK_JS, state_at(spec, tl, appear, t))
                    p = out_dir / f"beat_{i + 1:02d}{tag}.png"
                    page.screenshot(path=str(p))
                    paths.append(p)
        finally:
            b.close()
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description="두 사람 비교 스토리 릴스 (음악 없음)")
    ap.add_argument("mode", choices=["reel", "still"])
    ap.add_argument("spec")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    try:
        spec = load(a.spec)
        if a.mode == "reel":
            total, tl = render_reel(spec, a.out)
            print(f"duration={total:.1f}s")
            for i, (bt, b) in enumerate(zip(tl, spec["beats"])):
                print(f"{bt['start']:5.1f}-{bt['end']:5.1f}s  {HL.sub(lambda m: m.group(1), b['say'])}")
        else:
            for p in render_stills(spec, a.out):
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
