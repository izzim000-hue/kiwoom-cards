"""`motion: none` 새 배치 렌더가 바뀌지 않았음을 지키는 기준선 (MOTN-04, D-05; 표준 라이브러리와 reelkit 만 사용).

capture(spec) 는 렌더를 한 번 돌리며 상태별 디코딩 프레임 해시·지속 시간·총길이·표지 시점·경고·안전영역 미리보기 해시·
새 배치 마크업 해시·정규화한 ffmpeg 인자를 모은다. 기준선은 `--write` 로 만들며, 소스를 고치기 전의 코드에서만 다시 만든다.
"""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
GOLDEN = Path(__file__).resolve().parent / "golden" / "none-new.json"
SPECS = ("ok-layout.json", "bad-layout.json")
NOTE = "환경(Chromium·폰트·ffmpeg)이 바뀌면 바뀌기 전 코드에서 --write 로 다시 만든다"
sys.path.insert(0, str(TOOLS))

from reelkit import layout, render, stills, timeline  # noqa: E402
import reelkit.encode as encode_mod  # noqa: E402


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _normalise(argv, work, out_tmp):
    res = []
    for a in argv:
        a = str(a)
        if a == out_tmp or a.endswith(".part.mp4"):
            a = "<OUT>"
        res.append(a.replace(str(work), "<WORK>"))
    return res


def capture(spec_path):
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    states = timeline.build_states(spec)
    progs = timeline.progress_values(states)
    basis = spec.get("basis", "")
    rec = {"states": [], "argv": None}
    real_concat = render.encode_concat
    real_run = encode_mod.subprocess.run

    def concat_wrapper(files, total, out, work, *a, **kw):
        rec["states"] = [{"sha256": _sha(stills._decode(png)), "dur": dur} for png, dur in files]
        rec["total"] = total
        rec["work"] = str(work)
        return real_concat(files, total, out, work, *a, **kw)

    def run_wrapper(argv, *a, **kw):
        if isinstance(argv, (list, tuple)) and "concat" in argv:
            rec["argv"] = [str(x) for x in argv]
        return real_run(argv, *a, **kw)

    with tempfile.TemporaryDirectory(prefix="none-guard-") as tmp:
        out = Path(tmp) / "out.mp4"
        with mock.patch.object(render, "encode_concat", concat_wrapper), \
                mock.patch.object(encode_mod.subprocess, "run", run_wrapper):
            r = render.render_reel(spec_path, out, layout="new")
        overlays = [_sha(stills._decode(p)) for p in r.overlays]
    argv = _normalise(rec["argv"] or [], rec["work"], "")
    markup = [_sha(layout.new_inner_html(st.top, st.lines, st.k, prog, basis).encode("utf-8"))
              for st, prog in zip(states, progs)]
    return {"states": rec["states"], "total": rec["total"], "cover_ms": r.cover_ms,
            "warnings": [str(w) for w in r.warnings], "overlays": overlays,
            "new_inner_html": markup, "argv": argv}


def capture_all():
    return {"schema": 1, "note": NOTE, "specs": {name: capture(FIX / name) for name in SPECS}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="none 새 배치 기준선")
    ap.add_argument("--write", action="store_true", help="기준선 JSON 을 새로 쓴다 (소스 수정 전 코드에서만)")
    args = ap.parse_args(argv)
    data = capture_all()
    if args.write:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"기준선 기록: {GOLDEN}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
