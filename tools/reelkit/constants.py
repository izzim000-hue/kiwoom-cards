"""릴스 렌더 상수의 단일 출처 (색, 타이밍, 캔버스, 안전영역, 번들 폰트)."""
import re
from pathlib import Path

# 브랜드 색 (기존 릴스 10편과 동일 값)
SAGE = "#DEE9E0"
DG = "#2F4F3E"
GOLD = "#B08D46"
MUT = "#5B6E62"

# 타이밍과 캔버스
LINE = 0.85   # 한 줄이 나타나는 간격(초)
HOLD = 1.9    # 장면 마지막 줄 이후 멈춤(초)
W = 1080
H = 1920
FPS = 30
ACCOUNT = "@kiwoom.mentor"

# 안전영역 (D-03). 시작값이며 비공개 실기기 업로드 후 이 파일에서만 보정한다.
# top 270은 research 가정 A1(검증 전).
SAFE = dict(
    top=270,
    warn_y=1250,     # y > 1250 경고
    bottom_ui=450,   # 아래에서 450px(y 1470 이후)는 오류
    right=150,
    left=96,         # 기존 padding
)

# 근거 표기와 계정명 (D-02, Plan 03에서 사용)
BASIS_PX = 36
BASIS_MAX_LINES = 2
ACCT_PX = 36

# 경로
TOOLS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS_DIR.parent
FONTS_DIR = TOOLS_DIR / "fonts"
TEMPLATE = Path(__file__).resolve().parent / "templates" / "frame.html"
REQUIREMENTS = TOOLS_DIR / "requirements.txt"

# 번들 폰트: CSS weight -> 파일 이름 (Chromium 리비전 1243은 주석에서만 언급)
FONT_FILES = {
    400: "NotoSansKR-Regular.otf",
    700: "NotoSansKR-Bold.otf",
    900: "NotoSansKR-Black.otf",
}

# 폰트 파일 세트 종류: 'original'(무수정 업스트림) 또는 'subset'(축소판). 2026-10-28 사용자 결정: 원본.
FONT_VARIANT = "original"

# 폰트를 바꾸면 이 값과 tools/fonts/README.md를 함께 갱신하고 golden 회귀를 다시 돌린다.
FONT_SHA256 = {
    "NotoSansKR-Regular.otf": "69975a0ac8472717870aefeab0a4d52739308d90856b9955313b2ad5e0148d68",
    "NotoSansKR-Bold.otf": "5a6ceb287ed2fc6cfc6213144ebea68cbd94b20fc9eb873d8486493bf02d9bda",
    "NotoSansKR-Black.otf": "a9977a588488d2a7f544bb2b589b01bed071dca64a4655d438696301b527884b",
}

# 원고 글자 패턴 (IN-06: check·motion·expand 가 같은 식을 쓴다)
TAG_RE = re.compile(r"</?[gs]>")                            # 원고 마크업 <g>, </g>, <s>, </s>
LINE_WHERE_RE = re.compile(r"^scene (\d+) line (\d+)$")    # 장부 where 의 장면 줄 자리 (카운트업은 여기에만)
