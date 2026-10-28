"""게시된 릴스 10편의 golden 회귀 (ENV-03, D-05, D-06). stdlib 와 reelkit 만 쓴다.

기준 목록(manifest.json)은 커밋된 MP4 와 원고에서만 뽑는다. 렌더러 출력으로 기준을 다시 만들지 않는다.
렌더러가 만든 MP4 의 바이트는 비교하지 않는다(인코더 출력은 바이트가 달라질 수 있다):
프레임 수, 스트림 길이, 장면 경계 프레임, cover_ms, 프레임별 SSIM 으로 판정한다.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import specprobe, timeline
from .constants import FPS, HOLD, LINE, REPO_ROOT, TOOLS_DIR
from .spec import load_spec

GOLDEN_STEMS = (
    "2026-10-19-rate-secret-1",
    "2026-10-19-savings-interest",
    "2026-10-21-rate-secret-2",
    "2026-10-24-rate-secret-3",
    "2026-10-26-tax-deduction",
    "2026-10-28-salary-two-owners-1",
    "2026-10-29-ebook-event",
    "2026-10-31-salary-two-owners-2",
    "2026-11-02-salary-two-owners-3",
    "2026-11-04-salary-two-owners-4",
    "2026-11-07-salary-two-owners-5",
)
REELS_DIR = REPO_ROOT / "2026" / "reels"
SPECS_DIR = REELS_DIR / "specs"
MANIFEST = TOOLS_DIR / "tests" / "golden" / "manifest.json"
SSIM_MIN = 0.98          # 프레임별 SSIM 하한. 통과시키려고 낮추지 않는다 (폰트 로드·마크업을 조사한다)
SCENE_THRESHOLD = 0.003  # 장면 경계 검출 임계값 (측정: 정상 최소 SSIM 0.9923 / 깨진 렌더 최대 0.9508)

VERDICT_PASS, VERDICT_FAIL, VERDICT_NONE = "PASS", "FAIL", "재현 불가"
NOT_REPRODUCIBLE_REASON = "원고 없음 (D-06)"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def frame_count(mp4):
    out = _run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(mp4)]).stdout
    return int(out.strip())


def stream_durations(mp4):
    """(비디오 길이, 오디오 길이) 문자열. ffprobe 가 적은 그대로 비교한다."""
    out = _run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration",
                "-of", "json", str(mp4)]).stdout
    found = {}
    for s in json.loads(out).get("streams", []):
        found.setdefault(s.get("codec_type"), str(s.get("duration")))
    return found.get("video"), found.get("audio")


def boundaries(mp4):
    """장면 상태가 바뀌는 프레임 번호 목록 (scene 점수가 임계값을 넘는 프레임, round(pts_time*30))."""
    vf = f"scale=270:480,select='gt(scene,{SCENE_THRESHOLD})',showinfo"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-vf", vf, "-an", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    return sorted(round(float(t) * FPS) for t in re.findall(r"pts_time:([0-9.]+)", r.stderr))


def ssim_values(golden, new, work):
    """프레임별 SSIM 'All' 값 목록 (golden 이 첫 입력, 새 렌더가 둘째 입력)."""
    stats = Path(work) / "ssim.txt"
    _run(["ffmpeg", "-v", "error", "-i", str(golden), "-i", str(new),
          "-lavfi", f"[0:v][1:v]ssim=stats_file={stats}", "-f", "null", "-"])
    return [float(v) for v in re.findall(r"All:([0-9.]+)", stats.read_text(encoding="utf-8"))]


def _rel(path):
    return Path(path).relative_to(REPO_ROOT).as_posix()


def _expected_stdout(total, cover):
    return f"duration={total:.1f}s cover_ms={cover}"


def build_manifest():
    """커밋된 MP4 와 원고에서만 기준 목록을 만들어 MANIFEST 에 쓴다. 렌더러는 부르지 않는다."""
    entries = []
    for stem in GOLDEN_STEMS:
        mp4 = REELS_DIR / f"{stem}.mp4"
        spec_path = SPECS_DIR / f"{stem}.json"
        if not spec_path.is_file():
            entries.append({
                "stem": stem, "status": "not-reproducible", "reason": NOT_REPRODUCIBLE_REASON,
                "mp4": _rel(mp4), "mp4_sha256": sha256(mp4), "frames": frame_count(mp4),
            })
            continue
        spec = load_spec(spec_path)
        states = timeline.build_states(spec)
        cover = timeline.cover_ms(spec)
        bounds = boundaries(mp4)
        if len(bounds) != len(states) - 1:
            raise RuntimeError(
                f"{stem}: 경계 {len(bounds)}개, 상태 {len(states)}개 — 경계 수는 상태 수 - 1 이어야 합니다. "
                "게시된 영상이나 경계 검출 조건을 확인하세요")
        video, audio = stream_durations(mp4)
        entries.append({
            "stem": stem, "status": "reproducible", "layout": "legacy",
            "spec": _rel(spec_path), "spec_sha256": sha256(spec_path),
            "mp4": _rel(mp4), "mp4_sha256": sha256(mp4),
            "frames": frame_count(mp4), "video_duration": video, "audio_duration": audio,
            "boundaries": bounds, "states": len(states), "cover_ms": cover,
            "stdout": _expected_stdout(timeline.total_duration(states), cover),
        })
    manifest = {
        "generated_from": "committed MP4 (2026/reels/*.mp4)",
        "generated_at": datetime.date.today().isoformat(),
        "ssim_min_threshold": SSIM_MIN,
        "scene_threshold": SCENE_THRESHOLD,
        "entries": entries,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return manifest


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@dataclass
class ReelResult:
    stem: str
    verdict: str                              # "PASS" | "FAIL" | "재현 불가"
    details: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)


def _spec_verdict(checks):
    return "FAIL" if any(c.status == "FAIL" for c in checks) else "PASS"


def _first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b)) if len(a) != len(b) else None


def check_reel(entry):
    """기준 항목 하나를 판정한다. 게시된 영상·원고가 바뀌었으면 렌더하지 않고 FAIL 이다."""
    stem = entry["stem"]
    committed = REPO_ROOT / entry["mp4"]
    reasons, details = [], {}

    if not committed.is_file() or sha256(committed) != entry["mp4_sha256"]:
        return ReelResult(stem, VERDICT_FAIL, details, ["게시된 영상이 바뀜 (mp4 sha256 불일치)"])

    if entry["status"] != "reproducible":
        checks = specprobe.probe(committed)
        details["spec"] = _spec_verdict(checks)
        if details["spec"] == "FAIL":
            reasons.append("게시된 영상이 업로드 규격 FAIL: "
                           + ", ".join(c.item for c in checks if c.status == "FAIL"))
        return ReelResult(stem, VERDICT_NONE, details, reasons)

    spec_path = REPO_ROOT / entry["spec"]
    if not spec_path.is_file() or sha256(spec_path) != entry["spec_sha256"]:
        return ReelResult(stem, VERDICT_FAIL, details, ["원고가 바뀜 (spec sha256 불일치)"])

    from .render import render_reel  # playwright 는 렌더할 때만 필요하다

    work = tempfile.mkdtemp(prefix="golden-")
    try:
        try:
            r = render_reel(spec_path, Path(work) / "out.mp4", layout="legacy")
        except Exception as e:  # noqa: BLE001 - 렌더 실패도 한 릴스의 FAIL 로 보고한다
            return ReelResult(stem, VERDICT_FAIL, details, [f"렌더 실패: {e.__class__.__name__}: {e}"])
        new = r.out

        frames_new = frame_count(new)
        details["frames"] = (entry["frames"], frames_new)
        if frames_new != entry["frames"]:
            reasons.append(f"프레임 수 불일치 (기준 {entry['frames']}, 렌더 {frames_new})")

        video, audio = stream_durations(new)
        if video != entry["video_duration"]:
            reasons.append(f"비디오 길이 불일치 (기준 {entry['video_duration']}, 렌더 {video})")
        if audio != entry["audio_duration"]:
            reasons.append(f"오디오 길이 불일치 (기준 {entry['audio_duration']}, 렌더 {audio})")

        bounds = boundaries(new)
        details["boundaries"] = len(entry["boundaries"])
        details["boundary_mismatch"] = None if bounds == entry["boundaries"] else _first_diff(
            bounds, entry["boundaries"])
        if bounds != entry["boundaries"]:
            reasons.append(f"상태 경계 프레임 불일치 (기준 {entry['boundaries']}, 렌더 {bounds})")

        spec = load_spec(spec_path)
        n = len(spec["scenes"][0]["lines"])
        low, high = round(LINE * (n - 1) * 1000), round((LINE * (n - 1) + HOLD) * 1000)
        details["cover_ms"] = r.cover_ms
        if r.cover_ms != entry["cover_ms"]:
            reasons.append(f"cover_ms 불일치 (기준 {entry['cover_ms']}, 렌더 {r.cover_ms})")
        if not low <= r.cover_ms < high:
            reasons.append(f"cover_ms {r.cover_ms} 가 첫 장면의 마지막 줄 구간 [{low}, {high}) 밖")

        stdout = _expected_stdout(r.total, r.cover_ms)
        if stdout != entry["stdout"]:
            reasons.append(f"출력 한 줄 불일치 (기준 '{entry['stdout']}', 렌더 '{stdout}')")

        values = ssim_values(committed, new, work)
        details["ssim_min"] = min(values) if values else 0.0
        if len(values) != frames_new:
            reasons.append(f"SSIM 값 {len(values)}개 != 프레임 {frames_new}개")
        if not values or min(values) < SSIM_MIN:
            reasons.append(f"프레임 SSIM 최소 {details['ssim_min']:.4f} < {SSIM_MIN}")

        details["spec"] = _spec_verdict(r.spec_checks)
        if details["spec"] == "FAIL":
            reasons.append("업로드 규격 FAIL: " + ", ".join(c.item for c in r.spec_checks if c.status == "FAIL"))
    except Exception as e:  # noqa: BLE001 - ffprobe/ffmpeg 실패, 빈 출력 등도 이 릴스 하나의 FAIL 로 보고한다
        reasons.append(f"판정 중 오류: {e.__class__.__name__}: {e}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return ReelResult(stem, VERDICT_FAIL if reasons else VERDICT_PASS, details, reasons)


def unlisted_mp4s(entries, reels_dir=REELS_DIR):
    """기준 목록에 없는 MP4 를 알려 준다 (새 배치 릴스가 생겨도 이 시험이 깨지지 않게 판정하지 않는다)."""
    known = {e["stem"] for e in entries}
    return [f"기준 목록 밖: {p.stem} (판정 안 함)" for p in sorted(Path(reels_dir).glob("*.mp4"))
            if p.stem not in known]


def run(only=None, jobs=4):
    """(results, extras). 재현 가능한 릴스는 프로세스 풀로 병렬 판정하고 결과는 기준 목록 순서로 돌려준다."""
    manifest = load_manifest()
    entries = manifest["entries"]
    if only:
        unknown = [s for s in only if s not in {e["stem"] for e in entries}]
        if unknown:
            raise ValueError(f"기준 목록에 없는 이름: {', '.join(unknown)}")
        selected = [e for e in entries if e["stem"] in only]
    else:
        selected = list(entries)
    heavy = [e for e in selected if e["status"] == "reproducible"]
    done = {}
    if heavy:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, min(jobs, len(heavy)))) as pool:
            for e, res in zip(heavy, pool.map(check_reel, heavy)):
                done[e["stem"]] = res
    results = [done[e["stem"]] if e["stem"] in done else check_reel(e) for e in selected]
    return results, unlisted_mp4s(entries)


def _fmt_line(r):
    d = r.details
    if r.verdict == VERDICT_NONE:
        return f"재현 불가  {r.stem}  (원고 없음, D-06)  규격 {d.get('spec', '?')}"
    parts = [f"{r.verdict:<4}  {r.stem}"]
    if "frames" in d:
        parts.append(f"frames {d['frames'][0]}/{d['frames'][1]}")
        mismatch = d.get("boundary_mismatch")
        parts.append(f"경계 {d['boundaries']} 일치" if mismatch is None else f"경계 {mismatch}번째 불일치")
        parts.append(f"cover_ms {d['cover_ms']}")
        parts.append(f"SSIM 최소 {d['ssim_min']:.4f}")
        parts.append(f"규격 {d['spec']}")
    return "  ".join(parts)


def format_report(results, extras):
    lines = []
    for r in results:
        lines.append(_fmt_line(r))
        lines.extend(f"  {reason}" for reason in r.reasons)
    lines.extend(extras)
    repro = [r for r in results if r.verdict != VERDICT_NONE]
    passed = sum(1 for r in repro if r.verdict == VERDICT_PASS)
    none = sum(1 for r in results if r.verdict == VERDICT_NONE)
    failed = any(r.reasons or r.verdict == VERDICT_FAIL for r in results)
    lines.append(f"golden: {'FAIL' if failed else 'PASS'} {passed}/{len(repro)} (재현 불가 {none})")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="게시된 릴스 10편을 legacy 배치로 다시 그려 기준과 비교")
    ap.add_argument("--only", action="append", metavar="STEM", help="이 이름만 판정 (여러 번 쓸 수 있음)")
    ap.add_argument("--jobs", type=int, default=4, help="동시에 렌더할 수 (기본 4)")
    ap.add_argument("--rebuild-manifest", action="store_true",
                    help="커밋된 MP4·원고에서 기준 목록(manifest.json)을 다시 만든다 (렌더 안 함)")
    args = ap.parse_args(argv)
    if args.rebuild_manifest:
        m = build_manifest()
        print(f"기준 목록 {len(m['entries'])}건 기록: {MANIFEST}")
        return 0
    try:
        results, extras = run(only=args.only, jobs=args.jobs)
    except ValueError as e:
        print(f"golden 오류: {e}", file=sys.stderr)
        return 2
    except (OSError, subprocess.SubprocessError, concurrent.futures.BrokenExecutor) as e:
        # 환경 문제(ffmpeg 없음, 워커 프로세스 비정상 종료 등)는 릴스 FAIL(1)과 구분해 2 로 낸다
        print(f"golden 환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 2
    lines = format_report(results, extras)
    print("\n".join(lines))
    return 0 if lines[-1].startswith("golden: PASS") else 1
