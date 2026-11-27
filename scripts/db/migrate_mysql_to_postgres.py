"""
migrate_mysql_to_postgres.py — MySQL(international_analysis) -> PostgreSQL(Docker pgvector) 이관 및 검증 스크립트
"""

import argparse
import os
import sys
from pathlib import Path

import mysql.connector
import psycopg
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).resolve().parent / "postgres_schema.sql"
load_dotenv(PROJECT_ROOT / ".env")

# Topological order respecting foreign keys
TABLE_ORDER = [
    "scoring_runs",
    "signal_gap_snapshots",
    "alert_events",
    "risk_signal_scores",
    "alert_event_evidence",
    "alert_validation_audit",
    "analysis_reports",
    "cross_verified_events",
    "cross_verified_evidence",
    "data_quality_audit",
    "expert_analysis_extractions",
    "financial_proxy",
    "fred_indicators",
    "gov_announcements",
    "imf_trade",
    "issue_gov_match",
    "issue_summary",
    "maritime_chokepoint_signals",
    "maritime_market_proxies",
    "news_data",
    "official_statement_extractions",
    "polls_data",
    "reddit_opinion",
    "rss_signal_gap",
    "sanctions",
    "telegram_osint",
    "tone_review_log",
    "us_diplomatic_statements",
    "us_macro_financial_indicators",
    "us_presidential_actions",
    "wikipedia_pageviews",
]

BOOLEAN_COLUMNS = {
    ("alert_events", "requires_human_review"),
    ("cross_verified_events", "is_partial_probe"),
    ("cross_verified_events", "single_source_elevate_forbidden"),
    ("data_quality_audit", "is_dry_run"),
}

IDENTITY_TABLES = [
    "scoring_runs",
    "signal_gap_snapshots",
    "alert_events",
    "risk_signal_scores",
    "alert_event_evidence",
    "alert_validation_audit",
    "analysis_reports",
    "cross_verified_evidence",
    "data_quality_audit",
    "expert_analysis_extractions",
    "gov_announcements",
    "news_data",
    "official_statement_extractions",
    "rss_signal_gap",
    "telegram_osint",
    "tone_review_log",
    "us_diplomatic_statements",
    "us_macro_financial_indicators",
    "us_presidential_actions",
]

VIEWS = [
    "v_alert_evidence_trace",
    "v_alert_validation_summary",
    "v_chokepoint_supply_chain_radar",
    "v_cross_verified_events_summary",
    "v_dashboard_current_alerts",
    "v_human_in_the_loop_audit",
    "v_issue_geopolitical_risk_matrix",
    "v_issue_media_framing_summary",
    "v_issue_public_vs_gov_daily",
    "v_regression_test_fixture_alerts",
    "v_regression_test_fixture_evidence",
    "v_signal_attention_gap",
    "v_signal_gap_trend",
    "v_signal_tone_gap",
]


def get_mysql_conn():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "international_analysis"),
    )


def get_pg_conn():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "intl_admin"),
        password=os.getenv("POSTGRES_PASSWORD", "intl_pg_password_2026"),
        dbname=os.getenv("POSTGRES_DATABASE", "international_analysis"),
    )


def apply_schema(pg_conn):
    sql_text = SCHEMA_PATH.read_text(encoding="utf-8")
    with pg_conn.cursor() as cur:
        cur.execute(sql_text)
    pg_conn.commit()
    print("[OK] PostgreSQL schema & 14 views applied.")


def migrate_data(mysql_conn, pg_conn, truncate_first: bool = False):
    m_cur = mysql_conn.cursor()
    with pg_conn.cursor() as p_cur:
        if truncate_first:
            tables_rev = ", ".join(reversed(TABLE_ORDER))
            p_cur.execute(f"TRUNCATE TABLE {tables_rev} RESTART IDENTITY CASCADE;")
            print("[OK] Truncated target PostgreSQL tables.")

        for table in TABLE_ORDER:
            m_cur.execute(f"SELECT * FROM `{table}`")
            rows = m_cur.fetchall()
            col_names = [desc[0] for desc in m_cur.description]

            if not rows:
                print(f"  - {table}: 0 rows (skipped)")
                continue

            bool_indices = {
                idx for idx, col in enumerate(col_names)
                if (table, col) in BOOLEAN_COLUMNS
            }

            converted_rows = []
            for row in rows:
                if bool_indices:
                    row_list = list(row)
                    for idx in bool_indices:
                        if row_list[idx] is not None:
                            row_list[idx] = bool(row_list[idx])
                    converted_rows.append(tuple(row_list))
                else:
                    converted_rows.append(row)

            cols_sql = ", ".join(f'"{c}"' for c in col_names)
            placeholders = ", ".join(["%s"] * len(col_names))
            insert_sql = (
                f'INSERT INTO "{table}" ({cols_sql}) VALUES ({placeholders}) '
                f'ON CONFLICT DO NOTHING'
            )
            p_cur.executemany(insert_sql, converted_rows)
            print(f"  - {table}: migrated {len(converted_rows):,} rows")

        for table in IDENTITY_TABLES:
            p_cur.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM "{table}"), 1),
                    (SELECT COUNT(*) > 0 FROM "{table}")
                );
                """
            )
        pg_conn.commit()
    m_cur.close()
    print("[OK] All tables migrated and identity sequences synchronized.")


def verify_counts(mysql_conn, pg_conn):
    m_cur = mysql_conn.cursor()
    p_cur = pg_conn.cursor()

    print("\n=== Verification: Base Tables (MySQL vs PostgreSQL) ===")
    mismatches = 0
    total_mysql = 0
    total_pg = 0
    for table in TABLE_ORDER:
        m_cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        m_cnt = m_cur.fetchone()[0]
        p_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        p_cnt = p_cur.fetchone()[0]
        total_mysql += m_cnt
        total_pg += p_cnt
        status = "OK" if m_cnt == p_cnt else "MISMATCH"
        if m_cnt != p_cnt:
            mismatches += 1
            print(f"  [!] {table}: MySQL={m_cnt:,} vs PG={p_cnt:,}")

    print(f"Total Base Rows: MySQL={total_mysql:,}, PostgreSQL={total_pg:,}, Mismatches={mismatches}")

    print("\n=== Verification: Views (MySQL vs PostgreSQL) ===")
    view_errors = 0
    for view in VIEWS:
        m_cur.execute(f"SELECT COUNT(*) FROM `{view}`")
        m_cnt = m_cur.fetchone()[0]
        try:
            p_cur.execute(f'SELECT COUNT(*) FROM "{view}"')
            p_cnt = p_cur.fetchone()[0]
            mark = "OK" if m_cnt == p_cnt else "DIFF"
            print(f"  [{mark}] {view}: MySQL={m_cnt:,}, PG={p_cnt:,}")
        except Exception as exc:
            view_errors += 1
            pg_conn.rollback()
            print(f"  [ERR] {view}: {exc}")

    p_cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
    vec = p_cur.fetchone()
    print(f"\n[pgvector] extension version: {vec[0] if vec else 'NOT INSTALLED'}")

    m_cur.close()
    p_cur.close()
    return mismatches == 0 and view_errors == 0


def main():
    parser = argparse.ArgumentParser(description="Migrate MySQL data to PostgreSQL")
    parser.add_argument("--truncate", action="store_true", help="Truncate PostgreSQL tables before migrating")
    parser.add_argument("--verify-only", action="store_true", help="Only verify row counts")
    args = parser.parse_args()

    mysql_conn = get_mysql_conn()
    pg_conn = get_pg_conn()
    try:
        if not args.verify_only:
            apply_schema(pg_conn)
            migrate_data(mysql_conn, pg_conn, truncate_first=args.truncate)
        ok = verify_counts(mysql_conn, pg_conn)
        if not ok:
            sys.exit(1)
    finally:
        mysql_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
