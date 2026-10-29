"""basic 모션: 시간표(schedule)와 결정적 시간 탐색용 페이지 도우미 (MOTN-01, MOTN-02, D-01~D-03, D-07).

장면마다 레이어 하나를 쌓고, 줄 진입(투명도 + 24px 떠오름)·장면 크로스페이드·진행 막대를 Web Animations 로 만든 뒤
전부 일시정지해 둔다. 프레임마다 모든 애니메이션의 currentTime 을 t 로 맞추고 스크린샷을 찍으므로
결과는 t 만의 함수다 (실시간 녹화가 아님). 표준 라이브러리만 쓴다.
"""
import re
from dataclasses import dataclass

from . import constants, layout
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


def windows(sched):
    """레이어별 표시 시간창 [시작, 끝]: 앞 장면과 겹치는 크로스페이드 구간부터 자기 끝까지."""
    return [[0.0 if sc.index == 0 else sc.start - CROSS, sc.end] for sc in sched.scenes]


# --- 페이지 도우미 ---

# 애니메이션을 전부 만들어 일시정지한다. 데이터는 page.evaluate 인자(JSON)로만 받는다.
# 레이어 투명도: 들어오는 쪽은 fill both, 나가는 쪽은 forwards 만 (둘 다 both 면 뒤에 만든 쪽이 앞 구간까지 덮는다).
BUILD_JS = """(p) => {
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
}"""

# 프레임마다: 모든 애니메이션의 전역 시간을 t 로 맞추고, 시간창 밖 레이어는 display:none (프레임당 렌더 시간이 절반 이하).
SEEK_JS = """(a) => {
  for (const x of window.A) x.currentTime = a.t * 1000;
  const eps = 1e-9;
  document.querySelectorAll('.rk-layer').forEach((L) => {
    const w = a.windows[+L.dataset.s];
    L.style.display = (a.t >= w[0] - eps && a.t <= w[1] + eps) ? '' : 'none';
  });
}"""

_LAYER_STYLE = f"position:absolute;left:0;top:0;width:{constants.W}px;height:{constants.H}px"


def layers_html(spec):
    """장면마다 레이어 하나 (줄은 최종 상태 마크업, 투명도·위치는 애니메이션이 정한다)."""
    basis = spec.get("basis", "")
    out = ""
    for i, sc in enumerate(spec["scenes"]):
        out += (f'<div class="rk-layer" data-s="{i}" style="{_LAYER_STYLE}">'
                + layout.stack_html(sc["top"], sc["lines"], len(sc["lines"]), basis) + "</div>")
    return out


def build(page, spec, sched):
    """페이지 본문을 모션 레이어로 바꾸고 폰트 로드를 기다린 뒤 애니메이션을 만든다."""
    page.evaluate("h=>{document.body.innerHTML=h}", layout.root_html(1.0, layers_html(spec)))
    page.evaluate("document.fonts.ready.then(()=>0)")
    payload = {"total": sched.raw_total, "cross": CROSS, "enter": ENTER, "stagger": STAGGER, "rise": RISE_PX,
               "ease": EASE, "scenes": [{"start": sc.start, "end": sc.end, "n": sc.n_lines} for sc in sched.scenes]}
    page.evaluate(BUILD_JS, payload)


def seek(page, sched, t):
    """시각 t(초)의 프레임 상태로 맞춘다."""
    page.evaluate(SEEK_JS, {"t": t, "windows": windows(sched)})
