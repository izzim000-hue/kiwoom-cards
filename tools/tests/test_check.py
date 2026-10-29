"""reelkit.check / draft.py check 시험: 장부 따라가기, 등록부 밖 숫자 오류, 확인 필요 표시 (stdlib unittest 전용)."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from reelkit import check, figures  # noqa: E402
from reelkit.expand import expand_source  # noqa: E402

FIXTURE = TOOLS / "tests" / "fixtures" / "draft-tax.src.json"
DRAFT = TOOLS / "draft.py"
NEEDS = ["scene 3 line 2", "scene 3 line 3", "scene 4 line 2", "scene 4 line 3"]


def kinds(issues):
    return [i.kind for i in issues]


def hand_typed(spec):
    """scene 6 line 2 의 0원을 장부 없이 손으로 적은 7원으로 바꾼 사본."""
    bad = copy.deepcopy(spec)
    bad["scenes"][5]["lines"][1] = "세액공제도 <g>7원</g>"
    bad["figures"] = [f for f in bad["figures"] if f["where"] != "scene 6 line 2"]
    return bad


class TracerBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = figures.load_registry()
        cls.src = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.spec = expand_source(cls.src, cls.registry)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-check-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_cli(self, *args):
        r = subprocess.run([sys.executable, str(DRAFT), "check", *map(str, args)],
                           capture_output=True, text=True, encoding="utf-8")
        return r

    def write(self, name, obj):
        p = self.tmp / name
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return p


class CleanDraft(TracerBase):
    def test_no_errors_and_needs_check_wheres(self):
        rep = check.check_spec(self.spec, self.registry)
        self.assertEqual(rep.errors, [])
        self.assertEqual([n["where"] for n in rep.needs_check], NEEDS)

    def test_needs_check_merges_ids_and_keeps_text(self):
        rep = check.check_spec(self.spec, self.registry)
        by = {n["where"]: n for n in rep.needs_check}
        self.assertIn("pension_credit_rate_low", by["scene 4 line 2"]["ids"])
        self.assertIn("pension_credit_rate_high", by["scene 4 line 2"]["ids"])
        self.assertEqual(by["scene 4 line 3"]["ids"], ["pension_credit_wage_threshold"])
        self.assertEqual(by["scene 3 line 2"]["reason"], "미확인 수치")
        self.assertEqual(by["scene 4 line 3"]["scene"], 4)

    def test_figures_used_sorted_unique(self):
        rep = check.check_spec(self.spec, self.registry)
        self.assertEqual(rep.figures_used, sorted(set(rep.figures_used)))
        self.assertIn("local_income_tax_ratio", rep.figures_used)

    def test_summary_never_says_tonggwa(self):
        rep = check.check_spec(self.spec, self.registry)
        self.assertEqual(rep.summary(), "오류 0건 · 경고 0건 · 확인 필요 4줄")
        self.assertNotIn("통과", rep.summary())


class Failures(TracerBase):
    def test_hand_typed_number_is_unregistered_error(self):
        rep = check.check_spec(hand_typed(self.spec), self.registry)
        self.assertEqual(kinds(rep.errors), ["UNREGISTERED"])
        err = rep.errors[0]
        self.assertEqual((err.where, err.scene, err.detail), ("scene 6 line 2", 6, "7원"))
        self.assertTrue(str(err).startswith("scene 6 line 2: UNREGISTERED (7원) "))

    def test_changed_text_with_ledger_kept_is_mismatch(self):
        bad = copy.deepcopy(self.spec)
        bad["scenes"][2]["lines"][1] = "6.7% → 6.6만"
        rep = check.check_spec(bad, self.registry)
        self.assertIn(("LEDGER_MISMATCH", "scene 3 line 2"), [(e.kind, e.where) for e in rep.errors])

    def test_missing_version_is_not_expanded(self):
        bad = copy.deepcopy(self.spec)
        del bad["version"]
        rep = check.check_spec(bad, self.registry)
        self.assertEqual(kinds(rep.errors), ["NOT_EXPANDED"])
        self.assertIn("draft.py expand", rep.errors[0].detail)

    def test_unknown_registry_id_in_ledger(self):
        bad = copy.deepcopy(self.spec)
        bad["figures"][2]["sources"] = ["fig.no_such_figure"]
        rep = check.check_spec(bad, self.registry)
        self.assertIn(("UNKNOWN_FIG", "no_such_figure"), [(e.kind, e.detail) for e in rep.errors])

    def test_ledger_pointing_nowhere_is_mismatch(self):
        bad = copy.deepcopy(self.spec)
        bad["figures"][0]["where"] = "scene 99 line 1"
        rep = check.check_spec(bad, self.registry)
        self.assertIn("LEDGER_MISMATCH", kinds(rep.errors))


class Cli(TracerBase):
    def test_clean_draft_exit_0_and_check_json(self):
        spec = self.write("spec.json", self.spec)
        out = self.tmp / "check.json"
        r = self.run_cli(spec, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.strip().splitlines()[-1].startswith("check: 오류 0건"))
        self.assertIn('확인 필요: scene 3 line 2 [', r.stdout)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual([n["where"] for n in doc["needs_check"]], NEEDS)
        self.assertEqual(doc["errors"], [])
        self.assertEqual(doc["mode"], "draft")
        self.assertEqual(doc["registry"]["schema"], 1)
        self.assertNotIn("통과", doc["summary"])

    def test_hand_typed_number_exit_1_names_location_no_traceback(self):
        spec = self.write("bad.json", hand_typed(self.spec))
        out = self.tmp / "check.json"
        r = self.run_cli(spec, "--out", out)
        self.assertEqual(r.returncode, 1)
        self.assertIn("scene 6 line 2: UNREGISTERED (7원)", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        doc = json.loads(out.read_text(encoding="utf-8"))   # 오류가 있어도 check.json 은 쓴다
        self.assertEqual(doc["errors"][0]["kind"], "UNREGISTERED")

    def test_unreadable_spec_is_input_error_exit_1(self):
        r = self.run_cli(self.tmp / "missing.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("원고 오류", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
