"""slot.py 경계 시험: 잘못된 슬러그·날짜, 충돌, 날짜 제안 계산, 폴더 가둠 (stdlib unittest 전용)."""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from reelkit import slot  # noqa: E402

DRAFT = [sys.executable, str(TOOLS / "draft.py")]
BAD_SLUGS = ["../x", "A", "x_y", "x--y", "-x", "", "a" * 41]


def run_draft(*args):
    return subprocess.run(DRAFT + list(args), capture_output=True, text=True, encoding="utf-8")


def make_reels(root, used=()):
    """used: (날짜, 슬러그) 목록을 게시된 MP4 와 원고로 만든 임시 릴스 폴더."""
    reels = Path(root) / "reels"
    (reels / "specs").mkdir(parents=True)
    for d, s in used:
        (reels / f"{d}-{s}.mp4").write_bytes(b"")
        (reels / "specs" / f"{d}-{s}.json").write_text("{}", encoding="utf-8")
    return reels


class InvalidInput(unittest.TestCase):
    def test_bad_slugs_raise(self):
        for s in BAD_SLUGS:
            with self.subTest(slug=s):
                with self.assertRaises(slot.SlotError):
                    slot.check_slug(s)

    def test_bad_slugs_exit_1_via_cli(self):
        for s in BAD_SLUGS:
            with self.subTest(slug=s):
                r = run_draft("slot", f"--slug={s}")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("초안 오류", r.stderr)

    def test_forty_char_slug_ok(self):
        self.assertEqual(slot.check_slug("a" * 40), "a" * 40)

    def test_bad_date_exits_1(self):
        for d in ("2026-13-01", "2026-1-1", "내일"):
            with self.subTest(date=d):
                r = run_draft("slot", "--date", d, "--slug", "ok-slug")
                self.assertEqual(r.returncode, 1)
                self.assertIn("초안 오류", r.stderr)

    def test_create_needs_date_and_slug(self):
        r = run_draft("slot", "--slug", "ok-slug", "--create")
        self.assertEqual(r.returncode, 1)


class RealDirConflicts(unittest.TestCase):
    def before(self):
        drafts = REPO / "2026" / "reels" / "drafts"
        return sorted(p.name for p in drafts.glob("*")) if drafts.exists() else []

    def test_published_date_conflicts(self):
        info = slot.propose(date="2026-11-07", slug="brand-new-topic", today=date(2026, 10, 29))
        self.assertTrue(any(c.startswith("날짜 사용 중: 2026-11-07") for c in info["conflicts"]), info["conflicts"])
        self.assertTrue(info["ask"])

    def test_published_slug_conflicts(self):
        info = slot.propose(date="2027-01-01", slug="tax-deduction", today=date(2026, 10, 29))
        self.assertTrue(any(c.startswith("슬러그 사용 중: tax-deduction") for c in info["conflicts"]), info["conflicts"])

    def test_create_with_conflict_exits_1_and_creates_nothing(self):
        before = self.before()
        r = run_draft("slot", "--date", "2026-11-07", "--slug", "brand-new-topic", "--create")
        self.assertEqual(r.returncode, 1)
        self.assertIn("초안 오류", r.stderr)
        self.assertEqual(before, self.before())


class TempDirProposal(unittest.TestCase):
    def test_next_day_after_latest(self):
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t, [("2026-11-07", "a-b")])
            info = slot.propose(reels, slug="new-one", today=date(2026, 10, 29))
            self.assertEqual(info["proposed_date"], "2026-11-08")
            self.assertEqual(info["date"], "2026-11-08")
            self.assertTrue(info["ask"])
            self.assertEqual(info["conflicts"], [])

    def test_today_when_latest_is_older(self):
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t, [("2026-10-01", "a-b")])
            info = slot.propose(reels, slug="new-one", today=date(2026, 10, 29))
            self.assertEqual(info["proposed_date"], "2026-10-29")

    def test_empty_dir_proposes_today(self):
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t)
            self.assertEqual(slot.propose(reels, today=date(2026, 10, 29))["proposed_date"], "2026-10-29")

    def test_explicit_free_slot_does_not_ask(self):
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t, [("2026-11-07", "a-b")])
            info = slot.propose(reels, date="2026-11-09", slug="new-one", today=date(2026, 10, 29))
            self.assertFalse(info["ask"])
            self.assertEqual(info["conflicts"], [])

    def test_past_or_early_date_asks(self):
        # WR-05 회귀: 지난 날짜도 ask false 로 통과하던 문제
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t, [("2026-11-07", "a-b")])
            info = slot.propose(reels, date="2026-10-01", slug="new-one", today=date(2026, 10, 29))
            self.assertTrue(info["ask"])
            self.assertTrue(info["notices"][0].startswith("지난 날짜"), info["notices"])
            self.assertEqual(info["conflicts"], [])
            info = slot.propose(reels, date="2026-11-01", slug="new-one", today=date(2026, 10, 29))
            self.assertTrue(info["ask"])
            self.assertTrue(info["notices"][0].startswith("제안일보다 이른 날짜"), info["notices"])

    def test_other_year_in_a_year_folder_conflicts(self):
        with tempfile.TemporaryDirectory() as t:
            reels = Path(t) / "2026" / "reels"
            (reels / "specs").mkdir(parents=True)
            info = slot.propose(reels, date="2020-01-01", slug="old-date", today=date(2026, 10, 29))
            self.assertTrue(any(c.startswith("연도 불일치") for c in info["conflicts"]), info["conflicts"])
            with self.assertRaises(slot.SlotError):
                slot.create_draft_dir(reels, "2020-01-01", "old-date")
            self.assertFalse((reels / "drafts").exists())

    def test_real_dir_old_date_cannot_be_created(self):
        before = sorted(p.name for p in (REPO / "2026" / "reels" / "drafts").glob("*")) \
            if (REPO / "2026" / "reels" / "drafts").exists() else []
        r = run_draft("slot", "--date", "2020-01-01", "--slug", "old-date", "--create")
        self.assertEqual(r.returncode, 1)
        self.assertIn("연도 불일치", r.stderr)
        after = sorted(p.name for p in (REPO / "2026" / "reels" / "drafts").glob("*")) \
            if (REPO / "2026" / "reels" / "drafts").exists() else []
        self.assertEqual(before, after)

    def test_existing_draft_folder_conflicts(self):
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t)
            (reels / "drafts" / "2026-11-08-held-topic").mkdir(parents=True)
            info = slot.propose(reels, date="2026-11-08", slug="other-topic", today=date(2026, 10, 29))
            self.assertTrue(any("날짜 사용 중" in c for c in info["conflicts"]), info["conflicts"])
            info = slot.propose(reels, date="2026-11-20", slug="held-topic", today=date(2026, 10, 29))
            self.assertTrue(any("슬러그 사용 중" in c for c in info["conflicts"]), info["conflicts"])
            self.assertEqual(slot.propose(reels, today=date(2026, 10, 29))["proposed_date"], "2026-11-09")

    def test_create_stays_inside_drafts_and_second_create_fails(self):
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t)
            path = slot.create_draft_dir(reels, "2026-11-08", "pension-credit-limit")
            self.assertTrue(path.is_dir())
            self.assertTrue(path.is_relative_to((reels / "drafts").resolve()))
            with self.assertRaises(slot.SlotError):
                slot.create_draft_dir(reels, "2026-11-08", "pension-credit-limit")

    def test_create_refuses_path_like_slug(self):
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t)
            with self.assertRaises(slot.SlotError):
                slot.create_draft_dir(reels, "2026-11-08", "../escape")
            self.assertFalse((reels / "escape").exists())
            self.assertEqual(list((reels / "drafts").glob("*")) if (reels / "drafts").exists() else [], [])

    def test_cli_create_json(self):
        with tempfile.TemporaryDirectory() as t:
            reels = make_reels(t)
            r = run_draft("slot", "--reels-dir", str(reels), "--date", "2026-11-08", "--slug", "x1", "--create")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(json.loads(r.stdout)["created"])
            self.assertTrue((reels / "drafts" / "2026-11-08-x1").is_dir())


if __name__ == "__main__":
    unittest.main()
