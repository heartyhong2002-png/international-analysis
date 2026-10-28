"""
evidence_writer.py — 조기경보 증거 계층 트랜잭션 writer
=======================================================

점수·경보·근거·검증 판정을 한 트랜잭션으로 저장한다.
- run_key 중복 시 실패 (기존 이력 덮어쓰지 않음)
- 실패 시 전체 롤백
- REPLACE INTO 사용 금지 (append-only 증거 보존)
- 완료 후 공식 뷰 4개를 조회해 호출자에게 반환

운영 성과 집계는 TEST fixture를 제외한 뷰 정의를 따른다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT = _SCRIPT_DIR.parent.parent
load_dotenv(_ROOT / ".env")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")

ALERT_LEVELS = frozenset({"WATCH", "WARNING", "CRITICAL"})
LIFECYCLE_STATUSES = frozenset({"active", "resolved", "superseded", "held_for_review"})
EVENT_TYPES = frozenset({"raised", "level_changed", "resolved", "superseded"})
VERDICTS = frozenset(
    {"confirmed", "false_alarm", "missed_signal", "insufficient_evidence", "pending_review"}
)
SIGNAL_FAMILIES = frozenset(
    {"official", "independent", "public", "market", "trade", "llm", "other"}
)
OFFICIAL_VIEWS = (
    "v_dashboard_current_alerts",
    "v_alert_evidence_trace",
    "v_signal_gap_trend",
    "v_alert_validation_summary",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_dt(value: Any, field_name: str) -> datetime:
    if value is None or value == "":
        raise ValueError(f"{field_name} is required")
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO datetime, got {value!r}") from exc
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def optional_dt(value: Any, field_name: str) -> Optional[datetime]:
    if value is None or value == "":
        return None
    return parse_dt(value, field_name)


def get_connection():
    import mysql.connector

    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        autocommit=False,
    )


@dataclass
class RiskScoreInput:
    issue_key: str
    signal_family: str
    metric_name: str
    observed_at: Optional[str] = None
    raw_value: Optional[float] = None
    baseline_value: Optional[float] = None
    normalized_score: Optional[float] = None
    weight: Optional[float] = None
    contribution_score: Optional[float] = None
    confidence_score: Optional[float] = None
    evidence_count: int = 0
    freshness_hours: Optional[float] = None
    quality_status: str = "usable"
    evidence_summary: Optional[str] = None


@dataclass
class SignalGapInput:
    issue_key: str
    snapshot_at: str
    methodology_version: str
    official_score: Optional[float] = None
    independent_score: Optional[float] = None
    public_score: Optional[float] = None
    market_score: Optional[float] = None
    gap_score: Optional[float] = None
    evidence_coverage_pct: Optional[float] = None
    source_diversity: int = 0
    narrative_summary: Optional[str] = None


@dataclass
class EvidenceInput:
    evidence_role: str = "supporting"
    risk_score_ref: Optional[str] = None  # "issue_key|signal_family|metric_name"
    source_table: Optional[str] = None
    source_record_key: Optional[str] = None
    source_url: Optional[str] = None
    evidence_quote: Optional[str] = None
    relevance_score: Optional[float] = None
    observed_at: Optional[str] = None
    content_hash: Optional[str] = None


@dataclass
class AlertInput:
    issue_key: str
    event_type: str
    alert_level: str
    triggered_at: str
    decision_rationale: str
    previous_alert_level: Optional[str] = None
    lifecycle_status: str = "active"
    effective_until: Optional[str] = None
    requires_human_review: bool = True
    evidence: List[EvidenceInput] = field(default_factory=list)


@dataclass
class ValidationInput:
    issue_key: str
    audit_type: str
    verdict: str
    reviewed_at: str
    rationale: str
    alert_issue_key: Optional[str] = None  # link to alert created in same payload
    expected_alert_level: Optional[str] = None
    observed_outcome: Optional[str] = None
    validation_window_start: Optional[str] = None
    validation_window_end: Optional[str] = None
    reviewer: Optional[str] = None
    evidence_sufficiency: Optional[str] = None
    reference_url: Optional[str] = None


@dataclass
class ScoringRunPayload:
    run_key: str
    scoring_version: str
    executed_at: str
    config_hash: Optional[str] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    status: str = "completed"
    notes: Optional[str] = None
    scores: List[RiskScoreInput] = field(default_factory=list)
    gaps: List[SignalGapInput] = field(default_factory=list)
    alerts: List[AlertInput] = field(default_factory=list)
    validations: List[ValidationInput] = field(default_factory=list)


class EvidenceWriteError(ValueError):
    """입력 검증 또는 중복 run_key 오류."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceWriteError(message)


def validate_payload(payload: ScoringRunPayload) -> None:
    _require(bool(payload.run_key and payload.run_key.strip()), "run_key is required")
    _require(
        bool(payload.scoring_version and payload.scoring_version.strip()),
        "scoring_version is required",
    )
    parse_dt(payload.executed_at, "executed_at")
    _require(payload.status in {"completed", "failed", "partial"}, f"invalid status: {payload.status}")

    score_keys = set()
    for s in payload.scores:
        _require(bool(s.issue_key), "score.issue_key required")
        _require(s.signal_family in SIGNAL_FAMILIES, f"invalid signal_family: {s.signal_family}")
        _require(bool(s.metric_name), "score.metric_name required")
        key = (s.issue_key, s.signal_family, s.metric_name)
        _require(key not in score_keys, f"duplicate score component: {key}")
        score_keys.add(key)

    gap_keys = set()
    for g in payload.gaps:
        _require(bool(g.issue_key), "gap.issue_key required")
        _require(bool(g.methodology_version), "gap.methodology_version required")
        parse_dt(g.snapshot_at, "gap.snapshot_at")
        _require(g.issue_key not in gap_keys, f"duplicate gap for issue: {g.issue_key}")
        gap_keys.add(g.issue_key)

    alert_keys = set()
    for a in payload.alerts:
        _require(bool(a.issue_key), "alert.issue_key required")
        _require(a.event_type in EVENT_TYPES, f"invalid event_type: {a.event_type}")
        _require(a.alert_level in ALERT_LEVELS, f"invalid alert_level: {a.alert_level}")
        if a.previous_alert_level:
            _require(
                a.previous_alert_level in ALERT_LEVELS,
                f"invalid previous_alert_level: {a.previous_alert_level}",
            )
        _require(
            a.lifecycle_status in LIFECYCLE_STATUSES,
            f"invalid lifecycle_status: {a.lifecycle_status}",
        )
        _require(bool(a.decision_rationale and a.decision_rationale.strip()), "decision_rationale required")
        parse_dt(a.triggered_at, "alert.triggered_at")
        uniq = (a.issue_key, a.event_type)
        _require(uniq not in alert_keys, f"duplicate alert event: {uniq}")
        alert_keys.add(uniq)
        for e in a.evidence:
            if e.risk_score_ref:
                parts = e.risk_score_ref.split("|")
                _require(len(parts) == 3, f"risk_score_ref must be issue|family|metric: {e.risk_score_ref}")
                ref = (parts[0], parts[1], parts[2])
                _require(ref in score_keys, f"risk_score_ref not in payload scores: {e.risk_score_ref}")

    for v in payload.validations:
        _require(bool(v.issue_key), "validation.issue_key required")
        _require(bool(v.audit_type), "validation.audit_type required")
        _require(v.verdict in VERDICTS, f"invalid verdict: {v.verdict}")
        _require(bool(v.rationale and v.rationale.strip()), "validation.rationale required")
        parse_dt(v.reviewed_at, "validation.reviewed_at")
        if v.expected_alert_level:
            _require(
                v.expected_alert_level in ALERT_LEVELS,
                f"invalid expected_alert_level: {v.expected_alert_level}",
            )


def payload_from_dict(data: Dict[str, Any]) -> ScoringRunPayload:
    scores = [RiskScoreInput(**s) for s in data.get("scores", [])]
    gaps = [SignalGapInput(**g) for g in data.get("gaps", [])]
    alerts = []
    for a in data.get("alerts", []):
        ev = [EvidenceInput(**e) for e in a.get("evidence", [])]
        body = {k: v for k, v in a.items() if k != "evidence"}
        alerts.append(AlertInput(**body, evidence=ev))
    validations = [ValidationInput(**v) for v in data.get("validations", [])]
    top = {k: v for k, v in data.items() if k not in {"scores", "gaps", "alerts", "validations"}}
    return ScoringRunPayload(**top, scores=scores, gaps=gaps, alerts=alerts, validations=validations)


def _fetch_view_snapshot(cur, issue_keys: Sequence[str]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    keys = list(issue_keys)
    for view in OFFICIAL_VIEWS:
        if keys and view in {
            "v_dashboard_current_alerts",
            "v_alert_evidence_trace",
            "v_signal_gap_trend",
            "v_alert_validation_summary",
        }:
            placeholders = ",".join(["%s"] * len(keys))
            try:
                cur.execute(
                    f"SELECT * FROM {view} WHERE issue_key IN ({placeholders}) LIMIT 200",
                    tuple(keys),
                )
            except Exception:
                cur.execute(f"SELECT * FROM {view} LIMIT 50")
        else:
            cur.execute(f"SELECT * FROM {view} LIMIT 50")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        # datetime → iso for JSON safety
        for row in rows:
            for k, v in list(row.items()):
                if isinstance(v, datetime):
                    row[k] = v.isoformat(sep=" ")
        out[view] = rows
    return out


def save_scoring_run(
    payload: ScoringRunPayload,
    *,
    connection=None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """점수·경보·근거·검증을 한 트랜잭션으로 저장한다."""
    validate_payload(payload)
    own_conn = connection is None
    conn = connection or get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM scoring_runs WHERE run_key = %s", (payload.run_key,))
        existing = cur.fetchone()
        if existing:
            raise EvidenceWriteError(
                f"run_key already exists (id={existing[0]}): {payload.run_key}. "
                "Evidence history is append-only; use a new run_key."
            )

        if dry_run:
            issue_keys = sorted(
                {
                    *(s.issue_key for s in payload.scores),
                    *(g.issue_key for g in payload.gaps),
                    *(a.issue_key for a in payload.alerts),
                    *(v.issue_key for v in payload.validations),
                }
            )
            return {
                "dry_run": True,
                "run_key": payload.run_key,
                "issue_keys": issue_keys,
                "would_insert": {
                    "scoring_runs": 1,
                    "risk_signal_scores": len(payload.scores),
                    "signal_gap_snapshots": len(payload.gaps),
                    "alert_events": len(payload.alerts),
                    "alert_event_evidence": sum(len(a.evidence) for a in payload.alerts),
                    "alert_validation_audit": len(payload.validations),
                },
            }

        cur.execute(
            """
            INSERT INTO scoring_runs (
                run_key, scoring_version, config_hash, window_start, window_end,
                executed_at, status, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payload.run_key,
                payload.scoring_version,
                payload.config_hash,
                optional_dt(payload.window_start, "window_start"),
                optional_dt(payload.window_end, "window_end"),
                parse_dt(payload.executed_at, "executed_at"),
                payload.status,
                payload.notes,
            ),
        )
        scoring_run_id = cur.lastrowid

        score_id_map: Dict[Tuple[str, str, str], int] = {}
        for s in payload.scores:
            cur.execute(
                """
                INSERT INTO risk_signal_scores (
                    scoring_run_id, issue_key, signal_family, metric_name, observed_at,
                    raw_value, baseline_value, normalized_score, weight, contribution_score,
                    confidence_score, evidence_count, freshness_hours, quality_status,
                    evidence_summary
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    scoring_run_id,
                    s.issue_key,
                    s.signal_family,
                    s.metric_name,
                    optional_dt(s.observed_at, "score.observed_at"),
                    s.raw_value,
                    s.baseline_value,
                    s.normalized_score,
                    s.weight,
                    s.contribution_score,
                    s.confidence_score,
                    int(s.evidence_count or 0),
                    s.freshness_hours,
                    s.quality_status or "usable",
                    s.evidence_summary,
                ),
            )
            score_id_map[(s.issue_key, s.signal_family, s.metric_name)] = cur.lastrowid

        gap_id_map: Dict[str, int] = {}
        for g in payload.gaps:
            cur.execute(
                """
                INSERT INTO signal_gap_snapshots (
                    scoring_run_id, issue_key, snapshot_at, official_score, independent_score,
                    public_score, market_score, gap_score, evidence_coverage_pct,
                    source_diversity, methodology_version, narrative_summary
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    scoring_run_id,
                    g.issue_key,
                    parse_dt(g.snapshot_at, "gap.snapshot_at"),
                    g.official_score,
                    g.independent_score,
                    g.public_score,
                    g.market_score,
                    g.gap_score,
                    g.evidence_coverage_pct,
                    int(g.source_diversity or 0),
                    g.methodology_version,
                    g.narrative_summary,
                ),
            )
            gap_id_map[g.issue_key] = cur.lastrowid

        alert_id_map: Dict[str, int] = {}
        evidence_count = 0
        for a in payload.alerts:
            cur.execute(
                """
                INSERT INTO alert_events (
                    scoring_run_id, signal_gap_snapshot_id, issue_key, event_type,
                    alert_level, previous_alert_level, lifecycle_status, triggered_at,
                    effective_until, requires_human_review, decision_rationale
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    scoring_run_id,
                    gap_id_map.get(a.issue_key),
                    a.issue_key,
                    a.event_type,
                    a.alert_level,
                    a.previous_alert_level,
                    a.lifecycle_status,
                    parse_dt(a.triggered_at, "alert.triggered_at"),
                    optional_dt(a.effective_until, "alert.effective_until"),
                    bool(a.requires_human_review),
                    a.decision_rationale,
                ),
            )
            alert_event_id = cur.lastrowid
            alert_id_map[a.issue_key] = alert_event_id
            for e in a.evidence:
                risk_score_id = None
                if e.risk_score_ref:
                    p0, p1, p2 = e.risk_score_ref.split("|")
                    risk_score_id = score_id_map[(p0, p1, p2)]
                cur.execute(
                    """
                    INSERT INTO alert_event_evidence (
                        alert_event_id, risk_signal_score_id, source_table, source_record_key,
                        source_url, evidence_role, evidence_quote, relevance_score,
                        observed_at, content_hash
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        alert_event_id,
                        risk_score_id,
                        e.source_table,
                        e.source_record_key,
                        e.source_url,
                        e.evidence_role or "supporting",
                        e.evidence_quote,
                        e.relevance_score,
                        optional_dt(e.observed_at, "evidence.observed_at"),
                        e.content_hash,
                    ),
                )
                evidence_count += 1

        validation_ids: List[int] = []
        for v in payload.validations:
            link_issue = v.alert_issue_key or v.issue_key
            alert_event_id = alert_id_map.get(link_issue)
            cur.execute(
                """
                INSERT INTO alert_validation_audit (
                    alert_event_id, issue_key, audit_type, verdict, expected_alert_level,
                    observed_outcome, validation_window_start, validation_window_end,
                    reviewer, reviewed_at, evidence_sufficiency, rationale, reference_url
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    alert_event_id,
                    v.issue_key,
                    v.audit_type,
                    v.verdict,
                    v.expected_alert_level,
                    v.observed_outcome,
                    optional_dt(v.validation_window_start, "validation_window_start"),
                    optional_dt(v.validation_window_end, "validation_window_end"),
                    v.reviewer,
                    parse_dt(v.reviewed_at, "validation.reviewed_at"),
                    v.evidence_sufficiency,
                    v.rationale,
                    v.reference_url,
                ),
            )
            validation_ids.append(cur.lastrowid)

        conn.commit()

        issue_keys = sorted(set(alert_id_map) | set(gap_id_map) | {s.issue_key for s in payload.scores})
        views = _fetch_view_snapshot(cur, issue_keys)

        return {
            "dry_run": False,
            "scoring_run_id": scoring_run_id,
            "run_key": payload.run_key,
            "scoring_version": payload.scoring_version,
            "alert_event_ids": alert_id_map,
            "validation_ids": validation_ids,
            "inserted": {
                "risk_signal_scores": len(score_id_map),
                "signal_gap_snapshots": len(gap_id_map),
                "alert_events": len(alert_id_map),
                "alert_event_evidence": evidence_count,
                "alert_validation_audit": len(validation_ids),
            },
            "views": views,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        if own_conn:
            conn.close()


def append_validation_audits(
    rows: Sequence[ValidationInput],
    *,
    connection=None,
    dry_run: bool = False,
    skip_duplicates: bool = True,
) -> Dict[str, Any]:
    """alert_validation_audit에만 append. CSV 원본은 건드리지 않는다."""
    for v in rows:
        _require(bool(v.issue_key), "validation.issue_key required")
        _require(bool(v.audit_type), "validation.audit_type required")
        _require(v.verdict in VERDICTS, f"invalid verdict: {v.verdict}")
        _require(bool(v.rationale and v.rationale.strip()), "validation.rationale required")
        parse_dt(v.reviewed_at, "validation.reviewed_at")

    own_conn = connection is None
    conn = connection or get_connection()
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    ids: List[int] = []
    try:
        for v in rows:
            reviewed_at = parse_dt(v.reviewed_at, "validation.reviewed_at")
            if skip_duplicates:
                cur.execute(
                    """
                    SELECT id FROM alert_validation_audit
                    WHERE issue_key = %s AND audit_type = %s AND verdict = %s
                      AND reviewed_at = %s AND IFNULL(reviewer,'') = IFNULL(%s,'')
                      AND rationale = %s
                    LIMIT 1
                    """,
                    (v.issue_key, v.audit_type, v.verdict, reviewed_at, v.reviewer, v.rationale),
                )
                if cur.fetchone():
                    skipped += 1
                    continue
            if dry_run:
                inserted += 1
                continue
            alert_event_id = None
            if v.alert_issue_key or v.issue_key:
                cur.execute(
                    """
                    SELECT id FROM alert_events
                    WHERE issue_key = %s
                    ORDER BY triggered_at DESC, id DESC
                    LIMIT 1
                    """,
                    (v.alert_issue_key or v.issue_key,),
                )
                hit = cur.fetchone()
                if hit:
                    alert_event_id = hit[0]
            cur.execute(
                """
                INSERT INTO alert_validation_audit (
                    alert_event_id, issue_key, audit_type, verdict, expected_alert_level,
                    observed_outcome, validation_window_start, validation_window_end,
                    reviewer, reviewed_at, evidence_sufficiency, rationale, reference_url
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    alert_event_id,
                    v.issue_key,
                    v.audit_type,
                    v.verdict,
                    v.expected_alert_level,
                    v.observed_outcome,
                    optional_dt(v.validation_window_start, "validation_window_start"),
                    optional_dt(v.validation_window_end, "validation_window_end"),
                    v.reviewer,
                    reviewed_at,
                    v.evidence_sufficiency,
                    v.rationale,
                    v.reference_url,
                ),
            )
            ids.append(cur.lastrowid)
            inserted += 1
        if not dry_run:
            conn.commit()
        return {
            "dry_run": dry_run,
            "inserted": inserted,
            "skipped_duplicates": skipped,
            "validation_ids": ids,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        if own_conn:
            conn.close()


def is_test_fixture_issue(issue_key: str) -> bool:
    return bool(issue_key) and (
        issue_key.startswith("TEST_")
        or issue_key.startswith("TEST-")
        or "fixture" in issue_key.lower()
    )


def is_test_fixture_run(run_key: str, scoring_version: str = "") -> bool:
    rk = (run_key or "").upper()
    sv = (scoring_version or "").lower()
    return rk.startswith("TEST-FIXTURE") or "TEST-FIXTURE" in rk or sv == "test-fixture-v1"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Transactional early-warning evidence writer")
    parser.add_argument("--payload", required=True, help="JSON payload path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-result", action="store_true")
    args = parser.parse_args(argv)

    path = Path(args.payload)
    data = json.loads(path.read_text(encoding="utf-8"))
    payload = payload_from_dict(data)
    result = save_scoring_run(payload, dry_run=args.dry_run)
    if args.print_result:
        # Avoid dumping huge view payloads by default in CI logs
        slim = {k: v for k, v in result.items() if k != "views"}
        slim["view_row_counts"] = {vk: len(vv) for vk, vv in result.get("views", {}).items()}
        print(json.dumps(slim, ensure_ascii=False, indent=2, default=str))
    else:
        print(
            f"OK run_key={result.get('run_key')} dry_run={result.get('dry_run')} "
            f"inserted={result.get('inserted') or result.get('would_insert')}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceWriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
