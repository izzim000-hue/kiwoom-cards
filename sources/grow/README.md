# 비유 하나를 키우는 1인칭 스토리 릴스 (tools/grow.py)

설명 대신 그림 하나를 끝까지 키워 가며 '예전의 나 → 바꾼 것 → 달라진 것'을 1인칭으로 들려준다(2026-11-16). 캐릭터 없이 절제된 선화 + Noto Sans KR(2026-11-16 사용자: 캐릭터 빼고 전문가답게).
첫 비유: 월급 = 씨앗 한 봉지. 그달에 먹으면 사라지고, 먼저 심은 한 줌만 몇 년 뒤 나무가 된다.

```bash
python3 tools/grow.py still sources/grow/<파일>.json <점검 폴더>
python3 tools/grow.py reel  sources/grow/<파일>.json 2026/reels/drafts/duo/<파일>.mp4
```

- `beats[].key`: hook, payday, spend, empty, change, rest, sprout, grow, names, conclude, ask (연출은 grow.py CHOREO)
- `beats[].say` 자막·녹음 대본, `pose`(point/think/cheer/worry/wave), `labels` 이름표 보이기, `hide` 이름표 숨기기, `d` 길이
- `labels`: 이름표 {x, y, text, style(navy/red/grn/ghost)}, `hook`, `conclude`, `ask` 상자 문구
- 수치는 넣지 않는다. 넣을 때는 출처·예시 표시.
