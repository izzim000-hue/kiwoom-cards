"""릴스 초안의 게시일·슬러그 제안과 초안 폴더 만들기 (D-14).

날짜는 이미 쓰인 날짜(게시된 MP4, 원고, 기존 초안 폴더) 중 가장 늦은 날의 다음 날과 오늘 중 늦은 날로 제안한다.
날짜를 코드에 적어 두지 않고 매번 폴더를 읽어 계산한다. 폴더는 `2026/reels/drafts/` 안에만 만든다 (T-02-14).
"""
import json
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from . import constants

REELS_DIR = constants.REPO_ROOT / "2026" / "reels"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SLUG_MAX = 40
_SLOT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)$")


class SlotError(ValueError):
    """날짜나 슬러그가 규칙에 어긋나거나 폴더를 만들 수 없을 때. 메시지는 한국어."""


def check_slug(slug):
    if not isinstance(slug, str) or not slug:
        raise SlotError("슬러그가 비어 있음 (영문 소문자·숫자·하이픈, 예: pension-credit-limit)")
    if len(slug) > SLUG_MAX:
        raise SlotError(f"슬러그가 너무 김: {len(slug)}자 (최대 {SLUG_MAX}자)")
    if not SLUG_RE.match(slug):
        raise SlotError(f"슬러그 형식 오류: {slug!r} — 영문 소문자·숫자와 하이픈 하나씩만 쓸 수 있음 (경로 문자 금지)")
    return slug


def check_date(text):
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise SlotError(f"날짜 형식 오류: {text!r} — YYYY-MM-DD")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise SlotError(f"없는 날짜: {text}") from None


def used_slots(reels_dir=REELS_DIR):
    """(날짜, 슬러그, 위치) 목록. 게시된 MP4, specs 의 원고, drafts 의 폴더 이름에서 읽는다."""
    reels_dir = Path(reels_dir)
    found = []
    sources = (
        ("게시된 MP4", sorted(reels_dir.glob("*.mp4")), lambda p: p.stem),
        ("게시된 원고", sorted((reels_dir / "specs").glob("*.json")), lambda p: p.stem),
        ("초안 폴더", sorted(p for p in (reels_dir / "drafts").glob("*") if p.is_dir()), lambda p: p.name),
    )
    for where, paths, name in sources:
        for p in paths:
            m = _SLOT_RE.match(name(p))
            if m:
                found.append((m.group(1), m.group(2), where))
    return found


def propose(reels_dir=REELS_DIR, *, date=None, slug=None, today=None):  # noqa: A002 - CLI 이름과 맞춤
    """게시일·슬러그 제안. 충돌이 있거나 날짜를 받지 못했으면 ask 가 참이라 스킬이 사용자에게 한 번 묻는다.

    지난 날짜나 제안일보다 이른 날짜는 notices 에 적고 ask 를 참으로 한다 (WR-05: 모호한 날짜는 한 번 확인).
    릴스 폴더가 연도 폴더(예: 2026/reels) 안에 있으면 다른 해의 날짜는 충돌이다 (--create 거부).
    """
    reels_dir = Path(reels_dir)
    today = today or _today()
    used = used_slots(reels_dir)
    dates = []
    for d, _, _ in used:
        try:
            dates.append(_iso(d))
        except ValueError:
            continue
    proposed = today if not dates else max(max(dates) + timedelta(days=1), today)
    chosen = check_date(date) if date else proposed
    if slug is not None:
        check_slug(slug)
    conflicts, notices = [], []
    for d, s, where in used:
        if d == chosen.isoformat():
            conflicts.append(f"날짜 사용 중: {d} ({where} {d}-{s})")
    folder_year = reels_dir.resolve().parent.name
    if re.fullmatch(r"\d{4}", folder_year) and int(folder_year) != chosen.year:
        conflicts.append(f"연도 불일치: {chosen.isoformat()} 은 {folder_year}/ 폴더에 둘 수 없음 "
                         f"(--reels-dir {chosen.year}/reels 로 지정)")
    if chosen < today:
        notices.append(f"지난 날짜: {chosen.isoformat()} < 오늘 {today.isoformat()} — 사용자 확인 필요")
    elif chosen < proposed:
        notices.append(f"제안일보다 이른 날짜: {chosen.isoformat()} < {proposed.isoformat()} — 게시 순서 사용자 확인 필요")
    if slug:
        for d, s, where in used:
            if s == slug:
                conflicts.append(f"슬러그 사용 중: {s} ({where} {d}-{s})")
    folder = None
    if slug:
        folder = str(reels_dir / "drafts" / f"{chosen.isoformat()}-{slug}")
    return {
        "proposed_date": proposed.isoformat(),
        "date": chosen.isoformat(),
        "slug": slug,
        "dir": folder,
        "conflicts": conflicts,
        "notices": notices,
        "ask": bool(conflicts) or bool(notices) or not date,
    }


def create_draft_dir(reels_dir, date, slug):  # noqa: A002
    """`<reels_dir>/drafts/<날짜>-<슬러그>` 를 만든다. 충돌이면 거부하고, drafts 밖으로 풀리는 경로도 거부한다."""
    reels_dir = Path(reels_dir)
    info = propose(reels_dir, date=date, slug=slug)
    if info["conflicts"]:
        raise SlotError("초안 폴더를 만들 수 없음: " + "; ".join(info["conflicts"]))
    root = (reels_dir / "drafts").resolve()
    target = (reels_dir / "drafts" / f"{info['date']}-{slug}").resolve()
    if not target.is_relative_to(root) or target == root:
        raise SlotError(f"초안 폴더가 drafts 밖임: {target}")
    try:
        target.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise SlotError(f"이미 있는 폴더: {target}") from None
    try:
        stamp_created(target)
    except OSError as e:
        # 방금 만든 빈 폴더를 지워 다시 시도할 수 있게 한다 (IN-07). 무엇이든 들어 있으면 지우지 않는다.
        try:
            target.rmdir()
        except OSError:
            pass
        raise SlotError(f"created.json 을 쓸 수 없어 초안 폴더를 만들지 않음: {target} ({e})") from None
    return target


def stamp_created(folder):
    """초안 폴더를 만든 시각을 created.json 에 남긴다 (배타 생성). 묶음이 요청부터 걸린 시간을 잴 때 쓴다 (D-14)."""
    now = time.time()
    data = {"created_at": datetime.fromtimestamp(now).isoformat(timespec="seconds"), "epoch": round(now, 3)}
    with open(Path(folder) / "created.json", "x", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def _iso(text):
    return date.fromisoformat(text)


def _today():
    return date.today()
