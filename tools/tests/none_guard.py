"""`motion: none` 새 배치 렌더가 바뀌지 않았음을 지키는 기준선 (MOTN-04, D-05; 표준 라이브러리와 reelkit 만 사용).

capture(spec) 는 렌더를 한 번 돌리며 상태별 디코딩 프레임 해시·지속 시간·총길이·표지 시점·경고·안전영역 미리보기 해시·
새 배치 마크업 해시·정규화한 ffmpeg 인자를 모은다.

기준선 다시 만들기 (WR-03): 픽셀 해시(states 의 sha256, overlays)는 Chromium·폰트·ffmpeg 가 바뀌면 코드가 그대로여도 달라진다.
그때도 기준선을 **지금 코드로** 다시 만들면 안 된다 (그러면 지금 코드와 지금 코드를 비교해 아무것도 지키지 못한다).
`--regenerate-from-base` 가 단계 전 커밋(BASE_COMMIT)의 코드를 임시 git worktree 에 꺼내 그 코드로 같은 환경에서 기준선을 다시 찍고,
결과 JSON 만 이 저장소로 복사한 뒤 worktree 를 지운다. 그 다음 시험이 지금 코드와 비교한다. 지금 코드에서 `--write` 는 거부한다.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
GOLDEN = Path(__file__).resolve().parent / "golden" / "none-new.json"
SPECS = ("ok-layout.json", "bad-layout.json")
NOTE = "환경(Chromium·폰트·ffmpeg)이 바뀌면 바뀌기 전 코드에서 --write 로 다시 만든다"
BASE_COMMIT = "3fde951"   # none 렌더 코드를 고치기 전(Phase 4 소스 수정 전) 기준선을 처음 찍은 커밋
REGENERATE = ("픽셀 해시만 다르고 Chromium·폰트·ffmpeg 가 바뀌었다면 기준선을 지금 코드로 다시 만들지 말고 "
              f"`python3 tools/tests/none_guard.py --regenerate-from-base` 로 단계 전 커밋 {BASE_COMMIT} 의 코드에서 다시 찍는다 "
              "(tools/README.md '모션 none 기준선'). 환경이 그대로인데 다르면 코드 회귀다")
CODE_REGRESSION = "환경과 관계없는 항목이다: none 경로 코드가 바뀌었다 — 기준선을 다시 만들지 말고 코드를 고친다"
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


def regenerate_from_base():
    """BASE_COMMIT 의 코드를 임시 worktree 에 꺼내 그 none_guard.py --write 로 기준선을 찍고 GOLDEN 으로 복사한다."""
    repo = TOOLS.parent
    tmp = Path(tempfile.mkdtemp(prefix="none-base-"))
    wt = tmp / "wt"
    r = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(wt), BASE_COMMIT],
                       capture_output=True, text=True)
    if r.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"단계 전 커밋 {BASE_COMMIT} 을 꺼내지 못함: {r.stderr.strip()}", file=sys.stderr)
        return 1
    try:
        r = subprocess.run([sys.executable, str(wt / "tools" / "tests" / "none_guard.py"), "--write"],
                           cwd=str(wt), capture_output=True, text=True)
        if r.returncode != 0:
            print(f"단계 전 코드로 기준선을 찍지 못함:\n{r.stdout}{r.stderr}", file=sys.stderr)
            return 1
        data = (wt / "tools" / "tests" / "golden" / GOLDEN.name).read_text(encoding="utf-8")
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(data, encoding="utf-8")
        print(f"기준선 기록 (커밋 {BASE_COMMIT} 의 코드, 이 환경): {GOLDEN}")
        return 0
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "prune"], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="none 새 배치 기준선")
    ap.add_argument("--write", action="store_true",
                    help=f"기준선 JSON 을 지금 코드로 쓴다 — 거부됨 (단계 전 커밋 {BASE_COMMIT} 의 코드만 쓸 수 있다)")
    ap.add_argument("--regenerate-from-base", action="store_true",
                    help=f"단계 전 커밋 {BASE_COMMIT} 의 코드를 임시 worktree 에 꺼내 이 환경에서 기준선을 다시 찍는다")
    args = ap.parse_args(argv)
    if args.regenerate_from_base:
        return regenerate_from_base()
    if args.write:
        print(f"지금 코드로 기준선을 쓰지 않음 — {REGENERATE}", file=sys.stderr)
        return 1
    # 인자 없이: 지금 코드의 값을 stdout 으로만 낸다 (기준선 파일은 쓰지 않음, 비교용)
    print(json.dumps(capture_all(), ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
