"""reelkit.check / draft.py check 시험: 장부 따라가기, 등록부 밖 숫자 오류, 확인 필요 표시 (stdlib unittest 전용)."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from reelkit import check, expand, figures  # noqa: E402
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
        self.assertEqual(rep.summary(), "오류 0건 · 경고 0건 · 확인 필요 4줄 · 가정 수치 7줄")
        self.assertNotIn("통과", rep.summary())


class Failures(TracerBase):
    def test_hand_typed_number_is_unregistered_error(self):
        rep = check.check_spec(hand_typed(self.spec), self.registry)
        self.assertEqual(kinds(rep.errors), ["UNREGISTERED"])
        err = rep.errors[0]
        self.assertEqual((err.where, err.scene, err.detail), ("scene 6 line 2", 6, "7원"))
        self.assertTrue(str(err).startswith("scene 6 line 2: UNREGISTERED (7원) "))

    def test_hangul_number_words_are_unregistered(self):
        # CR-04 회귀: 숫자 없이 쓴 금액·배수·전망 연도도 등록부 밖 숫자다
        for line in ("천만 원 모으기", "세금이 두 배", "절반으로 줄어요", "2055년 기금 고갈", "300 대비 늘어"):
            spec = plain()
            spec["scenes"][4]["lines"][2] = line
            with self.subTest(line=line):
                self.assertEqual(kinds(check.check_spec(spec, self.registry).errors), ["UNREGISTERED"])

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
        entry = next(e for e in bad["figures"] if e["where"] == "scene 4 line 3")
        entry["ref"] = "fig.no_such_figure"
        rep = check.check_spec(bad, self.registry)
        self.assertIn(("UNKNOWN_FIG", "no_such_figure"), [(e.kind, e.detail) for e in rep.errors])

    def test_edited_ledger_sources_are_not_trusted(self):
        bad = copy.deepcopy(self.spec)
        bad["figures"][2]["sources"] = ["fig.no_such_figure"]
        self.assertIn("LEDGER_MISMATCH", kinds(check.check_spec(bad, self.registry).errors))

    def test_literal_unit_after_ledger_span_is_error(self):
        # CR-03 회귀: 장부 구간("900만") 뒤에 손으로 "원" 을 붙여도 check 가 잡는다
        spec = expand_lines(self.registry, ["{{fig.pension_credit_limit_total|man}}까지"])
        spec["scenes"][0]["lines"][0] = "900만 원까지"
        rep = check.check_spec(spec, self.registry)
        self.assertIn("UNIT_AFTER", kinds(rep.errors))

    def test_ledger_pointing_nowhere_is_mismatch(self):
        bad = copy.deepcopy(self.spec)
        bad["figures"][0]["where"] = "scene 99 line 1"
        rep = check.check_spec(bad, self.registry)
        self.assertIn("LEDGER_MISMATCH", kinds(rep.errors))


class ForgedLedger(TracerBase):
    """CR-01 회귀: check 는 원고 속 장부를 믿지 않고 ref·fmt 를 지금 등록부로 다시 계산한다."""

    def errors_of(self, spec, registry=None):
        return check.check_spec(spec, registry or self.registry).errors

    def test_forged_entry_with_empty_sources_does_not_hide_a_number(self):
        # 리뷰 재현 1: 손으로 쓴 "500만 원" 옆에 sources [] 장부를 붙이면 예전에는 오류 0건
        bad = copy.deepcopy(self.spec)
        bad["scenes"][4]["lines"][2] = "500만 원 차이"
        bad["figures"].append({"where": "scene 5 line 3", "start": 0, "end": 6, "text": "500만 원", "sources": []})
        got = kinds(self.errors_of(bad))
        self.assertIn("LEDGER_FORGED", got)
        self.assertIn("UNREGISTERED", got)

    def test_forged_entry_with_a_real_ref_but_other_text(self):
        bad = copy.deepcopy(self.spec)
        bad["scenes"][4]["lines"][2] = "500만 원 차이"
        bad["figures"].append({"where": "scene 5 line 3", "scene": 5, "start": 0, "end": 6, "text": "500만 원",
                               "ref": "inputs.amt", "fmt": "man_won", "value": "5000000", "exact": True,
                               "sources": ["inputs.amt"]})
        self.assertIn("STALE_FIGURE", kinds(self.errors_of(bad)))

    def test_text_and_ledger_edited_together(self):
        # 리뷰 재현 2: 줄의 16.5만 과 장부 text 를 함께 99.9만 으로 고침
        bad = copy.deepcopy(self.spec)
        line = bad["scenes"][3]["lines"][1]
        self.assertIn("16.5만", line)
        bad["scenes"][3]["lines"][1] = line.replace("16.5만", "99.9만")
        entry = next(e for e in bad["figures"] if e["where"] == "scene 4 line 2" and e["text"] == "16.5만")
        entry["text"] = "99.9만"
        errs = self.errors_of(bad)
        self.assertIn(("STALE_FIGURE", "scene 4 line 2"), [(e.kind, e.where) for e in errs])

    def test_registry_value_change_makes_old_spec_fail(self):
        # 리뷰 재현 3: 등록부 값이 바뀌면 예전 spec.json 은 통과하면 안 된다
        reg = copy.deepcopy(self.registry)
        reg["figures"]["pension_credit_wage_threshold"]["value"] = "56000000"
        errs = self.errors_of(self.spec, reg)
        self.assertIn(("STALE_FIGURE", "scene 4 line 3"), [(e.kind, e.where) for e in errs])
        spec = expand_lines(self.registry, ["평균 {{fig.nps_avg_old_age_all|man_won}}"])
        reg = copy.deepcopy(self.registry)
        reg["figures"]["nps_avg_old_age_all"]["value"] = "698000"
        # 화면 글자는 여전히 "70만 원" 이지만 장부 value(700000)가 다시 계산한 값과 달라 오류
        self.assertIn("LEDGER_MISMATCH", kinds(self.errors_of(spec, reg)))

    def test_ledger_value_field_edited(self):
        bad = copy.deepcopy(self.spec)
        bad["figures"][0]["value"] = "2000000"
        self.assertIn("LEDGER_MISMATCH", kinds(self.errors_of(bad)))

    def test_input_ref_not_declared_in_spec_inputs(self):
        bad = copy.deepcopy(self.spec)
        del bad["inputs"]["no_tax"]
        got = kinds(self.errors_of(bad))
        self.assertIn("LEDGER_REF", got)
        self.assertIn("UNREGISTERED", got)

    def test_edited_input_value_is_recomputed(self):
        bad = copy.deepcopy(self.spec)
        bad["inputs"]["amt"]["value"] = "2000000"
        self.assertIn("STALE_FIGURE", kinds(self.errors_of(bad)))

    def test_basis_items_edited_or_stale(self):
        bad = copy.deepcopy(self.spec)
        bad["basis_items"][0]["verified"] = "확인"
        self.assertIn("BASIS_ITEMS", kinds(self.errors_of(bad)))
        reg = copy.deepcopy(self.registry)
        reg["figures"]["income_tax_rate_b1"]["as_of"] = "2026-11"
        self.assertIn("BASIS_ITEMS", kinds(self.errors_of(self.spec, reg)))

    def test_missing_derive_cannot_be_recomputed(self):
        bad = copy.deepcopy(self.spec)
        del bad["derive"]
        self.assertIn("LEDGER_REF", kinds(self.errors_of(bad)))

    def test_clean_spec_still_clean(self):
        self.assertEqual(self.errors_of(self.spec), [])

    def test_source_comparison(self):
        self.assertEqual(check.compare_source(self.spec, self.src, self.registry), [])
        bad = copy.deepcopy(self.spec)
        bad["scenes"][1]["lines"][0] = "소득공제는 손으로 고침"
        self.assertEqual(kinds(check.compare_source(bad, self.src, self.registry)), ["SOURCE_MISMATCH"])
        reg = copy.deepcopy(self.registry)
        reg["figures"]["income_tax_rate_b1"]["value"] = "7"
        self.assertEqual(kinds(check.compare_source(self.spec, self.src, reg)), ["SOURCE_MISMATCH"])

    def test_cli_uses_sibling_source(self):
        (self.tmp / "spec.src.json").write_text(json.dumps(self.src, ensure_ascii=False), encoding="utf-8")
        bad = copy.deepcopy(self.spec)
        bad["scenes"][1]["lines"][0] = "소득공제는 손으로 고침"
        spec = self.write("spec.json", bad)
        out = self.tmp / "check.json"
        r = self.run_cli(spec, "--out", out)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("SOURCE_MISMATCH", r.stderr)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["source"], str(self.tmp / "spec.src.json"))
        self.write("spec.json", self.spec)
        self.assertEqual(self.run_cli(spec).returncode, 0)


class RegistryConfirmations(TracerBase):
    """CR-05 회귀: 등록부를 직접 고쳐 만든 잘못된 `확인` 은 check 가 오류로 알린다."""

    def test_future_confirmation_in_registry_is_error(self):
        reg = copy.deepcopy(self.registry)
        reg["figures"]["rule_of_72"].update(verified="확인", checked_by="팀장", checked_on="2099-01-01")
        rep = check.check_spec(self.spec, reg)
        self.assertEqual([(e.kind, e.detail[:10]) for e in rep.errors], [("REGISTRY_CONFIRM", "rule_of_72")])

    def test_confirmation_without_checker_is_error(self):
        reg = copy.deepcopy(self.registry)
        reg["figures"]["rule_of_72"].update(verified="확인", checked_by=None, checked_on="2026-10-29")
        self.assertIn("REGISTRY_CONFIRM", kinds(check.check_spec(self.spec, reg).errors))

    def test_cli_exit_1_for_hand_edited_registry(self):
        reg = copy.deepcopy(self.registry)
        reg["figures"]["rule_of_72"].update(verified="확인", checked_by="팀장", checked_on="2099-01-01")
        r = self.run_cli(self.write("spec.json", self.spec), "--registry", self.write("reg.json", reg))
        self.assertEqual(r.returncode, 1)
        self.assertIn("REGISTRY_CONFIRM", r.stderr)
        reg["figures"]["rule_of_72"]["checked_by"] = None   # 로드 단계에서 거부
        r = self.run_cli(self.write("spec.json", self.spec), "--registry", self.write("reg.json", reg))
        self.assertEqual(r.returncode, 1)
        self.assertIn("등록부 오류", r.stderr)


class Assumptions(TracerBase):
    """CR-02 회귀: inputs 는 화면에 예시·가정으로 보여야 하고, check.json 에 따로 적히며, 비율은 inputs 로 못 쓴다."""

    def test_hand_typed_rate_as_input_is_refused(self):
        # 리뷰 재현: "rate": 16.5 % 세율 예시 -> 예전에는 오류·경고 0건, 확인 필요에도 없음
        src = {"inputs": {"rate": {"value": "16.5", "unit": "%", "label": "세율 예시"}},
               "scenes": [{"top": "t", "lines": ["세액공제율 <g>{{inputs.rate|pct}}</g>"]}]}
        with self.assertRaises(expand.ExpandError) as cm:
            expand_source(src, self.registry)
        self.assertIn("비율(%)", str(cm.exception))

    def test_rate_made_only_from_inputs_is_refused(self):
        src = {"inputs": {"g": {"value": "165", "unit": "원", "label": "예시"},
                          "p": {"value": "1000", "unit": "원", "label": "예시"}},
               "derive": {"r": {"fn": "yield_pct", "args": ["inputs.g", "inputs.p"]}},
               "scenes": [{"top": "t", "lines": ["세율 예시 {{r|pct}}"]}]}
        with self.assertRaises(expand.ExpandError) as cm:
            expand_source(src, self.registry)
        self.assertIn("fig.", str(cm.exception))

    def test_input_rate_smuggled_into_spec_fails_check(self):
        bad = copy.deepcopy(self.spec)
        bad["inputs"]["rate"] = {"value": "16.5", "unit": "%", "label": "세율 예시"}
        self.assertIn("DERIVE", kinds(check.check_spec(bad, self.registry).errors))

    def test_unmarked_input_line_is_error(self):
        spec = expand_lines(self.registry, ["세액공제 {{inputs.amt|man_won}}"],
                            inputs={"amt": {"value": "1000000", "unit": "원", "label": "공제 예시"}})
        rep = check.check_spec(spec, self.registry)
        self.assertEqual([(e.kind, e.detail) for e in rep.errors], [("ASSUMPTION_UNMARKED", "inputs.amt")])
        self.assertEqual([a["where"] for a in rep.assumptions], ["scene 1 line 1"])

    def test_marked_on_line_or_basis_is_listed_not_blocked(self):
        inputs = {"amt": {"value": "1000000", "unit": "원", "label": "공제 예시"}}
        for lines, basis in ((["예시: 공제 {{inputs.amt|man_won}}"], None),
                             (["공제 {{inputs.amt|man_won}}"], "가정 · 지방소득세 포함")):
            spec = expand_lines(self.registry, lines, basis=basis, inputs=inputs)
            rep = check.check_spec(spec, self.registry)
            self.assertEqual(rep.errors, [], lines)
            self.assertEqual(rep.assumptions[0]["inputs"], ["inputs.amt"])
            self.assertEqual(rep.assumptions[0]["labels"], ["공제 예시"])

    def test_derived_from_input_counts_as_assumption(self):
        rep = check.check_spec(self.spec, self.registry)
        by = {a["where"]: a for a in rep.assumptions}
        self.assertEqual(by["scene 4 line 2"]["inputs"], ["inputs.amt"])
        self.assertEqual(by["scene 6 line 2"]["inputs"], ["inputs.no_tax"])
        self.assertNotIn("scene 4 line 3", by)   # 등록부 수치만 쓴 줄

    def test_cli_prints_and_writes_assumptions(self):
        spec = self.write("spec.json", self.spec)
        out = self.tmp / "check.json"
        r = self.run_cli(spec, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("가정 수치: scene 6 line 2 [inputs.no_tax]", r.stdout)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["assumptions"]), 7)


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


# ---- Task 2: 상태 규칙, 마크업, 경고, 하우스 패턴, --legacy ------------------------------------------------

def house_scenes():
    """하우스 패턴을 지키는 7장면 (숫자 없음, 26.05초)."""
    return [
        {"top": "연말정산 바로 알기", "lines": ["소득공제 vs 세액공제", "<g>뭐가 더 유리할까?</g>"]},
        {"top": "비유하면", "lines": ["소득공제는", "<g>가격표 깎기</g>", "세액공제는", "<g>계산대 쿠폰</g>"]},
        {"top": "소득공제", "lines": ["세율만큼 줄어요", "높은 구간일수록 커요", "<g>그래서 유리해요</g>"]},
        {"top": "세액공제", "lines": ["세율과 상관없이", "<g>같은 비율로 깎아요</g>", "<s>총급여 기준이 있어요</s>"]},
        {"top": "그래서", "lines": ["낮은 구간은 <g>세액공제</g>", "높은 구간은 <g>소득공제</g>", "효과가 커지는 편"]},
        {"top": "단, 꼭 알아둘 것", "lines": ["낼 세금이 없으면", "세액공제도 <g>효과 없음</g>", "<s>세무 판단은 세무사 확인</s>"]},
        {"top": "", "lines": ["저장해두고", "내 세율 구간부터", "확인해 보세요", "<s>프로필 링크 · 1분 노후자금 계산기</s>"]},
    ]


def plain(scenes=None, **extra):
    spec = {"version": 2, "scenes": scenes if scenes is not None else house_scenes(), "figures": []}
    spec.update(extra)
    return spec


def expand_lines(registry, lines, basis=None, inputs=None, derive=None):
    src = {"scenes": [{"top": "t", "lines": lines}]}
    if basis is not None:
        src["basis"] = basis
    if inputs:
        src["inputs"] = inputs
    if derive:
        src["derive"] = derive
    return expand_source(src, registry)


class StatusRules(TracerBase):
    def test_proposed_figure_without_marker_is_error(self):
        spec = expand_lines(self.registry, ["청년은 {{fig.pension_credit_young_gov_proposal|pct0}}"])
        rep = check.check_spec(spec, self.registry)
        self.assertEqual([(e.kind, e.where, e.detail) for e in rep.errors],
                         [("PROPOSED_AS_FACT", "scene 1 line 1", "pension_credit_young_gov_proposal")])

    def test_proposed_figure_with_marker_on_line_is_listed_not_blocked(self):
        spec = expand_lines(self.registry, ["정부안 {{fig.pension_credit_young_gov_proposal|pct0}}"])
        rep = check.check_spec(spec, self.registry)
        self.assertEqual(rep.errors, [])
        self.assertEqual([n["where"] for n in rep.needs_check], ["scene 1 line 1"])

    def test_proposed_figure_with_marker_in_basis_is_ok(self):
        spec = expand_lines(self.registry, ["청년은 {{fig.pension_credit_young_gov_proposal|pct0}}"],
                            basis="발의안 기준 · 심의 중")
        self.assertEqual(check.check_spec(spec, self.registry).errors, [])

    def test_proposed_marker_variants(self):
        for word in ("발의안", "개정안", "정부안", "시행 전"):
            spec = expand_lines(self.registry, [f"{word} {{{{fig.pension_credit_young_gov_proposal|pct0}}}}"])
            self.assertEqual(check.check_spec(spec, self.registry).errors, [], word)

    def test_repealed_figure_is_always_error(self):
        reg = copy.deepcopy(self.registry)
        reg["figures"]["income_tax_rate_b1"]["legal_status"] = "폐지"
        rep = check.check_spec(self.spec, reg)
        self.assertEqual([(e.kind, e.where) for e in rep.errors if e.kind == "REPEALED"],
                         [("REPEALED", "scene 3 line 2")])

    def test_repealed_is_error_even_with_marker(self):
        reg = copy.deepcopy(self.registry)
        reg["figures"]["income_tax_rate_b1"]["legal_status"] = "폐지"
        spec = expand_lines(reg, ["발의안 {{fig.income_tax_rate_b1|pct0}}"])
        self.assertIn("REPEALED", kinds(check.check_spec(spec, reg).errors))


class MarkupAndPlaceholder(TracerBase):
    def test_other_tags_are_markup_errors_all_collected(self):
        spec = plain()
        spec["scenes"][0]["lines"][0] = "줄바꿈<br>과 <b>굵게</b>"
        rep = check.check_spec(spec, self.registry)
        found = [(e.kind, e.detail) for e in rep.errors if e.kind == "MARKUP"]
        self.assertEqual([d for _, d in found][:1], ["<br>"])
        self.assertEqual(len(found), 3)   # <br>, <b>, </b>

    def test_allowed_tags_are_not_markup(self):
        self.assertEqual(kinds(check.check_spec(plain(), self.registry).errors), [])

    def test_markup_in_basis(self):
        spec = plain(basis="근거 <script>")
        rep = check.check_spec(spec, self.registry)
        self.assertEqual([(e.kind, e.where) for e in rep.errors], [("MARKUP", "basis")])

    def test_leftover_placeholder_is_error(self):
        spec = plain()
        spec["scenes"][2]["lines"][0] = "{{fig.x|pct}} 남음"
        rep = check.check_spec(spec, self.registry)
        self.assertIn(("PLACEHOLDER", "scene 3 line 1"), [(e.kind, e.where) for e in rep.errors])


class Warnings(TracerBase):
    def test_house_scenes_have_no_warnings_or_errors(self):
        rep = check.check_spec(plain(), self.registry)
        self.assertEqual((rep.errors, rep.warnings), ([], []))

    def test_approx_without_yak_warns_and_with_yak_does_not(self):
        bare = expand_lines(self.registry, ["평균 {{fig.sp500_long_run_avg|pct0}}"])
        self.assertIn("APPROX", kinds(check.check_spec(bare, self.registry).warnings))
        yak = expand_lines(self.registry, ["평균 약 {{fig.sp500_long_run_avg|pct0}}"])
        self.assertNotIn("APPROX", kinds(check.check_spec(yak, self.registry).warnings))
        yak_g = expand_lines(self.registry, ["평균 <g>약 {{fig.sp500_long_run_avg|pct0}}</g>"])
        self.assertNotIn("APPROX", kinds(check.check_spec(yak_g, self.registry).warnings))

    def test_exact_values_never_warn_approx(self):
        self.assertNotIn("APPROX", kinds(check.check_spec(self.spec, self.registry).warnings))

    def test_input_shadows_figure_names_the_id(self):
        spec = copy.deepcopy(self.spec)
        spec["inputs"]["pct"] = {"value": "55000000", "unit": "원", "label": "가정 예시"}
        rep = check.check_spec(spec, self.registry)
        w = [x for x in rep.warnings if x.kind == "INPUT_SHADOWS_FIG"]
        self.assertEqual(len(w), 1)
        self.assertIn("pension_credit_wage_threshold", w[0].detail)

    def test_input_with_other_unit_does_not_shadow(self):
        spec = copy.deepcopy(self.spec)
        spec["inputs"]["pct"] = {"value": "55000000", "unit": "세", "label": "가정 예시"}
        self.assertNotIn("INPUT_SHADOWS_FIG", kinds(check.check_spec(spec, self.registry).warnings))

    def test_expired_figure_warns_against_publish_date(self):
        reg = copy.deepcopy(self.registry)
        reg["figures"]["pension_credit_wage_threshold"]["valid_until"] = "2026-12-31"
        late = check.check_spec(self.spec, reg, publish_date=date(2027, 1, 2))
        self.assertEqual([(w.kind, w.where) for w in late.warnings if w.kind == "EXPIRED"],
                         [("EXPIRED", "scene 4 line 3")])
        early = check.check_spec(self.spec, reg, publish_date=date(2026, 12, 31))
        self.assertNotIn("EXPIRED", kinds(early.warnings))

    def test_local_tax_note_needed_when_basis_and_line_lack_it(self):
        spec = copy.deepcopy(self.spec)
        spec["basis"] = "100만 원"
        # 장부 구간(0..6) 은 그대로 맞는다
        rep = check.check_spec(spec, self.registry)
        wheres = [w.where for w in rep.warnings if w.kind == "LOCAL_TAX_NOTE"]
        self.assertEqual(wheres, ["scene 3 line 2", "scene 3 line 3", "scene 4 line 2"])

    def test_local_tax_note_satisfied_by_line_text(self):
        spec = copy.deepcopy(self.spec)
        spec["basis"] = "100만 원"
        spec["scenes"][2]["lines"][1] += " 지방소득세 포함"   # 장부 구간은 앞쪽이라 그대로 맞는다
        rep = check.check_spec(spec, self.registry)
        wheres = [w.where for w in rep.warnings if w.kind == "LOCAL_TAX_NOTE"]
        self.assertEqual(wheres, ["scene 3 line 3", "scene 4 line 2"])


class HousePattern(TracerBase):
    def kinds_of(self, scenes):
        return kinds(check.check_spec(plain(scenes), self.registry).warnings)

    def test_scene_count(self):
        self.assertIn("SCENES", self.kinds_of(house_scenes()[:5]))
        self.assertNotIn("SCENES", self.kinds_of(house_scenes()[:6]))
        self.assertIn("SCENES", self.kinds_of(house_scenes() + house_scenes()[1:4]))

    def test_duration(self):
        short = [{"top": "t%d" % i, "lines": ["가", "나"]} for i in range(7)]
        short[-1]["top"] = ""
        short[-1]["lines"] = ["가", "<s>프로필 링크</s>"]
        short[0]["lines"] = ["<g>가</g>", "나"]
        short[5]["top"] = "주의"
        got = self.kinds_of(short)
        self.assertIn("DURATION", got)
        self.assertNotIn("SCENES", got)
        longer = [dict(sc, lines=sc["lines"] + ["다", "라"][: max(0, 5 - len(sc["lines"]))]) for sc in house_scenes()]
        self.assertIn("DURATION", self.kinds_of(longer))

    def test_line_and_top_length(self):
        scenes = house_scenes()
        scenes[0]["lines"][0] = "가" * 22
        self.assertNotIn("LINE_LONG", self.kinds_of(scenes))
        scenes[0]["lines"][0] = "가" * 23
        self.assertIn("LINE_LONG", self.kinds_of(scenes))
        scenes = house_scenes()
        scenes[0]["top"] = "나" * 21
        self.assertNotIn("TOP_LONG", self.kinds_of(scenes))
        scenes[0]["top"] = "나" * 22
        self.assertIn("TOP_LONG", self.kinds_of(scenes))

    def test_length_ignores_tags(self):
        scenes = house_scenes()
        scenes[0]["lines"][1] = "<g>" + "가" * 22 + "</g>"
        self.assertNotIn("LINE_LONG", self.kinds_of(scenes))

    def test_lines_per_scene(self):
        scenes = house_scenes()
        scenes[1]["lines"] = ["<g>하나</g>"]
        self.assertIn("LINES", self.kinds_of(scenes))
        scenes = house_scenes()
        scenes[1]["lines"] = ["a", "b", "c", "d", "e", "f"]
        self.assertIn("LINES", self.kinds_of(scenes))

    def test_cta(self):
        scenes = house_scenes()
        scenes[-1]["top"] = "마무리"
        self.assertIn("NO_CTA", self.kinds_of(scenes))
        scenes = house_scenes()
        scenes[-1]["lines"] = ["저장해두고", "내 세율 구간부터"]
        self.assertIn("NO_CTA", self.kinds_of(scenes))

    def test_caution_scene(self):
        scenes = house_scenes()
        scenes[5]["top"] = "그리고"
        self.assertIn("NO_CAUTION", self.kinds_of(scenes))
        for word in ("단, 하나", "주의할 점", "알아둘 것"):
            scenes[5]["top"] = word
            self.assertNotIn("NO_CAUTION", self.kinds_of(scenes), word)

    def test_emphasis(self):
        scenes = [dict(sc, lines=[ln.replace("<g>", "").replace("</g>", "") for ln in sc["lines"]]) for sc in house_scenes()]
        self.assertIn("NO_EMPH", self.kinds_of(scenes))

    def test_legacy_report_has_no_structure_rules(self):
        spec = {"scenes": [{"top": "가" * 30, "lines": ["하나"]}]}
        rep = check.legacy_report(spec)
        self.assertEqual((rep.errors, rep.warnings), ([], []))


class CliModes(TracerBase):
    def test_strict_exit_codes(self):
        warn_only = plain()
        warn_only["scenes"] = warn_only["scenes"][:5]
        spec = self.write("warn.json", warn_only)
        self.assertEqual(self.run_cli(spec).returncode, 0)
        r = self.run_cli(spec, "--strict")
        self.assertEqual(r.returncode, 3)
        self.assertIn("SCENES", r.stderr)

    def test_strict_clean_tax_draft_exits_0(self):
        spec = self.write("tax.json", self.spec)
        self.assertEqual(self.run_cli(spec, "--strict").returncode, 0)

    def test_errors_beat_strict(self):
        self.assertEqual(self.run_cli(self.write("bad.json", hand_typed(self.spec)), "--strict").returncode, 1)

    def test_invalid_date_is_input_error(self):
        r = self.run_cli(self.write("tax.json", self.spec), "--date", "2026-13-40")
        self.assertEqual(r.returncode, 1)
        self.assertIn("원고 오류", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_date_makes_expired_warning(self):
        reg = copy.deepcopy(self.registry)
        reg["figures"]["pension_credit_wage_threshold"]["valid_until"] = "2026-12-31"
        regpath = self.write("reg.json", reg)
        spec = self.write("tax.json", self.spec)
        r = self.run_cli(spec, "--registry", regpath, "--date", "2027-01-02")
        self.assertEqual(r.returncode, 0)
        self.assertIn("EXPIRED", r.stderr)

    def test_spec_without_version_refused_unless_legacy(self):
        published = REPO / "2026" / "reels" / "specs" / "2026-10-26-tax-deduction.json"
        r = self.run_cli(published)
        self.assertEqual(r.returncode, 1)
        self.assertIn("NOT_EXPANDED", r.stderr)

    def test_legacy_reports_count_for_all_published_specs(self):
        specs = sorted((REPO / "2026" / "reels" / "specs").glob("*.json"))
        self.assertEqual(len(specs), 10)
        for path in specs:
            r = self.run_cli(path, "--legacy")
            self.assertEqual(r.returncode, 0, f"{path.name}: {r.stderr}")
            last = r.stdout.strip().splitlines()[-1]
            self.assertRegex(last, r"^check\(legacy\): 등록부 없음 \d+개 — 게시된 v1 원고는 고치지 않음$")
        r = self.run_cli(REPO / "2026" / "reels" / "specs" / "2026-10-26-tax-deduction.json", "--legacy")
        self.assertIn("등록부 없음 11개", r.stdout)

    def test_legacy_refused_for_v2_drafts(self):
        # WR-03 회귀: v2 초안에 손으로 쓴 숫자가 있어도 --legacy 로 종료 0 이 나던 문제
        bad = self.write("bad.json", hand_typed(self.spec))
        r = self.run_cli(bad, "--legacy")
        self.assertEqual(r.returncode, 1)
        self.assertIn("--legacy", r.stderr)
        no_version = hand_typed(self.spec)
        del no_version["version"]          # version 만 지워도 장부가 남아 있으면 거부
        r = self.run_cli(self.write("nov.json", no_version), "--legacy")
        self.assertEqual(r.returncode, 1)
        self.assertIn("figures", r.stderr)

    def test_legacy_writes_nothing_without_out(self):
        before = sorted(p.name for p in (REPO / "2026" / "reels" / "specs").iterdir())
        self.run_cli(REPO / "2026" / "reels" / "specs" / "2026-10-29-ebook-event.json", "--legacy")
        after = sorted(p.name for p in (REPO / "2026" / "reels" / "specs").iterdir())
        self.assertEqual(before, after)

    def test_legacy_out_json_mode(self):
        out = self.tmp / "legacy.json"
        r = self.run_cli(REPO / "2026" / "reels" / "specs" / "2026-10-29-ebook-event.json", "--legacy", "--out", out)
        self.assertEqual(r.returncode, 0)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual((doc["mode"], doc["errors"], doc["warnings"]), ("legacy", [], []))


if __name__ == "__main__":
    unittest.main()
