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


FIXTURE_SRC = TOOLS / "tests" / "fixtures" / "draft-tax.src.json"
PUBLISHED_TAX = REPO / "2026" / "reels" / "specs" / "2026-10-26-tax-deduction.json"
OPTIONAL_KEYS = ("version", "inputs", "figures", "basis_items")


def expanded_tax():
    from reelkit import figures
    from reelkit.expand import expand_source
    src = json.loads(FIXTURE_SRC.read_text(encoding="utf-8"))
    return expand_source(src, figures.load_registry())


class OptionalFieldsLoad(TempDirCase):
    def test_expanded_draft_loads_with_scenes_identical(self):
        spec = expanded_tax()
        got = load_spec(self.write("v2.json", spec))
        self.assertEqual(got, json.loads(json.dumps(spec)))
        self.assertEqual(got["scenes"], json.loads(PUBLISHED_TAX.read_text(encoding="utf-8"))["scenes"])

    def test_optional_fields_do_not_change_timeline(self):
        from reelkit import timeline
        v2 = load_spec(self.write("v2.json", expanded_tax()))
        stripped = {k: v for k, v in v2.items() if k not in OPTIONAL_KEYS}
        published = load_spec(PUBLISHED_TAX)
        self.assertEqual(timeline.build_states(stripped), timeline.build_states(published))
        self.assertEqual(timeline.total_duration(timeline.build_states(v2)),
                         timeline.total_duration(timeline.build_states(published)))
        self.assertEqual(timeline.cover_ms(stripped), timeline.cover_ms(published))

    def test_series_and_motion_accepted(self):
        spec = spec_of()
        spec["series"] = {"name": "내 월급의 두 주인", "episode": 6, "next": "2층 퇴직연금"}
        spec["motion"] = "calm"
        self.assertEqual(load_spec(self.write("s.json", spec)), spec)
        spec["motion"] = {"preset": "calm"}
        self.assertEqual(load_spec(self.write("s2.json", spec)), spec)
        spec["series"] = {"name": "연말정산 바로 알기"}
        self.assertEqual(load_spec(self.write("s3.json", spec)), spec)

    def test_v1_without_optional_keys_is_untouched(self):
        spec = spec_of()
        self.assertEqual(load_spec(self.write("v1.json", spec)), spec)


class OptionalFieldsErrors(TempDirCase):
    def bad(self, field, value, *needles):
        spec = spec_of()
        spec[field] = value
        with self.assertRaises(SpecError) as cm:
            load_spec(self.write("bad.json", spec))
        for n in (field,) + needles:
            self.assertIn(n, str(cm.exception))

    def test_version(self):
        for v in (3, "2", True, 1, None):
            with self.subTest(v=v):
                self.bad("version", v)

    def test_series_shape(self):
        self.bad("series", "내 월급의 두 주인")
        self.bad("series", {"name": ""}, "name")
        self.bad("series", {"episode": 1}, "name")
        self.bad("series", {"name": "a", "extra": 1}, "extra")

    def test_series_episode_range_and_type(self):
        for v in (0, 11, True, "1", 1.5):
            with self.subTest(v=v):
                self.bad("series", {"name": "a", "episode": v}, "episode")

    def test_series_next(self):
        self.bad("series", {"name": "a", "next": ""}, "next")
        self.bad("series", {"name": "a", "next": 3}, "next")

    def test_inputs(self):
        self.bad("inputs", [])
        self.bad("inputs", {"amt": {"value": 1000000, "unit": "원", "label": "예시"}}, "amt", "value")
        self.bad("inputs", {"amt": {"value": "1", "unit": "원"}}, "amt", "label")
        self.bad("inputs", {"amt": "1000000"}, "amt")

    def test_figures(self):
        self.bad("figures", {})
        self.bad("figures", ["x"])
        self.bad("figures", [{"text": "6.6%", "ref": "r", "sources": []}], "where")
        self.bad("figures", [{"where": "scene 1 line 1", "ref": "r", "sources": []}], "text")
        self.bad("figures", [{"where": "w", "text": "t", "ref": "r", "sources": "fig.a"}], "sources")

    def test_basis_items(self):
        self.bad("basis_items", {})
        self.bad("basis_items", [{"label": "x"}], "fig")

    def test_motion(self):
        self.bad("motion", 3)
        self.bad("motion", [1])


class UnexpandedSource(TempDirCase):
    def test_placeholder_in_line_is_refused_with_location_and_hint(self):
        spec = spec_of(lines=("a", "{{fig.x|pct}}"))
        with self.assertRaises(SpecError) as cm:
            load_spec(self.write("u.json", spec))
        msg = str(cm.exception)
        self.assertIn("scene 1 line 2", msg)
        self.assertIn("draft.py expand", msg)

    def test_placeholder_in_top_and_basis(self):
        with self.assertRaises(SpecError) as cm:
            load_spec(self.write("t.json", spec_of(top="{{x|pct}}")))
        self.assertIn("scene 1 top", str(cm.exception))
        with self.assertRaises(SpecError) as cm:
            load_spec(self.write("b.json", spec_of(basis="기준 }}")))
        self.assertIn("basis", str(cm.exception))

    def test_reel_cli_refuses_source_with_exit_1_no_mp4(self):
        out = self.tmp / "x.mp4"
        r = subprocess.run([sys.executable, str(TOOLS / "reel.py"), str(FIXTURE_SRC), str(out)],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertFalse(out.exists())
        self.assertIn("draft.py expand", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
