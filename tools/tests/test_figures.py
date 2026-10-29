"""수치 등록부 시험: 30개 id 시드, 검증 규칙, add/confirm, CLI (stdlib unittest 전용). 커밋된 등록부는 읽기만 한다."""
import contextlib
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock
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
        e = figures.confirm_figure(reg, "rule_of_72", " 홍길동 ", "2026-11-02", today=date(2026, 11, 5))
        self.assertEqual((e["verified"], e["checked_on"], e["checked_by"]), ("확인", "2026-11-02", "홍길동"))

    def test_confirm_refuses_future_and_pre_discovery_dates(self):
        # WR-04 회귀: --date 2099-01-01 이 저장되던 문제
        reg = copy.deepcopy(figures.load_registry())
        found = reg["figures"]["rule_of_72"]["found_on"]
        for on, needle in (("2099-01-01", "미래"), ("2026-11-06", "미래"), ("2020-01-01", "발견일")):
            with self.subTest(on=on):
                with self.assertRaisesRegex(RegistryError, needle):
                    figures.confirm_figure(reg, "rule_of_72", "홍길동", on, today=date(2026, 11, 5))
        figures.confirm_figure(reg, "rule_of_72", "홍길동", found, today=date(2026, 11, 5))   # 발견일 당일은 가능

    def test_validate_rejects_checked_before_found(self):
        with self.assertRaisesRegex(RegistryError, "발견일"):
            figures.validate_registry(registry_with(verified="확인", checked_on="2026-10-01", checked_by="홍길동"))

    def test_confirm_refuses_empty_and_ai_names(self):
        reg = copy.deepcopy(figures.load_registry())
        for who in ("", "   ", None, "Claude", "claude-code", "AI", "Claude Code"):
            with self.subTest(who=who):
                with self.assertRaises(RegistryError):
                    figures.confirm_figure(reg, "rule_of_72", who, "2026-11-02", today=date(2026, 11, 5))
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

    def test_confirm_refused_without_a_terminal(self):
        # CR-05 회귀: Claude 의 Bash 처럼 터미널이 아닌 곳에서는 사람 이름으로도 확인할 수 없다
        before = self.reg.read_bytes()
        for who in ("홍길동", "Claude"):
            r = subprocess.run([sys.executable, str(TOOLS / "draft.py"), "figures", "confirm", "rule_of_72",
                                "--by", who, "--registry", str(self.reg)],
                               capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("대화형 터미널", r.stderr)
        r = subprocess.run([sys.executable, str(TOOLS / "draft.py"), "figures", "confirm", "rule_of_72",
                            "--by", "홍길동", "--registry", str(self.reg)],
                           capture_output=True, text=True, encoding="utf-8", input="rule_of_72\n")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.reg.read_bytes(), before)

    def confirm_in_terminal(self, typed, *extra):
        class FakeTty(io.StringIO):
            def isatty(self):
                return True
        argv = ["figures", "confirm", "rule_of_72", "--by", "홍길동", "--registry", str(self.reg), *extra]
        with mock.patch.object(draft.sys, "stdin", FakeTty()), mock.patch("builtins.input", return_value=typed), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            code = draft.main(argv)
        return code, err.getvalue()

    def test_confirm_in_terminal_needs_the_id_retyped(self):
        before = self.reg.read_bytes()
        code, err = self.confirm_in_terminal("rule_of_7")
        self.assertEqual(code, 1)
        self.assertIn("id 가 다름", err)
        self.assertEqual(self.reg.read_bytes(), before)
        code, err = self.confirm_in_terminal("rule_of_72", "--date", "2099-01-01")
        self.assertEqual((code, "미래" in err), (1, True), err)
        today = date.today().isoformat()
        code, err = self.confirm_in_terminal("rule_of_72")
        self.assertEqual(code, 0, err)
        e = json.loads(self.reg.read_text(encoding="utf-8"))["figures"]["rule_of_72"]
        self.assertEqual((e["verified"], e["checked_on"], e["checked_by"]), ("확인", today, "홍길동"))

    def hand_edit(self, **fields):
        data = json.loads(self.reg.read_text(encoding="utf-8"))
        data["figures"]["rule_of_72"].update(fields)
        self.reg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_hand_edited_future_confirmation_is_reported_by_list(self):
        # CR-05 회귀: figures.json 을 직접 고친 미래 확인일은 list 가 오류로 알린다
        self.hand_edit(verified="확인", checked_by="팀장", checked_on="2099-01-01")
        r = self.run_cli("figures", "list", "--registry", self.reg)
        self.assertEqual(r.returncode, 1)
        self.assertIn("rule_of_72", r.stderr)
        self.assertIn("2099-01-01", r.stderr)

    def test_hand_edited_confirmation_without_checker_fails_to_load(self):
        self.hand_edit(verified="확인", checked_on=date.today().isoformat())
        r = self.run_cli("figures", "list", "--registry", self.reg)
        self.assertEqual(r.returncode, 1)
        self.assertIn("checked_by", r.stderr)

    def test_confirmation_problems(self):
        data = registry_with(verified="확인", checked_on="2026-10-30", checked_by="홍길동")
        self.assertEqual(figures.confirmation_problems(data, date(2026, 10, 30)), [])
        self.assertEqual([fid for fid, _ in figures.confirmation_problems(data, date(2026, 10, 29))], ["sample_x"])
        data["figures"]["sample_x"]["checked_by"] = None
        self.assertTrue(figures.confirmation_problems(data, date(2026, 10, 30)))

    def test_confirm_help_marks_it_human_only(self):
        r = self.run_cli("figures", "--help")
        self.assertIn("사람 확인자 전용", r.stdout)


if __name__ == "__main__":
    unittest.main()
