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

싱크탱크와 현지 언론 목록은 코드에 하드코딩하지 않고 향후 `config/source_registry/` 아래에서 관리한다.

권장 파일:

- `expert_feeds.yaml`
- `local_media_feeds.yaml`
- `government_sources.yaml`
- `opinion_sources.yaml`
- `customs_sources.yaml`

각 항목은 최소한 다음을 가진다.

```yaml
source_id: crisis_group_global
source_type: expert_analysis
url: https://www.crisisgroup.org/rss
country: BE
language: en
orientation: conflict_prevention_thinktank
cadence: daily
priority: high
access_method: rss
enabled: true
```

싱크탱크가 늘어나도 수집기 코드는 수정하지 않고 registry 항목만 추가한다.

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

1. `config/source_registry/` 스키마와 초기 registry 작성
2. `prototype_local_expert_sources.py`의 피드 목록을 registry로 이관
3. `fetch_expert_sources.py`를 registry 기반으로 구현
4. GDELT Cloud를 FAST 레인에 선택 단계로 연결
5. `run_pipeline.py`에 `--group fast/context/opinion/baseline` 추가
6. 소스별 실패 격리와 공통 영수증 검사 추가
7. 개별 레인 드라이런 후 검증 세션에 전달

현재 상태: **설계 문서화 완료, 레인 실행 코드와 registry 이관은 다음 구현 단계**.
