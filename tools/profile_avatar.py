#!/usr/bin/env python3
"""새싹 멘토 캐릭터로 인스타 프로필 사진(1080x1080, 원형으로 잘려도 안전) 만들기.

    python3 tools/profile_avatar.py OUT_DIR
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notebook_char as nc  # noqa: E402
from reelkit import browser  # noqa: E402

# 이름: (배경, 원 안 배경)
VARIANTS = {
    "A_딥그린": ("#2F4F3E", "#FBF8F1"),
    "B_아이보리": ("#FBF8F1", "#E3EDE5"),
}


def page(bg, disc):
    svg = nc.character("wave")
    return f'''<!doctype html><meta charset=utf-8><style>
html,body{{margin:0;width:1080px;height:1080px;overflow:hidden;background:{bg}}}
.disc{{position:absolute;left:90px;top:90px;width:900px;height:900px;border-radius:50%;background:{disc};overflow:hidden}}
.disc svg{{position:absolute;left:150px;top:96px;width:640px;height:auto}}
</style><div class="disc">{svg}</div>'''


def main(out_dir):
    from playwright.sync_api import sync_playwright
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work, sync_playwright() as pw:
        b, _ = browser.launch(pw)
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        for name, (bg, disc) in VARIANTS.items():
            f = Path(work) / "p.html"
            f.write_text(page(bg, disc), encoding="utf-8")
            pg.goto(f.as_uri())
            p = out / f"profile_{name}.png"
            pg.screenshot(path=str(p))
            print(p)
        b.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2026/character-pilot/profile")
