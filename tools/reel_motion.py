"""키움멘토 모션 릴스 생성기 (1080x1920, 30fps, 무음 트랙). 딥그린 바탕 + 큰 숫자 카운트업 + 막대 애니메이션.
사용: python3 tools/reel_motion.py spec.json 출력.mp4
장면 type:
  hero  {"tag","lines":[..],"count":{"from","to","unit"},"note"}   숫자가 0.8초 동안 올라감
  steps {"tag","title","items":[{"label","value"}],"note"}          막대가 차례로 자람(값은 만 원 단위 숫자)
  bars  {"tag","title","items":[{"label","sub","value","risk"}],"note"}
  list  {"tag","title","items":[{"left","right"}],"note"}
  text  {"tag","lines":[..],"note"}
  cta   {"tag","lines":[..],"keyword","note"}
공통: "dur"(초). 문구 안 <g>..</g> = 금색. spec 최상단 "basis" = 하단 고정 문구.
"""
import json, sys, subprocess, tempfile
from playwright.sync_api import sync_playwright
FPS = 30
PAGE = r"""<html><head><style>
*{box-sizing:border-box;margin:0}
body{width:1080px;height:1920px;background:#2F4F3E;font-family:'Noto Sans CJK KR',sans-serif;color:#fff;overflow:hidden}
.sc{position:absolute;inset:0;padding:0 90px;display:flex;flex-direction:column;justify-content:center;gap:44px;opacity:0}
.tag{align-self:flex-start;background:#B08D46;color:#1F3529;font-size:44px;font-weight:900;padding:14px 30px;border-radius:14px}
.big{font-size:104px;font-weight:900;line-height:1.22;letter-spacing:-.035em}
.g{color:#E2C27A}
.num{font-size:190px;font-weight:900;letter-spacing:-.04em;color:#E2C27A;line-height:1}
.unit{font-size:90px}
.note{font-size:40px;color:#B9CDBF;font-weight:700}
.title{font-size:78px;font-weight:900;line-height:1.25;letter-spacing:-.03em}
.row{display:flex;flex-direction:column;gap:12px}
.lab{display:flex;justify-content:space-between;align-items:baseline;font-size:50px;font-weight:900}
.lab small{font-size:36px;color:#B9CDBF;font-weight:700;margin-left:14px}
.val{color:#E2C27A;font-size:64px}
.track{height:64px;background:rgba(255,255,255,.1);border-radius:12px;overflow:hidden}
.bar{height:100%;width:0;background:linear-gradient(90deg,#8FB59B,#E2C27A);border-radius:12px}
.risk{font-size:34px;color:#B9CDBF;font-weight:700}
.li{display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,.08);border-left:12px solid #E2C27A;padding:30px 36px;border-radius:14px;font-size:52px;font-weight:900}
.li span:last-child{color:#E2C27A}
.kw{align-self:flex-start;font-size:150px;font-weight:900;color:#1F3529;background:#E2C27A;padding:10px 46px;border-radius:24px;letter-spacing:-.03em}
.pg{position:absolute;left:0;top:0;height:16px;background:#E2C27A}
.foot{position:absolute;left:90px;right:90px;bottom:140px;display:flex;justify-content:space-between;gap:30px;font-size:30px;color:#B9CDBF;white-space:nowrap}
</style></head><body><div class="pg" id="pg"></div><div id="root"></div>
<div class="foot"><span id="basis"></span><b>@kiwoom.mentor</b></div>
<script>
const g=s=>s.replace(/<g>/g,'<span class="g">').replace(/<\/g>/g,'</span>');
const ease=x=>1-Math.pow(1-Math.min(Math.max(x,0),1),3);
const fmt=n=>Math.round(n).toLocaleString('ko-KR');
let S=[],T=0;
function build(spec){
  document.getElementById('basis').textContent=spec.basis||'';
  const root=document.getElementById('root');let t0=0;
  spec.scenes.forEach(sc=>{
    const d=document.createElement('div');d.className='sc';let h=sc.tag?`<div class="tag">${sc.tag}</div>`:'';
    if(sc.type==='hero'){h+=`<div class="big">${sc.lines.map(g).join('<br>')}</div><div class="num"><span class="cnt">0</span><span class="unit">${sc.count.unit}</span></div>`}
    else if(sc.type==='steps'||sc.type==='bars'){const mx=Math.max(...sc.items.map(i=>i.value));
      h+=`<div class="title">${g(sc.title)}</div>`+sc.items.map(i=>`<div class="row it"><div class="lab"><span>${i.label}${i.sub?`<small>${i.sub}</small>`:''}</span><span class="val"><span class="cnt" data-to="${i.value}">0</span>만</span></div><div class="track"><div class="bar" data-w="${i.value/mx*100}"></div></div>${i.risk?`<div class="risk">${i.risk}</div>`:''}</div>`).join('')}
    else if(sc.type==='list'){h+=`<div class="title">${g(sc.title)}</div>`+sc.items.map(i=>`<div class="li it"><span>${i.left}</span><span>${i.right}</span></div>`).join('')}
    else{h+=`<div class="big">${sc.lines.map(g).join('<br>')}</div>`+(sc.keyword?`<div class="kw">${sc.keyword}</div>`:'')}
    if(sc.note)h+=`<div class="note">${g(sc.note)}</div>`;
    d.innerHTML=h;root.appendChild(d);S.push({el:d,sc,t0,t1:t0+sc.dur});t0+=sc.dur});
  T=t0;
}
function setT(t){
  document.getElementById('pg').style.width=(t/T*100)+'%';
  S.forEach(s=>{const on=t>=s.t0&&t<s.t1;s.el.style.opacity=on?1:0;if(!on)return;const lt=t-s.t0;
    const enter=ease(lt/0.25);s.el.style.transform=`translateY(${(1-enter)*40}px)`;
    if(s.sc.type==='hero'){const c=s.sc.count;s.el.querySelector('.cnt').textContent=fmt(c.from+(c.to-c.from)*ease(lt/0.8))}
    s.el.querySelectorAll('.it').forEach((it,i)=>{const p=ease((lt-0.2-i*0.45)/0.7);it.style.opacity=p>0?1:0.15;
      const b=it.querySelector('.bar');if(b)b.style.width=(b.dataset.w*p)+'%';
      const c=it.querySelector('.cnt');if(c)c.textContent=fmt(c.dataset.to*p)});
    const kw=s.el.querySelector('.kw');if(kw){const p=ease((lt-0.3)/0.4);kw.style.transform=`scale(${0.7+0.3*p})`;kw.style.opacity=p}});
}
</script></body></html>"""

def main(spec_path, out):
    spec = json.load(open(spec_path, encoding="utf-8"))
    total = sum(s["dur"] for s in spec["scenes"]); d = tempfile.mkdtemp()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.set_content(PAGE); pg.evaluate("s=>build(s)", spec); pg.wait_for_timeout(300)
        for n in range(int(total * FPS)):
            pg.evaluate("t=>setT(t)", n / FPS); pg.screenshot(path=f"{d}/f{n:04d}.png")
        b.close()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", f"{d}/f%04d.png", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "-t", f"{total:.2f}", "-movflags", "+faststart", out], check=True)
    print(f"duration={total:.1f}s cover_ms=1000")

if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
