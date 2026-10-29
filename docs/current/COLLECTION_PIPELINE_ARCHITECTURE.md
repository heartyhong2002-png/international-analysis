# 데이터 수집 파이프라인 아키텍처

기준일: 2026-10-10

## 목적

이 문서는 공급망·지정학 리스크 조기경보 시스템의 **수집·정규화 경계**를 정의한다. 이 세션은 관측 가능한 원시 데이터와 수집 영수증을 만들며, LLM 분석·교차검증·경보 산식은 별도 세션에서 처리한다.

## 핵심 결정

소스별 실행 단계를 계속 추가하지 않고, 데이터의 속도와 역할에 따라 수집 레인을 나눈다.

```text
source registry
    ↓
수집 레인별 실행
    ├─ FAST: GDELT Cloud·정부 발표·Telegram·AIS·시장
    ├─ CONTEXT: 현지 언론·싱크탱크·전문가 분석
    ├─ OPINION: X·PTT·핀충·Reddit·Google Trends
    └─ BASELINE: 세관·무역·여론조사·금융·Kaggle·IB
    ↓
원시 데이터 + 수집 영수증
    ↓
공통 형식 정규화
    ↓
품질·접근 상태 기록
    ↓
검증 세션으로 전달
    ↓
DB / 대시보드
```

GDELT Cloud·AIS·정부 발표는 빠른 감지 센서이고, 싱크탱크는 느리지만 깊은 맥락 센서다. 둘을 같은 종류의 신호로 합치지 않는다.

GDELT Cloud는 학술 계정의 월 5,000 QU 한도를 고려해 FAST 레인에서도 기본 비활성으로 둔다. `--with-gdelt-cloud`를 명시한 실행만 로컬 예산 가드(기본 월 4,500 QU·일 100 QU·요청 간격 2초)를 통과한 뒤 호출하며, 가드 상태는 `data/gdelt_cloud/quota_state.json`에 남긴다. 이는 공급자 사용량 화면을 대체하지 않는 보수적 차단 장치다.

## 소스 레지스트리

싱크탱크와 현지 언론 목록은 코드에 하드코딩하지 않고 `config/source_registry/` 아래에서 관리한다.

현재 초안(2026-10-29):

- `config/source_registry/SCHEMA.md` — `relationship_role`, `issue_tags`, `packet`, `shared_schema` 포함
- `expert_feeds.yaml`
- `local_media_feeds.yaml`
- `government_sources.yaml` — 패킷 A(미국 국내 정책, `pipeline_default: false`) + 패킷 B(동맹 `relationship_role: ally`)
- `opinion_sources.yaml`
- `customs_sources.yaml`

패킷 C(`competitor_adversary_axis`, OFAC/BIS)는 A/B 스키마 안정 후 registry만 추가한다.

각 항목은 최소한 다음을 가진다.

```yaml
source_id: crisis_group_global
source_type: expert_analysis
source_role: secondary
required: false
fallback: []
license_access_note: "Public Crisis Group RSS; conflict-prevention assessments only."
url: https://www.crisisgroup.org/rss
country: BE
language: en
orientation: conflict_prevention_thinktank
cadence: daily
priority: high
access_method: rss
enabled: true
pipeline_default: true
lane: CONTEXT
```

싱크탱크가 늘어나도 수집기 코드는 수정하지 않고 registry 항목만 추가한다. 유료·쿼터 API(`pipeline_default: false`)는 기본 `--collect-only`에서 호출하지 않는다. 항공/ADS-B·파나마 운하·다국가 세관·X는 `enabled: false` + `PENDING` 라이선스 메모만 두고, 접근 확인 후에 개별 구현한다.

## 공식 발표 공통 원시 스키마·중복 제거

`fetch_whitehouse_official.py`(선택, `--with-whitehouse`)와 `gov_announcements_collector.py`(기본 파이프라인)는 모두 공식·국영 채널이지만 **저장 경로와 호출 플래그가 다르다**. 교차검증·DB 세션으로 넘기기 전 수집 계층에서는 아래 원시 필드를 맞춘다.

공통 필드(해석·경보 없음):

```text
source_id
source_type          # official_statement | state_media_news
publisher / source   # 표시용 이름
country
language
source_url           # 정규화 전 원본 URL
published_at         # UTC ISO 8601 (가능하면)
observed_at          # UTC ISO 8601
title
summary              # RSS description/summary 일부
document_type        # release | briefing | sitemap_discovery | unknown
content_hash         # 원시 바이트 또는 정규화 레코드 SHA-256
raw_ref              # 원시 파일 상대 경로
parse_status
license_access_note
```

중복 제거 규칙(수집 계층):

1. **키**: `canonical_url` = URL에서 fragment 제거, trailing `/` 제거, host 소문자화. 가능하면 `guid`도 보조 키로 보존.
2. **동일 collector 실행 내**: 같은 `canonical_url`은 첫 레코드만 유지(백악관 RSS가 사이트맵보다 우선).
3. **collector 간**: `whitehouse.gov` URL은 `fetch_whitehouse_official` 산출을 우선하고, 향후 `gov_announcements_collector`에 동일 피드를 넣지 않는다. State Dept(`state.gov`)와 White House는 별개 `source_id`이므로 URL이 다르면 독립 신호로 유지한다.
4. **유형 분리**: `state_media_news`(IRNA, Al Jazeera)는 `official_statement`와 합치지 않으며, 독립 출처 카운트에 공식 발표로 가산하지 않는다.
5. **시간창**: 동일 `canonical_url` 재수집은 덮어쓰지 않고 영수증·`observed_at`만 갱신하는 append/스냅샷 정책을 유지한다(DB `REPLACE INTO` 금지와 동일 취지).

이 규칙은 수집 영수증·원시 JSON 정합용이다. `verification_state`·Alert Level은 검증 세션 책임이다.

## 공통 레코드와 영수증

모든 수집기는 원시 응답과 별도로 다음 메타데이터를 보존한다.

```text
source_id
source_type
source_url
published_at
observed_at
language
country_scope
content_hash
raw_ref
parse_status
access_note
license_access_note
```

수집 상태는 `SUCCESS`, `PARTIAL`, `AUTH_REQUIRED`, `RATE_LIMITED`, `TIMEOUT`, `BLOCKED`, `PARSE_ERROR`, `DISABLED` 중 하나로 기록한다. 한 소스의 실패가 다른 소스의 수집을 중단시키지 않도록 한다.

## 싱크탱크·전문가 분석 레인

`prototype_local_expert_sources.py`는 현재 기본 파이프라인에서 호출되지만, 장기적으로는 registry 기반 `fetch_expert_sources.py`로 이관한다.

전문가 자료에는 다음 분류를 보존한다.

```text
source_type: expert_analysis
claim_type: assessment | warning | forecast | background
orientation
issue_tags
```

전문가 분석의 원문 수집은 이 세션의 책임이다. 주장 해석, 신뢰도, 경보 상승, 전망의 적중 여부는 LLM·검증·경보 산식 세션의 책임이다.

## 실행 그룹

현재 호환 플래그:

```powershell
python scripts/run_pipeline.py --collect-only
python scripts/run_pipeline.py --skip-db
python scripts/run_pipeline.py --skip-dashboard
python scripts/run_pipeline.py --only-db
python scripts/run_pipeline.py --collect-only --with-gdelt-cloud  # QU 가드가 있는 선택 실행
```

다음 구현 단계에서 레인 이름을 추가한다.

```powershell
python scripts/run_pipeline.py --group fast
python scripts/run_pipeline.py --group context
python scripts/run_pipeline.py --group opinion
python scripts/run_pipeline.py --group baseline
python scripts/run_pipeline.py --group all
```

기존 플래그는 하위 호환용으로 유지한다.

## 세션 간 경계

수집 세션은 `source_url`, `published_at`, `observed_at`, `content_hash`, 원시 파일 경로, 접근·라이선스 메모를 전달한다. `verification_state`, Alert Level, LLM 해석 결과는 생성하지 않는다.

검증 세션은 GDELT Cloud·AIS·항만·시장·공식 발표·현지 언론·전문가 분석을 시간순으로 결합한다. 단일 출처로 경보를 상승시키지 않는다.

## 구현 순서

1. `config/source_registry/` 스키마와 초기 registry 작성 ← **초안 완료(2026-10-28)**
2. `prototype_local_expert_sources.py`의 피드 목록을 registry로 이관(코드 로드)
3. `fetch_expert_sources.py`를 registry 기반으로 구현
4. GDELT Cloud를 FAST 레인에 선택 단계로 연결(이미 `--with-gdelt-cloud`)
5. `run_pipeline.py`에 `--group fast/context/opinion/baseline` 추가
6. 소스별 실패 격리와 공통 영수증 검사 추가
7. 개별 레인 드라이런 후 검증 세션에 전달

현재 상태: **registry YAML 초안 존재. 수집기 코드의 registry 로드·레인 `--group` 실행은 다음 단계**.

## Media Cloud 후보 센서 (2026-10-28)

- 레인: CONTEXT(보조 뉴스 확산). FAST 기본 호출에 넣지 않는다.
- 호스트: `https://search.mediacloud.org/api/` (`api.mediacloud.org`는 DNS 실패).
- 인증: `Authorization: Token` 헤더. 쿼리 파라미터에 키를 넣지 않는다.
- 필수 필터: `cs` 또는 `ss`. 기본 프로브는 US National collection `34412234`만 사용한다.
- 산출: `data/mediacloud/latest.json`의 stories 메타데이터 + receipt. `verification_state`/Alert Level 미생성.
