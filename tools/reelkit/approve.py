"""사람 승인 기록과 정식 경로로 옮기기 (표준 라이브러리만 사용, BNDL-06, D-15, D-16).

approve 는 사람이 대화형 터미널에서만 실행한다 (Claude 실행 금지). 그때의 점검 결과·사람 기록·파일 지문(sha256)을
approval.json 으로 남긴다. promote 는 그 승인 기록이 있고, 지문이 그대로이고, 지금 규칙으로 다시 훑어도 수정 필요가 0건일 때만
영상·표지·원고·게시글을 게시 폴더로 옮긴다. 이미 있는 파일은 덮어쓰지 않고 git 은 부르지 않는다 (커밋은 사람 몫).
다시 만든 묶음(bundle)은 시작할 때 approval.json 을 지우므로 이전 승인은 자동으로 무효가 된다.
종료 코드: 0 정상, 1 거부·입력 오류, 2 파일 환경 오류.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from . import bundle, compliance, constants, figures, review
from .spec import SpecError, load_spec

# 옮기는 네 파일과 출처 확인용 여섯 파일. bundle.draft_paths 의 키 이름이다. 사람이 읽은 review.md 와, 묶음 산출물 지문을
# 담은 bundle.json 도 승인 지문에 넣는다 (WR-02). record.json 은 사람이 고치는 파일이라 넣지 않는다 (사본을 approval.json 에 둠).
PROMOTED_KEYS = ("mp4", "cover", "spec", "caption")
PROVENANCE_KEYS = ("spec_src", "caption_src", "check", "compliance", "review", "bundle")


def _names(draft_dir):
    p = bundle.draft_paths(draft_dir)
    return p, [p[k].name for k in PROMOTED_KEYS], [p[k].name for k in PROMOTED_KEYS + PROVENANCE_KEYS]


class ApproveError(ValueError):
    """거부 사유. 메시지는 한국어."""


def hashed_names(draft_dir):
    return _names(draft_dir)[2]


PROMOTED = PROMOTED_KEYS
HASHED = PROMOTED_KEYS + PROVENANCE_KEYS


sha256_file = bundle.sha256_file


def check_outputs(paths, info):
    """bundle.json 의 outputs 지문과 지금 파일을 대조한다. 묶음 뒤 손으로 고친 파일이 있으면 거부한다 (WR-02)."""
    outputs = info.get("outputs")
    names = {paths[k].name for k in bundle.OUTPUT_KEYS}
    if not isinstance(outputs, dict) or set(outputs) != names:
        raise ApproveError("bundle.json 에 산출물 지문이 없거나 목록이 다름 — bundle 을 다시 실행하세요")
    for key in bundle.OUTPUT_KEYS:
        p = paths[key]
        if p.is_symlink() or not p.is_file() or sha256_file(p) != outputs[p.name]:
            raise ApproveError(f"묶음을 만든 뒤 바뀜: {p.name} — 손으로 고치지 말고 bundle 을 다시 실행하세요")


def file_hashes(draft_dir):
    """{파일 이름: sha256} (HASHED 순서). 없거나 심볼릭 링크이거나 폴더 밖으로 풀리면 거부한다 (T-03-15)."""
    d = Path(draft_dir).resolve()
    paths = bundle.draft_paths(d)
    out = {}
    for key in HASHED:
        p = paths[key]
        if p.is_symlink():
            raise ApproveError(f"심볼릭 링크는 쓸 수 없음: {p.name}")
        if not p.is_file():
            raise ApproveError(f"파일 없음: {p.name} — bundle 을 다시 실행하세요")
        if p.resolve().parent != d:
            raise ApproveError(f"초안 폴더 밖 파일: {p.name}")
        out[p.name] = sha256_file(p)
    return out


def _load_rules():
    """승인·옮기기의 수정 필요 판정은 언제나 저장소의 규칙 파일로 한다. 호출하는 쪽이 규칙을 고를 수 없다 (CR-03)."""
    return compliance.load_rules(compliance.RULES_PATH)


def _bundle_rules_sha(paths):
    """묶음을 만들 때 쓴 규칙 파일의 sha256 (compliance.json 기록). 읽을 수 없으면 None."""
    try:
        data = json.loads(paths["compliance"].read_text(encoding="utf-8"))
        return data["rules"]["sha256"]
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError):
        return None


def live_scan(d, rules):
    """지금 규칙으로 spec.json + caption.txt (+ check.json) 를 다시 훑는다. 저장된 건수는 믿지 않는다 (T-03-16)."""
    paths = bundle.draft_paths(d)
    spec = load_spec(paths["spec"])
    text = paths["caption"].read_text(encoding="utf-8")
    check_json = json.loads(paths["check"].read_text(encoding="utf-8"))
    return compliance.run(spec, text, rules, check_json=check_json)


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _bundle_complete(paths):
    try:
        data = json.loads(paths["bundle"].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("status") == "complete" else None


def approve_cli(draft_dir, by):
    """D-15: 사람만 승인한다. 대화형 터미널이 아니면 어떤 일도 하기 전에 거부한다."""
    if not sys.stdin.isatty():
        print("승인 오류: approve 는 사람이 대화형 터미널에서만 실행할 수 있음 (Claude 실행 금지)", file=sys.stderr)
        return 1
    try:
        d, _date, name = bundle.validate_draft_dir(draft_dir)
        publish_dir(d, name)
    except (bundle.BundleError, ApproveError) as e:
        print(f"승인 오류: {e}", file=sys.stderr)
        return 1
    who = (by or "").strip()
    if not who:
        print("승인 오류: --by 승인자 이름이 비어 있음", file=sys.stderr)
        return 1
    if figures.is_ai_name(who):
        print("승인 오류: 승인자는 사람 이름이어야 함 (Claude/AI 이름 거부)", file=sys.stderr)
        return 1
    paths = bundle.draft_paths(d)
    info = _bundle_complete(paths)
    if info is None:
        print("승인 오류: bundle.json 이 없거나 완료(complete) 상태가 아님 — bundle 을 다시 실행하세요", file=sys.stderr)
        return 1
    try:
        check_outputs(paths, info)
        loaded = _load_rules()
        hashes = file_hashes(d)
        result = live_scan(d, loaded)
    except (compliance.RuleError, ApproveError, SpecError, ValueError, OSError) as e:
        print(f"승인 오류: {e}", file=sys.stderr)
        return 1
    n_fix = result.counts["수정 필요"]
    if n_fix > 0:
        print(f"승인 오류: 수정 필요 {n_fix}건 — spec.src.json·caption.src.json 을 고치고 bundle 을 다시 실행", file=sys.stderr)
        return 1
    if _bundle_rules_sha(paths) != loaded.sha256:
        print("승인 오류: 묶음이 저장소 규칙 파일과 다른 규칙으로 점검됨 — --rules 없이 bundle 을 다시 실행", file=sys.stderr)
        return 1
    record, problem = review.ensure_record(d)
    print(f"[{name}]", file=sys.stderr)
    print(f"  {result.headline}", file=sys.stderr)
    print(f"  {result.counts_line}", file=sys.stderr)
    print("  광고·심의 기록 (record.json):", file=sys.stderr)
    for key, value in record.items():
        mark = " ← 미확인" if value == "미확인" else ""
        print(f"    {key}: {value}{mark}", file=sys.stderr)
    if problem:
        print(f"  주의: {problem}", file=sys.stderr)
    code = info.get("exit_code")
    if code == 3:
        print("  주의: bundle 종료 코드 3 — 레이아웃·표지 경고가 있었음 (review.md 확인)", file=sys.stderr)
    elif code == 4:
        print("  주의: bundle 종료 코드 4 — 업로드 규격 FAIL 이 있었음 (review.md 확인)", file=sys.stderr)
    print("  지문을 기록할 파일:", file=sys.stderr)
    for fname in hashes:
        print(f"    {fname}", file=sys.stderr)
    try:
        typed = input(f"승인하려면 폴더 이름({name})을 다시 입력하세요: ")
    except EOFError:
        typed = ""
    if typed.strip() != name:
        print("승인 오류: 입력한 폴더 이름이 다름 — 승인하지 않음", file=sys.stderr)
        return 1
    try:
        again = file_hashes(d)
    except ApproveError as e:
        print(f"승인 오류: {e}", file=sys.stderr)
        return 1
    if again != hashes:
        print("승인 오류: 확인하는 사이 파일이 바뀜 — 승인하지 않음", file=sys.stderr)
        return 1
    data = {"schema": 1, "name": name, "approved_by": who, "approved_at": _now_iso(),
            "rules": {"version": loaded.version, "sha256": loaded.sha256},
            "counts": result.counts, "record": record, "files": hashes}
    try:
        bundle._atomic_write(paths["approval"], bundle._json_text(data))
    except OSError as e:
        print(f"환경 오류: approval.json 을 쓸 수 없음: {e}", file=sys.stderr)
        return 2
    print(f"approve: {name} 승인 기록 ({who}) — 옮기기: python3 tools/draft.py promote {draft_dir}")
    return 0


def _read_approval(paths, name):
    try:
        data = json.loads(paths["approval"].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise ApproveError("승인 기록 없음 — 사람이 approve 를 먼저 실행해야 함") from None
    if (not isinstance(data, dict) or data.get("schema") != 1 or data.get("name") != name
            or not isinstance(data.get("files"), dict) or not isinstance(data.get("rules"), dict)):
        raise ApproveError("승인 기록 없음 — 사람이 approve 를 먼저 실행해야 함")
    return data


def publish_dir(d, name):
    """게시 폴더는 언제나 저장소의 `<게시일 연도>/reels` 다 (WR-04). 초안 폴더가 그 아래 drafts/ 에 있지 않으면 거부한다.
    d 는 bundle.validate_draft_dir 이 풀어 둔(resolve) 경로라 심볼릭 링크로 옮겨 둔 drafts/ 도 여기서 걸린다."""
    expected = (constants.REPO_ROOT / name[:4] / "reels").resolve()
    if d.parent.parent != expected:
        raise ApproveError(f"초안 폴더가 게시일 연도({name[:4]})의 게시 폴더 아래가 아님: {expected}/drafts/{name} 이어야 함")
    return expected


def _targets(d, name):
    reels = publish_dir(d, name)
    paths = bundle.draft_paths(d)
    return reels, [
        (paths["mp4"], reels / f"{name}.mp4"),
        (paths["cover"], reels / f"{name}-cover.png"),
        (paths["spec"], reels / "specs" / f"{name}.json"),
        (paths["caption"], reels / "captions" / f"{name}.txt"),
    ]


def promote_cli(draft_dir):
    """D-16: 승인된, 그대로인, 수정 필요 0건인 네 파일만 게시 경로로 옮긴다. 덮어쓰지 않고 git 도 부르지 않는다."""
    try:
        d, _date, name = bundle.validate_draft_dir(draft_dir)
        publish_dir(d, name)
    except (bundle.BundleError, ApproveError) as e:
        print(f"옮기기 오류: {e}", file=sys.stderr)
        return 1
    paths = bundle.draft_paths(d)
    try:
        approval = _read_approval(paths, name)
        files = approval["files"]
        expected = set(hashed_names(d))
        if set(files) != expected:
            raise ApproveError("승인 기록의 파일 목록이 맞지 않음 — 사람이 approve 를 다시 실행해야 함")
        current = {}
        for fname in files:
            if (d / fname).is_symlink() or not (d / fname).is_file():
                raise ApproveError(f"승인 뒤 바뀜: {fname} — bundle 을 다시 실행하고 다시 승인 받으세요")
        for fname, digest in files.items():
            current[fname] = sha256_file(d / fname)
            if current[fname] != digest:
                raise ApproveError(f"승인 뒤 바뀜: {fname} — bundle 을 다시 실행하고 다시 승인 받으세요")
        file_hashes(d)   # 심볼릭 링크·폴더 밖 경로 거부
        loaded = _load_rules()
        if approval["rules"].get("sha256") != loaded.sha256:
            raise ApproveError("승인 때와 점검 규칙 파일이 다름 — bundle 을 다시 실행하고 사람이 approve 를 다시 실행해야 함")
        result = live_scan(d, loaded)
        if result.counts["수정 필요"] > 0:
            raise ApproveError(f"수정 필요 {result.counts['수정 필요']}건 — spec.src.json·caption.src.json 을 고치고 "
                               "bundle 을 다시 실행해 다시 승인 받으세요")
        reels, pairs = _targets(d, name)
        for _src, target in pairs:
            if os.path.lexists(target):
                raise ApproveError(f"이미 게시된 파일 — 덮어쓰지 않음: {target}")
    except (ApproveError, compliance.RuleError, SpecError, ValueError, OSError) as e:
        print(f"옮기기 오류: {e}", file=sys.stderr)
        return 1

    linked, parts, made_dirs = [], [], []
    try:
        for sub in ("specs", "captions"):
            if not (reels / sub).exists():
                (reels / sub).mkdir()
                made_dirs.append(reels / sub)
        for src, target in pairs:
            part = target.with_name(f".{target.name}.part")
            parts.append(part)
            with open(src, "rb") as fin, open(part, "xb") as fout:
                fout.write(fin.read())
            if sha256_file(part) != files[src.name]:
                raise ApproveError(f"복사본 지문이 승인 기록과 다름: {src.name}")
            os.link(part, target)   # 이미 있으면 FileExistsError — 교체하지 않는다
            linked.append(target)
            part.unlink()
    except (ApproveError, FileExistsError) as e:
        _rollback(linked, parts, made_dirs)
        text = f"이미 게시된 파일 — 덮어쓰지 않음: {e.filename}" if isinstance(e, FileExistsError) else str(e)
        print(f"옮기기 오류: {text}", file=sys.stderr)
        return 1
    except OSError as e:
        _rollback(linked, parts, made_dirs)
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 2
    for _src, target in pairs:
        print(f"git add {target}")
    print(f"promote: {name} → 4개 파일 (커밋은 사람이 직접)")
    return 0


def _rollback(linked, parts, made_dirs):
    for p in linked + parts:
        try:
            p.unlink()
        except OSError:
            pass
    for dd in made_dirs:
        try:
            dd.rmdir()
        except OSError:
            pass
