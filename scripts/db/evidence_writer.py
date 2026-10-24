"""Atomic early-warning evidence writer.

Persists one scoring bundle in a single transaction:
  scoring_runs → risk_signal_scores → signal_gap_snapshots
  → alert_events → alert_event_evidence → alert_validation_audit

Hard rules:
  - Never invent Alert Level from article counts; callers must supply
    explicit alert events (or omit them).
  - alert_events / alert_validation_audit are append-only (no UPDATE/DELETE).
  - REPLACE INTO is forbidden for this evidence layer.
  - TEST fixtures use run_key prefix TEST- / issue_key prefix TEST_.

Usage (library):
    from scripts.db.evidence_writer import ScoringBundle, write_scoring_bundle

CLI smoke (dry structure check only unless --commit):
    python scripts/db/evidence_writer.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mysql.connector import Error as MySQLError

try:
    from db_connection import (
        TEST_RUN_KEY_PREFIX,
        get_connection,
        is_test_issue_key,
        is_test_run_key,
    )
except ImportError:  # pragma: no cover - script/package dual import
    from scripts.db.db_connection import (  # type: ignore
        TEST_RUN_KEY_PREFIX,
        get_connection,
        is_test_issue_key,
        is_test_run_key,
    )

ALLOWED_ALERT_LEVELS = frozenset({"WATCH", "WARNING", "CRITICAL"})
ALLOWED_LIFECYCLE = frozenset({"active", "resolved", "superseded", "held_for_review"})
ALLOWED_EVENT_TYPES = frozenset({"raised", "level_changed", "resolved", "superseded"})
ALLOWED_VERDICTS = frozenset(
    {
        "confirmed",
        "false_alarm",
        "missed_signal",
        "insufficient_evidence",
        "pending_review",
    }
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_naive_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass
class RiskScoreInput:
    issue_key: str
    signal_family: str
    metric_name: str
    observed_at: datetime | str | None = None
    raw_value: float | None = None
    baseline_value: float | None = None
    normalized_score: float | None = None
    weight: float | None = None
    contribution_score: float | None = None
    confidence_score: float | None = None
    evidence_count: int = 0
    freshness_hours: float | None = None
    quality_status: str = "usable"
    evidence_summary: str | None = None
    # Local key used to attach evidence rows before DB ids exist.
    component_key: str | None = None


@dataclass
class SignalGapInput:
    issue_key: str
    snapshot_at: datetime | str | None = None
    official_score: float | None = None
    independent_score: float | None = None
    public_score: float | None = None
    market_score: float | None = None
    gap_score: float | None = None
    evidence_coverage_pct: float | None = None
    source_diversity: int = 0
    methodology_version: str = "gap-method-v1"
    narrative_summary: str | None = None


@dataclass
class EvidenceInput:
    evidence_role: str = "supporting"
    source_table: str | None = None
    source_record_key: str | None = None
    source_url: str | None = None
    evidence_quote: str | None = None
    relevance_score: float | None = None
    observed_at: datetime | str | None = None
    content_hash: str | None = None
    # Optional local key matching RiskScoreInput.component_key
    score_component_key: str | None = None


@dataclass
class AlertEventInput:
    issue_key: str
    event_type: str
    alert_level: str
    decision_rationale: str
    previous_alert_level: str | None = None
    lifecycle_status: str = "active"
    triggered_at: datetime | str | None = None
    effective_until: datetime | str | None = None
    requires_human_review: bool = True
    evidence: list[EvidenceInput] = field(default_factory=list)
    # Local key for attaching validation judgments before DB ids exist.
    local_key: str | None = None


@dataclass
class ValidationJudgmentInput:
    issue_key: str
    audit_type: str
    verdict: str
    rationale: str
    expected_alert_level: str | None = None
    observed_outcome: str | None = None
    validation_window_start: datetime | str | None = None
    validation_window_end: datetime | str | None = None
    reviewer: str | None = None
    reviewed_at: datetime | str | None = None
    evidence_sufficiency: str | None = None
    reference_url: str | None = None
    source_key: str | None = None
    # Optional local alert key; None = missed-signal style row without alert.
    alert_local_key: str | None = None


@dataclass
class ScoringBundle:
    scoring_version: str
    run_key: str | None = None
    config_hash: str | None = None
    window_start: datetime | str | None = None
    window_end: datetime | str | None = None
    executed_at: datetime | str | None = None
    status: str = "completed"
    notes: str | None = None
    scores: list[RiskScoreInput] = field(default_factory=list)
    gaps: list[SignalGapInput] = field(default_factory=list)
    alerts: list[AlertEventInput] = field(default_factory=list)
    judgments: list[ValidationJudgmentInput] = field(default_factory=list)


@dataclass
class WriteResult:
    scoring_run_id: int
    run_key: str
    score_ids: dict[str, int]
    gap_ids: dict[str, int]
    alert_ids: dict[str, int]
    evidence_ids: list[int]
    judgment_ids: list[int]


def validate_bundle(bundle: ScoringBundle) -> None:
    _require(bool(bundle.scoring_version), "scoring_version is required")
    _require(bundle.status in {"completed", "failed", "partial"}, f"invalid status: {bundle.status}")
    if bundle.run_key:
        _require(len(bundle.run_key) <= 36, "run_key must be <= 36 characters (CHAR(36))")

    for score in bundle.scores:
        _require(bool(score.issue_key), "score.issue_key required")
        _require(bool(score.signal_family), "score.signal_family required")
        _require(bool(score.metric_name), "score.metric_name required")

    for gap in bundle.gaps:
        _require(bool(gap.issue_key), "gap.issue_key required")
        _require(bool(gap.methodology_version), "gap.methodology_version required")

    for alert in bundle.alerts:
        _require(bool(alert.issue_key), "alert.issue_key required")
        _require(alert.event_type in ALLOWED_EVENT_TYPES, f"invalid event_type: {alert.event_type}")
        _require(alert.alert_level in ALLOWED_ALERT_LEVELS, f"invalid alert_level: {alert.alert_level}")
        _require(
            alert.lifecycle_status in ALLOWED_LIFECYCLE,
            f"invalid lifecycle_status: {alert.lifecycle_status}",
        )
        _require(bool(alert.decision_rationale.strip()), "alert.decision_rationale required")
        if alert.previous_alert_level is not None:
            _require(
                alert.previous_alert_level in ALLOWED_ALERT_LEVELS,
                f"invalid previous_alert_level: {alert.previous_alert_level}",
            )

    for judgment in bundle.judgments:
        _require(bool(judgment.issue_key), "judgment.issue_key required")
        _require(bool(judgment.audit_type), "judgment.audit_type required")
        _require(judgment.verdict in ALLOWED_VERDICTS, f"invalid verdict: {judgment.verdict}")
        _require(bool(judgment.rationale.strip()), "judgment.rationale required")

    # TEST consistency: fixture runs should only touch TEST_* issues.
    if is_test_run_key(bundle.run_key):
        for score in bundle.scores:
            _require(
                is_test_issue_key(score.issue_key),
                f"TEST run_key requires TEST_* issue_key, got {score.issue_key}",
            )
        for alert in bundle.alerts:
            _require(
                is_test_issue_key(alert.issue_key),
                f"TEST run_key requires TEST_* alert issue_key, got {alert.issue_key}",
            )


def ensure_validation_source_key_column(conn) -> None:
    """Additive schema guard: source_key used for idempotent history loads."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'alert_validation_audit'
          AND COLUMN_NAME = 'source_key'
        """
    )
    exists = cur.fetchone()[0] > 0
    if not exists:
        cur.execute(
            """
            ALTER TABLE alert_validation_audit
            ADD COLUMN source_key VARCHAR(191) NULL
                COMMENT 'Deterministic import key for frozen history / fixtures'
                AFTER reference_url,
            ADD INDEX idx_alert_validation_source_key (source_key)
            """
        )
    cur.close()


def write_scoring_bundle(conn, bundle: ScoringBundle) -> WriteResult:
    """Insert a full scoring + alert + evidence + judgment bundle atomically."""
    validate_bundle(bundle)
    ensure_validation_source_key_column(conn)

    run_key = bundle.run_key or str(uuid.uuid4())
    if len(run_key) > 36:
        raise ValueError("run_key must be <= 36 characters")

    executed_at = _as_naive_utc(bundle.executed_at) or _utc_now()
    window_start = _as_naive_utc(bundle.window_start)
    window_end = _as_naive_utc(bundle.window_end)
    config_hash = bundle.config_hash
    if config_hash and len(config_hash) > 64:
        config_hash = hashlib.sha256(config_hash.encode("utf-8")).hexdigest()

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO scoring_runs (
                run_key, scoring_version, config_hash,
                window_start, window_end, executed_at, status, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_key,
                bundle.scoring_version,
                config_hash,
                window_start,
                window_end,
                executed_at,
                bundle.status,
                bundle.notes,
            ),
        )
        scoring_run_id = int(cur.lastrowid)

        score_ids: dict[str, int] = {}
        for idx, score in enumerate(bundle.scores):
            local_key = score.component_key or (
                f"{score.issue_key}|{score.signal_family}|{score.metric_name}|{idx}"
            )
            cur.execute(
                """
                INSERT INTO risk_signal_scores (
                    scoring_run_id, issue_key, signal_family, metric_name,
                    observed_at, raw_value, baseline_value, normalized_score,
                    weight, contribution_score, confidence_score, evidence_count,
                    freshness_hours, quality_status, evidence_summary
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    scoring_run_id,
                    score.issue_key,
                    score.signal_family,
                    score.metric_name,
                    _as_naive_utc(score.observed_at) or executed_at,
                    score.raw_value,
                    score.baseline_value,
                    score.normalized_score,
                    score.weight,
                    score.contribution_score,
                    score.confidence_score,
                    int(score.evidence_count or 0),
                    score.freshness_hours,
                    score.quality_status or "usable",
                    score.evidence_summary,
                ),
            )
            score_ids[local_key] = int(cur.lastrowid)

        gap_ids: dict[str, int] = {}
        for gap in bundle.gaps:
            cur.execute(
                """
                INSERT INTO signal_gap_snapshots (
                    scoring_run_id, issue_key, snapshot_at,
                    official_score, independent_score, public_score, market_score,
                    gap_score, evidence_coverage_pct, source_diversity,
                    methodology_version, narrative_summary
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                """,
                (
                    scoring_run_id,
                    gap.issue_key,
                    _as_naive_utc(gap.snapshot_at) or executed_at,
                    gap.official_score,
                    gap.independent_score,
                    gap.public_score,
                    gap.market_score,
                    gap.gap_score,
                    gap.evidence_coverage_pct,
                    int(gap.source_diversity or 0),
                    gap.methodology_version,
                    gap.narrative_summary,
                ),
            )
            gap_ids[gap.issue_key] = int(cur.lastrowid)

        alert_ids: dict[str, int] = {}
        evidence_ids: list[int] = []
        for alert in bundle.alerts:
            local_key = alert.local_key or f"{alert.issue_key}|{alert.event_type}"
            cur.execute(
                """
                INSERT INTO alert_events (
                    scoring_run_id, signal_gap_snapshot_id, issue_key,
                    event_type, alert_level, previous_alert_level, lifecycle_status,
                    triggered_at, effective_until, requires_human_review, decision_rationale
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    scoring_run_id,
                    gap_ids.get(alert.issue_key),
                    alert.issue_key,
                    alert.event_type,
                    alert.alert_level,
                    alert.previous_alert_level,
                    alert.lifecycle_status,
                    _as_naive_utc(alert.triggered_at) or executed_at,
                    _as_naive_utc(alert.effective_until),
                    1 if alert.requires_human_review else 0,
                    alert.decision_rationale,
                ),
            )
            alert_id = int(cur.lastrowid)
            alert_ids[local_key] = alert_id

            for evidence in alert.evidence:
                risk_score_id = None
                if evidence.score_component_key:
                    risk_score_id = score_ids.get(evidence.score_component_key)
                cur.execute(
                    """
                    INSERT INTO alert_event_evidence (
                        alert_event_id, risk_signal_score_id, source_table,
                        source_record_key, source_url, evidence_role, evidence_quote,
                        relevance_score, observed_at, content_hash
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    """,
                    (
                        alert_id,
                        risk_score_id,
                        evidence.source_table,
                        evidence.source_record_key,
                        evidence.source_url,
                        evidence.evidence_role or "supporting",
                        evidence.evidence_quote,
                        evidence.relevance_score,
                        _as_naive_utc(evidence.observed_at) or executed_at,
                        evidence.content_hash,
                    ),
                )
                evidence_ids.append(int(cur.lastrowid))

        judgment_ids: list[int] = []
        for judgment in bundle.judgments:
            alert_event_id = None
            if judgment.alert_local_key:
                alert_event_id = alert_ids.get(judgment.alert_local_key)
                _require(
                    alert_event_id is not None,
                    f"judgment alert_local_key not found: {judgment.alert_local_key}",
                )
            cur.execute(
                """
                INSERT INTO alert_validation_audit (
                    alert_event_id, issue_key, audit_type, verdict,
                    expected_alert_level, observed_outcome,
                    validation_window_start, validation_window_end,
                    reviewer, reviewed_at, evidence_sufficiency,
                    rationale, reference_url, source_key
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    alert_event_id,
                    judgment.issue_key,
                    judgment.audit_type,
                    judgment.verdict,
                    judgment.expected_alert_level,
                    judgment.observed_outcome,
                    _as_naive_utc(judgment.validation_window_start),
                    _as_naive_utc(judgment.validation_window_end),
                    judgment.reviewer,
                    _as_naive_utc(judgment.reviewed_at) or executed_at,
                    judgment.evidence_sufficiency,
                    judgment.rationale,
                    judgment.reference_url,
                    judgment.source_key,
                ),
            )
            judgment_ids.append(int(cur.lastrowid))

        conn.commit()
        return WriteResult(
            scoring_run_id=scoring_run_id,
            run_key=run_key,
            score_ids=score_ids,
            gap_ids=gap_ids,
            alert_ids=alert_ids,
            evidence_ids=evidence_ids,
            judgment_ids=judgment_ids,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def append_validation_judgments(
    conn,
    judgments: list[ValidationJudgmentInput],
    *,
    skip_existing_source_keys: bool = True,
) -> list[int]:
    """Append-only validation judgments (no scoring run required).

    Used for frozen backtest / human-review history imports.
    """
    ensure_validation_source_key_column(conn)
    inserted: list[int] = []
    cur = conn.cursor(dictionary=True)
    try:
        for judgment in judgments:
            _require(bool(judgment.issue_key), "judgment.issue_key required")
            _require(judgment.verdict in ALLOWED_VERDICTS, f"invalid verdict: {judgment.verdict}")
            _require(bool(judgment.rationale.strip()), "judgment.rationale required")
            if skip_existing_source_keys and judgment.source_key:
                cur.execute(
                    "SELECT id FROM alert_validation_audit WHERE source_key = %s LIMIT 1",
                    (judgment.source_key,),
                )
                existing = cur.fetchone()
                if existing:
                    continue
            cur.execute(
                """
                INSERT INTO alert_validation_audit (
                    alert_event_id, issue_key, audit_type, verdict,
                    expected_alert_level, observed_outcome,
                    validation_window_start, validation_window_end,
                    reviewer, reviewed_at, evidence_sufficiency,
                    rationale, reference_url, source_key
                ) VALUES (
                    NULL, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    judgment.issue_key,
                    judgment.audit_type,
                    judgment.verdict,
                    judgment.expected_alert_level,
                    judgment.observed_outcome,
                    _as_naive_utc(judgment.validation_window_start),
                    _as_naive_utc(judgment.validation_window_end),
                    judgment.reviewer,
                    _as_naive_utc(judgment.reviewed_at) or _utc_now(),
                    judgment.evidence_sufficiency,
                    judgment.rationale,
                    judgment.reference_url,
                    judgment.source_key,
                ),
            )
            inserted.append(int(cur.lastrowid))
        conn.commit()
        return inserted
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def bundle_to_dict(result: WriteResult) -> dict[str, Any]:
    return {
        "scoring_run_id": result.scoring_run_id,
        "run_key": result.run_key,
        "score_ids": result.score_ids,
        "gap_ids": result.gap_ids,
        "alert_ids": result.alert_ids,
        "evidence_count": len(result.evidence_ids),
        "judgment_count": len(result.judgment_ids),
        "is_test_fixture": is_test_run_key(result.run_key),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atomic early-warning evidence writer")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Validate imports and vocabulary only (no DB write)",
    )
    args = parser.parse_args(argv)
    if args.self_check:
        print("evidence_writer self-check OK")
        print(f"TEST run prefix: {TEST_RUN_KEY_PREFIX}")
        print(f"alert levels: {sorted(ALLOWED_ALERT_LEVELS)}")
        print(f"verdicts: {sorted(ALLOWED_VERDICTS)}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MySQLError as exc:
        print(f"MySQL error: {exc}", file=sys.stderr)
        raise SystemExit(1)
