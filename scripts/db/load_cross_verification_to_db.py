"""
load_cross_verification_to_db.py — 해협 센서 및 교차검증 데이터 MySQL 적재기
=============================================================================
이 스크립트는 data/maritime_chokepoints 및 data/event_cross_verification의
최신 산출물을 MySQL international_analysis 데이터베이스에 적재하고,
조기경보 공급망 분석 뷰(Views)를 생성·갱신합니다.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import mysql.connector

# 루트 디렉터리 및 경로 설정
ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )


def create_tables(conn):
    """공급망 해협 센서 및 교차검증 전용 베이스 테이블 생성"""
    cur = conn.cursor()

    # 1. 4대 해협 병목 상태 테이블
    cur.execute("""
    CREATE TABLE IF NOT EXISTS maritime_chokepoint_signals (
        chokepoint_code VARCHAR(30) PRIMARY KEY,
        chokepoint_name VARCHAR(100) NOT NULL,
        supply_chain_role VARCHAR(255),
        detour_delay VARCHAR(100),
        insurance_war_risk VARCHAR(100),
        threat_level VARCHAR(50),
        market_proxy_signal VARCHAR(100),
        evaluated_at DATETIME,
        source_file VARCHAR(255),
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # 2. 해상 운임·에너지 시장 프록시 시세 테이블
    cur.execute("""
    CREATE TABLE IF NOT EXISTS maritime_market_proxies (
        ticker VARCHAR(20) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        asset_type VARCHAR(50),
        price DECIMAL(12, 4),
        daily_change_pct DECIMAL(8, 2),
        monthly_change_pct DECIMAL(8, 2),
        risk_signal VARCHAR(50),
        observed_at DATETIME,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # 3. 교차검증된 공급망 사건 메인 테이블
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cross_verified_events (
        event_id VARCHAR(100) PRIMARY KEY,
        event_title VARCHAR(500) NOT NULL,
        event_summary TEXT,
        geo_country VARCHAR(100),
        event_date DATE,
        category VARCHAR(100),
        subcategory VARCHAR(100),
        source_url VARCHAR(1000),
        observed_at DATETIME,
        published_at DATETIME,
        license_note VARCHAR(255),
        is_partial_probe BOOLEAN DEFAULT TRUE,
        verification_state VARCHAR(50) NOT NULL,
        claim_status VARCHAR(50),
        distinct_channel_count INT DEFAULT 0,
        matched_channels VARCHAR(500),
        corroborations_count INT DEFAULT 0,
        alert_candidate_level VARCHAR(50) NOT NULL,
        single_source_elevate_forbidden BOOLEAN DEFAULT TRUE,
        confidence_assessment VARCHAR(255),
        verified_at DATETIME,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_ver_state (verification_state),
        INDEX idx_alert_level (alert_candidate_level),
        INDEX idx_event_date (event_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # 4. 개별 사건 결합 근거(Corroboration Evidence) 세부 테이블
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cross_verified_evidence (
        id INT AUTO_INCREMENT PRIMARY KEY,
        event_id VARCHAR(100) NOT NULL,
        channel VARCHAR(50) NOT NULL,
        source VARCHAR(100) NOT NULL,
        signal_type VARCHAR(50),
        note TEXT,
        recorded_at DATETIME,
        INDEX idx_event_id (event_id),
        INDEX idx_channel (channel)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    conn.commit()
    cur.close()
    print("  ✓ MySQL 해협 및 교차검증 테이블(4개) 생성 및 확인 완료")


def create_views(conn):
    """공급망 조기경보 전용 MySQL 분석 뷰 생성"""
    cur = conn.cursor()

    # 뷰 1: v_cross_verified_events_summary (사건 교차검증 집계 및 우선순위 뷰)
    cur.execute("""
    CREATE OR REPLACE VIEW v_cross_verified_events_summary AS
    SELECT
        e.event_id,
        e.event_title,
        e.geo_country,
        e.event_date,
        e.verification_state,
        e.alert_candidate_level,
        e.distinct_channel_count,
        e.matched_channels,
        e.confidence_assessment,
        e.source_url,
        e.is_partial_probe,
        e.observed_at,
        e.verified_at,
        COUNT(v.id) AS total_evidence_items,
        CASE
            WHEN e.alert_candidate_level = 'WARNING' AND e.verification_state = 'CROSS_VERIFIED' THEN 1
            WHEN e.alert_candidate_level = 'WATCH' THEN 2
            ELSE 3
        END AS priority_rank
    FROM cross_verified_events e
    LEFT JOIN cross_verified_evidence v ON e.event_id = v.event_id
    GROUP BY e.event_id, e.event_title, e.geo_country, e.event_date,
             e.verification_state, e.alert_candidate_level, e.distinct_channel_count,
             e.matched_channels, e.confidence_assessment, e.source_url, e.is_partial_probe,
             e.observed_at, e.verified_at
    ORDER BY priority_rank ASC, e.distinct_channel_count DESC, e.event_date DESC;
    """)

    # 뷰 2: v_chokepoint_supply_chain_radar (해협 병목 및 실시간 시장 프록시 종합 뷰)
    cur.execute("""
    CREATE OR REPLACE VIEW v_chokepoint_supply_chain_radar AS
    SELECT
        c.chokepoint_code,
        c.chokepoint_name,
        c.supply_chain_role,
        c.detour_delay,
        c.insurance_war_risk,
        c.threat_level,
        c.market_proxy_signal,
        c.evaluated_at,
        m.ticker AS related_proxy_ticker,
        m.name AS proxy_name,
        m.monthly_change_pct AS proxy_monthly_change_pct,
        m.risk_signal AS proxy_risk_signal
    FROM maritime_chokepoint_signals c
    LEFT JOIN maritime_market_proxies m ON (
        (c.chokepoint_code = 'HORMUZ' AND m.ticker = 'FRO') OR
        (c.chokepoint_code = 'BAB_EL_MANDEB' AND m.ticker = 'ZIM') OR
        (c.chokepoint_code = 'TAIWAN_STRAIT' AND m.ticker = 'BDRY')
    );
    """)

    conn.commit()
    cur.close()
    print("  ✓ MySQL 조기경보 공급망 분석 뷰(2개) 생성 및 확인 완료")


def load_maritime_data(conn):
    """data/maritime_chokepoints 데이터를 MySQL에 적재"""
    summary_path = ROOT / "data" / "maritime_chokepoints" / "maritime_summary.json"
    if not summary_path.exists():
        print("  ⚠️ maritime_summary.json 파일이 존재하지 않습니다.")
        return 0, 0

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cur = conn.cursor()

    # 1. 해협 상태 적재
    chokepoints = data.get("chokepoints_status", [])
    chokepoint_count = 0
    now_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    for c in chokepoints:
        sql = """
        INSERT INTO maritime_chokepoint_signals (
            chokepoint_code, chokepoint_name, supply_chain_role,
            detour_delay, insurance_war_risk, threat_level,
            market_proxy_signal, evaluated_at, source_file
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            chokepoint_name = VALUES(chokepoint_name),
            supply_chain_role = VALUES(supply_chain_role),
            detour_delay = VALUES(detour_delay),
            insurance_war_risk = VALUES(insurance_war_risk),
            threat_level = VALUES(threat_level),
            market_proxy_signal = VALUES(market_proxy_signal),
            evaluated_at = VALUES(evaluated_at),
            source_file = VALUES(source_file);
        """
        c_code = c.get("chokepoint_code")
        c_name = c.get("chokepoint_name_ko") or c.get("name") or c_code
        eval_at = (c.get("observed_at") or c.get("evaluated_at") or now_dt)[:19].replace("T", " ")
        threat = c.get("preliminary_chokepoint_alert") or c.get("threat_level") or "WATCH"

        cur.execute(sql, (
            c_code,
            c_name,
            c.get("supply_chain_role"),
            c.get("detour_delay"),
            c.get("insurance_war_risk"),
            threat,
            c.get("market_proxy_signal"),
            eval_at,
            "data/maritime_chokepoints/maritime_summary.json"
        ))
        chokepoint_count += 1

    # 2. 시장 프록시 적재
    proxies = data.get("market_proxies", [])
    proxy_count = 0
    for p in proxies:
        sql = """
        INSERT INTO maritime_market_proxies (
            ticker, name, asset_type, price,
            daily_change_pct, monthly_change_pct, risk_signal, observed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            asset_type = VALUES(asset_type),
            price = VALUES(price),
            daily_change_pct = VALUES(daily_change_pct),
            monthly_change_pct = VALUES(monthly_change_pct),
            risk_signal = VALUES(risk_signal),
            observed_at = VALUES(observed_at);
        """
        p_name = p.get("asset_name") or p.get("name") or p.get("ticker")
        p_type = p.get("category") or p.get("type") or "Market_Proxy"
        p_price = p.get("latest_price") or p.get("price") or 0.0
        obs_at = (p.get("observed_at") or now_dt)[:19].replace("T", " ")

        cur.execute(sql, (
            p.get("ticker"),
            p_name,
            p_type,
            p_price,
            p.get("daily_change_pct", 0.0),
            p.get("monthly_change_pct", 0.0),
            p.get("risk_signal", "NORMAL"),
            obs_at
        ))
        proxy_count += 1

    conn.commit()
    cur.close()
    print(f"  ✓ 해협 병목 상태 {chokepoint_count}건, 시장 지표 {proxy_count}건 MySQL 적재 완료")
    return chokepoint_count, proxy_count


def load_cross_verification_data(conn):
    """data/event_cross_verification 데이터를 MySQL에 적재"""
    json_path = ROOT / "data" / "event_cross_verification" / "verification_latest.json"
    if not json_path.exists():
        print("  ⚠️ verification_latest.json 파일이 존재하지 않습니다.")
        return 0, 0

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    events = data.get("verified_events", [])
    cur = conn.cursor()
    now_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    ev_count = 0
    evidence_count = 0

    # 기존 evidence 테이블 정리 (멱등성 보장)
    cur.execute("TRUNCATE TABLE cross_verified_evidence;")

    for ev in events:
        eid = ev.get("event_id")
        obs_at = ev.get("observed_at", now_dt)[:19].replace("T", " ")
        pub_at = ev.get("published_at", now_dt)[:19].replace("T", " ") if ev.get("published_at") else None
        ver_at = ev.get("verified_at", now_dt)[:19].replace("T", " ")

        # 메인 사건 적재
        sql_ev = """
        INSERT INTO cross_verified_events (
            event_id, event_title, event_summary, geo_country, event_date,
            category, subcategory, source_url, observed_at, published_at,
            license_note, is_partial_probe, verification_state, claim_status,
            distinct_channel_count, matched_channels, corroborations_count,
            alert_candidate_level, single_source_elevate_forbidden,
            confidence_assessment, verified_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s
        )
        ON DUPLICATE KEY UPDATE
            event_title = VALUES(event_title),
            event_summary = VALUES(event_summary),
            geo_country = VALUES(geo_country),
            event_date = VALUES(event_date),
            category = VALUES(category),
            subcategory = VALUES(subcategory),
            source_url = VALUES(source_url),
            observed_at = VALUES(observed_at),
            published_at = VALUES(published_at),
            license_note = VALUES(license_note),
            is_partial_probe = VALUES(is_partial_probe),
            verification_state = VALUES(verification_state),
            claim_status = VALUES(claim_status),
            distinct_channel_count = VALUES(distinct_channel_count),
            matched_channels = VALUES(matched_channels),
            corroborations_count = VALUES(corroborations_count),
            alert_candidate_level = VALUES(alert_candidate_level),
            single_source_elevate_forbidden = VALUES(single_source_elevate_forbidden),
            confidence_assessment = VALUES(confidence_assessment),
            verified_at = VALUES(verified_at);
        """

        matched_ch_str = ", ".join(ev.get("matched_channels", []))
        cur.execute(sql_ev, (
            eid,
            ev.get("event_title", "")[:500],
            ev.get("event_summary", ""),
            ev.get("geo_country", ""),
            ev.get("event_date"),
            ev.get("category", ""),
            ev.get("subcategory", ""),
            ev.get("source_url", "")[:1000],
            obs_at,
            pub_at,
            ev.get("license_note", "")[:255],
            ev.get("is_partial_probe", True),
            ev.get("verification_state", "UNVERIFIED"),
            ev.get("claim_status", "UNVERIFIED"),
            ev.get("distinct_channel_count", 0),
            matched_ch_str,
            ev.get("corroborations_count", 0),
            ev.get("alert_candidate_level", "NORMAL"),
            ev.get("single_source_elevate_forbidden", True),
            ev.get("confidence_assessment", "")[:255],
            ver_at
        ))
        ev_count += 1

        # 개별 증거 항목 적재
        for item in ev.get("corroboration_evidence", []):
            sql_evid = """
            INSERT INTO cross_verified_evidence (
                event_id, channel, source, signal_type, note, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, %s);
            """
            cur.execute(sql_evid, (
                eid,
                item.get("channel", ""),
                item.get("source", ""),
                item.get("signal_type", ""),
                item.get("note", ""),
                ver_at
            ))
            evidence_count += 1

    conn.commit()
    cur.close()
    print(f"  ✓ 교차검증 사건 {ev_count}건, 결합 증거 {evidence_count}건 MySQL 적재 완료")
    return ev_count, evidence_count


def main():
    print("=" * 65)
    print("🗄️  해협 센서 및 사건 교차검증 MySQL DB 적재 파이프라인 시작")
    print("=" * 65)

    try:
        conn = get_connection()
        print(f"  ✓ MySQL 접속 성공: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
    except Exception as e:
        print(f"  ✗ MySQL 접속 실패: {e}")
        sys.exit(1)

    try:
        create_tables(conn)
        create_views(conn)
        load_maritime_data(conn)
        load_cross_verification_data(conn)
        print("\n🎉 모든 해협 센서 및 교차검증 데이터의 MySQL 동기화가 완결되었습니다.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

