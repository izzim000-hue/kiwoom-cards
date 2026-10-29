"""프레임 마크업. legacy 는 게시된 MP4 10편을 재현하는 배치(D-05), new 는 안전영역 배치(D-01~D-04)다."""
import html as _html
from dataclasses import dataclass

from .constants import (SAGE, DG, GOLD, MUT, ACCOUNT, W, H, SAFE, BASIS_PX, BASIS_MAX_LINES, ACCT_PX)


def legacy_inner_html(top, lines, k, prog, basis):
    """기존 reel.py frame() 과 같은 마크업(<body> 래퍼 제외).

    바뀐 점 두 가지: 글꼴은 번들 'Noto Sans KR', <s> 는 블록 줄(display:block).
    top 과 basis 는 원문 그대로 삽입한다(기존 동작 유지, 허용 목록 검사는 spec 단계).
    """
    out = ""
    for i, l in enumerate(lines):
        l = (l.replace("<g>", f'<span style="color:{GOLD}">').replace("</g>", "</span>")
              .replace("<s>", f'<span style="display:block;font-size:52px;font-weight:700;color:{MUT}">')
              .replace("</s>", "</span>"))
        out += f'<div style="opacity:{1 if i < k else 0}">{l}</div>'
    return f'''<div style="width:1080px;height:1920px;background:{SAGE};display:flex;flex-direction:column;justify-content:center;padding:0 96px;gap:40px;font-family:'Noto Sans KR',sans-serif;box-sizing:border-box;position:relative">
<div style="position:absolute;left:0;top:0;height:14px;width:{prog*100:.1f}%;background:{DG}"></div>
<div style="font-size:50px;font-weight:700;color:{DG};min-height:60px">{top}</div>
<div style="font-size:100px;font-weight:900;line-height:1.3;letter-spacing:-.03em;color:{DG};display:flex;flex-direction:column">{out}</div>
<div style="position:absolute;left:96px;right:96px;bottom:150px;display:flex;justify-content:space-between;font-size:30px;color:{MUT}"><span>{basis}</span><b>{ACCOUNT}</b></div></div>'''


# --- 새 배치 (D-01 ~ D-04, ENV-04) ---

_S_STYLE = f"display:block;font-size:52px;font-weight:700;color:{MUT}"


def markup_new(text):
    """원고 문자열을 전부 이스케이프하고 <g>, </g>, <s>, </s> 네 개만 마크업으로 되살린다."""
    t = _html.escape(text, quote=False)
    lt, gt = "&lt;", "&gt;"
    return (t.replace(f"{lt}g{gt}", f'<span style="color:{GOLD}">').replace(f"{lt}/g{gt}", "</span>")
             .replace(f"{lt}s{gt}", f'<span style="{_S_STYLE}">').replace(f"{lt}/s{gt}", "</span>"))


def stack_html(top, lines, k, basis, line_html=None):
    """`#rk-stack` 한 덩어리(위 라벨, 본문 줄, 근거, 계정명). 모션 레이어도 같은 마크업을 쓴다.

    line_html 이 있으면 줄마다 markup_new(line) 대신 이 이미 만들어 둔 마크업 문자열을 쓴다 (카운트업 span 용).
    """
    texts = line_html if line_html is not None else [markup_new(l) for l in lines]
    body = "".join(
        f'<div class="rk-ln" data-i="{i}" style="opacity:{1 if i < k else 0}">{t}</div>'
        for i, t in enumerate(texts))
    basis_block = ""
    if basis and basis.strip():
        basis_block = (f'<div class="rk-basis" style="font-size:{BASIS_PX}px;font-weight:400;line-height:1.3;'
                       f'color:{MUT}">{markup_new(basis)}</div>')
    stack = (f"position:absolute;left:{SAFE['left']}px;right:{SAFE['right']}px;top:{SAFE['top']}px;"
             f"height:{SAFE['warn_y'] - SAFE['top']}px;display:flex;flex-direction:column;"
             "justify-content:center;gap:40px;word-break:keep-all")
    return (
        f'<div id="rk-stack" style="{stack}">'
        f'<div class="rk-top" style="font-size:50px;font-weight:700;color:{DG};min-height:60px">{markup_new(top)}</div>'
        f'<div class="rk-body" style="font-size:100px;font-weight:900;line-height:1.3;letter-spacing:-.03em;'
        f'color:{DG};display:flex;flex-direction:column">{body}</div>'
        f"{basis_block}"
        f'<div class="rk-acct" style="font-size:{ACCT_PX}px;font-weight:700;color:{MUT}">{ACCOUNT}</div>'
        "</div>")


def root_html(prog, inner):
    """`#rk-root`(1080x1920 배경) 안에 진행 막대(#rk-bar)와 inner 를 둔다."""
    return (
        f'<div id="rk-root" style="width:{W}px;height:{H}px;background:{SAGE};position:relative;'
        "overflow:hidden;font-family:'Noto Sans KR',sans-serif\">"
        f'<div id="rk-bar" style="position:absolute;left:0;top:0;height:14px;width:{prog * 100:.1f}%;'
        f'background:{DG}"></div>'
        f"{inner}</div>")


def new_inner_html(top, lines, k, prog, basis):
    """근거(36px, 최대 2줄)를 본문 바로 아래, 계정명을 그 아래에 두고 전부 안전영역 안에 쌓는다.

    줄은 모두 배치에 참여한다(opacity 만 바뀜). 텍스트는 줄이거나 줄여 맞추지 않고 원고 그대로 그린다.
    """
    return root_html(prog, stack_html(top, lines, k, basis))


LAYOUTS = {"legacy": legacy_inner_html, "new": new_inner_html}


# --- 측정과 경고 (ENV-05) ---

# page.evaluate 용: 새 배치 장면의 최종 상태에서 텍스트 사각형을 모아 줄 수와 경계를 돌려준다.
MEASURE_JS = """() => {
  const textRects = (el) => {
    const out = []; const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n;
    while ((n = tw.nextNode())) {
      if (!n.nodeValue.trim()) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      const fs = parseFloat(getComputedStyle(n.parentElement).fontSize);
      for (const q of r.getClientRects()) if (q.width > 0.5) out.push({l: q.left, r: q.right, t: q.top, b: q.bottom, fs});
    }
    return out;
  };
  const lineCount = (rs) => {
    if (!rs.length) return 0;
    const c = rs.map(q => ({y: (q.t + q.b) / 2, tol: q.fs * 0.4})).sort((a, b) => a.y - b.y);
    let n = 1, last = c[0].y;
    for (const q of c.slice(1)) { if (q.y - last > q.tol) n++; last = q.y; }
    return n;
  };
  const info = (el) => {
    if (!el) return null;
    const rs = textRects(el);
    if (!rs.length) return null;
    return {n: lineCount(rs), l: Math.min(...rs.map(q => q.l)), r: Math.max(...rs.map(q => q.r)),
            t: Math.min(...rs.map(q => q.t)), b: Math.max(...rs.map(q => q.b)),
            fs: parseFloat(getComputedStyle(el).fontSize), text: el.textContent.trim().slice(0, 30)};
  };
  const q1 = (s) => document.querySelector(s);
  return {top: info(q1('.rk-top')), lines: [...document.querySelectorAll('.rk-ln')].map(info),
          basis: info(q1('.rk-basis')), acct: info(q1('.rk-acct'))};
}"""

# 글꼴 확인용 라벨: 텍스트 요소와 그 자손 전부에 data-rk 를 붙인다 (다음 상태가 innerHTML 을 바꾸므로 프레임에는 남지 않는다).
_TAG_HELPER = ("const lab=(el,v)=>{if(!el)return;el.dataset.rk=v;"
               "el.querySelectorAll('*').forEach(e=>{e.dataset.rk=v;});};")
TAG_JS = {
    "new": "() => {" + _TAG_HELPER +
           "lab(document.querySelector('.rk-top'),'top');"
           "document.querySelectorAll('.rk-ln').forEach(e=>lab(e,String(+e.dataset.i+1)));"
           "lab(document.querySelector('.rk-basis'),'basis');"
           "lab(document.querySelector('.rk-acct'),'account');}",
    "legacy": "() => {" + _TAG_HELPER +
              "const root=document.body.firstElementChild;"
              "lab(root.children[1],'top');"
              "[...root.children[2].children].forEach((e,i)=>lab(e,String(i+1)));"
              "lab(root.children[3].children[0],'basis');"
              "lab(root.children[3].children[1],'account');}",
}


@dataclass
class LayoutWarning:
    scene: int      # 1부터
    line: str       # "1".."n" | "top" | "basis" | "account"
    kind: str
    value: str
    text: str

    def __str__(self):
        where = f"scene {self.scene} line {self.line}" if self.line != "" else f"scene {self.scene}"   # 장면 단위 경고는 line 이 빈 문자열
        return f'{where}: {self.kind} ({self.value}) "{self.text}"'


def evaluate_layout(measure, scene):
    """측정값을 기준과 비교해 경고만 만든다. 글자·크기·문구는 절대 바꾸지 않는다."""
    out = []
    right_limit = W - SAFE["right"]
    ui_limit = H - SAFE["bottom_ui"]

    def positional(m, line):
        text = m.get("text", "")
        if m["r"] > right_limit:
            out.append(LayoutWarning(scene, line, "RIGHT", f"right={m['r']:.0f} > {right_limit}", text))
        if m["t"] < SAFE["top"]:
            out.append(LayoutWarning(scene, line, "TOP", f"top={m['t']:.0f} < {SAFE['top']}", text))
        if m["b"] > ui_limit:
            out.append(LayoutWarning(scene, line, "UI_ZONE", f"bottom={m['b']:.0f} > {ui_limit}", text))
        elif m["b"] > SAFE["warn_y"]:
            out.append(LayoutWarning(scene, line, "WARN_Y", f"bottom={m['b']:.0f} > {SAFE['warn_y']}", text))

    if measure.get("top"):
        positional(measure["top"], "top")
    for i, m in enumerate(measure.get("lines") or [], start=1):
        if not m:
            continue
        if m["n"] > 1:
            out.append(LayoutWarning(scene, str(i), "WRAP", f"{m['n']} lines", m.get("text", "")))
        positional(m, str(i))
    b = measure.get("basis")
    if b:
        if b["n"] > BASIS_MAX_LINES:
            out.append(LayoutWarning(scene, "basis", "BASIS_LINES", f"{b['n']} lines > {BASIS_MAX_LINES}", b.get("text", "")))
        if b["fs"] < BASIS_PX:
            out.append(LayoutWarning(scene, "basis", "SMALL", f"{b['fs']:.0f}px < {BASIS_PX}px", b.get("text", "")))
        positional(b, "basis")
    a = measure.get("acct")
    if a:
        if a["fs"] < ACCT_PX:
            out.append(LayoutWarning(scene, "account", "SMALL", f"{a['fs']:.0f}px < {ACCT_PX}px", a.get("text", "")))
        positional(a, "account")
    return out


def overlay_html():
    """안전영역 미리보기 띠. 값은 전부 constants.SAFE 에서 계산한다 (프레임에는 넣지 않고 별도 PNG 에만)."""
    top, warn, ui = SAFE["top"], SAFE["warn_y"], H - SAFE["bottom_ui"]

    def band(y0, y1, color):
        return (f'<div style="position:absolute;left:0;top:{y0}px;width:{W}px;height:{y1 - y0}px;'
                f'background:{color}"></div>')

    def rule(y, label):
        return (f'<div style="position:absolute;left:0;top:{y}px;width:{W}px;height:2px;background:#C00000"></div>'
                f'<div style="position:absolute;left:12px;top:{y + 4}px;font:700 28px sans-serif;color:#C00000">'
                f"{label}</div>")

    return (
        f'<div id="rk-ov" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;'
        'pointer-events:none;z-index:10">'
        + band(0, top, "rgba(255,200,0,.35)")
        + band(warn, ui, "rgba(255,200,0,.35)")
        + band(ui, H, "rgba(220,0,0,.35)")
        + f'<div style="position:absolute;left:{W - SAFE["right"]}px;top:0;width:{SAFE["right"]}px;'
          f'height:{H}px;background:rgba(220,0,0,.25)"></div>'
        + rule(top, f"y={top} top") + rule(warn, f"y={warn} warn") + rule(ui, f"y={ui} UI zone")
        + "</div>")
