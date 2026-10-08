# scripts 폴더 파일 지도

이 폴더는 프로젝트의 실행 스크립트를 목적별로 나눈 작업 공간이다. 이제 파일은 실제로 하위 폴더에 배치되어 있으므로, 새 세션이나 다른 AI가 작업할 때도 아래 지도를 기준으로 보면 된다.

## 전체 실행 진입점

| 파일 | 역할 |
|---|---|
| `run_pipeline.py` | 수집 → 분석/검증 → DB 적재 → 대시보드 생성을 이어주는 메인 실행기 |
| `run_pipeline_scheduled.bat` | Windows 작업 스케줄러용 실행 파일 |

기본 실행은 프로젝트 루트에서 한다.

```powershell
python scripts/run_pipeline.py
python scripts/dashboard/generate_dashboard_v2.py
```

## 폴더 구조

```text
scripts/
├── run_pipeline.py
├── run_pipeline_scheduled.bat
├── collection/    # 외부 데이터 수집
├── analysis/      # 신호 분석·교차검증·프로토타입 분석
├── db/            # MySQL 적재·뷰 생성·중복 정리
├── dashboard/     # HTML/Streamlit 대시보드 생성
├── reports/       # Markdown/PDF/DOCX 보고서 생성
├── validation/    # 모델 검증·팩트체크·백테스트·사람 검수
└── archive/       # 현재 핵심 흐름에서 벗어난 보조/레거시 스크립트
```

## collection

외부 공개 데이터를 가져오는 수집기다.

| 파일 | 수집 대상 |
|---|---|
| `fetch_gdelt_cloud_events.py` | GDELT Cloud 구조화 사건 |
| `fetch_maritime_chokepoints.py` | 해협·항만·운임·보험료·에너지 프록시 |
| `fetch_google_trends.py` | 위험 키워드 검색량 급등 |
| `fetch_local_opinions.py` | PTT, 핀충, Bluesky 등 현지 공개 표현 |
| `fetch_telegram_public.py` | 공개 Telegram OSINT 채널 |
| `fetch_signal_gap_rss.py` | 공식·독립 언론 신호 괴리 RSS |
| `fetch_financial_proxy.py` | 금융·시장 대체 지표 |
| `gov_announcements_collector.py` | 정부 공식 발표 RSS |
| `issue_data_collector.py` | Wikipedia 관심도, FRED, 제재, IMF 무역 |
| `fetch_us_macro_signals.py` | 미국 정치·경제·외교 신호 |
| `fetch_polling_data.py` | Pew, ECFR, Ipsos 등 여론조사 |
| `fetch_reddit_localized.py` | 지역별 Reddit 보조 신호 |
| `fetch_reddit_opinion.py` | Reddit 공개 RSS 여론 |
| `fetch_customs_korea_china.py` | 한중 관세·무역 |
| `fetch_uncomtrade_semiconductors.py` | 반도체 무역 |
| `fetch_kaggle_datasets.py` | Kaggle 공개 데이터셋 |
| `fetch_ib_research.py` | 글로벌 IB 리서치 |
| `fetch_data.py` | 초기 범용 수집기 |

## analysis

수집된 신호를 조기경보 후보, 신호 괴리, 분석 리포트 후보로 바꾸는 영역이다.

| 파일 | 역할 |
|---|---|
| `cross_verify_events.py` | GDELT, 해협·항만, 로컬 의견, 텔레그램, 시장 신호를 결합해 검증 상태 산출 |
| `analyze_signal_gap.py` | 공식·독립 신호 괴리 분석 |
| `analyze_signals.py` | 이슈별 일일 분석 리포트 생성 |
| `analyze_middle_east_osint.py` | 중동 OSINT 텔레그램 분석 프로토타입 |
| `analyze_ib_insights.py` | IB 리포트 기반 리스크 보고서 생성 |
| `analyze_video_prototype.py` | 영상·시각 자료 분석 프로토타입 |
| `prototype_llm_tone_extraction.py` | LLM 톤·주장 추출 프로토타입 |
| `prototype_local_expert_sources.py` | 싱크탱크·현지언론 수집 및 태깅 |
| `prototype_gdelt_supply_chain_watch.py` | GDELT 공급망 watch 프로토타입 |

## db

데이터베이스 적재, 뷰 생성, 정합성 점검 영역이다.

| 파일 | 역할 |
|---|---|
| `build_database.py` | CSV/JSON 결과를 MySQL 테이블로 적재 |
| `create_views.sql` | 대시보드·포트폴리오용 SQL 뷰 생성 |
| `load_cross_verification_to_db.py` | 교차검증 결과를 MySQL에 동기화 |
| `report_db_saver.py` | 보고서를 파일과 DB `analysis_reports`에 저장 |
| `check_duplicates.py` | 중복 데이터 점검 |
| `clean_orphan_broken.py` | 깨진 고아 데이터 정리 |
| `dedupe_gov_announcements.py` | 정부 발표 중복 제거 |
| `rematch_gov_issues.py` | 정부 발표 이슈 매칭 재계산 |

## dashboard

최종 화면과 시각화 생성 영역이다.

| 파일 | 역할 |
|---|---|
| `generate_dashboard_v2.py` | 최종 HTML 대시보드 생성. `output/dashboard/index.html`을 만든다 |
| `streamlit_dashboard.py` | Streamlit 기반 초기/보조 대시보드 |
| `generate_charts.py` | 초기 차트 생성 스크립트 |
| `serve_unga_prototype.ps1` | UNGA 프로토타입 로컬 서빙 |

## reports

포트폴리오 산출물로 보여줄 보고서 생성 영역이다.

| 파일 | 역할 |
|---|---|
| `generate_reports.py` | 한영 종합 이슈 보고서 생성 |
| `pdf_report_generator.py` | 공식 인텔리전스 문서 스타일 PDF 생성 |
| `docx_report_generator.py` | Word 보고서 생성 |
| `build_docx_template.py` | Word 템플릿 생성 |

## validation

모델 판단과 데이터 품질을 검증하는 영역이다.

| 파일 | 역할 |
|---|---|
| `verify_model_consensus.py` | 3개 모델 합의 기반 검증 |
| `verify_factcheck_api.py` | Google Fact Check API 또는 오프라인 캐시 검증 |
| `auto_benchmark_verifier.py` | 자동 벤치마크 검증 리포트 생성 |
| `backtest_early_warning.py` | 조기경보 백테스트 보고서 생성 |
| `sample_for_review.py` | 사람 검수 표본 추출 및 검수 결과 병합 |

## archive

현재 핵심 흐름에서 벗어난 보조·실험·레거시 스크립트다. 삭제하지 않고 보관해서 프로젝트의 시행착오와 발전 과정을 남긴다.

| 파일 | 역할 |
|---|---|
| `parse_local_reddit.py` | Reddit 로컬 데이터 파싱 |
| `reddit_comment_crawler.py` | Reddit 사용자 글·댓글 크롤링 실험 |
| `legacy_utilities/` | 과거 보조 유틸리티 모음 |

## 작업 원칙

1. 새 스크립트는 목적에 맞는 하위 폴더에 만든다.
2. 전체 실행 흐름에 들어가는 경우 `run_pipeline.py`의 호출 경로도 같이 업데이트한다.
3. DB 관련 파일은 `scripts/db/`, 화면 관련 파일은 `scripts/dashboard/`, 보고서 관련 파일은 `scripts/reports/`에 둔다.
4. 현재 방향과 직접 관련이 약한 파일은 삭제하지 말고 `scripts/archive/`에 둔다.
5. 이동 후 최소한 `python -m py_compile` 또는 해당 스크립트의 `--self-test`를 실행해 경로가 깨지지 않았는지 확인한다.
