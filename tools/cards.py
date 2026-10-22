"""키움멘토 카드뉴스 생성기 (1080x1350, 4:5) · 네이비 기본
사용: python3 tools/cards.py spec.json 출력폴더
spec.json 예시:
{"series": "돈 공부, 이제 시작",
 "foot": "예시(가정) · 일반 정보",
 "cards": [
   {"type": "hero", "kicker": "월 50만 원으로 1억", "big": "5년 7개월", "lines": ["같은 돈인데", "이만큼 먼저 도착합니다"]},
   {"title": "집 있는데<br>왜 늘 빠듯할까?", "lines": ["...", "..."], "emph": ["..."], "note": ""},
   {"type": "bars", "title": "...", "bars": [{"label": "모으기만", "value": 200, "text": "16년 8개월"}, ...], "lines": [...]},
   {"type": "list", "title": "...", "items": ["...", "..."]},
   {"type": "cta", "title": "...", "keyword": "1억", "gift": "「목표 금액 계산기」", "lines": [...]}
 ]}
type 생략 시 기본 텍스트 카드. 마지막 장 "foot"은 법적 최소 고지 한 줄.
"""
import json, sys, os
from playwright.sync_api import sync_playwright
NAVY="#1E2A44"; GOLD="#E8B04B"; CREAM="#F5EFE3"; MUT="#A9B2C3"; LINE="#33405E"; DG="#2F4F3E"
FONT="word-break:keep-all;font-family:'Noto Sans CJK KR',sans-serif"
def sprout(s=30): return f'<svg width="{s}" height="{s}" viewBox="0 0 64 64"><path d="M32 58V30" stroke="{CREAM}" stroke-width="5" stroke-linecap="round"/><path d="M32 34C32 22 22 14 8 14c0 13 10 20 24 20z" fill="{CREAM}"/><path d="M32 28c0-10 9-17 22-17 0 12-9 18-22 17z" fill="{CREAM}" opacity=".75"/></svg>'
def logo(series): return f'<div style="display:flex;align-items:center;gap:16px"><span style="width:52px;height:52px;border-radius:50%;background:{DG};display:flex;align-items:center;justify-content:center">{sprout()}</span><span style="font-size:32px;font-weight:700;color:{CREAM};opacity:.9">{series}</span></div>'
def lines(c, size=52):
    em=set(c.get("emph",[]))
    return "".join(f'<div style="font-size:{size+12 if l in em else size}px;font-weight:{900 if l in em else 500};color:{GOLD if l in em else CREAM};line-height:1.38">{l}</div>' for l in c.get("lines",[]))
def title(t, size=96): return f'<div style="font-size:{size}px;font-weight:900;line-height:1.18;letter-spacing:-.03em;color:{CREAM}">{t}</div>'
BAR=f'<div style="width:120px;height:8px;background:{GOLD}"></div>'
def body(c):
    t=c.get("type","text")
    if t=="hero":
        return f'''<div style="margin-top:110px;font-size:62px;font-weight:700;color:{CREAM}">{c.get("kicker","")}</div>
<div style="font-size:{c.get("bigsize",230)}px;font-weight:900;line-height:1;letter-spacing:-.05em;color:{GOLD};white-space:nowrap">{c["big"]}</div>
{BAR}<div style="display:flex;flex-direction:column;gap:14px">{lines(c,60)}</div>'''
    if t=="bars":
        mx=max(b["value"] for b in c["bars"])
        rows="".join(f'''<div style="display:flex;flex-direction:column;gap:12px">
<div style="display:flex;justify-content:space-between;font-size:40px;color:{CREAM}"><span style="font-weight:600">{b["label"]}</span><span style="font-weight:900;color:{GOLD if b.get("hi") else CREAM}">{b["text"]}</span></div>
<div style="height:44px;width:{b["value"]/mx*100:.1f}%;background:{GOLD if b.get("hi") else MUT};border-radius:6px;opacity:{1 if b.get("hi") else .55}"></div></div>''' for b in c["bars"])
        return f'''<div style="margin-top:40px">{title(c["title"],84)}</div>{BAR}
<div style="display:flex;flex-direction:column;gap:34px">{rows}</div>
<div style="display:flex;flex-direction:column;gap:8px">{lines(c,44)}</div>'''
    if t=="list":
        items="".join(f'''<div style="display:flex;gap:30px;align-items:flex-start"><span style="flex:none;width:76px;height:76px;border-radius:50%;background:{GOLD};color:{NAVY};font-size:44px;font-weight:900;display:flex;align-items:center;justify-content:center">{i}</span>
<span style="font-size:50px;font-weight:600;color:{CREAM};line-height:1.35;padding-top:6px">{it}</span></div>''' for i,it in enumerate(c["items"],1))
        return f'''<div style="margin-top:60px">{title(c["title"],90)}</div>{BAR}
<div style="display:flex;flex-direction:column;gap:44px">{items}</div>
<div style="display:flex;flex-direction:column;gap:8px">{lines(c,44)}</div>'''
    if t=="cta":
        return f'''<div style="margin-top:60px">{title(c["title"],90)}</div>{BAR}
<div style="border:4px solid {GOLD};border-radius:28px;padding:48px 44px;display:flex;flex-direction:column;gap:22px">
<div style="font-size:46px;font-weight:600;color:{CREAM}">♥ 누르고 팔로우</div>
<div style="font-size:64px;font-weight:900;color:{CREAM}">댓글에 <span style="color:{NAVY};background:{GOLD};padding:0 22px;border-radius:12px">{c["keyword"]}</span> 남기면</div>
<div style="font-size:50px;font-weight:700;color:{GOLD}">{c["gift"]}</div><div style="font-size:46px;font-weight:600;color:{CREAM}">DM으로 보내드려요</div></div>
<div style="display:flex;flex-direction:column;gap:8px">{lines(c,40)}</div>'''
    return f'''<div style="margin-top:80px">{title(c["title"])}</div>{BAR}<div style="display:flex;flex-direction:column;gap:26px">{lines(c)}</div>'''
def card(s,c,n,total):
    foot=c.get("note", s.get("foot","") if n==total else "")
    return f'''<div style="width:1080px;height:1350px;background:{NAVY};padding:100px 92px 80px;display:flex;flex-direction:column;gap:50px;box-sizing:border-box;{FONT}">
{logo(s["series"])}{body(c)}
<div style="margin-top:auto;display:flex;justify-content:space-between;align-items:flex-end;gap:30px;font-size:26px;color:{MUT}"><span>{foot}</span><span style="flex:none;font-weight:700">키움멘토 {n}/{total}</span></div></div>'''
def main(spec,out):
    s=json.load(open(spec,encoding="utf-8")); os.makedirs(out,exist_ok=True); cs=s["cards"]
    with sync_playwright() as pw:
        b=pw.chromium.launch(); pg=b.new_page(viewport={"width":1080,"height":1350})
        for i,c in enumerate(cs,1):
            pg.set_content("<body style='margin:0'>"+card(s,c,i,len(cs))+"</body>"); pg.wait_for_timeout(150)
            if pg.evaluate("()=>{const e=document.body.firstElementChild;return e.scrollHeight>e.clientHeight||e.scrollWidth>e.clientWidth}"): print("OVERFLOW", i)
            pg.screenshot(path=f"{out}/insta_{i}.png")
        b.close()
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
