"""키움멘토 자막형 릴스 생성기 (1080x1920, 목소리 없음, 무음 오디오 트랙 포함)
사용: python3 tools/reel.py spec.json 출력.mp4 [--layout {legacy,new}] [--strict] [--overlay-all]
  --layout legacy  게시된 릴스 10편과 같은 배치(기본). 레이아웃 측정 경고 없음(글꼴 대체만 검사)
  --layout new     근거(36px, 본문 바로 아래)·계정명을 안전영역 안에 쌓는 새 배치. 줄바꿈·넘침·안전영역 침범을
                   `scene N line M: KIND (값) "글자"` 로 stderr 에 내고, 안전영역 미리보기 `<출력>.safe-sNN.png` 를 쓴다
                   (1장면 + 가장 높은 장면, --overlay-all 이면 모든 장면). 글자는 줄이거나 자르지 않고 원고 그대로 그린다
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PLAYWRIGHT_MISSING = "playwright 미설치: python3 -m pip install --user -r tools/requirements.txt"

try:
    from reelkit.render import render_reel
    from reelkit.browser import BrowserLaunchError, FontLoadError
    from reelkit.spec import SpecError
    from reelkit.specprobe import format_report
except ImportError:
    print(PLAYWRIGHT_MISSING, file=sys.stderr)
    sys.exit(2)


def main(argv=None):
    ap = argparse.ArgumentParser(description="자막형 릴스 MP4 생성")
    ap.add_argument("spec", help="원고 JSON 경로")
    ap.add_argument("out", help="출력 MP4 경로")
    ap.add_argument("--layout", choices=["legacy", "new"], default="legacy", help="프레임 배치 (기본 legacy)")
    ap.add_argument("--strict", action="store_true", help="레이아웃 경고가 있으면 종료 코드 3")
    ap.add_argument("--overlay-all", action="store_true", help="모든 장면의 안전영역 미리보기 PNG 를 쓴다 (new 배치)")
    args = ap.parse_args(argv)
    try:
        r = render_reel(args.spec, args.out, layout=args.layout, overlay_all=args.overlay_all)
    except SpecError as e:
        print(f"원고 오류: {e}", file=sys.stderr)
        return 1
    except ImportError:
        print(PLAYWRIGHT_MISSING, file=sys.stderr)
        return 2
    except (FontLoadError, BrowserLaunchError) as e:
        print(f"렌더 환경 오류: {e}", file=sys.stderr)
        return 2
    print(f"duration={r.total:.1f}s cover_ms={r.cover_ms}")
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
