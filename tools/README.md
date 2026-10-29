# tools

- `cards.py`: 카드뉴스 6장(1080x1350) PNG 생성. 세이지 그린 바탕, 마지막 장 딥그린.
- `reel.py`: 자막형 릴스(1080x1920) MP4 생성. 목소리 없음. 출력 끝에 표지용 시점(cover_ms)을 알려 줌.
- `doctor.py`: 릴스를 그릴 수 있는 환경인지 점검 (세션 시작 때 자동으로도 실행됨).
- `specprobe.py`: MP4가 Instagram 업로드 규격을 지키는지 항목별 검사.
- `draft.py`: 릴스 초안 도구 (게시일·슬러그, 수치 등록부, 원고 확장·점검, 게시글 문구, 검수 묶음 `bundle`, 표현 점검 `compliance`·`redteam`, 사람 승인 `approve`, 옮기기 `promote`). 스킬 `make-reel` 이 사용.
- `golden.py`: 게시된 릴스 10편을 다시 그려 같은 결과가 나오는지 확인하는 회귀 검사.

이미지 폴더 규칙: `2026/<게시일>-<영문-슬러그>/insta_1..6.png`, 릴스는 `2026/reels/<게시일>-<영문-슬러그>.mp4`.
이 저장소에는 공개용 카드뉴스·릴스만 둔다. 고객 정보·상담 자료 금지.

## 릴스 만들기: `reel.py`

```
python3 tools/reel.py SPEC OUT [--layout legacy|new] [--motion none|basic] [--strict] [--overlay-all]
```

- `SPEC`: 원고 JSON (`2026/reels/specs/` 의 게시된 10편이 예시). `OUT`: 출력 MP4 경로.
- 끝에 `duration=26.1s cover_ms=1250` 한 줄을 stdout 으로 낸다. 경고와 규격 보고는 stderr.
- `--layout legacy` (기본): 게시된 10편과 같은 배치. **게시된 10편은 legacy 로만 재현한다.** 이 배치는 결과를 바꾸지 않는다 (D-05).
- `--layout new`: 근거(36px, 본문 바로 아래)와 계정명을 안전영역 안에 쌓는 새 배치. **새 릴스는 new 로 만든다.**
  줄바꿈·넘침·안전영역 침범을 `scene N line M: KIND (값) "글자"` 로 알린다. 글자는 줄이거나 자르지 않는다.
- `--strict`: 레이아웃 경고가 있으면 MP4 를 쓴 뒤 종료 코드 3.
- `--overlay-all`: 모든 장면의 안전영역 미리보기를 쓴다 (new 배치).
- 배경음은 넣지 않는다: `--bgm`·`--bgm-license` 를 주면 `음원 오류` 로 거부한다 (종료 코드 1, MP4 없음). 배경음은 `draft.py bundle` 로만 넣는다 (아래 "배경음").
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
- `caption`: 게시글 문구(첫 줄, 요약 3줄, 근거·기준, 면책, CTA, 다음 편, 해시태그)를 조립한다. 면책·CTA 문구는 준법 검토 전 초안이다. 게시글의 숫자는 원고 장부의 숫자만 쓸 수 있고, 미확인 수치를 쓴 줄은 `확인 필요` 경고, 발의 수치는 같은 줄에 발의안·정부안 표기가 필요하다. 원고 점검에 오류가 있으면 조립하지 않는다.

초안 폴더 `2026/reels/drafts/<게시일>-<슬러그>/` 에 들어가는 파일: `skeleton.json`(카드 입력일 때), `spec.src.json`, `spec.json`, `check.json`,
`caption.src.json`, `caption.txt`, `<게시일>-<슬러그>.mp4`, `<게시일>-<슬러그>.safe-sNN.png`.
초안은 `--layout new --strict` 로 그린다.

종료 코드: **0** 정상 / **1** 입력 오류 (파일 없음, JSON 오류, 규칙 위반, `check` 의 오류, 슬러그·날짜 오류) / **2** 환경 오류 (파일 쓰기 실패 등) / **3** `--strict` 인데 경고 있음.

초안은 git 에 올리지 않는다 (`2026/reels/drafts/` 는 `.gitignore`). 모든 산출물은 사람이 검수한 뒤에 게시한다.
`2026/reels/` 와 `specs/` 로 옮기는 일은 사람 승인 뒤 `promote` 로 한다 (아래 "승인과 옮기기").

## 검수 묶음: `draft.py bundle`

```
python3 tools/draft.py bundle 폴더 [--card 카드 spec.json] [--request-start EPOCH] [--rules PATH] [--registry PATH] [--config PATH] [--bgm 음원 --bgm-license 메모]
```

`폴더` 는 `2026/reels/drafts/<게시일>-<슬러그>/` 이고 안에 `spec.src.json` 과 `caption.src.json` 이 있어야 한다. 명령 한 번이 아래 순서로 전부 만든다.
`expand` -> `check` -> `caption` -> 표현 점검 -> 렌더(new 배치, 같은 프로세스) -> 표지 -> 장면 모음 -> `review.md`.
스킬 `make-reel` 의 유일한 렌더 경로다.

- 만드는 파일: `spec.json`, `check.json`, `caption.txt`, `compliance.json`, `<이름>.mp4`, `<이름>-cover.png`, `<이름>-scenes.png`, `review.md`, `record.json`, `bundle.json`.
  표지는 장면 1의 마지막 상태이고, 인스타그램 격자 자르기 안에 글자가 들어오는지 확인해 `COVER_CROP` 경고로 알린다.
- 다시 실행: 원고 소스를 고친 뒤에도 같은 명령으로 전부 다시 만든다. 시작할 때 이전 산출물과 `approval.json` 을 지우므로 이전 승인은 무효가 된다.
  손으로 쓴 `spec.src.json`, `caption.src.json`, `skeleton.json`, `record.json`, `created.json` 은 지우지 않는다.
- `record.json`: 광고 해당 여부, 키움 브랜드 관계, 심의 상태, 심의번호를 **사람이** 적는 파일. 처음에는 모두 `미확인`, 없을 때만 만들고 다시 쓰지 않는다. Claude 는 `미확인` 외의 값을 쓰지 않는다.
- `created.json`: `slot --create` 가 폴더를 만든 시각을 남긴다.
- 시간: `bundle.json` 에 단계별 초와 전체 초(`elapsed_s`)가 남는다. `--request-start` (epoch 초, 스킬이 `date +%s` 로 기록)나 `created.json` 이 있으면 요청부터 걸린 시간
  `elapsed_since_request_s` 와 `within_10_min` 도 남는다 (목표 10분). 둘 다 없으면 이 값들은 `null`.
- 종료 코드: **0** 완료 / **1** 초안·원고·규칙 입력 오류 (`check` 의 오류 포함, `review.md` 에 실패 요약) / **2** 렌더·파일 환경 오류 / **3** 레이아웃 또는 표지 경고 (항상 엄격, 파일은 이미 씀) / **4** 업로드 규격 FAIL (4 가 우선).
  표현 점검의 발견은 종료 코드를 바꾸지 않는다. 발견 자체가 산출물이다.

## 표현 점검: `draft.py compliance`, `draft.py redteam`

```
python3 tools/draft.py compliance 폴더/spec.json [--caption 폴더/caption.txt] [--check 폴더/check.json] [--rules PATH] [--out JSON]
python3 tools/draft.py redteam [--rules PATH] [--corpus PATH] [--heldout PATH] [--json]
```

- `compliance`: 원고, 근거(`basis`), 게시글, 해시태그를 `tools/data/compliance_rules.json` 의 규칙으로 훑는다. 발견마다 위치·문제 표현·사유·대체 표현 제안을 보이고 파일은 고치지 않는다.
  머리말은 두 가지뿐이다: `위험 표현 n건 발견` 또는 `패턴상 발견 없음 — 사람 검수 필요`. 어느 쪽도 점검이 끝났다는 뜻이 아니다.
  규칙 상태는 `초안 규칙 — 준법 검토 전` 이다. 법령 조문 번호는 규칙과 출력에 쓰지 않는다.
- 규칙 더하기·고치기 (코드 수정 없음): `rules` 배열에 항목을 추가한다.
  - 필수: `id`(겹치지 않게), `category`, `severity`, `reason`, `suggest`, 그리고 패턴 규칙은 `pattern` 과 `examples`(`hit` 목록과 `miss` 목록).
    `examples` 는 파일을 읽을 때 실제로 실행되므로, 안 맞는 예시나 잘못된 정규식이 있으면 규칙 id 를 밝히고 거부한다.
    `hit`·`miss` 가 하나라도 비어 있어도 거부한다. 규칙이 하나도 없는 파일도 거부한다.
  - 처리가 끝나지 않을 수 있는 정규식은 읽을 때 거부한다: 반복 안의 반복(`(?:가+나?)+다`, `(?:가{1,})+다`), 끝없는 반복 안의 갈래(`(가|가)+다`),
    그리고 긴 시험 글에서 0.1초를 넘는 정규식.
  - 선택: `negatable`(부정문 안의 표현은 제외, 기본 true), `except`(예외 정규식 목록), `applies_to`(`reel`/`caption`), `type`(`pattern`, `requires`, `basis_required`) 와 `when`·`when_scene`·`must_have`·`scope`.
  - 부정·언급 예외 (규칙 v0.2): 매치 바로 뒤 글은 장면의 그 줄 안에서만 보고(줄바꿈·쉼표·문장 끝에서 끊음), 최상위 `negators`·`mention_markers` 는
    그 글의 맨 앞에 맞춰 본다. 그래서 부정은 매치한 표현에 붙어 있어야 한다 ('보장하지 않습니다', '보장 상품은 없어요', '보장된다는 뜻은 아니에요').
    다음 줄의 '놓치지 마세요' 나 같은 줄 뒤 절의 '손해 보지 않아요' 는 앞의 주장을 덮지 않는다. 부정을 다음 줄로 넘겨 쓰면 잡히므로 같은 줄에 쓴다.
  - `compact_terms`(공백·숨은 글자로 쪼갠 표현): 문자열이나 `{"term": "무조건절세", "category": "세무 단정"}` 꼴. 분류를 안 적으면 단정·보장이다.
    낱말 첫머리에서 시작할 때만 세고('근무 조건' 의 '무조건' 은 제외), 같은 자리를 패턴 규칙이 이미 잡았거나 부정으로 뺐으면 다시 세지 않는다.
  - 매크로: 패턴 안의 `{J}` 는 조사(은/는/이/가…)가 있어도 없어도 맞게, `{S}` 는 공백이나 줄바꿈 한 번을 허용한다 (장면 경계는 넘지 않음).
  - 심각도 정책: **수정 필요** 는 정확한 패턴에만 쓴다. 수정 필요가 하나라도 남으면 `promote` 가 거부하고 면제 방법이 없기 때문이다. 애매한 표현은 **확인 필요** 로 둔다 (사람이 판단).
- `redteam`: 규칙의 탐지율과 오탐을 한국어 보고서로 낸다. 줄은 네 부분이다: 기존 10편(수정 필요 0건이어야 함), 가상 문장 표본(표본 내), 규칙을 보지 않고 먼저 써 둔 따로 쓴 문장(`규칙 조정에 쓰지 않음`)의 부적절·적절 문장.
  마지막 줄은 `redteam: 표본 내 탐지 a/b · 오탐 c/d · 따로 쓴 문장 탐지 e/f · 오탐 g/h · 기존 10편 수정 필요 0건` 형태다.
  표본 내 수치는 규칙을 쓴 쪽이 같은 문장을 보고 맞춘 결과라 실제보다 높게 나온다. 따로 쓴 문장 줄을 함께 읽는다. 키워드·패턴 방식이라 암시적 표현은 잡지 못한다.
  보고서를 보고 규칙을 고칠 때는 따로 쓴 문장 파일(`tools/tests/redteam/heldout.json`)을 고치거나 거기에 맞춰 패턴을 짜지 않는다.

## 승인과 옮기기: `draft.py approve`, `draft.py promote`

```
python3 tools/draft.py approve 폴더 --by 이름     # 사람 전용 (Claude 실행 금지)
python3 tools/draft.py promote 폴더
```

- `approve` 는 **사람이 자기 터미널에서만** 실행한다 (Claude 실행 금지). 터미널이 아니면 아무 일도 하기 전에 거부한다. 빈 이름과 Claude/AI 이름도 거부한다.
  `bundle.json` 이 완료 상태가 아니거나 업로드 규격 FAIL(종료 코드 4)이면 거부한다 (종료 3 레이아웃 경고는 주의만). `promote` 도 같은 검사를 다시 한다.
  지금 규칙으로 다시 훑어 수정 필요가 있으면 거부하고, 아니면 머리말·건수·`record.json` 값(미확인 항목 표시)·지문을 기록할 파일 목록을 보인 뒤 폴더 이름을 다시 입력받는다.
  맞으면 `approval.json` 에 승인자, 시각, 규칙 버전·sha256, 건수, `record.json` 사본, 열 파일의 sha256 을 쓴다. 지문 대상: `<이름>.mp4`, `<이름>-cover.png`, `spec.json`, `caption.txt`, `spec.src.json`, `caption.src.json`, `check.json`, `compliance.json`, `review.md`, `bundle.json`.
  완료된 `bundle` 은 `bundle.json` 의 `outputs` 에 원고 소스·산출물·`review.md`·장면 모음의 sha256 을 남기고, `approve` 는 지금 파일이 그와 같지 않으면(묶음 뒤 손으로 고침) 거부한다. 고치려면 소스를 고치고 `bundle` 을 다시 실행한다.
- `promote` 는 아래가 모두 맞을 때만, 네 파일을 그 초안의 릴스 폴더로 옮긴다: `<이름>.mp4` 와 `<이름>-cover.png` 는 `2026/reels/`, `spec.json` 은 `2026/reels/specs/<이름>.json`, `caption.txt` 는 `2026/reels/captions/<이름>.txt`.
  조건: `approval.json` 이 있고 폴더 이름과 같다 / 승인 뒤 열 파일이 하나도 바뀌지 않았다 / 저장소 규칙 파일이 승인 때와 같고(다르면 거부 — 다시 승인) 그 규칙으로 다시 훑어도 수정 필요 0건 / 네 목적지가 모두 비어 있다.
- 규칙 파일은 고를 수 없다: `approve`·`promote` 에는 `--rules` 가 없고 언제나 `tools/data/compliance_rules.json` 으로 판정한다. 규칙이 하나도 없는 파일은 읽을 때 거부한다.
  `bundle --rules` 로 다른 규칙을 써서 만든 묶음(`compliance.json` 의 규칙 sha256 이 다름)은 `approve` 가 거부한다.
  하나라도 어긋나면 파일 이름을 밝히는 한국어 사유로 거부하고 아무것도 만들지 않는다. 중간에 실패하면 이번에 만든 것을 전부 되돌린다.
- 덮어쓰지 않는다: 이미 있는 목적지는 거부하고, 복사본은 `.<목적지 이름>.part` 로 쓰고 지문을 다시 맞춘 뒤 하드링크로 이름을 붙여 경쟁 상황에서도 교체하지 않는다.
- git 은 실행하지 않는다. `promote` 가 `git add <경로>` 안내를 출력하면 사람이 실행하고 커밋도 사람이 한다.
- 남은 위험 (사용자 결정 사항): 터미널을 흉내 내는 pty 래퍼로 `approve` 를 실행할 수 있고, Claude 가 `approval.json` 이나 `record.json` 을 직접 써 넣을 수도 있다.
  `promote` 는 승인 기록의 승인자(사람 이름)·시각 꼴, 규칙 버전·sha256, 건수가 지금 규칙으로 다시 센 값과 맞는지 보지만, 지문을 계산할 수 있는 프로세스가 맞춰 쓴 기록까지 가려내지는 못한다.
  이를 막는 권한 거부 규칙은 사용자가 정할 일로 남겨 두었고 설정하지 않았다. 위조된 기록으로 `promote` 해도 파일이 `git status` 에 보일 뿐 커밋·게시는 일어나지 않으므로 사람이 `git diff` 와 `review.md` 로 확인한다.

## 자막 모션과 배경음

### 모션: `"motion": "none" | "basic"`

- 원고 소스(`spec.src.json`)의 `"motion"` 필드로 정한다. 없으면 `none` 이고 기존 10편과 같은 정지 화면 형식 그대로다 (`none` 은 바뀌지 않았고 기준선 시험이 지킨다).
  `bundle` 에는 모션 옵션이 없다. 단독 렌더(`reel.py`)에서만 `--motion none|basic` 으로 덮어쓸 수 있다. `basic` 은 `--layout new` 에서만 쓸 수 있다 (legacy 와 함께 쓰면 종료 코드 1).
- `basic`: 줄이 0.3초 동안 페이드하며 24px 떠오른다 (줄 사이 0.12초). 장면 사이는 0.3초 크로스페이드다. 표지와 장면 모음 이미지는 각 장면의 마지막 프레임이다.
  전환 0.3초 동안 앞뒤 장면의 근거 문구와 계정명이 겹쳐 보일 수 있다 (사람이 영상을 보고 판단).
- 카운트업: 장면 줄의 자리표시자 끝에 `|up` 을 붙인다 (`{{c_low|man1|up}}`). 줄에 처음 나타날 때 0 에서 0.8초 동안 올라가 마지막 프레임은 원고 숫자와 같다.
  중간 숫자는 연출이고 장부 값은 최종값뿐이다 (`review.md` 에 이 안내와 확인 항목이 붙는다). 시작값은 0 으로 고정이며 바꿀 수 있게 하는 것은 나중 선택지다.
  `top`·`basis` 에는 쓸 수 없다. 숫자가 줄바꿈을 바꾸면 `COUNTUP_WRAP` 경고 — 줄 수가 달라질 때뿐 아니라 줄 수가 같아도 줄바꿈 위치가
  달라질 때(`최대 연금 / 148.5만까지 받아요` -> `최대 연금 148.5만 / 까지 받아요`)도 낸다 (숫자 상자 뒤에 줄을 나눌 자리가 생기기 때문).
  중간 숫자는 마지막 숫자의 표시 정밀도로 센다 (`150만` 이면 `0만` … `149만`, `1억 원` 이면 억 단위). 숫자 상자의 폭은 렌더되는 모든 프레임의
  글자 중 가장 넓은 것에 맞춰 중간 숫자가 옆 글자를 덮지 않는다 (`motion.countup_step`, `countup_variants`; 시험 `CountUpFit` 이 프레임마다 잰다).
- 장면 체류 시간 = 줄이 다 나타나는 시간 + 0.6초 + 글자 수 / 16 (+ 전환 0.3초). 1.5초보다 짧으면 `DWELL_SHORT`, 6.0초보다 길면 `DWELL_LONG` 경고다.
  기준과 비교하는 값은 전환 0.3초를 포함한 장면 길이다. 마지막 장면에는 나가는 전환이 없으므로, 같은 기준이라도 마지막이 아닌 장면은
  읽을 수 있는 시간이 0.3초 덜 남는다 (예: 마지막이 아닌 장면은 읽기 1.2초 + 전환 0.3초면 `DWELL_SHORT` 가 아니다).
  `DWELL_SHORT`, `DWELL_LONG`, `COUNTUP_WRAP` 은 `bundle` 에서 종료 코드 3 (레이아웃 경고와 같음, 사람이 `review.md` 로 판단하고 승인 가능)이다.
  상수는 `tools/reelkit/motion.py` 한 곳에만 있다. 계수는 게시된 10편의 길이에 맞춰 잡은 값이며 사람이 영상을 본 확인은 아직 남아 있다.
- 렌더 시간: 프레임마다 시각을 맞춰 찍고 ffmpeg 에 흘려 보내므로 26.3초 `basic` 릴스(카운트업 2곳)의 묶음 전체가 이 환경에서 79.6초 걸렸다 (측정값, 10분 목표 안).

### 모션 none 기준선 (`tools/tests/golden/none-new.json`)

- `NoneUnchanged` 시험이 `motion: none` 새 배치 렌더를 Phase 4 소스 수정 전에 찍은 기준선과 비교한다. 시간·경고·마크업 해시·ffmpeg 인자는 환경과 관계없이
  정확히 같아야 하고(다르면 코드 회귀 — 기준선을 다시 만들지 말고 코드를 고친다), 디코딩 프레임·안전영역 미리보기의 픽셀 해시도 정확히 같아야 한다.
- 픽셀 해시는 Chromium·폰트·ffmpeg 가 바뀌면 코드가 그대로여도 달라진다. 그럴 때 **지금 코드로 다시 만들지 않는다** (그러면 지금 코드끼리 비교해 아무것도 지키지 못한다).
  `python3 tools/tests/none_guard.py --regenerate-from-base` 가 단계 전 커밋 `3fde951` 의 코드를 임시 git worktree 에 꺼내 그 코드로 이 환경에서
  기준선을 다시 찍고, JSON 만 복사한 뒤 worktree 를 지운다. 그 다음 시험이 지금 코드와 비교한다. 지금 코드에서 `--write` 는 거부한다 (종료 코드 1).
  다시 찍은 기준선은 사람이 `git diff` 로 픽셀 해시만 바뀌었는지 확인하고 커밋한다.

### 배경음: `--bgm`, `--bgm-license`

```
python3 tools/draft.py bundle 폴더 --bgm 음원파일 --bgm-license "이용 권리 메모"
```

- 배경음은 `bundle` 로만 넣는다. 라이선스 메모가 `bgm.json`·`review.md`·승인 지문에 남고 `approve`/`promote` 를 거치는 경로는 이것뿐이라,
  메모를 남기지 못하고 출력 경로(게시 폴더 `2026/reels/` 포함)를 막지 못하던 `reel.py --bgm` 은 뺐다 (주면 종료 코드 1 로 거부, WR-01).
- 기본은 무음이다. 음원 파일과 라이선스 메모를 **둘 다** 줘야 한다. 하나만 주거나 메모가 비어 있으면(공백만 포함) 아무것도 지우거나 렌더하기 전에 `음원 오류` 로 거부한다 (종료 코드 1).
  메모는 500자까지 자유 글이다. 라이선스 증빙을 어떤 형식으로 받을지는 소유자 결정이 남아 있어 형식을 정하지 않았다.
- 음원 규칙: 일반 파일(심볼릭 링크 거부), 확장자 `.mp3 .m4a .wav .aac .ogg .opus .flac`, 오디오 스트림이 있고(앨범 그림은 허용, 영상이 든 파일은 거부) 3초 이상.
  저장소 안의 파일은 그 초안 폴더 안에 있고, 이름이 `bgm.*` 가 아니며(대소문자 무관), `git check-ignore` 로 물어 git 이 무시하는 파일일 때만 받는다
  (커밋 방지 — `.gitignore` 내용이나 대소문자에 기대지 않는다. git 이 없거나 저장소가 아니면 거부). 저장소 밖 파일은 어디든 된다.
  초안 폴더에 `bgm.*` 와 대소문자만 다른 파일(`BGM.MP3` 등)이 있으면 복사가 그 파일을 덮지 않도록 거부한다.
- 이 도구는 음악을 찾거나 내려받거나 고르지 않는다. 입력은 사용자가 준 경로 하나뿐이다.
- 믹스: 영상 길이에 맞춰 반복하거나 자르고, 시작과 끝 1초 페이드, 약 -16 LUFS / 최대 -1.5 dBTP 로 음량을 맞춘다 (ffmpeg 한 번). 업로드 규격 9항목과 AAC 44.1 kHz 스테레오는 그대로다.
  실제 음악의 음량은 사인파 시험과 1~2 LU 다를 수 있어 귀로 확인한다 (`review.md` 의 음량 확인 항목).
- `bundle`: 음원을 초안 폴더에 `bgm.<확장자>` 로 복사하고 `bgm.json` (원본 파일 이름, 복사본 이름, sha256, 라이선스 메모, 길이)을 쓴다. 믹스는 복사본에서 한다.
  검사와 복사 사이에 원본이 바뀌면 (복사본 sha256 이 검사 때 원본과 다르거나 복사본이 오디오 검사를 다시 통과하지 못하면) 복사본을 지우고
  `음원 오류` 로 멈춘다 (종료 코드 1, 영상 없음). `bgm.json` 의 길이는 복사본에서 잰 값이다.
  `bundle.json` 에 같은 기록(`bgm`)과 두 파일의 지문(`outputs`)이 남고, `review.md` 의 음원 라이선스 줄이 원본 파일 이름·sha256 앞 12자·메모를 그대로 보여 준다 (사람이 이용 권리를 확인).
  배경음이 없으면 예전 문구(`배경음 없음 = 무음`)가 그대로 나온다.
- 승인: 배경음이 있는 묶음은 `approve` 와 `promote` 가 오디오를 지문(`approval.json` 의 `files`)에 포함하고, `bundle.json` 의 `bgm` 과 폴더의 `bgm.json`·복사본이 양쪽으로 맞는지 본다.
  `bundle.json` 에 없는데 폴더에 `bgm.json` 이나 `bgm.*` 가 있어도, 있는데 파일이 없거나 바뀌어도 거부한다. `promote` 는 오디오를 옮기지 않는다 (네 파일만).
- 다시 묶기: `--bgm` 없이 다시 `bundle` 하면 `bgm.json` 과 `bgm.*` 복사본이 지워져 낡은 음원이 이월되지 않는다. 사용자가 둔 다른 이름의 음원 파일은 지우지 않는다.
  폴더 목록에 글자 그대로 있는 `bgm.json`·`bgm.<확장자>` 만 지우므로 대소문자를 가리지 않는 파일 시스템에서도 `BGM.MP3` 같은 사용자 파일은 남고, 이번 실행의 원본도 지우지 않는다.
- 커밋 방지: `.gitignore` 가 mp3, m4a, wav, aac, ogg, opus, flac 을 대소문자와 관계없이(`*.[mM][pP]3` 꼴) 무시하고 `2026/reels/drafts/` 도 무시한다. 시험은 ffmpeg 사인파만 임시 폴더에서 만들어 쓴다.

## 수치 등록부

`tools/data/figures.json` 은 릴스에 쓰는 세법·요율·통계 수치의 단일 출처다. 항목마다 `label`, `kind`, `value`, `unit`,
`source`(이름·URL·위치), `candidate_sources`, `as_of`, `valid_until`, `legal_status`(시행·발의 등), `verified`(확인 여부), `notes` 를 가진다.

- **미확인**: 아직 사람이 1차 출처(law.go.kr 등)로 확인하지 않은 값. 릴스에는 쓸 수 있지만 `check` 가 그 줄을 `확인 필요` 로 알린다.
- **확인**: 사람 확인자가 1차 출처를 직접 열어 값을 맞춰 본 값.
- 검색으로 찾은 새 수치는 사용자가 승인한 뒤에만 `figures add` 로 넣고, 항상 `미확인` 이다 (확인 상태를 지정하는 옵션이 없다).
- `python3 tools/draft.py figures confirm ID --by 이름` 은 **사람 확인자(팀장)** 가 1차 출처를 확인한 뒤 대화형 터미널에서 직접 실행한다 (화면의 값을 보고 id 를 다시 입력해야 하며, 터미널이 아니면 거부). Claude 는 실행하지 않는다. 확인일은 발견일 이후·오늘 이전이어야 한다. 빈 이름과 Claude/AI 이름은 거부되지만 이 검사는 실수 방지용이다.
- `figures.json` 을 직접 고쳐 `확인` 으로 바꾼 항목에 확인자·확인일이 없거나 날짜가 미래·발견일 이전이면 `check` 와 `figures list` 가 오류(종료 1)로 알린다. 직접 고친 기록 자체는 git diff 로 사람이 확인한다.
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

전체 시험 679개 (게시된 릴스를 다시 그리고 모션·배경음 릴스를 여러 번 렌더하므로 이 환경에서 측정한 시간이 약 13분 — 793초). 일부만: `python3 -m unittest discover -s tools/tests -p 'test_doctor.py' -v`.
모션은 `test_motion.py` (60개, 약 6분), 배경음은 `test_bgm.py` (32개, 약 1.5분), 승인에 든 오디오는 `test_approve.py` 의 `ApproveBgm`.

## 폰트와 고정 버전

- `tools/fonts/`: 번들 Noto Sans KR 400/700/900 (SIL OFL, 출처와 sha256 은 `tools/fonts/README.md`). 시스템에 한글 폰트가 없어도 같은 글자 모양으로 그리기 위한 것이다.
  **폰트를 바꾸면** `reelkit/constants.py` 의 `FONT_SHA256` 과 `tools/fonts/README.md` 를 함께 고치고 `golden.py` 를 다시 돌린다.
- `tools/requirements.txt`: `playwright==1.63.0` 고정. 미리 깔린 Chromium 과 맞는 버전이다.
