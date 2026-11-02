"""
early_warning_pipeline_dag.py — 공급망·지정학 리스크 조기경보 Multi-Lane 오케스트레이션 DAG
===================================================================================

설계 원칙:
1. Concurrency (병렬성): 의존성이 없는 4대 수집 레인을 병렬 실행하여 I/O 지연 단축.
2. Fault Isolation (장애 격리): 특정 수집기 장애가 전체 파이프라인 중단으로 번지지 않도록 격리.
3. Resilience (자동 재시도): 네트워크 타임아웃/일시 오류 발생 시 Exponential Backoff 기반 재시도.
4. Determinism: Alert Level 및 Anomaly Score는 검증된 산식을 거쳐 단일 출처 상승을 차단.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

# 기본 실행 환경 및 인수 설정
DEFAULT_ARGS = {
    "owner": "international_analysis",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(minutes=15),
}

with DAG(
    dag_id="early_warning_risk_pipeline",
    default_args=DEFAULT_ARGS,
    description="OSINT 기반 공급망·지정학 리스크 조기경보 4-Lane 병렬 수집 & 지능형 전처리 파이프라인",
    schedule_interval="0 */4 * * *",  # 4시간마다 무인 자동 실행
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    tags=["geopolitics", "supply_chain", "early_warning", "osint"],
) as dag:

    # --------------------------------------------------------------------------
    # 파이프라인 시작 & 종료 마커
    # --------------------------------------------------------------------------
    start_pipeline = EmptyOperator(task_id="start_pipeline")
    end_pipeline = EmptyOperator(task_id="end_pipeline")

    # --------------------------------------------------------------------------
    # STAGE 1 : 4대 수집 레인 병렬 수집 (Parallel Collectors)
    # --------------------------------------------------------------------------
    # 1. FAST LANE: 해협 병목 & 공식 정부 발표
    collect_chokepoints = BashOperator(
        task_id="collect_maritime_chokepoints",
        bash_command="python /opt/airflow/scripts/collection/fetch_maritime_chokepoints.py",
    )

    collect_gov_announcements = BashOperator(
        task_id="collect_gov_announcements",
        bash_command="python /opt/airflow/scripts/collection/gov_announcements_collector.py",
    )

    collect_whitehouse = BashOperator(
        task_id="collect_whitehouse_official",
        bash_command="python /opt/airflow/scripts/collection/fetch_whitehouse_official.py",
    )

    # 2. CONTEXT LANE: 싱크탱크 & 3자 OSINT
    collect_expert_sources = BashOperator(
        task_id="collect_expert_sources",
        bash_command="python /opt/airflow/scripts/analysis/prototype_local_expert_sources.py",
    )

    collect_signal_gap_rss = BashOperator(
        task_id="collect_signal_gap_rss",
        bash_command="python /opt/airflow/scripts/collection/fetch_signal_gap_rss.py",
    )

    # 3. OPINION LANE: 로컬 포럼 & 검색 트렌드
    collect_local_opinions = BashOperator(
        task_id="collect_local_opinions",
        bash_command="python /opt/airflow/scripts/collection/fetch_local_opinions.py",
    )

    collect_google_trends = BashOperator(
        task_id="collect_google_trends",
        bash_command="python /opt/airflow/scripts/collection/fetch_google_trends.py",
    )

    # 4. BASELINE LANE: 거시지표 & 21개 이슈 관심도
    collect_issue_data = BashOperator(
        task_id="collect_issue_data",
        bash_command="python /opt/airflow/scripts/collection/issue_data_collector.py --resume",
    )

    collect_financial_proxy = BashOperator(
        task_id="collect_financial_proxy",
        bash_command="python /opt/airflow/scripts/collection/fetch_financial_proxy.py",
    )

    # 5. AUTONOMOUS SCANNER: 무인 글로벌 이상징후 스캐너
    scan_autonomous_anomalies = BashOperator(
        task_id="scan_autonomous_anomalies",
        bash_command="python /opt/airflow/scripts/automation/auto_anomaly_scanner.py --dry-run",
    )

    # 수집 완료 게이트웨이
    collect_barrier = EmptyOperator(task_id="all_collections_completed")

    # --------------------------------------------------------------------------
    # STAGE 2 : 지능형 4단계 다국어 NLP 전처리 (노이즈제거, 어간/악센트, 군집화, 엔티티태깅)
    # --------------------------------------------------------------------------
    preprocess_multilingual = BashOperator(
        task_id="preprocess_multilingual_signals",
        bash_command="python /opt/airflow/scripts/automation/preprocess_signals.py",
    )

    # --------------------------------------------------------------------------
    # STAGE 3 : 복수 계통 교차검증 & LLM 담론 괴리 분석
    # --------------------------------------------------------------------------
    cross_verify_events = BashOperator(
        task_id="cross_verify_events",
        bash_command="python /opt/airflow/scripts/analysis/cross_verify_events.py",
    )

    analyze_signal_gap = BashOperator(
        task_id="analyze_signal_gap_llm",
        bash_command="python /opt/airflow/scripts/analysis/analyze_signal_gap.py",
    )

    # --------------------------------------------------------------------------
    # STAGE 4 : 결정론적 Risk Signal Score & 경보 등급 산출
    # --------------------------------------------------------------------------
    calculate_alert_scoring = BashOperator(
        task_id="calculate_alert_scoring",
        bash_command="python /opt/airflow/scripts/analysis/analyze_signals.py",
    )

    # --------------------------------------------------------------------------
    # STAGE 5 : 트랜잭션 DB 적재 & 4대 관제 뷰 동기화
    # --------------------------------------------------------------------------
    build_database = BashOperator(
        task_id="build_database_mysql",
        bash_command="python /opt/airflow/scripts/db/build_database.py",
    )

    load_cross_verification_db = BashOperator(
        task_id="load_cross_verification_to_db",
        bash_command="python /opt/airflow/scripts/db/load_cross_verification_to_db.py",
    )

    # --------------------------------------------------------------------------
    # STAGE 6 : 비상 관제 HTML 대시보드 생성 & Notion 프로젝트 허브 동기화
    # --------------------------------------------------------------------------
    generate_dashboard = BashOperator(
        task_id="generate_interactive_dashboard",
        bash_command="python /opt/airflow/scripts/dashboard/generate_dashboard_v2.py",
    )

    sync_notion_hub = BashOperator(
        task_id="sync_notion_hub",
        bash_command="python /opt/airflow/scripts/notion/notion_manager.py --all",
    )

    # ==========================================================================
    # 의존성 그래프(DAG Dependency) 정의
    # ==========================================================================
    # 1. 시작 -> 10개 수집기 동시 병렬 실행
    collectors = [
        collect_chokepoints,
        collect_gov_announcements,
        collect_whitehouse,
        collect_expert_sources,
        collect_signal_gap_rss,
        collect_local_opinions,
        collect_google_trends,
        collect_issue_data,
        collect_financial_proxy,
        scan_autonomous_anomalies,
    ]
    start_pipeline >> collectors >> collect_barrier

    # 2. 수집 완료 -> 지능형 전처리
    collect_barrier >> preprocess_multilingual

    # 3. 전처리 완료 -> 교차검증 & LLM 분석 (병렬)
    preprocess_multilingual >> [cross_verify_events, analyze_signal_gap]

    # 4. 분석 완료 -> 경보 산출
    [cross_verify_events, analyze_signal_gap] >> calculate_alert_scoring

    # 5. 경보 산출 완료 -> DB 트랜잭션 적재
    calculate_alert_scoring >> build_database >> load_cross_verification_db

    # 6. DB 적재 완료 -> 관제 대시보드 & 노션 동기화 (병렬)
    load_cross_verification_db >> [generate_dashboard, sync_notion_hub] >> end_pipeline
