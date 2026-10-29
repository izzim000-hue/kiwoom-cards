# Phase 2: 초안 생성 (Draft Generation) - Research

**Researched:** 2026-10-29
**Domain:** 릴스 원고 생성 파이프라인 (수치 등록부 + 계산 + 숫자 검사 + 게시글 문구), Python stdlib + 기존 reelkit
**Confidence:** MEDIUM. 코드 구조·재현 계산·숫자 탐지는 이 세션에서 직접 실행해 HIGH. 세법·통계 값은 1차 출처(law.go.kr, nts.go.kr, nps.or.kr, kostat 계열)를 이 세션에서 한 번도 열지 못해 전부 2차(뉴스·블로그 요약) 수준이다.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**수치 등록부 확인 절차**
- **D-01:** 수치 등록부는 데이터 파일(저장소에 커밋)로 두고, 항목마다 값·단위·출처(URL 또는 문서명)·기준일·확인일·시행 상태(시행/발의/폐지)·확인 상태(미확인/확인)·확인자를 기록한다. — **Reversibility:** costly — 원고가 등록부 항목 id를 참조하므로 스키마를 바꾸면 기존 초안 참조와 재현 시험을 함께 고쳐야 함
- **D-02:** Claude가 웹 검색으로 찾은 수치는 등록부에 **"미확인"**으로 추가한다. 최초 확인은 사람(팀장)이 하고, 확인 시 확인 상태·확인일·확인자를 채운다. law.go.kr·nts.go.kr은 세션에서 열리지 않으므로 Claude가 "확인"으로 바꾸지 않는다.
- **D-03:** 미확인 수치도 초안 원고에는 쓸 수 있다. 다만 그 수치를 쓴 장면·줄은 출력에 **"확인 필요"**로 표시된다(3단계 점검표의 입력이 됨). 막지 않고 표시한다.
- **D-04:** "발의" 상태 수치는 원고에 확정 표현으로 쓰지 못한다. 쓰려면 "발의안" 등 상태 표기가 같은 줄 또는 basis에 있어야 하고, 없으면 오류로 걸러낸다. "폐지" 상태 수치는 사용 불가.
- **D-05:** 파생 수치(예: 100만 원 × 16.5% = 16.5만 원, 세율 구간별 효과)는 원고에 손으로 적지 않고 프로그램이 등록부 값으로 계산한다. 기존 편 수치(예: `2026-10-26-tax-deduction`의 6.6만·38.5만·16.5만·13.2만) 재현 시험을 둔다.

**등록부에 없는 수치가 필요할 때**
- **D-06:** 원고 작성 중 등록부에 없는 수치가 필요하면 **작성을 멈추고 사용자에게 먼저 묻는다** ("이 수치가 필요합니다 — 출처 후보 ○○"). 추정 숫자로 채우지 않는다. 사용자가 승인하면 D-02 절차로 미확인 항목을 추가하고 진행한다.
- **D-07:** 등록부에 없는 숫자가 원고에 남아 있으면 검사 단계에서 걸러진다(경고가 아니라 오류). 숫자가 아닌 일반 표현(회차 번호, "3가지" 같은 구성 숫자, 날짜)은 예외 규칙으로 구분한다 — 구분 규칙은 플래너 재량.

**시리즈·회차·다음 편 예고**
- **D-08:** 시리즈를 지정하면 첫 장면 상단(`top`)에 `시리즈명 ①` 형식(원문자 회차)으로 넣는다. 기존 편의 첫 장면 상단 = 시리즈명 관례를 잇는다.
- **D-09:** 다음 편 예고를 지정하면 마지막(CTA) 장면에 `다음 편: ○○` 한 줄을 넣는다.
- **D-10:** 게시글 문구 첫 줄에도 같은 시리즈명·회차가 자동으로 들어가고, 예고가 있으면 문구 끝에 같은 예고가 들어간다. 원고와 문구의 값은 한 곳(원고의 새 선택 필드)에서 나온다.

**게시글 문구 형식**
- **D-11:** 게시글 문구 순서: 훅 → 핵심 요약 3줄 → 근거·기준일 → 일반 정보 고지("개인 상황에 따라 다를 수 있으며, 세무 판단은 세무사 확인이 필요합니다" 취지) → CTA(프로필 링크 · 1분 노후자금 계산기).
- **D-12:** 해시태그는 주제 태그 3~5개, 최대 5개. 고정 브랜드 태그는 Claude가 임의로 만들지 않는다. 사용자가 정해 주면 설정값으로 추가하며, 그때도 합계 5개 이하를 지킨다.
- **D-13:** 문구에도 단정 표현("원금 보장", "확정 수익", "무조건 절세")을 쓰지 않는다. 자동 점검은 3단계이지만, 2단계 생성 지침(스킬 프롬프트)에 금지 목록을 넣는다.

**게시일·파일 이름**
- **D-14:** 게시일은 기존 게시분(`2026/reels/*.mp4`, `specs/*.json`) 다음의 빈 날짜를 제안하고, 영문 슬러그를 자동 생성한다. 날짜·슬러그가 모호하거나 충돌하면 진행 전에 한 번 묻는다.
- **D-15:** 초안은 `2026/reels/drafts/<게시일>-<슬러그>/`에 쓴다(1단계 결정, git 제외). 정식 경로 이동은 3단계 승인 게이트 범위다.

**1단계에서 이어지는 결정**
- **D-16:** 새 원고는 `--layout new`로 렌더한다. legacy 배치는 기존 10편 재현용이다.
- **D-17:** 기존 원고 10편(`2026/reels/specs/*.json`)은 고치지 않는다. 새 선택 필드(시리즈·모션·수치 참조·구조화 근거)가 없으면 v1로 읽히고, golden 회귀 시험 결과가 바뀌지 않아야 한다. — **Reversibility:** costly — 게시된 기록이자 회귀 기준

### Claude's Discretion
- 수치 등록부 파일 위치·형식(JSON 권장, stdlib만 사용)과 원고가 수치를 참조하는 문법.
- 숫자 탐지 정규식과 예외 규칙(D-07), 카드 원고 → 릴스 골격 변환 규칙(DRAFT-02)의 세부.
- 원고 JSON 생성 자체는 Claude가 세션에서 하고(외부 API 없음), 프로그램은 검증·계산·파일 쓰기만 한다는 분담의 구체 구조.
- 게시글 문구 파일 형식(Markdown 또는 텍스트)과 이름.

### Deferred Ideas (OUT OF SCOPE)
- 고정 브랜드 해시태그 — 사용자가 정해 주면 설정값으로 추가(현재 미정).
- 훅 대안 2~3개, 기존 편과의 주제·수치 중복 경고 — v2 (DRAFT-V2-01, -02).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DRAFT-01 | 주제 한 줄 → 하우스 패턴 릴스 원고 JSON | 하우스 패턴 통계(§House pattern), 스킬/도구 분담(§Architecture), 구조 검증기 |
| DRAFT-02 | 카드 원고 → 릴스 골격, 원본에 없는 숫자 경고 | 카드→릴스 매핑 규칙 실측(§Card→Reel), 출처 숫자 대조 실험(8건 경고, 전부 진짜 신규 숫자) |
| DRAFT-03 | 수치 등록부 + 파생 수치 계산 | 등록부 스키마·시드(§Figure Registry), 계산·반올림 규칙 재현(§Derived figures) |
| DRAFT-04 | 게시글 문구 + 해시태그 5개 이하 | 형식·한도·고지 문구(§Caption) |
| DRAFT-05 | 시리즈·회차·다음 편 일관 반영 | `series` 선택 필드, 기존 관례 실측(§Series) |
| DRAFT-06 | v1 그대로 읽힘, 새 필드는 선택 | `load_spec` 확장 규칙(§v1 compatibility) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- 브랜드(색·폰트·레이아웃) 기존 10편과 동일, 컴플라이언스(단정 표현·세무/법률 단정·타사 비방 금지), 정확성(수치는 `basis`에 근거·기준, 최신 여부 확인, 추정은 추정 표시), 개인정보(고객 실명·사례 금지), 모든 산출물은 초안(사람 검수 후 게시), 비용(API 키·유료 서비스 없음), 기술 스택(기존 Python + Playwright + ffmpeg), 환경(외부 다운로드 제한, 사전 설치 Chromium).
- 새 pip 의존성 금지 관례(stdlib만). 오류는 한국어 메시지, 종료 코드 1(원고 오류)/2(환경 오류).
- GSD Workflow Enforcement: 파일 변경은 GSD 명령(`/gsd-execute-phase` 등)을 통해서만.
- 프로젝트 스킬: `.claude/skills/`에 agent-browser, design-taste-frontend, find-skills, mcp-builder (이 단계와 무관). 새 스킬은 같은 디렉터리에 `SKILL.md`로 추가.

## Summary

핵심 발견 세 가지. (1) **기존 원고 10편의 숫자 99개(+구조 숫자 24개)는 모두 정규식으로 분리되고**, 카드 원고와 대조하면 진짜로 "원본에 없는 숫자" 8개만 경고된다(0원, 25년, 4%, 72만/151만/329만, 8만 …). 거짓 경고는 범위 표기(`28~84세`)와 `만`/무단위 표기 두 가지뿐이고 처리법이 있다. (2) **파생 수치 전부(6.6만·38.5만·16.5만·13.2만, 2.7%, 2.3%, 3.0%, 0.1%, 14년, 7년, 124/207/388만, 72/151/329만, 7,712만, 2.2달, −30%, +36%)를 Decimal 계산으로 재현**했다. 반올림은 "소수 첫째 자리 또는 만 원 정수, 사사오입(ROUND_HALF_UP)"이며, 387.5→388 같은 동점이 있어 Python `round()`(은행가 반올림) 대신 `Decimal.quantize(ROUND_HALF_UP)`를 써야 한다. (3) **세법·통계 값의 1차 출처는 이 세션에서 전혀 열리지 않는다**(`curl`은 nts/law/moef/korea/nps/fss/kosis/assembly 전부 `connect_rejected`, WebFetch는 law.go.kr·toss.im 등 `ENOTFOUND`). 웹 검색 요약으로 확인된 것은 2차(뉴스·블로그) 일치뿐이므로 **등록부 시드는 전부 "미확인"**(D-02)이고, 팀장이 열어 볼 후보 출처 목록을 함께 남긴다.

세법 쪽 새 소식(2026-10-29 기준, 모두 2차 출처): 재정경제부가 2026-08-03 「2026년 세제개편안」을 발표했고, 청년(15~34세) IRP 세액공제율을 소득과 무관하게 15%로 올리는 안(2027-01-01 이후 납입분부터)과 연금계좌 추가한도에 ISA 전환금을 넣는 안이 들어 있으며 국회 심의 단계다(= **"발의" 상태**, D-04 대상). 연금계좌 한도(연금저축 600만, 합산 900만)와 15%/12%(총급여 5,500만·종합소득금액 4,500만) 기준은 현행 유지로 보도된다. 소득세 기본세율 구간 변경은 어떤 자료에서도 찾지 못했다 — 이는 **부재 증거**이므로 "변경 없음"으로 단정하지 않는다([ASSUMED]).

**Primary recommendation:** 등록부(`tools/data/figures.json`) + `calc` 모듈(Decimal, HALF_UP) + 숫자 검사기를 먼저 만들고, Claude는 `{{이름|서식}}` 자리표시자가 든 **원고 소스**를 쓰며, 프로그램이 이를 확장해 v1 호환 `spec.json`과 `figures` 장부를 쓴다. `spec.py`는 새 키를 "있을 때만" 검사하고 반환 dict는 건드리지 않는다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 원고 문장·훅·비유 작성, 게시글 훅/요약 3줄 | Claude (세션, 스킬 지침) | — | 창작·압축은 판단 영역, 외부 API 금지 |
| 수치 등록부 보관·스키마 검증 | 데이터 파일 + `figures.py` | — | 커밋되는 단일 근거, 원고가 id로 참조 |
| 파생 수치 계산·서식 | `calc.py` (Decimal) | — | D-05, 손 계산 금지 |
| 숫자 탐지·등록부 대조 (D-07) | `numscan.py` / `draft.py check` | — | 결정적 검사, 오류/확인필요 판정 |
| 카드→릴스 골격 | `convert.py` (결정적 부분) | Claude (압축) | 구조·출처 주석은 도구, 문장 압축은 Claude |
| 시리즈 top·예고 줄 삽입, 캡션 조립 | `draft.py expand/caption` | — | 한 곳(`series`)에서 파생 → 불일치 방지 (D-10) |
| 게시일·슬러그 제안, 충돌 검사 | `draft.py slot` | Claude(영문 슬러그 제안) | 날짜 스캔은 결정적, 모호하면 질문 |
| 원고 로딩·선택 필드 검증 | `spec.py` | — | v1 불변, DRAFT-06 |
| 렌더 검증 | 기존 `reel.py --layout new --strict` | — | 변경 없음 |

## Standard Stack

Stdlib만 사용 (`json`, `re`, `decimal`, `datetime`, `pathlib`, `argparse`, `unittest`). 새 외부 패키지 없음.

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python 3.13 | system | 모든 도구 | 기존 reelkit 관례 [VERIFIED: 이 세션 `python3` 실행] |
| `decimal.Decimal` (ROUND_HALF_UP) | stdlib | 파생 수치 계산 | float는 `6*1.1 = 6.6000000000000005` 로 오차, `round()`는 은행가 반올림 [VERIFIED: 이 세션 실행] |
| `unittest` | stdlib | 시험 | 기존 135개 시험 관례 (`tools/tests/`) |
| 기존 `reel.py --layout new --strict` | repo | 초안 원고 렌더 검증 | D-16 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON 등록부 | YAML/TOML | stdlib `tomllib`은 읽기만; JSON이 쓰기·diff·기존 관례(spec)와 일치 |
| 자리표시자 확장 | 원고에 숫자 직접 + 사후 대조 | D-05가 "손으로 적지 않음"을 요구 → 확장 방식 채택 |

**Installation:** 없음.

## Package Legitimacy Audit

외부 패키지를 설치하지 않으므로 해당 없음. (`gsd-tools package-legitimacy`는 실행하지 않음.)
**Packages removed due to [SLOP] verdict:** none · **Packages flagged [SUS]:** none

## Architecture Patterns

### Data flow

```
 사용자: 주제 한 줄 | 카드 spec
        │
        ▼
 [스킬 make-reel, Claude]──(1) draft.py slot ──► 날짜 제안 / 슬러그 충돌 → 모호하면 질문 (D-14)
        │                  (2) draft.py convert CARD ► skeleton + 출처 숫자 집합 (카드 입력 시)
        │                  (3) draft.py figures list ► 사용 가능한 id (없으면 STOP & ASK, D-06)
        ▼
 Claude 작성: spec.src.json  (자리표시자 {{name|fmt}}, inputs, derive, series, caption 소스)
        │
        ▼
 draft.py expand ──► spec.json (v1 호환 문자열 + 선택 필드 series/figures)   ◄── tools/data/figures.json
        │                 │  calc.py: Decimal 계산, 서식
        ▼                 ▼
 draft.py check ──► 오류(등록부 밖 숫자, 폐지/발의 미표기, 알 수 없는 마크업) → 종료 1
        │            └► 확인 필요 목록 (미확인 수치 장면·줄) → check.json   (3단계 입력)
        ▼
 draft.py caption ──► caption.txt (시리즈 첫 줄 · 요약 3줄 · 근거 · 고지 · CTA · 예고 · 해시태그≤5)
        ▼
 reel.py spec.json out.mp4 --layout new --strict   (기존, 변경 없음)
```

### Recommended Project Structure
```
tools/
├── draft.py                 # 얇은 CLI: slot|convert|figures|expand|check|caption
├── data/figures.json        # 수치 등록부 (커밋)
├── data/caption_config.json # {"brand_hashtags": [], "disclaimer": "...", "cta": "..."} (브랜드 태그는 사용자가 채움)
└── reelkit/
    ├── figures.py           # 등록부 로드·스키마 검증·상태 규칙
    ├── calc.py              # Decimal 계산 함수 + 서식(pct/man/man_won/eok_man/nyeon…)
    ├── numscan.py           # 숫자 탐지·분류 (구조/수치)
    ├── convert.py           # 카드 → 골격
    ├── caption.py           # 캡션 조립·해시태그 검사
    └── spec.py              # (기존) 선택 필드 검증 추가
.claude/skills/make-reel/    # SKILL.md + references/ (few-shot 3편, 금지 목록, 캡션 템플릿, 등록부 규칙)
tools/tests/                 # test_figures / test_calc_repro / test_numscan / test_convert / test_caption / test_spec(확장)
2026/reels/drafts/<날짜>-<슬러그>/   # spec.src.json, spec.json, caption.src.json, caption.txt, check.json (git 제외)
```

### Pattern 1: 자리표시자 확장 (D-05, D-07 동시 충족)
**What:** Claude는 숫자를 직접 적지 않고 `{{이름|서식}}`을 쓴다. 이름은 (a) 등록부 id, (b) `inputs`(이 릴스 한정 시나리오 가정), (c) `derive`(함수 호출 결과). `expand`가 문자열을 채우고 **어느 장면·줄의 어느 텍스트가 어떤 출처에서 왔는지**를 `figures` 장부에 쓴다. 렌더러는 완성된 평문 문자열만 본다.
**Example (소스 → 결과):**
```json
{
  "series": {"name": "연말정산 바로 알기"},
  "inputs": {"amt": {"value": "1000000", "unit": "원", "label": "100만 원 공제 예시"}},
  "derive": {
    "e_low":  {"fn": "pct_of", "args": ["inputs.amt", "fig.income_tax_rate_b1_local"]},
    "e_high": {"fn": "pct_of", "args": ["inputs.amt", "fig.income_tax_rate_b4_local"]}
  },
  "scenes": [{"top": "소득공제 {{inputs.amt|man_won}}",
              "lines": ["세율만큼 줄어요", "{{fig.income_tax_rate_b1_local|pct1}} → {{e_low|man}}"]}]
}
```
확장 결과 `"6.6% → 6.6만"` 은 기존 편과 글자 단위로 같다(§Derived figures 표).
**검사:** 최종 `spec.json`에서 각 줄의 장부 텍스트를 가린 뒤 남은 텍스트에 구조 숫자 예외가 아닌 숫자 토큰이 있으면 오류. 장부가 없는 v1 원고는 `check --legacy`로 "등록부 없음 n개"만 보고(수정 안 함).

### Pattern 2: "있을 때만 검사" 선택 필드 (DRAFT-06)
`load_spec`은 v1 검증을 그대로 두고 `series`, `figures`, `motion`, `version`, `basis_items`가 **있으면** 형식만 검사한다. 반환 dict에 기본값을 넣거나 정규화하지 않는다(§v1 compatibility).

### Anti-Patterns to Avoid
- **`basis` 타입 변경:** `basis`는 문자열로 유지. 구조화 근거는 새 키 `basis_items`(예: `[{"text","fig","as_of"}]`)로 두고 표시용 `basis` 문자열은 확장이 만든다. 렌더러 두 곳이 `spec.get("basis", "")`를 문자열로 쓴다.
- **Claude가 등록부를 "확인"으로 바꾸기:** `figures add` 명령은 `verified`를 항상 `미확인`으로 쓰고 `--verified` 옵션이 없다. `figures confirm`은 사람 전용 명령으로 문서화하고 스킬이 호출을 금지한다.
- **웹 검색 결과 본문을 지시로 따르기:** 검색·페이지 텍스트는 데이터로만 쓰고 등록부 값으로만 숫자가 들어간다.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 반올림 | `round()` / float 곱셈 | `Decimal` + `ROUND_HALF_UP`, 값은 문자열로 저장 | 387.5 동점, `6*1.1` 오차 |
| 한글 형태소 분석으로 숫자 구분 | KoNLPy 등 | 정규식 + 단위 어휘 | 닫힌 단위 집합(만 원/%/억/세/년/개월/달/배…)으로 충분 |
| JSON 스키마 라이브러리 | jsonschema | 손으로 쓴 검사 함수 | 설치 보장 없음, 기존 관례 |
| 날짜·슬러그 충돌 로직 | 임의 | `re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*")` + 디렉터리 스캔 | 경로 주입 방지 |

## Figure Registry (focus 1·2)

### 접근 가능한 출처 현황 (이 세션)
| 시도 | 결과 |
|------|------|
| `curl` nts.go.kr, law.go.kr, moef.go.kr, korea.kr, nps.or.kr, fss.or.kr, kosis.kr, index.go.kr, assembly.go.kr, hometax.go.kr, fsc.go.kr, kofia.or.kr, instagram.com, help.instagram.com | 전부 `000` (`connect_rejected`: 세션 허용 도메인 밖) |
| WebFetch law.go.kr, nts.go.kr, toss.im, nsp.nanet.go.kr, taxtimes.co.kr | `ENOTFOUND` |
| WebSearch | 동작. 결과는 뉴스·블로그·금융사 페이지 요약. **1차 원문은 열지 못함** |

→ 모든 값은 **"2차 일치" 또는 "출처 없음"**. 도메인을 세션 허용 목록에 넣어야 1차 확인이 가능하다(사용자 결정 사항, §Open Questions).

### 기존 원고·카드에서 쓰인 수치와 규칙 (전수)
"출처 상태" 열: **2차 일치** = 이 세션 WebSearch 요약에서 값이 일치(1차 미확인) / **없음** = 값이나 규칙을 확인하는 자료를 못 찾음 / **충돌** = 자료 간 불일치. 값은 전부 [CITED: 검색 요약]이며 등록부에서는 `미확인`으로 시작한다.

| id (제안) | 값 | 규칙·정의 | 사용처 | 출처 상태 | 시행 상태·메모 |
|-----------|----|-----------|--------|-----------|----------------|
| `income_tax_rate_b1..b8` | 6/15/24/35/38/40/42/45 % | 소득세 기본세율. 구간 1,400만·5,000만·8,800만·1.5억·3억·5억·10억 | 6.6%, 16.5%(카드), 38.5% | 6~42% 구간은 **2차 일치**(wikidocs 등 다수 일치). 45%(10억 초과)는 검색에서 못 봄 → [ASSUMED] | 시행. 1,400만/5,000만 상향은 2022년 개편안 → 2023 적용으로 보도 (2차). 2026-08-03 세제개편안에서 기본세율 구간 변경은 **못 찾음**(부재 증거 → 단정 금지) |
| `local_income_tax_ratio` | 10 % (소득세의 10%) | 개인지방소득세. 6→6.6, 15→16.5, 35→38.5, 12→13.2 의 근거 | 모든 "지방소득세 포함" 수치 | **2차 일치** ("지방소득세 10%가 얹혀서 16.5%, 13.2%") | 시행. 조문 번호(지방세법 제92조)는 [ASSUMED] |
| `pension_credit_rate_low` | 15 % (국세) → 16.5 % (지방 포함) | 연금계좌 세액공제율, 종합소득금액 4,500만 원 이하(근로소득만이면 총급여 5,500만 원 이하) | 16.5만 | **2차 일치** + 검색 결과가 인용한 국가법령정보센터 조문 요약("4천 500만원 … 5천 500만원 … 100분의 15") | 시행. 일부 블로그는 구기준 4,000만 원 표기 → **충돌**, 4,500만 원 쪽이 조문 요약과 일치 |
| `pension_credit_rate_high` | 12 % → 13.2 % | 위 기준 초과 | 13.2만 | **2차 일치** | 시행 |
| `pension_credit_wage_threshold` | 5,500만 원 (총급여) | 위 15%/12% 경계(근로소득자) | `5,500만 원 기준` | **2차 일치** | 시행 |
| `pension_credit_income_threshold` | 4,500만 원 (종합소득금액) | 위 경계(종합소득자) | 카드 note | **2차 일치** (조문 요약), 구기준 4,000만 충돌 | 시행 |
| `pension_credit_limit_savings` | 600만 원 | 연금저축 세액공제 대상 납입 한도 | (기존 편 미사용, 신규 연금 주제에서 필요) | **2차 일치** | 시행 |
| `pension_credit_limit_total` | 900만 원 | 연금저축+IRP 합산 한도 | 〃 | **2차 일치** (한도 700→900 상향 보도) | 시행. 2026 세제개편안도 900만 유지로 보도 |
| `pension_credit_young_gov_proposal` | 15 % (청년 15~34세, 소득 무관) | 2026년 세제개편안(정부안, 2026-08-03). 적용 2027-01-01 이후 납입분 | 신규 | **2차 일치** (복수 언론 요약), 시행시기는 일부 자료가 2026-01로 적어 **충돌** | **발의** (국회 심의 중, 통과 미확인). D-04: 확정 표현 금지 |
| `pension_credit_member_bill` | IRP 12→15 %, 청년 17 % | 의원 대표발의 소득세법 개정안 | 신규 | **2차 일치**(발의 사실만), 의안번호 **없음** | **발의**, 통과 여부 미확인 |
| `interest_income_tax_rate` | 15.4 % | 소득세 14% + 지방소득세 1.4%, 일반과세 이자 원천징수 | rate-secret-1, -2 | **2차 일치** | 시행. 조문 번호(소득세법 제129조)는 [ASSUMED]. 2026 고소득자 저율과세 축소 언급 자료 있음 → 확인 필요 |
| `nps_early_reduction_per_year` | 6 %/년 (최대 5년 30 %) | 조기노령연금 감액 | −30 % | **2차 일치** | 시행 |
| `nps_defer_increase_per_year` | 7.2 %/년 (최대 5년 36 %) | 연기연금 가산 | +36 % | **2차 일치** | 시행 |
| `nps_start_age_1969` | 만 65세 | 1969년생 이후 노령연금 수급 개시 | 만 65세 | **2차 일치** (공단 설명 인용) | 시행. 2025 국민연금 개혁(보험료율 등)은 [ASSUMED], 수급개시연령과 무관 |
| `nps_avg_old_age_all` | 69.6~69.8 만 원 (월) | 노령연금 수급자 평균, 2026-01 | "전체 70만 원" | 자료 간 소수 차이 → **충돌(소수점)**, 70만으로 반올림하면 일치 | 통계. 정확값은 공단 통계 확인 필요 |
| `nps_avg_old_age_20y` | 116.67 만 원 (136만 8,813명, 2026-01) | 20년 이상 가입자 월평균 | "117만 원" | **2차 일치** | 통계 |
| `retire_age_main_job` | 53.0 세 | 가장 오래 다닌 일자리 퇴직 평균 연령, 2026-05 경제활동인구조사 고령층 부가조사(2026-08-05 발표) | 53세, 12년(=65−53) | **2차 일치** (복수 언론) | 통계. 카드의 "남자 55.3 · 여자 51.1"은 **없음** |
| `pension_avg_55_79` | 88 만 원 (월) | 같은 조사, 55~79세 연금 수령자 | "88만 원" | **2차 일치** | 통계 |
| `life_expectancy_2024` | 83.7 년 (남 80.8 · 여 86.6) | 2024 생명표, 국가데이터처 2025-12-03 발표 | "83.7세" | **2차 일치** (복수 언론) | 통계 |
| `female_60_remaining` | "약 88세까지" | 60세 여성 기대여명 | salary-1 | **없음** (검색에서 못 찾음) | 신규 사용 전 확인 필요 |
| `cpi_yoy_2026_09` | 2.9 % | 2026년 9월 소비자물가 전년동월비, 국가데이터처 2026-10-02 | rate-secret-2 basis | **2차 일치** | 통계. 2026-12에 기준연도 개편 예정으로 수치가 달라질 수 있음 (2차) |
| `sp500_2008_return` | −37 % | S&P500 2008 연간 (총수익 기준 −37.0%, SPY 기준 −36.8%로 소스마다 소수 차이) | rate-secret-3 | 2차 일치, 지수·총수익 정의 **충돌(소수)** | 시장 통계. 가격지수 −38.5%는 [ASSUMED] |
| `sp500_long_run_avg` | 약 10 %/년 | 1926~ 총수익 산술평균 10.12% (복리는 더 낮음) | rate-secret-3 | **2차 일치** (Motley Fool, FT Portfolios 인용) | 시장 통계, "과거 평균·미래 보장 아님" 고지 필요 |
| `rule_of_72` | 72 | 배가 시간 ≈ 72 ÷ 수익률(%) | rate-secret-3 | 수학 관례 (`kind: constant`) | 출처 확인 불필요 취급 가능, 사람 확인 한 번 |

**시나리오 가정(등록부 아님, 릴스별 `inputs`):** 100만 원 공제 예시, 예금 3.6%/3%, 적금 5%, 채권 5%, 4% 수익률, 월급 400만 원(통장 60·150·30·160), 목표 3억 7,200만 원, 28/38/45세 시작, 새는 돈 항목(3·3·1·8만). 각 `inputs`는 `label`에 "예시/가정/가상" 중 하나를 요구해 COMP-02(예시 표기 누락)의 입력이 되게 한다.

**기존 편에서 발견한 불일치 (등록부 설계에 반영):** salary-1 "월급 없는 30년" = 83.7−53 = 30.7 인데 30으로 표기(내림 또는 "30년 넘게"의 축약). 신규 파생은 반올림 규칙 일관 적용, 이 경우 "30년 넘게"처럼 서식을 별도로 둔다.

### 등록부 스키마 (D-01 필드 그대로)
```json
{
  "schema": 1,
  "figures": {
    "pension_credit_rate_low": {
      "label": "연금계좌 세액공제율(총급여 5,500만 원 이하·종합소득금액 4,500만 원 이하)",
      "kind": "law",                          // law | stat | market | constant
      "value": "15", "unit": "%",             // 값은 문자열(Decimal)
      "includes_local": false,                // true면 지방소득세 포함 값
      "source": {"name": "소득세법 제59조의3 제1항", "url": null, "locator": "후보: 국가법령정보센터"},
      "candidate_sources": ["https://www.law.go.kr (소득세법)", "국세청 연말정산 안내"],
      "as_of": "2026-01-01",                  // 기준일
      "valid_until": null,                    // 이 날짜 이후 게시면 재확인 경고
      "found_on": "2026-10-29",               // Claude가 검색으로 발견한 날
      "checked_on": null,                     // 확인일 (사람)
      "checked_by": null,                     // 확인자 (사람)
      "legal_status": "시행",                 // 시행 | 발의 | 폐지   (D-01 어휘 그대로)
      "verified": "미확인",                   // 미확인 | 확인
      "notes": "구기준 4,000만 원 표기 블로그 있음"
    }
  }
}
```
검증 규칙(`figures.py`): enum 두 개 정확 일치; `verified=="확인"`이면 `checked_on`·`checked_by` 필수이며 `checked_by`가 비어 있거나 "Claude"면 오류; `legal_status=="발의"`면 `source.name`에 "발의|개정안|정부안" 포함 요구; `value`는 `Decimal(str)` 파싱 가능; id는 `^[a-z0-9_]+$`. 원고가 id를 참조하므로 **필드 이름은 지금 확정**한다(costly).

### 사용 규칙 (D-03, D-04)
- `verified=="미확인"` → 해당 줄을 `check.json`의 `needs_check`에 (장면, 줄, id, 텍스트)로 기록, 렌더·출력은 막지 않음.
- `legal_status=="발의"` → 해당 줄 또는 `basis`에 정규식 `발의|개정안|정부안|시행 전` 이 없으면 **오류**. `폐지` → 사용 시 오류.
- `valid_until`이 게시일보다 이르면 경고(2027-01-01 이후 납입분 같은 시행일은 `as_of`/`valid_until`로 관리).

## Number detection (focus 3)

기존 10편의 `top`/`lines`/`basis` 전체에 적용한 실험(스크립트는 세션 스크래치패드): 숫자 토큰 **99 수치 + 12 원문자 + 7 구성 숫자 + 5 날짜**, 구조 오분류 0.

**규칙 (순서대로):**
1. 태그 `</?[gs]>`·`<br>` 제거 후 스캔.
2. **상수 문구 가림:** `1분 노후자금 계산기`, `S&P500`, `4대보험`, `72의 법칙`.
3. **구조(예외):** 원문자 `[①-⑳]` (회차·목록 ①②); 단위가 `가지|개|권|편|쪽|장|층|단계|대`인 구성 숫자(3권, 4개로, 1층); 날짜 — 4자리 연도(`(19|20)\d\d년`) 및 `\d{2}년 \d{1,2}월`, 단독 `N월`.
4. **그 외 모두 수치:** 단위 `만 원|억 원|만|억|원|%|세|년|개월|달|배|…` 또는 무단위. 부호 `[+\-−]`(U+2212 포함). 천 단위 쉼표 `\d{1,3}(,\d{3})+`. 복합 `3억 7,200만 원`은 한 토큰(= 372,000,000원). 범위 `55~79세`·`28~84세`는 전개 후 각각 토큰.
5. **정규화 키 = (종류, 값):** 만 원 계열은 원 단위 Decimal(6.6만 = 66,000원), `%`, 나이, 연, 개월을 종류로 구분(5% ≠ 5년). 무단위 숫자는 같은 값 또는 ×10⁴ 값의 금액과 매칭 허용(`60 · 150 · 30 · 160` ↔ 카드 `60만`).
6. `1969년생`처럼 `년생`은 4자리여도 **수치**(규칙 매개변수). 기준일 연도는 예외이나 `basis`의 `YYYY년` 기준일은 등록부 `as_of`와 대조하는 별도 경고로.

**알려진 한계:** (a) 정규식만으로 "등록부 사실 / 시나리오 가정 / 파생"을 구분하지 못한다 — 구분은 자리표시자 장부가 한다. (b) `약`, `이상` 같은 한정어는 숫자 밖. (c) 영문 약어 속 숫자(S&P500)는 상수 가림 목록 관리 필요.

**DRAFT-02 출처 대조 실험 (카드 7쌍 ↔ 릴스 7편):** 릴스 숫자 67개 중 카드에 없는 것 8개 — `0원`, `25년`(=53−28), `4%`, `72만/151만/329만`(연 4% 월복리 역산), `8만`(=6+2) — **전부 진짜 신규/파생 숫자**(참 양성). 거짓 양성 2종은 처리 완료: `28~84세` 범위 표기(→ 범위 전개), `60 · 150 · 30 · 160` 무단위 vs 카드 `만`(→ 규칙 5). 거짓 음성 후보: 4자리 연도를 날짜로 통과시키는 규칙 3 — 수치 의미 연도는 `년생`/`기준`으로 따로 잡는다(규칙 6).

## Derived figures (focus 4)

모든 값은 이 세션에서 Decimal/float로 직접 계산해 기존 원고와 대조했다. 가정: 월말 납입(보통연금), 4% 시나리오는 월복리 `r=0.04/12`.

| 기존 표기 | 계산 | 정확값 | 규칙 |
|-----------|------|--------|------|
| 6.6만 / 16.5만 / 38.5만 / 13.2만 | 100만 × (6, 15, 35, 12)% × 1.1 | 6.6 / 16.5 / 38.5 / 13.2 (정확) | 반올림 불필요, 지방소득세는 `×1.1` Decimal |
| 세전 약 2.7% | 월 100만, 연 5% 단리, 12개월: 100만×0.05/12×(12+…+1=78)=325,000 / 1,200만 | 2.7083 | % 소수 1자리, "약" |
| 세후 약 2.3% | 325,000×(1−0.154)=274,950 / 1,200만 | 2.29125 | 〃 |
| 약 3.0% / 약 0.1% | 3.6×(1−0.154)=3.0456 ; 3.0456−2.9=0.1456 | | 반올림은 **마지막에 한 번**(중간 반올림 금지) |
| 24년 / 약 14년 / 약 7년 | 72÷3, 72÷5, 72÷10 | 24 / 14.4 / 7.2 | 정수 반올림, 정확하지 않으면 "약" |
| 충전 300 / 사용 672개월 / 2.2달 | (53−28)×12, (84−28)×12, 672÷300 | 300 / 672 / 2.24 | 소수 1자리 |
| 월 124 / 207 / 388만 (수익률 0) | 3억 7,200만 ÷ 300 / 180 / 96개월 | 124 / 206.67 / **387.5** | 만 원 정수, **동점 → 올림(HALF_UP)** |
| 72 / 151 / 329만 (연 4%) | 연금 역산 `FV·r/((1+r)^n−1)` | 72.36 / 151.16 / 329.44 | 만 원 정수 |
| 4,500만 / 약 7,712만 | 15만×300 / `15만·((1+r)^300−1)/r` | 4,500 / 7,711.94 | 만 원 정수 |
| −30% / +36% | 6%×5 / 7.2%×5 | | 부호는 U+2212 `−` 와 `+` |
| 117만 / 70만 | 116.67 / 69.6~69.8 | | 만 원 정수 |

**서식 함수(기존 표기에서 역산):** `pct1`("2.7%", "3.0%" — 소수 1자리 유지), `man`("6.6만", "124만", "7,712만": 정수면 소수 생략·쉼표), `man_won`("88만 원"), `eok_man`("3억 7,200만 원"), `nyeon`("24년"), `dal`("2.2달"), `signed_pct`("−30%", "+36%"). 자리 수와 "약" 접두어 규칙: 값이 표시값과 다르면 `약` 자동 제안(기존 편은 비일관: `207만`·`388만`에는 약 없음) → **경고**로만 처리.

**재현 시험(D-05):** 위 표의 모든 행을 `test_calc_repro.py`에 (기대 문자열, 계산 호출) 쌍으로 고정. 최소 요구: tax-deduction 4개 값. 나머지는 계산 모듈의 일반성을 확인하므로 같은 시험 파일에 둔다.

## Card spec → reel skeleton (focus 5, DRAFT-02)

비교 대상: `2026/02-tax-deduction/spec.json`(카드 6장) ↔ `2026-10-26-tax-deduction.json`(7장면), `03~07-salary-two-owners-*` ↔ 각 릴스. 실제 사용된 규칙:

| # | 규칙 (관찰) | 도구가 할 일 | Claude가 할 일 |
|---|-------------|--------------|----------------|
| M1 | 장면 1 `top` = 카드 `series` (회차 있으면 `N편` → 원문자: "내 월급의 두 주인 1편" → "내 월급의 두 주인 ①"; 회차 없으면 시리즈명 그대로) | 자동 생성 | — |
| M2 | 장면 1 `lines` = 카드 1의 제목(`<br>`→공백)을 압축 + 질문형 훅 한 줄(`<g>`). 카드 본문은 안 씀 | 제목 평문화 | 훅 작성 |
| M3 | 카드 1~4(본문) → 장면 2~4: 카드 `emph` → `<g>`, 카드의 긴 문장 → 짧은 조각(≤ 약 20자, 최대 실측 22자), 표의 `원` 생략(`6.6% → 6.6만`), 구간 표 3행 → 양 끝 2행(16.5% 행 생략) | 골격 + `src` 카드 번호 주석 | 압축 |
| M4 | 카드 `note` → ① 장면 `<s>` 줄(`<s>2026년 고령층 부가조사</s>`) ② `basis`로 합침(`"100만 원 공제 예시 · 지방소득세 포함"` = 카드1 숫자 + 카드3 note) ③ 일부는 버려짐(`종합소득자는 4,500만 원 기준`) | note 후보 목록 + **버려진 note 목록** | 선택 |
| M5 | 카드 중 주제 이탈 카드는 통째로 생략(tax-deduction 카드 5 "직장인은 빼기 사장님은 더하기") | 생략 사실을 보고 | 판단 |
| M6 | "주의" 장면은 카드에 없고 새로 만든다: `단, 꼭 알아둘 것` + 한계 조건(`0원`) + `<s>세무 판단은 세무사 확인</s>` (원천: 카드 5 note "일반 정보 · 세무 판단은 세무사 확인") | note에서 고지 문구 후보 | 작성 |
| M7 | 마지막 카드(dark) 결론 → 결론 장면(장면 5) + **고정 CTA 장면 추가**: `저장해두고 / 내 ○○ / ○○해 보세요 / <s>프로필 링크 · 1분 노후자금 계산기</s>` (카드에는 없는 프로필 줄) | CTA 템플릿 자동 삽입 | 가운데 두 줄 문구 |
| M8 | 카드 마지막 줄 "다음 편: X" → 릴스에서는 **CTA 직전(장면 6) `<s>다음 편: X</s>`** 줄. (6편 모두 6/7번째 장면) | — | D-09와 위치 상이, 아래 참고 |
| M9 | 카드 수 6 → 장면 7. 줄 수 분포 2~4줄, 마지막 CTA는 항상 4줄 | 구조 검사 | — |

**숫자 대조(카드 ↔ 릴스)는 M3의 압축에서 새 숫자가 생기는 곳을 정확히 짚는다**(위 8건). 자유 압축이 아니라 계산으로 만든 파생 숫자는 `derive`로 이동시키면 경고가 사라진다.

**D-09와 관례의 차이 (실측):** 기존 6편은 `다음 편: …`을 **CTA 앞 장면**에 `<s>` 줄로 둔다. D-09는 **마지막(CTA) 장면**에 두라고 한다(잠금). 실험: `salary-two-owners-2`의 CTA 장면(이미 4줄)에 `<s>다음 편: …</s>`를 5번째 줄로 추가하고 `reel.py --layout new`로 렌더 → **레이아웃 경고 없음**, 길이 25.2초 → 26.1초(줄당 0.85초 증가). 따라서 D-09 그대로 가능. 줄 순서는 `프로필 링크` 줄 위/아래 중 플래너 결정(권장: 프로필 링크 줄 뒤가 아니라 앞 — CTA 마지막 줄을 고정 문구로 유지).

### 하우스 패턴 수치 (DRAFT-01 검증기용, 실측)
7장면 10편 모두. 장면당 줄 수 2~4(마지막 4), 최대 한 줄 길이 20~22자(태그 제외), `top` 최대 21자, `basis` 16~28자, 장면당 시간 = `0.85×(줄 수−1)+1.9`초 → 총 21.8~26.05초. `<g>` 강조 줄 5~8개/편. 검증기 기본값 제안: 장면 6~8, 길이 21~27초(경고), 줄 길이 >22자 경고, 마지막 장면 `top==""` + `프로필 링크` 줄 존재, 주의 장면 또는 `<s>`에 세무사 확인 문구(세무 키워드가 있을 때, 3단계 COMP-02와 중복되지 않게 구조 검사로만).
[VERIFIED: `tools/reelkit/constants.py:11-12`] `LINE = 0.85   # 한 줄이 나타나는 간격(초)` / `HOLD = 1.9    # 장면 마지막 줄 이후 멈춤(초)`

## Series, 날짜·슬러그 (focus 5 보충, DRAFT-05, D-08~D-10, D-14)

- 기존 관례(실측): 첫 장면 `top` = `시리즈명 ①~⑤` (금리의 비밀 ①②③, 내 월급의 두 주인 ①~⑤). 단발 시리즈(연말정산 바로 알기, 전자책 이벤트)는 회차 없음. 원문자는 ①~⑤만 실사용 검증됨; ⑪ 이상 글리프 지원은 확인 못 함 → `episode` 1~10 제한 권장([ASSUMED]).
- 제안 필드: `"series": {"name": "내 월급의 두 주인", "episode": 6, "next": "2층 퇴직연금"}` (`episode`, `next` 선택). `expand`가 `scenes[0].top = f"{name} {원문자}"`를 쓰고, `next`가 있으면 마지막 장면 끝에 `<s>다음 편: {next}</s>`를 추가한다. 캡션은 같은 객체에서만 읽는다(D-10). 사용자가 `top`에 이미 다른 문구를 써 두었으면 오류(덮어쓰지 않음).
- 날짜: 기존 게시분 최대 날짜는 **2026-11-07**(mp4·specs 모두), 간격은 1~3일(주로 2일). "다음 빈 날짜"는 최대일+1 = 2026-11-08이 기본 제안, 간격 관례상 11-09도 후보이므로 **제안 + 확인 질문 1회**(D-14). `drafts/`에 이미 같은 날짜나 슬러그가 있으면 질문. 슬러그는 Claude가 영문 소문자-하이픈으로 제안하고 도구가 `^[a-z0-9]+(-[a-z0-9]+)*$`와 충돌을 검사.
- `2026/reels/drafts/`는 현재 없음(.gitignore 대상) → 도구가 생성.

## Caption (focus 7, DRAFT-04)

**한도 [CITED: WebSearch 요약, 서드파티 다수]**: 캡션 최대 2,200자(릴스 포함, 해시태그 포함), 피드에서 처음 약 125자 후 "더 보기", 릴스 탭에서는 더 짧게(약 55~60자라는 출처 1개 — LOW). 해시태그는 게시물당 30개가 공식 한도로 알려져 있으나, **2025-12에 5개로 줄었다는 보도가 일부 있고 Instagram/Meta 1차 출처는 확인 못 함**(Circleboom은 30개 유지 주장) → 충돌, [ASSUMED]. D-12(최대 5개)는 어느 쪽이든 만족한다. 따라서 검사 규칙: 해시태그 ≤5, 전체 ≤2,200자, 첫 줄 ≤ 55자 권장(경고).

**조립 템플릿 (D-10, D-11):**
```
{series.name} {원문자} | {hook}                  ← 첫 줄: 시리즈·회차 + 훅 (한 줄로 묶어 더 보기 전에 노출)

• 핵심 요약 1
• 핵심 요약 2
• 핵심 요약 3

근거 · 기준: {basis} ({as_of 연월} 기준)         ← 도구가 basis/figures에서 조립
※ 일반적인 정보 제공이며 개인 상황에 따라 다를 수 있습니다. 세무 판단은 세무사 확인이 필요합니다. 특정 상품 권유가 아닙니다.

저장해두고 프로필 링크 · 1분 노후자금 계산기에서 계산해 보세요
다음 편: {series.next}                          ← 있을 때만, 같은 값

#태그1 #태그2 #태그3
```
- 고정 문구(고지·CTA)는 `tools/data/caption_config.json`에 두고 **"초안 문구, 준법 검토 전"** 으로 표시한다. 필수 고지 문구·위치는 오너 게이트(Phase 3 전)라 아직 확정되지 않았다 → 이 문구는 [ASSUMED]이며 단정 표현("보장", "확정", "무조건", "반드시")을 쓰지 않는 취지만 잠근다.
- 미확인 수치가 있어도 캡션 본문에는 "확인 필요"를 넣지 않는다(게시 문구가 아님). `check.json`에 별도로 남긴다.
- 해시태그: `#[0-9A-Za-z_가-힣]+`, 중복 금지, 공백·특수문자 금지, `brand_hashtags`(기본 `[]`) + 주제 태그 합 ≤5. 주제 태그는 Claude가 생성(2~4개 권장, D-12는 3~5개), 도구는 개수·형식·금지어(스킬의 금지 목록 파일)만 검사.
- 파일: `caption.txt`(인스타에 그대로 붙여넣는 평문) + `caption.src.json`(Claude 작성 소스: `hook`, `summary[3]`, `hashtags[]`). Markdown이 아닌 평문 권장.

## v1 compatibility (focus 6, DRAFT-06)

**현재 동작 (읽은 코드):**
- [VERIFIED: tools/reelkit/spec.py:44-45] `if "basis" in spec and not isinstance(spec["basis"], str):` → `raise SpecError("basis: 문자열이어야 함")` — `basis`를 객체로 바꾸면 v1 로더가 거부한다. 필수 검사는 `scenes`(비어 있지 않은 목록), 각 장면 `top`(문자열, 빈 문자열 허용), `lines`(비어 있지 않은 문자열 목록)뿐이고 **알 수 없는 최상위 키는 무시**한다.
- [VERIFIED: tools/tests/test_spec.py CommittedSpecs] `got = load_spec(f)` 후 `self.assertEqual(got, expected)` — 열 편의 로드 결과가 원본 JSON과 **같아야** 하므로 로더가 기본값을 채우거나 정규화하면 시험이 깨진다.
- [VERIFIED: tools/reelkit/render.py:97,155] `basis = spec.get("basis", "")` 문자열로 사용. `timeline.py`·`golden.py`는 `spec["scenes"]`만 읽는다 → 골든 비교는 `scenes` 변경 없이 영향받지 않는다.
- `legacy` 배치만 `check_legacy_markup`을 호출한다([VERIFIED: tools/reelkit/render.py `render_reel()` — `if layout == "legacy": check_legacy_markup(spec)`]). `new` 배치는 `markup_new`가 전부 이스케이프하고 `<g>`,`</g>`,`<s>`,`</s>`만 되살린다 → 새 원고에서 `<br>` 등을 쓰면 **글자 그대로 화면에 찍힌다**. 초안 검사기가 허용 4태그를 새 배치용으로도 검사해야 한다.

**확장 규칙:**
1. `load_spec`: v1 검사는 그대로, 새 키는 **존재할 때만** 형식 검사 (`series`: dict, `name` 비어 있지 않은 문자열, `episode` int 1..10, `next` 문자열 / `figures`: 항목 dict 목록 / `basis_items`: 목록 / `motion`: 값 형식만 받아들이고 의미는 4단계에서 정의 / `version`: int, 알 수 없는 큰 값은 오류). 오류 메시지는 기존처럼 한국어 + 필드 경로.
2. 반환 dict는 입력 그대로. 정규화가 필요하면 별도 함수(`view(spec)`)로 복사본을 반환.
3. 자리표시자 `{{`가 남은 원고는 렌더 거부(종료 코드 1, "확장 전 소스"). 기존 10편에 `{{`는 없음 [VERIFIED: grep 결과 없음].
4. 시험: (a) 기존 `CommittedSpecs` 그대로 통과, (b) 모든 선택 필드를 가진 샘플이 로드되고 `scenes`가 동일, (c) 선택 필드를 지운 사본과 지우기 전 사본의 렌더 길이·장면 경계·`cover_ms` 동일(`--layout new`), (d) 잘못된 `series.episode` 등 부정 시험, (e) 단계 종료 전 `python3 tools/golden.py` 1회(3~4분) 통과.

## Skill vs Python split (focus 8)

| 하는 일 | Claude(스킬) | Python(도구) |
|---------|--------------|--------------|
| 주제 이해, 장면 구성, 훅·비유·결론·CTA 문구 | ✓ | |
| 카드 압축, 질문형 훅 | ✓ | 골격·출처 주석·버려진 note 목록 |
| 숫자 선택 | 등록부 id/`inputs`/`derive`만 사용. 없으면 **멈추고 질문**(D-06) | `figures list/show`, 오류 메시지에 후보 id 제안 |
| 숫자 계산·서식 | ✗ (손 계산 금지) | `calc.py` |
| 등록부 항목 추가 | 사용자 승인 후 `figures add`(항상 미확인) | 스키마·상태 검증 |
| 등록부 "확인" 전환 | ✗ 금지 | 사람이 `figures confirm`(확인자·확인일 필수) |
| 시리즈 top / 예고 줄 | 값만 지정 | 삽입·불일치 오류 |
| 단정 표현 회피(D-13) | 스킬 지침의 금지 목록(원금 보장, 확정 수익, 무조건 절세, 반드시 오른다/받는다 등) 준수 | (자동 점검은 3단계) |
| 검증·렌더 | 실행·결과 읽기, 최대 2회 수정 | `check`, `reel.py --layout new --strict` |

스킬 `.claude/skills/make-reel/SKILL.md`는 **워크플로만** 담고(slot → figures → 소스 작성 → expand → check → caption → render), 규칙·서식·금지어는 `references/`와 `tools/data/`에 둔다(로직을 SKILL.md에 넣지 않음, ARCHITECTURE 안티패턴 1). 3단계가 같은 스킬을 번들 생성으로 확장한다.

## Common Pitfalls

### Pitfall 1: 동점 반올림 (387.5)
**What goes wrong:** `round(387.5)`는 우연히 388이지만 `round(386.5)`는 386. 다른 값에서 기존 편과 한 글자 어긋남.
**How to avoid:** `Decimal` + `ROUND_HALF_UP`, 값은 문자열로 저장하고 중간 반올림 금지.

### Pitfall 2: 지방소득세 포함 여부 혼동
16.5/13.2/6.6/38.5는 모두 지방 포함(×1.1). 등록부에 `includes_local`을 두고 `basis`에 "지방소득세 포함"이 없으면 경고.

### Pitfall 3: 기준 금액 구기준 혼입
종합소득금액 기준이 블로그마다 4,000만/4,500만으로 갈린다. 조문 요약은 4,500만. 사람이 1차 확인하기 전까지 `미확인`+`notes`에 충돌 기록.

### Pitfall 4: 발의안의 확정 표현
청년 IRP 15%는 정부안이며 국회 심의 중. "15%로 올라갑니다"는 오류. 캡션·원고 모두 "발의안/정부안 … 심의 중" 표기 필요(D-04 규칙이 같은 줄/basis 검사).

### Pitfall 5: 카드 `note` 소실
tax-deduction 변환에서 "종합소득자는 4,500만 원 기준"이 사라졌다. 도구는 버려진 note를 목록으로 보고해야 한다(주의 문구 누락 방지).

### Pitfall 6: 새 배치에서 `<br>`
`markup_new`는 모든 태그를 이스케이프 → `<br>`이 화면에 글자로 나온다. 카드 `title`의 `<br>`는 변환 시 공백/줄 분리로 처리.

### Pitfall 7: 날짜가 미래
기존 게시일이 2026-11-07까지이고 오늘이 2026-10-29이므로 "게시일"은 예약 일자다. 가장 늦은 날짜+1을 기본 제안하되 확인 질문 1회.

### Pitfall 8: 검색 결과를 사실로 확정
검색 요약은 2차이며 서로 충돌(소수점, 시행 시기)한다. 등록부는 항상 `미확인`, `notes`에 충돌 내용 기록.

## Code Examples

### 반올림·서식 (스케치, 기대값 표 기준으로 구현)
```python
# Source: 이 세션 실행으로 기존 편 값과 대조 (stdlib decimal)
from decimal import Decimal as D, ROUND_HALF_UP
def q(x, places="0.1"):                 # 사사오입 (동점은 올림)
    return x.quantize(D(places), rounding=ROUND_HALF_UP)
def with_local(rate_pct):               # 15 -> 16.5 (float 금지: 6*1.1 = 6.6000000000000005)
    return rate_pct * D("1.1")
assert with_local(D("15")) == D("16.5")
assert q(D("387.5"), "1") == D("388")   # round(387.5) 는 우연히 같지만 round(386.5) 는 386
```
`man`/`pct1` 같은 서식 함수의 소수 처리(정수면 소수 생략, 100 미만은 소수 1자리, 쉼표)는 `test_calc_repro`의 기대 문자열 표를 먼저 쓰고 그에 맞춰 구현한다.

### 연금(월복리) 역산·미래가치 (표의 72/151/329, 7,712 재현)
```python
def annuity_pmt(target, annual_rate, months):   # annual_rate=Decimal("0.04")
    r = annual_rate / 12
    return target * r / ((1 + r) ** months - 1)
def fv_monthly(pmt, annual_rate, months):
    r = annual_rate / 12
    return pmt * (((1 + r) ** months - 1) / r)
```
(Decimal 거듭제곱은 정수 지수에서 정확. 이 세션에서는 float로 검산: 72.355→72, 151.164→151, 329.441→329, 7711.94→7,712.)

## State of the Art

| Old | Current | When | Impact |
|-----|---------|------|--------|
| 부처명 기획재정부 | 재정경제부 (2026 세제개편안 발표 주체로 보도) | 2026 | 출처 이름 표기 시 확인 필요 [CITED: 검색 요약] |
| 통계청 | 국가데이터처 | 2026 보도 기준 | 기존 편 basis도 "국가데이터처" 사용 |
| 연금계좌 한도 700만 | 합산 900만 (연금저축 600만) | 2023 개정 | 현행 유지 보도 |
| 해시태그 30개 | 5개로 줄었다는 보도(미확인) | 2025-12 보도 | D-12(≤5)는 어느 쪽이든 안전 |

**Deprecated:** 소득세 기본세율 구구간(1,200만/4,600만)은 구기준 — 블로그에 남아 있음.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 소득세 기본세율 45%(10억 초과)·구간 경계, 2026-08-03 세제개편안에서 기본세율 구간 변경 없음 | Figure Registry | 신규 편 세율 틀림 → 사람 1차 확인 필수 |
| A2 | 조문 번호: 소득세법 제55조(세율), 제129조(원천징수), 지방세법 제92조 | Figure Registry | 출처 표기 오류 (제59조의3만 검색으로 확인) |
| A3 | `episode` ⑪ 이상 원문자 글리프가 번들 폰트에 있다 → 1~10 제한 | Series | 10편 초과 시리즈에서 두부(□) |
| A4 | Instagram 해시태그 한도 30개/5개 어느 쪽이 현행인지 | Caption | D-12가 이미 ≤5라 영향 없음 |
| A5 | 릴스 탭 캡션 노출 55~60자(출처 1개) | Caption | 첫 줄 길이 권장치가 달라질 수 있음 |
| A6 | 고지·CTA 고정 문구는 준법 검토 전 초안 | Caption | Phase 3 오너 게이트에서 문구·위치 변경 |
| A7 | S&P500 2008 가격지수 −38.5%, 국민연금 개혁(2025)이 수급개시연령에 영향 없음 | Registry | 신규 사용 시 재확인 |
| A8 | 2026-12 CPI 기준연도 개편 예정 → 9월 2.9% 수치가 재계산될 수 있음 (2차) | Registry | 기존 편 basis의 "26년 9월" 값 유효성 |

## Open Questions

1. **1차 출처 도메인 허용 여부**
   - 알고 있는 것: law.go.kr·nts.go.kr·nps.or.kr·kosis.kr 등 전부 이 세션에서 막힘. 검색 요약은 2차뿐.
   - 불명확: 사용자가 세션 네트워크 허용 목록에 도메인을 추가할지, 팀장이 밖에서 확인할지.
   - 권고: 시드는 전부 `미확인`으로 두고 팀장 확인용 체크리스트(후보 출처 + 확인할 조문)를 `tools/data/figures.json`의 `candidate_sources`에 담는다. 허용되면 같은 파일에 기준일만 갱신.
2. **정부안(세제개편안)을 `legal_status`에서 어떻게 표시할지** — D-01 어휘는 시행/발의/폐지 3개. 권고: 정부안·의원안 모두 `발의`로 두고 `source.name`에 구분을 적는다(스키마 확장 없음).
3. **게시일 기본값: 최대일+1(11-08) vs 관례 간격(11-09)** — 권고: 11-08 제안, 항상 질문 1회.
4. **`다음 편`을 D-09대로 CTA 장면에 둘지, 관례(CTA 직전 장면)를 따를지** — D-09 잠금이므로 CTA 장면(실험상 경고 없음). 변경하려면 사용자 확인.
5. **고정 브랜드 해시태그** — 현재 미정(deferred). `brand_hashtags: []`로 두고 합계 ≤5 검사만 구현.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 모든 도구 | ✓ | 3.13 | — |
| Playwright + Chromium + ffmpeg | `reel.py` 렌더 검증 | ✓ (`--layout new` 렌더 2회 성공, 14.5s) | 고정 1.63.0 계열 | doctor가 폴백 안내 |
| 1차 세법·통계 사이트 | 등록부 확인 | ✗ (connect_rejected / ENOTFOUND) | — | 팀장이 외부에서 확인 (D-02) |
| WebSearch | 2차 확인·시드 후보 | ✓ | — | — |

**Missing with no fallback:** 없음 (1차 확인은 설계상 사람 단계).

## Validation Architecture

`workflow.nyquist_validation: false` 이므로 최소 요약만. 프레임워크: stdlib `unittest`(`python3 -m unittest discover -s tools/tests`), 빠른 실행은 파일 단위 `-p 'test_xxx.py'`.

| Req | 시험 | 파일 |
|-----|------|------|
| DRAFT-03 | 등록부 스키마·상태 규칙(발의 미표기 오류, 폐지 사용 오류, 확인 필수 필드) | `test_figures.py` (신규) |
| DRAFT-03/D-05 | 위 파생 표의 모든 행 문자열 일치 | `test_calc_repro.py` (신규) |
| D-07 | 기존 10편 숫자 99개 분류, 구조 예외, 장부 가림 | `test_numscan.py` (신규) |
| DRAFT-02 | 카드 7쌍 ↔ 릴스: 경고 8건 정확히 일치 | `test_convert.py` (신규) |
| DRAFT-04/05 | 캡션 첫 줄·예고 일치, 해시태그 ≤5, 2,200자 | `test_caption.py` (신규) |
| DRAFT-06 | 기존 `CommittedSpecs` 유지 + 선택 필드 정·부정 | `test_spec.py` (확장) |
| 단계 게이트 | `python3 tools/golden.py` 1회 | 기존 |

Wave 0 갭: 위 신규 파일 6개 (프레임워크 설치 불필요).

## Security Domain

`security_enforcement` 활성(ASVS 1단계). 비밀·인증·세션 없음.

| ASVS | 적용 | 통제 |
|------|------|------|
| V5 입력 검증 | yes | 날짜·슬러그 정규식(경로 조작 방지), JSON 필드 타입 검사, 해시태그 정규식, 허용 4태그 검사(새 배치도), 자리표시자 이름 `^[a-zA-Z0-9_.]+$` |
| V8/V10 데이터·무결성 | yes | 등록부 `확인`은 사람 필드 필수; `figures add`는 `미확인` 강제; git diff로 변경자 추적 |
| V6 암호 | no | — |
| V2/V3/V4 | no | — |

| 위협 | STRIDE | 완화 |
|------|--------|------|
| 웹 검색 텍스트 속 지시(프롬프트 주입)로 숫자·문구 유입 | Tampering | 검색 결과는 데이터, 숫자는 등록부 경로로만, 추가는 사용자 승인(D-06) |
| 슬러그에 `../` | Tampering | 정규식 + 드래프트 루트 하위 경로 확인 |
| 고객 실명·사례 유입 | Info disclosure | 스킬 지침에 금지, 3단계 점검이 최종 |

## Sources

### Primary (HIGH — 이 세션에서 직접 읽거나 실행)
- `/home/user/kiwoom-cards/tools/reelkit/spec.py`, `timeline.py`, `constants.py`, `layout.py`, `render.py`, `reel.py`, `tests/test_spec.py`, `tools/README.md` — v1 호환·렌더 계약
- `2026/reels/specs/*.json` 10편, `2026/*/spec.json` 카드 7개 — 패턴·숫자 전수
- 이 세션 실행: 숫자 탐지 스크립트, 카드↔릴스 대조 스크립트, Decimal/float 재현 계산, `reel.py --layout new` 렌더 2회(CTA 5줄 실험) — 스크래치패드 `numscan.py`, `prov.py`, `prov2.py`

### Secondary (MEDIUM/LOW — WebSearch 요약, 1차 미확인)
- 연금계좌 공제율·한도: wikidocs.net 블로그 다수(https://wikidocs.net/blog/@TaxSave/25192/ 등), kbam.co.kr 안내, 국가법령정보센터 조문 요약(검색 결과 인용)
- 2026 세제개편안(재정경제부, 2026-08-03): https://segye.com/newsView/20260803518169 , https://www.khan.co.kr/article/202608032044015 , https://www.pwc.com/kr/ko/insights/tax-news-flash/samilpwc_tax-news-flash_260803_kr.pdf , https://www.tossbank.com/articles/tax-reform
- 고령층 부가조사(2026-08-05): https://www.newsis.com/view/NISX20260805_0003737146 , https://www.segye.com/newsView/20260805511809 , KDI https://eiec.kdi.re.kr/policy/materialView.do?num=285107
- 2024 생명표(2025-12-03): https://www.newsis.com/view/NISX20251203_0003426271
- 소비자물가 9월(2026-10-02): https://m.korea.kr/news/policyNewsView.do?newsId=156784092 (검색 결과로만 본 링크)
- 국민연금 노령연금 평균: https://www.kukinews.com/article/view/kuk202605030016 (검색 결과), 조기/연기: https://wikidocs.net/blog/@Insight_Lab/22306/
- 이자소득세 15.4%: https://wikidocs.net/blog/@Insight_Lab/23860/
- S&P500: https://ftportfolios.com/Commentary/MarketCommentary/2022/1/11/every-year-looks-volatile-compared-to-2017 , https://www.fool.com/investing/stock-market/indexes/sp-500/annual-returns
- Instagram 캡션/해시태그: https://www.sendible.com/insights/instagram-character-limit , https://www.lilachbullock.com/instagram-hashtag-limit/ , https://circleboom.com/blog/how-many-hashtags-should-you-use-on-instagram-in-2026/

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib만, 기존 구조 확인.
- Architecture / v1 compat / 숫자 탐지 / 재현 계산: HIGH — 직접 실행·읽음.
- 세법·통계 값: LOW~MEDIUM — 2차 일치뿐, 1차 미확인 → 전부 `미확인` 시드.
- Instagram 한도: LOW~MEDIUM — 서드파티, 해시태그는 충돌.

**Research date:** 2026-10-29
**Valid until:** 세법 값은 2026-12 국회 세법 통과 전후로 재확인(약 30일); 코드 구조 관찰은 Phase 2 실행 중 유효.
