"""배경음 시험: 거부 규칙, 사인파 믹스(반복·자르기, none/basic), 음량, 묶음 기록, 다시 묶으면 사라짐 (stdlib unittest 전용).

음원은 전부 `ffmpeg -f lavfi -i sine=...` 으로 저장소 밖 임시 폴더에 만든다. 음악을 찾거나 내려받지 않고, 저장소에 오디오 파일을 쓰지 않는다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
TOOLS = TESTS.parent
FIX = TESTS / "fixtures"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TESTS))

from reelkit import bgm, bundle, constants, render, specprobe  # noqa: E402
from reelkit.bgm import BgmError  # noqa: E402

DRAFT = [sys.executable, str(TOOLS / "draft.py")]
REEL = [sys.executable, str(TOOLS / "reel.py")]
DATE, SLUG = "2026-11-08", "pension-credit-limit"
NAME = f"{DATE}-{SLUG}"
MEMO = "자체 제작 음원 | 상업 사용 가능\n2026-10"
STATUTE_RE = re.compile(r"제\s*\d+\s*조")
OK_LAYOUT = FIX / "ok-layout.json"


def run_text(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def ffmpeg_sine(out, seconds, *extra):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", *extra, str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return Path(out)


class Audio:
    """모듈 전체가 같이 쓰는 사인파 음원 (한 번만 만든다)."""
    tmp = None

    @classmethod
    def make(cls):
        if cls.tmp is not None:
            return
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-bgm-audio-"))
        t = cls.tmp
        cls.s35 = ffmpeg_sine(t / "s35.mp3", 3.5, "-c:a", "libmp3lame")
        cls.s8 = ffmpeg_sine(t / "s8.mp3", 8, "-c:a", "libmp3lame")
        cls.s60 = ffmpeg_sine(t / "s60.m4a", 60, "-c:a", "aac")
        cls.s2 = ffmpeg_sine(t / "s2.mp3", 2, "-c:a", "libmp3lame")
        vid = t / "vid.m4a"
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
                            "-f", "lavfi", "-i", "testsrc=duration=5:size=64x64:rate=5", "-c:a", "aac", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-shortest", "-f", "mp4", str(vid)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        cls.video = vid
        cls.fake = t / "fake.mp3"
        cls.fake.write_text("이건 소리가 아니라 글자 파일\n", encoding="utf-8")
        cls.link = t / "link.mp3"
        os.symlink(cls.s8, cls.link)
        cls.wrongext = t / "s8.txt"
        shutil.copy(cls.s8, cls.wrongext)


def setUpModule():
    Audio.make()


def tearDownModule():
    if Audio.tmp is not None:
        shutil.rmtree(Audio.tmp, ignore_errors=True)


def probe_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                        "stream=codec_name,sample_rate,channels,duration", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    return s["codec_name"], int(s["sample_rate"]), int(s["channels"]), float(s["duration"])


def probe_video_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def integrated_lufs(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    values = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", r.stderr)
    assert values, r.stderr[-400:]
    return float(values[-1])


class Validate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.draft = self.root / "2026" / "reels" / "drafts" / NAME
        self.draft.mkdir(parents=True)
        patcher = mock.patch.object(constants, "REPO_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def refused(self, path, memo, fragment):
        with self.assertRaises(BgmError) as cm:
            bgm.validate(path, memo, self.draft)
        self.assertIn(fragment, str(cm.exception))

    def test_neither_is_none(self):
        self.assertIsNone(bgm.validate(None, None, self.draft))

    def test_pair_required(self):
        self.refused(Audio.s8, None, "함께")
        self.refused(None, MEMO, "함께")

    def test_blank_or_long_memo(self):
        self.refused(Audio.s8, "   ", "비어 있음")
        self.refused(Audio.s8, "", "비어 있음")
        self.refused(Audio.s8, "가" * (bgm.MEMO_MAX + 1), "너무 김")

    def test_good_source(self):
        src = bgm.validate(Audio.s35, f"  {MEMO}  ", self.draft)
        self.assertEqual((src.name, src.ext, src.license), ("s35.mp3", ".mp3", MEMO))
        self.assertAlmostEqual(src.duration_s, 3.5, delta=0.2)
        self.assertEqual(src.path, Audio.s35.resolve())

    def test_symlink_refused(self):
        self.refused(Audio.link, MEMO, "심볼릭")

    def test_missing_and_directory(self):
        self.refused(self.root / "none.mp3", MEMO, "일반 파일")
        self.refused(self.root, MEMO, "일반 파일")

    def test_extension_allow_list(self):
        self.refused(Audio.wrongext, MEMO, "확장자")

    def test_not_audio_bytes(self):
        self.refused(Audio.fake, MEMO, "읽을 수 없음")

    def test_video_refused(self):
        self.refused(Audio.video, MEMO, "영상이 든 파일")

    def test_too_short(self):
        self.refused(Audio.s2, MEMO, "너무 짧음")

    def git_repo(self, extra_ignore=""):
        """임시 루트를 이 저장소의 .gitignore 를 쓴 git 저장소로 만든다 (check-ignore 가 실제 규칙으로 답하게)."""
        r = subprocess.run(["git", "init", "-q", str(self.root)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (TOOLS.parent / ".gitignore").read_text(encoding="utf-8")
        (self.root / ".gitignore").write_text(text + extra_ignore, encoding="utf-8")

    def test_repository_paths(self):
        self.git_repo()
        tools = self.root / "tools"
        tools.mkdir()
        shutil.copy(Audio.s8, tools / "x.mp3")
        self.refused(tools / "x.mp3", MEMO, "저장소 안 음원")
        shutil.copy(Audio.s8, self.draft / "song.mp3")
        src = bgm.validate(self.draft / "song.mp3", MEMO, self.draft)
        self.assertEqual(src.name, "song.mp3")
        shutil.copy(Audio.s8, self.draft / "bgm.mp3")
        self.refused(self.draft / "bgm.mp3", MEMO, "복사본 이름")
        other = self.root / "2026" / "reels" / "drafts" / "other"
        other.mkdir()
        shutil.copy(Audio.s8, other / "song.mp3")
        self.refused(other / "song.mp3", MEMO, "저장소 안 음원")

    def test_uppercase_extensions_are_ignored_and_reserved_names_any_case(self):
        # CR-02: Song.MP3 는 .gitignore 가 막는다(대소문자 무관). BGM.MP3 는 도구 복사본 이름이라 대소문자와 관계없이 거부
        self.git_repo()
        shutil.copy(Audio.s8, self.draft / "Song.MP3")
        self.assertEqual(bgm.validate(self.draft / "Song.MP3", MEMO, self.draft).ext, ".mp3")
        (self.draft / "Song.MP3").unlink()
        shutil.copy(Audio.s8, self.draft / "BGM.MP3")
        self.refused(self.draft / "BGM.MP3", MEMO, "복사본 이름")
        # 다른 곳의 음원을 줘도, 초안 폴더에 bgm.* 와 대소문자만 다른 사용자 파일이 있으면 거부 (복사가 덮어쓰지 않게)
        self.refused(Audio.s8, MEMO, "대소문자만 다른")

    def test_in_repo_file_git_does_not_ignore_is_refused(self):
        # 초안 폴더라도 git 이 무시하지 않는 자리면 거부: 저장소 루트의 drafts/ (무시 목록에 없음) + 파일 하나를 되살리는 규칙
        self.git_repo("!keep.mp3\n")
        loose = self.root / "drafts" / NAME
        loose.mkdir(parents=True)
        shutil.copy(Audio.s8, loose / "keep.mp3")
        with self.assertRaises(BgmError) as cm:
            bgm.validate(loose / "keep.mp3", MEMO, loose)
        self.assertIn("git 에서 무시되지 않음", str(cm.exception))
        shutil.copy(Audio.s8, loose / "Other.Mp3")
        self.assertEqual(bgm.validate(loose / "Other.Mp3", MEMO, loose).name, "Other.Mp3")

    def test_in_repo_without_git_is_refused(self):
        shutil.copy(Audio.s8, self.draft / "song.mp3")     # 임시 루트는 git 저장소가 아님: 무시 여부를 알 수 없으면 거부
        self.refused(self.draft / "song.mp3", MEMO, "git 에서 무시되지 않음")

    def test_real_gitignore_blocks_audio_in_any_case(self):
        # 이 저장소의 .gitignore: 파일을 만들지 않고 check-ignore 로만 묻는다
        for rel in ("2026/reels/Song.MP3", "2026/reels/x.mp3", "drafts/n/T.M4A", "tools/a.Wav", "b.AAC", "c.OGG",
                    "d.Opus", "e.FLAC"):
            with self.subTest(rel):
                r = subprocess.run(["git", "-C", str(TOOLS.parent), "check-ignore", "-q", "--", rel])
                self.assertEqual(r.returncode, 0, rel)

    def test_purge_removes_only_exact_tool_names(self):
        # CR-02: 폴더 목록에 그 글자 그대로 있는 bgm.* 만 지운다. 사용자 파일(대소문자만 다른 이름 포함)과 이번 원본은 남는다
        for n in ("bgm.mp3", "bgm.json", "bgm.m4a.part", "BGM.MP3", "Bgm.Json", "song.mp3"):
            (self.draft / n).write_bytes(b"x")
        bundle.purge_outputs(self.draft, NAME)
        self.assertEqual(sorted(p.name for p in self.draft.iterdir()), ["BGM.MP3", "Bgm.Json", "song.mp3"])
        (self.draft / "bgm.wav").write_bytes(b"x")
        bundle.purge_outputs(self.draft, NAME, keep=self.draft / "bgm.wav")
        self.assertTrue((self.draft / "bgm.wav").is_file())

    def test_install_and_read_meta(self):
        src = bgm.validate(Audio.s8, MEMO, self.draft)
        meta = bgm.install(src, self.draft)
        self.assertEqual(set(meta), set(bgm.META_KEYS))
        self.assertEqual((meta["file"], meta["copy"], meta["license"]), ("s8.mp3", "bgm.mp3", MEMO))
        self.assertEqual(meta["sha256"], bundle.sha256_file(self.draft / "bgm.mp3"))
        self.assertEqual(bgm.read_meta(self.draft), meta)
        self.assertEqual(sorted(p.name for p in self.draft.iterdir()), ["bgm.json", "bgm.mp3"])

    def test_read_meta_refusals(self):
        self.assertIsNone(bgm.read_meta(self.draft))
        (self.draft / "bgm.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(BgmError):
            bgm.read_meta(self.draft)
        (self.draft / "bgm.json").unlink()
        (self.draft / "real.json").write_text("{}", encoding="utf-8")
        os.symlink(self.draft / "real.json", self.draft / "bgm.json")
        with self.assertRaises(BgmError):
            bgm.read_meta(self.draft)

    def test_filter_graph(self):
        g = bgm.filter_graph(24.7333)
        self.assertIn("atrim=0:24.734", g)
        self.assertIn("afade=t=out:st=23.734:d=1", g)
        self.assertIn("loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100", g)
        self.assertRegex(g, r"^\[1:a\]aloop=loop=-1:size=2e9,atrim=0:\d+\.\d{3},asetpts=PTS-STARTPTS,"
                            r"afade=t=in:st=0:d=1,afade=t=out:st=\d+\.\d{3}:d=1,loudnorm=I=-16:TP=-1.5:LRA=11,"
                            r"aresample=44100,aformat=channel_layouts=stereo\[a\]$")
        self.assertEqual(bgm.filter_graph(25.0).count("atrim=0:25.000"), 1)
        self.assertIn("st=0.000", bgm.filter_graph(0.5))

    def test_no_network_code(self):
        text = (TOOLS / "reelkit" / "bgm.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"^(import|from) (urllib|http|socket|requests)", text, re.M))


class Mix(unittest.TestCase):
    """ok-layout.json (장면 2개) 를 사인파 음원과 섞어 렌더한다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-bgm-mix-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def render_and_check(self, name, bgm_path, **kw):
        out = self.tmp / name
        r = render.render_reel(OK_LAYOUT, out, layout="new", bgm=bgm_path, **kw)
        self.assertEqual(r.bgm, Path(bgm_path).name)
        statuses = [(c.item, c.status) for c in r.spec_checks]
        self.assertEqual([s for _n, s in statuses], ["PASS"] * 9, statuses)
        codec, rate, channels, a_dur = probe_audio(out)
        self.assertEqual((codec, rate, channels), ("aac", 44100, 2))
        v_dur = probe_video_duration(out)
        self.assertAlmostEqual(a_dur, v_dur, delta=0.1)
        self.assertAlmostEqual(v_dur, r.total, delta=0.1)
        lufs = integrated_lufs(out)
        self.assertTrue(-17.5 <= lufs <= -14.5, f"통합 음량 {lufs} LUFS")
        return r

    def test_none_short_track_loops(self):
        r = self.render_and_check("none-loop.mp4", Audio.s35)
        self.assertEqual(r.motion, "none")
        self.assertGreater(r.total, 3.6)

    def test_basic_long_track_trims(self):
        r = self.render_and_check("basic-trim.mp4", Audio.s60, motion="basic")
        self.assertEqual(r.motion, "basic")


class BundleWithBgm(unittest.TestCase):
    """초안 폴더 하나를 --bgm 으로 묶는다 (none 렌더 1회)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        reels = Path(cls.tmp.name) / "reels"
        (reels / "specs").mkdir(parents=True)
        r = run_text(DRAFT + ["slot", "--reels-dir", str(reels), "--date", DATE, "--slug", SLUG, "--create"])
        assert r.returncode == 0, r.stderr
        cls.d = reels / "drafts" / NAME
        shutil.copy(FIX / "draft-pension.src.json", cls.d / "spec.src.json")
        shutil.copy(FIX / "draft-pension.caption.src.json", cls.d / "caption.src.json")
        cls.r = run_text(DRAFT + ["bundle", str(cls.d), "--bgm", str(Audio.s8), "--bgm-license", MEMO])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, name):
        return (self.d / name).read_text(encoding="utf-8")

    def test_exit_zero_and_spec(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)
        self.assertIn("spec: PASS 9/9", self.r.stderr)

    def test_meta_and_copy(self):
        meta = json.loads(self.read("bgm.json"))
        self.assertEqual(meta["schema"], 1)
        self.assertEqual((meta["file"], meta["copy"], meta["license"]), ("s8.mp3", "bgm.mp3", MEMO))
        self.assertEqual(meta["sha256"], bundle.sha256_file(self.d / "bgm.mp3"))
        self.assertEqual(meta["sha256"], bundle.sha256_file(Audio.s8))
        self.assertAlmostEqual(meta["duration_s"], 8.0, delta=0.2)

    def test_bundle_json_records(self):
        b = json.loads(self.read("bundle.json"))
        self.assertEqual(b["bgm"], json.loads(self.read("bgm.json")))
        self.assertIn("bgm.json", b["outputs"])
        self.assertIn("bgm.mp3", b["outputs"])
        self.assertEqual(b["outputs"]["bgm.mp3"], bundle.sha256_file(self.d / "bgm.mp3"))
        names = [s["name"] for s in b["steps"]]
        self.assertIn("bgm", names)
        self.assertLess(names.index("bgm"), names.index("render"))
        self.assertGreater(names.index("bgm"), names.index("compliance"))

    def test_review_shows_license_for_human(self):
        text = self.read("review.md")
        line = next(ln for ln in text.splitlines() if ln.startswith("- [ ] 음원 라이선스"))
        self.assertIn("`s8.mp3`", line)
        self.assertIn(bundle.sha256_file(self.d / "bgm.mp3")[:12], line)
        self.assertIn("자체 제작 음원 \\| 상업 사용 가능 2026-10", line)
        self.assertNotIn("배경음 없음", line)
        self.assertIn("- [ ] 배경음 음량", text)
        self.assertIn("- 배경음: `s8.mp3`", text)
        self.assertEqual(len([ln for ln in text.splitlines() if "음원 라이선스" in ln]), 1)

    def test_no_forbidden_words(self):
        for n in ("review.md", "compliance.json", "bundle.json", "bgm.json"):
            text = self.read(n)
            self.assertNotIn("통과", text, n)
            self.assertIsNone(STATUTE_RE.search(text), n)
        self.assertNotIn("통과", self.r.stdout)

    def test_audio_in_video(self):
        codec, rate, channels, _dur = probe_audio(self.d / f"{NAME}.mp4")
        self.assertEqual((codec, rate, channels), ("aac", 44100, 2))
        self.assertTrue(-17.5 <= integrated_lufs(self.d / f"{NAME}.mp4") <= -14.5)


class Refusal(unittest.TestCase):
    """거부는 아무것도 지우거나 렌더하기 전에 일어난다 (Chromium 을 띄우지 않음)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        reels = Path(cls.tmp.name) / "reels"
        (reels / "specs").mkdir(parents=True)
        r = run_text(DRAFT + ["slot", "--reels-dir", str(reels), "--date", DATE, "--slug", SLUG, "--create"])
        assert r.returncode == 0, r.stderr
        cls.d = reels / "drafts" / NAME
        shutil.copy(FIX / "draft-pension.src.json", cls.d / "spec.src.json")
        shutil.copy(FIX / "draft-pension.caption.src.json", cls.d / "caption.src.json")
        cls.fakes = {f"{NAME}.mp4": b"old-mp4", f"{NAME}-cover.png": b"old-cover", "caption.txt": b"old-caption",
                     "spec.json": b"{}"}
        for n, data in cls.fakes.items():
            (cls.d / n).write_bytes(data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def assert_refused(self, *args):
        r = run_text(DRAFT + ["bundle", str(self.d), *args])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("음원 오류", r.stderr)
        for n, data in self.fakes.items():
            self.assertEqual((self.d / n).read_bytes(), data, n)
        self.assertFalse((self.d / "bgm.json").exists())
        self.assertFalse((self.d / "bgm.mp3").exists())
        self.assertFalse((self.d / "bundle.json").exists())

    def test_file_without_memo(self):
        self.assert_refused("--bgm", str(Audio.s8))

    def test_blank_memo(self):
        self.assert_refused("--bgm", str(Audio.s8), "--bgm-license", "   ")

    def test_memo_without_file(self):
        self.assert_refused("--bgm-license", "자체 제작")

    def test_bad_file(self):
        self.assert_refused("--bgm", str(Audio.fake), "--bgm-license", "자체 제작")


class Rebuild(unittest.TestCase):
    """--bgm 으로 묶은 폴더를 --bgm 없이 다시 묶으면 음원 기록이 남지 않는다 (D-09, T-04-15). none 렌더 2회."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        reels = Path(cls.tmp.name) / "reels"
        (reels / "specs").mkdir(parents=True)
        r = run_text(DRAFT + ["slot", "--reels-dir", str(reels), "--date", DATE, "--slug", SLUG, "--create"])
        assert r.returncode == 0, r.stderr
        cls.d = reels / "drafts" / NAME
        shutil.copy(FIX / "draft-pension.src.json", cls.d / "spec.src.json")
        shutil.copy(FIX / "draft-pension.caption.src.json", cls.d / "caption.src.json")
        shutil.copy(Audio.s8, cls.d / "song.mp3")   # 사용자 파일: 다시 묶어도 지우지 않는다
        cls.first = run_text(DRAFT + ["bundle", str(cls.d), "--bgm", str(cls.d / "song.mp3"), "--bgm-license", "자체 제작 음원"])
        cls.second = run_text(DRAFT + ["bundle", str(cls.d)])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_first_had_bgm(self):
        self.assertEqual(self.first.returncode, 0, self.first.stdout + self.first.stderr)
        self.assertIn("spec: PASS 9/9", self.first.stderr)

    def test_second_has_no_bgm(self):
        self.assertEqual(self.second.returncode, 0, self.second.stdout + self.second.stderr)
        self.assertFalse((self.d / "bgm.json").exists())
        self.assertFalse((self.d / "bgm.mp3").exists())
        self.assertTrue((self.d / "song.mp3").is_file())
        b = json.loads((self.d / "bundle.json").read_text(encoding="utf-8"))
        self.assertIsNone(b["bgm"])
        self.assertNotIn("bgm.json", b["outputs"])
        self.assertNotIn("bgm", [s["name"] for s in b["steps"]])
        text = (self.d / "review.md").read_text(encoding="utf-8")
        self.assertIn("- [ ] 음원 라이선스 — 배경음 없음 = 무음 (음원을 넣었다면 이용 권리 확인)", text)
        self.assertIn("- 배경음: 없음 (무음 트랙)", text)
        self.assertNotIn("배경음 음량", text)
        _codec, _rate, _ch, _dur = probe_audio(self.d / f"{NAME}.mp4")
        self.assertLess(integrated_lufs_or_silence(self.d / f"{NAME}.mp4"), -60)


def integrated_lufs_or_silence(path):
    """무음 트랙이면 매우 낮은 값(-70)이다. ebur128 이 -inf 로 읽는 경우도 -70 으로 본다."""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    values = re.findall(r"I:\s+(-?\d+(?:\.\d+)?|-inf)\s+LUFS", r.stderr)
    return -70.0 if not values or values[-1] == "-inf" else float(values[-1])


class ReelFlags(unittest.TestCase):
    """reel.py 는 배경음을 받지 않는다 (WR-01): --bgm/--bgm-license 는 렌더 전에 종료 코드 1, 출력 없음. 배경음은 bundle 로만."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-bgm-reel-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def reel(self, out, *args):
        return run_text(REEL + [str(OK_LAYOUT), str(out), "--layout", "new", *map(str, args)])

    def test_no_bgm_has_no_line(self):
        out = self.tmp / "plain.mp4"
        r = self.reel(out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("bgm=", r.stdout)

    def test_bgm_flags_refused_and_point_to_bundle(self):
        for args in (("--bgm", Audio.s35, "--bgm-license", "자체 제작 음원"), ("--bgm", Audio.s35),
                     ("--bgm-license", "자체 제작"), ("--bgm", Audio.s35, "--bgm-license", "  "),
                     ("--bgm", Audio.fake, "--bgm-license", "자체 제작")):
            with self.subTest(args=args):
                out = self.tmp / "refused.mp4"
                r = self.reel(out, *args)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("음원 오류", r.stderr)
                self.assertIn("draft.py bundle", r.stderr)
                self.assertNotIn("duration=", r.stdout)
                self.assertFalse(out.exists())
                self.assertEqual(sorted(p.name for p in self.tmp.iterdir() if p.name != "plain.mp4"
                                        and not p.name.startswith("plain.")), [])


if __name__ == "__main__":
    unittest.main()
