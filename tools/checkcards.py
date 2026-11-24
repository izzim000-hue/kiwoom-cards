#!/usr/bin/env python3
"""키움멘토 점검표 카드뉴스 생성기 (2026-11-23 사용자 승인 'A 점검표' 틀).

딥그린 #2F4F3E + 흰 종이 + 굵은 고딕(Noto Sans KR). 캐릭터·손글씨 없음.
보는 사람이 펜을 들고 '예/모름'을 체크하고 싶어지는 진단표 형식.

    python3 tools/checkcards.py SPEC.json OUT_DIR      # card_1.png ... + preview.png

SPEC.json
  {"series": "키움멘토 점검표", "no": "01", "tag": "50대 은퇴 준비",
   "disclaimer": "세금·건보료는 ...",          # 본문 카드 아래 작은 글씨
   "cards": [ {...}, ... ]}                    # 6장 권장

카드 종류 (type)
  cover     title(줄바꿈 \\n, ==강조==), sub, preview[문장 4개], save
  checklist title, rows[{q, sub?}], judge(==강조== 가능)
  steps     title, rows[{no, do}]               '모름'이 나온 줄별 첫 한 걸음
  sheet     title, cols[4], rows[첫 칸 글자], note   저장해서 채우는 빈 양식
            rows 항목을 리스트로 주면 칸을 채운 표("dense": true 면 줄 높이를 줄임)
  why       kicker, big, body                  설계사의 판단 한 문장
  last      title, body, question
본문에서 ==글자== 는 강조(형광 밑줄 또는 금색 글자)로 바뀐다.
"""
import html
import json
import re
import sys
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "fonts"

CSS = """
@font-face{font-family:NK;src:url(%(f)s/NotoSansKR-Regular.otf);font-weight:400}
@font-face{font-family:NK;src:url(%(f)s/NotoSansKR-Bold.otf);font-weight:700}
@font-face{font-family:NK;src:url(%(f)s/NotoSansKR-Black.otf);font-weight:900}
:root{--green:#2F4F3E;--ink:#1E2722;--muted:#6E7771;--line:#D8DCD7;--paper:#FAF9F6;--gold:#B08D57}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#888;font-family:NK;color:var(--ink);word-break:keep-all}
.card{width:1080px;height:1350px;position:relative;overflow:hidden;background:var(--paper)}
.top{position:absolute;left:84px;right:84px;top:72px;display:flex;justify-content:space-between;font-size:24px;color:var(--muted)}
.top b{color:var(--green);font-weight:700}
.foot{position:absolute;left:84px;right:84px;bottom:64px;display:flex;justify-content:space-between;align-items:flex-end;gap:30px;font-size:21px;color:var(--muted);line-height:1.4}
.foot .brand{font-weight:700;color:var(--green);font-size:23px;flex:none}
.hl{background:linear-gradient(transparent 62%,#E7DCC6 62%)}
.box{display:block;width:42px;height:42px;border:3px solid var(--ink);border-radius:5px;background:#fff}
.t2{position:absolute;left:84px;right:84px;top:170px;font-size:62px;font-weight:900;line-height:1.25;letter-spacing:-.02em}
/* cover */
.cv .rule{position:absolute;left:84px;right:84px;top:122px;border-top:3px solid var(--green)}
.cv .title{position:absolute;left:84px;top:210px;font-size:104px;font-weight:900;line-height:1.16;letter-spacing:-.03em}
.cv .sub{position:absolute;left:84px;top:615px;font-size:34px;color:#46504A;line-height:1.5}
.cv .prev{position:absolute;left:84px;right:84px;top:750px;border:2px solid var(--ink);background:#fff}
.cv .h,.cv .r{display:grid;grid-template-columns:70px 1fr 110px 110px;align-items:center}
.cv .h div,.cv .r div{padding-left:22px}
.cv .h{height:64px;background:var(--green);color:#fff;font-size:24px;font-weight:700}
.cv .r{height:82px;border-top:1px solid var(--line);font-size:28px}
.cv .r .n{color:var(--muted);font-weight:700}
.cv .box{width:34px;height:34px;border-width:2.5px;border-radius:4px}
.cv .r.fade{opacity:.45}
.cv .save{position:absolute;right:84px;bottom:130px;font-size:28px;font-weight:700;color:var(--green)}
/* checklist */
.ck .tbl{position:absolute;left:84px;right:84px;top:370px;border-top:3px solid var(--ink);border-bottom:3px solid var(--ink)}
.ck .h,.ck .r{display:grid;grid-template-columns:76px 1fr 104px 104px;align-items:center}
.ck .h{height:66px;font-size:24px;font-weight:700;color:var(--muted);border-bottom:1.5px solid var(--ink)}
.ck .c{display:flex;justify-content:center;text-align:center}
.ck .r{min-height:118px;border-top:1px solid var(--line);padding:18px 0}
.ck .r:nth-child(2){border-top:none}
.ck .n{font-size:40px;font-weight:900;color:var(--green)}
.ck .q{font-size:33px;font-weight:700;line-height:1.38}
.ck .q small,.st .q small{display:block;font-size:23px;font-weight:400;color:var(--muted);margin-top:6px}
.ck .circ{position:absolute;left:868px;top:376px}
.judge{position:absolute;left:84px;right:84px;top:1040px;background:var(--green);color:#fff;padding:30px 36px;font-size:31px;line-height:1.5;font-weight:700}
.judge .hl{background:none;color:#E9D9B8}
/* steps */
.st .tbl{position:absolute;left:84px;right:84px;top:370px;border-top:3px solid var(--ink)}
.st .r{display:grid;grid-template-columns:150px 1fr;align-items:center;min-height:126px;border-bottom:1px solid var(--line);padding:16px 0}
.st .tag{display:inline-block;border:2px solid var(--green);color:var(--green);border-radius:30px;padding:6px 18px;font-size:24px;font-weight:700}
.st .q{font-size:32px;font-weight:700;line-height:1.4}
/* sheet */
.sh .tbl{position:absolute;left:84px;right:84px;top:390px;border:2px solid var(--ink);background:#fff}
.sh .h,.sh .r{display:grid;grid-template-columns:1.25fr 1fr 1fr 1fr}
.sh .h div{background:var(--green);color:#fff;font-size:25px;font-weight:700;padding:20px 22px}
.sh .r div{height:118px;border-top:1px solid var(--line);border-left:1px solid var(--line);padding:0 22px;display:flex;align-items:center;font-size:29px;font-weight:700}
.sh .r div:first-child{border-left:none}
.sh .dense .r div{height:100px;font-size:30px}
.sh .dense .r div .hl{background:none;color:var(--green);font-weight:900}
.sh .note{position:absolute;left:84px;right:84px;top:1050px;font-size:30px;line-height:1.55;color:#46504A}
.sh .note b{color:var(--green)}
/* why */
.wy{background:var(--green);color:#fff}
.wy .top{color:#B9C8BE}.wy .top b{color:#fff}
.wy .foot{color:#A9BAAF}.wy .foot .brand{color:#fff}
.wy .kick{position:absolute;left:84px;top:250px;font-size:30px;font-weight:700;color:#E3CFA4}
.wy .big{position:absolute;left:84px;right:84px;top:330px;font-size:72px;font-weight:900;line-height:1.3;letter-spacing:-.02em}
.wy .big .hl{background:none;color:#E3CFA4}
.wy .body{position:absolute;left:84px;right:84px;top:820px;font-size:34px;line-height:1.6;color:#D3DDD6;border-top:2px solid rgba(255,255,255,.35);padding-top:40px}
/* last */
.ls .title{position:absolute;left:84px;right:84px;top:260px;font-size:84px;font-weight:900;line-height:1.22;letter-spacing:-.03em}
.ls .body{position:absolute;left:84px;right:84px;top:620px;font-size:36px;line-height:1.6;color:#46504A}
.ls .q{position:absolute;left:84px;right:84px;top:900px;border-top:3px solid var(--green);padding-top:34px;font-size:40px;font-weight:900;color:var(--green);line-height:1.4}
"""

CIRCLE = ('<svg class="circ" width="140" height="70" viewBox="0 0 140 70"><path d="M20 38 C 18 12, 118 6, 124 32 '
          'C 130 58, 30 66, 16 44 C 10 34, 40 18, 70 16" fill="none" stroke="#B08D57" stroke-width="4" '
          'stroke-linecap="round"/></svg>')


def fmt(s):
    s = html.escape(s or "")
    s = re.sub(r"==(.+?)==", r'<span class="hl">\1</span>', s, flags=re.S)
    return s.replace("\n", "<br>")


def card(spec, c, i, n):
    t = c["type"]
    head = (f'<div class="top"><span><b>{html.escape(spec["series"])}</b> · No.{html.escape(spec["no"])}</span>'
            f'<span>{html.escape(spec["tag"]) if i == 1 else f"{i:02d} / {n:02d}"}</span></div>')
    disc = "일반 정보 · 특정 상품 권유가 아닙니다" if t in ("cover", "last") else spec.get("disclaimer", "")
    foot = f'<div class="foot"><span>{html.escape(disc)}</span><span class="brand">키움멘토 · 재무설계</span></div>'
    if t == "cover":
        rows = ""
        for k, q in enumerate(c["preview"][:4]):
            cls = ""
            rows += (f'<div class="r {cls}"><div class="n">{k+1:02d}</div><div>{html.escape(q)}</div>'
                     '<div><i class="box"></i></div><div><i class="box"></i></div></div>')
        body = (f'<div class="rule"></div><div class="title">{fmt(c["title"])}</div><div class="sub">{fmt(c["sub"])}</div>'
                f'<div class="prev"><div class="h"><div>#</div><div>점검 항목</div><div>예</div><div>모름</div></div>{rows}</div>'
                f'<div class="save">{html.escape(c.get("save", "저장해 두고 하나씩 체크해 보세요 →"))}</div>')
        cls = "cv"
    elif t == "checklist":
        rows = "".join(
            f'<div class="r"><div class="n">{k+1:02d}</div><div class="q">{fmt(r["q"])}'
            f'{"<small>" + fmt(r["sub"]) + "</small>" if r.get("sub") else ""}</div>'
            '<div class="c"><i class="box"></i></div><div class="c"><i class="box"></i></div></div>'
            for k, r in enumerate(c["rows"]))
        body = (f'<div class="t2">{fmt(c["title"])}</div><div class="tbl"><div class="h"><div></div><div>점검 항목</div>'
                f'<div class="c">예</div><div class="c">모름</div></div>{rows}</div>{CIRCLE}'
                f'<div class="judge">{fmt(c["judge"])}</div>')
        cls = "ck"
    elif t == "steps":
        rows = "".join(f'<div class="r"><div><span class="tag">{html.escape(r["no"])}</span></div>'
                       f'<div class="q">{fmt(r["do"])}</div></div>' for r in c["rows"])
        body = f'<div class="t2">{fmt(c["title"])}</div><div class="tbl">{rows}</div>'
        cls = "st"
    elif t == "sheet":
        hd = "".join(f"<div>{html.escape(x)}</div>" for x in c["cols"])
        def srow(x):  # 문자열이면 첫 칸만(빈 양식), 리스트면 칸을 채운 표
            cells = x if isinstance(x, list) else [x] + [""] * (len(c["cols"]) - 1)
            return '<div class="r">' + "".join(f"<div>{fmt(v)}</div>" for v in cells) + "</div>"
        rows = "".join(srow(x) for x in c["rows"])
        body = (f'<div class="t2">{fmt(c["title"])}</div><div class="tbl{" dense" if c.get("dense") else ""}"><div class="h">{hd}</div>{rows}</div>'
                f'<div class="note">{fmt(c["note"]).replace("<span class=\"hl\">", "<b>").replace("</span>", "</b>")}</div>')
        cls = "sh"
    elif t == "why":
        body = (f'<div class="kick">{fmt(c["kicker"])}</div><div class="big">{fmt(c["big"])}</div>'
                f'<div class="body">{fmt(c["body"])}</div>')
        cls = "wy"
    elif t == "last":
        body = (f'<div class="title">{fmt(c["title"])}</div><div class="body">{fmt(c["body"])}</div>'
                f'<div class="q">{fmt(c["question"])}</div>')
        cls = "ls"
    else:
        raise SystemExit(f"알 수 없는 카드 종류: {t}")
    return f'<section class="card {cls}" id="c{i}">{head}{body}{foot}</section>'


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
    n = len(spec["cards"])
    page = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>' + CSS.replace("%(f)s", FONT_DIR.as_uri())
            + "</style></head><body>" + "".join(card(spec, c, i + 1, n) for i, c in enumerate(spec["cards"]))
            + "</body></html>")
    src = out / "_cards.html"
    src.write_text(page, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        pg.goto(src.as_uri())
        pg.evaluate("document.fonts.ready")
        for i in range(1, n + 1):
            pg.locator(f"#c{i}").screenshot(path=str(out / f"card_{i}.png"))
        b.close()
    src.unlink()
    from PIL import Image
    cols = 3
    rows = (n + cols - 1) // cols
    w, h, g = 540, 675, 20
    sheet = Image.new("RGB", (cols * w + (cols + 1) * g, rows * h + (rows + 1) * g), "#D9DCD6")
    for i in range(n):
        im = Image.open(out / f"card_{i+1}.png").resize((w, h))
        sheet.paste(im, (g + (i % cols) * (w + g), g + (i // cols) * (h + g)))
    sheet.save(out / "preview.png")
    print(f"{n}장 → {out}")


if __name__ == "__main__":
    main()
