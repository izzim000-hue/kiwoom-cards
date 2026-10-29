"""수치 등록부 시험: 30개 id 시드, 검증 규칙, add/confirm, CLI (stdlib unittest 전용). 커밋된 등록부는 읽기만 한다."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import draft  # noqa: E402
from reelkit import figures  # noqa: E402
from reelkit.figures import RegistryError  # noqa: E402

EXPECTED_IDS = {
    "income_tax_rate_b1", "income_tax_rate_b2", "income_tax_rate_b3", "income_tax_rate_b4",
    "income_tax_rate_b5", "income_tax_rate_b6", "income_tax_rate_b7",
    "local_income_tax_ratio",
    "pension_credit_rate_low", "pension_credit_rate_high", "pension_credit_wage_threshold",
    "pension_credit_income_threshold", "pension_credit_limit_savings", "pension_credit_limit_total",
    "pension_credit_young_gov_proposal", "pension_credit_member_bill_irp", "pension_credit_member_bill_young",
    "interest_income_tax_rate",
    "nps_early_reduction_per_year", "nps_defer_increase_per_year", "nps_start_age_1969",
    "nps_avg_old_age_all", "nps_avg_old_age_20y",
    "retire_age_main_job", "pension_avg_55_79", "life_expectancy_2024", "cpi_yoy_2026_09",
    "sp500_2008_return", "sp500_long_run_avg", "rule_of_72",
}
UNSOURCED_TEXTS = {"남자 55.3세 · 여자 51.1세", "60세 여성은 약 88세까지", "소득세 최고세율 45% (10억 원 초과)"}


def committed():
    return json.loads(figures.REGISTRY_PATH.read_text(encoding="utf-8"))


def entry(**over):
    e = {
        "label": "예시 항목", "kind": "law", "value": "15", "unit": "%", "includes_local": False,
        "source": {"name": "소득세법", "url": None, "locator": None}, "candidate_sources": [],
        "as_of": "2026-10", "valid_until": None, "found_on": "2026-10-29", "checked_on": None, "checked_by": None,
        "legal_status": "시행", "verified": "미확인", "notes": "",
    }
    e.update(over)
    return e


def registry_with(fid="sample_x", **over):
    return {"schema": 1, "figures": {fid: entry(**over)}, "unsourced": []}


class CommittedRegistry(unittest.TestCase):
    def test_loads_with_exactly_the_30_documented_ids(self):
        reg = figures.load_registry()
        self.assertEqual(set(reg["figures"]), EXPECTED_IDS)
        self.assertEqual(len(reg["figures"]), 30)

    def test_every_entry_is_unconfirmed_with_no_checker(self):
        for fid, e in figures.load_registry()["figures"].items():
            with self.subTest(fid=fid):
                self.assertEqual(e["verified"], "미확인")
                self.assertIsNone(e["checked_on"])
                self.assertIsNone(e["checked_by"])

    def test_unsourced_figures_listed_but_not_usable(self):
        reg = figures.load_registry()
        self.assertEqual({u["text"] for u in reg["unsourced"]}, UNSOURCED_TEXTS)
        blob = json.dumps(reg["figures"], ensure_ascii=False)
        for text in UNSOURCED_TEXTS:
            self.assertNotIn(text, blob)
        self.assertNotIn("income_tax_rate_b8", reg["figures"])

    def test_proposals_carry_their_status_in_the_source_name(self):
        reg = figures.load_registry()["figures"]
        proposals = {k for k, v in reg.items() if v["legal_status"] == "발의"}
        self.assertEqual(proposals, {"pension_credit_young_gov_proposal", "pension_credit_member_bill_irp",
                                     "pension_credit_member_bill_young"})

    def test_values_documented_by_research(self):
        reg = figures.load_registry()
        self.assertEqual(str(figures.figure_value(reg, "interest_income_tax_rate")), "15.4")
        self.assertTrue(reg["figures"]["interest_income_tax_rate"]["includes_local"])
        self.assertEqual(str(figures.figure_value(reg, "sp500_2008_return")), "-37.0")
        self.assertEqual(reg["figures"]["rule_of_72"]["unit"], "")


class Validation(unittest.TestCase):
    def reject(self, data, *needles):
        with self.assertRaises(RegistryError) as cm:
            figures.validate_registry(data)
        for n in needles:
            self.assertIn(n, str(cm.exception))

    def test_valid_sample_passes(self):
        figures.validate_registry(registry_with())

    def test_confirmed_requires_checker_and_date(self):
        self.reject(registry_with(verified="확인"), "sample_x", "checked_on")
        self.reject(registry_with(verified="확인", checked_on="2026-10-30"), "checked_by")
        figures.validate_registry(registry_with(verified="확인", checked_on="2026-10-30", checked_by="홍길동"))

    def test_confirmed_by_claude_or_ai_rejected(self):
        for who in ("Claude", "claude-code", "AI", "assistant", "my-bot"):
            with self.subTest(who=who):
                self.reject(registry_with(verified="확인", checked_on="2026-10-30", checked_by=who), "확인자")

    def test_proposal_needs_marker_in_source_name(self):
        self.reject(registry_with(legal_status="발의"), "발의/개정안/정부안")
        for name in ("소득세법 개정안", "2026 세제개편안(정부안)", "의원 대표발의 법안"):
            figures.validate_registry(registry_with(legal_status="발의", source={"name": name, "url": None, "locator": None}))

    def test_bad_fields_rejected(self):
        self.reject(registry_with(value="abc"), "sample_x.value")
        self.reject(registry_with(value="NaN"), "sample_x.value")
        self.reject(registry_with(value=15), "sample_x.value")
        self.reject(registry_with(fid="Bad-Id"), "id")
        self.reject(registry_with(kind="Law"), "sample_x.kind")
        self.reject(registry_with(verified="confirmed"), "sample_x.verified")
        self.reject(registry_with(legal_status="시행중"), "sample_x.legal_status")
        self.reject(registry_with(unit="달러"), "sample_x.unit")
        self.reject(registry_with(as_of="26-10"), "sample_x.as_of")
        self.reject(registry_with(found_on="2026-13-40"), "sample_x.found_on")

    def test_unknown_and_missing_keys_rejected(self):
        self.reject(registry_with(extra="x"), "extra")
        data = registry_with()
        del data["figures"]["sample_x"]["notes"]
        self.reject(data, "notes")
        data = registry_with()
        data["extra"] = 1
        self.reject(data, "extra")

    def test_schema_and_unsourced_shape(self):
        data = registry_with()
        data["schema"] = 2
        self.reject(data, "schema")
        data = registry_with()
        data["unsourced"] = [{"text": "x"}]
        self.reject(data, "unsourced")

    def test_get_figure_suggests_ids(self):
        reg = figures.load_registry()
        with self.assertRaises(RegistryError) as cm:
            figures.get_figure(reg, "pension_credit_rate_lo")
        self.assertIn("pension_credit_rate_low", str(cm.exception))


class AddAndConfirm(unittest.TestCase):
    def fields(self, **over):
        f = {"label": "새 수치", "kind": "stat", "value": "12.5", "unit": "%",
             "source": {"name": "통계 보도"}, "legal_status": "시행"}
        f.update(over)
        return f

    def test_add_always_writes_unconfirmed(self):
        reg = copy.deepcopy(figures.load_registry())
        e = figures.add_figure(reg, "new_stat", self.fields(), "2026-11-01")
        self.assertEqual((e["verified"], e["checked_on"], e["checked_by"], e["found_on"]),
                         ("미확인", None, None, "2026-11-01"))
        self.assertIn("new_stat", reg["figures"])
        figures.validate_registry(reg)

    def test_add_cannot_set_verification_state(self):
        reg = copy.deepcopy(figures.load_registry())
        for key, val in (("verified", "확인"), ("checked_by", "홍길동"), ("checked_on", "2026-11-01")):
            with self.subTest(key=key):
                with self.assertRaises(RegistryError):
                    figures.add_figure(reg, "new_stat", self.fields(**{key: val}), "2026-11-01")
        self.assertNotIn("new_stat", reg["figures"])

    def test_add_refuses_existing_id_and_bad_value(self):
        reg = copy.deepcopy(figures.load_registry())
        with self.assertRaises(RegistryError) as cm:
            figures.add_figure(reg, "rule_of_72", self.fields(), "2026-11-01")
        self.assertIn("이미", str(cm.exception))
        with self.assertRaises(RegistryError):
            figures.add_figure(reg, "bad_value", self.fields(value="열두 점 오"), "2026-11-01")
        self.assertNotIn("bad_value", reg["figures"])

    def test_confirm_sets_the_three_fields(self):
        reg = copy.deepcopy(figures.load_registry())
        e = figures.confirm_figure(reg, "rule_of_72", " 홍길동 ", "2026-11-02")
        self.assertEqual((e["verified"], e["checked_on"], e["checked_by"]), ("확인", "2026-11-02", "홍길동"))

    def test_confirm_refuses_empty_and_ai_names(self):
        reg = copy.deepcopy(figures.load_registry())
        for who in ("", "   ", None, "Claude", "claude-code", "AI", "Claude Code"):
            with self.subTest(who=who):
                with self.assertRaises(RegistryError):
                    figures.confirm_figure(reg, "rule_of_72", who, "2026-11-02")
        self.assertEqual(reg["figures"]["rule_of_72"]["verified"], "미확인")

    def test_add_parser_has_no_verification_option(self):
        parser = draft.build_parser()
        fig = next(a for a in parser._subparsers._group_actions[0].choices["figures"]._subparsers._group_actions)
        add = fig.choices["add"]
        dests = {a.dest for a in add._actions}
        self.assertFalse({d for d in dests if "verif" in d or "check" in d or "confirm" in d}, dests)
        flags = {s for a in add._actions for s in a.option_strings}
        self.assertFalse({f for f in flags if "verif" in f or "check" in f}, flags)


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-figures-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.reg = self.tmp / "figures.json"
        shutil.copyfile(figures.REGISTRY_PATH, self.reg)
        self.committed_before = figures.REGISTRY_PATH.read_bytes()
        self.addCleanup(lambda: self.assertEqual(figures.REGISTRY_PATH.read_bytes(), self.committed_before))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(TOOLS / "draft.py"), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8")

    def test_list_on_committed_registry_prints_30_lines(self):
        r = self.run_cli("figures", "list")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(r.stdout.splitlines()), 30)

    def test_list_grep_filters_by_id(self):
        r = self.run_cli("figures", "list", "--grep", "pension", "--registry", self.reg)
        self.assertEqual(r.returncode, 0, r.stderr)
        ids = [ln.split()[0] for ln in r.stdout.splitlines()]
        self.assertTrue(ids)
        self.assertTrue(all(i.startswith("pension_") for i in ids), ids)

    def test_show_prints_json_and_unknown_id_exits_1(self):
        r = self.run_cli("figures", "show", "local_income_tax_ratio", "--registry", self.reg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["value"], "10")
        r = self.run_cli("figures", "show", "local_income_tax_rati", "--registry", self.reg)
        self.assertEqual(r.returncode, 1)
        self.assertIn("등록부 오류", r.stderr)
        self.assertIn("local_income_tax_ratio", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_add_then_duplicate_add_refused(self):
        args = ["figures", "add", "--registry", self.reg, "--id", "cli_new", "--label", "시험 수치", "--kind", "stat",
                "--value", "3.5", "--unit", "%", "--source-name", "시험 출처", "--legal-status", "시행",
                "--candidate-source", "후보 A", "--candidate-source", "후보 B", "--as-of", "2026-10"]
        r = self.run_cli(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        e = json.loads(self.reg.read_text(encoding="utf-8"))["figures"]["cli_new"]
        self.assertEqual((e["verified"], e["checked_by"]), ("미확인", None))
        self.assertEqual(e["candidate_sources"], ["후보 A", "후보 B"])
        r = self.run_cli(*args)
        self.assertEqual(r.returncode, 1)
        self.assertIn("등록부 오류", r.stderr)

    def test_add_rejects_verification_flag(self):
        r = self.run_cli("figures", "add", "--registry", self.reg, "--id", "x1", "--label", "l", "--kind", "stat",
                         "--value", "1", "--source-name", "s", "--legal-status", "시행", "--verified", "확인")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("x1", self.reg.read_text(encoding="utf-8"))

    def test_confirm_by_human_works_and_ai_name_refused(self):
        r = self.run_cli("figures", "confirm", "rule_of_72", "--by", "Claude", "--registry", self.reg)
        self.assertEqual(r.returncode, 1)
        self.assertIn("등록부 오류", r.stderr)
        r = self.run_cli("figures", "confirm", "rule_of_72", "--by", "", "--registry", self.reg)
        self.assertEqual(r.returncode, 1)
        r = self.run_cli("figures", "confirm", "rule_of_72", "--by", "홍길동", "--date", "2026-11-02", "--registry", self.reg)
        self.assertEqual(r.returncode, 0, r.stderr)
        e = json.loads(self.reg.read_text(encoding="utf-8"))["figures"]["rule_of_72"]
        self.assertEqual((e["verified"], e["checked_on"], e["checked_by"]), ("확인", "2026-11-02", "홍길동"))

    def test_confirm_help_marks_it_human_only(self):
        r = self.run_cli("figures", "--help")
        self.assertIn("사람 확인자 전용", r.stdout)


if __name__ == "__main__":
    unittest.main()
