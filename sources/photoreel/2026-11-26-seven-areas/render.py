"""「재무 일곱 칸」 사진+보드 릴스 렌더 (Pillow → ffmpeg, 무음).
사용: python3 render.py 출력.mp4            # 영상
      python3 render.py 표지.png --cover      # 표지
      python3 render.py DM_일곱칸_점검표.png --dm  # DM 빈 점검표
DURS=durs.json 이 있으면 장면 길이를 녹음에 맞춤.
"""
import sys, os, json, math, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
F = '/home/user/kiwoom-cards/tools/fonts/'
fB = lambda s: ImageFont.truetype(F + 'NotoSansKR-Black.otf', s)
fBo = lambda s: ImageFont.truetype(F + 'NotoSansKR-Bold.otf', s)
fR = lambda s: ImageFont.truetype(F + 'NotoSansKR-Regular.otf', s)

GREEN = (47, 79, 62)
GOLD = (233, 196, 106)
IVORY = (250, 248, 242)
TOP = '돈 문제, 어디부터 볼까요'

# ── 데이터 블록: 화면 원문 그대로(사용자 지시: 일곱 칸은 누구나 같다) ──
AREAS = [
    ('01', '현금흐름', '새는 곳을 막고', '돈의 흐름 정리'),
    ('02', '위험대비', '아플 때도', '무너지지 않게'),
    ('03', '투자', '물가보다 빠르게', '자산 성장'),
    ('04', '절세', '줄일 수 있는', '세금은 줄이기'),
    ('05', '부동산', '내 집과 자산의', '균형 설계'),
    ('06', '노후', '월급 끊겨도', '들어올 돈 만들기'),
    ('07', '상속·증여', '가족에게 잘 넘기는', '방법까지 함께'),
]
# (모드, 위 작은 줄, 큰 글씨 줄들, 아래 메모, 길이)
SCENES = [
    ('photo', '저는 이 화면부터 띄워요', ['돈 문제가', '==다 엉켜 있는 것==', '같을 때'], '', 5.0),
    ('build', '', ['누구에게나', '==일곱 칸==이 있어요'], '', 5.4),
    ('board', '', ['칸은', '==누구나 똑같아요=='], '현금흐름부터 상속·증여까지', 4.8),
    ('cycle', '', ['다른 건', '==어느 칸부터== 보느냐예요'], '', 5.0),
    ('board', '', ['그래서 한 번에', '==다 풀려고== 하지 않아요'], '지금 가장 중요한 것부터 짚어 갑니다', 5.2),
    ('cycle', '저는 먼저 이렇게 물어요', ['지금 제일', '==신경 쓰이는 칸==,', '어디세요?'], '', 5.0),
    ('check', '내 일곱 칸, 한 번 채워 보고 싶다면', ['댓글에', '==[일곱칸]=='], '빈 일곱 칸 점검표를 보내 드릴게요', 5.2),
]


def screen_photo():
    im = Image.open(os.path.join(HERE, 'screen_src.jpg')).convert('RGB')
    im = im.crop((53, 30, 1028, 762))  # 블로그 글씨 아래쪽 제외, TV 화면만
    # 상단 '상담에서 함께 짚어보는 것들' 줄 흐림(‘상담’ 단어 노출 최소화)
    box = (70, 158, 330, 199)
    im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(9)), box[:2])
    return im


def background(photo):
    w, h = photo.size
    s = H / h
    b = photo.resize((int(w * s), H))
    bx = (b.width - W) // 2
    b = b.crop((bx, 0, bx + W, H)).filter(ImageFilter.GaussianBlur(38))
    b = Image.blend(b, Image.new('RGB', (W, H), (18, 32, 26)), 0.62)
    return b.resize((int(W * 1.1), int(H * 1.1)))


def parse(line):
    return [(p, i % 2 == 1) for i, p in enumerate(line.split('==')) if p]


def text_layer(sub, big, note):
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    ft = fBo(46)
    tw = d.textlength(TOP, font=ft)
    d.rounded_rectangle(((W - tw) / 2 - 34, 150, (W + tw) / 2 + 34, 240), radius=45, fill=GREEN + (235,))
    d.text((W / 2, 195), TOP, font=ft, fill=(255, 255, 255), anchor='mm')
    y = 470 - 58 * (len(big) - 2)
    if sub:
        d.text((W / 2, y - 105), sub, font=fBo(44), fill=(255, 236, 150), anchor='mm',
               stroke_width=6, stroke_fill=(20, 25, 22))
    fb = fB(86)
    for line in big:
        segs = parse(line)
        total = sum(d.textlength(t, font=fb) for t, _ in segs)
        x = (W - total) / 2
        for t, hl in segs:
            d.text((x, y), t, font=fb, fill=(255, 224, 90) if hl else (255, 255, 255), anchor='lm',
                   stroke_width=10, stroke_fill=(20, 25, 22))
            x += d.textlength(t, font=fb)
        y += 114
    if note:
        d.text((W / 2, 1700), note, font=fBo(40), fill=(255, 255, 255), anchor='mm',
               stroke_width=6, stroke_fill=(20, 25, 22))
    return L


# 보드 배치: 2열 4행(마지막 칸 가운데)
BX, BY, BW, BH, GAP = 70, 760, 455, 190, 30


def box_xy(i):
    if i == 6:
        return (W - BW) // 2, BY + 3 * (BH + GAP)
    return BX + (i % 2) * (BW + GAP), BY + (i // 2) * (BH + GAP)


def draw_box(d, i, alpha=1.0, hl=False, check=False, pop=1.0):
    num, name, l1, l2 = AREAS[i]
    x, y = box_xy(i)
    s = 0.85 + 0.15 * pop
    cx, cy = x + BW / 2, y + BH / 2
    x0, y0, x1, y1 = cx - BW * s / 2, cy - BH * s / 2, cx + BW * s / 2, cy + BH * s / 2
    a = int(255 * alpha)
    fill = GOLD + (a,) if hl else IVORY + (int(238 * alpha),)
    d.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=fill)
    if alpha < 0.5:
        return
    tc = GREEN + (a,)
    d.text((x0 + 28, y0 + 26), num, font=fBo(30), fill=tc)
    d.text((x0 + 78, y0 + 18), name, font=fB(40), fill=tc)
    d.text((x0 + 28, y0 + 88), l1, font=fBo(32), fill=(60, 70, 64, a))
    d.text((x0 + 28, y0 + 132), l2, font=fBo(32), fill=(60, 70, 64, a))
    if check:
        d.rounded_rectangle((x1 - 70, y0 + 22, x1 - 26, y0 + 66), radius=8, outline=GREEN + (a,), width=4)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def board_layer(mode, t):
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for i in range(7):
        if mode == 'build':
            p = ease((t - 0.5 - i * 0.45) / 0.35)
            if p <= 0:
                continue
            draw_box(d, i, alpha=p, pop=p)
        elif mode == 'cycle':
            cur = int(t / 0.55) % 7
            draw_box(d, i, hl=(i == cur))
        elif mode == 'check':
            draw_box(d, i, check=True)
        else:
            draw_box(d, i)
    return L


def frame(bg, photo_card, mode, L, t, dur, full=False):
    k = t / dur
    z = 1.0 + 0.06 * k
    bw, bh = bg.size
    cw, ch = int(W * 1.1 / z), int(H * 1.1 / z)
    cx, cy = (bw - cw) // 2, (bh - ch) // 2
    fr = bg.crop((cx, cy, cx + cw, cy + ch)).resize((W, H), Image.BILINEAR).convert('RGBA')
    if mode == 'photo':
        s = 1.0 + 0.05 * k
        pw = int((W - 60) * s)
        ph = int(photo_card.height * pw / photo_card.width)
        pc = photo_card.resize((pw, ph), Image.BILINEAR)
        fr.paste(pc, ((W - pw) // 2, 820 - (ph - int(photo_card.height * (W - 60) / photo_card.width)) // 2))
    else:
        fr = Image.alpha_composite(fr, board_layer(mode, dur if full else t))
    a = 1.0 if full else ease(t / 0.6)
    if a < 1:
        LL = L.copy()
        LL.putalpha(LL.split()[3].point(lambda v: int(v * a)))
        tmp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        tmp.paste(LL, (0, int(30 * (1 - a))))
        LL = tmp
    else:
        LL = L
    return Image.alpha_composite(fr, LL).convert('RGB')


def dm_sheet(out):
    Wd, Hd = 1080, 1350
    im = Image.new('RGB', (Wd, Hd), IVORY)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, Wd, 190), fill=GREEN)
    d.text((Wd / 2, 80), '내 돈의 일곱 칸 점검표', font=fB(56), fill=(255, 255, 255), anchor='mm')
    d.text((Wd / 2, 148), '지금 제일 신경 쓰이는 칸에 ○, 한 줄씩 적어 보세요', font=fBo(30),
           fill=(230, 236, 232), anchor='mm')
    Q = ['매달 들어오고 나가는 돈, 한 장에 적어 본 적 있나요?',
         '일을 쉬게 되면 몇 달 버틸 수 있나요?',
         '이 돈, 언제 쓸 돈인가요?',
         '챙길 수 있는 공제를 놓치고 있진 않나요?',
         '집에 묶인 돈과 쓸 수 있는 돈, 균형은요?',
         '월급이 끊긴 뒤 매달 들어올 돈은요?',
         '가족과 돈 이야기를 해 본 적 있나요?']
    y = 225
    for i, (num, name, _, _) in enumerate(AREAS):
        d.rounded_rectangle((50, y, Wd - 50, y + 140), radius=18, fill=(255, 255, 255), outline=(214, 220, 214), width=2)
        d.ellipse((76, y + 24, 124, y + 72), outline=GREEN, width=4)
        d.text((150, y + 22), f'{num} {name}', font=fB(34), fill=GREEN)
        d.text((150 + d.textlength(f'{num} {name}', font=fB(34)) + 24, y + 30), Q[i], font=fBo(26), fill=(90, 100, 94))
        d.line((150, y + 112, Wd - 90, y + 112), fill=(200, 206, 200), width=2)
        y += 152
    d.text((Wd / 2, Hd - 30), '키움멘토 · 내 돈의 지도, 함께 그립니다', font=fBo(26), fill=GREEN, anchor='mm')
    im.save(out)


def main():
    out = sys.argv[1]
    if '--dm' in sys.argv:
        return dm_sheet(out)
    photo = screen_photo()
    bg = background(photo)
    D = json.load(open(os.environ['DURS'])) if os.environ.get('DURS') else None
    scenes = []
    for i, (mode, sub, big, note, dur) in enumerate(SCENES):
        scenes.append((mode, text_layer(sub, big, note), D[i] if D else dur))
    if '--cover' in sys.argv:
        frame(bg, photo, 'board', text_layer('', ['누구에게나 있는', '==일곱 칸=='], ''), 0, 5, full=True).save(out)
        return
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'png', '-framerate', str(FPS),
                           '-i', '-', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-shortest', '-c:v', 'libx264',
                           '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart',
                           out], stdin=subprocess.PIPE)
    prev = None
    for si, (mode, L, dur) in enumerate(scenes):
        n = int(dur * FPS)
        for i in range(n):
            fr = frame(bg, photo, mode, L, i / FPS, dur)
            if si > 0 and i < 9 and prev is not None:
                fr = Image.blend(prev, fr, (i + 1) / 10)
            if i == n - 1:
                prev = fr
            fr.save(ff.stdin, 'PNG', compress_level=1)
    ff.stdin.close()
    ff.wait()


if __name__ == '__main__':
    main()
