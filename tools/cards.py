"""키움멘토 카드뉴스 생성기 (1080x1350, 4:5)
사용: python3 tools/cards.py spec.json 출력폴더
spec.json 예시:
{"series": "돈의 구조 설계 #2",
 "cards": [
   {"title": "집 있는데<br>왜 늘 빠듯할까?", "lines": ["우리 집 순자산,", "계산해본 적 있으세요?", "10분이면 돈 지도가 나와요"],
    "emph": ["10분이면 돈 지도가 나와요"], "note": ""},
   ... 6장, 마지막 장은 "dark": true (한 톤 더 깊은 네이비) ]}
"""
import json, sys, os
from playwright.sync_api import sync_playwright
# 기본 팔레트(2026-10-22 확정): 딥 네이비 배경 · 골드 숫자/강조 · 크림 본문. CI 초록은 로고 표식에만.
NAVY="#1E2A44"; NAVY2="#16203A"; GOLD="#E8B04B"; CREAM="#F5EFE3"; MUT="#AEB7C8"; CI="#2F4F3E"
def logo(s=56): return f'<span style="display:inline-flex;width:{s+16}px;height:{s+16}px;border-radius:16px;background:{CREAM};align-items:center;justify-content:center">{sprout(CI,s-4)}</span>'
def sprout(c,s=56): return f'<svg width="{s}" height="{s}" viewBox="0 0 64 64"><path d="M32 58V30" stroke="{c}" stroke-width="4" stroke-linecap="round"/><path d="M32 34C32 22 22 14 8 14c0 13 10 20 24 20z" fill="{c}"/><path d="M32 28c0-10 9-17 22-17 0 12-9 18-22 17z" fill="{c}" opacity=".75"/></svg>'
def card(series,c,n,total):
    dark=c.get("dark",False); bg=NAVY2 if dark else NAVY; fg=CREAM; tc=CREAM
    em=set(c.get("emph",[]))
    body="".join(f'<div style="font-size:{68 if l in em else 54}px;font-weight:{900 if l in em else 500};color:{GOLD if l in em else fg};line-height:1.35">{l}</div>' for l in c["lines"])
    return f'''<div style="width:1080px;height:1350px;background:{bg};padding:110px 92px;display:flex;flex-direction:column;gap:56px;box-sizing:border-box;font-family:'Noto Sans CJK KR',sans-serif">
<div style="display:flex;align-items:center;gap:16px">{logo()}<span style="font-size:34px;font-weight:700;color:{tc}">{series}</span></div>
<div style="margin-top:90px;font-size:108px;font-weight:900;line-height:1.16;letter-spacing:-.03em;color:{tc}">{c["title"]}</div>
<div style="width:120px;height:8px;background:{GOLD}"></div>
<div style="display:flex;flex-direction:column;gap:30px">{body}</div>
<div style="margin-top:auto;display:flex;justify-content:space-between;font-size:28px;color:{MUT}"><span>{c.get("note","")}</span><span style="font-weight:700">키움멘토 {n}/{total}</span></div></div>'''
def main(spec,out):
    s=json.load(open(spec,encoding="utf-8")); os.makedirs(out,exist_ok=True); cs=s["cards"]
    with sync_playwright() as pw:
        b=pw.chromium.launch(); pg=b.new_page(viewport={"width":1080,"height":1350})
        for i,c in enumerate(cs,1):
            pg.set_content("<body style='margin:0'>"+card(s["series"],c,i,len(cs))+"</body>"); pg.wait_for_timeout(120)
            if pg.evaluate("()=>{const e=document.body.firstElementChild;return e.scrollHeight>e.clientHeight}"): print("OVERFLOW", i)
            pg.screenshot(path=f"{out}/insta_{i}.png")
        b.close()
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
