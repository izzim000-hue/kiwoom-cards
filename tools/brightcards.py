#!/usr/bin/env python3
"""밝고 귀여운 정보 카드뉴스 (2026-11-24 국가장학금 편에서 시작, 젊은 취향 주제용).

하늘·레몬·민트·핑크 파스텔, 둥근 스티커, 학사모 쓴 동전 캐릭터 '동글이', 손글씨 메모(Poor Story).

    python3 tools/brightcards.py OUT_DIR      # card_1.png ... + preview.png
내용은 아래 '데이터 블록'만 고치면 된다.
"""
import sys
from pathlib import Path

FONT = (Path(__file__).resolve().parent / "fonts").as_uri()

# ───────────── 데이터 블록 ─────────────
FOOT = "2026.11.23 정부 발표 보도 기준 · 실제 지급은 심사 결과에 따라 달라질 수 있어요"
START = ("2026.11.24", "화", "오전 9시")
END = ("2027.1.7", "목", "오후 6시")
BANDS = [  # 새 구간, 기존 구간, 연간 지원(만 원, None=미지원), 다자녀 첫째·둘째
    ("가", "1~3", 600, 610), ("나", "4~6", 440, 505), ("다", "7~8", 360, 465),
    ("라", "9", 100, 135), ("마", "10", None, None)]
CHECKS = ["신청 기간 안에 신청 완료!", "부모님(가구원) 정보 제공 동의까지 완료",
          "재학생은 1차 신청이 원칙", "고3·N수생도 합격 전에 지금 신청 가능", "국가근로장학금도 같은 기간에 함께"]
# ──────────────────────────────────────

COLORS = {"가": "#FF8FA3", "나": "#FFB86B", "다": "#FFD84D", "라": "#7FD8BE", "마": "#B9C3D6"}

CSS = f"""
@font-face{{font-family:NK;src:url({FONT}/NotoSansKR-Regular.otf);font-weight:400}}
@font-face{{font-family:NK;src:url({FONT}/NotoSansKR-Bold.otf);font-weight:700}}
@font-face{{font-family:NK;src:url({FONT}/NotoSansKR-Black.otf);font-weight:900}}
@font-face{{font-family:PS;src:url({FONT}/PoorStory-Regular.ttf)}}
:root{{--ink:#24324A;--sky:#DDF0FF;--lemon:#FFF3B0;--mint:#CFF5E7;--pink:#FFD9E2;--blue:#3D7BFF}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:NK;color:var(--ink);word-break:keep-all;background:#999}}
.card{{width:1080px;height:1350px;position:relative;overflow:hidden;
  background:var(--sky) radial-gradient(circle at 1px 1px,rgba(61,123,255,.13) 2px,transparent 2.5px) 0 0/36px 36px}}
.card.lemon{{background-color:#FFF8D6}} .card.mint{{background-color:#E3FAF1}} .card.pink{{background-color:#FFEAF0}}
.page{{position:absolute;right:70px;top:64px;background:var(--ink);color:#fff;font-weight:700;font-size:26px;padding:8px 22px;border-radius:30px}}
.brand{{position:absolute;left:70px;top:70px;font-weight:900;font-size:28px;color:var(--blue)}}
.foot{{position:absolute;left:70px;right:70px;bottom:46px;font-size:20px;color:#6A7890;text-align:center}}
.chip{{display:inline-block;background:#fff;border:4px solid var(--ink);border-radius:40px;padding:8px 30px;font-weight:900;font-size:34px;box-shadow:6px 6px 0 var(--ink)}}
.h1{{font-weight:900;font-size:96px;line-height:1.12;letter-spacing:-.03em}}
.h2{{font-weight:900;font-size:76px;line-height:1.15;letter-spacing:-.03em}}
.mark{{background:linear-gradient(transparent 58%,#FFE15A 58%)}}
.pen{{font-family:PS;font-weight:400}}
.panel{{background:#fff;border:4px solid var(--ink);border-radius:36px;box-shadow:10px 10px 0 var(--ink)}}
.star{{position:absolute}}
"""


def star(x, y, s=48, c="#FFD84D", r=0):
    return (f'<svg class="star" style="left:{x}px;top:{y}px;transform:rotate({r}deg)" width="{s}" height="{s}" viewBox="0 0 24 24">'
            f'<path d="M12 1.5l3 6.8 7.3.7-5.5 4.9 1.6 7.2L12 17.3 5.6 21.1l1.6-7.2L1.7 9l7.3-.7z" fill="{c}" stroke="#24324A" stroke-width="1.6" stroke-linejoin="round"/></svg>')


def mascot(x, y, s=260, mood="smile"):
    """학사모 쓴 동전 '동글이' (원본 그림)."""
    mouth = ('<path d="M84 128 q16 18 32 0" stroke="#24324A" stroke-width="6" fill="#FF7A8A" stroke-linecap="round"/>'
             if mood == "smile" else '<ellipse cx="100" cy="132" rx="12" ry="14" fill="#FF7A8A" stroke="#24324A" stroke-width="5"/>')
    return f'''<svg style="position:absolute;left:{x}px;top:{y}px" width="{s}" height="{s}" viewBox="0 0 200 200">
<circle cx="100" cy="112" r="72" fill="#FFD84D" stroke="#24324A" stroke-width="7"/>
<circle cx="100" cy="112" r="56" fill="none" stroke="#F2B705" stroke-width="5"/>
<circle cx="76" cy="104" r="8" fill="#24324A"/><circle cx="124" cy="104" r="8" fill="#24324A"/>
<circle cx="79" cy="101" r="2.6" fill="#fff"/><circle cx="127" cy="101" r="2.6" fill="#fff"/>
<ellipse cx="62" cy="124" rx="11" ry="7" fill="#FF9DB0" opacity=".8"/><ellipse cx="138" cy="124" rx="11" ry="7" fill="#FF9DB0" opacity=".8"/>
{mouth}
<path d="M40 44 L100 20 L160 44 L100 68 Z" fill="#24324A"/><path d="M68 56 v18 q32 16 64 0 v-18" fill="#24324A"/>
<path d="M150 44 v34" stroke="#24324A" stroke-width="4"/><circle cx="150" cy="82" r="7" fill="#FF8FA3" stroke="#24324A" stroke-width="3"/>
</svg>'''


def frame(i, n, body, cls=""):
    return (f'<section class="card {cls}" id="c{i}"><div class="brand">키움멘토</div>'
            f'<div class="page">{i}/{n}</div>{body}<div class="foot">{FOOT}</div></section>')


def cards():
    out = []
    # 1 표지
    out.append(("", f'''
<div style="position:absolute;left:70px;top:200px"><span class="chip" style="background:#FFE15A">2027 국가장학금</span></div>
<div class="h1" style="position:absolute;left:70px;top:310px;font-size:120px">우리 집은<br><span class="mark">몇 구간</span>일까?</div>
<div style="position:absolute;left:74px;top:640px;font-size:40px;font-weight:700;line-height:1.5">10칸이 5칸으로 바뀌고,<br>신청은 <b style="color:var(--blue)">오늘부터</b> 시작이에요</div>
{mascot(640, 760, 360)}
<div class="pen" style="position:absolute;left:96px;top:880px;font-size:50px;transform:rotate(-4deg);line-height:1.3">대학생·예비 대학생,<br>그리고 엄마 아빠도<br>같이 보기!</div>
<div style="position:absolute;left:70px;top:1150px"><span class="chip" style="font-size:28px">저장해 두고 하나씩 체크 ✓</span></div>
{star(900, 190, 70)}{star(980, 300, 44, "#FF8FA3", 20)}{star(560, 730, 40, "#7FD8BE", -10)}'''))
    # 2 일정
    chips = "".join(f'<span class="chip" style="font-size:30px;margin:0 14px 18px 0;box-shadow:4px 4px 0 var(--ink);background:{c}">{t}</span>'
                    for t, c in [("신입생", "#FFD9E2"), ("재학생", "#DDF0FF"), ("편입생", "#CFF5E7"), ("재입학생", "#FFF3B0"), ("복학생", "#FFE3C7")])
    out.append(("lemon", f'''
<div class="h2" style="position:absolute;left:70px;top:170px">언제까지<br>신청해요?</div>
<div class="panel" style="position:absolute;left:70px;right:70px;top:380px;padding:40px 48px">
  <div style="display:flex;align-items:center;gap:30px">
    <div style="flex:1"><div style="font-size:28px;font-weight:700;color:#6A7890">시작</div>
      <div style="font-size:52px;font-weight:900">{START[0]}</div><div style="font-size:32px;font-weight:700">({START[1]}) {START[2]}</div></div>
    <div style="font-size:70px;font-weight:900;color:var(--blue)">→</div>
    <div style="flex:1"><div style="font-size:28px;font-weight:700;color:#FF5C7A">마감</div>
      <div style="font-size:52px;font-weight:900">{END[0]}</div><div style="font-size:32px;font-weight:700">({END[1]}) {END[2]}</div></div>
  </div>
  <div class="pen" style="margin-top:26px;font-size:40px;color:#FF5C7A">주말·공휴일도 OK! 마감 날은 저녁 6시 땡!</div>
</div>
<div style="position:absolute;left:70px;top:770px;font-size:34px;font-weight:900">누가 신청해요?</div>
<div style="position:absolute;left:70px;right:70px;top:830px">{chips}</div>
<div style="position:absolute;left:70px;right:330px;top:1010px;font-size:32px;font-weight:700;line-height:1.5">
  고3·N수생도 <span class="mark">합격 전에 지금</span> 신청할 수 있어요.<br>신청은 한국장학재단 누리집·앱에서!</div>
{mascot(790, 930, 230)}{star(930, 180, 60)}'''))
    # 3 구간 변화
    groups = [("가", 3), ("나", 3), ("다", 2), ("라", 1), ("마", 1)]
    pills, k = "", 1
    for name, cnt in groups:
        inner = "".join(f'<div style="width:58px;height:58px;border-radius:50%;background:#fff;border:3px solid var(--ink);display:flex;align-items:center;justify-content:center;font-weight:900;font-size:26px">{k+j}</div>' for j in range(cnt))
        k += cnt
        pills += (f'<div style="display:flex;align-items:center;gap:26px;margin-bottom:22px">'
                  f'<div style="width:300px;display:flex;gap:10px;justify-content:flex-end">{inner}</div>'
                  f'<div style="font-size:50px;font-weight:900;color:var(--blue)">→</div>'
                  f'<div style="background:{COLORS[name]};border:4px solid var(--ink);border-radius:28px;box-shadow:6px 6px 0 var(--ink);'
                  f'padding:6px 40px;font-size:46px;font-weight:900">{name} 구간</div></div>')
    out.append(("mint", f'''
<div class="h2" style="position:absolute;left:70px;top:170px">10칸 → <span class="mark">5칸</span>으로<br>바뀌었어요</div>
<div class="panel" style="position:absolute;left:70px;right:70px;top:420px;padding:46px 40px 26px">
  <div style="display:flex;gap:26px;margin:0 0 20px;font-size:26px;font-weight:700;color:#6A7890"><div style="width:300px;text-align:right">예전 구간</div><div style="width:50px"></div><div>2027년부터</div></div>
  {pills}</div>
<div class="pen" style="position:absolute;left:80px;top:1130px;font-size:42px;transform:rotate(-2deg)">기초생활수급·차상위는 따로 지원해요!</div>
{star(940, 1080, 64, "#FF8FA3", 15)}'''))
    # 4 금액
    bars = '<div style="display:flex;align-items:center;gap:20px;margin-bottom:24px"><div style="width:150px;font-size:30px;font-weight:900">기초·차상위</div><div style="flex:1;height:64px;border-radius:32px;border:4px solid var(--ink);background:repeating-linear-gradient(45deg,#FFE15A 0 18px,#FFF3B0 18px 36px);display:flex;align-items:center;padding-left:26px;font-size:32px;font-weight:900">등록금 전액!</div></div>'
    for name, _, amt, _m in BANDS:
        w = 0 if amt is None else amt / 600 * 100
        label = "지원 없음" if amt is None else f"{amt}만 원"
        bar = (f'<div style="width:{max(w, 0):.0f}%;height:64px;border-radius:32px;border:4px solid var(--ink);background:{COLORS[name]}"></div>' if amt else "")
        bars += (f'<div style="display:flex;align-items:center;gap:20px;margin-bottom:24px"><div style="width:150px;font-size:40px;font-weight:900">{name}</div>'
                 f'<div style="flex:1;display:flex;align-items:center;gap:18px"><div style="flex:0 0 72%;display:flex">{bar}</div>'
                 f'<div style="font-size:34px;font-weight:900;white-space:nowrap;{"color:#8A94A6" if amt is None else ""}">{label}</div></div></div>')
    out.append(("", f'''
<div class="h2" style="position:absolute;left:70px;top:170px">그래서 1년에<br><span class="mark">얼마</span> 받아요?</div>
<div style="position:absolute;right:70px;top:335px"><span class="chip" style="font-size:26px;background:#CFF5E7">국가장학금 I유형</span></div>
<div class="panel" style="position:absolute;left:70px;right:70px;top:420px;padding:44px 40px 20px">{bars}</div>
<div style="position:absolute;left:70px;right:70px;top:1110px;font-size:30px;font-weight:700;line-height:1.5">
  모두 <span class="mark">연간 최대</span> 금액이고, 실제 등록금 범위 안에서 지원돼요.</div>
{mascot(860, 120, 170, "wow")}'''))
    # 5 다자녀
    rows = "".join(
        f'<div style="display:flex;align-items:center;justify-content:space-between;padding:16px 0;border-bottom:3px dashed #C9D3E3">'
        f'<span style="background:{COLORS[n]};border:3px solid var(--ink);border-radius:20px;padding:2px 26px;font-size:36px;font-weight:900">{n}</span>'
        f'<span style="font-size:42px;font-weight:900">{m}만 원</span></div>' for n, _, _a, m in BANDS if m)
    out.append(("pink", f'''
<div class="h2" style="position:absolute;left:70px;top:170px">형제자매 많으면<br><span class="mark">더</span> 받아요</div>
<div style="position:absolute;left:70px;top:440px;width:450px" class="panel">
  <div style="padding:34px 40px"><div style="font-size:34px;font-weight:900;margin-bottom:10px">첫째·둘째</div>{rows}</div></div>
<div style="position:absolute;right:70px;top:440px;width:440px" class="panel">
  <div style="padding:34px 40px;background:#FFF3B0;border-radius:32px">
    <div style="font-size:34px;font-weight:900;margin-bottom:24px">셋째부터는</div>
    <div style="font-size:30px;font-weight:700;color:#6A7890">기초·차상위 ~ 다 구간</div>
    <div style="font-size:54px;font-weight:900;color:#FF5C7A;margin-bottom:26px">등록금 전액</div>
    <div style="font-size:30px;font-weight:700;color:#6A7890">라 구간</div>
    <div style="font-size:54px;font-weight:900">200만 원</div></div></div>
<div class="pen" style="position:absolute;left:560px;top:960px;font-size:40px;transform:rotate(-3deg);line-height:1.3">셋째는 다 구간까지<br>등록금 걱정 덜어요</div>
<div style="position:absolute;left:70px;right:70px;top:1130px;font-size:28px;font-weight:700;color:#6A7890">연간 금액 · 실제 등록금 범위 안에서 지원</div>
{star(110, 1000, 70, "#FF8FA3")}{star(220, 1050, 44)}'''))
    # 6 구간 정하는 법 + 판단
    box = lambda t, s, c: (f'<div style="flex:1;background:{c};border:4px solid var(--ink);border-radius:30px;box-shadow:6px 6px 0 var(--ink);'
                           f'padding:30px 10px;text-align:center"><div style="font-size:42px;font-weight:900">{t}</div>'
                           f'<div style="font-size:24px;font-weight:700;margin-top:8px;line-height:1.35">{s}</div></div>')
    plus = '<div style="font-size:60px;font-weight:900;color:var(--blue);align-self:center">+</div>'
    out.append(("", f'''
<div class="h2" style="position:absolute;left:70px;top:170px">구간은 <span class="mark">월급만</span>으로<br>안 정해져요</div>
<div style="position:absolute;left:70px;right:70px;top:440px;display:flex;gap:18px">
  {box("월급", "근로·사업·<br>연금 소득", "#DDF0FF")}{plus}{box("집·예금·차", "재산을 소득으로<br>바꿔서 더해요", "#FFF3B0")}{plus}{box("가족", "미혼이면 부모님,<br>기혼이면 배우자", "#FFD9E2")}</div>
<div style="position:absolute;left:70px;top:720px;font-size:30px;font-weight:700;color:#6A7890">그래서 가족의 <b style="color:var(--ink)">정보 제공 동의</b>가 꼭 필요해요</div>
<div class="panel" style="position:absolute;left:70px;right:70px;top:820px;padding:40px 46px;background:#2F4F3E;color:#fff">
  <div style="font-size:28px;font-weight:700;color:#E3CFA4">재무설계사 키움멘토의 한마디</div>
  <div style="font-size:40px;font-weight:900;line-height:1.45;margin-top:14px">같은 월급이어도 집·예금에 따라<br>구간이 달라질 수 있어요.<br>우리 집 돈의 지도를 알면, 구간도 보여요.</div></div>
{star(950, 170, 60, "#7FD8BE", 10)}'''))
    # 7 체크리스트
    items = "".join(
        f'<div style="display:flex;align-items:center;gap:26px;padding:22px 0;border-bottom:3px dashed #C9D3E3">'
        f'<div style="flex:none;width:58px;height:58px;border:4px solid var(--ink);border-radius:14px;background:#fff"></div>'
        f'<div style="font-size:38px;font-weight:900">{t}</div></div>' for t in CHECKS)
    out.append(("lemon", f'''
<div class="h2" style="position:absolute;left:70px;top:170px">신청 전에<br><span class="mark">이것만</span> 체크!</div>
<div class="panel" style="position:absolute;left:70px;right:70px;top:420px;padding:20px 46px">{items}</div>
<div style="position:absolute;left:70px;top:1130px"><span class="chip" style="background:#FF8FA3">저장 → 마감 전에 다시 보기</span></div>
{mascot(820, 1000, 200)}{star(930, 180, 64)}'''))
    return out


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
    cs = cards(); n = len(cs)
    page = ("<!doctype html><html lang='ko'><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"
            + "".join(frame(i + 1, n, b, c) for i, (c, b) in enumerate(cs)) + "</body></html>")
    src = out / "_cards.html"; src.write_text(page, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        pg.goto(src.as_uri()); pg.evaluate("document.fonts.ready")
        for i in range(1, n + 1):
            pg.locator(f"#c{i}").screenshot(path=str(out / f"card_{i}.png"))
        b.close()
    src.unlink()
    from PIL import Image
    w, h, g, cols = 432, 540, 16, 4
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * g, rows * h + (rows + 1) * g), "#E5E8EE")
    for i in range(n):
        sheet.paste(Image.open(out / f"card_{i+1}.png").resize((w, h)), (g + (i % cols) * (w + g), g + (i // cols) * (h + g)))
    sheet.save(out / "preview.png"); print(f"{n}장 → {out}")


if __name__ == "__main__":
    main()
