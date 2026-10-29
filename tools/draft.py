"""키움멘토 릴스 초안 도구 (원고 소스 확장, 수치 등록부)
사용: python3 tools/draft.py expand SRC OUT [--registry PATH]
  expand  자리표시자 `{{이름|서식}}` 가 든 원고 소스(SRC)를 등록부·계산 모듈로 채워 v1 호환 원고(OUT)로 쓴다.
          OUT 에는 숫자마다 출처를 적은 `figures` 장부와 쓰인 등록부 항목 `basis_items` 가 함께 들어간다.
          OUT 은 `python3 tools/reel.py OUT out.mp4 --layout new` 로 그대로 렌더할 수 있다.
종료 코드: 0 정상, 1 원고·등록부 입력 오류(파일 없음, JSON 오류, 규칙 위반), 2 환경 오류(파일 쓰기 실패 등)
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reelkit import calc, expand, figures  # noqa: E402


def build_parser():
    ap = argparse.ArgumentParser(description="릴스 초안 도구")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("expand", help="원고 소스의 자리표시자를 채워 원고 JSON 을 쓴다")
    p.add_argument("src", help="원고 소스 JSON 경로")
    p.add_argument("out", help="출력 원고 JSON 경로")
    p.add_argument("--registry", default=str(figures.REGISTRY_PATH), help="수치 등록부 경로 (기본 tools/data/figures.json)")
    return ap


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


def main(argv=None):
    args = build_parser().parse_args(argv)
    return {"expand": cmd_expand}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
