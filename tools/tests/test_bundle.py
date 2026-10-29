"""draft.py bundle: 초안 폴더 하나가 검수 묶음으로 만들어지는 전체 흐름 (렌더 1회, stdlib unittest 전용)."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
DRAFT = [sys.executable, str(TOOLS / "draft.py")]
sys.path.insert(0, str(TOOLS))

from reelkit import review, timeline  # noqa: E402

DATE, SLUG = "2026-11-08", "pension-credit-limit"
NAME = f"{DATE}-{SLUG}"
RISKY_HOOK = "원금 보장처럼 들리는 연금계좌 세액공제"
STATUTE_RE = re.compile(r"제\s*\d+\s*조")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


class Bundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        reels = Path(cls.tmp.name) / "reels"
        (reels / "specs").mkdir(parents=True)
        r = run(DRAFT + ["slot", "--reels-dir", str(reels), "--date", DATE, "--slug", SLUG, "--create"])
        assert r.returncode == 0, r.stderr
        cls.d = reels / "drafts" / NAME
        shutil.copy(FIX / "draft-pension.src.json", cls.d / "spec.src.json")
        cap = json.loads((FIX / "draft-pension.caption.src.json").read_text(encoding="utf-8"))
        cap["hook"] = RISKY_HOOK
        (cls.d / "caption.src.json").write_text(json.dumps(cap, ensure_ascii=False, indent=1), encoding="utf-8")
        cls.before = {n: (cls.d / n).read_bytes() for n in ("spec.src.json", "caption.src.json")}
        cls.r = run(DRAFT + ["bundle", str(cls.d)])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, name):
        return (self.d / name).read_text(encoding="utf-8")

    def test_exit_zero_and_files(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)
        for n in ("spec.json", "check.json", "caption.txt", "compliance.json", f"{NAME}.mp4", f"{NAME}-cover.png",
                  "review.md", "record.json", "bundle.json"):
            self.assertTrue((self.d / n).is_file(), n)

    def test_steps_in_order_with_timing(self):
        b = json.loads(self.read("bundle.json"))
        self.assertEqual([s["name"] for s in b["steps"]],
                         ["expand", "check", "caption", "compliance", "render", "cover", "review"])
        self.assertTrue(all(s["status"] == "ok" for s in b["steps"]), b["steps"])
        self.assertEqual(b["status"], "complete")
        self.assertLess(b["elapsed_s"], 600)
        self.assertIsNone(b["request_started_at"])

    def test_compliance_headline_and_caption_finding(self):
        c = json.loads(self.read("compliance.json"))
        self.assertRegex(c["headline"], r"^위험 표현 \d+건 발견 · 규칙 v0\.1\(초안\) · 기준일 2026-10-29$")
        hits = [f for f in c["findings"] if "G-01" in f["rule"]]
        self.assertTrue(hits, c["findings"])
        self.assertEqual((hits[0]["doc"], hits[0]["where"]), ("caption", "caption line 1"))
        self.assertIn("수정 필요", c["counts_line"])

    def test_cover_is_scene_one_final_state(self):
        r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                 "-of", "csv=p=0", str(self.d / f"{NAME}-cover.png")])
        self.assertEqual(r.stdout.strip(), "1080,1920")
        spec = json.loads(self.read("spec.json"))
        t = 0.0
        for st in timeline.build_states(spec):
            if st.scene == 0 and st.k == len(st.lines):
                self.assertTrue(t <= timeline.cover_ms(spec) / 1000 < t + st.dur, (t, st.dur))
                break
            t += st.dur
        else:
            self.fail("scene 1 final state not found")

    def test_review_md(self):
        text = self.read("review.md")
        c = json.loads(self.read("compliance.json"))
        for need in ("초안 — 사람 검수 후 게시", c["headline"], "광고 해당 여부", "심의 상태", "심의번호", "미확인",
                     "수치 재확인", "기준일", "표지 크롭", "음원 라이선스", "개인정보"):
            self.assertIn(need, text)
        self.assertEqual(json.loads(self.read("record.json")), review.RECORD_DEFAULTS)

    def test_sources_unchanged(self):
        for n, data in self.before.items():
            self.assertEqual((self.d / n).read_bytes(), data, n)

    def test_forbidden_words_absent(self):
        for n in ("review.md", "compliance.json", "bundle.json"):
            text = self.read(n)
            self.assertNotIn("통과", text, n)
            self.assertIsNone(STATUTE_RE.search(text), n)
        self.assertNotIn("통과", self.r.stdout)
        self.assertIsNone(STATUTE_RE.search(self.r.stdout))

    def test_last_stdout_line(self):
        last = self.r.stdout.rstrip("\n").splitlines()[-1]
        self.assertRegex(last, rf"^bundle: {NAME} · ")

    def test_record_survives_rerun_helper(self):
        values, problem = review.ensure_record(self.d)
        self.assertIsNone(problem)
        self.assertEqual(values, review.RECORD_DEFAULTS)


class BadFolders(unittest.TestCase):
    def test_outside_drafts_and_bad_name(self):
        with tempfile.TemporaryDirectory() as t:
            outside = Path(t) / "2026-11-08-abc"
            outside.mkdir()
            r = run(DRAFT + ["bundle", str(outside)])
            self.assertEqual(r.returncode, 1)
            self.assertIn("초안 오류", r.stderr)
            bad = Path(t) / "drafts" / "x"
            bad.mkdir(parents=True)
            r = run(DRAFT + ["bundle", str(bad)])
            self.assertEqual(r.returncode, 1)
            self.assertIn("초안 오류", r.stderr)


if __name__ == "__main__":
    unittest.main()
