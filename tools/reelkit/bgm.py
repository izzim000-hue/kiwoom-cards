"""배경음(BGM): 사용자가 준 음원 파일 + 라이선스 메모가 함께 있을 때만 영상에 섞는다 (MOTN-06, D-08~D-11; 표준 라이브러리 + ffprobe).

- 기본은 무음이다. 음원을 찾거나 내려받거나 고르는 코드는 이 도구에 없다: 입력은 사용자가 준 경로 하나뿐이다 (D-09).
- 검증(validate)은 파일을 지우거나 렌더하기 전에 끝낸다. 거부 사유는 BgmError 로 한국어 메시지를 담아 종료 코드 1 이 된다.
- 묶음은 음원을 초안 폴더에 `bgm.<확장자>` 로 복사하고 `bgm.json` 에 해시·메모를 적는다 (install). 믹스는 복사본에서 한다.
- ffmpeg/ffprobe 는 인자 목록으로만 실행하고, 필터 문자열에는 계산한 숫자만 넣는다 (파일 이름은 `-i` 인자로만 간다).
"""
import hashlib
import json
import math
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import constants

AUDIO_EXTS = (".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus", ".flac")
COPY_NAMES = tuple("bgm" + e for e in AUDIO_EXTS)
META = "bgm.json"
TOOL_NAMES = frozenset((META, *COPY_NAMES, *(n + ".part" for n in COPY_NAMES)))   # 도구가 쓰고 지우는 정확한 이름
MIN_SECONDS = 3.0
MEMO_MAX = 500
FADE_S = 1.0
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"
META_KEYS = ("schema", "file", "copy", "sha256", "license", "duration_s")


class BgmError(ValueError):
    """음원·라이선스 메모가 규칙에 어긋날 때. 메시지는 한국어 (종료 코드 1)."""


@dataclass(frozen=True)
class BgmSource:
    path: Path
    name: str
    ext: str
    license: str
    duration_s: float


def _probe(path):
    """ffprobe JSON 을 dict 로. 실행 불가(OSError)는 그대로 올려 환경 오류가 되게 하고, 읽기 실패는 BgmError."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type:stream_disposition=attached_pic:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        raise BgmError("음원으로 읽을 수 없음 (ffprobe 가 파일을 열지 못함)")
    try:
        data = json.loads(r.stdout)
    except ValueError:
        raise BgmError("음원으로 읽을 수 없음 (ffprobe 결과를 해석하지 못함)") from None
    if not isinstance(data, dict):
        raise BgmError("음원으로 읽을 수 없음 (ffprobe 결과 형식 오류)")
    return data


def _duration(data):
    try:
        value = float((data.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        raise BgmError("음원으로 읽을 수 없음 (길이를 알 수 없음)") from None
    if not math.isfinite(value):
        raise BgmError("음원으로 읽을 수 없음 (길이를 알 수 없음)")
    return value


def same_file(a, b):
    """두 경로가 같은 파일·폴더인지 (대소문자를 가리지 않는 파일 시스템에서도 맞게 os.path.samefile 로)."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _inside(path, root):
    """path 가 root 자신이거나 그 아래에 있는지. 이름 비교가 아니라 같은 폴더인지로 본다 (경로 글자의 대소문자가 달라도 잡는다)."""
    p = Path(path)
    return any(same_file(q, root) for q in (p, *p.parents))


def reserved_name(name):
    """도구가 쓰는 배경음 이름(bgm.json, bgm.<확장자>, 그 .part)인지 — 대소문자를 가리지 않는다 (CR-02)."""
    return str(name).lower() in TOOL_NAMES


def _git_ignores(repo, path):
    """git 이 path 를 무시하는지 (`git check-ignore`). 추적 중인 파일은 무시되지 않는 것으로 나온다. git 이 없거나 저장소가 아니면 False."""
    try:
        r = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "--", str(path)],
                           capture_output=True, text=True)
    except OSError:
        return False
    return r.returncode == 0


def validate(path, memo, draft_dir):
    """(--bgm, --bgm-license) 를 검사해 BgmSource 를 돌려준다. 둘 다 없으면 None (D-08, D-09).

    ffmpeg 를 돌리거나 파일을 지우기 전에 부른다. ffprobe 를 실행하지 못하면 OSError 가 그대로 올라간다 (환경 오류).
    """
    if path is None and memo is None:
        return None
    if path is None or memo is None:
        raise BgmError("음원 파일(--bgm)과 라이선스 메모(--bgm-license)는 함께 줘야 함")
    text = str(memo).strip()
    if not text:
        raise BgmError("라이선스 메모가 비어 있음 — 음원 이용 권리를 적어야 배경음을 넣을 수 있음")
    if len(text) > MEMO_MAX:
        raise BgmError(f"라이선스 메모가 너무 김 ({len(text)}자 > {MEMO_MAX}자)")
    given = Path(path)
    if given.is_symlink():
        raise BgmError(f"심볼릭 링크 음원은 받지 않음: {given.name}")
    src = given.resolve()
    if not src.is_file():
        raise BgmError(f"음원이 일반 파일이 아니거나 없음: {given}")
    ext = src.suffix.lower()
    if ext not in AUDIO_EXTS:
        raise BgmError(f"음원 확장자는 {' '.join(AUDIO_EXTS)} 만 받음: {src.name}")
    draft = Path(draft_dir).resolve()
    if src.parent.is_dir() and same_file(src.parent, draft) and reserved_name(src.name):
        # 대소문자를 가리지 않는 파일 시스템에서는 BGM.MP3 가 곧 bgm.mp3 라 다시 묶을 때 지워진다 (CR-02)
        raise BgmError(f"음원 이름이 도구의 복사본 이름(bgm.*)과 겹침 — 이름을 바꾸세요: {src.name}")
    clash = sorted(p.name for p in draft.iterdir() if reserved_name(p.name) and p.name not in TOOL_NAMES) \
        if draft.is_dir() else []
    if clash:
        raise BgmError(f"초안 폴더에 도구의 복사본 이름(bgm.*)과 대소문자만 다른 파일이 있음 — 이름을 바꾸세요: {', '.join(clash)}")
    repo = Path(constants.REPO_ROOT).resolve()
    if _inside(src, repo):
        if not same_file(src.parent, draft):
            raise BgmError("저장소 안 음원은 그 초안 폴더 안(bgm.* 이 아닌 이름)에서만 받음 — 커밋 방지")
        if not _git_ignores(repo, src):
            raise BgmError("저장소 안 음원이 git 에서 무시되지 않음(.gitignore 에 막혀 있지 않거나 이미 추적 중) — 커밋 방지. "
                           "저장소 밖으로 옮겨서 주세요")
    data = _probe(src)
    streams = data.get("streams")
    streams = [s for s in streams if isinstance(s, dict)] if isinstance(streams, list) else []
    if not any(s.get("codec_type") == "audio" for s in streams):
        raise BgmError("오디오 스트림이 없는 파일은 음원으로 받지 않음")
    for s in streams:
        if s.get("codec_type") == "video" and (s.get("disposition") or {}).get("attached_pic") != 1:
            raise BgmError("영상이 든 파일은 받지 않음")
    duration = _duration(data)
    if duration < MIN_SECONDS:
        raise BgmError(f"음원이 너무 짧음 ({duration:.1f}초 < {MIN_SECONDS:g}초)")
    return BgmSource(path=src, name=src.name, ext=ext, license=text, duration_s=duration)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def install(src, draft_dir):
    """검증된 음원을 `<초안>/bgm<확장자>` 로 복사하고 bgm.json 을 쓴다. 쓴 내용(dict)을 돌려준다 (D-11)."""
    d = Path(draft_dir)
    copy_name = "bgm" + src.ext
    target = d / copy_name
    part = d / (copy_name + ".part")
    try:
        with open(src.path, "rb") as fin, open(part, "wb") as fout:
            for chunk in iter(lambda: fin.read(1 << 20), b""):
                fout.write(chunk)
        os.replace(part, target)
    finally:
        try:
            part.unlink()
        except OSError:
            pass
    meta = {"schema": 1, "file": src.name, "copy": copy_name, "sha256": _sha256(target),
            "license": src.license, "duration_s": round(src.duration_s, 2)}
    fd, tmp = tempfile.mkstemp(prefix=f".{META}.", suffix=".part", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
        os.replace(tmp, d / META)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return meta


def read_meta(draft_dir):
    """bgm.json 의 내용. 파일이 없으면 None, 심볼릭 링크이거나 형식이 다르면 BgmError."""
    p = Path(draft_dir) / META
    if p.is_symlink():
        raise BgmError(f"심볼릭 링크는 쓸 수 없음: {META}")
    if not os.path.lexists(p):
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise BgmError(f"{META} 를 읽을 수 없음") from None
    if (not isinstance(data, dict) or set(data) != set(META_KEYS) or data.get("schema") != 1
            or data.get("copy") not in COPY_NAMES
            or not all(isinstance(data.get(k), str) for k in ("file", "sha256", "license"))
            or isinstance(data.get("duration_s"), bool) or not isinstance(data.get("duration_s"), (int, float))):
        raise BgmError(f"{META} 형식이 다름")
    return data


def filter_graph(total):
    """오디오 필터 그래프 `[1:a]...[a]` (입력 1번이 음원). total 은 영상 길이(초).

    T 는 천분의 일 초로 올림해 오디오가 영상보다 짧아지지 않게 한다 (Pitfall 4). loudnorm 은 내부에서 192 kHz 로 올리므로
    뒤에 aresample=44100 이 반드시 필요하다. 숫자만 넣고 문자열은 넣지 않는다.
    """
    t = math.ceil(round(float(total) * 1000, 6)) / 1000
    return (f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{t:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={FADE_S:g},afade=t=out:st={max(t - FADE_S, 0):.3f}:d={FADE_S:g},"
            f"{LOUDNORM},aresample=44100,aformat=channel_layouts=stereo[a]")
