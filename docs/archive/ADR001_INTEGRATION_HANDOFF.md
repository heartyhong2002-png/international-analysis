# ADR-001 연동 프로토타입 — 인수인계

> 컨트롤타워 세션(③)이 만든 프로토타입입니다. 준기님이 "LLM 추가해서 더
> 자세히 분석하고 싶다"고 하셔서, 이미 존재하는 `ADR-001_LLM_역할정의_및_감성분석_휴먼인더루프.md`
> (②번 오픈소스 LLM 트랙이 2026-09-10 작성)의 설계를 제가 수집하는 데이터에
> 연결하는 첫 단계를 만들었습니다.

## 이미 반영 완료 (검증됨)

### 1. `scripts/gov_announcements_collector.py` — `source_type` 추가

ADR 결정 2("정부 공식 보도자료는 뉴스와 분리된 '공식 입장' 레이어로 저장")를
따라, 각 RSS 피드에 `source_type`을 붙였습니다:

| source_type | 대상 | 의미 |
|---|---|---|
| `official_statement` | 한국 외교부, US State Dept 전체 | 정부 기관이 직접 운영하는 진짜 보도자료 채널 |
| `state_media_news` | IRNA, Al Jazeera | 국영/국가소유지만 광범위한 주제를 다루는 뉴스 매체 — ADR의 "뉴스" 레이어에 더 가까움 |

이 구분은 그냥 이론적인 게 아니라, 실제로 `Iran_Nuclear` 키워드 과매칭
버그(9/8 세션)의 원인이 IRNA가 "보도자료"가 아니라 "뉴스"처럼 광범위한
주제를 다뤄서였다는 걸 데이터로 이미 확인한 것에 근거합니다.

**결과물이 저장되는 곳:** `gov_announcements` 테이블의 각 행에 대응하는
JSON(`all_announcements_*.json`)에 `source_type` 필드가 이제 같이 저장됩니다.
`build_database.py`의 `gov_announcements` 테이블에는 아직 이 컬럼이 없으니,
①번(SQL) 트랙이 `ALTER TABLE gov_announcements ADD COLUMN source_type VARCHAR(30)`
정도를 추가해주면 바로 활용 가능합니다.

### 2. `scripts/prototype_llm_tone_extraction.py` — 1차 LLM 분류 프로토타입

ADR 결정 3(톤/감성 분류, 3단계 휴먼인더루프)의 **1차 단계(LLM 분류)**를
프로토타입으로 짰습니다.

- **검증 완료:** 프롬프트 구성, LLM 응답(JSON) 파싱 로직 — `python scripts/prototype_llm_tone_extraction.py --self-test`로 실행 가능 (Ollama 없이도 동작, mock 응답 4종 전부 통과 확인함). 코드펜스로 감싸진 응답, 루브릭 밖 라벨("긍정적" 같은) 등 실제로 로컬 소형 모델이 낼 법한 지저분한 출력까지 처리하도록 만들었습니다.
- **검증 못 함:** 실제 Ollama 호출(`call_ollama()`) — 샌드박스에 Ollama가 없어서 못 돌려봄. 로컬에서 `ollama serve` 켜놓고 작은 샘플로 먼저 확인 필요.
- **아직 안 만듦:** DB에서 읽어오는 부분, DB에 결과 쓰는 부분(INSERT). 프롬프트/파싱까지만 프로토타입이고, 실제 파이프라인 연결은 ②번(LLM) 트랙이 이어받는 게 자연스러울 것 같습니다 — Ollama 모델 라우팅/배치 처리 로직을 이미 그쪽이 맡고 있으니까요.

## 제안만 함 — 검토/반영 필요 (SQL 트랙)

ADR-001의 "검수 로그 데이터 스키마" 표를 그대로 옮긴 MySQL DDL을
`prototype_llm_tone_extraction.py` 안 `SCHEMA_DDL` 변수에 넣어놨습니다:

- `official_statement_extractions` — LLM이 발표문에서 뽑아낸 구조화 데이터 (발표주체/날짜/상대국/핵심주장/정책액션)
- `tone_review_log` — ADR 표와 1:1 대응 (`article_id`, `language`, `issue_id`, `source_type`, `llm_label`, `llm_evidence_quote`, `human_label`, `correction_note`, `reviewed_at`)

두 테이블 다 `gov_announcements.id`를 FK로 참조하도록 설계했습니다(기존 `issue_gov_match`와 같은 패턴). **build_database.py는 제가 직접 안 건드렸습니다** — SQL 트랙이 검토해서 `create_schema()`에 반영할지 결정해주세요.

## 다음 단계 제안 (트랙별)

- **①SQL:** `gov_announcements.source_type` 컬럼 추가 + 위 두 테이블 스키마 검토/반영
- **②LLM:** `prototype_llm_tone_extraction.py`를 로컬 Ollama로 실제 테스트 → DB 연동 완성 → ADR의 2차(표본 검수)/3차(교정 피드백) 워크플로우 설계
- **③(저, 컨트롤타워):** 두 트랙 결과물이 나오면, `generate_dashboard_v2.py`에 톤 분류 결과(예: 이슈별 우호적/중립적/비판적 비율)를 반영하는 걸 다음 프로토타입으로 제안드릴게요

---

## 이슈 ID 네이밍 통일 (2026-09-13, 준기님 결정)

준기님이 업로드해주신 `README_1.md`(②번 LLM 트랙의 실제 작업 진행 보고서)를
분석해보니, ②번 트랙이 이미 실제로 동작하는 `prototype_all_in_one.py`를
만들었고, 거기서 이슈를 `na-1`/`na-2`/`na-3` 같은 "대륙코드-숫자" 방식으로
부르고 있었습니다. 반면 제 쪽(`gov_announcements_collector.py`의
`ISSUE_MATCH_KEYWORDS`)은 처음부터 `US_Canada_Trade` 같은 서술형
snake_case 이름을 쓰고 있었어서, 같은 이슈를 가리키는 두 개의 서로 다른
ID 체계가 각 트랙에 따로 생겨버린 상태였습니다.

**준기님 결정: 서술형 이름(제 방식)으로 통일.** `na-N` 스타일은 폐기하고,
앞으로 두 트랙 다 아래 표의 서술형 이름을 issue_id로 씁니다.

### 전체 21개 매핑 표

`claude/대륙별_이슈_분석_프레임워크.md`(프로젝트 문서) 기준 21개 이슈
전체에 대한 매핑입니다. ②번 트랙은 현재 북미 3개(`na-1~3`)만 구현했고
나머지 18개는 `prototype_all_in_one.py` 130번째 줄 주석에 "나머지
15개는 프레임워크 문서 참고해서 추가"라고 직접 적어뒀으니(제가 실제
코드를 읽고 확인했습니다), 지금 당장 바꿀 건 3개뿐이고 나머지는 앞으로
새로 추가할 때 아래 이름을 바로 쓰면 됩니다 — 나중에 또 reconcile 할
필요 없게요.

| 대륙 | 구 ID (`na-N` 스타일) | 신 ID (서술형, 채택) | 비고 |
|---|---|---|---|
| 북미 | `na-1` | `US_Canada_Trade` | ②번 트랙에 이미 구현됨 — 리네임 필요 |
| 북미 | `na-2` | `US_Mexico_Migration` | ②번 트랙에 이미 구현됨 — 리네임 필요 |
| 북미 | `na-3` | `Trump_Economy` | ②번 트랙에 이미 구현됨 — 리네임 필요 |
| 남미 | `sa-1` | `Venezuela_Crisis` | 아직 미구현 — 추가 시 이 이름 사용 |
| 남미 | `sa-2` | `Brazil_Politics` | 아직 미구현 |
| 남미 | `sa-3` | `Argentina_Economy` | 아직 미구현 |
| 유럽 | `eu-1` | `Ukraine_War` | 아직 미구현 |
| 유럽 | `eu-2` | `EU_Russia` | 아직 미구현 |
| 유럽 | `eu-3` | `Baltic_Security` | 아직 미구현 |
| 중동 | `me-1` | `Iran_Nuclear` | 아직 미구현 |
| 중동 | `me-2` | `Israel_Palestine` | 아직 미구현 |
| 중동 | `me-3` | `Middle_East_Energy` | 아직 미구현 |
| 아프리카 | `af-1` | `Sudan_Conflict` | 아직 미구현 |
| 아프리카 | `af-2` | `Ethiopia_Crisis` | 아직 미구현 |
| 아프리카 | `af-3` | `Congo_Minerals` | 아직 미구현 |
| 아태 | `ap-1` | `North_Korea_Nuclear` | 아직 미구현 |
| 아태 | `ap-2` | `Taiwan_Strait` | 아직 미구현 |
| 아태 | `ap-3` | `India_Pakistan` | 아직 미구현 |
| 아태 | `ap-4` | `South_China_Sea` | 아직 미구현 |
| 아태 | `ap-5` | `Japan_Korea` | 아직 미구현 |
| 아태 | `ap-6` | `Myanmar_Crisis` | 아직 미구현 |

(`sa-N`/`eu-N`/`me-N`/`af-N`/`ap-N`은 실제로 코드에 존재하는 ID가
아니라, 프레임워크 문서 순서에 맞춰 제가 편의상 붙인 참고 번호입니다.
실제 코드에는 아직 없는 이슈들이므로 "구 ID → 신 ID" 리네임 대상이
아니라 "신규 추가 시 이 이름으로" 참고용입니다.)

### ②번(LLM) 트랙에 제안하는 변경 (제가 직접 안 건드렸습니다 — `prototype_all_in_one.py`는 ②번 트랙 소유 파일)

`prototype_all_in_one.py` 132~137번째 줄의 `ISSUES` 리스트를 아래처럼
바꾸면 됩니다 (이슈 정의 내용은 그대로, `issue_id` 문자열만 교체):

```python
ISSUES: list[IssueDef] = [
    IssueDef("US_Canada_Trade", "북미", "미-캐 무역 및 이민 갈등", ["USA", "Canada"],
             ["tariff", "trade war", "border", "immigration", "usmca"]),
    IssueDef("US_Mexico_Migration", "북미", "미-멕 이민 및 마약 정책", ["USA", "Mexico"],
             ["border wall", "cartel", "fentanyl", "migrant", "asylum"]),
    IssueDef("Trump_Economy", "북미", "트럼프 미국 경제 정책", ["USA"],
             ["federal reserve", "inflation", "tax cut", "gdp", "unemployment", "trump"]),
]
```

**주의:** 이미 `review_log.csv`에 `na-1`/`na-2`/`na-3`로 저장된 기존 검수
기록이 있다면, 리네임 시 그 CSV의 `issue_ids` 컬럼도 같이 일괄 치환해야
과거 기록과 새 기록의 issue_id가 어긋나지 않습니다 (`na-1` → `US_Canada_Trade`
등 단순 문자열 치환이면 충분합니다). 이 부분은 실제 CSV를 갖고 계신
②번 트랙에서 판단해주세요.

### 아직 안 푼 것 (참고)

- `tone_review_log.article_id` 타입 불일치: 제가 제안한 스키마(`SCHEMA_DDL`)는
  `gov_announcements.id`(정수)를 참조하도록 설계했는데, ②번 트랙의 실제
  `review_log.csv`는 `article_id`가 `e7a1726b` 같은 해시 문자열입니다.
  두 체계가 가리키는 대상 자체가 달라서(하나는 정부 발표문, 하나는 RSS
  뉴스 기사) 이건 issue_id처럼 "하나로 통일"이 아니라 "애초에 별개
  테이블/컬럼"일 가능성이 높습니다 — SQL 트랙(①)과 같이 스키마를 다시
  검토할 필요가 있습니다.
- AllSides 매체 편향(outlet_bias) 값을 공유 스키마에 어떻게 반영할지는
  아직 미정입니다 (우선순위 낮음).
