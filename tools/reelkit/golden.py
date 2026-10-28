"""golden 회귀 (자리표시자: GREEN 커밋에서 실제 구현으로 교체한다)."""
from dataclasses import dataclass, field

from .constants import REPO_ROOT, TOOLS_DIR

GOLDEN_STEMS = (
    "2026-10-19-rate-secret-1", "2026-10-19-savings-interest", "2026-10-21-rate-secret-2",
    "2026-10-24-rate-secret-3", "2026-10-26-tax-deduction", "2026-10-28-salary-two-owners-1",
    "2026-10-29-ebook-event", "2026-10-31-salary-two-owners-2", "2026-11-02-salary-two-owners-3",
    "2026-11-04-salary-two-owners-4", "2026-11-07-salary-two-owners-5",
)
REELS_DIR = REPO_ROOT / "2026" / "reels"
SPECS_DIR = REELS_DIR / "specs"
MANIFEST = TOOLS_DIR / "tests" / "golden" / "manifest.json"
SSIM_MIN = 0.0
SCENE_THRESHOLD = 0.0


@dataclass
class ReelResult:
    stem: str
    verdict: str
    details: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)


def check_reel(entry):
    return ReelResult(entry["stem"], "PASS")


def unlisted_mp4s(entries, reels_dir=REELS_DIR):
    return []


def format_report(results, extras):
    return []
