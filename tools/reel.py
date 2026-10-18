"""키움멘토 자막형 릴스 생성기 (1080x1920, 목소리 없음, 무음 오디오 트랙 포함)
사용: python3 tools/reel.py spec.json 출력.mp4
spec.json 예시:
{"basis": "단리 적금 예시 · 일반과세 15.4% 기준",
 "scenes": [
   {"top": "헷갈리는 돈 상식 #1", "lines": ["연 5% 적금", "월 100만 원, 1년", "<g>이자 60만 원?</g>"]},
   ...,
   {"top": "", "lines": ["저장해두고", "내 적금도 계산해 보세요", "<s>프로필 링크 · 1분 노후자금 계산기</s>"]}]}
<g>..</g> = 금색 강조, <s>..</s> = 작은 회색 글씨. 한 줄 0.85초씩 나타나고 장면 끝에서 1.9초 멈춤.
"""
import json, sys, subprocess, tempfile, os
from playwright.sync_api import sync_playwright
SAGE="#DEE9E0"; DG="#2F4F3E"; GOLD="#B08D46"; LINE=0.85; HOLD=1.9
def frame(top,lines,k,prog,basis):
    out=""
    for i,l in enumerate(lines):
        l=l.replace("<g>",f'<span style="color:{GOLD}">').replace("</g>","</span>").replace("<s>",'<span style="font-size:52px;font-weight:700;color:#5B6E62">').replace("</s>","</span>")
        out+=f'<div style="opacity:{1 if i<k else 0}">{l}</div>'
    return f'''<body style="margin:0"><div style="width:1080px;height:1920px;background:{SAGE};display:flex;flex-direction:column;justify-content:center;padding:0 96px;gap:40px;font-family:'Noto Sans CJK KR',sans-serif;box-sizing:border-box;position:relative">
<div style="position:absolute;left:0;top:0;height:14px;width:{prog*100:.1f}%;background:{DG}"></div>
<div style="font-size:50px;font-weight:700;color:{DG};min-height:60px">{top}</div>
<div style="font-size:100px;font-weight:900;line-height:1.3;letter-spacing:-.03em;color:{DG};display:flex;flex-direction:column">{out}</div>
<div style="position:absolute;left:96px;right:96px;bottom:150px;display:flex;justify-content:space-between;font-size:30px;color:#5B6E62"><span>{basis}</span><b>@kiwoom.mentor</b></div></div></body>'''
def main(spec,out):
    s=json.load(open(spec,encoding="utf-8")); seq=[]
    for sc in s["scenes"]:
        for k in range(1,len(sc["lines"])+1): seq.append((sc["top"],sc["lines"],k,LINE if k<len(sc["lines"]) else HOLD))
    total=sum(x[3] for x in seq); t=0; d=tempfile.mkdtemp(); files=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch(); pg=b.new_page(viewport={"width":1080,"height":1920})
        for n,(top,lines,k,dur) in enumerate(seq):
            t+=dur; pg.set_content(frame(top,lines,k,t/total,s.get("basis",""))); pg.wait_for_timeout(60)
            f=f"{d}/v{n:03d}.png"; pg.screenshot(path=f); files.append((f,dur))
        b.close()
    open(f"{d}/seq.txt","w").write("".join(f"file '{f}'\nduration {du}\n" for f,du in files)+f"file '{files[-1][0]}'\n")
    subprocess.run(["ffmpeg","-loglevel","error","-y","-f","concat","-safe","0","-i",f"{d}/seq.txt","-f","lavfi","-i","anullsrc=r=44100:cl=stereo",
      "-vf","fps=30,format=yuv420p","-c:v","libx264","-crf","20","-c:a","aac","-shortest","-t",f"{total:.2f}","-movflags","+faststart",out],check=True)
    first=len(s["scenes"][0]["lines"]); print(f"duration={total:.1f}s cover_ms={int((LINE*(first-1)+0.4)*1000)}")
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
