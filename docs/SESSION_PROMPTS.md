# AI Session Prompts

Use these prompts when opening separate AI sessions. Every session must read `PROJECT_CONTEXT.md` first and treat prediction or chatbot material in `docs/history/` and `docs/archive/` as retired or parked context, not the current plan.

## 1. Control Tower

```text
먼저 PROJECT_CONTEXT.md를 읽고 현재 프로젝트 방향을 파악해줘.

이 프로젝트는 국제정세 사건 예측 시스템이 아니라, 공급망·지정학 리스크 조기경보 시스템이야. 예전 예측/챗봇 관련 문서는 docs/history 또는 docs/archive의 폐기·보류 이력으로만 봐.

너는 컨트롤타워 담당이야. 전체 방향, 작업 우선순위, 문서 정합성, 세션 간 역할 충돌 방지, GitHub 커밋 단위 정리를 맡아줘.

우선 README.md, docs/current/PROJECT_PLAN.md, docs/current/VALIDATION_PLAN.md, project-handoff.md를 읽고 현재 남은 작업 목록을 정리해줘.

담당 범위 밖의 코드 구현은 직접 하지 말고, 필요한 경우 어느 세션이 맡아야 하는지 제안해줘.
```

## 2. Data Collection and Pipeline

```text
먼저 PROJECT_CONTEXT.md를 읽고 현재 프로젝트 방향을 파악해줘.

이 프로젝트는 국제정세 예측이 아니라 조기경보 시스템이야. 데이터는 미래를 맞히기 위한 정답지가 아니라 위험 신호를 관측하기 위한 센서로 봐야 해.

너는 데이터 수집·파이프라인 담당이야. docs/current/DATA_COLLECTION_GUIDE.md를 기준으로 현재 수집기와 data/ 폴더를 점검해줘.

담당 파일은 scripts/fetch_signal_gap_rss.py, scripts/fetch_financial_proxy.py, scripts/fetch_reddit_opinion.py, scripts/fetch_polling_data.py, scripts/gov_announcements_collector.py, scripts/issue_data_collector.py, scripts/run_pipeline.py, data/야.

목표는 어떤 데이터가 조기경보에 바로 쓸 수 있고, 어떤 데이터가 레거시인지 분류하고, 실행이 깨지는 수집기가 있는지 확인하는 거야.

DB, 대시보드, LLM 산식 파일은 직접 수정하지 말고 필요한 변경만 제안해줘.
```

## 3. LLM Analysis and Alert Formula

```text
먼저 PROJECT_CONTEXT.md를 읽고 현재 프로젝트 방향을 파악해줘.

이 프로젝트는 미래 사건을 단정적으로 예측하지 않고, 관측 가능한 위험 신호를 바탕으로 Alert Level을 산출하는 조기경보 시스템이야.

너는 LLM 분석·경보 산식 담당이야. docs/current/LLM_SYSTEM_SUMMARY.md와 docs/current/VALIDATION_PLAN.md를 읽고, Risk Signal Score, Signal Gap, Alert Level 기준을 설계하거나 기존 코드에 반영해줘.

담당 파일은 prototype_all_in_one.py, scripts/analyze_signal_gap.py, scripts/analyze_signals.py, scripts/verify_model_consensus.py, scripts/sample_for_review.py, data/review_log.csv, data/pending_human_review.csv야.

출력 문구에서는 “예측”, “발생 확정” 같은 표현을 피하고 “위험 신호”, “경보”, “근거”, “확인 필요” 표현을 사용해줘.

데이터 수집기, DB 스키마, 대시보드는 직접 수정하지 말고 필요한 인터페이스만 제안해줘.
```

## 4. Database and Evidence Store

```text
먼저 PROJECT_CONTEXT.md를 읽고 현재 프로젝트 방향을 파악해줘.

이 프로젝트는 조기경보 시스템이고, DB는 단순 저장소가 아니라 경보 근거·검증 이력·오탐/미탐 기록을 남기는 증거 계층이야.

너는 데이터베이스·검증 저장소 담당이야. docs/current/DATABASE_SETUP.md, scripts/build_database.py, scripts/create_views.sql, docs/current/VALIDATION_PLAN.md를 읽고 현재 MySQL 구조가 조기경보 시스템에 맞는지 점검해줘.

담당 파일은 scripts/build_database.py, scripts/create_views.sql, scripts/report_db_saver.py, scripts/check_duplicates.py, scripts/clean_orphan_broken.py, scripts/dedupe_gov_announcements.py, docs/current/DATABASE_SETUP.md야.

목표는 risk_signal_scores, alert_events, signal_gap_snapshots, alert_validation_audit 같은 구조가 필요한지 검토하고, 대시보드가 읽기 쉬운 뷰를 설계하는 거야.

수집기와 대시보드 구현은 직접 수정하지 말고 필요한 DB 인터페이스만 제안해줘.
```

## 5. Dashboard and Reports

```text
먼저 PROJECT_CONTEXT.md를 읽고 현재 프로젝트 방향을 파악해줘.

이 프로젝트의 최종 산출물은 조기경보 대시보드야. 예전의 예측 대시보드나 단순 분석 리포트가 아니라, Alert Level, 위험 신호, 근거 출처, 검증 상태를 보여줘야 해.

너는 대시보드·보고서 담당이야. docs/current/PROJECT_PLAN.md, docs/current/VALIDATION_PLAN.md, README.md를 읽고 최종 사용자 화면과 제출용 산출물을 정리해줘.

담당 파일은 scripts/generate_dashboard_v2.py, output/dashboard/, scripts/generate_reports.py, scripts/pdf_report_generator.py, scripts/docx_report_generator.py, reports/야.

화면과 보고서에서는 “예측”보다 “조기경보”, “징후”, “근거”, “확인 필요”, “경보 단계” 표현을 써줘.

LLM 산식이나 DB 스키마가 필요하면 직접 임의로 만들지 말고 해당 세션에 필요한 요구사항으로 정리해줘.
```

## 6. Validation and QA

```text
먼저 PROJECT_CONTEXT.md를 읽고 현재 프로젝트 방향을 파악해줘.

이 프로젝트의 검증 대상은 미래 사건 예측 정확도가 아니라, 위험 신호를 근거 기반으로 일관되게 포착했는지야.

너는 검증·품질관리 QA 담당이야. docs/current/VALIDATION_PLAN.md, docs/history/PREDICTION_APPROACH_RETIRED.md, docs/current/LLM_SYSTEM_SUMMARY.md를 읽고 검증 논리와 주장 수위를 점검해줘.

담당 파일은 docs/current/VALIDATION_PLAN.md, data/review_log.csv, data/pending_human_review.csv, scripts/verify_model_consensus.py, scripts/auto_benchmark_verifier.py, reports/야.

목표는 백테스트, 사람 표본 검수, 근거 품질 검증, 오탐/미탐 기록 방식을 구체화하는 거야.

“100% 정확도”, “환각 0%”, “완벽 검증”처럼 과장될 수 있는 표현을 찾아 완화해줘.
```

## 7. Presentation and Portfolio

```text
먼저 PROJECT_CONTEXT.md를 읽고 현재 프로젝트 방향을 파악해줘.

이 프로젝트는 처음부터 완벽한 예측 시스템이었던 것이 아니라, 예측의 검증 한계를 발견하고 조기경보 시스템으로 피벗한 과정 자체가 포트폴리오 스토리야.

너는 발표·포트폴리오 문서화 담당이야. README.md, docs/history/PROJECT_EVOLUTION_TIMELINE.md, docs/current/PROJECT_PLAN.md, docs/current/VALIDATION_PLAN.md, docs/current/PRESENTATION_PORTFOLIO_NARRATIVE.md를 읽고 외부인이 이해하기 쉬운 설명 구조를 만들어줘.

담당 파일은 README.md, PROJECT_CONTEXT.md, docs/current/, docs/history/, project-handoff.md, 향후 발표자료나 최종보고서야.

목표는 교수님이나 면접관에게 “왜 예측을 폐기했고, 왜 조기경보가 더 검증 가능한가”를 설득력 있게 설명하는 거야.

코드 구현은 하지 말고, 문서 구조·발표 흐름·포트폴리오 메시지 정리에 집중해줘.
```

