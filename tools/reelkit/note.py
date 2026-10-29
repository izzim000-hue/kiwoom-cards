"""노트 배치 (layout "note"): 스프링 노트 위에 손글씨로 쓰는 릴스.

원고 소스에 장면을 손으로 쓰는 대신 `note` 블록을 두면 (expand.py), 이 모듈이
- 블록을 검사하고 (validate_note) 표준 `scenes` 를 만들어 주며 (derive_scenes) 모든 기존 점검(수치 장부, 표현 점검, 게시글, 하우스 패턴)이
  그대로 동작하게 하고,
- 항목 수로 시간표를 정하고 (schedule), 결정적 시간 탐색(renderAt(t) -> 프레임) 으로 렌더한다 (render_note).

렌더는 기본 틀과 별개의 페이지(templates/note.html)를 쓰며 PNG 파이프 인코더(encode.PipeEncoder)를 그대로 재사용한다.
글자는 줄이거나 자르지 않고 원고 그대로 그린다. 넘침·안전영역 침범·항목 줄바꿈은 LayoutWarning 으로만 알린다.
표준 라이브러리만 쓴다 (Playwright 는 렌더 함수 안에서만 가져온다).
"""
import html as _html
import math
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import constants
from .constants import ACCOUNT, FPS, H, SAFE, W
from .layout import LayoutWarning, overlay_html

LAYOUT_NAME = "note"
TEMPLATE = Path(__file__).resolve().parent / "templates" / "note.html"

NOTE_KEYS = ("title", "highlight", "boxes", "footer")
BOX_KEYS = ("head", "sub", "color", "items")
COLORS = ("green", "gold")                    # 상자 머리띠 색: green #2F4F3E, gold(짙은 금색) #8A6B2C
DEFAULT_COLORS = ("green", "gold")            # color 를 생략했을 때 상자 순서대로
TITLE_MAX, BOXES_MAX, ITEMS_MAX = 2, 2, 5

# 표준 장면으로 풀 때 쓰는 고정 문구
SEP = " · "                      # 장면 top = 머리글 + SEP + 보조 라벨 (보조 라벨도 표현 점검·수치 점검을 받도록 top 에 싣는다)
FOOTER_TOP = "단, 꼭 알아둘 것"
CTA_LINES = ["저장해두고", "내 상황부터", "확인해 보세요", "<s>프로필 링크 · 1분 노후자금 계산기</s>"]

# 안전영역 (constants.SAFE): 글자는 y 270 ~ 1470, 오른쪽 150px 여백 안. 노트 배치는 사용자가 승인한 시안대로 y 1250~1470 구간까지
# 근거·계정명을 두므로 기존 새 배치의 WARN_Y(1250) 경고는 쓰지 않는다. 오류 구간(UI_ZONE)만 지킨다.
TEXT_TOP = SAFE["top"]
TEXT_RIGHT = W - SAFE["right"]
TEXT_BOTTOM = H - SAFE["bottom_ui"]
CROP_TOP, CROP_BOTTOM = (H - 1440) // 2, (H - 1440) // 2 + 1440   # 프로필 그리드 크롭 (stills.py 와 같은 값)

# 레이아웃 수치 (화면 좌표). 종이는 y 150 에서 시작하고 글자 흐름은 안전영역 맨 위(270)에서 시작한다.
PAPER_TOP = 150
PAPER_H = 1316
FLOW_TOP_ABS = 270          # 제목 글줄의 윗끝이 270 아래에 오도록 시안 조정값 (측정으로 확인, 시험이 지킨다)
FLOW_GAP = 18
FOOT_BOTTOM_ABS = 1460      # 계정명 윗줄 상자의 아랫끝 (종이 안쪽, UI 영역 1470 위)
BOX_BORDER, BOX_PAD_X = 7, 30

# 시간표 (초). 시안(note-anim.html)의 값을 글자 수·항목 수로 일반화한 것.
START = 0.3
WRITE_BASE, WRITE_PER_CHAR = 0.6, 0.05    # 쓰는 데 걸리는 시간 = 0.6 + 0.05 * 글자 수 (제목·꼭 알아둘 것)
POP = 0.4                                 # 상자가 나타나는 시간
GAP_TITLE_BOX = 0.3
ITEM_LEAD, ITEM_STEP, ITEM_D = 0.5, 0.75, 0.6
GAP_BOX_BOX = 0.35
GAP_BOX_FOOTER = 0.45
GAP_FOOTER_FADE = 0.2
FADE_D = 0.5
HOLD_MIN, HOLD_MAX = 6.8, 9.0             # 끝 정지(초): 최소 6초 이상, 짧은 노트는 18초에 가깝도록 늘린다 (최대 HOLD_MAX)
DUR_MIN, DUR_MAX = 18.0, 27.0             # 하우스 패턴(노트): 이 범위 밖이면 check 가 DURATION 경고
COVER_AFTER = 0.3                         # 모든 애니메이션이 끝난 뒤 표지 프레임까지의 여유


class NoteError(ValueError):
    """note 블록이 규칙에 어긋날 때. 메시지는 한국어이며 위치를 밝힌다."""


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _text(value, where, *, allow_empty=False):
    if not isinstance(value, str):
        raise NoteError(f"{where}: 문자열이어야 함")
    if not allow_empty and not value.strip():
        raise NoteError(f"{where}: 비어 있지 않은 문자열이어야 함")
    if "<" in value or ">" in value:
        raise NoteError(f"{where}: '<', '>' 는 노트 글자에 쓸 수 없음 (<g>, <s> 같은 마크업은 노트 형식에서 지원하지 않음)")
    if "\n" in value or "\r" in value:
        raise NoteError(f"{where}: 줄바꿈을 넣을 수 없음 (줄은 목록의 항목으로 나눈다)")
    return value


def validate_note(note):
    """note 블록을 검사한다. 위치(note.title[1] 처럼 1부터)를 밝힌 NoteError 를 던진다. 입력은 바꾸지 않는다."""
    if not isinstance(note, dict):
        raise NoteError("note: 객체여야 함")
    unknown = [k for k in note if k not in NOTE_KEYS]
    if unknown:
        raise NoteError(f"note: 알 수 없는 키 {', '.join(map(str, unknown))} (허용: {', '.join(NOTE_KEYS)})")
    title = note.get("title")
    if not isinstance(title, list) or not 1 <= len(title) <= TITLE_MAX:
        raise NoteError(f"note.title: 글줄 1~{TITLE_MAX}개의 목록이어야 함")
    for i, line in enumerate(title, 1):
        _text(line, f"note.title[{i}]")
    if "highlight" in note:
        hl = note["highlight"]
        if not _is_int(hl) or not 0 <= hl < len(title):
            raise NoteError(f"note.highlight: 0~{len(title) - 1} 정수여야 함 (형광펜을 칠할 제목 줄의 0부터 번호) — {hl!r}")
    boxes = note.get("boxes")
    if not isinstance(boxes, list) or not 1 <= len(boxes) <= BOXES_MAX:
        raise NoteError(f"note.boxes: 상자 1~{BOXES_MAX}개의 목록이어야 함")
    for b, box in enumerate(boxes, 1):
        where = f"note.boxes[{b}]"
        if not isinstance(box, dict):
            raise NoteError(f"{where}: 객체여야 함")
        unknown = [k for k in box if k not in BOX_KEYS]
        if unknown:
            raise NoteError(f"{where}: 알 수 없는 키 {', '.join(map(str, unknown))} (허용: {', '.join(BOX_KEYS)})")
        _text(box.get("head"), f"{where}.head")
        if "sub" in box:
            _text(box["sub"], f"{where}.sub")
        if "color" in box and (not isinstance(box["color"], str) or box["color"] not in COLORS):
            raise NoteError(f"{where}.color: {' 또는 '.join(COLORS)} 만 쓸 수 있음 — {box['color']!r}")
        items = box.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= ITEMS_MAX:
            raise NoteError(f"{where}.items: 항목 1~{ITEMS_MAX}개의 목록이어야 함")
        for i, item in enumerate(items, 1):
            _text(item, f"{where}.items[{i}]")
    if "footer" in note:
        _text(note["footer"], "note.footer")


def strings(note):
    """검사된 note 블록의 화면 글자를 문서 순서로 낸다 (제목, 상자 머리글·보조 라벨·항목, 꼭 알아둘 것)."""
    yield from note["title"]
    for box in note["boxes"]:
        yield box["head"]
        if "sub" in box:
            yield box["sub"]
        yield from box["items"]
    if "footer" in note:
        yield note["footer"]


def box_color(note, b):
    """상자 b(0부터)의 색 이름. 생략하면 순서대로 green, gold."""
    return note["boxes"][b].get("color") or DEFAULT_COLORS[b]


def derive_scenes(note):
    """note 블록 -> 표준 장면 목록 (자리표시자가 아직 풀리지 않은 소스 글자 그대로).

    1 제목 장면(top 은 비움: 시리즈를 쓰면 expand 가 채운다, lines = 제목 줄)
    2~ 상자마다 한 장면 (top = 머리글 [+ " · " + 보조 라벨], lines = 항목)
    footer 가 있으면 '단, 꼭 알아둘 것' 장면 하나, 마지막에 표준 CTA 장면.
    CTA 장면은 점검(하우스 패턴·시리즈 다음 편 줄)용이며 노트 화면에는 그려지지 않는다 (영상 끝은 노트 + 계정명).
    """
    scenes = [{"top": "", "lines": list(note["title"])}]
    for box in note["boxes"]:
        top = box["head"] + (SEP + box["sub"] if "sub" in box else "")
        scenes.append({"top": top, "lines": list(box["items"])})
    if "footer" in note:
        scenes.append({"top": FOOTER_TOP, "lines": [note["footer"]]})
    scenes.append({"top": "", "lines": list(CTA_LINES)})
    return scenes


def is_note(spec):
    return isinstance(spec, dict) and spec.get("layout") == LAYOUT_NAME


# --- 시간표 ---

@dataclass(frozen=True)
class NoteSchedule:
    title: tuple         # ((시작, 길이), ...) 제목 줄마다
    boxes: tuple         # ((시작, 길이), ...) 상자가 나타나는 시간
    items: tuple         # (((시작, 길이), ...), ...) 상자마다 항목들
    footer: object       # (시작, 길이) 또는 None
    foot: tuple          # (시작, 길이) 근거·계정명이 나타나는 시간
    stage_done: tuple    # 표준 장면마다 "그 장면 내용이 다 써진" 시각 (CTA 장면은 영상 끝)
    anim_end: float      # 모든 애니메이션이 끝나는 시각
    hold: float
    total: float
    nframes: int
    cover_t: float


def _r(x):
    return round(x, 2)


def _write_d(text):
    return _r(WRITE_BASE + WRITE_PER_CHAR * len(text.replace(" ", "")))


def schedule(note):
    """note(검사된 블록) -> NoteSchedule. 순수 함수이며 값을 자르지 않는다 (길이 경고는 check 가 판단)."""
    t = START
    title = []
    for line in note["title"]:
        d = _write_d(line)
        title.append((_r(t), d))
        t += d
    title_end = t
    boxes, items, box_done = [], [], []
    t = title_end + GAP_TITLE_BOX
    for box in note["boxes"]:
        boxes.append((_r(t), POP))
        row, s = [], t + ITEM_LEAD
        for _ in box["items"]:
            row.append((_r(s), ITEM_D))
            s += ITEM_STEP
        items.append(tuple(row))
        last_end = row[-1][0] + ITEM_D
        box_done.append(_r(last_end))
        t = last_end + GAP_BOX_BOX
    content_end = box_done[-1]
    footer, stage_done = None, [_r(title_end), *box_done]
    if "footer" in note:
        s = content_end + GAP_BOX_FOOTER
        d = _write_d(note["footer"])
        footer = (_r(s), d)
        content_end = _r(s + d)
        stage_done.append(content_end)
        fade_s = content_end + GAP_FOOTER_FADE
    else:
        fade_s = content_end + GAP_BOX_FOOTER
    foot = (_r(fade_s), FADE_D)
    anim_end = _r(fade_s + FADE_D)
    hold = min(max(HOLD_MIN, DUR_MIN - anim_end), HOLD_MAX)
    nframes = round((anim_end + hold) * FPS)
    total = nframes / FPS
    stage_done.append(_r(total))   # CTA 장면 (화면에 없음): 영상 끝
    return NoteSchedule(title=tuple(title), boxes=tuple(boxes), items=tuple(items), footer=footer, foot=foot,
                        stage_done=tuple(stage_done), anim_end=anim_end, hold=_r(hold), total=total,
                        nframes=nframes, cover_t=_r(anim_end + COVER_AFTER))


def scene_times(spec):
    """검수 요약의 장면별 시점(초): 표준 장면마다 그 내용이 다 써진 시각 (소수 둘째 자리)."""
    return list(schedule(spec["note"]).stage_done)


# --- 페이지 ---

_CHECK_SVG = ('<svg class="ck" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="8" '
              'stroke-linecap="round" stroke-linejoin="round"><path d="M7 26 L19 38 L41 9"/></svg>')


def _esc(s):
    return _html.escape(s, quote=True)


def _w(action, sd, inner, cls="", tag="span", extra=""):
    s, d = sd
    cls = ("w " + cls).strip()
    return f'<{tag} class="{cls}" data-a="{action}" data-s="{s}" data-d="{d}"{extra}>{inner}</{tag}>'


def body_parts(note, basis, sched):
    """템플릿에 들어갈 조각 {RINGS, FLOW, FOOT}. 글자는 전부 이스케이프하고 마크업은 이 함수가 만든 것뿐이다."""
    rings = '<div class="ring"></div>' * 10
    title_html = []
    hl = note.get("highlight")
    for i, line in enumerate(note["title"]):
        cls = "hl" if hl == i else ""
        span = _w("write", sched.title[i], _esc(line), cls, extra=f' data-nt="title|{i + 1}"')
        title_html.append(f'<div class="tl">{span}</div>')
    flow = ['<div class="title">' + "".join(title_html) + "</div>"]
    for b, box in enumerate(note["boxes"]):
        sub = f'<small data-nt="sub|{b + 1}">{_esc(box["sub"])}</small>' if "sub" in box else ""
        head = f'<div class="head"><span data-nt="head|{b + 1}">{_esc(box["head"])}</span>{sub}</div>'
        lis = []
        for j, item in enumerate(box["items"]):
            span = _w("write", sched.items[b][j], _esc(item), "it", extra=f' data-nt="item|{b + 1}|{j + 1}"')
            lis.append(f"<li>{_CHECK_SVG}{span}</li>")
        flow.append(_w("pop", sched.boxes[b], head + "<ul>" + "".join(lis) + "</ul>",
                       f"box c-{box_color(note, b)}", tag="div"))
    if "footer" in note:
        flow.append('<div class="fnote">' + _w("write", sched.footer, _esc(note["footer"]), extra=' data-nt="footer"')
                    + "</div>")
    foot = []
    if basis and basis.strip():
        foot.append(_w("fade", sched.foot, _esc(basis), "basis", tag="div", extra=' data-nt="basis"'))
    foot.append(_w("fade", sched.foot, _esc(ACCOUNT), "acct", tag="div", extra=' data-nt="account"'))
    return {"RINGS": rings, "FLOW": "".join(flow), "FOOT": "".join(foot)}


def page_html(note, basis, sched, fonts_dir=constants.FONTS_DIR):
    parts = body_parts(note, basis, sched)
    html = TEMPLATE.read_text(encoding="utf-8")
    subs = {"FONTDIR_URI": Path(fonts_dir).resolve().as_uri(), "TOTAL": repr(float(sched.total)),
            "PAPER_H": str(PAPER_H), "FLOW_TOP": str(FLOW_TOP_ABS - PAPER_TOP), "FLOW_GAP": str(FLOW_GAP),
            "FOOT_BOTTOM": str(PAPER_TOP + PAPER_H - FOOT_BOTTOM_ABS), **parts}
    for key, val in subs.items():
        html = html.replace("{{" + key + "}}", val)
    return html


FONT_STATUS_JS = ("Promise.all([...document.fonts].map(f=>f.load().then(()=>f.status,()=>'error')"
                  ".then(s=>f.family.replace(/[\"']/g,'')+' '+f.weight+' '+s)))")


def font_statuses(page):
    """{'Gaegu 700': 'loaded', 'Noto Sans KR 700': 'loaded'} — 노트 페이지에 선언된 @font-face 의 로드 상태."""
    out = {}
    for item in page.evaluate(FONT_STATUS_JS):
        name, status = item.rsplit(" ", 1)
        out[name] = status
    return out


def font_problems(page):
    problems = []
    states = font_statuses(page)
    for want in (f"{constants.NOTE_FONT_FAMILY} {constants.NOTE_FONT_WEIGHT}", "Noto Sans KR 700"):
        status = states.get(want)
        if status != "loaded":
            problems.append(f"노트 폰트 {want} 로드 실패: 상태 {status or '없음'}")
    return problems


def open_page(b, work, note, basis, sched):
    """노트 페이지(file://)를 열어 돌려준다. 원고 글자는 이스케이프되어 있고 외부 요청(http/https)은 막는다."""
    from . import browser   # 순환 import 를 피하려 함수 안에서 (browser 는 constants 만 쓴다)
    frame = Path(work) / "note.html"
    frame.write_text(page_html(note, basis, sched), encoding="utf-8")
    page = b.new_page(viewport={"width": W, "height": H})
    page.route(re.compile(r"^https?://"), lambda r: r.abort())
    page.goto(frame.as_uri())
    page.evaluate("document.fonts.ready.then(()=>0)")
    problems = font_problems(page)
    if problems:
        raise browser.FontLoadError(
            "; ".join(problems) + ". 시스템 폰트로 대체하지 않고 중단합니다. python3 tools/doctor.py 로 점검하세요")
    return page


# --- 측정과 경고 ---

MEASURE_JS = """(boxPad) => {
  const out = [];
  for (const el of document.querySelectorAll('[data-nt]')) {
    const rs = []; const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n;
    while ((n = tw.nextNode())) {
      if (!n.nodeValue.trim()) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      for (const q of r.getClientRects()) if (q.width > 0.5) rs.push(q);
    }
    if (!rs.length) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    const c = rs.map(q => (q.top + q.bottom) / 2).sort((a, b) => a - b);
    let lines = 1, last = c[0];
    for (const y of c.slice(1)) { if (y - last > fs * 0.4) lines++; last = y; }
    const bx = el.closest('.box');
    out.push({nt: el.dataset.nt, n: lines, l: Math.min(...rs.map(q => q.left)), r: Math.max(...rs.map(q => q.right)),
              t: Math.min(...rs.map(q => q.top)), b: Math.max(...rs.map(q => q.bottom)), fs,
              text: el.textContent.trim().slice(0, 30),
              lim: bx ? bx.getBoundingClientRect().right - boxPad : null});
  }
  const flow = document.getElementById('nt-flow').getBoundingClientRect();
  const foot = document.getElementById('nt-foot').firstElementChild.getBoundingClientRect();
  const boxes = [...document.querySelectorAll('.box')].map(e => {const q = e.getBoundingClientRect(); return {t: q.top, b: q.bottom};});
  return {items: out, flowBottom: flow.bottom, footTop: foot.top, boxes};
}"""


def _label(nt, n_scenes_before_footer):
    """data-nt 라벨 -> (장면 번호, 줄 라벨). 장면: 1 제목, 2~ 상자, 그 다음 꼭 알아둘 것."""
    kind, *rest = nt.split("|")
    if kind == "title":
        return 1, rest[0]
    if kind in ("head", "sub"):
        return 1 + int(rest[0]), "top"
    if kind == "item":
        return 1 + int(rest[0]), rest[1]
    if kind == "footer":
        return n_scenes_before_footer, "1"
    return 1, kind   # basis, account: 화면 전체에 속하므로 장면 1


def layout_warnings(measure, note):
    """최종 상태 측정값 -> LayoutWarning 목록: TOP/RIGHT/UI_ZONE(안전영역), OVERFLOW(상자·흐름 넘침), WRAP(항목 줄바꿈), 근거·계정명 크기."""
    out = []
    footer_scene = 2 + len(note["boxes"])
    for m in measure["items"]:
        scene, line = _label(m["nt"], footer_scene)
        text = m["text"]
        kind = m["nt"].split("|")[0]
        if m["t"] < TEXT_TOP:
            out.append(LayoutWarning(scene, line, "TOP", f"top={m['t']:.0f} < {TEXT_TOP}", text))
        if m["r"] > TEXT_RIGHT:
            out.append(LayoutWarning(scene, line, "RIGHT", f"right={m['r']:.0f} > {TEXT_RIGHT}", text))
        if m["b"] > TEXT_BOTTOM:
            out.append(LayoutWarning(scene, line, "UI_ZONE", f"bottom={m['b']:.0f} > {TEXT_BOTTOM}", text))
        if m["lim"] is not None and m["r"] > m["lim"] + 0.5:
            out.append(LayoutWarning(scene, line, "OVERFLOW", f"right={m['r']:.0f} > box {m['lim']:.0f}", text))
        if kind == "item" and m["n"] > 1:
            out.append(LayoutWarning(scene, line, "WRAP", f"{m['n']} lines", text))
        if kind in ("head", "sub", "title", "footer") and m["n"] > 1:
            out.append(LayoutWarning(scene, line, "WRAP", f"{m['n']} lines", text))
        if kind == "basis":
            if m["n"] > constants.BASIS_MAX_LINES:
                out.append(LayoutWarning(scene, line, "BASIS_LINES", f"{m['n']} lines > {constants.BASIS_MAX_LINES}", text))
            if m["fs"] < constants.BASIS_PX:
                out.append(LayoutWarning(scene, line, "SMALL", f"{m['fs']:.0f}px < {constants.BASIS_PX}px", text))
        if kind == "account" and m["fs"] < constants.ACCT_PX:
            out.append(LayoutWarning(scene, line, "SMALL", f"{m['fs']:.0f}px < {constants.ACCT_PX}px", text))
    if measure["flowBottom"] > measure["footTop"] - 6:
        out.append(LayoutWarning(1, "", "OVERFLOW",
                                 f"본문 아래 {measure['flowBottom']:.0f} > 근거·계정명 위 {measure['footTop']:.0f}",
                                 note["title"][0][:30]))
    return out


def crop_warnings(measure):
    """표지(최종 프레임) 글자가 프로필 그리드 크롭(가운데 1080x1440) 밖에 있으면 stills.cover_crop_warnings 와 같은 문장.

    노트는 배경이 단색이 아니라(종이와 고리가 크롭 밖까지 이어짐) 픽셀 검사가 맞지 않아 글자 위치로 판단한다.
    """
    rows = [(m["t"], m["b"]) for m in measure["items"]]
    bad = sorted({int(y) for t, b in rows for y in range(int(math.floor(t)), int(math.ceil(b)))
                  if y < CROP_TOP or y >= CROP_BOTTOM})
    out, start = [], None
    for y in bad:
        if start is not None and y == prev + 1:
            prev = y
            continue
        if start is not None:
            out.append((start, prev))
        start = prev = y
    if start is not None:
        out.append((start, prev))
    return [f"COVER_CROP: 표지 글자가 프로필 그리드 크롭(가운데 {W}×1440, y {CROP_TOP}~{CROP_BOTTOM - 1}) 밖에 있음 — y {a}~{b}"
            for a, b in out]


def _font_fallback_warnings(page, note):
    from . import browser
    labels = page.evaluate("[...document.querySelectorAll('[data-nt]')].map(e=>[e.dataset.nt, e.textContent.trim().slice(0,30)])")
    fonts = browser.platform_fonts(page, "[data-nt]")
    footer_scene = 2 + len(note["boxes"])
    out, seen = [], set()
    for (nt, text), used in zip(labels, fonts):
        fallback = [f for f in used if not f.get("isCustomFont")]
        if fallback and nt not in seen:
            seen.add(nt)
            scene, line = _label(nt, footer_scene)
            out.append(LayoutWarning(scene, line, "FONT_FALLBACK", str(fallback[0].get("familyName", "?")), text))
    return out


def final_state(page, note, sched):
    """모든 애니메이션이 끝난 상태로 맞춘 뒤 글자 위치·넘침·폰트를 본다: (측정값, LayoutWarning 목록)."""
    page.evaluate(f"renderAt({sched.total})")
    measure = page.evaluate(MEASURE_JS, BOX_BORDER + BOX_PAD_X)
    return measure, layout_warnings(measure, note) + _font_fallback_warnings(page, note)


# --- 렌더 ---

def render_note(spec, out_path, *, keep_work=False, frame_sink=None, bgm=None):
    """노트 원고를 MP4 로. frame_sink(0, PNG 경로) 에는 모든 애니메이션이 끝난 최종 프레임(표지) 하나를 준다."""
    from . import browser, specprobe
    from .encode import PipeEncoder
    from .render import RenderResult

    note = spec["note"]
    try:
        validate_note(note)
    except NoteError as e:
        from .spec import SpecError
        raise SpecError(str(e)) from None
    basis = spec.get("basis", "")
    sched = schedule(note)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright  # 미설치 시 ImportError 는 CLI 가 안내한다

    work = tempfile.mkdtemp(prefix="reelkit-note-")
    warnings, overlays, cover_warnings = [], [], []
    cover_frame = max(0, min(sched.nframes - 1, math.ceil(sched.cover_t * FPS)))
    try:
        with sync_playwright() as pw:
            b, used = browser.launch(pw)
            try:
                page = open_page(b, work, note, basis, sched)
                measure, warnings = final_state(page, note, sched)
                cover_warnings = crop_warnings(measure)
                with PipeEncoder(out_path, bgm=bgm, total=sched.total) as enc:
                    for f in range(sched.nframes):
                        page.evaluate(f"renderAt({f / FPS})")
                        png = page.screenshot(type="png")
                        if f == cover_frame:
                            still = Path(work) / "s01.png"
                            still.write_bytes(png)
                            if frame_sink is not None:
                                frame_sink(0, str(still))
                            ov = out_path.with_name(out_path.stem + ".safe-s01.png")
                            page.evaluate("h=>{document.getElementById('nt-root').insertAdjacentHTML('beforeend', h)}",
                                          overlay_html())
                            page.screenshot(path=str(ov))
                            page.evaluate("()=>{const o=document.getElementById('rk-ov'); if(o) o.remove()}")
                            overlays.append(ov)
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
    return RenderResult(out=out_path, total=sched.total, cover_ms=round(sched.cover_t * 1000), launch=used,
                        warnings=warnings, overlays=overlays, spec_checks=spec_checks, motion=LAYOUT_NAME,
                        bgm=None if bgm is None else Path(bgm).name, cover_warnings=cover_warnings)
