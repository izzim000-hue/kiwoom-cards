"""basic 모션: 시간표(schedule)와 결정적 시간 탐색용 페이지 도우미 (MOTN-01, MOTN-02, D-01~D-03, D-07).

장면마다 레이어 하나를 쌓고, 줄 진입(투명도 + 24px 떠오름)·장면 크로스페이드·진행 막대를 Web Animations 로 만든 뒤
전부 일시정지해 둔다. 프레임마다 모든 애니메이션의 currentTime 을 t 로 맞추고 스크린샷을 찍으므로
결과는 t 만의 함수다 (실시간 녹화가 아님). 표준 라이브러리만 쓴다.
"""
import html
import re
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from . import calc, constants, layout
from .spec import SpecError

MODES = ("none", "basic")

ENTER = 0.30        # 줄 진입 시간(초)
STAGGER = 0.12      # 줄 사이 시작 간격(초)
RISE_PX = 24        # 진입 시 떠오르는 거리
CROSS = 0.30        # 장면 크로스페이드(초)
COUNT = 0.80        # 숫자 세어 올라가기(카운트업) 시간(초)
READ_BASE = 0.6     # 읽기 시간 = READ_BASE + 글자 수 / READ_CPS
READ_CPS = 16
DWELL_MIN = 1.5     # 장면 길이 경고 기준(초)
DWELL_MAX = 6.0
EASE = "cubic-bezier(.2,.7,.2,1)"
FPS = constants.FPS

TAG_RE = re.compile(r"</?[gs]>")  # check.py 의 TAG_RE 와 같은 식 (check 가 motion 을 가져오므로 거꾸로 가져오지 않는다)
LINE_WHERE_RE = re.compile(r"^scene (\d+) line (\d+)$")


def resolve(spec, override=None):
    """이 렌더의 모션 모드. override 가 None 이 아니면 그 값, 아니면 spec 의 motion (없으면 none)."""
    mode = override if override is not None else spec.get("motion", "none")
    if isinstance(mode, bool) or not isinstance(mode, str) or mode not in MODES:
        raise SpecError(f"motion: 'none' 또는 'basic' 만 쓸 수 있음 — {mode!r}")
    return mode


@dataclass(frozen=True)
class SceneTiming:
    index: int          # 0부터
    start: float        # 장면 시작(초)
    end: float          # 장면 끝(초, 다음 장면 시작과 같음)
    settle: float       # 모든 줄 진입(과 카운트업)이 끝나기까지
    read: float         # 읽는 시간
    dur: float          # end - start
    final_t: float      # 모든 애니메이션이 끝난 첫 프레임의 시각 (표지·장면 모음에 쓰는 프레임)
    final_frame: int
    chars: int          # 보이는 글자 수(top + 줄 전부)
    n_lines: int
    countup_lines: tuple  # 카운트업이 있는 줄의 0부터 인덱스


@dataclass(frozen=True)
class Schedule:
    scenes: tuple
    raw_total: float
    nframes: int
    total: float        # nframes / FPS


def _visible(text):
    return len(TAG_RE.sub("", text))


def _countup_lines(spec, i, n):
    """장면 i(0부터)에서 장부에 countup 표시가 있는 줄의 0부터 인덱스."""
    found = set()
    for entry in spec.get("figures") or []:
        if not isinstance(entry, dict) or not entry.get("countup"):
            continue
        where = entry.get("where")
        for j in range(n):
            if where == f"scene {i + 1} line {j + 1}":
                found.add(j)
    return tuple(sorted(found))


def schedule(spec):
    """장면별 시간표. 순수 함수이며 값을 자르지 않는다 (경고는 호출한 쪽이 판단)."""
    scenes, t = [], 0.0
    last = len(spec["scenes"]) - 1
    for i, sc in enumerate(spec["scenes"]):
        lines = sc["lines"]
        n = len(lines)
        cu = _countup_lines(spec, i, n)
        settle = max((n - 1) * STAGGER + ENTER, max((j * STAGGER + COUNT for j in cu), default=0.0))
        chars = _visible(sc["top"]) + sum(_visible(l) for l in lines)
        read = READ_BASE + chars / READ_CPS
        dur = settle + read + (CROSS if i < last else 0.0)
        final_frame = round((t + settle) * FPS) + 1
        scenes.append(SceneTiming(index=i, start=t, end=t + dur, settle=settle, read=read, dur=dur,
                                  final_t=final_frame / FPS, final_frame=final_frame, chars=chars,
                                  n_lines=n, countup_lines=cu))
        t += dur
    nframes = round(t * FPS)
    return Schedule(scenes=tuple(scenes), raw_total=t, nframes=nframes, total=nframes / FPS)


def dwell_warnings(spec, sched):
    """장면 길이가 DWELL_MIN 보다 짧거나 DWELL_MAX 보다 길면 장면 단위 경고 (line 은 ""). 값은 자르지 않는다 (D-06)."""
    out = []
    for sc, scene in zip(sched.scenes, spec["scenes"]):
        text = TAG_RE.sub("", scene["lines"][0])[:30] if scene["lines"] else ""
        if sc.dur < DWELL_MIN:
            out.append(layout.LayoutWarning(sc.index + 1, "", "DWELL_SHORT", f"{sc.dur:.2f}초 < {DWELL_MIN:g}초", text))
        elif sc.dur > DWELL_MAX:
            out.append(layout.LayoutWarning(sc.index + 1, "", "DWELL_LONG", f"{sc.dur:.2f}초 > {DWELL_MAX:g}초", text))
    return out


def windows(sched):
    """레이어별 표시 시간창 [시작, 끝]: 앞 장면과 겹치는 크로스페이드 구간부터 자기 끝까지."""
    return [[0.0 if sc.index == 0 else sc.start - CROSS, sc.end] for sc in sched.scenes]


# --- 카운트업 (D-04) ---

def _bad_entry(where, why):
    return SpecError(f"figures: 카운트업 자리 {where} 가 원고 줄과 맞지 않음 — {why}")


# 끝의 ".0" 을 생략하는 0.1 단위 서식과 그 기본 단위. 최종 글자에 소수점이 없으면(150만, 10%) 중간 숫자도
# 정수 단위로 센다: 그렇지 않으면 "98.6만" 처럼 최종 글자보다 넓은 중간 숫자가 상자 밖으로 넘친다 (CR-01).
_POINT_DROPPING = {"pct": 1, "signed_pct": 1, "man1": 10000, "num": 1, "se": 1, "dal": 1}
_EOK = 100000000


def countup_step(entry):
    """중간 숫자를 0 쪽으로 내림할 단위(기본 단위, Decimal) 또는 None (서식 그대로).

    중간 숫자가 최종 글자보다 자릿수·단위가 많아지지 않게 최종 글자의 표시 정밀도로 센다 (CR-01):
    - 소수점을 생략하는 서식에서 최종 글자에 소수점이 없으면 정수 단위 (150만 -> 0만 … 149만).
    - eok_man_won 의 최종 글자가 억 단위면 만 부분이 있을 때 만 단위, 없으면 억 단위
      ("1억 원" 은 "9,999만 원" 처럼 넓은 중간 글자 없이 "0만 원" 에서 "1억 원" 으로 바뀐다).
    """
    fmt, text = entry["fmt"], entry["text"]
    if fmt in _POINT_DROPPING and "." not in text:
        return Decimal(_POINT_DROPPING[fmt])
    if fmt == "eok_man_won" and "억" in text:
        return Decimal(10000 if "만" in text else _EOK)
    return None


def cu_text(entry, p):
    """진행도 p(0~1)의 카운트업 글자. p >= 1 이면 장부 글자 그대로, 아니면 calc.FORMATS 로 찍은 중간값 (시작값은 0).

    중간값은 countup_step 단위로 0 쪽으로 내림한 뒤 찍는다 (최종 글자보다 넓어지지 않게, CR-01).
    """
    if p >= 1:
        return entry["text"]
    eased = 1 - (1 - max(p, 0)) ** 3
    value = Decimal(entry["value"]) * Decimal(str(eased))
    step = countup_step(entry)
    if step is not None:
        value = (value / step).to_integral_value(rounding=ROUND_DOWN) * step
    return calc.FORMATS[entry["fmt"]](value)[0]


def countup_entries(spec):
    """장부에서 countup 표시가 있는 항목을 검사해 [(장면 0부터, 줄 0부터, 항목)] 을 문서 순서로 돌려준다.

    손으로 고치거나 잘못 둔 항목은 렌더 전에 SpecError (T-04-06).
    """
    scenes = spec["scenes"]
    items, taken = [], {}
    for entry in spec.get("figures") or []:
        if not isinstance(entry, dict) or "countup" not in entry:
            continue
        where = entry.get("where")
        label = where if isinstance(where, str) else repr(where)
        if entry["countup"] is not True:
            raise _bad_entry(label, "countup 은 true 만 쓸 수 있음")
        m = LINE_WHERE_RE.match(where) if isinstance(where, str) else None
        if not m or not (1 <= int(m.group(1)) <= len(scenes)) or not (1 <= int(m.group(2)) <= len(scenes[int(m.group(1)) - 1]["lines"])):
            raise _bad_entry(label, "장면 줄이 아님")
        si, li = int(m.group(1)) - 1, int(m.group(2)) - 1
        line = scenes[si]["lines"][li]
        start, end, text = entry.get("start"), entry.get("end"), entry.get("text")
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (start, end)) or not isinstance(text, str):
            raise _bad_entry(label, "start/end/text 형식")
        if not (0 <= start < end <= len(line)) or line[start:end] != text:
            raise _bad_entry(label, "글자 구간이 줄과 다름")
        fmt = entry.get("fmt")
        if not isinstance(fmt, str) or fmt not in calc.FORMATS:
            raise _bad_entry(label, f"알 수 없는 서식 {fmt!r}")
        try:
            value = Decimal(entry.get("value"))
        except (InvalidOperation, TypeError, ValueError):
            raise _bad_entry(label, "값을 숫자로 읽을 수 없음") from None
        if not value.is_finite():
            raise _bad_entry(label, "값이 유한한 숫자가 아님")
        for s0, e0 in taken.get((si, li), []):
            if start < e0 and s0 < end:
                raise _bad_entry(label, "다른 카운트업 구간과 겹침")
        taken.setdefault((si, li), []).append((start, end))
        try:
            cu_text(entry, 0)
        except (calc.CalcError, InvalidOperation) as e:
            raise _bad_entry(label, f"서식 오류 {e}") from None
        items.append((si, li, entry))
    items.sort(key=lambda it: (it[0], it[1], it[2]["start"]))
    return items


def countup_texts(sched, items, t):
    """시각 t 의 카운트업 글자 목록 (items 와 같은 순서). 줄이 들어오기 시작할 때부터 COUNT 초 동안 센다."""
    return [cu_text(entry, (t - (sched.scenes[si].start + li * STAGGER)) / COUNT) for si, li, entry in items]


def countup_variants(sched, items):
    """카운트업마다 렌더 프레임(0 .. nframes-1)에 실제로 나오는 글자 전부 (나온 순서, 중복 없음).

    BUILD_JS 가 이 글자들을 모두 재서 상자 폭을 가장 넓은 글자에 맞춘다 (CR-01: 어떤 프레임도 상자 밖으로 넘치지 않음).
    """
    seen = [dict() for _ in items]
    for f in range(sched.nframes):
        for k, text in enumerate(countup_texts(sched, items, f / FPS)):
            seen[k][text] = None
    return [list(s) for s in seen]


def _line_markup(line, ents):
    """카운트업이 든 줄의 마크업: 숫자 자리만 고정 폭 span 으로 감싼다 (조각을 이으면 markup_new(line) 과 같다)."""
    out, pos = "", 0
    for k, entry in ents:
        out += (layout.markup_new(line[pos:entry["start"]])
                + f'<span class="rk-cu" data-k="{k}">{html.escape(entry["text"], quote=False)}</span>')
        pos = entry["end"]
    return out + layout.markup_new(line[pos:])


# --- 페이지 도우미 ---

# 애니메이션을 전부 만들어 일시정지한다. 데이터는 page.evaluate 인자(JSON)로만 받는다.
# 레이어 투명도: 들어오는 쪽은 fill both, 나가는 쪽은 forwards 만 (둘 다 both 면 뒤에 만든 쪽이 앞 구간까지 덮는다).
BUILD_JS = """(p) => {
  const textRects = (el) => {
    const out = []; const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n;
    while ((n = tw.nextNode())) {
      if (!n.nodeValue.trim()) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      const fs = parseFloat(getComputedStyle(n.parentElement).fontSize);
      for (const q of r.getClientRects()) if (q.width > 0.5) out.push({t: q.top, b: q.bottom, fs});
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
  // 줄바꿈 위치 (WR-02): 공백이 아닌 글자마다 그 줄 안의 몇 번째 행에 있는지. 행 수가 같아도 숫자와 조사가 갈라지면 다르다.
  // text 는 사람이 읽을 모양 ("최대 연금 148.5만 / 까지 받아요").
  const breaks = (ln) => {
    const sig = []; let text = '', row = 0, last = null;
    const tw = document.createTreeWalker(ln, NodeFilter.SHOW_TEXT); let n;
    while ((n = tw.nextNode())) {
      const tol = parseFloat(getComputedStyle(n.parentElement).fontSize) * 0.4;
      for (let i = 0; i < n.nodeValue.length; i++) {
        const ch = n.nodeValue[i];
        if (ch.trim()) {
          const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 1);
          const q = r.getClientRects()[0];
          if (q) {
            const y = (q.top + q.bottom) / 2;
            if (last !== null && y - last > tol) { row++; text = text.trimEnd() + ' / '; }
            last = y;
          }
          sig.push(row);
        }
        if (ch.trim() || !text.endsWith(' / ')) text += ch;
      }
    }
    return {sig: sig.join(','), text: text.trim()};
  };
  const cuRows = [];
  [...document.querySelectorAll('.rk-layer')].forEach((layer, s) => {
    [...layer.querySelectorAll('.rk-ln')].forEach((ln, j) => { if (ln.querySelector('.rk-cu')) cuRows.push(breaks(ln)); });
  });
  // 카운트업 숫자 상자: 렌더 프레임에 나오는 글자(p.cuTexts[k]: 중간 숫자 전부와 최종 글자) 중 가장 넓은 것의 폭으로 고정한다
  // (CR-01: 어떤 프레임의 숫자도 상자 밖으로 넘쳐 옆 글자를 덮지 않는다). 중간 숫자는 최종 글자의 자릿수·단위로 세므로(cu_text)
  // 보통 최종 글자의 폭 그대로라 줄 배치가 정적 배치와 같다. 글자는 오른쪽 정렬: 숫자 뒤 조사(150만이면)와 붙어 있다.
  // 애니메이션을 만들기 전, 모든 레이어가 보일 때 잰다.
  const cus = [...document.querySelectorAll('.rk-cu')];
  const widths = cus.map(e => e.getBoundingClientRect().width);
  const fits = cus.map((e, i) => {
    const final = e.textContent; let w = widths[i];
    e.style.whiteSpace = 'nowrap';
    for (const s of (p.cuTexts[+e.dataset.k] || [])) { e.textContent = s; w = Math.max(w, e.getBoundingClientRect().width); }
    e.textContent = final; e.style.whiteSpace = '';
    return w;
  });
  cus.forEach((e, i) => {
    e.style.display = 'inline-block'; e.style.whiteSpace = 'nowrap'; e.style.textAlign = 'right'; e.style.width = fits[i] + 'px';
  });
  // 상자로 바꾼 뒤 다시 잰다: 줄 수(n)와 줄바꿈 위치(moved, before/after)를 돌려준다
  const cuLines = [];
  [...document.querySelectorAll('.rk-layer')].forEach((layer, s) => {
    [...layer.querySelectorAll('.rk-ln')].forEach((ln, j) => {
      if (!ln.querySelector('.rk-cu')) return;
      const before = cuRows[cuLines.length], after = breaks(ln);
      cuLines.push({s: s, j: j, n: lineCount(textRects(ln)), moved: before.sig !== after.sig,
                    before: before.text, after: after.text});
    });
  });
  window.A = [];
  const add = (el, kf, o) => { const a = el.animate(kf, Object.assign({fill: 'both'}, o)); a.pause(); a.currentTime = 0; window.A.push(a); };
  const layers = [...document.querySelectorAll('.rk-layer')];
  const bar = document.getElementById('rk-bar');
  // 진행 막대는 transform 대신 width 로 움직인다: scaleX 는 합성기가 막대를 늘려 그려 아래 가장자리가 번지고(y 14 이후 잉크),
  // 표지 크롭 검사가 그것을 글자로 본다. 막대는 절대 위치라 width 애니메이션이 다른 요소의 배치를 바꾸지 않는다.
  add(bar, [{width: '0%'}, {width: '100%'}], {duration: p.total * 1000, easing: 'linear'});
  const last = p.scenes.length - 1;
  p.scenes.forEach((s, i) => {
    const layer = layers[i];
    if (i > 0) add(layer, [{opacity: 0}, {opacity: 1}],
                   {duration: p.cross * 1000, delay: (s.start - p.cross) * 1000, easing: 'linear'});
    if (i < last) add(layer, [{opacity: 1}, {opacity: 0}],
                      {duration: p.cross * 1000, delay: (s.end - p.cross) * 1000, easing: 'linear', fill: 'forwards'});
    [...layer.querySelectorAll('.rk-ln')].forEach((ln, j) => {
      add(ln, [{opacity: 0, transform: 'translateY(' + p.rise + 'px)'}, {opacity: 1, transform: 'translateY(0px)'}],
          {duration: p.enter * 1000, delay: (s.start + j * p.stagger) * 1000, easing: p.ease});
    });
  });
  return cuLines;
}"""

# 프레임마다: 모든 애니메이션의 전역 시간을 t 로 맞추고, 시간창 밖 레이어는 display:none (프레임당 렌더 시간이 절반 이하).
SEEK_JS = """(a) => {
  for (const x of window.A) x.currentTime = a.t * 1000;
  const eps = 1e-9;
  document.querySelectorAll('.rk-layer').forEach((L) => {
    const w = a.windows[+L.dataset.s];
    L.style.display = (a.t >= w[0] - eps && a.t <= w[1] + eps) ? '' : 'none';
  });
  // 카운트업 글자는 textContent 로만 바꾼다 (마크업으로 해석하지 않음)
  if (a.cu) document.querySelectorAll('.rk-cu').forEach((e) => {
    const v = a.cu[+e.dataset.k];
    if (e.textContent !== v) e.textContent = v;
  });
}"""

_LAYER_STYLE = f"position:absolute;left:0;top:0;width:{constants.W}px;height:{constants.H}px"


def layers_html(spec, items=None):
    """장면마다 레이어 하나 (줄은 최종 상태 마크업, 투명도·위치는 애니메이션이 정한다). 카운트업 숫자는 span 으로 감싼다."""
    basis = spec.get("basis", "")
    if items is None:
        items = countup_entries(spec)
    by_line = {}
    for k, (si, li, entry) in enumerate(items):
        by_line.setdefault((si, li), []).append((k, entry))
    out = ""
    for i, sc in enumerate(spec["scenes"]):
        line_html = None
        if any(si == i for si, _li in by_line):
            line_html = [_line_markup(l, by_line[(i, j)]) if (i, j) in by_line else layout.markup_new(l)
                         for j, l in enumerate(sc["lines"])]
        out += (f'<div class="rk-layer" data-s="{i}" style="{_LAYER_STYLE}">'
                + layout.stack_html(sc["top"], sc["lines"], len(sc["lines"]), basis, line_html=line_html) + "</div>")
    return out


def build(page, spec, sched):
    """페이지 본문을 모션 레이어로 바꾸고 폰트 로드를 기다린 뒤 애니메이션을 만든다.

    카운트업 줄마다 모션 DOM 에서 잰 값 [{s, j, n, moved, before, after}] (장면·줄 0부터) 를 돌려준다:
    n 은 숫자 상자로 바꾼 뒤의 줄 수, moved 는 상자로 바꾸기 전(정적 배치와 같은 마크업)과 뒤의 줄바꿈 위치가 다른지,
    before/after 는 그 두 배치를 " / " 로 나눠 적은 글자 (WR-02).
    """
    items = countup_entries(spec)
    page.evaluate("h=>{document.body.innerHTML=h}", layout.root_html(1.0, layers_html(spec, items)))
    page.evaluate("document.fonts.ready.then(()=>0)")
    payload = {"total": sched.raw_total, "cross": CROSS, "enter": ENTER, "stagger": STAGGER, "rise": RISE_PX,
               "ease": EASE, "scenes": [{"start": sc.start, "end": sc.end, "n": sc.n_lines} for sc in sched.scenes],
               "cuTexts": countup_variants(sched, items)}
    return page.evaluate(BUILD_JS, payload)


def seek(page, sched, t, cu=None):
    """시각 t(초)의 프레임 상태로 맞춘다. cu: 카운트업 글자 목록 (countup_texts)."""
    arg = {"t": t, "windows": windows(sched)}
    if cu:
        arg["cu"] = cu
    page.evaluate(SEEK_JS, arg)
