"""Instagram 업로드 규격 검사 (ENV-06): ffprobe JSON + MP4 최상위 atom 순회. stdlib 만 사용한다.

측정할 수 없는 항목은 PASS 로 두지 않는다: 항상 FAIL 이고 actual 이 '측정 불가'로 시작한다.
"""
import argparse
import json
import struct
import subprocess
from fractions import Fraction
from typing import NamedTuple

from .constants import W, H, FPS


class Check(NamedTuple):
    item: str
    status: str    # "PASS" | "FAIL" | "WARN"
    actual: str
    expected: str


_OK_PROFILES = ("High", "Main", "Constrained Baseline")
_MIN_DURATION, _MAX_DURATION = 3, 90   # 연구 가정 A3: 길이 상한은 출처마다 달라 WARN 만 낸다


def top_atoms(path):
    """MP4 최상위 atom 이름 목록. size==1 은 64비트 크기, size==0 은 파일 끝까지. 손상 파일도 멈춘다."""
    out = []
    with open(path, "rb") as f:
        f.seek(0, 2)
        end = f.tell()
        pos = 0
        while pos + 8 <= end:
            f.seek(pos)
            size, typ = struct.unpack(">I4s", f.read(8))
            if size == 1:
                ext = f.read(8)
                if len(ext) < 8:
                    out.append(typ.decode("latin-1"))
                    break
                size = struct.unpack(">Q", ext)[0]
            elif size == 0:
                size = end - pos
            out.append(typ.decode("latin-1"))
            if size < 8:
                break
            pos += size
    return out


def ffprobe_json(path):
    """ffprobe 결과 dict. ffprobe 가 없거나 실패하거나 JSON 이 깨졌으면 None."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        return None
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _unmeasurable(item, reason, expected):
    return Check(item, "FAIL", f"측정 불가: {reason}", expected)


def _frac(text):
    try:
        return Fraction(str(text))
    except (ValueError, ZeroDivisionError):
        return None


def probe(path):
    """9개 항목의 Check 목록. 예외를 던지지 않는다."""
    exp = {
        "video_stream": "비디오 스트림 1개",
        "codec": "h264",
        "size": f"{W}x{H}",
        "fps": f"{FPS}/1 (r_frame_rate 와 avg_frame_rate 모두)",
        "pix_fmt": "yuv420p",
        "profile": " / ".join(_OK_PROFILES),
        "audio": "AAC 오디오 스트림 1개 이상",
        "faststart": "moov 가 mdat 보다 앞",
        "duration": f"{_MIN_DURATION}~{_MAX_DURATION}초",
    }
    order = list(exp)
    info = ffprobe_json(path)
    if info is None:
        reason = "ffprobe 를 실행하지 못했거나 파일을 읽을 수 없음"
        checks = [_unmeasurable(i, reason, exp[i]) for i in order if i != "faststart"]
        checks.insert(order.index("faststart"), _faststart(path, exp["faststart"]))
        return checks

    streams = info.get("streams") if isinstance(info.get("streams"), list) else []
    videos = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"]
    audios = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    v = videos[0] if len(videos) == 1 else None
    checks = []

    checks.append(Check("video_stream", "PASS" if len(videos) == 1 else "FAIL",
                        f"{len(videos)}개", exp["video_stream"]))

    def vfield(item, key, ok):
        if v is None:
            return _unmeasurable(item, "비디오 스트림이 하나가 아님", exp[item])
        val = v.get(key)
        if val in (None, ""):
            return _unmeasurable(item, f"{key} 값 없음", exp[item])
        return Check(item, "PASS" if ok(val) else "FAIL", str(val), exp[item])

    checks.append(vfield("codec", "codec_name", lambda x: x == "h264"))
    if v is None:
        checks.append(_unmeasurable("size", "비디오 스트림이 하나가 아님", exp["size"]))
    elif v.get("width") is None or v.get("height") is None:
        checks.append(_unmeasurable("size", "width/height 값 없음", exp["size"]))
    else:
        got = f"{v['width']}x{v['height']}"
        checks.append(Check("size", "PASS" if got == f"{W}x{H}" else "FAIL", got, exp["size"]))

    if v is None:
        checks.append(_unmeasurable("fps", "비디오 스트림이 하나가 아님", exp["fps"]))
    else:
        r_rate, avg = v.get("r_frame_rate"), v.get("avg_frame_rate")
        shown = f"r={r_rate} avg={avg}"
        avg_f = _frac(avg) if avg else None
        if not r_rate or avg is None:
            checks.append(_unmeasurable("fps", "frame_rate 값 없음", exp["fps"]))
        else:
            ok = r_rate == f"{FPS}/1" and avg_f is not None and avg_f == FPS
            checks.append(Check("fps", "PASS" if ok else "FAIL", shown, exp["fps"]))

    checks.append(vfield("pix_fmt", "pix_fmt", lambda x: x == "yuv420p"))
    checks.append(vfield("profile", "profile", lambda x: x in _OK_PROFILES))   # 오디오 스트림의 LC 와 섞지 않는다

    if not audios:
        checks.append(Check("audio", "FAIL", "오디오 없음", exp["audio"]))
    else:
        codec = audios[0].get("codec_name")
        checks.append(Check("audio", "PASS" if codec == "aac" else "FAIL", str(codec), exp["audio"]))

    checks.append(_faststart(path, exp["faststart"]))

    raw = info.get("format", {}).get("duration") if isinstance(info.get("format"), dict) else None
    try:
        dur = float(raw)
    except (TypeError, ValueError):
        checks.append(_unmeasurable("duration", "format.duration 값 없음", exp["duration"]))
    else:
        ok = _MIN_DURATION <= dur <= _MAX_DURATION
        checks.append(Check("duration", "PASS" if ok else "WARN", f"{dur:.1f}초", exp["duration"]))
    return checks


def _faststart(path, expected):
    try:
        atoms = top_atoms(path)
    except OSError as e:
        return _unmeasurable("faststart", f"파일을 읽을 수 없음 ({e.__class__.__name__})", expected)
    shown = "atoms=" + ",".join(atoms)
    if "moov" in atoms and "mdat" in atoms:
        ok = atoms.index("moov") < atoms.index("mdat")
        return Check("faststart", "PASS" if ok else "FAIL", shown, expected)
    return Check("faststart", "FAIL", shown + " (moov 또는 mdat 없음)", expected)


def format_report(path, checks):
    lines = [f"{c.status:<4} {c.item:<12} {c.actual} (기준 {c.expected})" for c in checks]
    passed = sum(1 for c in checks if c.status == "PASS")
    verdict = "FAIL" if any(c.status == "FAIL" for c in checks) else "PASS"
    lines.append(f"spec: {verdict} {passed}/{len(checks)} — {path}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="MP4 가 Instagram 업로드 규격을 지키는지 항목별로 검사")
    ap.add_argument("files", nargs="+", help="검사할 MP4 경로")
    args = ap.parse_args(argv)
    failed = False
    for path in args.files:
        checks = probe(path)
        for line in format_report(path, checks):
            print(line)
        failed = failed or any(c.status == "FAIL" for c in checks)
    return 1 if failed else 0
