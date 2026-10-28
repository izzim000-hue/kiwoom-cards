"""golden 회귀(ENV-03) 시험: 기준 목록 무결성, 게시된 릴스 10편 재렌더 비교, 재현 불가 보고 (stdlib unittest 전용).

기준 목록(manifest.json)은 게시된 MP4 에서 한 번 뽑은 값이다. 렌더러 출력으로 다시 만들지 않는다.
"""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from reelkit import golden  # noqa: E402

NOT_REPRODUCIBLE = "2026-10-19-savings-interest"


def load_entries():
    data = json.loads(golden.MANIFEST.read_text(encoding="utf-8"))
    return data, {e["stem"]: e for e in data["entries"]}


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot():
    """2026/reels 와 2026/reels/specs 바로 아래 파일의 sha256 (drafts 같은 하위 폴더는 제외)."""
    snap = {}
    for d in (golden.REELS_DIR, golden.SPECS_DIR):
        for p in sorted(d.iterdir()):
            if p.is_file():
                snap[str(p.relative_to(REPO))] = file_sha(p)
    return snap


class GoldenManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.entries = load_entries()

    def test_threshold_constant_is_fixed_at_098(self):
        self.assertEqual(golden.SSIM_MIN, 0.98)
        self.assertEqual(self.data["ssim_min_threshold"], 0.98)
        self.assertEqual(golden.SCENE_THRESHOLD, 0.003)

    def test_eleven_entries_match_golden_stems(self):
        self.assertEqual(len(golden.GOLDEN_STEMS), 11)
        self.assertEqual(list(golden.GOLDEN_STEMS), sorted(golden.GOLDEN_STEMS))
        self.assertEqual([e["stem"] for e in self.data["entries"]], list(golden.GOLDEN_STEMS))

    def test_savings_interest_is_not_reproducible_with_d06_reason(self):
        e = self.entries[NOT_REPRODUCIBLE]
        self.assertEqual(e["status"], "not-reproducible")
        self.assertIn("D-06", e["reason"])
        self.assertEqual(e["frames"], 622)

    def test_other_ten_are_reproducible_legacy_with_states_minus_one_boundaries(self):
        repro = [e for e in self.data["entries"] if e["stem"] != NOT_REPRODUCIBLE]
        self.assertEqual(len(repro), 10)
        for e in repro:
            with self.subTest(stem=e["stem"]):
                self.assertEqual(e["status"], "reproducible")
                self.assertEqual(e["layout"], "legacy")
                self.assertEqual(len(e["boundaries"]), e["states"] - 1)

    def test_grounded_boundary_counts(self):
        expect = {"2026-10-19-rate-secret-1": 19, "2026-10-21-rate-secret-2": 18,
                  "2026-10-24-rate-secret-3": 18, "2026-10-26-tax-deduction": 21,
                  "2026-10-28-salary-two-owners-1": 16, "2026-10-29-ebook-event": 18,
                  "2026-10-31-salary-two-owners-2": 20, "2026-11-02-salary-two-owners-3": 20,
                  "2026-11-04-salary-two-owners-4": 19, "2026-11-07-salary-two-owners-5": 16}
        for stem, n in expect.items():
            self.assertEqual(len(self.entries[stem]["boundaries"]), n, stem)

    def test_tax_deduction_grounded_values(self):
        t = self.entries["2026-10-26-tax-deduction"]
        self.assertEqual(t["frames"], 781)
        self.assertEqual(t["boundaries"][:3], [25, 83, 108])
        self.assertEqual(t["stdout"], "duration=26.1s cover_ms=1250")
        self.assertEqual(t["video_duration"], "26.033333")
        self.assertEqual(t["audio_duration"], "26.050000")

    def test_expected_stdout_lines(self):
        expect = {"2026-10-19-rate-secret-1": "duration=24.3s cover_ms=1250",
                  "2026-10-21-rate-secret-2": "duration=23.5s cover_ms=1250",
                  "2026-10-24-rate-secret-3": "duration=23.5s cover_ms=1250",
                  "2026-10-29-ebook-event": "duration=23.5s cover_ms=1250",
                  "2026-10-28-salary-two-owners-1": "duration=21.8s cover_ms=1250",
                  "2026-11-07-salary-two-owners-5": "duration=21.8s cover_ms=1250",
                  "2026-10-31-salary-two-owners-2": "duration=25.2s cover_ms=1250",
                  "2026-11-02-salary-two-owners-3": "duration=25.2s cover_ms=2100",
                  "2026-11-04-salary-two-owners-4": "duration=24.3s cover_ms=1250"}
        for stem, line in expect.items():
            self.assertEqual(self.entries[stem]["stdout"], line, stem)

    def test_spec_hashes_match_committed_specs(self):
        for e in self.data["entries"]:
            if e["status"] != "reproducible":
                continue
            with self.subTest(stem=e["stem"]):
                self.assertEqual(e["spec_sha256"], file_sha(REPO / e["spec"]))

    def test_mp4_hashes_match_committed_mp4s(self):
        for e in self.data["entries"]:
            with self.subTest(stem=e["stem"]):
                self.assertEqual(e["mp4_sha256"], file_sha(REPO / e["mp4"]))


class GoldenUnitTest(unittest.TestCase):
    """렌더 없이 확인되는 판정과 보고 형식."""

    @classmethod
    def setUpClass(cls):
        cls.data, cls.entries = load_entries()

    def test_changed_published_mp4_hash_fails_without_rendering(self):
        e = copy.deepcopy(self.entries["2026-10-26-tax-deduction"])
        e["mp4_sha256"] = "0" * 64
        r = golden.check_reel(e)
        self.assertEqual(r.verdict, "FAIL")
        self.assertTrue(any("게시된 영상이 바뀜" in x for x in r.reasons), r.reasons)

    def test_changed_spec_hash_fails_without_rendering(self):
        e = copy.deepcopy(self.entries["2026-10-26-tax-deduction"])
        e["spec_sha256"] = "0" * 64
        r = golden.check_reel(e)
        self.assertEqual(r.verdict, "FAIL")
        self.assertTrue(any("원고가 바뀜" in x for x in r.reasons), r.reasons)

    def test_unlisted_mp4_is_listed_not_judged(self):
        d = Path(tempfile.mkdtemp(prefix="test-golden-"))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "2026-12-01-new-layout.mp4").write_bytes(b"x")
        (d / f"{NOT_REPRODUCIBLE}.mp4").write_bytes(b"x")
        (d / "note.png").write_bytes(b"x")
        extras = golden.unlisted_mp4s(self.data["entries"], d)
        self.assertEqual(extras, ["기준 목록 밖: 2026-12-01-new-layout (판정 안 함)"])

    def test_report_line_formats_and_last_line(self):
        ok = golden.ReelResult("2026-10-26-tax-deduction", "PASS",
                               {"frames": (781, 781), "boundaries": 21, "boundary_mismatch": None,
                                "cover_ms": 1250, "ssim_min": 0.993194, "spec": "PASS"}, [])
        bad = golden.ReelResult("2026-10-28-salary-two-owners-1", "FAIL",
                                {"frames": (655, 656), "boundaries": 16, "boundary_mismatch": 3,
                                 "cover_ms": 1250, "ssim_min": 0.9, "spec": "PASS"}, ["frames 655 != 656"])
        nr = golden.ReelResult(NOT_REPRODUCIBLE, "재현 불가", {"spec": "PASS"}, [])
        lines = golden.format_report([ok, bad, nr], ["기준 목록 밖: x (판정 안 함)"])
        self.assertIn("frames 781/781", lines[0])
        self.assertIn("SSIM 최소 0.9932", lines[0])
        self.assertTrue(lines[0].startswith("PASS"))
        self.assertTrue(lines[1].startswith("FAIL"))
        self.assertIn("  frames 655 != 656", lines[2])
        self.assertIn(f"재현 불가  {NOT_REPRODUCIBLE}  (원고 없음, D-06)  규격 PASS", lines)
        self.assertEqual(lines[-1], "golden: FAIL 1/2 (재현 불가 1)")
        self.assertIn("기준 목록 밖: x (판정 안 함)", lines)


class GoldenRenderTest(unittest.TestCase):
    """게시된 릴스를 legacy 배치로 다시 그려 기준과 비교한다. 릴스마다 시험 하나가 import 시점에 만들어진다."""

    @classmethod
    def setUpClass(cls):
        cls.before = snapshot()
        cls.data, cls.entries = load_entries()

    def test_not_reproducible_report(self):
        r = golden.check_reel(self.entries[NOT_REPRODUCIBLE])
        self.assertEqual(r.verdict, "재현 불가", r.reasons)
        self.assertEqual(r.reasons, [])
        self.assertEqual(r.details["spec"], "PASS")
        lines = golden.format_report([r], [])
        self.assertTrue(any(x.startswith(f"재현 불가  {NOT_REPRODUCIBLE}") and "규격 PASS" in x for x in lines), lines)

    def test_structural_mismatch_fails_with_reasons(self):
        """기준 값이 다르면 FAIL 이 나오고 이유가 한국어로 적힌다 (판정이 항상 PASS 가 아님을 확인)."""
        e = copy.deepcopy(self.entries["2026-10-28-salary-two-owners-1"])
        e["frames"] += 1
        e["boundaries"][2] += 1
        e["cover_ms"] += 1
        r = golden.check_reel(e)
        self.assertEqual(r.verdict, "FAIL")
        joined = " | ".join(r.reasons)
        for needle in ("프레임", "경계", "cover_ms"):
            self.assertIn(needle, joined)

    def test_zz_published_reels_untouched(self):
        self.assertEqual(snapshot(), self.before)


def _make_reel_test(stem):
    def test(self):
        r = golden.check_reel(self.entries[stem])
        self.assertEqual(r.verdict, "PASS", "; ".join(r.reasons))
    test.__name__ = "test_" + stem.replace("-", "_")
    return test


for _stem in golden.GOLDEN_STEMS:
    if _stem != NOT_REPRODUCIBLE:
        _t = _make_reel_test(_stem)
        setattr(GoldenRenderTest, _t.__name__, _t)


if __name__ == "__main__":
    unittest.main()
