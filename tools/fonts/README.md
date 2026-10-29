# 번들 폰트: Noto Sans KR (Sans CJK KR)

릴스 렌더러(`tools/reelkit`)가 쓰는 브랜드 폰트다. 세션 이미지에 한글 폰트가 없어도 기존 릴스 10편과 같은 글리프로 그려지도록 저장소에 함께 둔다. 시스템에는 아무것도 설치하지 않는다.

## 출처

- Regular: <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/KR/NotoSansKR-Regular.otf>
- Bold: <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/KR/NotoSansKR-Bold.otf>
- Black: <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/KR/NotoSansKR-Black.otf>
- 라이선스 원문: <https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE> (`OFL.txt`로 저장)
- 업스트림 버전: Noto Sans CJK 2.004 (name ID 0 저작권 표기 "© 2014-2021 Adobe")
- 받은 날짜: 2026-10-28

## 라이선스

SIL Open Font License 1.1 (SIL Open Font License). 전문은 같은 폴더의 `OFL.txt`에 있다. 재배포와 저장소 포함이 허용된다.

## 벤더링 방식

- 선택: 원본 (2026-10-28 사용자 결정). `constants.FONT_VARIANT = "original"`.
- 업스트림 파일을 수정하지 않고 그대로 둔다. 서브셋 도구(pyftsubset, fonttools)는 쓰지 않았다.
- 그래서 아래 표의 digest는 업스트림 원본 digest와 같고, `tools/reelkit/constants.py`의 `FONT_SHA256`과도 같다.
- 세 파일 합계 14,494,040 bytes (약 14.5 MB)가 git 기록에 들어간다.

## 파일 목록

| file | bytes | sha256 | CSS weight |
|------|------:|--------|-----------:|
| NotoSansKR-Regular.otf | 4644748 | `69975a0ac8472717870aefeab0a4d52739308d90856b9955313b2ad5e0148d68` | 400 |
| NotoSansKR-Bold.otf | 4816044 | `5a6ceb287ed2fc6cfc6213144ebea68cbd94b20fc9eb873d8486493bf02d9bda` | 700 |
| NotoSansKR-Black.otf | 5033248 | `a9977a588488d2a7f544bb2b589b01bed071dca64a4655d438696301b527884b` | 900 |
| OFL.txt | 4301 | `6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2` | - |

`main` 브랜치는 움직일 수 있으므로 URL이 아니라 위 sha256으로 고정한다. 업스트림 커밋 SHA는 기록하지 못했다.

## 사용 방법과 규칙

- 400/700/900 세 굵기만 벤더링한다. `tools/cards.py`가 쓰는 Medium(500)은 이번 범위 밖이다.
- 렌더러는 `tools/reelkit/templates/frame.html`의 `@font-face`로 이 파일들을 `file://`에서 읽는다. 로드에 실패하면 시스템 폰트로 대체하지 않고 중단한다(종료 코드 2).
- 폰트를 바꾸면 `constants.FONT_VARIANT`·`FONT_SHA256`과 이 표를 함께 갱신하고 golden 회귀 시험을 다시 돌린다.

## 노트 배치 손글씨 폰트: Gaegu Bold

`layout: "note"` (노트 형식 릴스, `tools/reelkit/note.py`)에서만 쓰는 손글씨 폰트다. 위 Noto Sans KR 세트와 따로 두며 `constants.FONT_FILES`에는 넣지 않는다 (`browser.font_problems`가 기본 틀의 `@font-face` 3개를 기대하기 때문). 노트 페이지가 `@font-face`로 직접 불러온다.

- 출처: <https://raw.githubusercontent.com/google/fonts/main/ofl/gaegu/Gaegu-Bold.ttf> (Google Fonts, Gaegu Project Authors)
- 라이선스 원문: <https://raw.githubusercontent.com/google/fonts/main/ofl/gaegu/OFL.txt> (`OFL-Gaegu.txt`로 저장). SIL Open Font License 1.1, 재배포와 저장소 포함 허용
- 받은 날짜: 2026-10-29, 업스트림 파일을 수정하지 않음 (`main` 브랜치는 움직이므로 아래 sha256으로 고정)
- `tools/reelkit/constants.py`의 `NOTE_FONT_SHA256`과 같은 값이며 `python3 tools/doctor.py`의 `font-files` 줄이 이 파일을 함께 본다 (없거나 바뀌면 경고, 기존 Noto 점검은 그대로)

| file | bytes | sha256 | CSS weight |
|------|------:|--------|-----------:|
| Gaegu-Bold.ttf | 2962664 | `cc38a4af9506a45254d1ce07c589ec473d9e5f0be319e5a77b17c214903f8c1c` | 700 |
| OFL-Gaegu.txt | 4344 | `53a9ce47085d9fef613c7ecb3730dc80d25962510bbea231b89564f58240f251` | - |
