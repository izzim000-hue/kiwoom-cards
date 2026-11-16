# 두 사람 비교 스토리 릴스 원고 (tools/duo.py)

노트 템플릿이 강의처럼 보이는 문제를 풀려고 만든 형식(2026-11-16). 조건이 같은 가상 인물 두 명을 좌우에 세우고,
같은 화면 위에 요소가 하나씩 쌓이며 차이가 벌어지는 걸 보여 준다. 설명·팁 없이 장면과 결과로 느끼게 하고 결론은 끝에 한 번만.

```bash
python3 tools/duo.py still sources/duo/<파일>.json <점검 폴더>     # beat 마다 끝 화면 PNG
python3 tools/duo.py reel  sources/duo/<파일>.json 2026/reels/drafts/duo/<파일>.mp4
python3 tools/specprobe.py 2026/reels/drafts/duo/<파일>.mp4          # 9/9 PASS
```

| 키 | 뜻 |
|---|---|
| `title`, `badge`, `foot` | 맨 위 제목, 그 위 작은 표시("가상 인물 · 가상 예시"), 자막 위 작은 근거 줄 |
| `left` / `right` | `name`, `age`, `look`(`a` 짧은 머리 회색 셔츠 / `b` 단발 남색 니트) |
| `hook` | 첫 화면 큰 글씨(0초부터 보임). `big` 은 `|` 줄바꿈, `==강조==` 형광펜. `sub` 작은 글씨 |
| `items` | 화면 요소. `side` L/R(칸 안, `y` 는 칸 기준) 또는 C(가운데 상자, `y` 는 화면 기준) |
| `beats` | 자막 한 줄 = 한 박자. `say` 자막(녹음 대본), `show`/`hide` 요소, `pose` {L,R}, `focus` L/R/C(다른 칸 흐리게, C 는 둘 다), `d` 길이(없으면 글자 수로) |

요소 종류: `tag`(알약, `icon`·`style` navy/red/grn/ghost), `money`(작은 라벨 + 큰 숫자), `jar`(저금통, `fill` 0~1, 숫자 카운트업). 가운데 상자는 `style: dark`, `mentor: true`(새싹 멘토 등장).
특수 요소: `eq`(=), `vs`(≠).
포즈: stand, phone, card, book, worry, happy, sigh, oh. 아이콘: cal, card, bank, wallet, car, arrow, zero.

규칙: 인물·금액은 가상이면 화면(`badge`)과 본문에 표시한다. 외부 수치는 공식 출처 확인 뒤 `src` 에 기준을 적는다. 단정 수익 표현 금지. 장면당 4초 안팎.
