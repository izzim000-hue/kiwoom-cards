"""draft.py approve / promote: 사람 승인 기록과 덮어쓰지 않는 옮기기 (렌더 없음, stdlib unittest 전용)."""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
DRAFT = [sys.executable, str(TOOLS / "draft.py")]
sys.path.insert(0, str(TOOLS))

import draft  # noqa: E402
from reelkit import approve, caption, check, compliance, constants, expand, figures, slot  # noqa: E402

DATE, SLUG = "2026-11-08", "pension-credit-limit"
NAME = f"{DATE}-{SLUG}"
STATUTE_RE = re.compile(r"제\s*\d+\s*조")
MP4_BYTES = b"\x00\x00\x00 ftypisom-placeholder-mp4"
PNG_BYTES = b"\x89PNG\r\n\x1a\n-placeholder-cover"
BLOCK_RULE = {"id": "U-99", "category": "단정·보장", "severity": "수정 필요", "pattern": "쿠폰 묶음",
              "reason": "시험용 규칙", "suggest": "다른 비유로 바꾸세요",
              "examples": {"hit": ["쿠폰 묶음의 크기"], "miss": ["묶음"]}}


class FakeTty(io.StringIO):
    def isatty(self):
        return True


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


def make_draft(reels, date_text=DATE, slug=SLUG):
    """라이브러리 호출만으로 완성된 초안 폴더를 만든다 (영상·표지는 작은 대체 바이트)."""
    reels = Path(reels)
    (reels / "specs").mkdir(parents=True, exist_ok=True)
    d = slot.create_draft_dir(reels, date_text, slug)
    name = d.name
    (d / "spec.src.json").write_bytes((FIX / "draft-pension.src.json").read_bytes())
    (d / "caption.src.json").write_bytes((FIX / "draft-pension.caption.src.json").read_bytes())
    registry = figures.load_registry()
    src = json.loads((d / "spec.src.json").read_text(encoding="utf-8"))
    spec = expand.expand_source(src, registry)
    expand.write_spec(spec, d / "spec.json")
    report = check.check_spec(spec, registry, publish_date=date.fromisoformat(date_text))
    check_data = report.to_json(d / "spec.json", figures.REGISTRY_PATH)
    (d / "check.json").write_text(json.dumps(check_data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cap_src = json.loads((d / "caption.src.json").read_text(encoding="utf-8"))
    text, warnings = caption.build_caption(spec, cap_src, caption.load_config(), registry)
    (d / "caption.txt").write_text(text, encoding="utf-8")
    result = compliance.run(spec, text, compliance.load_rules(), check_json=check_data, caption_warnings=warnings)
    (d / "compliance.json").write_text(json.dumps(result.to_json(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (d / f"{name}.mp4").write_bytes(MP4_BYTES)
    (d / f"{name}-cover.png").write_bytes(PNG_BYTES)
    (d / "bundle.json").write_text(json.dumps({"schema": 1, "name": name, "status": "complete", "exit_code": 0}), encoding="utf-8")
    return d


class ApproveBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.reels = self.root / "2026" / "reels"   # 게시 폴더는 <저장소>/<연도>/reels (WR-04): 저장소 뿌리를 self.root 로 바꿔 시험
        self.d = make_draft(self.reels)
        patcher = mock.patch.object(constants, "REPO_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.targets = [self.reels / f"{NAME}.mp4", self.reels / f"{NAME}-cover.png",
                        self.reels / "specs" / f"{NAME}.json", self.reels / "captions" / f"{NAME}.txt"]

    def tearDown(self):
        self.tmp.cleanup()

    def rules_file(self):
        data = json.loads(compliance.RULES_PATH.read_text(encoding="utf-8"))
        data["rules"].append(BLOCK_RULE)
        p = self.root / "rules-block.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return p

    def call(self, argv, typed=None, rules_path=None):
        """rules_path: 저장소 규칙 파일이 바뀐 상황을 흉내 낸다 (CLI 에는 --rules 가 없음, CR-03)."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(draft.sys, "stdin", FakeTty()), \
                mock.patch("builtins.input", return_value=NAME if typed is None else typed), \
                mock.patch.object(compliance, "RULES_PATH", rules_path or compliance.RULES_PATH), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = draft.main(argv)
        self.check_words(out.getvalue() + err.getvalue())
        return code, out.getvalue(), err.getvalue()

    def check_words(self, text):
        self.assertNotIn("통과", text)
        self.assertIsNone(STATUTE_RE.search(text), text)

    def approve(self, typed=None, by="홍길동", rules=None):
        return self.call(["approve", str(self.d), "--by", by], typed, rules_path=rules)

    def promote(self, rules=None, d=None):
        return self.call(["promote", str(d or self.d)], rules_path=rules)

    def approved(self):
        code, _out, err = self.approve()
        self.assertEqual(code, 0, err)

    def assertNothingPublished(self):
        for t in self.targets:
            self.assertFalse(os.path.lexists(t), str(t))
        self.assertEqual(list(self.reels.rglob(".*.part")), [])


class Approve(ApproveBase):
    def test_non_tty_refuses_before_anything(self):
        r = run(DRAFT + ["approve", str(self.d), "--by", "홍길동"], stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("대화형 터미널", r.stderr)
        self.assertFalse((self.d / "approval.json").exists())
        self.check_words(r.stdout + r.stderr)

    def test_help_marks_human_only(self):
        r = run(DRAFT + ["approve", "--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("사람 전용", r.stdout)
        self.assertEqual(run(DRAFT + ["promote", "--help"]).returncode, 0)

    def test_wrong_retype_refuses(self):
        code, _o, err = self.approve(typed="다른 폴더")
        self.assertEqual(code, 1)
        self.assertIn("폴더 이름", err)
        self.assertFalse((self.d / "approval.json").exists())

    def test_eof_counts_as_empty(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(draft.sys, "stdin", FakeTty()), mock.patch("builtins.input", side_effect=EOFError), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = draft.main(["approve", str(self.d), "--by", "홍길동"])
        self.assertEqual(code, 1)
        self.assertFalse((self.d / "approval.json").exists())

    def test_ai_and_empty_names_refuse(self):
        for who in ("Claude", "  ", "AI 어시스턴트"):
            code, _o, err = self.approve(by=who)
            self.assertEqual(code, 1, who)
            self.assertFalse((self.d / "approval.json").exists(), who)

    def test_must_fix_rule_blocks_approval(self):
        code, _o, err = self.approve(rules=self.rules_file())
        self.assertEqual(code, 1)
        self.assertIn("수정 필요", err)
        self.assertFalse((self.d / "approval.json").exists())

    def test_incomplete_bundle_refuses(self):
        (self.d / "bundle.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")
        code, _o, err = self.approve()
        self.assertEqual(code, 1)
        self.assertFalse((self.d / "approval.json").exists())

    def test_symlinked_source_refuses(self):
        real = self.root / "elsewhere.json"
        real.write_bytes((self.d / "spec.json").read_bytes())
        (self.d / "spec.json").unlink()
        (self.d / "spec.json").symlink_to(real)
        code, _o, err = self.approve()
        self.assertEqual(code, 1)
        self.assertIn("spec.json", err)
        self.assertFalse((self.d / "approval.json").exists())

    def test_success_writes_record(self):
        code, out, err = self.approve()
        self.assertEqual(code, 0, err)
        self.assertIn(NAME, err)
        self.assertIn("미확인", err)
        self.assertTrue(out.strip().splitlines()[-1].startswith(f"approve: {NAME} 승인 기록 (홍길동)"))
        data = json.loads((self.d / "approval.json").read_text(encoding="utf-8"))
        self.assertEqual((data["schema"], data["name"], data["approved_by"]), (1, NAME, "홍길동"))
        self.assertEqual(len(data["files"]), 8)
        self.assertEqual(data["counts"]["수정 필요"], 0)
        self.assertEqual(data["rules"]["sha256"], compliance.load_rules().sha256)
        self.assertEqual(data["record"]["ad_applicable"], "미확인")
        self.assertRegex(data["approved_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
        for fname, digest in data["files"].items():
            self.assertEqual(approve.sha256_file(self.d / fname), digest)
        self.assertNothingPublished()


class Promote(ApproveBase):
    def test_module_has_no_subprocess(self):
        self.assertFalse(hasattr(approve, "subprocess"))
        self.assertFalse((self.root / ".git").exists())

    def test_promote_copies_four_files(self):
        self.approved()
        code, out, err = self.promote()
        self.assertEqual(code, 0, err)
        for src, target in zip((self.d / f"{NAME}.mp4", self.d / f"{NAME}-cover.png", self.d / "spec.json",
                                self.d / "caption.txt"), self.targets):
            self.assertEqual(target.read_bytes(), src.read_bytes(), str(target))
        self.assertEqual(sum(1 for line in out.splitlines() if line.startswith("git add ")), 4)
        self.assertEqual(out.strip().splitlines()[-1], f"promote: {NAME} → 4개 파일 (커밋은 사람이 직접)")
        self.assertEqual(list(self.reels.rglob(".*.part")), [])

    def test_second_promote_never_overwrites(self):
        self.approved()
        self.assertEqual(self.promote()[0], 0)
        before = [t.read_bytes() for t in self.targets]
        code, _o, err = self.promote()
        self.assertEqual(code, 1)
        self.assertIn("이미 게시된 파일", err)
        self.assertEqual([t.read_bytes() for t in self.targets], before)

    def test_caption_edit_after_approval_refuses(self):
        self.approved()
        with open(self.d / "caption.txt", "a", encoding="utf-8") as f:
            f.write("\n추가 문구\n")
        code, _o, err = self.promote()
        self.assertEqual(code, 1)
        self.assertIn("caption.txt", err)
        self.assertNothingPublished()
        self.assertFalse((self.reels / "captions").exists())

    def test_provenance_edit_after_approval_refuses(self):
        self.approved()
        with open(self.d / "spec.src.json", "a", encoding="utf-8") as f:
            f.write("\n")
        code, _o, err = self.promote()
        self.assertEqual(code, 1)
        self.assertIn("spec.src.json", err)
        self.assertNothingPublished()

    def test_rules_changed_since_approval_refuses(self):
        # CR-03: 규칙 파일이 승인 때와 다르면 (더 엄격하든 느슨하든) 다시 승인 받아야 한다
        self.approved()
        code, _o, err = self.promote(rules=self.rules_file())
        self.assertEqual(code, 1)
        self.assertIn("규칙 파일이 다름", err)
        self.assertNothingPublished()

    def test_rules_flag_removed_from_approve_and_promote(self):
        # CR-03: 호출하는 쪽(Claude 포함)이 수정 필요 판정 규칙을 고를 수 없다
        self.approved()
        empty = self.root / "empty.json"
        data = json.loads(compliance.RULES_PATH.read_text(encoding="utf-8"))
        data["rules"] = []
        empty.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        for argv in (["promote", str(self.d), "--rules", str(empty)],
                     ["approve", str(self.d), "--by", "홍길동", "--rules", str(empty)]):
            with self.subTest(argv=argv[0]):
                r = run(DRAFT + argv, stdin=subprocess.DEVNULL)
                self.assertEqual(r.returncode, 2, r.stderr)   # argparse: 알 수 없는 인자
                self.assertIn("--rules", r.stderr)
        self.assertNothingPublished()

    def test_empty_rule_list_is_refused_at_load(self):
        data = json.loads(compliance.RULES_PATH.read_text(encoding="utf-8"))
        data["rules"] = []
        p = self.root / "empty.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(compliance.RuleError):
            compliance.load_rules(p)
        self.approved()
        code, _o, err = self.promote(rules=p)
        self.assertEqual(code, 1)
        self.assertIn("rules", err)
        self.assertNothingPublished()

    def test_bundle_checked_with_other_rules_refuses_approval(self):
        # CR-03: bundle --rules 로 느슨한 규칙을 쓴 묶음은 승인하지 않는다
        path = self.d / "compliance.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rules"]["sha256"] = "0" * 64
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        code, _o, err = self.approve()
        self.assertEqual(code, 1)
        self.assertIn("다른 규칙", err)
        self.assertFalse((self.d / "approval.json").exists())

    def test_missing_approval_refuses(self):
        code, _o, err = self.promote()
        self.assertEqual(code, 1)
        self.assertIn("승인 기록 없음", err)
        self.assertNothingPublished()

    def test_approval_for_another_name_refuses(self):
        self.approved()
        path = self.d / "approval.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["name"] = "2026-11-09-other-name"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        code, _o, err = self.promote()
        self.assertEqual(code, 1)
        self.assertIn("승인 기록 없음", err)
        self.assertNothingPublished()

    def test_symlinked_spec_after_approval_refuses(self):
        self.approved()
        real = self.root / "same.json"
        real.write_bytes((self.d / "spec.json").read_bytes())
        (self.d / "spec.json").unlink()
        (self.d / "spec.json").symlink_to(real)
        code, _o, err = self.promote()
        self.assertEqual(code, 1)
        self.assertIn("spec.json", err)
        self.assertNothingPublished()

    def test_folder_outside_drafts_refuses(self):
        self.approved()
        other = self.reels / "elsewhere" / NAME
        other.parent.mkdir()
        self.d.rename(other)
        code, _o, err = self.promote(d=other)
        self.assertEqual(code, 1)
        self.assertIn("drafts", err)
        self.assertNothingPublished()

    def test_preexisting_target_creates_none_of_the_others(self):
        self.approved()
        existing = self.targets[3]
        existing.parent.mkdir()
        existing.write_text("이미 있는 게시글\n", encoding="utf-8")
        code, _o, err = self.promote()
        self.assertEqual(code, 1)
        self.assertIn("이미 게시된 파일", err)
        self.assertEqual(existing.read_text(encoding="utf-8"), "이미 있는 게시글\n")
        for t in self.targets[:3]:
            self.assertFalse(os.path.lexists(t), str(t))
        self.assertEqual(list(self.reels.rglob(".*.part")), [])

    def test_failure_midway_rolls_back_every_target(self):
        self.approved()
        real_link = os.link
        calls = []

        def flaky(src, dst):
            calls.append(dst)
            if len(calls) == 3:
                raise PermissionError("시험용 실패")
            return real_link(src, dst)

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(approve.os, "link", flaky), mock.patch.object(draft.sys, "stdin", FakeTty()), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = draft.main(["promote", str(self.d)])
        self.assertEqual(code, 2, err.getvalue())
        self.assertNothingPublished()
        self.assertFalse((self.reels / "captions").exists())

    def test_year_mismatch_refuses(self):
        made = make_draft(self.root / "2027" / "reels", "2027-01-05", "new-year-reel")
        d = self.reels / "drafts" / made.name
        made.rename(d)   # 폴더 이름은 2027-…, 놓인 곳은 2026/reels/drafts
        code, _o, err = self.call(["approve", str(d), "--by", "홍길동"], typed=d.name)
        self.assertEqual(code, 1)
        self.assertIn("연도", err)
        self.assertFalse((d / "approval.json").exists())
        code, _o, err = self.call(["promote", str(d)])
        self.assertEqual(code, 1)
        self.assertIn("연도", err)
        self.assertFalse((self.reels / f"{d.name}.mp4").exists())

    def test_drafts_outside_the_repository_year_folder_refuse(self):
        # WR-04: 아무 X/drafts/<이름> 이 X/ 로 옮겨지지 않는다
        self.approved()
        other_reels = self.root / "elsewhere"
        (other_reels / "drafts").mkdir(parents=True)
        moved = other_reels / "drafts" / NAME
        self.d.rename(moved)
        code, _o, err = self.promote(d=moved)
        self.assertEqual(code, 1)
        self.assertIn("게시 폴더", err)
        self.assertFalse((other_reels / f"{NAME}.mp4").exists())
        self.assertNothingPublished()

    def test_symlinked_drafts_folder_refuses(self):
        self.approved()
        real = self.root / "x" / "drafts"
        real.parent.mkdir()
        (self.reels / "drafts").rename(real)
        (self.reels / "drafts").symlink_to(real)
        code, _o, err = self.promote()
        self.assertEqual(code, 1)
        self.assertIn("게시 폴더", err)
        self.assertNothingPublished()
        self.assertFalse((self.root / f"{NAME}.mp4").exists())


if __name__ == "__main__":
    unittest.main()
