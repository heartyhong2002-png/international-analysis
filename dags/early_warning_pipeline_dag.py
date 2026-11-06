"""
early_warning_pipeline_dag.py — 공급망·지정학 리스크 조기경보 Multi-Lane 오케스트레이션 DAG
===================================================================================

설계 원칙:
1. Concurrency (병렬성): 의존성이 없는 수집 레인을 병렬 실행하여 I/O 지연 단축.
2. Fault Isolation (장애 격리): 특정 수집기 장애가 전체 파이프라인 중단으로 번지지 않도록 격리.
3. Resilience (자동 재시도): 네트워크 타임아웃/일시 오류 발생 시 Exponential Backoff 기반 재시도.
4. Determinism: Alert Level 및 Anomaly Score는 검증된 산식을 거쳐 단일 출처 상승을 차단.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

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

    start_pipeline = EmptyOperator(task_id="start_pipeline")
    end_pipeline = EmptyOperator(
        task_id="end_pipeline",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    # STAGE 0 : 엣지 수집 브랜치의 최신 커밋만 흡수 (실패해도 본 수집 계속)
    sync_edge_data = BashOperator(
        task_id="sync_edge_collection_data",
        bash_command=(
            "cd /opt/airflow && "
            "git fetch origin cursor/actions-light-collection 2>/dev/null || true; "
            "git merge --ff-only FETCH_HEAD 2>/dev/null || "
            "echo 'edge sync skipped (not a git worktree or non-ff)'; "
            "true"
        ),
    )

    # STAGE 1 : 병렬 수집
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

    collect_federal_register = BashOperator(
        task_id="collect_federal_register",
        bash_command="python /opt/airflow/scripts/collection/fetch_federal_register.py",
    )

    collect_expert_sources = BashOperator(
        task_id="collect_expert_sources",
        bash_command="python /opt/airflow/scripts/analysis/prototype_local_expert_sources.py",
    )

    collect_signal_gap_rss = BashOperator(
        task_id="collect_signal_gap_rss",
        bash_command="python /opt/airflow/scripts/collection/fetch_signal_gap_rss.py",
    )

    collect_local_opinions = BashOperator(
        task_id="collect_local_opinions",
        bash_command="python /opt/airflow/scripts/collection/fetch_local_opinions.py",
    )

    collect_bluesky = BashOperator(
        task_id="collect_bluesky_public",
        bash_command="python /opt/airflow/scripts/collection/fetch_bluesky_public.py",
    )

    collect_telegram = BashOperator(
        task_id="collect_telegram_osint",
        bash_command="python /opt/airflow/scripts/collection/fetch_telegram_public.py",
    )

    collect_google_trends = BashOperator(
        task_id="collect_google_trends",
        bash_command="python /opt/airflow/scripts/collection/fetch_google_trends.py",
    )

    collect_issue_data = BashOperator(
        task_id="collect_issue_data",
        bash_command="python /opt/airflow/scripts/collection/issue_data_collector.py --resume",
    )

    collect_financial_proxy = BashOperator(
        task_id="collect_financial_proxy",
        bash_command="python /opt/airflow/scripts/collection/fetch_financial_proxy.py",
    )

    scan_autonomous_anomalies = BashOperator(
        task_id="scan_autonomous_anomalies",
        bash_command="python /opt/airflow/scripts/automation/auto_anomaly_scanner.py --dry-run",
    )

    # 하나라도 성공하면 후속 단계 진행 (전부 실패 시에만 스킵)
    collect_barrier = EmptyOperator(
        task_id="all_collections_completed",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    # STAGE 2 : 레인 브릿지 전처리 (실제 파일 I/O)
    preprocess_multilingual = BashOperator(
        task_id="preprocess_multilingual_signals",
        bash_command="python /opt/airflow/scripts/pipeline/bridge_preprocess_lanes.py",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    # STAGE 3 : 교차검증 & LLM (호스트 Ollama: OLLAMA_HOST)
    cross_verify_events = BashOperator(
        task_id="cross_verify_events",
        bash_command="python /opt/airflow/scripts/analysis/cross_verify_events.py",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    analyze_signal_gap = BashOperator(
        task_id="analyze_signal_gap_llm",
        # OLLAMA_HOST is injected by docker-compose (default host.docker.internal:11434)
        bash_command=(
            'export OLLAMA_HOST="${OLLAMA_HOST:-http://host.docker.internal:11434}"; '
            "python /opt/airflow/scripts/analysis/analyze_signal_gap.py"
        ),
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    # STAGE 4 : 경보 산출
    calculate_alert_scoring = BashOperator(
        task_id="calculate_alert_scoring",
        bash_command="python /opt/airflow/scripts/analysis/analyze_signals.py",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    # STAGE 5 : DB 적재
    build_database = BashOperator(
        task_id="build_database_mysql",
        bash_command="python /opt/airflow/scripts/db/build_database.py",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    load_cross_verification_db = BashOperator(
        task_id="load_cross_verification_to_db",
        bash_command="python /opt/airflow/scripts/db/load_cross_verification_to_db.py",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    # STAGE 6 : 대시보드 & Notion
    generate_dashboard = BashOperator(
        task_id="generate_interactive_dashboard",
        bash_command="python /opt/airflow/scripts/dashboard/generate_dashboard_v2.py",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    sync_notion_hub = BashOperator(
        task_id="sync_notion_hub",
        bash_command="python /opt/airflow/scripts/notion/notion_manager.py --all",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    collectors = [
        collect_chokepoints,
        collect_gov_announcements,
        collect_whitehouse,
        collect_federal_register,
        collect_expert_sources,
        collect_signal_gap_rss,
        collect_local_opinions,
        collect_bluesky,
        collect_telegram,
        collect_google_trends,
        collect_issue_data,
        collect_financial_proxy,
        scan_autonomous_anomalies,
    ]
    start_pipeline >> sync_edge_data >> collectors >> collect_barrier
    collect_barrier >> preprocess_multilingual
    preprocess_multilingual >> [cross_verify_events, analyze_signal_gap]
    [cross_verify_events, analyze_signal_gap] >> calculate_alert_scoring
    calculate_alert_scoring >> build_database >> load_cross_verification_db
    load_cross_verification_db >> [generate_dashboard, sync_notion_hub] >> end_pipeline
