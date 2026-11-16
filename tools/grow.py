#!/usr/bin/env python3
"""비유 하나를 키우는 1인칭 스토리 릴스 — '월급은 씨앗' (2026-11-16).

설명 대신 그림 하나(땅 · 씨앗 봉투 · 그릇 · 자라는 나무)를 처음부터 끝까지 키워 가며,
'예전의 나 → 바꾼 것 → 달라진 것'을 1인칭으로 들려준다. 화자는 새싹 멘토(=나).

    python3 tools/grow.py reel  SPEC.json OUT.mp4
    python3 tools/grow.py still SPEC.json OUT_DIR

원고는 장면(beat)마다 key 를 갖고, key 별 연출은 아래 CHOREO 에 있다.
문구(say · hook · 상자 · 이름표)는 원고에서 바꾼다. 형식은 sources/grow/README.md.
"""

import argparse
import html
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duo  # noqa: E402  (CSS · 강조 문법 · 자막 길이)
import notebook_char as nc  # noqa: E402
from reelkit import browser  # noqa: E402
from reelkit.encode import EncodeError, PipeEncoder  # noqa: E402

FPS = 30
GROUND = 1150
ENV = (270, 470)
BOWL = (800, 640)
SPOTS = [(560, GROUND), (740, GROUND), (920, GROUND)]
ENV_S, BOWL_S, SEED_S, PLANT_S = 1.5, 1.4, 1.5, 1.2
N_SEED = 12
KEYS = ["hook", "payday", "spend", "empty", "change", "rest", "sprout", "grow", "names", "conclude", "ask"]


def seed_home(i):
    return (ENV[0] - 120 + (i % 6) * 48, ENV[1] - 12 + (i // 6) * 44)


# ---------------------------------------------------------------- 그림
def plant(h):
    """원점이 뿌리(땅 위)인 나무. h = 높이."""
    leaves = []
    for k, y in enumerate(range(-int(h * 0.35), -h, -max(46, h // 5))):
        side = -1 if k % 2 else 1
        leaves.append(f'<path d="M0 {y} q{side*46} -30 {side*78} -6 q{-side*30} 30 {-side*78} 6 Z" fill="#8CC56E" stroke="#333" stroke-width="5" stroke-linejoin="round"/>')
    top = (f'<path d="M0 {-h} q-38 -40 -70 -26 q22 40 70 26 Z" fill="#8CC56E" stroke="#333" stroke-width="5"/>'
           f'<path d="M0 {-h} q38 -48 76 -30 q-24 44 -76 30 Z" fill="#8CC56E" stroke="#333" stroke-width="5"/>')
    return (f'<path d="M0 0 L0 {-h}" stroke="#333" stroke-width="16" stroke-linecap="round"/>'
            f'<path d="M0 0 L0 {-h}" stroke="#6E9E4E" stroke-width="8" stroke-linecap="round"/>{"".join(leaves)}{top}')


SEED = '<ellipse rx="12" ry="8" fill="#9A6A3A" stroke="#333" stroke-width="4"/>'
ENVELOPE = ('<rect x="-130" y="-78" width="260" height="150" rx="14" fill="#fff" stroke="#333" stroke-width="6"/>'
            '<path d="M-130 -78 L0 -6 L130 -78" fill="none" stroke="#333" stroke-width="5"/>')
BOWL_SVG = ('<path d="M-130 -20 Q-126 80 0 86 Q126 80 130 -20 Z" fill="#fff" stroke="#333" stroke-width="6" stroke-linejoin="round"/>'
            '<path d="M-150 -20 H150" stroke="#333" stroke-width="7" stroke-linecap="round"/>')
EMPTY = ('<ellipse cx="0" cy="40" rx="300" ry="60" fill="none" stroke="#C8574F" stroke-width="6" stroke-dasharray="18 14"/>')


CSS_EXTRA = """
.scene{position:absolute;left:0;top:0;width:1080px;height:1920px;overflow:visible}
.k{opacity:0}
.me{position:absolute;left:-10px;top:650px;width:400px;height:522px;overflow:visible;z-index:2}
.lab{position:absolute;opacity:0;font:700 42px/1.15 Hand;background:#fff;border:4px solid #333;border-radius:20px;padding:6px 16px;white-space:nowrap;transform-origin:center}
.lab.red{color:#C8574F;border-color:#C8574F}.lab.grn{color:#3E7C5B;border-color:#3E7C5B}.lab.ghost{background:transparent;border-style:dashed}
.lab.navy{background:#34507A;color:#fff;border-color:#34507A}
"""


def page_html(spec):
    labels = spec.get("labels", {})
    css = duo.CSS.replace("{FONTS}", duo.FONTS) + CSS_EXTRA
    s = [f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="dots"></div>',
         f'<div class="top"><span class="badge">{html.escape(spec.get("badge", "제 이야기"))}</span>'
         f'<div class="ttl">{duo.rich(spec["title"])}</div></div>',
         '<svg class="scene" viewBox="0 0 1080 1920">',
         f'<rect x="0" y="{GROUND}" width="1080" height="160" fill="#C79A63"/>',
         f'<path d="M0 {GROUND} Q270 {GROUND-14} 540 {GROUND} T1080 {GROUND}" stroke="#6E9E4E" stroke-width="14" fill="none"/>',
         f'<g class="k" data-k="empty">{EMPTY}</g>',
         f'<g class="k" data-k="bowl">{BOWL_SVG}</g>', f'<g class="k" data-k="env">{ENVELOPE}</g>', f'<g class="k" data-k="env2">{ENVELOPE}</g>']
    heights = [260, 380, 500]
    for i in range(3):
        s.append(f'<g class="k" data-k="p{i}">{plant(heights[i])}</g>')
    for i in range(N_SEED):
        s.append(f'<g class="k" data-k="s{i}">{SEED}</g>')
        s.append(f'<g class="k" data-k="t{i}">{SEED}</g>')
    s.append('</svg>')
    poses = "".join(f'<g class="pose" data-p="{p}" style="display:none">{duo.person("sprout", p)}</g>' for p in nc.ARMS)
    s.append(f'<svg class="me" viewBox="0 0 360 470" overflow="visible">{poses}</svg>')
    for lid, lb in labels.items():
        s.append(f'<div class="lab k {lb.get("style", "")}" data-k="L.{lid}" style="left:{lb["x"]}px;top:{lb["y"]}px">{duo.rich(lb["text"])}</div>')
    for cid in ("conclude", "ask"):
        c = spec.get(cid)
        if c:
            cls = "box dark" if cid == "conclude" else "box"
            s.append(f'<div class="center k" data-k="C.{cid}" style="top:{c.get("y", 560)}px;opacity:0"><div class="{cls}">{duo.rich(c["text"])}</div></div>')
    hook = spec.get("hook")
    if hook:
        sub = f'<small>{html.escape(hook["sub"])}</small>' if hook.get("sub") else ""
        s.append(f'<div class="hook k" data-k="hook" style="opacity:1"><div class="big">{duo.rich(hook["big"])}{sub}</div></div>')
    for bi, b in enumerate(spec["beats"]):
        s.append(f'<div class="sub" data-b="{bi}" style="opacity:0"><span>{duo.rich(b["say"])}</span></div>')
    s.append(f'<div class="foot">{html.escape(spec.get("foot", ""))}</div></body></html>')
    return "".join(s)


# ---------------------------------------------------------------- 연출 (키프레임)
class Tracks:
    """요소마다 (t, x, y, scale, opacity) 키프레임."""

    def __init__(self):
        self.k = {}

    def set(self, el, t, x=None, y=None, s=None, o=None):
        lst = self.k.setdefault(el, [])
        prev = lst[-1] if lst else [0.0, 0, 0, 1, 0]
        self.k[el].append([round(t, 3), prev[1] if x is None else x, prev[2] if y is None else y,
                           prev[3] if s is None else s, prev[4] if o is None else o])

    def pop(self, el, t, x=0, y=0, s=1, dur=0.35):
        self.set(el, t, x, y, s * 0.6, 0)
        self.set(el, t + dur, x, y, s, 1)

    def fade(self, el, t, dur=0.3):
        self.set(el, t)
        self.set(el, t + dur, o=0)

    def move(self, el, t, x, y, dur=0.7, s=None):
        self.set(el, t)
        self.set(el, t + dur, x, y, s)


def choreo(spec, tl):
    T = Tracks()
    at = {b["key"]: tl[i] for i, b in enumerate(spec["beats"])}
    for k in at:
        if k not in KEYS:
            raise duo.SpecError(f"key '{k}' 를 모릅니다. 쓸 수 있는 key: {', '.join(KEYS)}")
    lab_times = {}
    for i, b in enumerate(spec["beats"]):
        for j, lid in enumerate(b.get("labels", [])):
            lab_times[lid] = tl[i]["start"] + 0.4 + 0.45 * j
        for lid in b.get("hide", []):
            lab_times.setdefault("~" + lid, tl[i]["start"])
    if "hook" in at:
        T.set("hook", 0, o=1)
        T.set("hook", at["hook"]["end"] - 0.35, o=1)
        T.set("hook", at["hook"]["end"] - 0.05, o=0)
    if "payday" in at:
        t0 = at["payday"]["start"] + 0.2
        T.pop("env", t0, *ENV, s=ENV_S)
        for i in range(N_SEED):
            T.pop(f"s{i}", t0 + 0.5 + 0.06 * i, *seed_home(i), s=SEED_S)
    if "spend" in at:
        t0 = at["spend"]["start"] + 0.2
        T.pop("bowl", t0, *BOWL, s=BOWL_S)
        for i in range(N_SEED):
            ts = t0 + 0.9 + 0.12 * i
            T.move(f"s{i}", ts, BOWL[0] - 100 + (i % 5) * 50, BOWL[1] - 20 + (i % 2) * 16, 0.7)
            T.fade(f"s{i}", ts + 0.9, 0.35)
        T.fade("env", t0 + 2.6, 0.4)
    if "empty" in at:
        T.pop("empty", at["empty"]["start"] + 0.3, 740, GROUND)
    if "change" in at:
        t0 = at["change"]["start"] + 0.2
        T.fade("empty", t0, 0.3)
        T.pop("env2", t0 + 0.2, *ENV, s=ENV_S)
        for i in range(N_SEED):
            T.pop(f"t{i}", t0 + 0.5 + 0.04 * i, *seed_home(i), s=SEED_S)
        for j in range(3):  # 한 줌(앞의 세 알)을 먼저 땅으로
            T.move(f"t{j}", t0 + 1.6 + 0.3 * j, SPOTS[j][0], SPOTS[j][1] - 6, 0.8)
    if "rest" in at:
        t0 = at["rest"]["start"] + 0.2
        for i in range(3, N_SEED):
            ts = t0 + 0.3 + 0.1 * (i - 3)
            T.move(f"t{i}", ts, BOWL[0] - 100 + (i % 5) * 50, BOWL[1] - 20 + (i % 2) * 16, 0.7)
            T.fade(f"t{i}", ts + 0.9, 0.35)
        T.fade("env2", t0 + 1.8, 0.4)
    if "sprout" in at:
        t0 = at["sprout"]["start"] + 0.3
        for j in range(3):
            T.fade(f"t{j}", t0 + 0.2 * j, 0.25)
            T.set(f"p{j}", t0 + 0.2 * j, SPOTS[j][0], SPOTS[j][1], 0.05, 0)
            T.set(f"p{j}", t0 + 0.2 * j + 0.6, SPOTS[j][0], SPOTS[j][1], 0.22, 1)
    if "grow" in at:
        t0 = at["grow"]["start"] + 0.3
        for j in range(3):
            T.set(f"p{j}", t0 + 0.15 * j)
            T.set(f"p{j}", t0 + 0.15 * j + 1.6, s=PLANT_S)
        T.fade("bowl", t0, 0.5)
    for el in list(T.k):
        T.k[el].sort(key=lambda r: r[0])
    for lid, t in lab_times.items():
        if lid.startswith("~"):
            continue
        T.pop("L." + lid, t)
        if "~" + lid in lab_times:
            T.fade("L." + lid, lab_times["~" + lid])
    for cid in ("conclude", "ask"):
        if cid in at:
            T.pop("C." + cid, at[cid]["start"] + 0.2)
            if cid == "conclude" and "ask" in at:
                T.fade("C.conclude", at["ask"]["start"])
    for el in T.k:
        T.k[el].sort(key=lambda r: r[0])
    return T.k


SEEK_JS = """(st) => {
  const ease = x => x < .5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
  const val = (kf, t) => {
    if (t <= kf[0][0]) return kf[0];
    for (let i = 1; i < kf.length; i++) {
      if (t < kf[i][0]) { const a = kf[i - 1], b = kf[i], p = ease((t - a[0]) / Math.max(1e-6, b[0] - a[0]));
        return [t, a[1] + (b[1] - a[1]) * p, a[2] + (b[2] - a[2]) * p, a[3] + (b[3] - a[3]) * p, a[4] + (b[4] - a[4]) * p]; }
    }
    return kf[kf.length - 1];
  };
  document.querySelectorAll('.k').forEach(el => {
    const kf = st.tracks[el.dataset.k]; if (!kf) { el.style.opacity = 0; return; }
    const v = val(kf, st.t);
    el.style.opacity = v[4];
    if (el instanceof SVGElement) el.setAttribute('transform', 'translate(' + v[1].toFixed(1) + ' ' + v[2].toFixed(1) + ') scale(' + v[3].toFixed(3) + ')');
    else el.style.transform = 'scale(' + v[3].toFixed(3) + ')';
  });
  document.querySelectorAll('.me .pose').forEach(g => g.style.display = g.dataset.p === st.pose ? '' : 'none');
  const bob = document.querySelector('.me .pose[data-p="' + st.pose + '"] .bob');
  if (bob) bob.setAttribute('transform', 'translate(0 ' + (Math.sin(st.t * 2.4) * 4).toFixed(2) + ')');
  const ph = st.t % 3.6;
  document.querySelectorAll('.me .eyes').forEach(e => e.setAttribute('transform', ph < 0.12 ? 'translate(0 152) scale(1 0.1)' : ''));
  document.querySelectorAll('.sub').forEach(s => { const b = +s.dataset.b; s.style.opacity = b === st.beat ? Math.min(1, (st.t - st.bstart) / 0.15) : 0; });
}"""


def timeline(spec):
    t, out = 0.0, []
    for b in spec["beats"]:
        d = duo.beat_len(b)
        out.append(dict(start=t, end=t + d))
        t += d
    return out


def state_at(spec, tl, tracks, t):
    bi = next((i for i, b in enumerate(tl) if b["start"] <= t < b["end"]), len(tl) - 1)
    pose = "think"
    for j in range(bi + 1):
        pose = spec["beats"][j].get("pose", pose)
    return dict(t=t, beat=bi, bstart=tl[bi]["start"], tracks=tracks, pose=pose)


def _open(pw, spec, work):
    b, _ = browser.launch(pw)
    page = b.new_page(viewport={"width": 1080, "height": 1920})
    f = Path(work) / "page.html"
    f.write_text(page_html(spec), encoding="utf-8")
    page.goto(f.as_uri())
    page.evaluate("document.fonts.ready")
    return b, page


def run(spec, out, still=False):
    from playwright.sync_api import sync_playwright
    tl = timeline(spec)
    tracks = choreo(spec, tl)
    total = tl[-1]["end"]
    with tempfile.TemporaryDirectory(prefix="grow-") as work, sync_playwright() as pw:
        b, page = _open(pw, spec, work)
        try:
            if still:
                Path(out).mkdir(parents=True, exist_ok=True)
                for i, bt in enumerate(tl):
                    page.evaluate(SEEK_JS, state_at(spec, tl, tracks, bt["end"] - 0.05))
                    page.screenshot(path=str(Path(out) / f"beat_{i + 1:02d}.png"))
                page.evaluate(SEEK_JS, state_at(spec, tl, tracks, 0))
                page.screenshot(path=str(Path(out) / "beat_00_first.png"))
            else:
                enc = PipeEncoder(out)
                try:
                    for i in range(int(round(total * FPS))):
                        page.evaluate(SEEK_JS, state_at(spec, tl, tracks, i / FPS))
                        enc.write(page.screenshot(type="png"))
                    enc.close()
                except BaseException:
                    enc.abort()
                    raise
        finally:
            b.close()
    return total, tl


def main(argv=None):
    ap = argparse.ArgumentParser(description="비유 하나를 키우는 1인칭 스토리 릴스 (음악 없음)")
    ap.add_argument("mode", choices=["reel", "still"])
    ap.add_argument("spec")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    try:
        spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
        total, tl = run(spec, a.out, still=a.mode == "still")
        print(f"duration={total:.1f}s")
        for bt, b in zip(tl, spec["beats"]):
            print(f"{bt['start']:5.1f}-{bt['end']:5.1f}s  {duo.HL.sub(lambda m: m.group(1), b['say'])}")
    except duo.SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    except (browser.BrowserLaunchError, browser.FontLoadError, EncodeError) as e:
        print(f"환경 오류: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
