"""scenes.html의 장면을 프레임 단위로 찍어 scene1~7.mp4로 만든다.

    python3 tools/scene_art/render_scenes.py <출력 폴더> [--preview]

--preview: 장면마다 몇 프레임만 PNG로 저장(빠른 점검용).
각 장면 길이는 live_reel.py가 필요로 하는 길이(장면 길이 + 디졸브 0.5초)와 같다.
"""
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FPS = 30


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    preview = "--preview" in sys.argv
    only = [int(a) for a in sys.argv[2:] if a.isdigit()] or list(range(1, 8))
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = b.new_page(viewport={"width": 1080, "height": 1920})
        page.goto((HERE / "scenes.html").as_uri())
        for sid in only:
            dur = page.evaluate(f"setup({sid})")
            n = int(round(dur * FPS))
            if preview:
                for k, f in enumerate((0, n // 3, 2 * n // 3, n - 1)):
                    page.evaluate(f"render({f / FPS},{f})")
                    page.screenshot(path=str(out / f"s{sid}_{k}.png"))
                continue
            ff = subprocess.Popen(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png",
                 "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                 str(out / f"scene{sid}.mp4")], stdin=subprocess.PIPE)
            for f in range(n):
                page.evaluate(f"render({f / FPS},{f})")
                ff.stdin.write(page.screenshot(type="png"))
            ff.stdin.close()
            ff.wait()
            print(f"scene{sid}.mp4 {n}프레임")
        b.close()


if __name__ == "__main__":
    main()
