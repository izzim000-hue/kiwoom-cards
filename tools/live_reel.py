"""실사 클립(Kling 등에서 생성)을 이어 붙여 35초 무음 릴스를 만든다.

사용법:
    python3 tools/live_reel.py <클립 폴더> <출력.mp4>

클립 폴더에는 scene1.mp4 ~ scene7.mp4 와 profile.jpg(또는 .png)를 둔다.
- 클립이 필요한 길이보다 짧으면 자동으로 살짝 느리게 늘린다(최대 1.4배).
- 9:16이 아닌 클립은 가운데 기준으로 잘라 1080x1920에 맞춘다.
- 마지막 장면은 프로필 사진에 가벼운 확대만 준다(얼굴 변형 없음).
- 소리는 넣지 않는다(무음 AAC 트랙만, 녹음은 나중에 앱에서).

월별·회차별로 바꿀 것은 아래 '데이터 블록'만 고치면 된다.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ───────────────────────── 데이터 블록 ─────────────────────────
W, H, FPS = 1080, 1920, 30
XFADE = 0.5  # 장면 사이 디졸브 길이(초)

# (클립 파일, 장면 시작초, 장면 끝초, 자막 줄들)
SCENES = [
    ("scene1.mp4", 0.0, 4.0, ["돈은 꾸준히 모으는데,", "왜 미래는 여전히 불안할까요?"]),
    ("scene2.mp4", 4.0, 8.0, ["월급도 들어오고,", "저축도 하고 있는데…"]),
    ("scene3.mp4", 8.0, 12.0, ["정작 내 돈이 어디로 가는지", "알고 계신가요?"]),
    ("scene4.mp4", 12.0, 16.5, ["저는 상품부터", "추천하지 않습니다."]),
    ("scene5.mp4", 16.5, 21.5, ["먼저 수입과 지출,", "현재 자산과 미래 목표를 확인합니다."]),
    ("scene6.mp4", 21.5, 26.0, ["그다음 필요한 준비의", "순서를 함께 정합니다."]),
    ("scene7.mp4", 26.0, 32.0, ["재무설계는 상품이 아니라", "순서입니다."]),
]
PROFILE = ("profile", 32.0, 35.0)  # profile.jpg / profile.png
END_NAME = "키움멘토 | 이문영"
END_SLOGAN = "내 돈의 지도, 함께 그립니다."
END_SMALL = "돈 흐름이 궁금하다면 프로필 DM"  # 빈 문자열이면 생략

DEEP_GREEN = (47, 79, 62)
BEIGE = (245, 239, 228)
FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_BOLD = FONT_DIR / "NotoSansKR-Bold.otf"
FONT_BLACK = FONT_DIR / "NotoSansKR-Black.otf"
FONT_REG = FONT_DIR / "NotoSansKR-Regular.otf"
SUB_SIZE = 70
SUB_CENTER_Y = 1290  # 인스타 하단 UI(약 320px)를 피한 자막 중심 높이
GRADE = "eq=saturation=0.9:contrast=1.03,colorbalance=rs=0.03:bs=-0.03"  # 따뜻·차분하게
MAX_SLOW = 1.4
# ───────────────────────────────────────────────────────────────


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"명령 실패: {' '.join(cmd[:6])} ...\n{r.stderr[-2000:]}")
    return r.stdout


def duration(path: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)])
    return float(json.loads(out)["format"]["duration"])


def subtitle_png(lines: list[str], path: Path) -> None:
    """반투명 어두운 띠 위 흰 글씨. 화면 가득 채우지 않는 작은 자막."""
    font = ImageFont.truetype(str(FONT_BOLD), SUB_SIZE)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gap = int(SUB_SIZE * 0.42)
    boxes = [d.textbbox((0, 0), t, font=font) for t in lines]
    heights = [b[3] - b[1] for b in boxes]
    total = sum(heights) + gap * (len(lines) - 1)
    widest = max(b[2] - b[0] for b in boxes)
    pad_x, pad_y = 54, 40
    top = SUB_CENTER_Y - total // 2
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.rounded_rectangle(
        (W // 2 - widest // 2 - pad_x, top - pad_y, W // 2 + widest // 2 + pad_x, top + total + pad_y),
        radius=28, fill=(20, 28, 24, 120),
    )
    band = band.filter(ImageFilter.GaussianBlur(2))
    img.alpha_composite(band)
    y = top
    for t, b, h in zip(lines, boxes, heights):
        x = W // 2 - (b[2] - b[0]) // 2 - b[0]
        d.text((x + 2, y - b[1] + 3), t, font=font, fill=(0, 0, 0, 110))
        d.text((x, y - b[1]), t, font=font, fill=(255, 255, 255, 255))
        y += h + gap
    img.save(path)


def end_png(path: Path) -> None:
    """마지막 장면 하단 베이지 띠 + 진녹 글씨. 사진(얼굴)은 가리지 않음."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top = 1180
    d.rectangle((0, top, W, H), fill=(*BEIGE, 238))
    d.rectangle((0, top, W, top + 8), fill=(*DEEP_GREEN, 255))
    f_name = ImageFont.truetype(str(FONT_BLACK), 74)
    f_slo = ImageFont.truetype(str(FONT_BOLD), 54)
    f_small = ImageFont.truetype(str(FONT_REG), 38)
    y = top + 90
    for text, f, color in ((END_NAME, f_name, DEEP_GREEN), (END_SLOGAN, f_slo, (60, 60, 56))):
        b = d.textbbox((0, 0), text, font=f)
        d.text((W // 2 - (b[2] - b[0]) // 2 - b[0], y - b[1]), text, font=f, fill=(*color, 255))
        y += (b[3] - b[1]) + 46
    if END_SMALL:
        b = d.textbbox((0, 0), END_SMALL, font=f_small)
        d.text((W // 2 - (b[2] - b[0]) // 2 - b[0], y + 20 - b[1]), END_SMALL, font=f_small, fill=(110, 110, 104, 255))
    img.save(path)


def find_profile(folder: Path) -> Path:
    for ext in (".jpg", ".jpeg", ".png", ".JPG", ".PNG"):
        p = folder / f"{PROFILE[0]}{ext}"
        if p.exists():
            return p
    sys.exit(f"{folder}에 profile.jpg(또는 .png)가 없습니다.")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    folder, out = Path(sys.argv[1]), Path(sys.argv[2])
    missing = [s[0] for s in SCENES if not (folder / s[0]).exists()]
    if missing:
        sys.exit(f"없는 클립: {', '.join(missing)}")
    profile = find_profile(folder)
    total = PROFILE[2]

    tmp = Path(tempfile.mkdtemp(prefix="live_reel_"))
    inputs: list[str] = []
    filters: list[str] = []
    seg_labels: list[str] = []
    n_seg = len(SCENES) + 1

    # 1) 장면별 클립: 꽉 채워 자르기 → 필요한 길이로 맞추기
    for i, (name, start, end, _) in enumerate(SCENES):
        need = (end - start) + (XFADE if i > 0 else 0.0)
        src = folder / name
        have = duration(src)
        factor = max(1.0, need / have)
        if factor > MAX_SLOW:
            print(f"경고: {name}이 {have:.1f}초로 짧아 {factor:.2f}배 느리게 늘립니다(10초 클립 권장).")
        inputs += ["-i", str(src)]
        filters.append(
            f"[{i}:v]setpts={factor:.4f}*(PTS-STARTPTS),fps={FPS},"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
            f"{GRADE},trim=0:{need:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{i}]"
        )
        seg_labels.append(f"v{i}")

    # 2) 프로필 사진: 가벼운 확대(1.00→1.06)만
    p_idx = len(SCENES)
    p_need = (PROFILE[2] - PROFILE[1]) + XFADE
    frames = int(round(p_need * FPS))
    inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{p_need:.3f}", "-i", str(profile)]
    filters.append(
        f"[{p_idx}:v]scale={W*3}:{H*3}:force_original_aspect_ratio=increase,crop={W*3}:{H*3},"
        f"zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d=1:s={W}x{H}:fps={FPS},setsar=1,trim=0:{p_need:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{p_idx}]"
    )
    seg_labels.append(f"v{p_idx}")

    # 3) 디졸브로 잇기 (장면 경계 = 데이터 블록의 시작초)
    bounds = [s[1] for s in SCENES[1:]] + [PROFILE[1]]
    cur = seg_labels[0]
    for k in range(1, n_seg):
        lab = f"x{k}"
        filters.append(f"[{cur}][{seg_labels[k]}]xfade=transition=fade:duration={XFADE}:offset={bounds[k-1]-XFADE:.3f}[{lab}]")
        cur = lab

    # 4) 자막 얹기 (첫 장면은 0초부터 바로 보이게)
    n_in = p_idx + 1
    overlays = [(lines, start, end) for _, start, end, lines in SCENES]
    for j, (lines, start, end) in enumerate(overlays):
        png = tmp / f"sub{j}.png"
        subtitle_png(lines, png)
        a = start if j == 0 else start + 0.25
        b = end - 0.3
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total}", "-i", str(png)]
        fin = "" if j == 0 else f"fade=t=in:st={a:.2f}:d=0.3:alpha=1,"
        filters.append(f"[{n_in}:v]format=rgba,{fin}fade=t=out:st={b-0.3:.2f}:d=0.3:alpha=1[s{j}]")
        filters.append(f"[{cur}][s{j}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[o{j}]")
        cur = f"o{j}"
        n_in += 1
    endp = tmp / "end.png"
    end_png(endp)
    inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total}", "-i", str(endp)]
    ea = PROFILE[1] + 0.2
    filters.append(f"[{n_in}:v]format=rgba,fade=t=in:st={ea:.2f}:d=0.5:alpha=1[se]")
    filters.append(f"[{cur}][se]overlay=0:0:enable='gte(t,{ea:.2f})',format=yuv420p[vout]")
    n_in += 1

    inputs += ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", f"{n_in}:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-t", f"{total}", "-movflags", "+faststart", str(out),
    ]
    run(cmd)
    print(f"완료: {out} ({duration(out):.2f}초)")


if __name__ == "__main__":
    main()
