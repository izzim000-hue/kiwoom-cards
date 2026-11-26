"""「후기 한 문장에서 멈췄어요」 후기 소개 릴스 (무음 시안).
render.py 의 사진·보드 부품을 재사용한다.
사용: python3 render_review.py 출력.mp4 | 표지.png --cover
"""
import sys, os, json, subprocess
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R

W, H, FPS = R.W, R.H, R.FPS
R.TOP = '받은 후기를 읽다가'
# 공정위 추천·보증 지침: 대가 관계 표시(모든 프레임 고정)
DISCLOSURE = '소정의 대가를 드리고 받은 후기를, 작성자 동의를 받아 소개합니다'

# ── 데이터 블록 ── (모드, 위 작은 줄, 큰 글씨, 아래 메모, 인용문, 길이)
SCENES = [
    ('photo', '', ['후기 한 문장에서', '==오래 멈췄어요=='], '', None, None, 5.0),
    ('quote', '', [], '', ['제가 처한 상황과', '기존 경험을', '먼저 충분히', '이해해 주셨어요'], 'text1', 5.4),
    ('plain', '', ['상품 설명보다', '==제 상황을 먼저==', '이해해 줬다는 거예요'], '', None, 'roadmap', 5.2),
    ('quote', '', [], '', ['보험에 익숙하지 않은', '제 눈높이에 맞춰', '설명해 주셨고'], 'text2', 5.0),
    ('board', '', ['일곱 칸을 펼쳐도', '==어느 칸부터==는', '그 사람 이야기가 정해요'], '그래서 저는 상품보다 이야기를 먼저 들어요', None, None, 5.6),
    ('plain', '저도 다시 묻게 됐어요', ['내 돈 이야기,', '==먼저 들어 준 사람==', '있었나요?'], '', None, 'table', 5.2),
]

# 후기 사진(작성자 블로그 캡처) — 이름은 흐림
def review_img(key):
    from PIL import ImageFilter
    H_ = os.path.dirname(os.path.abspath(__file__))
    if key == 'roadmap':
        im = Image.open(os.path.join(H_, 'review_roadmap.jpg')).convert('RGB').crop((53, 0, 1028, 722))
        b = (420, 50, 680, 170)
        im.paste(im.crop(b).filter(ImageFilter.GaussianBlur(14)), b[:2])
        return im
    if key == 'table':
        return Image.open(os.path.join(H_, 'review_table.jpg')).convert('RGB').crop((0, 20, 1080, 818))
    im = Image.open(os.path.join(H_, 'review_text.jpg')).convert('RGB')
    if key == 'text1':
        return im.crop((150, 380, 4200, 930))
    return im.crop((150, 1310, 4200, 1830))


def place_img(L, im, y0, y1, tag):
    maxw, maxh = W - 120, y1 - y0
    s = min(maxw / im.width, maxh / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    x = (W - im.width) // 2
    y = y0 + (maxh - im.height) // 2
    d = ImageDraw.Draw(L)
    d.rounded_rectangle((x - 10, y - 10, x + im.width + 10, y + im.height + 10), radius=18, fill=(255, 255, 255, 255))
    L.paste(im, (x, y))
    f = R.fBo(28)
    tw = d.textlength(tag, font=f)
    d.rounded_rectangle((x - 10, y - 72, x + tw + 20, y - 22), radius=10, fill=R.GREEN + (235,))
    d.text((x + 5, y - 47), tag, font=f, fill=(255, 255, 255), anchor='lm')
    return L


TAGS = {'text1': '후기 원문', 'text2': '후기 원문', 'roadmap': '그분 상황에 맞춘 로드맵 화면', 'table': '그분 기준으로 함께 세운 목표·비율'}


def disclosure_layer():
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    f = R.fBo(28)
    tw = d.textlength(DISCLOSURE, font=f)
    d.rounded_rectangle(((W - tw) / 2 - 22, 1790, (W + tw) / 2 + 22, 1846), radius=14, fill=(0, 0, 0, 120))
    d.text((W / 2, 1818), DISCLOSURE, font=f, fill=(235, 235, 235), anchor='mm')
    return L


def quote_layer(lines, top=300):
    L = R.text_layer('', [], '')  # 상단 제목 pill 만
    d = ImageDraw.Draw(L)
    n = len(lines)
    bottom = top + 170 + n * 96 + 120
    d.rounded_rectangle((90, top, W - 90, bottom), radius=30, fill=R.IVORY + (245,))
    d.text((150, top + 30), '“', font=R.fB(150), fill=R.GREEN + (255,))
    y = top + 190
    for ln in lines:
        d.text((W / 2, y), ln, font=R.fB(64), fill=R.GREEN + (255,), anchor='mm')
        y += 96
    d.text((W - 150, bottom - 60), '— 블로그 후기 중', font=R.fBo(32), fill=(110, 118, 112), anchor='rm')
    return L


def build_layer(mode, sub, big, note, quote, img):
    if mode == 'quote':
        card_h = 170 + len(quote) * 96 + 120
        im = review_img(img) if img else None
        ih = int(im.height * (W - 120) / im.width) + 20 if im else 0
        top = int(280 + (1760 - 280 - card_h - 110 - ih) / 2)
        L = quote_layer(quote, top)
        if im:
            y0 = top + card_h + 110
            L = place_img(L, im, y0, y0 + ih, TAGS[img])
        return L
    L = R.text_layer(sub, big, note)
    if img:
        L = place_img(L, review_img(img), 840, 1750, TAGS[img])
    return L


def frame(bg, photo, mode, L, t, dur, D, full=False):
    if mode in ('photo', 'board'):
        fr = R.frame(bg, photo, mode, L, t, dur, full=full).convert('RGBA')
    else:
        k = t / dur
        z = 1.0 + 0.06 * k
        bw, bh = bg.size
        cw, ch = int(W * 1.1 / z), int(H * 1.1 / z)
        cx, cy = (bw - cw) // 2, (bh - ch) // 2
        fr = bg.crop((cx, cy, cx + cw, cy + ch)).resize((W, H), Image.BILINEAR).convert('RGBA')
        a = 1.0 if full else R.ease(t / 0.6)
        LL = L
        if a < 1:
            LL = L.copy()
            LL.putalpha(LL.split()[3].point(lambda v: int(v * a)))
            tmp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            tmp.paste(LL, (0, int(30 * (1 - a))))
            LL = tmp
        fr = Image.alpha_composite(fr, LL)
    return Image.alpha_composite(fr, D).convert('RGB')


def main():
    out = sys.argv[1]
    photo = R.screen_photo()
    bg = R.background(photo)
    D = disclosure_layer()
    DUR = json.load(open(os.environ['DURS'])) if os.environ.get('DURS') else None
    scenes = []
    for i, (mode, sub, big, note, quote, img, dur) in enumerate(SCENES):
        L = build_layer(mode, sub, big, note, quote, img)
        scenes.append((mode, L, DUR[i] if DUR else dur))
    if '--cover' in sys.argv:
        frame(bg, photo, 'quote', scenes[1][1], 0, 5, D, full=True).save(out)
        return
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'png', '-framerate', str(FPS),
                           '-i', '-', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-shortest', '-c:v', 'libx264',
                           '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart',
                           out], stdin=subprocess.PIPE)
    prev = None
    for si, (mode, L, dur) in enumerate(scenes):
        n = int(dur * FPS)
        for i in range(n):
            fr = frame(bg, photo, mode, L, i / FPS, dur, D)
            if si > 0 and i < 9 and prev is not None:
                fr = Image.blend(prev, fr, (i + 1) / 10)
            if i == n - 1:
                prev = fr
            fr.save(ff.stdin, 'PNG', compress_level=1)
    ff.stdin.close()
    ff.wait()


if __name__ == '__main__':
    main()
