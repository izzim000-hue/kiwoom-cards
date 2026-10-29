# tools

- `cards.py`: 카드뉴스 6장(1080x1350) PNG 생성. 세이지 그린 바탕, 마지막 장 딥그린.
- `reel.py`: 자막형 릴스(1080x1920) MP4 생성. 목소리 없음. 출력 끝에 표지용 시점(cover_ms)을 알려 줌.
- `doctor.py`: 릴스를 그릴 수 있는 환경인지 점검 (세션 시작 때 자동으로도 실행됨).
- `specprobe.py`: MP4가 Instagram 업로드 규격을 지키는지 항목별 검사.
- `draft.py`: 릴스 초안 도구 (게시일·슬러그, 수치 등록부, 원고 확장·점검, 게시글 문구). 스킬 `make-reel` 이 사용.
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

## 릴스 초안: `draft.py`

주제 한 줄이나 카드뉴스 원고로 **검수용 릴스 초안**을 만든다. 보통은 Claude Code 세션에서 "이 주제로 릴스 만들어 줘" 라고 말하면
프로젝트 스킬 `.claude/skills/make-reel/` 이 아래 명령을 순서대로 실행한다. 직접 쓸 수도 있다.

```
python3 tools/draft.py slot [--date YYYY-MM-DD] [--slug 영문-슬러그] [--create]
python3 tools/draft.py convert 2026/NN-이름/spec.json --out 폴더/skeleton.json
python3 tools/draft.py figures list [--grep 글자] | show ID | add ... | confirm ID --by 이름
python3 tools/draft.py expand 폴더/spec.src.json 폴더/spec.json
python3 tools/draft.py check 폴더/spec.json --out 폴더/check.json --strict [--src 폴더/spec.src.json] [--card 카드 spec.json]
python3 tools/draft.py caption 폴더/spec.json 폴더/caption.src.json --out 폴더/caption.txt
python3 tools/reel.py 폴더/spec.json 폴더/<게시일>-<슬러그>.mp4 --layout new --strict
```

- `slot`: 게시된 릴스와 기존 초안을 읽어 다음 게시일을 계산해 제안하고, 영문 슬러그를 검사하고, 날짜·슬러그 충돌을 알린다 (JSON). `--create` 는 `2026/reels/drafts/<게시일>-<슬러그>/` 만 만든다.
- `convert`: 카드뉴스 원고를 릴스 골격(시리즈, 장면 역할, 카드 재료, note, 카드 숫자)으로 바꾼다.
- `figures`: 수치 등록부 조회·추가·확인 (아래 "수치 등록부").
- `expand`: 자리표시자 `{{이름|서식}}` 가 든 원고 소스를 등록부·계산 모듈로 채워 `reel.py` 가 읽는 원고로 쓴다. 숫자마다 출처 장부가 붙는다.
- `check`: 숫자가 모두 등록부·입력·계산에서 왔는지 따라가 본다. 원고 속 장부를 믿지 않고 지금 등록부로 다시 계산하며, 옆에 `spec.src.json`(또는 `--src`)이 있으면 다시 확장한 결과와 대조한다. 등록부 밖 숫자는 오류, 미확인 수치를 쓴 줄은 `확인 필요` 로 알린다. `--card` 는 카드 원고와 대조한다.
- `caption`: 게시글 문구(첫 줄, 요약 3줄, 다음 편, 면책, CTA, 해시태그)를 조립한다. 면책·CTA 문구는 준법 검토 전 초안이다.

초안 폴더 `2026/reels/drafts/<게시일>-<슬러그>/` 에 들어가는 파일: `skeleton.json`(카드 입력일 때), `spec.src.json`, `spec.json`, `check.json`,
`caption.src.json`, `caption.txt`, `<게시일>-<슬러그>.mp4`, `<게시일>-<슬러그>.safe-sNN.png`.
초안은 `--layout new --strict` 로 그린다.

종료 코드: **0** 정상 / **1** 입력 오류 (파일 없음, JSON 오류, 규칙 위반, `check` 의 오류, 슬러그·날짜 오류) / **2** 환경 오류 (파일 쓰기 실패 등) / **3** `--strict` 인데 경고 있음.

초안은 git 에 올리지 않는다 (`2026/reels/drafts/` 는 `.gitignore`). 모든 산출물은 사람이 검수한 뒤에 게시한다.
`2026/reels/` 와 `specs/` 로 옮기는 승격은 Phase 3 승인 단계에서 한다.

## 수치 등록부

`tools/data/figures.json` 은 릴스에 쓰는 세법·요율·통계 수치의 단일 출처다. 항목마다 `label`, `kind`, `value`, `unit`,
`source`(이름·URL·위치), `candidate_sources`, `as_of`, `valid_until`, `legal_status`(시행·발의 등), `verified`(확인 여부), `notes` 를 가진다.

- **미확인**: 아직 사람이 1차 출처(law.go.kr 등)로 확인하지 않은 값. 릴스에는 쓸 수 있지만 `check` 가 그 줄을 `확인 필요` 로 알린다.
- **확인**: 사람 확인자가 1차 출처를 직접 열어 값을 맞춰 본 값.
- 검색으로 찾은 새 수치는 사용자가 승인한 뒤에만 `figures add` 로 넣고, 항상 `미확인` 이다 (확인 상태를 지정하는 옵션이 없다).
- `python3 tools/draft.py figures confirm ID --by 이름` 은 **사람 확인자(팀장)** 가 1차 출처를 확인한 뒤 직접 실행한다. Claude 는 실행하지 않는다. 빈 이름과 Claude/AI 이름은 거부된다.
- 출처가 없는 수치(`unsourced`)는 릴스에 쓰면 안 된다.
- `tools/data/caption_config.json`: 게시글의 면책·CTA 초안 문구와 브랜드 해시태그 목록. 브랜드 해시태그는 비어 있고 사용자만 채운다. 해시태그는 전체 5개 이하.

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
종료 코드: **0** 모두 통과 / **1** 릴스가 하나라도 FAIL (판정 불일치) / **2** 사용·환경 오류 (playwright 미설치, Chromium 실행 실패, 폰트 로드 실패, ffmpeg 인코딩 실패 등 — 릴스 FAIL 열 줄로 나누지 않고 한 줄로 알림).
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
