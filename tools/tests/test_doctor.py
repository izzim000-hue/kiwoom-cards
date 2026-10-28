"""reelkit.doctor 단위 시험과 tools/doctor.py CLI 시험 (stdlib unittest 전용)."""
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from reelkit import constants, doctor  # noqa: E402
from reelkit.doctor import Check  # noqa: E402

INSTALL_CMD = "python3 -m pip install --user -r tools/requirements.txt"


def six_checks(**levels):
    """여섯 점검을 고정 순서로 만든다. levels 로 이름별 수준을 바꾼다."""
    details = {
        "playwright": "playwright 1.63.0 (고정 버전)",
        "chromium": "Chromium 153.0.8010.12 (기본 실행)",
        "font-files": "3/3 sha256 일치",
        "font-load": "Noto Sans KR 400/700/900 로드됨, 시스템 폰트 대체 없음",
        "ffmpeg": "ffmpeg version 6.1.1-3ubuntu5 Copyright (c) 2000-2023 the FFmpeg developers",
        "ffprobe": "ffprobe version 6.1.1-3ubuntu5",
    }
    out = []
    for name in ("playwright", "chromium", "font-files", "font-load", "ffmpeg", "ffprobe"):
        level = levels.get(name, "ok")
        detail = details[name]
        if name == "playwright" and level == "warn":
            detail = f"playwright 1.64.1 사용 중 (고정 1.63.0 아님) — 안내 {INSTALL_CMD}"
        if level == "fail":
            detail = f"{name} 실패 원인"
        out.append(Check(name, level, detail))
    return out


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-doctor-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def fonts_dir(self, **overrides):
        """실제 폰트로 향하는 심볼릭 링크 폴더. overrides[파일이름]=None 이면 빼고, 문자열이면 그 내용으로 만든다."""
        d = Path(tempfile.mkdtemp(dir=self.tmp))
        for name in constants.FONT_FILES.values():
            if name in overrides:
                if overrides[name] is not None:
                    (d / name).write_text(overrides[name], encoding="utf-8")
                continue
            (d / name).symlink_to(constants.FONTS_DIR / name)
        return d


class PureChecks(TempDirCase):
    def test_read_pin_from_committed_requirements(self):
        self.assertEqual(doctor.read_pin(constants.REQUIREMENTS), "1.63.0")

    def test_read_pin_without_playwright_line_is_none(self):
        p = self.tmp / "req.txt"
        p.write_text("# 비어 있음\nfoo==1.0\n", encoding="utf-8")
        self.assertIsNone(doctor.read_pin(p))

    def test_version_mismatch_is_warning_with_both_versions_and_command(self):
        c = doctor.check_playwright_version("1.64.1", "1.63.0")
        self.assertEqual(c.name, "playwright")
        self.assertEqual(c.level, "warn")
        for needle in ("1.64.1", "1.63.0", INSTALL_CMD):
            self.assertIn(needle, c.detail)

    def test_version_missing_is_fail_naming_install(self):
        c = doctor.check_playwright_version(None, "1.63.0")
        self.assertEqual(c.level, "fail")
        self.assertIn("미설치", c.detail)
        self.assertIn(INSTALL_CMD, c.detail)

    def test_version_equal_is_ok(self):
        c = doctor.check_playwright_version("1.63.0", "1.63.0")
        self.assertEqual(c.level, "ok")
        self.assertIn("1.63.0", c.detail)

    def test_summary_with_only_playwright_warning_is_healthy_and_counts_it(self):
        s = doctor.summarize(six_checks(playwright="warn"))
        self.assertTrue(s.startswith("릴스 렌더 환경 점검: 정상"), s)
        self.assertIn("경고 1건", s)
        self.assertIn("1.64.1", s)  # 쓰는 Playwright 버전이 요약에 드러난다

    def test_summary_with_chromium_fail_is_failure(self):
        s = doctor.summarize(six_checks(chromium="fail"))
        self.assertTrue(s.startswith("릴스 렌더 환경 점검: 실패"), s)
        self.assertNotIn("정상", s)

    def test_summary_is_never_green_when_font_checks_fail(self):
        for name in ("font-load", "font-files"):
            s = doctor.summarize(six_checks(**{name: "fail"}))
            self.assertNotIn("정상", s, name)

    def test_font_files_missing_black_is_fail_naming_file(self):
        d = self.fonts_dir(**{"NotoSansKR-Black.otf": None})
        c = doctor.check_font_files(d)
        self.assertEqual(c.level, "fail")
        self.assertIn("NotoSansKR-Black.otf", c.detail)

    def test_font_files_garbage_black_is_fail_naming_file_and_sha256(self):
        d = self.fonts_dir(**{"NotoSansKR-Black.otf": "garbage"})
        c = doctor.check_font_files(d)
        self.assertEqual(c.level, "fail")
        self.assertIn("NotoSansKR-Black.otf", c.detail)
        self.assertIn("sha256", c.detail)

    def test_font_files_reports_every_problem(self):
        d = self.fonts_dir(**{"NotoSansKR-Black.otf": "garbage", "NotoSansKR-Bold.otf": None})
        c = doctor.check_font_files(d)
        self.assertIn("NotoSansKR-Black.otf", c.detail)
        self.assertIn("NotoSansKR-Bold.otf", c.detail)

    def test_font_files_real_dir_is_ok(self):
        c = doctor.check_font_files(constants.FONTS_DIR)
        self.assertEqual((c.level, c.detail), ("ok", "3/3 sha256 일치"))

    def test_ffmpeg_and_ffprobe_are_ok_here(self):
        self.assertEqual(doctor.check_ffmpeg().level, "ok")
        self.assertEqual(doctor.check_ffprobe().level, "ok")


def run_cli(*args, env=None):
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    e.update(env or {})
    return subprocess.run([sys.executable, "tools/doctor.py", *args], cwd=REPO,
                          capture_output=True, text=True, env=e)


class Cli(TempDirCase):
    def test_default_run_exits_0_and_prints_healthy_summary(self):
        r = run_cli()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("정상", r.stdout)
        self.assertNotIn("[실패]", r.stdout)
        self.assertEqual(sum(1 for line in r.stdout.splitlines() if line.startswith("[")), 6)

    def test_quiet_prints_exactly_one_stdout_line_and_nothing_on_stderr(self):
        r = run_cli("--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = [line for line in r.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, r.stdout)
        self.assertIn("정상", lines[0])
        self.assertEqual(r.stderr, "")

    def test_json_has_six_checks_and_playwright_and_launch(self):
        r = run_cli("--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = json.loads(r.stdout)
        self.assertIs(d["ok"], True)
        self.assertEqual(len(d["checks"]), 6)
        self.assertEqual([c["name"] for c in d["checks"]],
                         ["playwright", "chromium", "font-files", "font-load", "ffmpeg", "ffprobe"])
        self.assertEqual(d["playwright"], importlib.metadata.version("playwright"))
        self.assertTrue(d["launch"])
        self.assertIn("정상", d["summary"])

    def test_broken_black_face_exits_1_naming_file_and_weight_900(self):
        d = self.fonts_dir(**{"NotoSansKR-Black.otf": "garbage"})
        r = run_cli("--fonts-dir", str(d))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        out = r.stdout + r.stderr
        self.assertIn("NotoSansKR-Black.otf", out)
        self.assertIn("900", out)
        self.assertIn("[실패]", r.stdout)
        self.assertNotIn("릴스 렌더 환경 점검: 정상", out)

    def test_quiet_failure_puts_details_on_stderr_and_summary_on_stdout(self):
        d = self.fonts_dir(**{"NotoSansKR-Black.otf": "garbage"})
        r = run_cli("--quiet", "--fonts-dir", str(d))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len([x for x in r.stdout.splitlines() if x.strip()]), 1)
        self.assertIn("실패", r.stdout)
        self.assertIn("NotoSansKR-Black.otf", r.stderr)


class ProbeFailures(unittest.TestCase):
    """멈추거나 사라진 ffmpeg/ffprobe 는 트레이스백이 아니라 FAIL 한 줄이어야 한다 (세션 시작 훅이 부른다)."""

    def patched(self, exc):
        return mock.patch("reelkit.doctor.subprocess.run", side_effect=exc)

    def test_timeout_is_a_fail_check(self):
        with mock.patch("reelkit.doctor.shutil.which", return_value="/usr/bin/ffmpeg"), \
                self.patched(subprocess.TimeoutExpired(["ffmpeg"], 30)):
            c = doctor.check_ffmpeg()
        self.assertEqual(c.level, "fail")
        self.assertIn("TimeoutExpired", c.detail)

    def test_executable_vanishing_after_which_is_a_fail_check(self):
        with mock.patch("reelkit.doctor.shutil.which", return_value="/usr/bin/ffprobe"), \
                self.patched(FileNotFoundError("ffprobe")):
            c = doctor.check_ffprobe()
        self.assertEqual(c.level, "fail")

    def test_run_passes_a_timeout(self):
        with mock.patch("reelkit.doctor.subprocess.run") as run:
            doctor._run(["ffmpeg", "-version"])
        self.assertIsNotNone(run.call_args.kwargs.get("timeout"))


if __name__ == "__main__":
    unittest.main()
