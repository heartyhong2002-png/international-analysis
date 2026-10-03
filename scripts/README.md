# scripts 폴더 파일 지도

이 폴더는 데이터 수집, 분석, DB 적재, 대시보드 생성, 보고서 생성 스크립트가 한곳에 모여 있는 실행 폴더다.

현재는 많은 문서와 파이프라인이 `python scripts/파일명.py` 형태로 직접 호출한다. 따라서 파일을 목적별 하위 폴더로 바로 이동하면 실행 경로가 깨질 수 있다. 당분간 실제 파일은 `scripts/` 루트에 두고, 이 문서를 기준으로 목적별로 이해한다.

## 1. 전체 실행 진입점

| 파일 | 역할 | 상태 |
|---|---|---|
| `run_pipeline.py` | 수집 → DB 적재 → 교차검증 DB 동기화 → 대시보드 생성을 순서대로 실행하는 메인 오케스트레이터 | 활성 |
| `run_pipeline_scheduled.bat` | Windows 작업 스케줄러용 실행 배치 파일 | 보조 |

처음 전체 흐름을 공부할 때는 `run_pipeline.py`를 먼저 읽는다. 이 파일이 어떤 스크립트를 어떤 순서로 부르는지 보면 프로젝트의 실행 구조가 잡힌다.

## 2. 핵심 데이터 수집기

조기경보 시스템의 현재 방향과 직접 연결되는 수집기다.

| 파일 | 수집 대상 | 주요 출력 |
|---|---|---|
| `fetch_gdelt_cloud_events.py` | GDELT Cloud 구조화 사건 | `data/gdelt_cloud/` |
| `fetch_maritime_chokepoints.py` | 해협·항만·운임·보험료·에너지 프록시 | `data/maritime_chokepoints/` |
| `fetch_google_trends.py` | 위험 키워드 검색량 급등 | `data/google_trends/` |
| `fetch_local_opinions.py` | PTT, 핀충, Bluesky 등 현지 공개 표현 | `data/local_opinions/` |
| `fetch_telegram_public.py` | 공개 Telegram OSINT 채널 | `data/signal_gap/telegram_osint_latest.csv` |
| `fetch_signal_gap_rss.py` | 공식·독립 언론 신호 괴리 RSS | `data/signal_gap/` |
| `fetch_financial_proxy.py` | 금융·시장 대체 지표 | `data/signal_gap/financial_proxy_latest.csv` |
| `gov_announcements_collector.py` | 정부 공식 발표 RSS | `scripts/data/gov_announcements/` |
| `issue_data_collector.py` | Wikipedia 관심도, FRED, 제재, IMF 무역 | `scripts/data/issues/` |

## 3. 보조·확장 데이터 수집기

현재 핵심 파이프라인에 직접 쓰이거나, 감시축 확장 시 참고할 수 있는 수집기다.

| 파일 | 역할 | 비고 |
|---|---|---|
| `fetch_us_macro_signals.py` | 미국 정치·경제·외교 신호 수집 | `run_pipeline.py` 기본 단계 |
| `fetch_polling_data.py` | Pew, ECFR, Ipsos 등 여론조사 | `run_pipeline.py` 기본 단계 |
| `fetch_reddit_localized.py` | 지역별 Reddit 보조 신호 | Reddit은 보조 센서 |
| `fetch_reddit_opinion.py` | 구형 Reddit 공개 RSS 여론 수집 | `--with-reddit` 옵션에서만 실행 |
| `fetch_customs_korea_china.py` | 한중 관세·무역 관련 수집 | 무역 신호 확장용 |
| `fetch_uncomtrade_semiconductors.py` | UN Comtrade 반도체 무역 수집 | 미중·대만 축 확장용 |
| `fetch_kaggle_datasets.py` | Kaggle 공개 데이터셋 동기화 | `--with-kaggle` 옵션 |
| `fetch_ib_research.py` | 글로벌 IB 리서치 수집 | 보고서/시장 분석 보조 |
| `fetch_data.py` | 초기 범용 수집기 | 레거시 성격, 이동 전 참조 확인 필요 |

## 4. 교차검증·신호 분석

수집된 데이터에서 조기경보 후보와 신호 괴리를 계산하거나 검증한다.

| 파일 | 역할 | 상태 |
|---|---|---|
| `cross_verify_events.py` | GDELT, 해협·항만, 로컬 의견, 텔레그램, 시장 신호를 결합해 `verification_state` 산출 | 활성 |
| `analyze_signal_gap.py` | 공식·독립 신호 괴리 분석 | 활성 |
| `analyze_signals.py` | 수집 신호를 이슈별 일일 리포트로 분석 | 활성/보조 |
| `analyze_middle_east_osint.py` | 중동 OSINT 텔레그램 분석 프로토타입 | 특정 축 보조 |
| `analyze_ib_insights.py` | IB 리포트 기반 리스크 보고서 생성 | 보조 |
| `analyze_video_prototype.py` | 영상·시각 자료 분석 프로토타입 | 실험 |
| `prototype_llm_tone_extraction.py` | LLM 톤·주장 추출 프로토타입 | LLM 구조 이해용 |
| `prototype_local_expert_sources.py` | 싱크탱크·현지언론 수집 및 태깅 | `run_pipeline.py` 기본 단계 |
| `prototype_gdelt_supply_chain_watch.py` | GDELT 공급망 watch 프로토타입 | GDELT 실험 |

## 5. DB·증거 저장·정리

MySQL 적재, 뷰 생성, 중복 정리, 보고서 DB 저장과 관련된 파일이다.

| 파일 | 역할 | 상태 |
|---|---|---|
| `build_database.py` | CSV/JSON 결과를 MySQL 테이블로 적재 | 핵심 |
| `create_views.sql` | 대시보드·포트폴리오용 SQL 뷰 생성 | 핵심 |
| `load_cross_verification_to_db.py` | 해협 센서 및 교차검증 결과를 MySQL에 동기화 | 핵심 |
| `report_db_saver.py` | 보고서를 파일과 DB `analysis_reports`에 저장 | 핵심 |
| `check_duplicates.py` | 중복 데이터 점검 | 보조 |
| `clean_orphan_broken.py` | 깨진 고아 데이터 정리 | 보조 |
| `dedupe_gov_announcements.py` | 정부 발표 중복 제거 | 보조 |
| `rematch_gov_issues.py` | 정부 발표의 이슈 매칭 재계산 | 보조 |

## 6. 대시보드·시각화

화면 생성과 시각화 관련 파일이다.

| 파일 | 역할 | 상태 |
|---|---|---|
| `generate_dashboard_v2.py` | 최종 HTML 대시보드 생성. `output/dashboard/index.html`을 만든다. | 핵심 |
| `streamlit_dashboard.py` | Streamlit 기반 초기/보조 대시보드 | 보조 |
| `generate_charts.py` | 초기 차트 생성 스크립트 | 레거시 가능성 큼 |
| `serve_unga_prototype.ps1` | UNGA 프로토타입 로컬 서빙 | 실험/보조 |

## 7. 보고서 생성

대시보드를 뒷받침하는 Markdown, PDF, Word 보고서 생성 파일이다.

| 파일 | 역할 | 출력 |
|---|---|---|
| `generate_reports.py` | 한영 종합 이슈 보고서 생성 | `reports/issues/` |
| `pdf_report_generator.py` | 공식 인텔리전스 문서 스타일 PDF 생성 | `reports/issues/pdf/` |
| `docx_report_generator.py` | Word 보고서 생성 | `reports/issues/docx/` |
| `build_docx_template.py` | Word 템플릿 생성 | 보고서 템플릿 |

## 8. 검증·품질관리

LLM 판단, 팩트체크, 백테스트, 사람 검수와 관련된 파일이다.

| 파일 | 역할 | 상태 |
|---|---|---|
| `verify_model_consensus.py` | 3개 모델 합의 기반 검증 | 활성 |
| `verify_factcheck_api.py` | Google Fact Check API 또는 오프라인 캐시 검증 | 활성/보조 |
| `auto_benchmark_verifier.py` | 자동 벤치마크 검증 리포트 생성 | 보조 |
| `backtest_early_warning.py` | 조기경보 백테스트 보고서 생성 | 활성/보조 |
| `sample_for_review.py` | 사람 검수 표본 추출 및 검수 결과 병합 | 활성 |

## 9. Reddit·커뮤니티 보조 유틸리티

Reddit은 현재 주 센서가 아니라 보조 신호다.

| 파일 | 역할 | 상태 |
|---|---|---|
| `parse_local_reddit.py` | Reddit 로컬 데이터 파싱 | 보조 |
| `reddit_comment_crawler.py` | Reddit 사용자 글·댓글 크롤링 실험 | 실험/주의 |

## 10. 정리 우선순위

실제 파일 이동은 다음 순서로 진행한다.

1. `scripts/README.md`로 목적별 분류를 유지한다.
2. `run_pipeline.py`와 각 문서에서 직접 호출되는 파일 목록을 고정한다.
3. 활성 파일, 보조 파일, 레거시 파일을 표시한다.
4. 레거시 후보는 먼저 `rg "파일명"`으로 참조 여부를 확인한다.
5. 참조가 없고 현재 방향과 무관하면 `scripts/archive/`로 이동한다.
6. 파일을 하위 폴더로 이동할 때는 반드시 래퍼 또는 호출 경로 업데이트를 같이 한다.
7. 이동 후 `python scripts/run_pipeline.py --only-db` 또는 최소한 `python scripts/generate_dashboard_v2.py`를 실행해 깨지지 않는지 확인한다.

## 11. 물리적 폴더 재배치 후보

나중에 호출 경로를 모두 업데이트할 수 있을 때의 목표 구조는 아래와 같다.

```text
scripts/
├── run_pipeline.py
├── collection/
│   ├── fetch_gdelt_cloud_events.py
│   ├── fetch_maritime_chokepoints.py
│   ├── fetch_google_trends.py
│   └── ...
├── analysis/
│   ├── cross_verify_events.py
│   ├── analyze_signal_gap.py
│   └── verify_model_consensus.py
├── db/
│   ├── build_database.py
│   ├── create_views.sql
│   └── report_db_saver.py
├── dashboard/
│   └── generate_dashboard_v2.py
├── reports/
│   ├── generate_reports.py
│   ├── pdf_report_generator.py
│   └── docx_report_generator.py
├── validation/
│   ├── backtest_early_warning.py
│   └── sample_for_review.py
└── archive/
    └── retired_or_legacy_scripts.py
```

지금은 위 구조를 목표로만 둔다. 현재 실행 안정성을 우선한다.
