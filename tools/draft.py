"""키움멘토 릴스 초안 도구 (원고 소스 확장, 수치 등록부)
사용: python3 tools/draft.py expand SRC OUT [--registry PATH]
      python3 tools/draft.py check SPEC [--out JSON] [--registry PATH] [--date YYYY-MM-DD] [--strict] [--legacy]
      python3 tools/draft.py figures {list [--grep 글자] | show ID | add ... | confirm ID --by 이름 [--date YYYY-MM-DD]}
  expand  자리표시자 `{{이름|서식}}` 가 든 원고 소스(SRC)를 등록부·계산 모듈로 채워 v1 호환 원고(OUT)로 쓴다.
          OUT 에는 숫자마다 출처를 적은 `figures` 장부와 쓰인 등록부 항목 `basis_items` 가 함께 들어간다.
          OUT 은 `python3 tools/reel.py OUT out.mp4 --layout new` 로 그대로 렌더할 수 있다.
  check   확장된 원고(SPEC)의 숫자가 모두 등록부·입력·계산에서 왔는지 따라가 점검한다 (D-07).
          등록부 밖 숫자는 오류(종료 1), 미확인 수치를 쓴 줄은 `확인 필요` 로 적을 뿐 막지 않는다 (D-03).
          --out 을 주면 오류가 있어도 check.json 을 쓴다. --strict 는 경고가 있으면 종료 3.
          --date 는 게시 예정일(기본 오늘): 등록부 valid_until 이 이보다 이르면 EXPIRED 경고.
          --legacy 는 게시된 v1 원고(장부 없음)용 보고 전용: 등록부 없는 수치 숫자 개수만 알리고 종료 0, 원고는 고치지 않는다.
  figures 수치 등록부(tools/data/figures.json) 조회·추가·확인.
          add      새 수치를 추가한다. 확인 상태는 항상 `미확인` 이고 지정하는 옵션이 없다 (D-02).
          confirm  사람 확인자 전용이다 (D-02). 1차 출처(law.go.kr 등)를 직접 열어 값을 맞춰 본 사람이 확인자 이름으로
                   실행한다. Claude 는 이 명령을 실행하면 안 된다. 빈 이름과 Claude/AI 이름은 거부된다.
종료 코드: 0 정상, 1 원고·등록부 입력 오류(파일 없음, JSON 오류, 규칙 위반, check 의 오류), 2 환경 오류(파일 쓰기 실패 등)
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reelkit import calc, check, expand, figures  # noqa: E402
from reelkit.spec import SpecError, load_spec  # noqa: E402


def build_parser():
    ap = argparse.ArgumentParser(description="릴스 초안 도구")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("expand", help="원고 소스의 자리표시자를 채워 원고 JSON 을 쓴다")
    p.add_argument("src", help="원고 소스 JSON 경로")
    p.add_argument("out", help="출력 원고 JSON 경로")
    _registry_arg(p)

    p = sub.add_parser("check", help="확장된 원고의 숫자를 등록부에 대조해 점검한다")
    p.add_argument("spec", help="확장된 원고 JSON 경로")
    p.add_argument("--out", help="check.json 을 쓸 경로 (오류가 있어도 씀)")
    p.add_argument("--strict", action="store_true", help="경고가 있으면 종료 코드 3")
    p.add_argument("--date", help="게시 예정일 YYYY-MM-DD (기본 오늘) — valid_until 만료 경고 기준")
    p.add_argument("--legacy", action="store_true", help="게시된 v1 원고: 수치 숫자 개수만 보고하고 종료 0")
    _registry_arg(p)

    fp = sub.add_parser("figures", help="수치 등록부 조회·추가·확인")
    fsub = fp.add_subparsers(dest="figures_command", required=True)

    p = fsub.add_parser("list", help="등록부 항목을 한 줄씩 보인다")
    p.add_argument("--grep", help="id 또는 label 에 이 글자가 든 항목만")
    _registry_arg(p)

    p = fsub.add_parser("show", help="항목 하나를 JSON 으로 보인다")
    p.add_argument("id")
    _registry_arg(p)

    p = fsub.add_parser("add", help="새 수치를 추가한다 (항상 미확인)")
    p.add_argument("--id", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--kind", required=True, choices=figures.KINDS)
    p.add_argument("--value", required=True, help="Decimal 로 읽히는 숫자 (돈은 원, 비율은 퍼센트)")
    p.add_argument("--unit", default="", choices=figures.UNITS)
    p.add_argument("--source-name", required=True)
    p.add_argument("--source-url")
    p.add_argument("--candidate-source", action="append", default=[], help="사람이 확인할 후보 출처 (여러 번 지정 가능)")
    p.add_argument("--as-of", help="기준일 YYYY, YYYY-MM 또는 YYYY-MM-DD")
    p.add_argument("--legal-status", required=True, choices=figures.LEGAL_STATUSES)
    p.add_argument("--includes-local", action="store_true", help="지방소득세 포함 값")
    p.add_argument("--valid-until", help="이 날짜 이후 게시면 재확인 (YYYY-MM-DD)")
    p.add_argument("--notes", default="")
    _registry_arg(p)

    p = fsub.add_parser(
        "confirm", help="[사람 확인자 전용 — Claude 는 실행 금지] 1차 출처로 확인한 수치를 확인 상태로 바꾼다")
    p.add_argument("id")
    p.add_argument("--by", required=True, help="확인한 사람 이름 (Claude/AI 이름은 거부됨)")
    p.add_argument("--date", help="확인일 YYYY-MM-DD (기본 오늘)")
    _registry_arg(p)
    return ap


def _registry_arg(p):
    p.add_argument("--registry", default=str(figures.REGISTRY_PATH), help="수치 등록부 경로 (기본 tools/data/figures.json)")


def _read_json(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        reason = getattr(e, "strerror", None) or str(e)
        raise ValueError(f"원고 소스를 열 수 없음: {path} ({reason})") from e
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"원고 소스 JSON 형식 오류: {path} 줄 {e.lineno} 열 {e.colno}") from e


def cmd_expand(args):
    try:
        src = _read_json(args.src)
        registry = figures.load_registry(args.registry)
        spec = expand.expand_source(src, registry)
    except (figures.RegistryError, expand.ExpandError, calc.CalcError, ValueError) as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    try:
        expand.write_spec(spec, args.out)
    except OSError as e:
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 2
    print(f"expand: {args.out} 숫자 {len(spec['figures'])}개 · 등록부 id {len(spec['basis_items'])}개")
    return 0


def _write_check_json(args, report, registry_path):
    try:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(report.to_json(args.spec, registry_path), ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
    except OSError as e:
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 2
    return 0


def cmd_check(args):
    publish_date = None
    if args.date:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
            print(f"원고 오류: --date 는 YYYY-MM-DD 형식이어야 함: {args.date}", file=sys.stderr)
            return 1
        try:
            publish_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"원고 오류: --date 가 없는 날짜임: {args.date}", file=sys.stderr)
            return 1
    try:
        spec = load_spec(args.spec)
        registry = None if args.legacy else figures.load_registry(args.registry)
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    except figures.RegistryError as e:
        print(f"등록부 오류: {e}", file=sys.stderr)
        return 1
    if args.legacy:
        report = check.legacy_report(spec)
        if args.out and _write_check_json(args, report, None):
            return 2
        print(f"check(legacy): {report.summary()}")
        return 0
    report = check.check_spec(spec, registry, publish_date=publish_date)
    for issue in report.errors + report.warnings:
        print(str(issue), file=sys.stderr)
        if issue.kind in check.HINTS and issue.kind != "NOT_EXPANDED":
            print(f"  -> {check.HINTS[issue.kind]}", file=sys.stderr)
    for item in report.needs_check:
        print(f'확인 필요: {item["where"]} [{", ".join(item["ids"])}] "{item["text"]}"')
    if args.out and _write_check_json(args, report, args.registry):
        return 2
    print(f"check: {report.summary()}")
    if report.errors:
        return 1
    if args.strict and report.warnings:
        return 3
    return 0


def _registry_command(fn):
    """등록부 하위 명령 공통 처리: RegistryError -> '등록부 오류' 종료 코드 1, 파일 쓰기 실패 -> 종료 코드 2."""
    def run(args):
        try:
            return fn(args)
        except figures.RegistryError as e:
            print(f"등록부 오류: {e}", file=sys.stderr)
            return 1
        except OSError as e:
            print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
            return 2
    return run


@_registry_command
def cmd_figures_list(args):
    reg = figures.load_registry(args.registry)
    needle = (args.grep or "").lower()
    for fid, e in reg["figures"].items():
        if needle and needle not in fid.lower() and needle not in e["label"].lower():
            continue
        value = f"{e['value']} {e['unit']}".strip()
        print(f"{fid}  {value}  {e['legal_status']}  {e['verified']}  {e['label']}")
    return 0


@_registry_command
def cmd_figures_show(args):
    reg = figures.load_registry(args.registry)
    print(json.dumps(figures.get_figure(reg, args.id), ensure_ascii=False, indent=2))
    return 0


@_registry_command
def cmd_figures_add(args):
    reg = figures.load_registry(args.registry)
    fields = {
        "label": args.label, "kind": args.kind, "value": args.value, "unit": args.unit,
        "includes_local": args.includes_local,
        "source": {"name": args.source_name, "url": args.source_url, "locator": None},
        "candidate_sources": args.candidate_source, "as_of": args.as_of, "valid_until": args.valid_until,
        "legal_status": args.legal_status, "notes": args.notes,
    }
    figures.add_figure(reg, args.id, fields, date.today().isoformat())
    figures.save_registry(reg, args.registry)
    print(f"figures add: {args.id} 추가 (미확인) — 사람이 1차 출처로 확인하기 전까지 미확인으로 남음")
    return 0


@_registry_command
def cmd_figures_confirm(args):
    reg = figures.load_registry(args.registry)
    on = args.date or date.today().isoformat()
    figures.confirm_figure(reg, args.id, args.by, on)
    figures.save_registry(reg, args.registry)
    print(f"figures confirm: {args.id} 확인 ({on}, {args.by.strip()})")
    return 0


FIGURES_COMMANDS = {"list": cmd_figures_list, "show": cmd_figures_show, "add": cmd_figures_add,
                    "confirm": cmd_figures_confirm}


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "figures":
        return FIGURES_COMMANDS[args.figures_command](args)
    if args.command == "check":
        return cmd_check(args)
    return cmd_expand(args)


if __name__ == "__main__":
    sys.exit(main())
