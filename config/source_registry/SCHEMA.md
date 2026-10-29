# Source Registry Schema

기준일: 2026-10-29

수집기는 URL·피드 목록을 코드에 하드코딩하지 않고, 가능하면 이 디렉터리의 YAML을 읽는다.
이 초안은 **문서·계약**이며, 기존 수집기를 즉시 registry 전용으로 바꾸지 않는다.
registry 항목만으로 Alert Level / `verification_state` / 선거·전쟁 예측을 산출하지 않는다.

## 공통 필드

| 필드 | 필수 | 설명 |
|---|---|---|
| `source_id` | yes | 안정적인 소문자 snake_case 식별자 |
| `source_type` | yes | `official_statement`, `state_media_news`, `local_media`, `expert_analysis`, `online_expression`, `trade_statistics`, `event_api`, `news_api`, `regulation_notice` 등 |
| `source_role` | yes | `primary` / `secondary` / `discovery_only` / `fallback` |
| `relationship_role` | no | `ally` / `competitor_adversary_axis` / `domestic_us` / `multilateral` / `other`. 대외 문서는 “적대국” 대신 `competitor_adversary_axis` |
| `required` | yes | 기본 수집 레인에서 실패를 치명으로 볼지 여부. 유료·쿼터 API는 보통 `false` |
| `fallback` | no | 실패 시 대체 `source_id` 목록 |
| `license_access_note` | yes | 공개 여부, robots/ToS, 키 필요 여부, 재배포 한계 |
| `robots_note` | no | robots.txt·요청 제한 메모 (`checked` / `pending` / `n/a-api`) |
| `url` | yes* | 피드·엔드포인트·문서 URL (`*` API 경로만 있는 경우는 `endpoint`로 대체 가능) |
| `endpoint` | no | REST/JSON API 기본 경로 |
| `country` | yes | ISO 3166-1 alpha-2, `MULTI`, 또는 기구 코드(`NATO`, `EU`) |
| `language` | yes | BCP 47 유사 태그 (`en`, `ko`, `zh`, `multi`) |
| `access_method` | yes | `rss` / `atom` / `api` / `html` / `sitemap` / `file` |
| `enabled` | yes | registry에서 활성 여부 |
| `pipeline_default` | yes | `run_pipeline.py` 기본 `--collect-only`에서 호출할지. 유료/쿼터/신규 API는 `false` |
| `collector` | no | 담당 스크립트 경로. 미구현이면 `PENDING` |
| `shared_schema` | no | 공식 발표 공통 원시 스키마 사용 여부 (`official_raw_v1`) |
| `issue_tags` | no | 정책 신호 태그 후보(해석·경보 아님). 예: `US_Trade_Tariff` |
| `cadence` | no | `hourly` / `daily` / `weekly` / `manual` |
| `priority` | no | `high` / `medium` / `low` |
| `orientation` | no | 매체·싱크탱크 성향 메모(해석 결과가 아님) |
| `lane` | no | `FAST` / `CONTEXT` / `OPINION` / `BASELINE` |
| `packet` | no | `A` / `B` / `C` / `legacy` — 컨트롤타워 착수 패킷 |

## 공식 발표 공통 스키마 (`shared_schema: official_raw_v1`)

White House·정부 RSS·미국 국내 정책 API 정규화 시 최소 필드:

```text
source_id, source_type, publisher, country, language,
source_url, published_at, observed_at, title, summary,
document_type, content_hash, raw_ref, parse_status,
license_access_note, relationship_role, issue_tags
```

중복 제거: `canonical_url`(fragment·trailing slash 제거, host 소문자). `whitehouse.gov`는 `fetch_whitehouse_official` 우선. 상세는 `COLLECTION_PIPELINE_ARCHITECTURE.md`.

## 수집 상태 값 (영수증)

`SUCCESS`, `PARTIAL`, `AUTH_REQUIRED`, `RATE_LIMITED`, `TIMEOUT`, `BLOCKED`, `PARSE_ERROR`, `DISABLED`

## 금지

- 비공개 그룹·로그인 우회·계정 탈취
- API 키·Authorization 헤더를 registry·영수증·로그에 기록
- registry 항목만으로 Alert Level / `verification_state` 산출
- 당선·전쟁 발발 예측 태그 사용 (`US_Election_Policy_Signal`은 공약·법안·행정조치 관측만)
