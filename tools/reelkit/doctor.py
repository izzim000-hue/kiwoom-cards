"""릴스 렌더 환경 점검 (ENV-01): Playwright 버전, Chromium, 번들 폰트, ffmpeg, ffprobe.

폰트 로드 점검은 렌더러가 쓰는 browser.open_page / browser.font_problems 와 같은 코드 경로를 쓴다.
그래서 doctor 가 정상이라고 하면 렌더러도 같은 판단을 한다.
"""
import argparse
import hashlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple, Optional

from . import browser, constants

INSTALL_CMD = "python3 -m pip install --user -r tools/requirements.txt"
NAMES = ("playwright", "chromium", "font-files", "font-load", "ffmpeg", "ffprobe")
_TAGS = {"ok": "[정상]", "warn": "[경고]", "fail": "[실패]"}
_HEAD = "릴스 렌더 환경 점검"


class Check(NamedTuple):
    name: str
    level: str      # "ok" | "warn" | "fail"
    detail: str


class Report(NamedTuple):
    checks: list
    playwright: Optional[str]   # 설치된 Playwright 버전, 없으면 None
    launch: Optional[str]       # browser.launch 가 쓴 경로("default" 또는 실행 파일), 못 띄웠으면 None


def read_pin(requirements=constants.REQUIREMENTS):
    """requirements.txt 의 첫 `playwright==X` 줄에서 X 를 돌려준다. 없으면 None."""
    try:
        text = Path(requirements).read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        m = re.match(r"\s*playwright\s*==\s*([^\s#;]+)", line)
        if m:
            return m.group(1)
    return None


def installed_playwright():
    try:
        return importlib.metadata.version("playwright")
    except importlib.metadata.PackageNotFoundError:
        return None


def check_playwright_version(installed, pinned):
    """버전 불일치는 경고다. 렌더 가능 여부는 chromium·font-load 점검이 정한다 (설치 없이 쓰는 허용 경로)."""
    if installed is None:
        return Check("playwright", "fail", f"playwright 미설치 → {INSTALL_CMD}")
    if pinned is not None and installed != pinned:
        return Check(
            "playwright", "warn",
            f"playwright {installed} 사용 중 (고정 {pinned} 아님) — 설치 없이 미리 깔린 Chromium으로 "
            f"렌더하는 허용 경로. 고정 버전으로 맞추려면 → {INSTALL_CMD} "
            "(pip --user가 거부되면 PIP_BREAK_SYSTEM_PACKAGES=1 로 다시 시도)")
    return Check("playwright", "ok", f"playwright {installed} (고정 버전)")


def check_chromium(pw):
    """(Check, browser 또는 None, used 또는 None). browser 는 호출한 쪽이 닫는다."""
    try:
        b, used = browser.launch(pw)
    except browser.BrowserLaunchError as e:
        return Check("chromium", "fail", str(e)), None, None
    except Exception as e:  # noqa: BLE001 - 어떤 실패든 점검 결과로 보고한다
        return Check("chromium", "fail", f"Chromium 점검 중 오류: {browser._first_line(e)}"), None, None
    version = b.version
    if used == "default":
        return Check("chromium", "ok", f"Chromium {version} (기본 실행)"), b, used
    return Check("chromium", "warn", f"기본 실행 실패 → {used} 로 폴백함 (Chromium {version})"), b, used


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_font_files(fonts_dir=constants.FONTS_DIR):
    """번들 폰트 3개의 존재와 sha256. 문제는 첫 번째만이 아니라 전부 보고한다."""
    problems = []
    for name in constants.FONT_FILES.values():
        path = Path(fonts_dir) / name
        if not path.is_file():
            problems.append(f"{path} 없음")
        elif _sha256(path) != constants.FONT_SHA256[name]:
            problems.append(f"{path} 내용이 바뀜 (sha256 불일치)")
    if problems:
        return Check("font-files", "fail", " / ".join(problems))
    return Check("font-files", "ok", "3/3 sha256 일치")


def check_note_font(fonts_dir=constants.FONTS_DIR):
    """노트 배치 손글씨 폰트(Gaegu Bold)의 존재와 sha256. 문제 문장 목록을 돌려주고 빈 목록이면 정상.

    노트 배치에서만 쓰는 폰트라 기존 점검의 수준(fail)을 올리지 않고 경고로만 합친다 (run_checks).
    """
    path = Path(fonts_dir) / constants.NOTE_FONT_FILE
    if not path.is_file():
        return [f"{path} 없음"]
    if _sha256(path) != constants.NOTE_FONT_SHA256:
        return [f"{path} 내용이 바뀜 (sha256 불일치)"]
    return []


def _with_note_font(files_check, fonts_dir):
    """font-files 점검에 노트 폰트 결과를 덧붙인다. 기본 폰트가 실패이면 그대로 두고, 정상일 때만 한 줄 더한다."""
    if files_check.level == "fail":
        return files_check
    problems = check_note_font(fonts_dir)
    if not problems:
        return Check(files_check.name, files_check.level,
                     f"{files_check.detail} · 노트 폰트 {constants.NOTE_FONT_FILE} 일치")
    return Check(files_check.name, "warn",
                 f"{files_check.detail} · 노트 배치 폰트 문제(노트 형식 렌더 불가): {' / '.join(problems)}")


def check_font_load(b, fonts_dir=constants.FONTS_DIR):
    """렌더러와 같은 코드 경로(open_page + font_problems)로 3개 면 로드와 시스템 폰트 대체 여부를 본다."""
    work = tempfile.mkdtemp(prefix="doctor-")
    try:
        page = browser.open_page(b, work, fonts_dir)
        try:
            problems = browser.font_problems(page)
        finally:
            page.close()
    except Exception as e:  # noqa: BLE001
        return Check("font-load", "fail", f"폰트 로드 점검 중 오류: {browser._first_line(e)}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if problems:
        return Check("font-load", "fail", " / ".join(problems))
    return Check("font-load", "ok", "Noto Sans KR 400/700/900 로드됨, 시스템 폰트 대체 없음")


PROBE_TIMEOUT = 30  # 초. 세션 시작 훅이 doctor 를 동기로 부르므로 멈춘 ffmpeg 가 세션을 붙잡지 않게 한다


def _run(cmd, timeout=PROBE_TIMEOUT):
    """cmd 를 실행한다. 시간 초과나 실행 오류(which 와 실행 사이의 경합 등)는 종료 코드 127 로 돌려준다."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as e:
        return subprocess.CompletedProcess(cmd, 127, "", f"{e.__class__.__name__}: {e}")


def _first_text_line(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        return Check("ffmpeg", "fail", "ffmpeg 없음")
    enc = _run(["ffmpeg", "-hide_banner", "-encoders"])
    if enc.returncode != 0:
        return Check("ffmpeg", "fail", f"ffmpeg 실행 실패: {_first_text_line(enc.stderr) or enc.returncode}")
    if not re.search(r"\blibx264\b", enc.stdout):
        return Check("ffmpeg", "fail", "libx264 없음")
    if not re.search(r"^\s*[A-Z.]+\s+aac\s", enc.stdout, re.M):
        return Check("ffmpeg", "fail", "aac 인코더 없음")
    one = _run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.1",
                "-frames:v", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-f", "null", "-"])
    if one.returncode != 0:
        return Check("ffmpeg", "fail", f"1프레임 인코딩 실패: {_first_text_line(one.stderr) or one.returncode}")
    ver = _run(["ffmpeg", "-version"])
    return Check("ffmpeg", "ok", _first_text_line(ver.stdout) or "ffmpeg")


def check_ffprobe():
    if shutil.which("ffprobe") is None:
        return Check("ffprobe", "fail", "ffprobe 없음")
    r = _run(["ffprobe", "-version"])
    if r.returncode != 0:
        return Check("ffprobe", "fail", f"ffprobe 실행 실패: {_first_text_line(r.stderr) or r.returncode}")
    return Check("ffprobe", "ok", _first_text_line(r.stdout) or "ffprobe")


def run_checks(fonts_dir=constants.FONTS_DIR, requirements=constants.REQUIREMENTS):
    """여섯 점검을 고정 순서로 돌려 Report 로 낸다."""
    installed = installed_playwright()
    pw_check = check_playwright_version(installed, read_pin(requirements))
    launch_used = None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sync_playwright = None

    if sync_playwright is None:
        msg = "playwright 없이 점검 불가 — 먼저 설치하세요"
        chromium, font_load = Check("chromium", "fail", msg), Check("font-load", "fail", msg)
    else:
        chromium, font_load = None, None
        try:
            with sync_playwright() as pw:
                chromium, b, launch_used = check_chromium(pw)
                if b is None:
                    font_load = Check("font-load", "fail", "Chromium 을 띄우지 못해 점검 불가")
                else:
                    try:
                        font_load = check_font_load(b, fonts_dir)
                    finally:
                        b.close()
        except Exception as e:  # noqa: BLE001 - 드라이버 시작 실패 등
            if chromium is None:
                chromium = Check("chromium", "fail", f"Playwright 시작 실패: {browser._first_line(e)}")
            if font_load is None:
                font_load = Check("font-load", "fail", "Playwright 를 시작하지 못해 점검 불가")
    checks = [pw_check, chromium, _with_note_font(check_font_files(fonts_dir), fonts_dir), font_load, check_ffmpeg(), check_ffprobe()]
    return Report(checks, installed, launch_used)


def _ffmpeg_token(detail):
    m = re.match(r"ffmpeg version (\S+)", detail)
    return f"ffmpeg {m.group(1)}" if m else detail


def summarize(checks):
    """한 줄 요약. 폰트 점검이 실패하면 정상으로 나올 수 없다."""
    by_name = {c.name: c for c in checks}
    fails = [c for c in checks if c.level == "fail"]
    if fails:
        first = fails[0]
        return (f"{_HEAD}: 실패 {len(fails)}건 — {first.name}: {first.detail} "
                "(자세히: python3 tools/doctor.py)")
    warns = sum(1 for c in checks if c.level == "warn")
    pw_head = by_name["playwright"].detail.split(" — ")[0]
    text = (f"{_HEAD}: 정상 ({pw_head} · {by_name['chromium'].detail} · 폰트 3/3 · "
            f"{_ffmpeg_token(by_name['ffmpeg'].detail)})")
    if warns:
        text += f", 경고 {warns}건"
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description="릴스 렌더 환경 점검 (Playwright · Chromium · 번들 폰트 · ffmpeg)")
    ap.add_argument("--quiet", action="store_true", help="요약 한 줄만 stdout 에 낸다 (실패 시 자세한 줄은 stderr)")
    ap.add_argument("--json", action="store_true", help="결과를 JSON 으로 낸다")
    ap.add_argument("--fonts-dir", default=str(constants.FONTS_DIR), help="시험용, 기본값 tools/fonts")
    args = ap.parse_args(argv)

    report = run_checks(fonts_dir=Path(args.fonts_dir))
    checks = report.checks
    summary = summarize(checks)
    ok = not any(c.level == "fail" for c in checks)
    lines = [f"{_TAGS[c.level]} {c.name}  {c.detail}" for c in checks]

    if args.json:
        print(json.dumps({
            "ok": ok,
            "checks": [{"name": c.name, "level": c.level, "detail": c.detail} for c in checks],
            "summary": summary,
            "playwright": report.playwright,
            "launch": report.launch,
        }, ensure_ascii=False))
    elif args.quiet:
        print(summary)
        if not ok:
            print("\n".join(lines), file=sys.stderr)
    else:
        print("\n".join(lines))
        print(summary)
    return 0 if ok else 1
