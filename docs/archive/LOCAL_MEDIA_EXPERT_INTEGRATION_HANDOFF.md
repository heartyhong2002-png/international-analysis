# 현지언론(local_media)/전문가분석(expert_analysis) 통합 프로토타입 — 인수인계

> 컨트롤타워 세션(③)이 만든 프로토타입입니다. 준기님이 "현지 언론이랑 전문가
> 의견도 중요할 것 같은데 어떻게 수집해야 할까?"라고 물어보셔서, ADR-001 구조
> (source_type: `official_statement` / `state_media_news` / `news`)에 두 레이어를
> 새로 추가하는 설계 논의를 먼저 하고, 코드 프로토타입까지 만든 결과물입니다.

## 왜 이 두 소스가 기존 레이어에 안 맞았는가

- **현지 언론(local_media)**: `news`(prototype_all_in_one.py의 NPR/BBC)와 성격은
  같지만, `OutletBiasLookup`이 쓰는 AllSides 데이터가 미국 매체 중심이라 해외
  현지 매체(Moscow Times, Al-Monitor 등)는 편향 태깅이 전혀 안 됩니다. 그렇다고
  이걸 무시하면 "이란 국영매체(IRNA)는 state_media로 태깅해두고, 러시아 독립
  매체는 아무 성향 정보 없이 그냥 news로 섞인다"는 비일관성이 생깁니다.
- **전문가 분석(expert_analysis)**: 이게 진짜 문제였습니다. ADR-001 addendum
  (2026-09-14)이 "비판적 = narrative적으로 특정 주체를 비난할 때만"으로 톤
  기준을 확정했는데, 싱크탱크 리포트나 칼럼은 애초에 "정부가 이렇게 해야
  한다/이 정책은 위험하다"는 식으로 **주장하는 게 본업**입니다. 이 기준을 그대로
  적용하면 전문가 의견 대다수가 critical로 쏠려서, 정작 이 프로젝트가 잡고
  싶어했던 "같은 사건도 매체마다 다르게 프레이밍하는가"라는 신호가 오염됩니다.
  → 톤 분류 대신 "이 사람/기관이 뭘 주장하고 뭘 예측하는지"를 뽑아내는 별도
  스키마가 필요하다고 판단했습니다.

## 이미 반영 완료 (검증됨)

### 1. `scripts/prototype_local_expert_sources.py` — 신규 파일

- **LOCAL_EXPERT_FEEDS**: 5개 피드, 전부 WebFetch로 실제 RSS 2.0 응답과 최신
  게시물 제목까지 확인함(2026-09-14). 9개 후보 중 4개는 탈락시켰고 이유를
  파일 상단에 기록해뒀습니다(다음에 또 시도 안 하도록).

  | 소스 | source_type | 커버 이슈 |
  |---|---|---|
  | The Moscow Times | local_media | Ukraine_War, EU_Russia, Baltic_Security |
  | Al-Monitor | expert_analysis | Israel_Palestine, Iran_Nuclear, Middle_East_Energy |
  | Chatham House Expert Comment | expert_analysis | 전 지역 (규칙기반 태깅에 맡김) |
  | International Crisis Group | expert_analysis | Sudan_Conflict, Ethiopia_Crisis, Congo_Minerals, Myanmar_Crisis, Venezuela_Crisis |
  | 38 North | expert_analysis | North_Korea_Nuclear |

- **EXPERT_ANALYSIS_PROMPT**: 톤 라벨 없이 `author_or_org / key_argument /
  forecast / forecast_horizon / evidence_basis / stance_toward` 6개 필드를
  뽑는 프롬프트. `parse_expert_response()` 파싱 로직은
  `python scripts/prototype_local_expert_sources.py --self-test`로 검증
  가능(4종 케이스 전부 통과 확인).
- **LOCAL_OUTLET_ORIENTATION**: AllSides가 못 잡는 해외 매체를 위한 보조
  성향 태그(예: Moscow Times = "independent-in-exile"). `local_media` 기사에
  `source_orientation` 필드로 같이 저장됩니다.
- **`prototype_all_in_one.py`의 `tag_article`/`OutletBiasLookup`/
  `MODEL_BY_LANGUAGE`/`_call_ollama`를 그대로 import해서 재사용**했습니다
  (이슈 매칭 로직을 두 군데서 따로 관리하면 어긋난다는 걸 기존 프로젝트에서
  이미 경험했기 때문 — `gov_announcements_collector.py`의 `ISSUE_MATCH_KEYWORDS`가
  `prototype_all_in_one.py`의 `ISSUES`와 별도로 진화해온 전례 참고). 실제 import가
  동작하는지 클라우드 세션에서 `python -c "from prototype_local_expert_sources
  import ..."`로 확인 완료.
- **결과 저장**: `scripts/data/local_expert_review_log.csv`에 append 방식으로
  저장합니다 (review_log.csv를 직접 덮어쓰지 않음 — 두 세션이 같은 파일을
  동시에 쓰면 위험하다는 project-handoff.md의 경고를 따른 것).

### 2. 이슈 키워드 커버리지 문제 — 발견 후 수정 완료

38 North의 실제 최근 기사("북중 무역시설 개통") 하나로 `tag_article()`을
직접 돌려보니, `countries_involved`는 `["North Korea", "China"]`로 정확히
잡히는데 `North_Korea_Nuclear`의 키워드(`nuclear test`, `missile launch`,
`denuclearization`)에는 안 걸려서 `tag_status="unclassified"`로 빠졌습니다.
이어서 5개 소스의 실제 최신 헤드라인 8건 전체로 확인해보니 **7건(87.5%)이
같은 이유로 unclassified**였습니다 — `unclassified`는 자원 절약을 위해
LLM을 아예 안 부르는 설계라서, 이대로 두면 모처럼 추가한 전문가 소스
대부분이 그냥 버려지는 셈이었습니다.

**준기님 확정으로 코드에 반영함**: `tag_article_with_source_awareness()`를
추가해서, `local_media`/`expert_analysis`에 한해 "국가는 맞고 이슈 키워드는
안 맞는" 케이스를 `unclassified` 대신 `ambiguous`(LLM 판단에 맡김)로
승격시킵니다. `news`(NPR/BBC)는 그대로 둠 — 거긴 진짜 무관한 기사(Nicolas
Cage 싱크홀 등)를 걸러내는 목적으로 unclassified가 필요하기 때문입니다.
`tag_article()` 자체(②번 트랙 소유)는 안 건드리고 후처리로만 구현했고,
실제 헤드라인 8건을 고정 회귀 테스트(`_self_test_tagging()`)로 넣어뒀습니다
(기대값: unclassified 1건[Somalia, 애초에 COUNTRY_ALIASES에 없는 국가라
정상] + ambiguous 6건 + matched 1건). `python scripts/prototype_local_expert_sources.py
--self-test`로 재현 가능.

**덤으로 발견한 것**: `LOCAL_EXPERT_LOG_FIELDS`에 애초에 `issue_ids`/
`countries_involved`/`tag_status`/`outlet_bias`가 빠져 있어서, `tag_article()`이
계산한 결과가 CSV에 저장 안 되고 `DictWriter(extrasaction="ignore")`에
조용히 버려지고 있었습니다. 같이 고침.

## 아직 안 함 (다음 단계 제안)

- **①SQL 트랙**: `SCHEMA_DDL_ADDENDUM`(파일 하단)에 `expert_analysis_extractions`
  테이블 제안을 넣어뒀습니다. `article_id` 타입 불일치 문제는
  `ADR001_INTEGRATION_HANDOFF.md`에 이미 적힌 미해결 이슈와 동일하니 그때
  한 번에 정리하는 걸 추천합니다.
- **②LLM 트랙**: 실제 로컬 Ollama로 `--with-llm` 검증 필요 (클라우드 세션에는
  Ollama가 없어서 self-test까지만 확인함). 이 프로토타입을
  `prototype_all_in_one.py`에 합칠지 결정 필요 — 합치는 정확한 방법을 그
  파일에는 손 안 대고 `prototype_local_expert_sources.py` 맨 아래 주석으로
  4단계 스니펫을 남겨뒀습니다(RSS_FEEDS 구조 변경, `fetch_articles()` 언어
  하드코딩 제거, `source_type` 하드코딩 제거, LLM 분기 추가).
- **다음 라운드 후보 (이번엔 소스를 못 찾음)**: 남미 3개 이슈(Venezuela/
  Brazil/Argentina), 아태 5개 이슈(Taiwan_Strait/India_Pakistan/
  South_China_Sea/Japan_Korea/Myanmar_Crisis — Myanmar는 Crisis Group이
  일부 커버하지만 전용 소스는 아직 없음).
- Kyiv Independent(404), Haaretz(WebFetch가 robots.txt 차단) — 로컬 환경에서
  `requests` + 브라우저형 User-Agent로 재시도해볼 가치 있음
  (`gov_announcements_collector.py`의 `REQUEST_HEADERS` 패턴 참고).
