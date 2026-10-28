"""환경 점검 (자리표시자: GREEN 커밋에서 실제 구현으로 교체한다)."""
from typing import NamedTuple


class Check(NamedTuple):
    name: str
    level: str
    detail: str


def read_pin(requirements=None):
    return None


def check_playwright_version(installed, pinned):
    return Check("playwright", "ok", "")


def summarize(checks):
    return ""


def check_font_files(fonts_dir=None):
    return Check("font-files", "ok", "")


def check_ffmpeg():
    return Check("ffmpeg", "fail", "")


def check_ffprobe():
    return Check("ffprobe", "fail", "")
