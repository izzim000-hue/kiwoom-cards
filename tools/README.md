# tools

- `cards.py`: 카드뉴스 6장(1080x1350) PNG 생성. 세이지 그린 바탕, 마지막 장 딥그린.
- `reel.py`: 자막형 릴스(1080x1920) MP4 생성. 목소리 없음. 출력 끝에 표지용 시점(cover_ms)을 알려 줌.
- `doctor.py`: 릴스를 그릴 수 있는 환경인지 점검 (세션 시작 때 자동으로도 실행됨).
- `specprobe.py`: MP4가 Instagram 업로드 규격을 지키는지 항목별 검사.
- `golden.py`: 게시된 릴스 10편을 다시 그려 같은 결과가 나오는지 확인하는 회귀 검사.

이미지 폴더 규칙: `2026/<게시일>-<영문-슬러그>/insta_1..6.png`, 릴스는 `2026/reels/<게시일>-<영문-슬러그>.mp4`.
이 저장소에는 공개용 카드뉴스·릴스만 둔다. 고객 정보·상담 자료 금지.

## 릴스 만들기: `reel.py`

```
python3 tools/reel.py SPEC OUT [--layout legacy|new] [--strict] [--overlay-all]
```

- `SPEC`: 원고 JSON (`2026/reels/specs/` 의 게시된 10편이 예시). `OUT`: 출력 MP4 경로.
- 끝에 `duration=26.1s cover_ms=1250` 한 줄을 stdout 으로 낸다. 경고와 규격 보고는 stderr.
- `--layout legacy` (기본): 게시된 10편과 같은 배치. **게시된 10편은 legacy 로만 재현한다.** 이 배치는 결과를 바꾸지 않는다 (D-05).
- `--layout new`: 근거(36px, 본문 바로 아래)와 계정명을 안전영역 안에 쌓는 새 배치. **새 릴스는 new 로 만든다.**
  줄바꿈·넘침·안전영역 침범을 `scene N line M: KIND (값) "글자"` 로 알린다. 글자는 줄이거나 자르지 않는다.
- `--strict`: 레이아웃 경고가 있으면 MP4 를 쓴 뒤 종료 코드 3.
- `--overlay-all`: 모든 장면의 안전영역 미리보기를 쓴다 (new 배치).
- 안전영역 미리보기 파일 이름: `<출력이름>.safe-s01.png` (1장면), 가장 높은 장면은 `<출력이름>.safe-sNN.png`, `--overlay-all` 이면 장면마다 하나. MP4 에는 들어가지 않는다.

종료 코드: **0** 정상 / **1** 원고 오류 (파일 없음, JSON 오류, 허용되지 않은 마크업) / **2** 환경 오류 (playwright 미설치, Chromium 실행 실패, 번들 폰트 로드 실패) / **3** `--strict` 인데 레이아웃 경고 있음 / **4** 출력 MP4 의 업로드 규격 FAIL (3 과 4 모두 MP4 는 이미 써 둠, 4 가 우선).

초안은 `2026/reels/drafts/` 에 만들고 git에 올리지 않는다 (D-08). 렌더 중간 파일도 올리지 않는다 (`.gitignore` 에 있음).

## 환경 점검: `doctor.py`

```
python3 tools/doctor.py [--quiet | --json] [--fonts-dir DIR]
```

Playwright 버전, Chromium 실행, 번들 폰트 파일(sha256)과 로드(400/700/900, 시스템 폰트 대체 없음), ffmpeg(libx264·aac·1프레임 인코딩), ffprobe 를 차례로 점검한다. 실패하면 원인과 해결 방법을 한국어로 알려 준다.

- `--quiet`: 요약 한 줄만 출력 (실패하면 자세한 줄은 stderr). 세션 시작 훅(`.claude/hooks/session-start.sh`)이 이 형태로 자동 실행한다.
- `--json`: `ok`, `checks`, `summary`, `playwright`(설치 버전), `launch`(`default` 또는 Chromium 경로) 를 JSON 으로 출력.
- 종료 코드 0: 실패 없음 (경고는 허용). 1: 실패 있음.
- Playwright 가 고정 버전(`tools/requirements.txt`)과 다르면 **경고**다. 렌더가 되는지는 Chromium·폰트 점검이 정한다.
  기본 실행이 안 돼서 `/opt/pw-browsers/chromium` 으로 폴백하면 그 경로를 적고 경고로 통과시킨다.
- 훅은 고정 버전과 설치 버전이 다를 때만 `pip install --user -r tools/requirements.txt` 를 실행하고, 실패해도 세션을 막지 않는다.
  pip 설치가 거부되는 환경이면 `PIP_BREAK_SYSTEM_PACKAGES=1` 을 붙여 다시 시도한다.

## 규격 검사: `specprobe.py`

```
python3 tools/specprobe.py FILE...
```

MP4 마다 9개 항목(비디오 스트림, 코덱, 크기, fps, pix_fmt, 프로필, 오디오, faststart, 길이)을 한 줄씩 보여 주고 `spec: PASS 9/9` 로 끝낸다. 측정할 수 없는 항목은 PASS 가 아니라 FAIL. 종료 코드 1: FAIL 있음.

## 회귀 검사: `golden.py`

```
python3 tools/golden.py [--only STEM] [--jobs N]
```

게시된 릴스 10편의 원고를 legacy 배치로 다시 그려 게시된 MP4 와 비교한다 (4개 동시 렌더로 약 1~2분).
프레임 수, 비디오·오디오 길이, 장면 경계 프레임, `cover_ms`, 출력 한 줄, 프레임별 SSIM(0.98 이상), 업로드 규격을 본다.
마지막 줄은 `golden: PASS 10/10 (재현 불가 1)`. 원고가 없는 `2026-10-19-savings-interest` 는 재현 불가로 보고하고 규격만 본다 (D-06).
기준 목록에 없는 MP4 는 `기준 목록 밖` 으로 알리기만 하고 판정하지 않는다.
기준은 `tools/tests/golden/manifest.json` (게시된 MP4 에서 한 번 뽑은 값)이다. 렌더러 출력으로 다시 만들지 않고, SSIM 기준을 낮춰서 통과시키지도 않는다.
실패하면 폰트 로드나 마크업부터 조사한다. 게시된 `2026/reels/*.mp4` 와 `specs/*.json` 은 고치지 않는다.

## 시험

```
python3 -m unittest discover -s tools/tests -v
```

전체 시험 (게시된 릴스를 하나씩 다시 그리므로 3~4분). 일부만: `python3 -m unittest discover -s tools/tests -p 'test_doctor.py' -v`.

## 폰트와 고정 버전

- `tools/fonts/`: 번들 Noto Sans KR 400/700/900 (SIL OFL, 출처와 sha256 은 `tools/fonts/README.md`). 시스템에 한글 폰트가 없어도 같은 글자 모양으로 그리기 위한 것이다.
  **폰트를 바꾸면** `reelkit/constants.py` 의 `FONT_SHA256` 과 `tools/fonts/README.md` 를 함께 고치고 `golden.py` 를 다시 돌린다.
- `tools/requirements.txt`: `playwright==1.63.0` 고정. 미리 깔린 Chromium 과 맞는 버전이다.
