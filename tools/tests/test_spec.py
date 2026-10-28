"""spec.load_spec / check_legacy_markup 단위 시험과 reel.py CLI 종료 코드 시험 (stdlib unittest 전용)."""
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

from reelkit.spec import ALLOWED_TAGS, SpecError, check_legacy_markup, load_spec  # noqa: E402

LT, GT = chr(60), chr(62)


def tag(name):
    return LT + name + GT


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-spec-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, name, content):
        p = self.tmp / name
        p.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
        return p


def spec_of(top="t", lines=("x",), basis="b"):
    return {"basis": basis, "scenes": [{"top": top, "lines": list(lines)}]}


class CommittedSpecs(unittest.TestCase):
    def test_all_ten_committed_specs_load_untouched_and_pass_allowlist(self):
        files = sorted((REPO / "2026" / "reels" / "specs").glob("*.json"))
        self.assertEqual(len(files), 10)
        for f in files:
            with self.subTest(spec=f.name):
                expected = json.loads(f.read_text(encoding="utf-8"))
                got = load_spec(f)
                self.assertEqual(got, expected)
                self.assertIsNone(check_legacy_markup(got))


class LoadSpecErrors(TempDirCase):
    def assert_spec_error(self, path, *needles):
        with self.assertRaises(SpecError) as cm:
            load_spec(path)
        for n in needles:
            self.assertIn(n, str(cm.exception))

    def test_missing_file_names_the_path(self):
        p = self.tmp / "nope.json"
        self.assert_spec_error(p, str(p))

    def test_invalid_json(self):
        self.assert_spec_error(self.write("bad.json", '{"scenes": ['), "JSON")

    def test_no_scenes(self):
        self.assert_spec_error(self.write("a.json", "{}"), "scenes")
        self.assert_spec_error(self.write("b.json", {"scenes": []}), "scenes")

    def test_scene_without_lines_is_numbered(self):
        spec = {"scenes": [{"top": "a", "lines": ["x"]}, {"top": "b", "lines": []}]}
        self.assert_spec_error(self.write("c.json", spec), "scene 2")

    def test_non_string_line_is_numbered(self):
        spec = {"scenes": [{"top": "a", "lines": ["x", 5]}]}
        self.assert_spec_error(self.write("d.json", spec), "scene 1 line 2")

    def test_missing_top(self):
        spec = {"scenes": [{"lines": ["x"]}]}
        self.assert_spec_error(self.write("e.json", spec), "scene 1 top")

    def test_non_string_basis(self):
        spec = {"basis": 3, "scenes": [{"top": "a", "lines": ["x"]}]}
        self.assert_spec_error(self.write("f.json", spec), "basis")

    def test_valid_spec_is_returned_untouched(self):
        spec = {"scenes": [{"top": "", "lines": ["x"]}]}
        p = self.write("g.json", spec)
        self.assertEqual(load_spec(p), spec)
        self.assertEqual(json.loads(p.read_text(encoding="utf-8")), spec)


class CheckLegacyMarkup(unittest.TestCase):
    def assert_rejected(self, spec, *needles):
        with self.assertRaises(SpecError) as cm:
            check_legacy_markup(spec)
        for n in needles:
            self.assertIn(n, str(cm.exception))

    def test_allowed_tags_constant(self):
        self.assertEqual(ALLOWED_TAGS, ("<g>", "</g>", "<s>", "</s>"))

    def test_i_tag_in_line(self):
        self.assert_rejected(spec_of(lines=[tag("i") + "x"]), "scene 1 line 1", "허용되지 않은 마크업")

    def test_script_tag_in_top_of_scene_2(self):
        spec = {"scenes": [{"top": "a", "lines": ["x"]},
                           {"top": tag("script") + "alert(1)", "lines": ["y"]}]}
        self.assert_rejected(spec, "scene 2 top")

    def test_b_tag_in_basis(self):
        self.assert_rejected(spec_of(basis=tag("b") + "x"), "basis")

    def test_near_miss_tags_rejected(self):
        self.assert_rejected(spec_of(lines=[LT + "g " + GT + "x" + LT + "/g" + GT]), "scene 1 line 1")
        self.assert_rejected(spec_of(lines=[LT + "gg" + GT]), "scene 1 line 1")
        self.assert_rejected(spec_of(lines=["a " + LT + " b"]), "scene 1 line 1")

    def test_allowed_markup_and_ampersand_accepted(self):
        ok = tag("g") + "금" + tag("/g") + " " + tag("s") + "작게" + tag("/s")
        self.assertIsNone(check_legacy_markup(spec_of(lines=[ok, "S&P500"])))


class CliExitCodes(TempDirCase):
    def run_cli(self, spec, out):
        return subprocess.run([sys.executable, "tools/reel.py", str(spec), str(out)],
                              cwd=REPO, capture_output=True, text=True)

    def test_disallowed_markup_exits_1_without_mp4(self):
        spec = self.write("bad.json", spec_of(lines=[tag("i") + "x"]))
        out = self.tmp / "x.mp4"
        r = self.run_cli(spec, out)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("scene 1 line 1", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse(out.exists())

    def test_missing_spec_exits_1_without_traceback(self):
        r = self.run_cli(self.tmp / "missing.json", self.tmp / "x.mp4")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("원고", r.stderr)


if __name__ == "__main__":
    unittest.main()
