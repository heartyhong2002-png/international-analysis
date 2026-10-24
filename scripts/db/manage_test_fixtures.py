"""Create / verify / cleanup TEST-FIXTURE-* synthetic evidence rows.

Operational and official views exclude TEST-* run keys and TEST_* issue keys.
This script only touches synthetic fixture rows — never production issues.

Commands:
  python scripts/db/manage_test_fixtures.py status
  python scripts/db/manage_test_fixtures.py seed --run-key TEST-FIXTURE-20261010-00000001
  python scripts/db/manage_test_fixtures.py cleanup --run-key TEST-FIXTURE-20261010-00000001 --yes
  python scripts/db/manage_test_fixtures.py verify-exclusion
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Allow `python scripts/db/manage_test_fixtures.py` imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db_connection import (
    TEST_FIXTURE_RUN_KEY_PREFIX,
    TEST_RUN_KEY_PREFIX,
    TEST_SCORING_VERSION,
    get_connection,
    is_test_run_key,
)
from evidence_writer import (
    AlertEventInput,
    EvidenceInput,
    RiskScoreInput,
    ScoringBundle,
    SignalGapInput,
    ValidationJudgmentInput,
    write_scoring_bundle,
)

CANONICAL_RUN_KEY = "TEST-FIXTURE-20261010-00000001"
EXECUTED_AT = datetime(2026, 10, 10, 9, 0, 0)
WINDOW_START = datetime(2026, 10, 3, 0, 0, 0)
WINDOW_END = EXECUTED_AT

# Matches the handoff fixture: 1 run · 3 alerts · 6 evidence · 3 gaps · 3 audits
# and 9 score components (3 families × 3 issues).
FIXTURE_ISSUES = [
    {
        "issue_key": "TEST_HORMUZ",
        "alert_level": "WARNING",
        "verdict": "confirmed",
        "evidence_sufficiency": "sufficient",
        "scores": [
            ("official", "official_response", 16.2, 2, 0.82),
            ("independent", "independent_reporting", 18.0, 2, 0.82),
            ("market", "market_proxy", 16.2, 2, 0.82),
        ],
        "gap": (65.0, 72.0, 81.0, 74.0, 76.0, 85.0),
        "evidence_pairs": [("official", "supporting"), ("independent", "corroborating")],
    },
    {
        "issue_key": "TEST_TAIWAN",
        "alert_level": "WATCH",
        "verdict": "pending_review",
        "evidence_sufficiency": "pending",
        "scores": [
            ("official", "official_response", 9.6, 1, 0.82),
            ("independent", "independent_reporting", 14.25, 1, 0.82),
            ("market", "market_proxy", 10.2, 1, 0.82),
        ],
        "gap": (48.0, 57.0, 62.0, 51.0, 61.0, 60.0),
        "evidence_pairs": [("official", "supporting"), ("independent", "corroborating")],
    },
    {
        "issue_key": "TEST_REDSEA",
        "alert_level": "WATCH",
        "verdict": "false_alarm",
        "evidence_sufficiency": "pending",
        "scores": [
            ("official", "official_response", 5.8, 1, 0.65),
            ("independent", "independent_reporting", 8.75, 1, 0.65),
            ("market", "market_proxy", 6.0, 1, 0.65),
        ],
        "gap": (29.0, 35.0, 40.0, 30.0, 45.0, 60.0),
        "evidence_pairs": [("official", "supporting"), ("independent", "corroborating")],
    },
]


def build_canonical_bundle(run_key: str = CANONICAL_RUN_KEY) -> ScoringBundle:
    if not is_test_run_key(run_key):
        raise ValueError(f"fixture run_key must start with {TEST_RUN_KEY_PREFIX}")
    if len(run_key) > 36:
        raise ValueError("run_key must be <= 36 characters")

    scores: list[RiskScoreInput] = []
    gaps: list[SignalGapInput] = []
    alerts: list[AlertEventInput] = []
    judgments: list[ValidationJudgmentInput] = []

    for spec in FIXTURE_ISSUES:
        issue = spec["issue_key"]
        for family, metric, contribution, evidence_count, confidence in spec["scores"]:
            scores.append(
                RiskScoreInput(
                    issue_key=issue,
                    signal_family=family,
                    metric_name=metric,
                    observed_at=EXECUTED_AT,
                    contribution_score=contribution,
                    evidence_count=evidence_count,
                    confidence_score=confidence,
                    quality_status="usable",
                    component_key=f"{issue}|{family}|{metric}",
                    evidence_summary="Synthetic fixture score component; not operational.",
                )
            )
        off, ind, pub, mkt, gap, cov = spec["gap"]
        gaps.append(
            SignalGapInput(
                issue_key=issue,
                snapshot_at=EXECUTED_AT,
                official_score=off,
                independent_score=ind,
                public_score=pub,
                market_score=mkt,
                gap_score=gap,
                evidence_coverage_pct=cov,
                source_diversity=3,
                methodology_version="gap-method-test-v1",
                narrative_summary="Synthetic fixture gap snapshot; not an operational finding.",
            )
        )
        evidence_rows = []
        for family, role in spec["evidence_pairs"]:
            metric = next(m for f, m, *_ in spec["scores"] if f == family)
            evidence_rows.append(
                EvidenceInput(
                    evidence_role=role,
                    source_table="TEST_FIXTURE",
                    source_record_key=f"TEST-{issue}-{family}",
                    source_url=f"https://example.invalid/test-fixture/{issue}/{family}",
                    evidence_quote=f"Synthetic {family}-source quote for traceability test.",
                    relevance_score=0.9,
                    observed_at=EXECUTED_AT,
                    content_hash=f"sha256:test-{issue.lower()}-{family}",
                    score_component_key=f"{issue}|{family}|{metric}",
                )
            )
        local_alert = f"{issue}|raised"
        alerts.append(
            AlertEventInput(
                issue_key=issue,
                event_type="raised",
                alert_level=spec["alert_level"],
                decision_rationale=(
                    "Synthetic fixture alert for DB traceability testing; "
                    "do not interpret as a live alert."
                ),
                lifecycle_status="active",
                triggered_at=EXECUTED_AT,
                requires_human_review=True,
                evidence=evidence_rows,
                local_key=local_alert,
            )
        )
        judgments.append(
            ValidationJudgmentInput(
                issue_key=issue,
                audit_type="fixture_review",
                verdict=spec["verdict"],
                expected_alert_level=spec["alert_level"],
                observed_outcome="synthetic_fixture_outcome",
                validation_window_start=EXECUTED_AT,
                validation_window_end=EXECUTED_AT,
                reviewer="fixture-reviewer",
                reviewed_at=EXECUTED_AT,
                evidence_sufficiency=spec["evidence_sufficiency"],
                rationale="Synthetic validation row for view testing; not a real evaluation.",
                reference_url=f"https://example.invalid/test-fixture/{issue}",
                source_key=f"fixture:{run_key}:{issue}",
                alert_local_key=local_alert,
            )
        )

    return ScoringBundle(
        run_key=run_key,
        scoring_version=TEST_SCORING_VERSION,
        config_hash="sha256:test-fixture-config",
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        executed_at=EXECUTED_AT,
        status="completed",
        notes="Synthetic DB/validation fixture; not an operational alert run.",
        scores=scores,
        gaps=gaps,
        alerts=alerts,
        judgments=judgments,
    )


def _count_for_run(cur, run_id: int) -> dict[str, int]:
    out = {"scoring_runs": 1}
    for table, col in [
        ("risk_signal_scores", "scoring_run_id"),
        ("signal_gap_snapshots", "scoring_run_id"),
        ("alert_events", "scoring_run_id"),
    ]:
        cur.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE {col} = %s", (run_id,))
        out[table] = int(cur.fetchone()["c"])
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM alert_event_evidence e
        JOIN alert_events a ON a.id = e.alert_event_id
        WHERE a.scoring_run_id = %s
        """,
        (run_id,),
    )
    out["alert_event_evidence"] = int(cur.fetchone()["c"])
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM alert_validation_audit v
        JOIN alert_events a ON a.id = v.alert_event_id
        WHERE a.scoring_run_id = %s
        """,
        (run_id,),
    )
    out["alert_validation_audit"] = int(cur.fetchone()["c"])
    return out


def cmd_status(run_key: str) -> int:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, run_key, scoring_version, status, notes FROM scoring_runs WHERE run_key = %s",
        (run_key,),
    )
    row = cur.fetchone()
    if not row:
        print(f"fixture not found: {run_key}")
        conn.close()
        return 1
    counts = _count_for_run(cur, int(row["id"]))
    print("fixture present:")
    print(dict(row))
    print("counts:", counts)
    conn.close()
    return 0


def cmd_seed(run_key: str, force: bool) -> int:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM scoring_runs WHERE run_key = %s", (run_key,))
    existing = cur.fetchone()
    if existing and not force:
        print(f"fixture already exists (id={existing['id']}). Use --force to recreate.")
        print("Recreate = TEST-only cleanup then seed. No operational rows touched.")
        conn.close()
        return 0
    if existing and force:
        print(f"force recreate: cleaning TEST run {run_key}")
        _cleanup_run(conn, run_key, confirm=True)
    bundle = build_canonical_bundle(run_key)
    result = write_scoring_bundle(conn, bundle)
    print("seeded fixture:", result.run_key, "scoring_run_id=", result.scoring_run_id)
    print(
        "counts:",
        {
            "scores": len(result.score_ids),
            "gaps": len(result.gap_ids),
            "alerts": len(result.alert_ids),
            "evidence": len(result.evidence_ids),
            "judgments": len(result.judgment_ids),
        },
    )
    conn.close()
    return 0


def _cleanup_run(conn, run_key: str, confirm: bool) -> None:
    if not is_test_run_key(run_key):
        raise RuntimeError("refusing cleanup: run_key is not a TEST-* fixture key")
    if not confirm:
        raise RuntimeError("cleanup requires --yes")

    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM scoring_runs WHERE run_key = %s", (run_key,))
        row = cur.fetchone()
        if not row:
            print(f"nothing to cleanup for {run_key}")
            return
        run_id = int(row["id"])

        # Safety: refuse if any non-TEST issue is linked to this run.
        cur.execute(
            """
            SELECT DISTINCT issue_key FROM (
                SELECT issue_key FROM risk_signal_scores WHERE scoring_run_id = %s
                UNION
                SELECT issue_key FROM signal_gap_snapshots WHERE scoring_run_id = %s
                UNION
                SELECT issue_key FROM alert_events WHERE scoring_run_id = %s
            ) x
            WHERE issue_key NOT LIKE 'TEST\\_%' ESCAPE '\\\\'
            """,
            (run_id, run_id, run_id),
        )
        bad = cur.fetchall()
        if bad:
            raise RuntimeError(
                f"refusing cleanup: non-TEST issue keys linked to run: {[r['issue_key'] for r in bad]}"
            )

        cur.execute(
            "SELECT id FROM alert_events WHERE scoring_run_id = %s",
            (run_id,),
        )
        alert_ids = [int(r["id"]) for r in cur.fetchall()]
        if alert_ids:
            placeholders = ",".join(["%s"] * len(alert_ids))
            # TEST fixture audits only — append-only exception scoped to fixtures.
            cur.execute(
                f"DELETE FROM alert_validation_audit WHERE alert_event_id IN ({placeholders})",
                alert_ids,
            )
            cur.execute(
                f"DELETE FROM alert_event_evidence WHERE alert_event_id IN ({placeholders})",
                alert_ids,
            )
            cur.execute(
                f"DELETE FROM alert_events WHERE id IN ({placeholders})",
                alert_ids,
            )
        cur.execute("DELETE FROM risk_signal_scores WHERE scoring_run_id = %s", (run_id,))
        cur.execute("DELETE FROM signal_gap_snapshots WHERE scoring_run_id = %s", (run_id,))
        cur.execute(
            "DELETE FROM alert_validation_audit WHERE source_key LIKE %s",
            (f"fixture:{run_key}:%",),
        )
        cur.execute("DELETE FROM scoring_runs WHERE id = %s", (run_id,))
        conn.commit()
        print(f"cleaned TEST fixture run_key={run_key} id={run_id}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def cmd_cleanup(run_key: str, yes: bool) -> int:
    conn = get_connection()
    try:
        _cleanup_run(conn, run_key, confirm=yes)
    finally:
        conn.close()
    return 0


def _view_columns(cur, view: str) -> set[str]:
    cur.execute(
        """
        SELECT COLUMN_NAME AS name
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (view,),
    )
    return {r["name"] for r in cur.fetchall()}


def cmd_verify_exclusion() -> int:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    views = [
        "v_dashboard_current_alerts",
        "v_alert_evidence_trace",
        "v_signal_gap_trend",
        "v_alert_validation_summary",
    ]
    ok = True
    for view in views:
        cols = _view_columns(cur, view)
        if "issue_key" in cols:
            cur.execute(
                f"SELECT COUNT(*) AS c FROM {view} WHERE issue_key LIKE 'TEST\\_%' ESCAPE '\\\\'"
            )
            leaked = int(cur.fetchone()["c"])
            print(f"{view}: TEST issue rows visible = {leaked}")
            if leaked:
                ok = False
        if "run_key" in cols:
            cur.execute(
                f"SELECT COUNT(*) AS c FROM {view} WHERE run_key LIKE %s",
                (f"{TEST_RUN_KEY_PREFIX}%",),
            )
            leaked_run = int(cur.fetchone()["c"])
            print(f"{view}: TEST run_key rows visible = {leaked_run}")
            if leaked_run:
                ok = False
        else:
            print(f"{view}: run_key column not present (skipped)")

    for view in [
        "v_regression_test_fixture_alerts",
        "v_regression_test_fixture_evidence",
    ]:
        cur.execute(f"SELECT COUNT(*) AS c FROM {view}")
        print(f"{view}: {cur.fetchone()['c']} rows")

    cur.execute(
        "SELECT COUNT(*) AS c FROM scoring_runs WHERE run_key LIKE %s",
        (f"{TEST_FIXTURE_RUN_KEY_PREFIX}%",),
    )
    print("TEST-FIXTURE scoring_runs:", cur.fetchone()["c"])
    conn.close()
    return 0 if ok else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage TEST-FIXTURE evidence rows")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Show fixture row counts")
    p_status.add_argument("--run-key", default=CANONICAL_RUN_KEY)

    p_seed = sub.add_parser("seed", help="Create canonical synthetic fixture")
    p_seed.add_argument("--run-key", default=CANONICAL_RUN_KEY)
    p_seed.add_argument(
        "--force",
        action="store_true",
        help="TEST-only recreate (cleanup then seed). Never touches non-TEST rows.",
    )

    p_cleanup = sub.add_parser("cleanup", help="Delete ONE TEST-* fixture run only")
    p_cleanup.add_argument("--run-key", default=CANONICAL_RUN_KEY)
    p_cleanup.add_argument("--yes", action="store_true", help="Confirm TEST-only delete")

    sub.add_parser("verify-exclusion", help="Confirm operational views hide TEST rows")

    args = parser.parse_args(argv)
    if args.command == "status":
        return cmd_status(args.run_key)
    if args.command == "seed":
        return cmd_seed(args.run_key, force=args.force)
    if args.command == "cleanup":
        if not args.yes:
            print("Refusing cleanup without --yes (TEST-only delete still requires explicit confirm).")
            return 2
        return cmd_cleanup(args.run_key, yes=True)
    if args.command == "verify-exclusion":
        return cmd_verify_exclusion()
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
