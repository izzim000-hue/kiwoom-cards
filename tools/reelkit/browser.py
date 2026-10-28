"""Chromium 실행(경로 폴백), file:// 템플릿 페이지, 번들 폰트 검증."""
import glob
import os
import re
from pathlib import Path

from . import constants


class BrowserLaunchError(RuntimeError):
    """사용 가능한 Chromium 을 띄우지 못했다."""


class FontLoadError(RuntimeError):
    """번들 폰트가 로드되지 않았거나 다른 폰트로 대체되었다."""


def _first_line(exc):
    text = str(exc).strip().splitlines()
    return text[0] if text else exc.__class__.__name__


def launch(pw):
    """(browser, used) 를 돌려준다. 기본 launch -> 환경변수 -> /opt/pw-browsers 순서로 시도한다.

    Playwright 와 Chromium 리비전이 어긋난 이미지(예: 브라우저 1243)에서도 렌더가 되도록 한다.
    """
    attempts = []
    try:
        return pw.chromium.launch(), "default"
    except Exception as e:  # noqa: BLE001 - 어떤 실패든 다음 후보로 넘어간다
        attempts.append(("기본 launch()", _first_line(e)))

    candidates = []
    env_path = os.environ.get("AGENT_BROWSER_EXECUTABLE_PATH")
    if env_path:
        if os.access(env_path, os.X_OK):
            candidates.append(env_path)
        else:
            attempts.append((env_path, "AGENT_BROWSER_EXECUTABLE_PATH 가 실행 가능한 파일이 아님"))
    found = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome"))
    for path in ["/opt/pw-browsers/chromium"] + found[-1:]:
        if path not in candidates:
            candidates.append(path)

    for path in candidates:
        try:
            return pw.chromium.launch(executable_path=path), path
        except Exception as e:  # noqa: BLE001
            attempts.append((path, _first_line(e)))

    detail = "; ".join(f"{what}: {why}" for what, why in attempts)
    raise BrowserLaunchError(f"Chromium 을 실행하지 못했습니다. 시도한 경로와 오류: {detail}")


def open_page(browser, work_dir, fonts_dir=constants.FONTS_DIR):
    """@font-face 만 든 빈 템플릿을 file:// 로 열어 돌려준다 (set_content 는 file:// 폰트가 막힌다)."""
    html = constants.TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("{{FONTDIR_URI}}", Path(fonts_dir).resolve().as_uri())
    frame = Path(work_dir) / "frame.html"
    frame.write_text(html, encoding="utf-8")
    page = browser.new_page(viewport={"width": constants.W, "height": constants.H})
    # 원고 문자열이 외부로 요청을 보내지 못하게 http/https 는 모두 막는다
    page.route(re.compile(r"^https?://"), lambda r: r.abort())
    page.goto(frame.as_uri())
    return page


def platform_fonts(page, selector):
    """selector 에 맞는 노드마다 실제로 쓰인 플랫폼 폰트 목록(CDP)을 문서 순서로 돌려준다."""
    cdp = page.context.new_cdp_session(page)
    try:
        cdp.send("DOM.enable")
        cdp.send("CSS.enable")
        doc = cdp.send("DOM.getDocument", {"depth": -1})
        ids = cdp.send("DOM.querySelectorAll",
                       {"nodeId": doc["root"]["nodeId"], "selector": selector})["nodeIds"]
        return [cdp.send("CSS.getPlatformFontsForNode", {"nodeId": nid})["fonts"] for nid in ids]
    finally:
        try:
            cdp.detach()
        except Exception:  # noqa: BLE001
            pass


_PROBE_TEXT = "가나다 ABC 123 ① → · %"


def font_problems(page):
    """번들 폰트 문제를 한국어 문장 목록으로 돌려준다. 빈 목록이면 정상."""
    problems = []
    states = page.evaluate(
        "Promise.all([...document.fonts].map(f=>f.load().then(()=>f.status,()=>'error')"
        ".then(s=>f.weight+' '+s)))")
    loaded = {}
    for item in states:
        weight, status = item.split(" ", 1)
        loaded[int(weight)] = status
    if len(states) != 3:
        problems.append(f"번들 폰트 @font-face 가 3개여야 하는데 {len(states)}개입니다")
    for weight, name in constants.FONT_FILES.items():
        status = loaded.get(weight)
        if status != "loaded":
            problems.append(f"폰트 {weight} ({name}) 로드 실패: 상태 {status or '없음'}")

    page.evaluate(
        """t=>{document.body.innerHTML=[400,700,900].map(w=>
            `<div id="rk-probe-${w}" style="font-family:'Noto Sans KR';font-weight:${w}">${t}</div>`).join('')}""",
        _PROBE_TEXT)
    page.evaluate("document.fonts.ready.then(()=>0)")
    for weight in constants.FONT_FILES:
        substitutes = []
        for fonts in platform_fonts(page, f"#rk-probe-{weight}"):
            if not fonts:
                problems.append(f"폰트 {weight}: 실제 사용된 폰트를 확인하지 못했습니다")
            for f in fonts:
                name = str(f.get("familyName", ""))
                if (not f.get("isCustomFont") or not name.startswith("Noto Sans KR")) and name not in substitutes:
                    substitutes.append(name)
        if substitutes:
            problems.append(
                f"폰트 {weight} ({constants.FONT_FILES[weight]}) 대신 시스템 폰트 "
                f"{', '.join(repr(n) for n in substitutes)} 로 그려집니다")
    page.evaluate("document.body.innerHTML=''")
    return problems
