# Phase 4: 자막 연출 + 선택 배경음 (Motion & BGM) - Context

**Gathered:** 2026-10-29
**Status:** Ready for planning

<domain>
## Phase Boundary

같은 원고로 줄 진입(페이드+살짝 떠오름), 장면 전환 1종, 숫자 카운트업이 들어간 릴스를 만든다. 모션 끄기(`none`)는 기존 결과와 같다. 장면 체류 시간은 글자 양에 맞춰 정하고 너무 빠르거나 긴 장면은 경고한다. 사용자가 음원 파일과 라이선스 메모를 함께 줄 때만 배경음을 넣는다. Phase 3 검수 묶음 흐름(`draft.py bundle`)과 업로드 규격은 그대로 지킨다.

요구사항: MOTN-01 ~ MOTN-06. 미니 그래프(MOTN-V2-01)와 AI 내레이션(MOTN-V2-02)은 v2.

</domain>

<decisions>
## Implementation Decisions

진행 방식: 야간 예약 작업에서 사용자가 "추천대로"로 답해 온 방식에 따라 추천안으로 정했다(2026-10-29). 모두 되돌릴 수 있는 기본값이다.

### 모션 (MOTN-01~05)
- **D-01:** 렌더는 Phase 1의 결정적 시간 탐색 방식(Web Animations 일시정지 + `currentTime` 설정, 프레임마다 PNG)을 그대로 쓴다. 실시간 녹화(`record_video`)는 쓰지 않는다.
- **D-02:** 줄 진입: 각 줄이 약 300ms 동안 투명도 0→1, 아래에서 약 24px 위로 올라오며 나타난다. 줄 사이 간격은 약 120ms. 줄 단위 애니메이션으로 하고 글자(자소) 단위 분리는 하지 않는다 — 한글 줄바꿈 위치가 흔들리지 않게 하기 위해서다. 줄바꿈은 모션 없이 측정한 배치를 기준으로 고정한다.
- **D-03:** 장면 전환 1종: 약 0.3초 크로스페이드(이전 장면 페이드아웃과 다음 장면 페이드인 겹침). 슬라이드·와이프는 넣지 않는다.
- **D-04:** 카운트업: 원고의 등록부 수치 자리(`spec.json` 장부)에 선택 표시를 하면 0(또는 지정 시작값)에서 최종값까지 약 0.8초 동안 올라간다. 숫자 상자는 최종값 기준 고정 너비로 잡아 줄이 흔들리지 않게 한다. 마지막 프레임의 글자는 원고 표시 문자열과 한 글자까지 같아야 한다(테스트). 중간 값은 표시 서식(만, %, 원)을 따르고 반올림은 표시에서만 한다.
- **D-05:** 모션 선택은 원고 선택 필드 `motion`(Phase 2에서 예약됨)과 렌더 옵션으로 한다. 값은 `none`(기본, 기존 결과와 동일)과 `basic`(D-02~D-04) 둘. 기존 10편과 기존 초안은 `none`으로 렌더되어 golden이 바뀌지 않는다. — **Reversibility:** reversible
- **D-06:** 장면 체류 시간(MOTN-05): `basic`일 때 글자 수 기준으로 자동 계산한다(줄 진입·카운트업 시간 + 읽기 시간). 너무 짧거나(예: 1.5초 미만) 긴(예: 6초 초과) 장면은 렌더 시 경고한다. 기준값은 상수 한 곳에 둔다. `none`은 기존 timeline 규칙을 그대로 쓴다.
- **D-07:** 표지(cover_ms)와 장면 모음 정지 화면은 모션이 끝난 장면의 마지막 상태를 쓴다(Phase 3 frame_sink 유지).

### 배경음 (MOTN-06) — 오너 게이트
- **D-08:** 오너 게이트(음원·라이선스)는 미결정이다. 배경음은 **기본 비활성**이며, 사용자가 음원 파일 경로와 라이선스 메모를 함께 줄 때만 켜진다. 라이선스 메모가 없거나 비어 있으면 렌더를 거부한다(종료 코드 1).
- **D-09:** 음원은 절대 검색·다운로드·기본값으로 넣지 않는다. 음원 파일은 저장소에 커밋되지 않게 `.gitignore`로 막고, 초안 폴더 안이나 저장소 밖 경로만 받는다. 테스트는 ffmpeg로 만든 합성 음(사인파)만 쓴다.
- **D-10:** 믹싱: ffmpeg 필터로 영상 길이에 맞춰 반복·자르기, 페이드인·아웃(약 1초), 음량 정규화(목표 약 −16 LUFS, 피크 −1.5 dBTP). 배경음이 있어도 업로드 규격 검사(AAC 포함)를 통과해야 한다. 없으면 기존 무음 트랙 유지.
- **D-11:** 검수 요약(`review.md`)의 "음원 라이선스" 확인 항목에 음원 파일 이름과 라이선스 메모를 그대로 적고 사람 확인 대상으로 둔다. 승인 지문에 음원 파일 해시를 포함한다.

### 이어지는 결정
- 새 릴스는 `--layout new`, 기존 게시 파일은 건드리지 않음, golden 10/10 유지.
- 사용량 절약: 계획 검토·재리뷰 없이 코드 리뷰 1회, 최종 검증 1회.

### Claude's Discretion
- 정확한 이징 곡선, 줄 간 지연, 카운트업 표시 방식(원고 문법 또는 장부 플래그).
- 체류 시간 공식의 계수, 경고 기준값.
- 배경음 옵션 이름과 라이선스 메모 저장 형식.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/REQUIREMENTS.md` (MOTN-01~06), `.planning/ROADMAP.md` §Phase 4 (성공 기준 5개, Owner gate, Research flag: Intl.Segmenter·고정 너비 카운트업·렌더 시간 spike)
- `.claude/CLAUDE.md` — 결정적 시간 탐색 렌더, PNG 파이프, BGM ffmpeg 필터와 음량 수치(검증된 값)
- `.planning/research/STACK.md`, `.planning/research/PITFALLS.md`
- `.planning/phases/01-render-foundation/01-CONTEXT.md` 및 SUMMARY — 렌더러·timeline·golden
- `.planning/phases/02-draft-generation/02-CONTEXT.md` — `motion` 선택 필드, 장부·표시 서식
- `.planning/phases/03-compliance-review-bundle/03-0*-SUMMARY.md`, `03-REVIEW-FIX.md` — bundle 단계, frame_sink, review.md, approve 지문
- `tools/reelkit/{render,timeline,layout,encode,bundle,review,approve}.py`, `tools/reelkit/templates/frame.html`

</canonical_refs>

<code_context>
## Existing Code Insights

- 렌더는 현재 장면 끝 상태 PNG를 concat으로 인코딩(정지 화면). 모션은 프레임 단위 시간 탐색 + `image2pipe` 경로가 필요하다(CLAUDE.md에 검증된 방식과 측정값).
- `timeline.py`가 장면 시간·cover_ms를 계산한다. `none` 경로는 바꾸지 않는다.
- `encode.py`가 무음 AAC 트랙을 넣는다. 배경음은 같은 단계에서 필터 그래프로 대체한다.
- `bundle.py`가 render 단계를 부른다. 모션·배경음 옵션은 원고 필드와 bundle 옵션으로 전달한다.

</code_context>

<specifics>
## Specific Ideas

- 카운트업 예: "148.5만"은 0.0만 → 148.5만, 표시 서식 `man1`. 마지막 프레임 = "148.5만".

</specifics>

<deferred>
## Deferred Ideas

- 배경음 실제 음원·라이선스 증빙 형식 — 오너 게이트, 사용자 결정 대기
- 미니 그래프, AI 내레이션 — v2

</deferred>

---

*Phase: 04-motion-bgm*
*Context gathered: 2026-10-29*
