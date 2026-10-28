"""키움멘토 자막형 릴스 생성기 (1080x1920, 목소리 없음, 무음 오디오 트랙 포함)
사용: python3 tools/reel.py spec.json 출력.mp4
종료 코드: 0 정상, 1 원고/입력 오류(파일 없음, JSON 오류, 허용되지 않은 마크업), 2 환경 오류(playwright 미설치, Chromium 실행 실패, 번들 폰트 로드 실패),
          4 출력 MP4 의 업로드 규격 FAIL (MP4 는 이미 써 둠)
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
    args = ap.parse_args(argv)
    try:
        r = render_reel(args.spec, args.out, layout="legacy")
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
    for line in format_report(r.out, r.spec_checks):
        print(line, file=sys.stderr)
    if any(c.status == "FAIL" for c in r.spec_checks):
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
