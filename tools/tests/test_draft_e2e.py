"""make-reel 스킬 문서 점검, 초안 전체 흐름(렌더 포함), 실제 릴스 폴더에 대한 slot 읽기 시험 (stdlib unittest 전용)."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
FIX = Path(__file__).resolve().parent / "fixtures"
SKILL_DIR = REPO / ".claude" / "skills" / "make-reel"
DRAFT = [sys.executable, str(TOOLS / "draft.py")]
REEL = [sys.executable, str(TOOLS / "reel.py")]
sys.path.insert(0, str(TOOLS))

from reelkit import figures  # noqa: E402

DOC_FILES = [SKILL_DIR / "SKILL.md", SKILL_DIR / "references" / "source-format.md",
             SKILL_DIR / "references" / "house-style.md"]
DRAFT_CMD_RE = re.compile(r"python3 tools/draft\.py ((?:figures )?[a-z]+)")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


class SkillDoc(unittest.TestCase):
    def test_frontmatter_and_links(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        head = text.split("---")[1]
        self.assertRegex(head, r"(?m)^name: make-reel$")
        self.assertRegex(head, r"(?m)^description: \S")
        for ref in ("references/source-format.md", "references/house-style.md"):
            self.assertIn(ref, text)
            self.assertTrue((SKILL_DIR / ref).is_file(), ref)

    def test_required_phrases(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ("python3 tools/draft.py bundle", "--request-start", "--layout new --strict", "2026/reels/drafts/"):
            self.assertIn(phrase, text)
        style = (SKILL_DIR / "references" / "house-style.md").read_text(encoding="utf-8")
        for phrase in ("원금 보장", "확정 수익", "무조건 절세", "tools/data/compliance_rules.json"):
            self.assertIn(phrase, style)

    def test_every_draft_command_exists(self):
        seen = set()
        for path in DOC_FILES:
            for sub in DRAFT_CMD_RE.findall(path.read_text(encoding="utf-8")):
                seen.add(sub)
        self.assertTrue({"slot", "expand", "convert", "bundle", "approve", "promote", "figures list", "figures add"} <= seen, seen)
        for sub in sorted(seen):
            with self.subTest(sub=sub):
                r = run(DRAFT + sub.split() + ["--help"])
                self.assertEqual(r.returncode, 0, r.stderr)

    def test_confirm_only_on_human_only_lines(self):
        for path in DOC_FILES:
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "figures confirm" in line:
                    with self.subTest(file=path.name, line=n):
                        self.assertTrue("사람" in line or "금지" in line, line)

    def test_approve_only_on_human_only_lines(self):
        seen = 0
        for path in DOC_FILES:
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "draft.py approve" in line:
                    seen += 1
                    with self.subTest(file=path.name, line=n):
                        self.assertTrue("사람" in line or "금지" in line, line)
        self.assertGreaterEqual(seen, 1)


class EndToEnd(unittest.TestCase):
    def test_pension_draft_pipeline(self):
        with tempfile.TemporaryDirectory() as t:
            reels = Path(t) / "reels"
            (reels / "specs").mkdir(parents=True)
            r = run(DRAFT + ["slot", "--reels-dir", str(reels), "--date", "2026-11-08",
                             "--slug", "pension-credit-limit", "--create"])
            self.assertEqual(r.returncode, 0, r.stderr)
            d = reels / "drafts" / "2026-11-08-pension-credit-limit"
            self.assertTrue(d.is_dir())
            shutil.copy(FIX / "draft-pension.src.json", d / "spec.src.json")
            shutil.copy(FIX / "draft-pension.caption.src.json", d / "caption.src.json")

            r = run(DRAFT + ["expand", str(d / "spec.src.json"), str(d / "spec.json")])
            self.assertEqual(r.returncode, 0, r.stderr)
            r = run(DRAFT + ["check", str(d / "spec.json"), "--out", str(d / "check.json"), "--strict"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = run(DRAFT + ["caption", str(d / "spec.json"), str(d / "caption.src.json"), "--out", str(d / "caption.txt")])
            self.assertEqual(r.returncode, 0, r.stderr)
            mp4 = d / "2026-11-08-pension-credit-limit.mp4"
            r = run(REEL + [str(d / "spec.json"), str(mp4), "--layout", "new", "--strict"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

            spec = json.loads((d / "spec.json").read_text(encoding="utf-8"))
            self.assertEqual(len(spec["scenes"]), 7)
            m = re.search(r"(?m)^duration=(\d+\.\d)s cover_ms=\d+$", r.stdout)
            self.assertTrue(m, r.stdout)
            self.assertTrue(21 <= float(m.group(1)) <= 27, m.group(1))
            self.assertTrue(mp4.is_file())
            self.assertTrue((d / "2026-11-08-pension-credit-limit.safe-s01.png").is_file())

            check = json.loads((d / "check.json").read_text(encoding="utf-8"))
            self.assertEqual(check["errors"], [])
            self.assertTrue(check["needs_check"])
            registry = figures.load_registry(figures.REGISTRY_PATH)
            for item in check["needs_check"]:
                for fid in item["ids"]:
                    fid = fid[4:] if fid.startswith("fig.") else fid
                    self.assertEqual(figures.get_figure(registry, fid)["verified"], "미확인", fid)

            lines = (d / "caption.txt").read_text(encoding="utf-8").rstrip("\n").splitlines()
            self.assertTrue(lines[0].startswith("연말정산 바로 알기 ②"), lines[0])
            self.assertTrue(1 <= len(lines[-1].split()) <= 5, lines[-1])


class RealDirSlot(unittest.TestCase):
    def test_proposes_later_date_and_creates_nothing(self):
        before = sorted(p.name for p in (REPO / "2026" / "reels" / "drafts").glob("*")) \
            if (REPO / "2026" / "reels" / "drafts").exists() else []
        r = run(DRAFT + ["slot", "--slug", "pension-credit-limit"])
        self.assertEqual(r.returncode, 0, r.stderr)
        info = json.loads(r.stdout)
        self.assertGreater(info["proposed_date"], "2026-11-07")
        self.assertTrue(info["ask"])
        self.assertEqual(info["conflicts"], [])
        after = sorted(p.name for p in (REPO / "2026" / "reels" / "drafts").glob("*")) \
            if (REPO / "2026" / "reels" / "drafts").exists() else []
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
