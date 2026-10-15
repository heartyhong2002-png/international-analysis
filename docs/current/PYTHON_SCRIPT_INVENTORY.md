# Python 스크립트 인벤토리

기준일: 2026-10-10

이 문서는 Python 파일을 이동하기 전에 역할·상태·호출 관계를 확인하기 위한 인벤토리다. 이 단계에서는 파일을 삭제하거나 이동하지 않는다.

## 현재 구조 요약

- Python 파일: 57개
- 전체 Python 파일 컴파일 점검: 통과
- 정식 오케스트레이터: `scripts/run_pipeline.py`
- 현재 파이프라인이 직접 호출하는 주요 영역: `collection/`, `analysis/`, `db/`, `dashboard/`
- 최근 추가된 외부 API 프로토타입 4개는 `scripts/collection/`으로 이동함

## 1. 수집기

### 활성·주요 수집기 (`scripts/collection/`)

| 파일 | 역할 | 상태 |
|---|---|---|
| `fetch_maritime_chokepoints.py` | 해협·해운·에너지 프록시 | active |
| `fetch_gdelt_cloud_events.py` | GDELT Cloud Events | active/구독 상태 의존 |
| `fetch_whitehouse_official.py` | 백악관 공식 RSS·제한적 사이트맵 보완 | optional active; `--with-whitehouse` |
| `fetch_signal_gap_rss.py` | 권위주의 국가 신호 공백 RSS | active |
| `gov_announcements_collector.py` | 정부 발표 RSS | active |
| `issue_data_collector.py` | 이슈·Wikipedia·FRED·제재·무역 | active |
| `fetch_local_opinions.py` | PTT·핀충·Bluesky·Google News·Telegram | active |
| `fetch_google_trends.py` | Google Trends | active |
| `fetch_us_macro_signals.py` | 미국 정치·경제·금융·외교 | active |
| `fetch_financial_proxy.py` | 금융 프록시 | active |
| `fetch_polling_data.py` | 여론조사 | active |
| `fetch_customs_korea_china.py` | 한국·중국 세관 | active/manual |
| `fetch_uncomtrade_semiconductors.py` | UN Comtrade 반도체 무역 | active/manual |
| `fetch_telegram_public.py` | 공개 Telegram OSINT | active/manual |
| `fetch_reddit_opinion.py` | Reddit 공개 여론 | optional |
| `fetch_reddit_localized.py` | Reddit 지역화 수집 | optional |
| `fetch_kaggle_datasets.py` | 공개 데이터셋 동기화 | optional |
| `fetch_ib_research.py` | IB 리서치 자료 | manual; `run_pipeline.py` 미호출 |
| `fetch_data.py` | 초기 통합 수집 유틸리티 | review-needed |

### 신규 대체·보조 수집기 (`scripts/collection/`)

| 파일 | 역할 | 현재 상태 |
|---|---|---|
| `collection/fetch_gdelt_v2_public.py` | 원본 GDELT 2.0 DOC | candidate; 429 확인 |
| `collection/fetch_mediacloud.py` | Media Cloud 뉴스 검색 | candidate; 엔드포인트 재확인 필요 |
| `collection/fetch_acled.py` | ACLED 분쟁·시위 사건 | candidate; 예멘 3건 테스트 성공 |
| `collection/fetch_event_registry.py` | Event Registry 이벤트 | candidate; 3건 테스트 성공, 보조 수단 |

### 실제 호출 여부 확인(2026-10-10)

- `analysis/prototype_local_expert_sources.py`는 이름에 prototype이 남아 있지만 현재 `run_pipeline.py`에서 기본 호출되므로 **active (legacy naming)**로 분류한다.
- `collection/fetch_reddit_opinion.py`, `collection/fetch_kaggle_datasets.py`는 각각 `--with-reddit`, `--with-kaggle` 선택 시 호출되는 **optional active** 수집기다.
- `analysis/prototype_gdelt_supply_chain_watch.py`, `analysis/prototype_llm_tone_extraction.py`, `collection/fetch_ib_research.py`, `collection/fetch_reddit_localized.py`는 현재 오케스트레이터에서 직접 호출되지 않는 **manual/candidate**다.
- `analysis/analyze_*.py` 대부분은 파이프라인에서 직접 실행되지 않는 수동 분석 도구이며, 검증 세션과 소유권을 확인한 뒤 `manual` 또는 `archive`로 이동한다.
- `scripts/archive/` 파일은 계속 legacy 보관 대상으로 유지하며 이번 정리에서 삭제하지 않는다.

## 2. 분석·검증

| 경로 | 역할 | 상태 |
|---|---|---|
| `analysis/cross_verify_events.py` | 복수 계통 교차검증 | 별도 검증 세션 담당 |
| `analysis/analyze_signal_gap.py` | 신호 공백 분석 | review-needed |
| `analysis/analyze_signals.py` | 신호 분석 | review-needed |
| `analysis/analyze_middle_east_osint.py` | 중동 OSINT 분석 | manual/prototype |
| `analysis/analyze_ib_insights.py` | IB 분석 | manual/prototype |
| `analysis/prototype_*.py` | 실험·프로토타입 | candidate 또는 legacy 검토 |
| `validation/*.py` | 백테스트·표본검수·모델검증 | 검증 세션 담당 |

## 3. DB·대시보드·보고서

- `db/build_database.py`: 원본·정규화 데이터 DB 적재
- `db/load_cross_verification_to_db.py`: 교차검증 결과 DB 적재
- `db/check_duplicates.py`, `db/dedupe_gov_announcements.py`, `db/clean_orphan_broken.py`: DB 유지보수
- `dashboard/generate_dashboard_v2.py`, `dashboard/streamlit_dashboard.py`: 대시보드 담당 세션 소유
- `reports/*.py`: PDF·Word·분석보고서 생성

이 세션은 대시보드·검증 로직을 직접 수정하지 않는다.

## 4. 보관·레거시

`scripts/archive/` 아래 파일은 현재 파이프라인에서 직접 호출하지 않는 보관 대상이다.

- `archive/legacy_utilities/advanced_fetch_data.py`
- `archive/legacy_utilities/convert_to_pdf.py`
- `archive/legacy_utilities/merge_semiconductor_trade.py`
- `archive/legacy_utilities/test_opensanctions_key.py`
- `archive/parse_local_reddit.py`
- `archive/reddit_comment_crawler.py`

삭제하지 말고, 재현성·역사 추적을 위해 유지한다.

## 5. 파이프라인 호출 관계

`run_pipeline.py`는 현재 다음 경로를 사용한다.

```text
run_pipeline.py
├─ collection/* 수집기
├─ analysis/prototype_local_expert_sources.py
├─ analysis/cross_verify_events.py
├─ db/build_database.py
├─ db/load_cross_verification_to_db.py
└─ dashboard/generate_dashboard_v2.py
```

새 외부 API 수집기는 인증과 엔드포인트가 안정화될 때까지 정식 파이프라인에 연결하지 않는다. 연결 시에는 `--skip-*` 플래그와 실패 영수증을 먼저 추가한다.

실행 그룹은 다음 플래그로 분리한다.

- 수집·전처리: `python scripts/run_pipeline.py --collect-only`
- DB 제외: `--skip-db`
- 대시보드 제외: `--skip-dashboard`
- 기존 DB 전용 동작: `--only-db`

## 6. 정리 원칙

1. 문서 인벤토리와 호출 관계를 먼저 갱신한다.
2. `active`, `candidate`, `manual`, `review-needed`, `legacy` 상태를 확정한다.
3. 파일 이동은 한 번에 하나의 영역만 수행한다.
4. 이동 후 모든 `run_pipeline.py`, README, 문서의 호출 경로를 갱신한다.
5. 전체 57개 파일 컴파일과 선택 파이프라인 테스트를 실행한다.
6. 삭제 대신 `scripts/archive/`로 이동하고, 이동 기록을 남긴다.

## 7. 향후 수집기 위치 결정

| 센서 | 권장 경로 | 배치 원칙 |
|---|---|---|
| 항공 화물·공항 운항 | `scripts/collection/fetch_aviation_supply_chain.py` | 항만 센서와 동일한 원시 영수증 형식으로 저장하되 별도 데이터셋 유지 |
| 파나마 운하 | `scripts/collection/fetch_panama_canal.py` | 기존 해협 수집기와 분리해 운하 통행·대기·제한 공지를 독립 수집 |
| 다국가 세관 | `scripts/collection/fetch_customs_multi_country.py` | 국가별 어댑터를 한 수집기 아래에 두고 소스 목록은 `config/source_registry/`에 관리 |
| X 공개 신호 | `scripts/collection/fetch_x_public.py` | API·공개 검색 범위만 사용하고 온라인 정보환경 신호로 표시 |
| 정부 웹/API·RSS·HTML/PDF | `scripts/collection/fetch_government_web.py` | 기존 RSS 수집기와 분리해 API→RSS→sitemap→HTML/PDF 순서의 허용된 공개 접근만 사용 |

## 다음 정리 작업

- `fetch_data.py`, `prototype_*`, `manual` 파일의 소유 세션과 보관 위치 확정
- ACLED·Event Registry를 후보 수집 그룹에 선택 연결할지 결정
- 항공·파나마 운하·다국가 세관·X·정부 웹 수집기 구현 및 개별 영수증 테스트

수집 레인·source registry·싱크탱크 수집 경계는 [`COLLECTION_PIPELINE_ARCHITECTURE.md`](COLLECTION_PIPELINE_ARCHITECTURE.md)에 정리했다.
