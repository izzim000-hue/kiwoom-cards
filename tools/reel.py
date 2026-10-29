"""키움멘토 자막형 릴스 생성기 (1080x1920, 목소리 없음, 무음 오디오 트랙 포함)
사용: python3 tools/reel.py spec.json 출력.mp4 [--layout {legacy,new}] [--motion {none,basic}] [--strict] [--overlay-all] [--bgm 음원 --bgm-license 메모]
  --layout legacy  게시된 릴스 10편과 같은 배치(기본). 레이아웃 측정 경고 없음(글꼴 대체만 검사)
  --layout new     근거(36px, 본문 바로 아래)·계정명을 안전영역 안에 쌓는 새 배치. 줄바꿈·넘침·안전영역 침범을
                   `scene N line M: KIND (값) "글자"` 로 stderr 에 내고, 안전영역 미리보기 `<출력>.safe-sNN.png` 를 쓴다
                   (1장면 + 가장 높은 장면, --overlay-all 이면 모든 장면). 글자는 줄이거나 자르지 않고 원고 그대로 그린다
  --motion none    정지 화면 연결(기본, 원고에 motion 이 없을 때와 같음)
  --motion basic   줄이 0.3초 페이드하며 24px 떠오르고(줄 사이 0.12초) 장면 사이를 0.3초 크로스페이드하는 모션. 프레임 시각마다
                   애니메이션을 멈춰 찍는 결정적 렌더이며 --layout new 에서만 쓸 수 있다 (legacy 와 함께 쓰면 종료 코드 1, MP4 없음).
                   주면 원고의 "motion" 필드보다 우선한다 (단독 렌더용; draft.py bundle 은 spec.src.json 의 필드만 따른다)
  --bgm 경로       배경음 음원 파일. --bgm-license 와 함께만 쓸 수 있다 (둘 중 하나만 있거나 메모가 비면 `음원 오류` 로 거부, 종료 코드 1,
                   Chromium 을 띄우기 전). 영상 길이에 맞춰 반복·자르고 1초 페이드, 약 -16 LUFS 로 섞는다. 복사본·bgm.json 은 만들지 않는다
                   (그건 draft.py bundle 이 한다). 저장소 안 파일은 출력 MP4 와 같은 폴더에 있고 이름이 bgm.* 가 아닐 때만 받는다.
                   음악을 찾거나 내려받지 않는다. 쓰면 stdout 에 `bgm=<파일 이름>` 한 줄이 더 나온다
  --bgm-license 메모  음원 이용 권리 메모 (빈 값 거부)
  --strict         경고가 있으면 MP4 를 쓴 뒤 종료 코드 3
종료 코드: 0 정상, 1 원고/입력 오류(파일 없음, JSON 오류, 허용되지 않은 마크업), 2 환경 오류(playwright 미설치, Chromium 실행 실패, 번들 폰트 로드 실패),
          3 --strict 인데 레이아웃 경고가 있음, 4 출력 MP4 의 업로드 규격 FAIL (3 과 4 모두 MP4 는 이미 써 둠, 4 가 우선)
매 실행의 끝에 출력 MP4 를 규격 검사(9개 항목)해 항목별 결과를 stderr 로 낸다.
spec.json 예시:
{"basis": "단리 적금 예시 · 일반과세 15.4% 기준",
 "scenes": [
   {"top": "헷갈리는 돈 상식 #1", "lines": ["연 5% 적금", "월 100만 원, 1년", "<g>이자 60만 원?</g>"]},
   ...,
   {"top": "", "lines": ["저장해두고", "내 적금도 계산해 보세요", "<s>프로필 링크 · 1분 노후자금 계산기</s>"]}]}
<g>..</g> = 금색 강조, <s>..</s> = 작은 회색 글씨. 한 줄 0.85초씩 나타나고 장면 끝에서 1.9초 멈춤.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reelkit import bgm as bgm_mod  # noqa: E402
from reelkit.render import PLAYWRIGHT_MISSING, env_error_message, render_reel  # noqa: E402,F401
from reelkit.spec import SpecError  # noqa: E402
from reelkit.specprobe import format_report  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="자막형 릴스 MP4 생성")
    ap.add_argument("spec", help="원고 JSON 경로")
    ap.add_argument("out", help="출력 MP4 경로")
    ap.add_argument("--layout", choices=["legacy", "new"], default="legacy", help="프레임 배치 (기본 legacy)")
    ap.add_argument("--motion", choices=["none", "basic"], default=None,
                    help="모션 (기본: 원고의 motion 필드, 없으면 none). basic 은 --layout new 에서만")
    ap.add_argument("--strict", action="store_true", help="레이아웃 경고가 있으면 종료 코드 3")
    ap.add_argument("--overlay-all", action="store_true", help="모든 장면의 안전영역 미리보기 PNG 를 쓴다 (new 배치)")
    ap.add_argument("--bgm", help="배경음 음원 파일 — --bgm-license 와 함께만")
    ap.add_argument("--bgm-license", help="음원 이용 권리 메모 (빈 값 거부)")
    args = ap.parse_args(argv)
    try:
        src = bgm_mod.validate(args.bgm, args.bgm_license, Path(args.out).resolve().parent)
    except bgm_mod.BgmError as e:
        print(f"음원 오류: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"환경 오류: 음원을 검사하지 못함: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 2
    try:
        r = render_reel(args.spec, args.out, layout=args.layout, overlay_all=args.overlay_all,
                        motion=args.motion, bgm=None if src is None else src.path)
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 - 환경 오류만 2 로 바꾸고 나머지는 그대로 다시 던진다
        msg = env_error_message(e)
        if msg is None:
            raise
        print(msg, file=sys.stderr)
        return 2
    print(f"duration={r.total:.1f}s cover_ms={r.cover_ms}")
    if r.motion == "basic":
        print("motion=basic")
    if r.bgm:
        print(f"bgm={src.name}")
    for w in r.warnings:
        print(str(w), file=sys.stderr)
    if r.warnings:
        print(f"레이아웃 경고 {len(r.warnings)}건", file=sys.stderr)
    for path in r.overlays:
        print(f"안전영역 미리보기: {path}", file=sys.stderr)
    for line in format_report(r.out, r.spec_checks):
        print(line, file=sys.stderr)
    if any(c.status == "FAIL" for c in r.spec_checks):
        return 4
    if args.strict and r.warnings:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
