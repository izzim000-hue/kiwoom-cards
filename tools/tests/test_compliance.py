"""금소법 표현 점검기: 규칙 읽기, 위치, 부정·인용 예외, 쪼갠 표현, 겹침 합치기, 근거 누락 규칙, 확인 필요 옮기기, draft.py compliance
(표준 라이브러리 unittest 전용, 렌더 없음)."""
import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
FIX = Path(__file__).resolve().parent / "fixtures"
DRAFT = [sys.executable, str(TOOLS / "draft.py")]
sys.path.insert(0, str(TOOLS))

from reelkit import compliance, expand, figures, golden  # noqa: E402

STATUTE_RE = re.compile(r"제\s*\d+\s*조")
RULES = compliance.load_rules()


def mk(*scenes, basis="", tops=None):
    """scenes: 줄 목록들. tops: 장면별 top (기본 빈 글자)."""
    tops = tops or [""] * len(scenes)
    return {"basis": basis, "scenes": [{"top": t, "lines": list(lines)} for t, lines in zip(tops, scenes)]}


def scan_reel(spec, rules=RULES):
    return compliance.scan(compliance.reel_doc(spec), rules)


def ids(findings):
    return [i for f in findings for i in f["rule"]]


def run_cli(*args):
    return subprocess.run(DRAFT + list(args), capture_output=True, text=True, encoding="utf-8")


class Locations(unittest.TestCase):
    def test_reel_locations(self):
        spec = mk(["안녕하세요"], ["첫째 줄", "무조건 오르는 종목"], basis="가입하세요", tops=["원금 보장", "", ""])
        found, _ = scan_reel(spec)
        where = {i: f["where"] for f in found for i in f["rule"]}
        self.assertEqual(where["G-01"], "scene 1 top")
        self.assertEqual(where["G-03"], "scene 2 line 2")
        self.assertEqual(where["S-01"], "basis")

    def test_scene_two_line_one(self):
        found, _ = scan_reel(mk(["안녕"], ["원금 보장이에요", "다음"]))
        self.assertEqual([f["where"] for f in found], ["scene 2 line 1"])
        self.assertEqual(found[0]["doc"], "reel")

    def test_caption_locations(self):
        text = "첫 줄\n\n• 요약\n• 둘째\n• 원금 보장 상품\n\n#연금저축 #무조건절세 #IRP\n"
        found, _ = compliance.scan(compliance.caption_doc(text), RULES)
        where = {i: f["where"] for f in found for i in f["rule"]}
        self.assertEqual(where["G-01"], "caption line 5")
        self.assertEqual(where["G-03"], "hashtag #2")

    def test_wrapped_line_is_one_finding_across_scenes_is_not(self):
        found, _ = scan_reel(mk(["이건 원금", "보장 상품"]))
        self.assertEqual(ids(found).count("G-01"), 1)
        found, _ = scan_reel(mk(["이건 원금"], ["보장 상품"]))
        self.assertNotIn("G-01", ids(found))


class Suppression(unittest.TestCase):
    def suppressed_ids(self, spec):
        found, sup = scan_reel(spec)
        return found, sup

    def test_negator(self):
        found, sup = scan_reel(mk(["원금 보장 아님"]))
        self.assertEqual(found, [])
        self.assertEqual(sup[0]["rule"], ["G-01"])
        self.assertEqual(sup[0]["by"], "negator")

    def test_window_crosses_line_break(self):
        found, sup = scan_reel(mk(["손실이 없다는 보장은", "어디에도 없어요"]))
        self.assertEqual(found, [])
        self.assertIn("G-05", ids(sup))

    def test_mention_marker(self):
        found, sup = scan_reel(mk(["'확정 수익'이라는 말은", "조심해서 보세요"]))
        self.assertEqual(found, [])
        self.assertEqual(sup[0]["by"], "mention")

    def test_except_at_start_and_mid_document(self):
        found, sup = scan_reel(mk(["반드시 세무사에게", "확인해 보세요"]))
        self.assertEqual(found, [])
        self.assertEqual((sup[0]["rule"], sup[0]["by"]), (["G-07"], "except"))
        found, sup = scan_reel(mk(["먼저 계산해 보세요.", "반드시 세무사에게 확인해 보세요"]))
        self.assertEqual(found, [])
        self.assertEqual(sup[0]["by"], "except")
        found, sup = scan_reel(mk(["끝났어요.반드시 세무사에게 확인"]))   # 구분 글자 바로 뒤 첫 글자가 잘리지 않아야 한다
        self.assertEqual(found, [])
        self.assertEqual(sup[0]["by"], "except")

    def test_sentence_stop_ends_window(self):
        found, _ = scan_reel(mk(["원금 보장 상품이에요. 손실은 걱정하지 않아도 돼요"]))
        self.assertIn("G-01", ids(found))

    def test_scene_boundary_ends_window(self):
        found, _ = scan_reel(mk(["이건 원금 보장"], ["않아도 돼요"]))
        self.assertIn("G-01", ids(found))

    def test_second_claim_flagged_first_listed_suppressed(self):
        found, sup = scan_reel(mk(["원금 보장되며 위험하지 않습니다"]))
        self.assertIn("G-05", ids(found))
        self.assertIn("G-01", ids(sup))


class CompactAndDedupe(unittest.TestCase):
    def test_spaced_term(self):
        found, _ = scan_reel(mk(["이건 원 금 보 장 상품"]))
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["rule"], found[0]["severity"], found[0]["kind"]),
                         (["X-compact"], "수정 필요", "compact"))

    def test_zero_width_term(self):
        found, _ = scan_reel(mk(["이건 원금​보장 상품"]))
        self.assertEqual(len(found), 1)
        self.assertIn("X-compact", found[0]["rule"])
        self.assertEqual(found[0]["severity"], "수정 필요")

    def test_negated_term_not_reflagged(self):
        found, sup = scan_reel(mk(["원금 보장 아님"]))
        self.assertEqual(found, [])
        self.assertEqual(len(sup), 1)

    def test_overlap_is_one_finding(self):
        found, _ = scan_reel(mk(["이렇게 하면 무조건 절세예요"]))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["category"], "세무 단정")
        self.assertIn("T-01", found[0]["rule"])
        self.assertIn("G-03", found[0]["rule"])


class Requires(unittest.TestCase):
    def run_spec(self, spec):
        return compliance.run(spec, None, RULES).findings

    def test_r02_tax_without_tax_advisor_line(self):
        spec = mk(["세액공제 한도는", "연 900만 원"], ["다음 이야기"], basis="2026년 기준 예시")
        f = [x for x in self.run_spec(spec) if "R-02" in x["rule"]]
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]["severity"], f[0]["kind"], f[0]["where"].split(" line")[0]),
                         ("확인 필요", "requires", "scene 1"))
        spec["scenes"][1]["lines"].append("<s>세무 판단은 세무사 확인</s>")
        self.assertEqual([x for x in self.run_spec(spec) if "R-02" in x["rule"]], [])

    def test_r01_past_performance(self):
        spec = mk(["과거 10년 평균 수익률은", "연 8%였어요"], basis="예시 기준")
        self.assertIn("R-01", ids(self.run_spec(spec)))
        spec["scenes"][0]["lines"].append("미래 보장 아님")
        self.assertNotIn("R-01", ids(self.run_spec(spec)))

    def test_r05_reel_only(self):
        spec = mk(["연 5% 수익률", "20년 모으면"], basis="")
        self.assertIn("R-05", ids(self.run_spec(spec)))
        spec["basis"] = "2026년 기준 예시"
        self.assertNotIn("R-05", ids(self.run_spec(spec)))
        res = compliance.run(mk(["안녕"]), "연 5% 수익률 100만 원\n", RULES)
        self.assertNotIn("R-05", [i for f in res.findings if f["doc"] == "caption" for i in f["rule"]])


class Lift(unittest.TestCase):
    def test_lift_entries(self):
        check = {"needs_check": [{"where": "scene 3 line 1", "ids": ["fig.a"], "text": "연 900만 원"}],
                 "assumptions": [{"where": "scene 4 line 2", "inputs": ["inputs.x"], "text": "월 100만 원"}],
                 "warnings": [{"where": "scene 1 top", "scene": 1, "kind": "HOUSE_LEN", "detail": "22자", "text": "긴 글"}]}
        res = compliance.run(mk(["안녕"]), None, RULES, check_json=check, caption_warnings=["첫 줄 60자"])
        lifted = {f["rule"][0]: f for f in res.findings if f["kind"] == "lift"}
        self.assertEqual(set(lifted), {"CHK-NEEDS", "CHK-ASSUME", "CHK-WARN", "CHK-CAPTION"})
        self.assertEqual(lifted["CHK-NEEDS"]["text"], "연 900만 원")
        self.assertEqual(lifted["CHK-NEEDS"]["where"], "scene 3 line 1")
        self.assertEqual(lifted["CHK-CAPTION"]["text"], "첫 줄 60자")
        self.assertTrue(all(f["severity"] == "확인 필요" for f in lifted.values()))
        self.assertEqual(res.counts["확인 필요"], 4)
        self.assertEqual(res.counts["위험 표현"], 0)


class Headline(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(compliance.headline(0, RULES),
                         "패턴상 발견 없음 — 사람 검수 필요 · 규칙 v0.1(초안) · 기준일 2026-10-29")
        res = compliance.run(mk(["무조건 오르는 종목", "100% 안전한 투자"]), None, RULES)
        self.assertEqual(res.counts["위험 표현"], 2)
        self.assertEqual(res.headline, "위험 표현 2건 발견 · 규칙 v0.1(초안) · 기준일 2026-10-29")

    def test_json_shape_and_words(self):
        res = compliance.run(mk(["원금 보장 아님", "무조건 오르는 종목"]), None, RULES)
        data = res.to_json()
        for key in ("schema", "rules", "headline", "counts_line", "counts", "findings", "suppressed", "limits"):
            self.assertIn(key, data)
        self.assertEqual(set(data["counts"]), {"수정 필요", "확인 필요", "위험 표현", "예외 제외"})
        self.assertRegex(data["counts_line"], r"^수정 필요 \d+건 · 확인 필요 \d+건 · 예외 처리로 제외 1건$")
        self.assertEqual(data["rules"]["sha256"], RULES.sha256)
        text = json.dumps(data, ensure_ascii=False)
        self.assertNotIn("통과", text)
        self.assertIsNone(STATUTE_RE.search(text))


class Loader(unittest.TestCase):
    def base(self):
        return json.loads(compliance.RULES_PATH.read_text(encoding="utf-8"))

    def load_data(self, data):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "rules.json"
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return compliance.load_rules(p)

    def rule(self, **kw):
        r = {"id": "U-01", "category": "단정·보장", "severity": "수정 필요", "pattern": "쿠폰 묶음",
             "reason": "시험", "suggest": "시험"}
        r.update(kw)
        return r

    def expect_error(self, mutate, needle):
        data = self.base()
        mutate(data)
        with self.assertRaises(compliance.RuleError) as cm:
            self.load_data(data)
        self.assertIn(needle, str(cm.exception))

    def test_duplicate_id(self):
        self.expect_error(lambda d: d["rules"].append(copy.deepcopy(d["rules"][0])), "G-01")

    def test_unknown_keys(self):
        self.expect_error(lambda d: d["rules"][0].update(bogus=1), "G-01")
        self.expect_error(lambda d: d.update(bogus=1), "bogus")

    def test_bad_severity_and_type(self):
        self.expect_error(lambda d: d["rules"].append(self.rule(severity="통과")), "U-01")
        self.expect_error(lambda d: d["rules"].append(self.rule(severity="높음")), "U-01")
        self.expect_error(lambda d: d["rules"].append(self.rule(type="magic")), "U-01")

    def test_bad_regex_empty_and_nested(self):
        self.expect_error(lambda d: d["rules"].append(self.rule(pattern="(쿠폰")), "U-01")
        self.expect_error(lambda d: d["rules"].append(self.rule(pattern="(?:쿠폰)?")), "U-01")
        self.expect_error(lambda d: d["rules"].append(self.rule(pattern="(a+)+b")), "U-01")

    def test_forbidden_strings(self):
        self.expect_error(lambda d: d["rules"].append(self.rule(reason="제 17 조에 따라")), "U-01")
        self.expect_error(lambda d: d["rules"].append(self.rule(suggest="점검 통과")), "U-01")

    def test_missing_top_fields(self):
        for key in ("version", "as_of", "status"):
            data = self.base()
            del data[key]
            with self.assertRaises(compliance.RuleError, msg=key):
                self.load_data(data)
        self.expect_error(lambda d: d.update(as_of="어제"), "as_of")

    def test_examples_are_executed(self):
        self.expect_error(lambda d: d["rules"].append(
            self.rule(examples={"hit": ["전혀 다른 문장"], "miss": []})), "U-01")
        self.expect_error(lambda d: d["rules"].append(
            self.rule(examples={"hit": ["쿠폰 묶음"], "miss": ["쿠폰 묶음이에요"]})), "U-01")
        self.load_data({**self.base(), "rules": self.base()["rules"] + [
            self.rule(examples={"hit": ["쿠폰 묶음"], "miss": ["쿠폰 한 장"]})]})

    def test_missing_file_message(self):
        with self.assertRaises(compliance.RuleError) as cm:
            compliance.load_rules(Path("/nonexistent/rules.json"))
        self.assertIn("규칙 파일", str(cm.exception))


class DataDriven(unittest.TestCase):
    def test_new_rule_takes_effect_without_code_change(self):
        registry = figures.load_registry(figures.REGISTRY_PATH)
        src = json.loads((FIX / "draft-pension.src.json").read_text(encoding="utf-8"))
        spec = expand.expand_source(src, registry)
        data = json.loads(compliance.RULES_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "rules.json"
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            before = compliance.run(spec, None, compliance.load_rules(p)).findings
            self.assertNotIn("U-01", ids(before))
            data["rules"].append({"id": "U-01", "category": "상품 권유", "severity": "수정 필요",
                                  "pattern": "쿠폰 묶음", "reason": "시험 규칙", "suggest": "시험"})
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            after = compliance.run(spec, None, compliance.load_rules(p)).findings
            hit = [f for f in after if "U-01" in f["rule"]]
            self.assertEqual([f["where"] for f in hit], ["scene 2 line 2"])
            data["rules"].pop()
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.assertNotIn("U-01", ids(compliance.run(spec, None, compliance.load_rules(p)).findings))


class ShippedData(unittest.TestCase):
    def test_every_pattern_rule_has_examples(self):
        for rule in RULES.rules:
            if rule.type == "pattern":
                with self.subTest(rule=rule.id):
                    self.assertTrue(rule.examples.get("hit"), rule.id)
                    self.assertTrue(rule.examples.get("miss"), rule.id)

    def test_published_reels_have_no_must_fix(self):
        entries = [e for e in golden.load_manifest()["entries"] if e["status"] == "reproducible"]
        self.assertEqual(len(entries), 10)
        for e in entries:
            with self.subTest(stem=e["stem"]):
                spec = json.loads((REPO / e["spec"]).read_text(encoding="utf-8"))
                res = compliance.run(spec, None, RULES)
                self.assertEqual(res.counts["수정 필요"], 0, [f for f in res.findings if f["severity"] == "수정 필요"])

    def test_caption_config_is_clean(self):
        cfg = json.loads((TOOLS / "data" / "caption_config.json").read_text(encoding="utf-8"))
        text = f"{cfg['disclaimer']}\n\n{cfg['cta']}\n"
        found, sup = compliance.scan(compliance.caption_doc(text), RULES)
        self.assertEqual(found, [])

    def test_no_forbidden_words_in_rules_file(self):
        text = compliance.RULES_PATH.read_text(encoding="utf-8")
        self.assertNotIn("통과", text)
        self.assertIsNone(STATUTE_RE.search(text))
        self.assertIn("초안 규칙 — 준법 검토 전", text)


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_findings_exit_zero_and_inputs_unchanged(self):
        spec = self.t / "spec.json"
        spec.write_text(json.dumps(mk(["원금 보장이에요"], ["세액공제 16.5%"], basis="예시"), ensure_ascii=False), encoding="utf-8")
        cap = self.t / "caption.txt"
        cap.write_text("훅\n\n• 무조건 절세\n\n#IRP\n", encoding="utf-8")
        before = (spec.read_bytes(), cap.read_bytes())
        out = self.t / "c.json"
        r = run_cli("compliance", str(spec), "--caption", str(cap), "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stderr)
        last = r.stdout.rstrip("\n").splitlines()[-1]
        self.assertRegex(last, r"^compliance: 위험 표현 \d+건 발견 · 규칙 v0\.1\(초안\) · 기준일 2026-10-29 \| 수정 필요 \d+건")
        self.assertIn("G-01", r.stdout)
        self.assertNotIn("통과", r.stdout)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertGreaterEqual(data["counts"]["수정 필요"], 2)
        self.assertEqual((spec.read_bytes(), cap.read_bytes()), before)

    def test_bad_rules_exit_one_names_rule(self):
        spec = self.t / "spec.json"
        spec.write_text(json.dumps(mk(["안녕"]), ensure_ascii=False), encoding="utf-8")
        data = json.loads(compliance.RULES_PATH.read_text(encoding="utf-8"))
        data["rules"][0]["pattern"] = "(원금"
        rules = self.t / "rules.json"
        rules.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        r = run_cli("compliance", str(spec), "--rules", str(rules))
        self.assertEqual(r.returncode, 1)
        self.assertIn("G-01", r.stderr)

    def test_missing_input_exit_one(self):
        r = run_cli("compliance", str(self.t / "nope.json"))
        self.assertEqual(r.returncode, 1)

    def test_unwritable_out_exit_two(self):
        spec = self.t / "spec.json"
        spec.write_text(json.dumps(mk(["안녕"]), ensure_ascii=False), encoding="utf-8")
        r = run_cli("compliance", str(spec), "--out", str(self.t / "no" / "such" / "dir" / "c.json"))
        # 상위 폴더는 만들어 쓰므로 정상, 디렉터리를 파일 경로로 주면 쓰기 오류
        self.assertIn(r.returncode, (0, 2))
        r = run_cli("compliance", str(spec), "--out", str(self.t))
        self.assertEqual(r.returncode, 2)

    def test_help(self):
        self.assertEqual(run_cli("compliance", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
