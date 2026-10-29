# 원고 소스 문법 (spec.src.json, caption.src.json)

도구가 읽는 문법만 적는다. 판단 기준(문체, 줄 너비, 금지 표현)은 [house-style.md](house-style.md).
확장은 `python3 tools/draft.py expand <dir>/spec.src.json <dir>/spec.json`.

## spec.src.json

최상위 키는 `series`, `basis`, `inputs`, `derive`, `scenes` 다섯 개뿐이다 (그 밖의 키는 오류). `scenes` 만 필수.

```json
{
 "series": {"name": "연말정산 바로 알기", "episode": 2, "next": "IRP 세액공제 개정안"},
 "basis": "{{fig.pension_credit_limit_total|man_won}} 납입 예시 · 지방소득세 포함",
 "inputs": {"amt": {"value": "1000000", "unit": "원", "label": "100만 원 공제 예시"}},
 "derive": {"c_low": {"fn": "pct_of", "args": ["inputs.amt", "fig.pension_credit_rate_low"]}},
 "scenes": [{"top": "", "lines": ["연금계좌 세액공제", "<g>한도가 얼마일까?</g>"]}]
}
```

### 자리표시자

숫자는 글자로 적지 않고 `{{이름|서식}}` 으로 쓴다. 이름은 셋 중 하나다.

| 이름 | 뜻 |
|------|----|
| `fig.<id>` | 수치 등록부 항목 (`python3 tools/draft.py figures list --grep 글자` 로 id 확인) |
| `inputs.<이름>` | 이 릴스 한정 시나리오 가정. `value`(문자열 숫자), `unit`, `label` 을 쓰고 라벨에 **예시, 가정, 가상** 중 하나를 넣는다 |
| `<derive 이름>` | 앞서 정의한 `derive` 결과 (선언 순서대로만 참조 가능) |

`derive` 는 `{"fn": 함수 이름, "args": [이름 또는 앞선 derive, ...]}` 다. 이름은 소문자·숫자·밑줄.
계산을 직접 하거나 계산 결과를 글자로 적지 않는다.

### 계산 함수 (calc.FUNCTIONS)

| 함수 | 인자 | 뜻 |
|------|------|----|
| `add` / `sub` / `mul` / `div` | a, b | 더하기, 빼기, 곱하기, 나누기 (0 나누기 오류) |
| `neg` | a | 부호 반대 |
| `pct_of` | amount, rate_pct | amount 의 rate_pct 퍼센트 |
| `with_local` | rate_pct, local_ratio_pct | 소득세율에 지방소득세(소득세의 ratio %)를 더한 실효율 |
| `after_tax` | value, tax_pct | 세금을 뗀 값 |
| `installment_simple_interest` | monthly, annual_rate_pct, months | 월 납입 적금의 단리 이자 합계 |
| `yield_pct` | gain, principal | 수익률(%) |
| `months_between_ages` | from_age, to_age | 나이 구간의 개월 수 |
| `annuity_pmt` | target, annual_rate_pct, months | 목표 금액을 월 납입(월말, 월복리)으로 모으는 월 납입액 |
| `fv_monthly` | pmt, annual_rate_pct, months | 월 납입(월말, 월복리)의 만기 금액 |

개월 수는 1~1200 의 정수. 비율 인자는 퍼센트 값(15 는 15%).

### 표시 서식 (calc.FORMATS)

반올림은 표시 서식에서 한 번만, 사사오입(동점은 올림)이다.

| 서식 | 값 단위 | 예 (값 → 화면) |
|------|---------|----------------|
| `pct` | `%` | 15.4 → "15.4%", 15 → "15%" |
| `pct0` | `%` | 15.4 → "15%" |
| `pct1` | `%` | 3 → "3.0%" |
| `signed_pct` | `%` | -30 → "−30%", 12.5 → "+12.5%" (음수 부호는 − 로 쓴다) |
| `man` | `원` | 77,120,000 → "7,712만" |
| `man1` | `원` | 66,000 → "6.6만" |
| `man_won` | `원` | 55,000,000 → "5,500만 원" |
| `eok_man_won` | `원` | 372,000,000 → "3억 7,200만 원" |
| `won` | `원` | 12,345 → "12,345원" |
| `num` | 단위 없음 | 1234.5 → "1,234.5" |
| `se` | `세` | 65 → "65세" |
| `nyeon` | `년` | 20 → "20년" |
| `gaewol` | `개월` | 36 → "36개월" |
| `dal` | `개월` 또는 단위 없음 | 7.5 → "7.5달" |

서식은 값의 단위(등록부 `unit`, `inputs` 의 `unit`, derive 결과 단위)에 맞는 것만 쓸 수 있다. 금액에 `num`,
비율에 `man_won` 처럼 안 맞으면 확장 오류다. 자리표시자 바로 뒤에 `만`, `원`, `%` 같은 단위를 글자로 붙이지 않는다
(`{{x|man}}원` 은 오류 — `{{x|man_won}}` 을 쓴다). 조사(`까지`, `의`, `만에`)는 붙여도 된다.

derive 결과 단위: `add`/`sub` 는 같은 단위끼리(나이 − 나이 = 년), `mul` 은 단위 없음 × 무엇이든, 원 × 개월/년 = 원,
% × 년/개월 = %, `div` 는 같은 단위끼리 = 단위 없음, 원 ÷ 개월/년 = 원, 단위 없음 ÷ % = 년(72의 법칙).
`pct_of`, `after_tax` 의 비율 인자와 `with_local` 의 두 인자는 `%`, 적금·월 납입 함수는 (원, %, 개월),
`months_between_ages` 는 (세, 세) 여야 한다.

화면 값이 정확값과 다르게 반올림되면 점검이 APPROX 경고를 낸다. 이때 "약" 을 앞에 쓴다 ("약 {{x|man}}").
정확히 떨어지는 값에는 "약" 을 쓰지 않는다. 추정치에는 항상 예시·가정 표시를 붙인다.

### series

`series` 에 `name`, `episode`(1~10 정수), `next`(선택)를 적으면 도구가 채운다.

- 장면 1 의 `top` 은 `""` 로 비워 두면 `시리즈명 ①` 로 채워진다. 직접 쓸 때는 같은 값이어야 한다.
- 마지막(CTA) 장면 끝에 `<s>다음 편: ...</s>` 줄이 붙는다. 직접 쓰려면 `series.next` 와 같아야 한다.
- 시리즈 이름·회차·다음 편은 `series` 에만 쓴다 (본문에 따로 쓰지 않는다).

### scenes

장면 하나는 `{"top": 문자열, "lines": [문자열, ...]}`. `top` 은 비울 수 있다.
마크업은 `<g>강조(금색)</g>`, `<s>작은 글씨</s>` 만 쓴다.

## caption.src.json

```json
{
 "hook": "연금계좌 세액공제, 한도가 얼마일까?",
 "summary": ["요약 1", "요약 2", "요약 3"],
 "hashtags": ["#연금저축", "#IRP", "#세액공제", "#연말정산"]
}
```

- `hook`: 첫 줄 후킹 문장. `summary`: 정확히 3줄. `hashtags`: 주제 태그 3~5개 (브랜드 태그 포함 최대 5개).
- 게시글에 쓰는 숫자는 이미 `spec.json` 에 있는 숫자여야 한다. 새 숫자를 넣지 않는다.
- 시리즈명·회차·다음 편은 도구가 `spec.json` 의 `series` 에서 가져온다 (여기에 쓰지 않는다).
- 면책·CTA 문구는 `tools/data/caption_config.json` 에서 붙는다. 브랜드 해시태그는 만들어 넣지 않는다.

## 예시

- 세액공제 vs 소득공제 (입력 가정 + derive): `tools/tests/fixtures/draft-tax.src.json`
- 연금계좌 세액공제 한도 (등록부 수치만, 시리즈 ②): `tools/tests/fixtures/draft-pension.src.json` 과 `draft-pension.caption.src.json`

`발의` 상태 수치는 줄이나 `basis` 에 "발의안" 또는 "정부안" 표현을 함께 적는다.
