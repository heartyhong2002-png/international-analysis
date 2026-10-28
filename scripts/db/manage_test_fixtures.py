"""
manage_test_fixtures.py — TEST fixture 생성/검증/정리 + 운영 조회 제외
======================================================================

합성 fixture run_key: TEST-FIXTURE-20261010-00000001
scoring_version: test-fixture-v1
issue_key: TEST_*

운영 대시보드/성과 뷰는 create_views.sql에서 fixture를 제외한다.
이 스크립트는 베이스 테이블로 회귀 검증하고, 정리 시 data_quality_audit에 남긴다.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from evidence_writer import (
    AlertInput,
    EvidenceInput,
    RiskScoreInput,
    ScoringRunPayload,
    SignalGapInput,
    ValidationInput,
    get_connection,
    save_scoring_run,
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FIXTURE_RUN_KEY = "TEST-FIXTURE-20261010-00000001"
FIXTURE_VERSION = "test-fixture-v1"
FIXTURE_EXECUTED_AT = "2026-10-10T09:00:00"


def build_fixture_payload() -> ScoringRunPayload:
    ts = FIXTURE_EXECUTED_AT
    scores = [
        RiskScoreInput(
            issue_key="TEST_HORMUZ",
            signal_family="official",
            metric_name="statement_intensity",
            observed_at=ts,
            raw_value=0.7,
            normalized_score=0.7,
            weight=0.3,
            contribution_score=0.21,
            confidence_score=0.8,
            evidence_count=2,
            evidence_summary="fixture official",
        ),
        RiskScoreInput(
            issue_key="TEST_HORMUZ",
            signal_family="market",
            metric_name="freight_spike",
            observed_at=ts,
            raw_value=0.9,
            normalized_score=0.9,
            weight=0.4,
            contribution_score=0.36,
            confidence_score=0.75,
            evidence_count=1,
            evidence_summary="fixture market",
        ),
        RiskScoreInput(
            issue_key="TEST_TAIWAN",
            signal_family="independent",
            metric_name="local_media_surge",
            observed_at=ts,
            raw_value=0.55,
            normalized_score=0.55,
            weight=0.5,
            contribution_score=0.275,
            confidence_score=0.7,
            evidence_count=2,
        ),
        RiskScoreInput(
            issue_key="TEST_REDSEA",
            signal_family="public",
            metric_name="search_interest",
            observed_at=ts,
            raw_value=0.4,
            normalized_score=0.4,
            weight=0.4,
            contribution_score=0.16,
            confidence_score=0.6,
            evidence_count=1,
        ),
    ]
    gaps = [
        SignalGapInput(
            issue_key="TEST_HORMUZ",
            snapshot_at=ts,
            methodology_version="fixture-gap-v1",
            official_score=0.7,
            independent_score=0.5,
            public_score=0.4,
            market_score=0.9,
            gap_score=0.35,
            evidence_coverage_pct=80.0,
            source_diversity=3,
            narrative_summary="fixture hormuz gap",
        ),
        SignalGapInput(
            issue_key="TEST_TAIWAN",
            snapshot_at=ts,
            methodology_version="fixture-gap-v1",
            official_score=0.3,
            independent_score=0.55,
            public_score=0.4,
            market_score=0.2,
            gap_score=0.25,
            evidence_coverage_pct=60.0,
            source_diversity=2,
            narrative_summary="fixture taiwan gap",
        ),
        SignalGapInput(
            issue_key="TEST_REDSEA",
            snapshot_at=ts,
            methodology_version="fixture-gap-v1",
            official_score=0.2,
            independent_score=0.3,
            public_score=0.4,
            market_score=0.35,
            gap_score=0.15,
            evidence_coverage_pct=50.0,
            source_diversity=2,
            narrative_summary="fixture redsea gap",
        ),
    ]
    alerts = [
        AlertInput(
            issue_key="TEST_HORMUZ",
            event_type="raised",
            alert_level="WARNING",
            triggered_at=ts,
            lifecycle_status="active",
            decision_rationale="Synthetic fixture WARNING for view regression.",
            evidence=[
                EvidenceInput(
                    risk_score_ref="TEST_HORMUZ|market|freight_spike",
                    source_table="fixture",
                    source_record_key="hormuz-1",
                    source_url="https://example.invalid/fixture/hormuz",
                    evidence_quote="fixture quote hormuz",
                    evidence_role="primary",
                    observed_at=ts,
                )
            ],
        ),
        AlertInput(
            issue_key="TEST_TAIWAN",
            event_type="raised",
            alert_level="WATCH",
            triggered_at=ts,
            lifecycle_status="active",
            decision_rationale="Synthetic fixture WATCH for view regression.",
            evidence=[
                EvidenceInput(
                    risk_score_ref="TEST_TAIWAN|independent|local_media_surge",
                    source_table="fixture",
                    source_record_key="taiwan-1",
                    source_url="https://example.invalid/fixture/taiwan",
                    evidence_quote="fixture quote taiwan",
                    observed_at=ts,
                )
            ],
        ),
        AlertInput(
            issue_key="TEST_REDSEA",
            event_type="raised",
            alert_level="WATCH",
            triggered_at=ts,
            lifecycle_status="active",
            decision_rationale="Synthetic fixture WATCH / false_alarm path.",
            evidence=[
                EvidenceInput(
                    risk_score_ref="TEST_REDSEA|public|search_interest",
                    source_table="fixture",
                    source_record_key="redsea-1",
                    source_url="https://example.invalid/fixture/redsea",
                    evidence_quote="fixture quote redsea",
                    observed_at=ts,
                )
            ],
        ),
    ]
    validations = [
        ValidationInput(
            issue_key="TEST_HORMUZ",
            audit_type="fixture_review",
            verdict="confirmed",
            reviewed_at=ts,
            rationale="Synthetic confirmed fixture review.",
            reviewer="fixture-reviewer",
            expected_alert_level="WARNING",
        ),
        ValidationInput(
            issue_key="TEST_TAIWAN",
            audit_type="fixture_review",
            verdict="pending_review",
            reviewed_at=ts,
            rationale="Synthetic pending fixture review.",
            reviewer="fixture-reviewer",
            expected_alert_level="WATCH",
        ),
        ValidationInput(
            issue_key="TEST_REDSEA",
            audit_type="fixture_review",
            verdict="false_alarm",
            reviewed_at=ts,
            rationale="Synthetic false_alarm fixture review.",
            reviewer="fixture-reviewer",
            expected_alert_level="WATCH",
        ),
    ]
    return ScoringRunPayload(
        run_key=FIXTURE_RUN_KEY,
        scoring_version=FIXTURE_VERSION,
        executed_at=ts,
        config_hash="0" * 64,
        status="completed",
        notes="Synthetic DB/validation fixture; not an operational alert run.",
        scores=scores,
        gaps=gaps,
        alerts=alerts,
        validations=validations,
    )


def status_report() -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, run_key, scoring_version, status, executed_at
            FROM scoring_runs
            WHERE run_key = %s OR scoring_version = %s
            """,
            (FIXTURE_RUN_KEY, FIXTURE_VERSION),
        )
        runs = cur.fetchall()
        cur.execute(
            """
            SELECT id, issue_key, alert_level, lifecycle_status
            FROM alert_events
            WHERE issue_key LIKE 'TEST\\_%' ESCAPE '\\\\'
            """
        )
        alerts = cur.fetchall()
        cur.execute(
            """
            SELECT COUNT(*) FROM v_dashboard_current_alerts
            WHERE issue_key LIKE 'TEST\\_%' ESCAPE '\\\\'
               OR scoring_version = %s
            """,
            (FIXTURE_VERSION,),
        )
        dash_fixture = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(*) FROM v_alert_validation_summary
            WHERE issue_key LIKE 'TEST\\_%' ESCAPE '\\\\'
            """
        )
        val_fixture = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(*) FROM scoring_runs
            WHERE NOT (run_key LIKE 'TEST-FIXTURE%%' OR scoring_version = %s)
            """,
            (FIXTURE_VERSION,),
        )
        ops_runs = cur.fetchone()[0]
        return {
            "fixture_runs": [
                {
                    "id": r[0],
                    "run_key": r[1],
                    "scoring_version": r[2],
                    "status": r[3],
                    "executed_at": str(r[4]),
                }
                for r in runs
            ],
            "fixture_alerts": [
                {"id": a[0], "issue_key": a[1], "alert_level": a[2], "lifecycle_status": a[3]}
                for a in alerts
            ],
            "ops_scoring_runs": ops_runs,
            "dashboard_view_fixture_rows": dash_fixture,
            "validation_summary_fixture_rows": val_fixture,
            "ops_exclusion_ok": dash_fixture == 0 and val_fixture == 0,
        }
    finally:
        cur.close()
        conn.close()


def verify_fixture_base_tables() -> Dict[str, Any]:
    """공식 뷰는 fixture를 제외하므로, 회귀는 베이스 테이블로 확인한다."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM scoring_runs WHERE run_key = %s", (FIXTURE_RUN_KEY,))
        run = cur.fetchone()
        if not run:
            return {"ok": False, "reason": "fixture run missing"}
        rid = run["id"]
        cur.execute("SELECT COUNT(*) AS c FROM risk_signal_scores WHERE scoring_run_id = %s", (rid,))
        scores = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM signal_gap_snapshots WHERE scoring_run_id = %s", (rid,))
        gaps = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM alert_events WHERE scoring_run_id = %s", (rid,))
        alerts = cur.fetchone()["c"]
        cur.execute(
            """
            SELECT COUNT(*) AS c FROM alert_event_evidence e
            JOIN alert_events a ON a.id = e.alert_event_id
            WHERE a.scoring_run_id = %s
            """,
            (rid,),
        )
        evidence = cur.fetchone()["c"]
        cur.execute(
            """
            SELECT COUNT(*) AS c FROM alert_validation_audit
            WHERE audit_type = 'fixture_review' AND issue_key LIKE 'TEST\\_%' ESCAPE '\\\\'
            """
        )
        audits = cur.fetchone()["c"]
        ok = scores >= 3 and gaps >= 3 and alerts >= 3 and evidence >= 3 and audits >= 3
        return {
            "ok": ok,
            "scoring_run_id": rid,
            "scores": scores,
            "gaps": gaps,
            "alerts": alerts,
            "evidence": evidence,
            "fixture_audits": audits,
        }
    finally:
        cur.close()
        conn.close()


def ensure_fixture(*, dry_run: bool = False) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM scoring_runs WHERE run_key = %s", (FIXTURE_RUN_KEY,))
        hit = cur.fetchone()
        if hit:
            return {"action": "exists", "scoring_run_id": hit[0], "run_key": FIXTURE_RUN_KEY}
    finally:
        cur.close()
        conn.close()

    payload = build_fixture_payload()
    if dry_run:
        return {"action": "would_create", "run_key": FIXTURE_RUN_KEY}
    result = save_scoring_run(payload)
    return {"action": "created", **{k: result[k] for k in result if k != "views"}}


def cleanup_fixture(*, dry_run: bool = True, executed_by: str = "manage_test_fixtures") -> Dict[str, Any]:
    """
    TEST fixture만 제거. 운영 alert_events는 건드리지 않는다.
    기본은 dry-run. 실제 삭제는 --execute + data_quality_audit 기록.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM scoring_runs WHERE run_key = %s OR scoring_version = %s",
            (FIXTURE_RUN_KEY, FIXTURE_VERSION),
        )
        run_ids = [r[0] for r in cur.fetchall()]
        if not run_ids:
            return {"action": "noop", "reason": "no fixture runs"}

        placeholders = ",".join(["%s"] * len(run_ids))
        cur.execute(
            f"SELECT id FROM alert_events WHERE scoring_run_id IN ({placeholders})",
            tuple(run_ids),
        )
        alert_ids = [r[0] for r in cur.fetchall()]

        counts = {}
        if alert_ids:
            aph = ",".join(["%s"] * len(alert_ids))
            cur.execute(
                f"SELECT COUNT(*) FROM alert_event_evidence WHERE alert_event_id IN ({aph})",
                tuple(alert_ids),
            )
            counts["alert_event_evidence"] = cur.fetchone()[0]
            cur.execute(
                f"SELECT COUNT(*) FROM alert_validation_audit WHERE alert_event_id IN ({aph})",
                tuple(alert_ids),
            )
            counts["alert_validation_audit_linked"] = cur.fetchone()[0]
        else:
            counts["alert_event_evidence"] = 0
            counts["alert_validation_audit_linked"] = 0

        cur.execute(
            f"SELECT COUNT(*) FROM risk_signal_scores WHERE scoring_run_id IN ({placeholders})",
            tuple(run_ids),
        )
        counts["risk_signal_scores"] = cur.fetchone()[0]
        cur.execute(
            f"SELECT COUNT(*) FROM signal_gap_snapshots WHERE scoring_run_id IN ({placeholders})",
            tuple(run_ids),
        )
        counts["signal_gap_snapshots"] = cur.fetchone()[0]
        counts["alert_events"] = len(alert_ids)
        counts["scoring_runs"] = len(run_ids)

        cur.execute(
            """
            SELECT COUNT(*) FROM alert_validation_audit
            WHERE audit_type = 'fixture_review'
              AND issue_key LIKE 'TEST\\_%' ESCAPE '\\\\'
            """
        )
        counts["fixture_review_audits"] = cur.fetchone()[0]

        reason = (
            "Remove synthetic TEST fixture only; not an operational evidence purge. "
            f"run_ids={run_ids}"
        )
        cur.execute(
            """
            INSERT INTO data_quality_audit (
                action_type, target_table, affected_record_ids, affected_row_count,
                reason, backup_path, is_dry_run, executed_by
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                "cleanup_test_fixture",
                "scoring_runs,alert_events,alert_validation_audit",
                json.dumps({"scoring_run_ids": run_ids, "alert_event_ids": alert_ids}),
                sum(counts.values()),
                reason,
                None,
                bool(dry_run),
                executed_by,
            ),
        )

        if dry_run:
            conn.commit()
            return {"action": "dry_run", "counts": counts, "run_ids": run_ids, "alert_ids": alert_ids}

        # Child rows first. alert_event_evidence cascades from alert_events.
        if alert_ids:
            aph = ",".join(["%s"] * len(alert_ids))
            cur.execute(
                f"DELETE FROM alert_validation_audit WHERE alert_event_id IN ({aph})",
                tuple(alert_ids),
            )
            cur.execute(
                f"DELETE FROM alert_events WHERE id IN ({aph})",
                tuple(alert_ids),
            )
        cur.execute(
            """
            DELETE FROM alert_validation_audit
            WHERE audit_type = 'fixture_review'
              AND issue_key LIKE 'TEST\\_%' ESCAPE '\\\\'
            """
        )
        cur.execute(
            f"DELETE FROM risk_signal_scores WHERE scoring_run_id IN ({placeholders})",
            tuple(run_ids),
        )
        cur.execute(
            f"DELETE FROM signal_gap_snapshots WHERE scoring_run_id IN ({placeholders})",
            tuple(run_ids),
        )
        cur.execute(
            f"DELETE FROM scoring_runs WHERE id IN ({placeholders})",
            tuple(run_ids),
        )
        conn.commit()
        return {"action": "deleted", "counts": counts, "run_ids": run_ids, "alert_ids": alert_ids}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def query_official_views() -> Dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    out = {}
    try:
        for view in (
            "v_dashboard_current_alerts",
            "v_alert_evidence_trace",
            "v_signal_gap_trend",
            "v_alert_validation_summary",
        ):
            cur.execute(f"SELECT COUNT(*) FROM {view}")
            out[view] = cur.fetchone()[0]
        return out
    finally:
        cur.close()
        conn.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Manage TEST early-warning fixtures")
    parser.add_argument(
        "command",
        choices=["status", "ensure", "verify", "cleanup", "views"],
        help="status|ensure|verify|cleanup|views",
    )
    parser.add_argument("--dry-run", action="store_true", help="For ensure/cleanup")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete fixture on cleanup (default is dry-run)",
    )
    args = parser.parse_args(argv)

    if args.command == "status":
        print(json.dumps(status_report(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "ensure":
        print(json.dumps(ensure_fixture(dry_run=args.dry_run), ensure_ascii=False, indent=2, default=str))
        return 0
    if args.command == "verify":
        base = verify_fixture_base_tables()
        st = status_report()
        print(json.dumps({"base": base, "status": st}, ensure_ascii=False, indent=2))
        return 0 if base.get("ok") and st.get("ops_exclusion_ok") else 1
    if args.command == "cleanup":
        dry = not args.execute
        if args.dry_run:
            dry = True
        print(json.dumps(cleanup_fixture(dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if args.command == "views":
        print(json.dumps(query_official_views(), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
