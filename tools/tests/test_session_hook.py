"""SessionStart 훅의 Playwright 고정 블록 시험: 가짜 python3/agent-browser 로 pip 호출만 관찰한다 (네트워크·설치 없음)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / ".claude" / "hooks" / "session-start.sh"

FAKE_PYTHON = r"""#!/bin/bash
# 호출 기록: 인자와 PIP_BREAK_SYSTEM_PACKAGES 값
case "$*" in
  *importlib.metadata*)
    # pip 이 한 번 돈 뒤에는 FAKE_PW_AFTER(있으면)를 설치된 버전으로 보고한다
    if [ -e "$FAKE_LOG.installed" ] && [ -n "${FAKE_PW_AFTER:-}" ]; then echo "$FAKE_PW_AFTER"; else echo "${FAKE_PW_VERSION:-0.0.0}"; fi
    exit 0 ;;
  *sys.prefix*) exit 1 ;;
  *"-m pip"*) : > "$FAKE_LOG.installed"; echo "pip break=${PIP_BREAK_SYSTEM_PACKAGES:-} $*" >> "$FAKE_LOG"; exit "${FAKE_PIP_EXIT:-0}" ;;
  *doctor.py*) echo "doctor $*" >> "$FAKE_LOG"; exit 0 ;;
esac
exit 0
"""


class SessionHook(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-hook-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "python3").write_text(FAKE_PYTHON)
        (self.bin / "agent-browser").write_text("#!/bin/bash\nexit 0\n")
        for f in self.bin.iterdir():
            f.chmod(0o755)
        self.home = self.tmp / "home"
        (self.home / ".claude" / "skills" / "gsd-help").mkdir(parents=True)
        self.proj = self.tmp / "proj"
        (self.proj / "tools").mkdir(parents=True)
        self.log = self.tmp / "calls.log"
        self.log.write_text("")
        self.envfile = self.tmp / "envfile"
        self.envfile.write_text("")

    def run_hook(self, requirements_bytes, pw_version, pip_exit=0, pw_after=""):
        (self.proj / "tools" / "requirements.txt").write_bytes(requirements_bytes)
        env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}", "HOME": str(self.home),
            "CLAUDE_CODE_REMOTE": "true", "CLAUDE_ENV_FILE": str(self.envfile),
            "CLAUDE_PROJECT_DIR": str(self.proj), "TMPDIR": str(self.tmp),
            "FAKE_LOG": str(self.log), "FAKE_PW_VERSION": pw_version, "FAKE_PIP_EXIT": str(pip_exit),
            "FAKE_PW_AFTER": pw_after,
        }
        r = subprocess.run(["bash", str(HOOK)], env=env, capture_output=True, text=True)
        calls = self.log.read_text().splitlines()
        return r, [c for c in calls if c.startswith("pip")]

    def test_crlf_pin_matching_installed_version_does_not_run_pip(self):
        r, pips = self.run_hook(b"playwright==1.63.0\r\n", "1.63.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(pips, [])

    def test_spaces_and_comment_in_pin_do_not_force_reinstall(self):
        r, pips = self.run_hook(b"  playwright == 1.63.0   # pinned for chromium 1243\n", "1.63.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(pips, [])

    def test_version_mismatch_runs_pip_once_when_it_succeeds(self):
        r, pips = self.run_hook(b"playwright==1.63.0\n", "1.64.1", pw_after="1.63.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(pips), 1)
        self.assertNotIn("설치 실패", r.stderr)
        self.assertFalse(list(self.tmp.glob(".reelkit-pw-install-failed-*")))

    def test_pip_success_but_version_unchanged_stamps_and_stops_retrying(self):
        # pip 은 0 으로 끝났지만 가려진 사본 때문에 고정 버전이 잡히지 않는 경우 (WR-08)
        r, pips = self.run_hook(b"playwright==1.63.0\n", "1.64.1", pw_after="1.64.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(pips), 1)
        self.assertIn("설치 실패", r.stderr)
        self.assertTrue(list(self.tmp.glob(".reelkit-pw-install-failed-*")))
        self.log.write_text("")
        (self.tmp / "calls.log.installed").unlink()
        r2, pips2 = self.run_hook(b"playwright==1.63.0\n", "1.64.1", pw_after="1.64.1")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(pips2, [])

    def test_failed_install_retries_with_break_system_packages_then_stamps(self):
        r, pips = self.run_hook(b"playwright==1.63.0\n", "1.64.1", pip_exit=1)
        self.assertEqual(r.returncode, 0, r.stderr)  # 훅은 세션 시작을 막지 않는다
        self.assertEqual(len(pips), 2)
        self.assertIn("break=1", pips[1])
        self.assertIn("설치 실패", r.stderr)
        self.assertTrue(list(self.tmp.glob(".reelkit-pw-install-failed-*")))
        # 같은 컨테이너의 다음 세션은 실패한 설치를 되풀이하지 않는다
        self.log.write_text("")
        r2, pips2 = self.run_hook(b"playwright==1.63.0\n", "1.64.1", pip_exit=1)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(pips2, [])

    def test_still_exports_browser_path_and_runs_doctor(self):
        r, _ = self.run_hook(b"playwright==1.63.0\n", "1.63.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        if os.access("/opt/pw-browsers/chromium", os.X_OK):
            self.assertIn("AGENT_BROWSER_EXECUTABLE_PATH=/opt/pw-browsers/chromium", self.envfile.read_text())
        self.assertTrue(any(c.startswith("doctor") for c in self.log.read_text().splitlines()))


if __name__ == "__main__":
    unittest.main()
