"""후기 소개 릴스 — 프로 톤(진한 딥그린 바탕·아이보리·금색) 버전. 협찬 표시는 인용 장면의 작은 태그로만.
사용: python3 render_editorial.py 출력.mp4 | 표지.png --cover | 미리보기.png --preview
"""
import sys, os, json, subprocess
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
import render_review as V

W, H, FPS = 1080, 1920, 30
F = '/home/user/kiwoom-cards/tools/fonts/'
from PIL import ImageFont
sans = lambda s, w='Bold': ImageFont.truetype(F + f'NotoSansKR-{w}.otf', s)
serif = lambda s, w='SemiBold': ImageFont.truetype(F + f'NotoSerifKR-{w}.otf', s)

PAPER = (246, 243, 236)
INK = (31, 42, 36)
GREEN = (205, 172, 104)      # 강조 = 금색
INK = (243, 239, 230)        # 아이보리 글씨
SAGE = None
MUTED = (160, 176, 166)
GOLD = (205, 172, 104)
LINE = (70, 96, 82)
BOX = (31, 54, 43)
BOXON = (44, 72, 57)
X0 = 90
LABEL = '받은 후기를 읽다가'
DISCLOSURE = V.DISCLOSURE

# ── 데이터 블록 ── (모드, 큰 글씨 줄들(==강조==), 인용문, 사진 키, 사진 설명, 길이)
SCENES = [
    ('text', ['후기 한 문장에서', '==오래 멈췄어요=='], None, 'screen', '제가 쓰는 일곱 칸 화면', 5.0),
    ('quote', [], ['제가 처한 상황과', '기존 경험을 먼저', '충분히 이해해 주셨어요'], 'text1', '후기 원문', 5.4),
    ('text', ['상품 설명보다', '==제 상황을 먼저==', '이해해 줬다는 거예요'], None, 'roadmap', '그분 상황에 맞춘 로드맵 화면 · 이름 가림', 5.2),
    ('quote', [], ['보험에 익숙하지 않은', '제 눈높이에 맞춰', '설명해 주셨고'], 'text2', '후기 원문', 5.0),
    ('board', ['일곱 칸은 같아도', '==어느 칸부터==는', '그 사람 이야기가 정해요'], None, None, '그래서 저는 상품보다 이야기를 먼저 들어요', 5.6),
    ('text', ['내 돈 이야기,', '==먼저 들어 준 사람==', '있었나요?'], None, 'table', '그분 기준으로 함께 세운 목표·비율', 5.2),
]


def get_img(key):
    if key == 'screen':
        return R.screen_photo()
    return V.review_img(key)


_BG = None


def background():
    global _BG
    if _BG is None:
        import numpy as np
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W * 0.3) / W) ** 2 + ((yy - H * 0.25) / H) ** 2)
        t = np.clip(r / 1.0, 0, 1)[..., None]
        c0, c1 = np.array([34, 60, 47]), np.array([14, 27, 21])
        arr = (c0 * (1 - t) + c1 * t)
        arr += np.random.default_rng(1).normal(0, 2.2, arr.shape)
        _BG = Image.fromarray(np.clip(arr, 0, 255).astype('uint8')).convert('RGBA')
    return _BG.copy()


def chrome():
    L = background()
    d = ImageDraw.Draw(L)
    d.line((X0, 170, X0 + 46, 170), fill=GREEN, width=4)
    d.text((X0 + 62, 170), LABEL, font=sans(34), fill=GREEN, anchor='lm')
    d.text((W - X0, 170), '키움멘토', font=sans(30, 'Regular'), fill=MUTED, anchor='rm')
    return L


def big_text(d, lines, y, size=78):
    f = sans(size)
    lh = int(size * 1.38)
    for line in lines:
        x = X0
        for part, hl in V.parse(line) if False else [(p, i % 2 == 1) for i, p in enumerate(line.split('==')) if p]:
            w = d.textlength(part, font=f)
            d.text((x, y), part, font=f, fill=GREEN if hl else INK)
            x += w
        y += lh
    return y


def photo_card(L, im, y0, y1, caption):
    maxw, maxh = W - 120, y1 - y0 - 60
    s = min(maxw / im.width, maxh / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    x = (W - im.width) // 2
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((x + 6, y0 + 12, x + im.width + 6, y0 + im.height + 12), fill=(0, 0, 0, 140))
    L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    L.paste(im, (x, y0))
    d = ImageDraw.Draw(L)
    d.rectangle((x - 1, y0 - 1, x + im.width + 1, y0 + im.height + 1), outline=GOLD, width=2)
    d.text((x, y0 + im.height + 26), caption, font=sans(28, 'Regular'), fill=MUTED)
    return L


def layer(mode, big, quote, key, cap):
    C = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    content(C, mode, big, quote, key, cap)
    top, bot = C.getbbox()[1], C.getbbox()[3]
    off = int(290 + (1640 - 290 - (bot - top)) / 2) - top
    OFFS[id(big)] = off
    L = chrome()
    L.alpha_composite(C, (0, off) if off >= 0 else (0, 0))
    return L


OFFS = {}


def content(L, mode, big, quote, key, cap):
    d = ImageDraw.Draw(L)
    if mode == 'quote':
        y = 100
        d.text((X0 - 6, y - 40), '“', font=serif(180, 'Bold'), fill=GOLD)
        y += 150
        f = sans(26)
        tw = d.textlength('협찬 후기', font=f)
        d.rounded_rectangle((W - X0 - tw - 36, y - 110, W - X0, y - 64), radius=23, outline=GOLD, width=2)
        d.text((W - X0 - 18 - tw / 2, y - 87), '협찬 후기', font=f, fill=GOLD, anchor='mm')
        d.line((X0, y, X0, y + len(quote) * 110 - 20), fill=GOLD, width=4)
        for ln in quote:
            d.text((X0 + 34, y), ln, font=serif(72), fill=INK)
            y += 110
        y += 70
        if key:
            photo_card(L, get_img(key), y, y + 600, cap)
        return L
    y = big_text(d, big, 100)
    if mode == 'board':
        draw_board(d, y + 40, cap)
    elif key:
        photo_card(L, get_img(key), y + 70, y + 70 + 900, cap)
    return L


def draw_board(d, y0, note, hl=None):
    bw, bh, gap = (W - 2 * X0 - 24) // 2, 150, 20
    for i, (num, name, l1, l2) in enumerate(R.AREAS):
        if i == 6:
            x, y = X0, y0 + 3 * (bh + gap)
            w = W - 2 * X0
        else:
            x, y, w = X0 + (i % 2) * (bw + 24), y0 + (i // 2) * (bh + gap), bw
        on = hl == i
        d.rectangle((x, y, x + w, y + bh), fill=BOXON if on else BOX, outline=GOLD if on else LINE, width=2)
        d.text((x + 26, y + 22), num, font=sans(26), fill=GOLD)
        d.text((x + 72, y + 14), name, font=sans(36), fill=INK)
        d.text((x + 26, y + 80), f'{l1} {l2}', font=sans(26, 'Regular'), fill=MUTED)
    d.text((X0, y0 + 4 * (bh + gap) + 30), note, font=sans(34), fill=INK)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def frame(L, mode, big, t, dur, full=False):
    fr = L
    if mode == 'board':
        cur = int(t / 0.6) % 7
        fr = L.copy()
        d = ImageDraw.Draw(fr)
        y = 100 + len(big) * int(78 * 1.38) + OFFS[id(big)]
        draw_board(d, y + 40, '', hl=cur)
        # 메모 줄은 레이어에 이미 있음
    a = 1.0 if full else ease(t / 0.7)
    if a >= 1:
        return fr.convert('RGB')
    base = background()
    tmp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    tmp.paste(fr, (0, int(24 * (1 - a))))
    return Image.blend(base, Image.alpha_composite(base, tmp), a).convert('RGB')


def main():
    out = sys.argv[1]
    DUR = json.load(open(os.environ['DURS'])) if os.environ.get('DURS') else None
    sc = [(m, b, layer(m, b, q, k, c), DUR[i] if DUR else d) for i, (m, b, q, k, c, d) in enumerate(SCENES)]
    if '--preview' in sys.argv:
        s = Image.new('RGB', (360 * len(sc), 640))
        for i, (m, b, L, d) in enumerate(sc):
            s.paste(frame(L, m, b, d - 0.3, d).resize((360, 640)), (360 * i, 0))
        s.save(out)
        return
    if '--cover' in sys.argv:
        frame(sc[1][2], 'quote', [], 0, 5, full=True).save(out)
        return
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'png', '-framerate', str(FPS),
                           '-i', '-', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-shortest', '-c:v', 'libx264',
                           '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart',
                           out], stdin=subprocess.PIPE)
    for m, b, L, d in sc:
        for i in range(int(d * FPS)):
            frame(L, m, b, i / FPS, d).save(ff.stdin, 'PNG', compress_level=1)
    ff.stdin.close()
    ff.wait()


if __name__ == '__main__':
    main()
