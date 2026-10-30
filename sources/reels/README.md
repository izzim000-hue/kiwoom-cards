# 보관된 릴스 원고 소스

승인 전 초안의 원고 소스(`spec.src.json`, `caption.src.json`)를 보관합니다. 초안 폴더(`2026/reels/drafts/`)는 git에 올라가지 않으므로, 다른 컴퓨터에서 같은 초안을 다시 만들 때 이 폴더를 씁니다.

## PC에서 다시 만들고 승인·게시하기

```
python3 tools/draft.py slot --date 2026-11-10 --slug deduction-vs-credit-items --create
cp sources/reels/2026-11-10-deduction-vs-credit-items/*.src.json 2026/reels/drafts/2026-11-10-deduction-vs-credit-items/
python3 tools/draft.py bundle 2026/reels/drafts/2026-11-10-deduction-vs-credit-items
python3 tools/draft.py approve 2026/reels/drafts/2026-11-10-deduction-vs-credit-items --by 이름
python3 tools/draft.py promote 2026/reels/drafts/2026-11-10-deduction-vs-credit-items
```

- `approve`는 사람 전용입니다. 자기 터미널에서 직접 실행하고 폴더 이름을 다시 입력합니다.
- 승인 전 확인: 영상, `review.md`, 항목 분류(홈택스 안내와 대조), 게시글 고지 문구(준법 검토 전 초안).
- 게시가 끝난 원고 소스는 이 폴더에서 지워도 됩니다.
