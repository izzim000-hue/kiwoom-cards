"""키움멘토 릴스 초안 도구 (원고 소스 확장, 수치 등록부)
사용: python3 tools/draft.py expand SRC OUT [--registry PATH]
      python3 tools/draft.py check SPEC [--out JSON] [--src SRC] [--registry PATH] [--date YYYY-MM-DD] [--strict] [--legacy] [--card CARD]
      python3 tools/draft.py convert CARD [--out JSON]
      python3 tools/draft.py caption SPEC SRC --out TXT [--config PATH] [--registry PATH]
      python3 tools/draft.py slot [--date YYYY-MM-DD] [--slug 영문-슬러그] [--reels-dir DIR] [--create]
      python3 tools/draft.py bundle DIR [--card CARD] [--request-start EPOCH] [--rules PATH] [--registry PATH] [--config PATH]
      python3 tools/draft.py compliance SPEC [--caption TXT] [--check JSON] [--rules PATH] [--out JSON]
      python3 tools/draft.py redteam [--rules PATH] [--corpus PATH] [--heldout PATH] [--json]
      python3 tools/draft.py figures {list [--grep 글자] | show ID | add ... | confirm ID --by 이름 [--date YYYY-MM-DD]}
  expand  자리표시자 `{{이름|서식}}` 가 든 원고 소스(SRC)를 등록부·계산 모듈로 채워 v1 호환 원고(OUT)로 쓴다.
          OUT 에는 숫자마다 출처를 적은 `figures` 장부와 쓰인 등록부 항목 `basis_items` 가 함께 들어간다.
          OUT 은 `python3 tools/reel.py OUT out.mp4 --layout new` 로 그대로 렌더할 수 있다.
  check   확장된 원고(SPEC)의 숫자가 모두 등록부·입력·계산에서 왔는지 따라가 점검한다 (D-07).
          원고 속 장부를 믿지 않고 장부의 참조·서식을 지금 등록부와 원고의 inputs·derive 로 다시 계산해 맞춰 본다.
          SPEC 옆에 원고 소스(<이름>.src.json, 또는 --src)가 있으면 다시 확장한 결과와도 대조한다.
          등록부 밖 숫자는 오류(종료 1), 미확인 수치를 쓴 줄은 `확인 필요` 로 적을 뿐 막지 않는다 (D-03).
          inputs(가정)를 쓴 줄은 `가정 수치` 로 적고, 그 줄이나 basis 에 예시·가정·가상 표기가 없으면 오류다.
          --out 을 주면 오류가 있어도 check.json 을 쓴다. --strict 는 경고가 있으면 종료 3.
          --date 는 게시 예정일(기본 오늘): 등록부 valid_until 이 이보다 이르면 EXPIRED 경고.
          --legacy 는 게시된 v1 원고(장부 없음)용 보고 전용: 등록부 없는 수치 숫자 개수만 알리고 종료 0, 원고는 고치지 않는다.
          version·series·inputs·derive·figures·basis_items 중 하나라도 있는 원고(v2 초안)에는 --legacy 를 쓸 수 없다.
          --card 는 카드뉴스 원고(spec.json)와 대조한다: 릴스에만 있는 숫자는 NOT_IN_CARD, 릴스에 옮겨지지 않은 카드 note 는
          CARD_NOTE_DROPPED 경고(--strict 규칙은 다른 경고와 같음). --legacy 와 함께 쓸 수 있다.
  convert  카드뉴스 원고(CARD)를 릴스 골격 JSON(시리즈, 장면 역할, 카드 재료, note, 카드 숫자)으로 바꿔 stdout 또는 --out 에 쓴다.
  caption  원고(SPEC)와 게시글 문구 원본(SRC: hook, summary 3줄, hashtags)으로 게시글 caption.txt 를 조립한다 (D-11 순서).
          시리즈명·회차·다음 편은 원고의 series 에서만 가져온다. 해시태그는 브랜드 태그 포함 최대 5개, 전체 2,200자 이하.
          게시글 문구의 숫자는 원고 장부에 있는 숫자여야 하고, 미확인 수치를 쓴 줄은 `확인 필요` 경고, 발의 수치는 같은 줄에
          발의안·개정안·정부안 표기가 필요하다. 원고 점검(check)에 오류가 있으면 조립하지 않는다.
          면책·CTA 문구는 준법 검토 전 초안이다.
  slot    게시일과 영문 슬러그를 제안하고 게시된 릴스·기존 초안과의 충돌을 알린다 (JSON). 날짜는 폴더를 읽어 계산한다.
          --create 는 --date 와 --slug 가 필요하고 `2026/reels/drafts/<날짜>-<슬러그>/` 만 만든다 (D-14).
  bundle  초안 폴더(2026/reels/drafts/<게시일>-<슬러그>/, spec.src.json 과 caption.src.json 이 든 곳) 하나를 검수 묶음으로 만든다.
          expand -> check -> caption -> 표현 점검 -> 렌더(new 배치, 같은 프로세스) -> 표지 -> review.md 순서로 spec.json, check.json,
          caption.txt, compliance.json, <이름>.mp4, <이름>-cover.png, review.md, record.json, bundle.json 을 폴더에 쓴다.
          표현 점검은 tools/data/compliance_rules.json 규칙(초안, 준법 검토 전)을 원고·근거·게시글·해시태그에 적용하고 결과는
          `위험 표현 n건 발견` 또는 `패턴상 발견 없음 — 사람 검수 필요` 둘 중 하나로만 낸다. 발견이 있어도 종료 코드는 바뀌지 않는다.
          원고 소스를 고친 뒤에도 같은 명령으로 전부 다시 만든다. record.json(광고 해당 여부·심의 기록)은 없을 때만 만들고 고치지 않는다.
          --request-start 는 요청 시각(epoch 초)으로, 주어지면 bundle.json 에 요청부터 걸린 시간을 남긴다 (없으면 slot --create 가 남긴 created.json).
          종료 코드: 0 완료, 1 입력 오류(점검 오류 포함), 2 렌더·파일 환경 오류, 3 레이아웃 경고, 4 업로드 규격 FAIL (4 우선).
  compliance  원고(SPEC)와 게시글(--caption)을 금소법 표현 규칙(tools/data/compliance_rules.json, 초안·준법 검토 전)으로 점검한다.
          결과 머리말은 `위험 표현 n건 발견` 또는 `패턴상 발견 없음 — 사람 검수 필요` 둘 중 하나이며 규칙 버전·기준일이 붙는다.
          발견마다 위치·문제 표현·사유·대체 표현 제안을 보이고 원고·게시글 파일은 고치지 않는다 (제안만). 발견이 있어도 종료 0.
          --check 는 draft.py check 의 check.json 으로, 확인 필요·가정·경고를 그대로 옮겨 싣는다. --out 은 compliance.json 을 쓴다.
          종료 코드: 0 정상, 1 규칙 파일·입력 오류(규칙 id 를 밝힘), 2 --out 쓰기 실패.
  redteam 점검 규칙의 탐지율·오탐 보고서를 한국어로 낸다 (COMP-04): 기존 10편(골든 기준표의 재현 가능 항목), 가상 문장 표본
          (tools/tests/redteam/corpus.json, 표본 내), 규칙을 보지 않고 먼저 써 둔 따로 쓴 문장(heldout.json, 규칙 조정에 쓰지 않음).
          표본 내 수치는 실제보다 높게 나오므로 따로 쓴 문장 줄을 함께 본다. 키워드·패턴 방식이라 암시적 표현은 잡지 못한다.
          --json 은 같은 숫자를 JSON 객체 하나로 낸다. 종료 코드: 0 보고서 출력, 1 말뭉치·규칙 파일 오류.
  figures 수치 등록부(tools/data/figures.json) 조회·추가·확인.
          add      새 수치를 추가한다. 확인 상태는 항상 `미확인` 이고 지정하는 옵션이 없다 (D-02).
          confirm  사람 확인자 전용이다 (D-02). 1차 출처(law.go.kr 등)를 직접 열어 값을 맞춰 본 사람이 확인자 이름으로
                   실행한다. Claude 는 이 명령을 실행하면 안 된다. 대화형 터미널에서만 실행되고 id 를 다시 입력해야 한다.
                   확인일은 발견일 이후·오늘 이전이어야 한다. 빈 이름과 Claude/AI 이름도 거부되지만 이 이름 검사는
                   실수 방지일 뿐이다. figures.json 을 직접 고친 `확인` 의 기록 문제는 check 와 figures list 가 오류로 알린다.
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

from reelkit import calc, caption, check, convert, expand, figures, slot  # noqa: E402
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
    p.add_argument("--card", help="대조할 카드뉴스 원고 JSON (NOT_IN_CARD, CARD_NOTE_DROPPED 경고)")
    p.add_argument("--src", help="원고 소스 JSON (기본: SPEC 옆의 <이름>.src.json 이 있으면 그것). 다시 확장해 대조한다")
    _registry_arg(p)

    p = sub.add_parser("caption", help="원고와 문구 원본으로 게시글 caption.txt 를 쓴다")
    p.add_argument("spec", help="확장된 원고 JSON 경로")
    p.add_argument("src", help="게시글 문구 원본 JSON 경로 (hook, summary, hashtags)")
    p.add_argument("--out", required=True, help="caption.txt 를 쓸 경로")
    p.add_argument("--config", default=str(caption.CONFIG_PATH), help="게시글 설정 경로 (기본 tools/data/caption_config.json)")
    _registry_arg(p)

    p = sub.add_parser("compliance", help="원고·게시글을 금소법 표현 규칙으로 점검한다 (제안만, 파일은 고치지 않음)")
    p.add_argument("spec", help="확장된 원고 JSON 경로")
    p.add_argument("--caption", help="게시글 caption.txt 경로")
    p.add_argument("--check", help="draft.py check 가 쓴 check.json 경로 (확인 필요·가정·경고를 옮김)")
    p.add_argument("--rules", help="규칙 파일 (기본 tools/data/compliance_rules.json)")
    p.add_argument("--out", help="compliance.json 을 쓸 경로")

    p = sub.add_parser("redteam", help="점검 규칙의 탐지율·오탐 보고서 (기존 10편, 표본, 따로 쓴 문장)")
    p.add_argument("--rules", help="규칙 파일 (기본 tools/data/compliance_rules.json)")
    p.add_argument("--corpus", help="표본 말뭉치 (기본 tools/tests/redteam/corpus.json)")
    p.add_argument("--heldout", help="따로 쓴 문장 (기본 tools/tests/redteam/heldout.json, 규칙 조정에 쓰지 않음)")
    p.add_argument("--json", action="store_true", help="같은 숫자를 JSON 객체 하나로 낸다")

    p = sub.add_parser("bundle", help="초안 폴더를 검수 묶음(MP4·표지·점검표·검수 요약)으로 만든다")
    p.add_argument("dir", help="초안 폴더 경로 (2026/reels/drafts/<게시일>-<슬러그>)")
    p.add_argument("--card", help="대조할 카드뉴스 원고 JSON (check 의 --card 와 같음)")
    p.add_argument("--request-start", help="요청 시각 epoch 초 — bundle.json 에 요청부터 걸린 시간을 남김")
    p.add_argument("--rules", help="표현 점검 규칙 파일 (기본 tools/data/compliance_rules.json)")
    p.add_argument("--config", help="게시글 설정 경로 (기본 tools/data/caption_config.json)")
    _registry_arg(p)

    p = sub.add_parser("convert", help="카드뉴스 원고를 릴스 골격 JSON 으로 바꾼다")
    p.add_argument("card", help="카드뉴스 원고 JSON 경로 (2026/NN-이름/spec.json)")
    p.add_argument("--out", help="골격 JSON 을 쓸 경로 (기본 stdout)")

    p = sub.add_parser("slot", help="게시일·슬러그를 제안하고 초안 폴더를 만든다")
    p.add_argument("--date", help="게시 예정일 YYYY-MM-DD (없으면 제안만)")
    p.add_argument("--slug", help="영문 소문자·숫자·하이픈 슬러그")
    p.add_argument("--reels-dir", default=str(slot.REELS_DIR), help="릴스 폴더 (기본 2026/reels)")
    p.add_argument("--create", action="store_true", help="초안 폴더를 만든다 (--date, --slug 필요)")

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


def _read_json(path, label="원고 소스"):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        reason = getattr(e, "strerror", None) or str(e)
        raise ValueError(f"{label} 파일을 열 수 없음: {path} ({reason})") from e
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"{label} JSON 형식 오류: {path} 줄 {e.lineno} 열 {e.colno}") from e


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


# 게시된 v1 원고에는 없는 v2 초안 필드. 하나라도 있으면 --legacy(보고 전용, 종료 0)로 점검을 건너뛸 수 없다 (WR-03).
LEGACY_FORBIDDEN_KEYS = ("version", "series", "inputs", "derive", "figures", "basis_items")


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
        card = convert.load_card(args.card) if args.card else None
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    except convert.ConvertError as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    except figures.RegistryError as e:
        print(f"등록부 오류: {e}", file=sys.stderr)
        return 1
    if args.legacy:
        v2_keys = [k for k in LEGACY_FORBIDDEN_KEYS if k in spec]
        if v2_keys:
            print(f"원고 오류: --legacy 는 게시된 v1 원고 전용 — v2 초안 필드({', '.join(v2_keys)})가 있는 원고에는 쓸 수 없음",
                  file=sys.stderr)
            return 1
        report = check.legacy_report(spec)
        if card is not None:
            for issue in check.apply_card(report, card, spec, args.card):
                print(str(issue), file=sys.stderr)
        if args.out and _write_check_json(args, report, None):
            return 2
        print(f"check(legacy): {report.summary()}")
        return 3 if args.strict and report.warnings else 0
    report = check.check_spec(spec, registry, publish_date=publish_date)
    src_path = Path(args.src) if args.src else Path(args.spec).with_name(Path(args.spec).stem + ".src.json")
    if args.src or src_path.is_file():
        try:
            src = _read_json(src_path, "원고 소스")
        except ValueError as e:
            print(f"원고 오류: {e}", file=sys.stderr)
            return 1
        report.source = str(src_path)
        report.errors.extend(check.compare_source(spec, src, registry))
    if card is not None:
        check.apply_card(report, card, spec, args.card)
    for issue in report.errors + report.warnings:
        print(str(issue), file=sys.stderr)
        if issue.kind in check.HINTS and issue.kind != "NOT_EXPANDED":
            print(f"  -> {check.HINTS[issue.kind]}", file=sys.stderr)
    for item in report.needs_check:
        print(f'확인 필요: {item["where"]} [{", ".join(item["ids"])}] "{item["text"]}"')
    for item in report.assumptions:
        print(f'가정 수치: {item["where"]} [{", ".join(item["inputs"])}] "{item["text"]}" — 화면에 예시·가정 표기 확인')
    if args.out and _write_check_json(args, report, args.registry):
        return 2
    print(f"check: {report.summary()}")
    if report.errors:
        return 1
    if args.strict and report.warnings:
        return 3
    return 0


def cmd_convert(args):
    try:
        card = convert.load_card(args.card)
        skeleton = convert.card_skeleton(card, args.card)
    except convert.ConvertError as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    text = json.dumps(skeleton, ensure_ascii=False, indent=1) + "\n"
    if args.out:
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text, encoding="utf-8")
        except OSError as e:
            print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(text)
    print(f"convert: 카드 {len(card['cards'])}장 -> 장면 {len(skeleton['scenes'])}개 골격 · "
          f"원본 숫자 {len(skeleton['source_numbers'])}개 · note {len(skeleton['notes'])}개", file=sys.stderr)
    return 0


def cmd_caption(args):
    try:
        spec = load_spec(args.spec)
        src = _read_json(args.src, "게시글 문구 원본")
        config = caption.load_config(args.config)
        registry = figures.load_registry(args.registry)
        report = check.check_spec(spec, registry)
        if report.errors:
            raise caption.CaptionError(
                f"원고 점검 오류 {len(report.errors)}건 — 먼저 python3 tools/draft.py check 로 오류를 고치세요 "
                f"(첫 오류: {report.errors[0]})")
        text, warnings = caption.build_caption(spec, src, config, registry)
    except (SpecError, caption.CaptionError, figures.RegistryError, ValueError) as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    try:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    except OSError as e:
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 2
    for w in warnings:
        print(f"경고: {w}", file=sys.stderr)
    tags = len(config["brand_hashtags"]) + len(src["hashtags"])   # 마지막 줄을 세지 않는다 (해시태그가 없을 수 있음)
    print(f"caption: {args.out} 글자 {len(text)}자 · 해시태그 {tags}개")
    return 0


def cmd_compliance(args):
    from reelkit import compliance   # 표준 라이브러리만 쓰므로 가볍지만, 점검을 안 하는 명령은 읽지 않는다
    try:
        spec = load_spec(args.spec)
        text = None
        if args.caption:
            try:
                text = Path(args.caption).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                raise ValueError(f"게시글 파일을 열 수 없음: {args.caption} ({getattr(e, 'strerror', None) or e})") from None
        check_json = _read_json(args.check, "check.json") if args.check else None
        rules = compliance.load_rules(args.rules or compliance.RULES_PATH)
        result = compliance.run(spec, text, rules, check_json=check_json)
    except (SpecError, compliance.RuleError, ValueError) as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    for f in result.findings:
        print(f'{f["severity"]} · {f["where"]} · "{f["text"]}" · {", ".join(f["rule"])} {f["category"]} — '
              f'{f["reason"]} → {f["suggest"]}')
    for s in result.suppressed:
        print(f'예외 처리로 제외 · {s["where"]} · "{s["text"]}" · {", ".join(s["rule"])} ({s["by"]})')
    print(compliance.LIMITS)
    if args.out:
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(result.to_json(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        except OSError as e:
            print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
            return 2
    print(f"compliance: {result.headline} | {result.counts_line}")
    return 0


def cmd_redteam(args):
    from reelkit import compliance, redteam   # 보고서를 내는 명령에서만 읽는다
    try:
        rules = compliance.load_rules(args.rules or compliance.RULES_PATH)
        corpus = redteam.load_corpus(args.corpus or redteam.CORPUS_PATH)
        heldout = redteam.load_corpus(args.heldout or redteam.HELDOUT_PATH)
        lines, data = redteam.report(rules, corpus, heldout)
    except (compliance.RuleError, redteam.CorpusError) as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        print("\n".join(lines))
    return 0


def cmd_bundle(args):
    from reelkit import bundle   # 렌더러를 쓰는 명령에서만 읽는다 (다른 명령은 Playwright 를 읽지 않음)
    return bundle.run_cli(args.dir, card=args.card, request_start=args.request_start, rules=args.rules,
                          registry=args.registry, config=args.config)


def cmd_slot(args):
    try:
        if args.create and not (args.date and args.slug):
            raise slot.SlotError("--create 는 --date 와 --slug 가 모두 필요함")
        info = slot.propose(args.reels_dir, date=args.date, slug=args.slug)
        if args.create:
            if info["conflicts"]:
                raise slot.SlotError("; ".join(info["conflicts"]))
            slot.create_draft_dir(args.reels_dir, args.date, args.slug)
            info["created"] = True
    except slot.SlotError as e:
        print(f"초안 오류: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"환경 오류: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(info, ensure_ascii=False, indent=1))
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
    problems = figures.confirmation_problems(reg)
    for fid, problem in problems:
        print(f"등록부 오류: {fid}: {problem}", file=sys.stderr)
    return 1 if problems else 0


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
    # D-02 / CR-05: 사람만 확인한다. Claude Code 의 Bash 처럼 터미널이 아닌 곳에서는 실행되지 않고,
    # 사람이 화면의 값을 보고 id 를 다시 입력해야 한다. (pty 를 흉내 내는 우회는 막지 못한다 — REVIEW-FIX 참고)
    if not sys.stdin.isatty():
        print("등록부 오류: figures confirm 은 사람이 대화형 터미널에서만 실행할 수 있음 (Claude 실행 금지)", file=sys.stderr)
        return 1
    reg = figures.load_registry(args.registry)
    on = args.date or date.today().isoformat()
    entry = figures.get_figure(reg, args.id)
    print(f"{args.id}: {entry['label']} = {entry['value']} {entry['unit']}".rstrip(), file=sys.stderr)
    print(f"  출처: {entry['source']['name']} {entry['source']['url'] or ''}".rstrip(), file=sys.stderr)
    try:
        typed = input("1차 출처에서 이 값을 직접 확인했으면 id 를 다시 입력하세요: ")
    except EOFError:
        typed = ""
    if typed.strip() != args.id:
        print("등록부 오류: 입력한 id 가 다름 — 확인하지 않음", file=sys.stderr)
        return 1
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
    if args.command == "caption":
        return cmd_caption(args)
    if args.command == "convert":
        return cmd_convert(args)
    if args.command == "bundle":
        return cmd_bundle(args)
    if args.command == "compliance":
        return cmd_compliance(args)
    if args.command == "redteam":
        return cmd_redteam(args)
    if args.command == "slot":
        return cmd_slot(args)
    return cmd_expand(args)


if __name__ == "__main__":
    sys.exit(main())
