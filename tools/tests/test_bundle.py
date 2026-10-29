"""draft.py bundle: 초안 폴더 하나가 검수 묶음으로 만들어지는 전체 흐름 (렌더 1회, stdlib unittest 전용)."""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
DRAFT = [sys.executable, str(TOOLS / "draft.py")]
sys.path.insert(0, str(TOOLS))

from reelkit import bundle, render, review, timeline  # noqa: E402
from reelkit.browser import BrowserLaunchError  # noqa: E402

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
                  f"{NAME}-scenes.png", "review.md", "record.json", "bundle.json"):
            self.assertTrue((self.d / n).is_file(), n)

    def test_steps_in_order_with_timing(self):
        b = json.loads(self.read("bundle.json"))
        self.assertEqual([s["name"] for s in b["steps"]],
                         ["expand", "check", "caption", "compliance", "render", "cover", "scenes", "review"])
        self.assertTrue(all(s["status"] == "ok" for s in b["steps"]), b["steps"])
        self.assertEqual(b["status"], "complete")
        self.assertLess(b["elapsed_s"], 600)
        self.assertEqual(b["request_source"], "created.json")
        self.assertIsNotNone(b["request_started_at"])
        self.assertIsNotNone(b["elapsed_since_request_s"])
        self.assertIs(b["within_10_min"], True)
        for key in ("started_at", "finished_at"):
            self.assertRegex(b[key], r"^\d{4}-\d{2}-\d{2}T")
        self.assertEqual(b["failed_step"], None)
        # WR-02: 산출물 지문이 기록되고 지금 파일과 같다
        self.assertEqual(b["outputs"], bundle.output_hashes(bundle.draft_paths(self.d)))
        self.assertEqual(len(b["outputs"]), len(bundle.OUTPUT_KEYS))

    def test_review_section_5_timing(self):
        text = self.read("review.md").split("## 5. 걸린 시간", 1)[1]
        for need in ("묶음 시작", "묶음 끝", "걸린 시간 (초)", "render:", "요청부터 (초)", "10분 이내 여부: 예", "포함되지 않음"):
            self.assertIn(need, text)

    def test_compliance_headline_and_caption_finding(self):
        c = json.loads(self.read("compliance.json"))
        self.assertRegex(c["headline"], r"^위험 표현 \d+건 발견 · 규칙 v0\.2\(초안\) · 기준일 2026-10-29$")
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

    def test_scene_sheet_and_crop_audit(self):
        r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                 "-of", "csv=p=0", str(self.d / f"{NAME}-scenes.png")])
        self.assertEqual(r.stdout.strip(), "1500,1316")
        self.assertNotIn("COVER_CROP", self.r.stderr)
        text = self.read("review.md")
        for need in ("![장면 모음](", "표지 크롭 검사", "예외 처리로 제외된 표현", "| 장면 | 시점(초) | 첫 줄 |"):
            self.assertIn(need, text)
        table = text.split("| 장면 | 시점(초) | 첫 줄 |", 1)[1].split("\n\n", 1)[0]
        self.assertEqual(len([ln for ln in table.splitlines() if re.match(r"\| \d+ \|", ln)]), 7)
        self.assertNotIn("<", table)

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


def make_folder(root, *, spec_src=None, caption_src=None, hook=None):
    """drafts/<이름> 폴더에 원고 소스 두 개를 둔다 (slot 명령 없이)."""
    d = Path(root) / "reels" / "drafts" / NAME
    d.mkdir(parents=True)
    if spec_src is None:
        shutil.copy(FIX / "draft-pension.src.json", d / "spec.src.json")
    else:
        (d / "spec.src.json").write_text(spec_src, encoding="utf-8")
    cap = json.loads((FIX / "draft-pension.caption.src.json").read_text(encoding="utf-8"))
    if hook:
        cap["hook"] = hook
    (d / "caption.src.json").write_text(json.dumps(cap, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def run_inproc(d, **kw):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = bundle.run_cli(d, **kw)
    return code, out.getvalue(), err.getvalue()


class Rebuild(unittest.TestCase):
    """편집 후 다시 만들기 (렌더 2회): 산출물은 새로 생기고, 승인 기록은 사라지고, 사람 기록은 남는다 (BNDL-05)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d = make_folder(cls.tmp.name, hook=RISKY_HOOK)
        (cls.d / "created.json").write_text('{"created_at": "x", "epoch": 1.0}\n', encoding="utf-8")
        (cls.d / "skeleton.json").write_text('{"keep": 1}\n', encoding="utf-8")
        cls.first = run(DRAFT + ["bundle", str(cls.d)])
        assert cls.first.returncode == 0, cls.first.stderr
        cls.outputs = ("spec.json", "check.json", "caption.txt", "compliance.json", "review.md", f"{NAME}.mp4",
                       f"{NAME}-cover.png", f"{NAME}-scenes.png")
        rec = {"ad_applicable": "해당", "brand_relation": "미확인", "review_stage": "내부 검수",
               "review_no": "테스트-001", "reviewer": "", "note": ""}
        (cls.d / "record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (cls.d / "approval.json").write_text('{"approved": true}\n', encoding="utf-8")
        cls.keep_before = {n: (cls.d / n).read_bytes() for n in ("record.json", "created.json", "skeleton.json")}
        cls.mtime_before = {n: (cls.d / n).stat().st_mtime_ns for n in cls.outputs}
        cap = json.loads((cls.d / "caption.src.json").read_text(encoding="utf-8"))
        cap["hook"] = "연금계좌 세액공제, 한도가 얼마일까?"
        (cls.d / "caption.src.json").write_text(json.dumps(cap, ensure_ascii=False, indent=1), encoding="utf-8")
        src = (cls.d / "spec.src.json").read_text(encoding="utf-8")
        assert "채운 만큼만 받아요" in src
        (cls.d / "spec.src.json").write_text(src.replace("채운 만큼만 받아요", "채운 만큼 받아요"), encoding="utf-8")
        cls.second = run(DRAFT + ["bundle", str(cls.d)])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_rerun_ok_and_approval_gone(self):
        self.assertEqual(self.second.returncode, 0, self.second.stderr)
        self.assertFalse((self.d / "approval.json").exists())

    def test_human_files_untouched_and_shown(self):
        for n, data in self.keep_before.items():
            self.assertEqual((self.d / n).read_bytes(), data, n)
        text = (self.d / "review.md").read_text(encoding="utf-8")
        for v in ("해당", "내부 검수", "테스트-001"):
            self.assertIn(v, text)

    def test_outputs_regenerated(self):
        self.assertIn("채운 만큼 받아요", (self.d / "spec.json").read_text(encoding="utf-8"))
        c = json.loads((self.d / "compliance.json").read_text(encoding="utf-8"))
        self.assertFalse([f for f in c["findings"] if "G-01" in f["rule"]], c["findings"])
        for n in self.outputs:
            self.assertGreater((self.d / n).stat().st_mtime_ns, self.mtime_before[n], n)


class Purge(unittest.TestCase):
    def test_purge_list_is_exact(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_folder(t)
            gone = ["spec.json", "check.json", "caption.txt", "compliance.json", "review.md", "bundle.json",
                    "approval.json", f"{NAME}.mp4", f"{NAME}.mp4.part.mp4", f"{NAME}-cover.png",
                    f"{NAME}-scenes.png", f"{NAME}.safe-s01.png", f"{NAME}.safe-s05.png"]
            kept = ["record.json", "created.json", "skeleton.json", "notes.txt", "other.png"]
            for n in gone + kept:
                (d / n).write_bytes(b"x")
            bundle.purge_outputs(d, NAME)
            self.assertEqual([n for n in gone if (d / n).exists()], [])
            self.assertEqual([n for n in kept if not (d / n).exists()], [])
            self.assertTrue((d / "spec.src.json").is_file() and (d / "caption.src.json").is_file())


class Failures(unittest.TestCase):
    STALE = ("caption.txt", f"{NAME}.mp4", f"{NAME}-cover.png", f"{NAME}-scenes.png", "approval.json")

    def stale(self, d):
        for n in self.STALE:
            (d / n).write_bytes(b"old")

    def test_unregistered_number_stops_before_render(self):
        with tempfile.TemporaryDirectory() as t:
            src = (FIX / "draft-pension.src.json").read_text(encoding="utf-8")
            bad = src.replace("연 {{fig.pension_credit_limit_savings|man_won}}까지", "연 700만 원까지")
            self.assertNotEqual(src, bad)
            d = make_folder(t, spec_src=bad)
            self.stale(d)
            r = run(DRAFT + ["bundle", str(d)])
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertTrue((d / "check.json").is_file())
            self.assertTrue((d / "compliance.json").is_file())
            for n in self.STALE:
                self.assertFalse((d / n).exists(), n)
            text = (d / "review.md").read_text(encoding="utf-8")
            self.assertIn("원고 오류 — 영상 미생성", text)
            self.assertIn("700만", text)
            self.assertIn("광고 해당 여부", text)
            b = json.loads((d / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual((b["status"], b["failed_step"]), ("failed", "check"))

    def test_invalid_json_is_expand_failure(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_folder(t, spec_src="{ not json")
            self.stale(d)
            r = run(DRAFT + ["bundle", str(d)])
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            b = json.loads((d / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual((b["status"], b["failed_step"]), ("failed", "expand"))
            text = (d / "review.md").read_text(encoding="utf-8")
            self.assertIn("원고 오류 — 영상 미생성", text)
            self.assertIn("JSON 형식 오류", text)
            self.assertFalse((d / f"{NAME}.mp4").exists())

    def test_render_environment_error_is_exit_2(self):
        cases = [(BrowserLaunchError("Chromium 을 열 수 없음"), "렌더 환경 오류: Chromium 을 열 수 없음"),
                 (ModuleNotFoundError("No module named 'playwright'", name="playwright"), render.PLAYWRIGHT_MISSING)]
        for exc, want in cases:
            with self.subTest(exc=type(exc).__name__), tempfile.TemporaryDirectory() as t:
                d = make_folder(t)
                self.stale(d)
                with mock.patch("reelkit.bundle.render_reel", side_effect=exc):
                    code, _out, err = run_inproc(d)
                self.assertEqual(code, 2, err)
                self.assertIn(want, err)
                self.assertEqual(render.env_error_message(exc), want)
                b = json.loads((d / "bundle.json").read_text(encoding="utf-8"))
                self.assertEqual((b["status"], b["failed_step"]), ("failed", "render"))
                self.assertIn("렌더 환경 오류", (d / "review.md").read_text(encoding="utf-8"))
                for n in (f"{NAME}.mp4", f"{NAME}-cover.png", f"{NAME}-scenes.png", "approval.json"):
                    self.assertFalse((d / n).exists(), n)

    def test_internal_import_bug_is_not_mapped(self):
        self.assertIsNone(render.env_error_message(ImportError("x", name="reelkit.layout")))
        self.assertIsNone(render.env_error_message(ValueError("x")))


class Timing(unittest.TestCase):
    """요청 시각 기록 (BNDL-07, 렌더 없음: 원고 오류로 일찍 멈추는 폴더에서 bundle.json 을 읽는다)."""

    def folder(self, t, created=None):
        d = make_folder(t, spec_src="{ not json")
        if created is not None:
            (d / "created.json").write_text(json.dumps({"created_at": "x", "epoch": created}), encoding="utf-8")
        return d

    def read_bundle(self, d):
        return json.loads((d / "bundle.json").read_text(encoding="utf-8"))

    def test_request_start_flag(self):
        import time
        with tempfile.TemporaryDirectory() as t:
            d = self.folder(t, created=time.time() - 5000)
            e = time.time() - 30
            run(DRAFT + ["bundle", str(d), "--request-start", str(e)])
            b = self.read_bundle(d)
            self.assertEqual(b["request_source"], "--request-start")
            self.assertTrue(30 <= b["elapsed_since_request_s"] < 90, b)
            self.assertIs(b["within_10_min"], True)
            self.assertIn("요청부터 (초)", (d / "review.md").read_text(encoding="utf-8"))

    def test_over_ten_minutes_is_false(self):
        import time
        with tempfile.TemporaryDirectory() as t:
            d = self.folder(t)
            run(DRAFT + ["bundle", str(d), "--request-start", str(time.time() - 700)])
            b = self.read_bundle(d)
            self.assertGreaterEqual(b["elapsed_since_request_s"], 700)
            self.assertIs(b["within_10_min"], False)
            self.assertIn("10분 이내 여부: 아니오", (d / "review.md").read_text(encoding="utf-8"))

    def test_created_json_fallback(self):
        import time
        with tempfile.TemporaryDirectory() as t:
            d = self.folder(t, created=time.time() - 10)
            run(DRAFT + ["bundle", str(d)])
            b = self.read_bundle(d)
            self.assertEqual(b["request_source"], "created.json")
            self.assertTrue(10 <= b["elapsed_since_request_s"] < 70, b)
            self.assertTrue((d / "created.json").is_file())

    def test_no_request_time(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.folder(t)
            run(DRAFT + ["bundle", str(d)])
            b = self.read_bundle(d)
            for key in ("request_started_at", "request_source", "elapsed_since_request_s", "within_10_min"):
                self.assertIsNone(b[key], key)
            self.assertIn("요청 시각 없음 — 묶음 시간만 기록", (d / "review.md").read_text(encoding="utf-8"))

    def test_future_or_bad_request_start_is_exit_1(self):
        import time
        with tempfile.TemporaryDirectory() as t:
            d = self.folder(t)
            for bad in (str(time.time() + 3600), "nan", "inf", "abc"):
                r = run(DRAFT + ["bundle", str(d), "--request-start", bad])
                self.assertEqual(r.returncode, 1, (bad, r.stderr))
                self.assertIn("초안 오류", r.stderr)
            self.assertFalse((d / "bundle.json").exists())

    def test_any_bundle_run_invalidates_approval_first(self):
        # IN-02: 인자 오류로 바로 멈추는 실행도 승인 기록부터 지운다
        with tempfile.TemporaryDirectory() as t:
            d = self.folder(t)
            (d / "approval.json").write_text("{}", encoding="utf-8")
            r = run(DRAFT + ["bundle", str(d), "--request-start", "abc"])
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertFalse((d / "approval.json").exists())
        self.assertEqual(bundle.PURGE_FIXED[0], "approval.json")


class UploadSpecLine(unittest.TestCase):
    def test_warn_is_named_not_silently_unmet(self):
        # IN-05: PASS 만 충족으로 세므로 모자란 수를 실패·경고로 밝힌다
        self.assertEqual(review.upload_spec_line(6, 7, 0, 1), "- 업로드 규격 검사: 6/7 항목 충족 (경고 1)")
        self.assertEqual(review.upload_spec_line(5, 7, 1, 1), "- 업로드 규격 검사: 5/7 항목 충족 (실패 1, 경고 1)")
        self.assertEqual(review.upload_spec_line(7, 7, 0, 0), "- 업로드 규격 검사: 7/7 항목 충족")


class ExitCode(unittest.TestCase):
    def test_final_code(self):
        ok, bad = [SimpleNamespace(status="PASS")], [SimpleNamespace(status="PASS"), SimpleNamespace(status="FAIL")]
        self.assertEqual(bundle.final_code([], [], ok), 0)
        self.assertEqual(bundle.final_code(["w"], [], ok), 3)
        self.assertEqual(bundle.final_code([], ["COVER_CROP"], ok), 3)
        self.assertEqual(bundle.final_code(["w"], ["c"], bad), 4)
        self.assertEqual(bundle.final_code([], [], bad), 4)


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
