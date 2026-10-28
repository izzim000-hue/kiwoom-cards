"""프레임 마크업. legacy 는 게시된 MP4 10편을 재현하는 배치다 (D-05)."""
from .constants import SAGE, DG, GOLD, MUT, ACCOUNT


def legacy_inner_html(top, lines, k, prog, basis):
    """기존 reel.py frame() 과 같은 마크업(<body> 래퍼 제외).

    바뀐 점 두 가지: 글꼴은 번들 'Noto Sans KR', <s> 는 블록 줄(display:block).
    top 과 basis 는 원문 그대로 삽입한다(기존 동작 유지, 허용 목록 검사는 spec 단계).
    """
    out = ""
    for i, l in enumerate(lines):
        l = (l.replace("<g>", f'<span style="color:{GOLD}">').replace("</g>", "</span>")
              .replace("<s>", f'<span style="display:block;font-size:52px;font-weight:700;color:{MUT}">')
              .replace("</s>", "</span>"))
        out += f'<div style="opacity:{1 if i < k else 0}">{l}</div>'
    return f'''<div style="width:1080px;height:1920px;background:{SAGE};display:flex;flex-direction:column;justify-content:center;padding:0 96px;gap:40px;font-family:'Noto Sans KR',sans-serif;box-sizing:border-box;position:relative">
<div style="position:absolute;left:0;top:0;height:14px;width:{prog*100:.1f}%;background:{DG}"></div>
<div style="font-size:50px;font-weight:700;color:{DG};min-height:60px">{top}</div>
<div style="font-size:100px;font-weight:900;line-height:1.3;letter-spacing:-.03em;color:{DG};display:flex;flex-direction:column">{out}</div>
<div style="position:absolute;left:96px;right:96px;bottom:150px;display:flex;justify-content:space-between;font-size:30px;color:{MUT}"><span>{basis}</span><b>{ACCOUNT}</b></div></div>'''


# Plan 03 에서 "new" 배치를 등록한다
LAYOUTS = {"legacy": legacy_inner_html}
