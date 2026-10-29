"""표지 크롭 검사와 장면 모음 이미지 (BNDL-02, BNDL-03, D-03, D-12; 표준 라이브러리와 ffmpeg 만 사용).

인스타그램 프로필 그리드는 1080x1920 표지의 가운데 1080x1440(위아래 240px 씩 잘림)만 보여 준다.
크롭 창의 숫자는 이 파일에만 둔다. 표지 PNG 에서 배경색이 아닌 줄이 창 밖에 있으면 경고하고,
맨 위 진행 막대(14px)는 글자가 아니므로 제외한다. 외부 명령은 인자 목록으로만 부른다 (셸 사용 없음).
"""
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import constants, motion, timeline
from . import note as note_mod

GRID_W = constants.W
GRID_H = 1440
CROP_TOP = (constants.H - GRID_H) // 2          # 240
CROP_BOTTOM = CROP_TOP + GRID_H                 # 1680 (미포함)
BAR_ROWS = 14
STILL_OFFSET_S = 0.4                            # 장면 마지막 상태가 시작된 뒤 이 시간에 찍은 것으로 표시 (표지와 같은 규칙)
SHEET_COLS = 4
TILE_W, TILE_H = 360, 640
SHEET_PAD = 12


class StillsError(RuntimeError):
    """ffmpeg 가 이미지를 읽거나 만들지 못했을 때. 메시지는 한국어."""


def _hex_rgb(color):
    c = color.lstrip("#")
    return bytes(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _decode(png):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True)
    if r.returncode != 0:
        raise StillsError(f"ffmpeg 가 PNG 를 읽지 못함: {png} ({r.stderr.decode('utf-8', 'replace').strip()[:200]})")
    return r.stdout


def ink_rows_outside_crop(png, *, bg=constants.SAGE, tol=0):
    """배경이 아닌 줄 중 진행 막대(0..13)와 크롭 창(240..1679) 밖인 줄 번호 목록. PNG 는 1080x1920 이어야 한다."""
    data = _decode(png)
    w, h = constants.W, constants.H
    if len(data) != w * h * 3:
        raise StillsError(f"표지 크기가 {w}x{h} 가 아님: {png}")
    px = _hex_rgb(bg)
    flat = px * w
    stride = w * 3
    rows = []
    for y in range(h):
        if BAR_ROWS <= y < CROP_TOP or y >= CROP_BOTTOM:
            row = data[y * stride:(y + 1) * stride]
            if row == flat:
                continue
            if tol and all(abs(a - b) <= tol for a, b in zip(row, flat)):
                continue
            rows.append(y)
    return rows


def _ranges(rows):
    out = []
    for y in rows:
        if out and y == out[-1][1] + 1:
            out[-1][1] = y
        else:
            out.append([y, y])
    return out


def cover_crop_warnings(png, **kw):
    """창 밖 글자 줄을 연속 구간으로 묶어 `COVER_CROP: ... y A~B` 경고 문장 목록으로 돌려준다."""
    return [f"COVER_CROP: 표지 글자가 프로필 그리드 크롭(가운데 {GRID_W}×{GRID_H}, y {CROP_TOP}~{CROP_BOTTOM - 1}) 밖에 있음 — y {a}~{b}"
            for a, b in _ranges(ink_rows_outside_crop(png, **kw))]


def scene_times(spec):
    """장면마다 마지막 상태가 시작된 시각 + 0.4초 (초, 소수 둘째 자리). 장면 1 은 표지 시점과 같다.

    motion basic 이면 시간표의 final_t (모든 애니메이션이 끝난 프레임, 표지·장면 모음에 쓰는 프레임)를 쓴다.
    """
    if note_mod.is_note(spec):
        return note_mod.scene_times(spec)
    if motion.resolve(spec) == "basic":
        return [round(sc.final_t, 2) for sc in motion.schedule(spec).scenes]
    states = timeline.build_states(spec)
    times, t = {}, 0.0
    for st in states:
        if st.k == len(st.lines):
            times[st.scene] = round(t + STILL_OFFSET_S, 2)
        t += st.dur
    return [times[i] for i in sorted(times)]


def _filter_escape(text):
    return str(text).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def contact_sheet(frames, out, *, font=constants.FONTS_DIR / "NotoSansKR-Bold.otf", cols=SHEET_COLS):
    """장면 PNG 목록을 `장면 N` 라벨이 붙은 한 장의 PNG 로 이어 붙인다 (ffmpeg scale + drawtext + tile)."""
    frames = [Path(f) for f in frames]
    if not frames:
        raise StillsError("장면 이미지가 없음")
    out = Path(out)
    n = len(frames)
    cols = min(cols, n)
    rows = math.ceil(n / cols)
    work = Path(tempfile.mkdtemp(prefix="reel-sheet-"))
    try:
        for i, f in enumerate(frames, 1):
            shutil.copyfile(f, work / f"sc{i:02d}.png")
        vf = (f"scale={TILE_W}:{TILE_H},"
              f"drawtext=fontfile='{_filter_escape(font)}':text='장면 %{{eif\\:n+1\\:d}}':x=10:y=10:fontsize=28:"
              f"fontcolor=black:box=1:boxcolor=white@0.8:boxborderw=6,"
              f"tile={cols}x{rows}:padding={SHEET_PAD}:margin={SHEET_PAD}:color=white")
        tmp = work / "sheet.png"
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(work / "sc%02d.png"),
                            "-vf", vf, "-frames:v", "1", str(tmp)], capture_output=True)
        if r.returncode != 0 or not tmp.is_file():
            raise StillsError("ffmpeg 가 장면 모음 이미지를 만들지 못함: "
                              + r.stderr.decode("utf-8", "replace").strip()[:300])
        part = out.with_name(out.name + ".part")
        shutil.copyfile(tmp, part)
        os.replace(part, out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out
