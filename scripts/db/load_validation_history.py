"""Load frozen backtest / human-review history into alert_validation_audit.

Append-only. Does NOT invent official Alert Level events from article counts.
Does NOT write TEST fixtures (see manage_test_fixtures.py).

Sources (in order):
  1. data/validation_backtest_log.csv — if data rows exist
  2. data/false_alarm_missed_signal_log.csv — if data rows exist
  3. data/tev1_backtest_results.json + scripts/validation/backtest_early_warning.BACKTEST_CASES
     (frozen advisory comparison + simulated human review labels)
  4. data/pending_human_review.csv — rows with reviewer_decision filled

Idempotent via alert_validation_audit.source_key.

Usage:
  python scripts/db/load_validation_history.py --dry-run
  python scripts/db/load_validation_history.py --commit
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db_connection import ROOT, get_connection, is_test_issue_key
from evidence_writer import ValidationJudgmentInput, append_validation_judgments

VALIDATION_BACKTEST_CSV = ROOT / "data" / "validation_backtest_log.csv"
FALSE_ALARM_CSV = ROOT / "data" / "false_alarm_missed_signal_log.csv"
TEV1_JSON = ROOT / "data" / "tev1_backtest_results.json"
PENDING_REVIEW_CSV = ROOT / "data" / "pending_human_review.csv"


def _map_reviewer_decision(decision: str, error_type: str | None = None) -> str:
    d = (decision or "").strip().lower()
    e = (error_type or "").strip().lower()
    if e in {"false_alarm_candidate", "false_alarm"}:
        return "false_alarm"
    if e in {"missed_signal_candidate", "missed_signal"}:
        return "missed_signal"
    if e in {"evidence_gap"}:
        return "insufficient_evidence"
    if d == "accept":
        return "confirmed"
    if d == "revise":
        return "insufficient_evidence"
    if d == "reject":
        return "false_alarm"
    return "pending_review"


def _map_case_human_review(case: dict) -> str:
    """Map backtest_early_warning human_review block to verdict vocabulary."""
    hr = case.get("human_review") or {}
    alert = (hr.get("alert_level") or "").lower()
    evidence = (hr.get("evidence") or "").lower()
    note = (case.get("note") or "").lower()
    if "missed signal" in note or "미탐" in note:
        return "missed_signal"
    if alert == "accept" and evidence in {"supported", "partial"}:
        return "confirmed"
    if alert == "revise":
        return "insufficient_evidence"
    if alert == "reject":
        return "false_alarm"
    if evidence in {"insufficient", "unsupported"}:
        return "insufficient_evidence"
    return "pending_review"


def _normalize_alert_level(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().upper()
    if text in {"WATCH", "WARNING", "CRITICAL"}:
        return text
    # early_warning cases use title case
    mapping = {
        "WATCH": "WATCH",
        "WARNING": "WARNING",
        "CRITICAL": "CRITICAL",
    }
    return mapping.get(text)


def judgments_from_validation_backtest_csv() -> list[ValidationJudgmentInput]:
    if not VALIDATION_BACKTEST_CSV.exists():
        return []
    out: list[ValidationJudgmentInput] = []
    with VALIDATION_BACKTEST_CSV.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            backtest_id = (row.get("backtest_id") or "").strip()
            issue_id = (row.get("issue_id") or "").strip()
            if not backtest_id or not issue_id or is_test_issue_key(issue_id):
                continue
            decision = row.get("alert_decision") or row.get("reviewer_decision") or ""
            verdict = _map_reviewer_decision(decision)
            out.append(
                ValidationJudgmentInput(
                    issue_key=issue_id,
                    audit_type="frozen_backtest",
                    verdict=verdict,
                    expected_alert_level=_normalize_alert_level(row.get("alert_level")),
                    observed_outcome=(row.get("post_reference_note") or "")[:100] or None,
                    validation_window_start=row.get("observation_start") or None,
                    validation_window_end=row.get("observation_end") or None,
                    reviewer=row.get("reviewer_id") or None,
                    reviewed_at=row.get("reviewed_at") or None,
                    evidence_sufficiency=row.get("evidence_support") or None,
                    rationale=(
                        f"Frozen backtest {backtest_id}. "
                        f"limitations={(row.get('limitations') or '').strip() or 'n/a'}"
                    ),
                    reference_url=(row.get("evidence_urls") or "").split("|")[0] or None,
                    source_key=f"validation_backtest:{backtest_id}",
                )
            )
    return out


def judgments_from_false_alarm_csv() -> list[ValidationJudgmentInput]:
    if not FALSE_ALARM_CSV.exists():
        return []
    out: list[ValidationJudgmentInput] = []
    with FALSE_ALARM_CSV.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            record_id = (row.get("record_id") or "").strip()
            issue_id = (row.get("issue_id") or "").strip()
            if not record_id or not issue_id or is_test_issue_key(issue_id):
                continue
            record_type = (row.get("record_type") or "").lower()
            if "missed" in record_type:
                verdict = "missed_signal"
            elif "false" in record_type:
                verdict = "false_alarm"
            else:
                verdict = "pending_review"
            out.append(
                ValidationJudgmentInput(
                    issue_key=issue_id,
                    audit_type="error_log",
                    verdict=verdict,
                    expected_alert_level=_normalize_alert_level(row.get("alert_level_at_time")),
                    observed_outcome=(row.get("status") or "")[:100] or None,
                    validation_window_start=row.get("observation_start") or None,
                    validation_window_end=row.get("observation_end") or None,
                    reviewer=row.get("owner") or None,
                    reviewed_at=row.get("discovered_at") or None,
                    evidence_sufficiency=None,
                    rationale=(
                        f"{row.get('why_flagged') or ''} | "
                        f"hypothesis={row.get('root_cause_hypothesis') or ''} | "
                        f"action={row.get('corrective_action') or ''}"
                    ).strip(" |"),
                    reference_url=(row.get("available_evidence_urls") or "").split("|")[0]
                    or None,
                    source_key=f"false_alarm_log:{record_id}",
                )
            )
    return out


def judgments_from_tev1_and_cases() -> list[ValidationJudgmentInput]:
    """Wire tev1 advisory results + early-warning case human labels.

    These are frozen comparison / simulated review rows — not official alerts.
    """
    # Import case definitions without executing report generation side effects
    # beyond module load (module only defines data + helpers).
    sys.path.insert(0, str(ROOT / "scripts" / "validation"))
    from backtest_early_warning import BACKTEST_CASES  # type: ignore

    tev1_by_id: dict[str, dict] = {}
    if TEV1_JSON.exists():
        payload = json.loads(TEV1_JSON.read_text(encoding="utf-8"))
        for item in payload.get("results") or []:
            if item.get("case_id"):
                tev1_by_id[item["case_id"]] = item

    out: list[ValidationJudgmentInput] = []
    for case in BACKTEST_CASES:
        case_id = case["case_id"]
        tev1 = tev1_by_id.get(case_id, {})
        issue_key = tev1.get("issue_id") or case_id.lower().replace("-", "_")
        if is_test_issue_key(issue_key):
            continue
        window = case.get("observation_window") or ""
        start, end = None, None
        if "~" in window:
            parts = [p.strip() for p in window.split("~", 1)]
            if len(parts) == 2:
                start, end = parts[0], parts[1]
        verdict = _map_case_human_review(case)
        expected = _normalize_alert_level(case.get("system_alert_level"))
        tev1_choice = tev1.get("tev1_choice")
        rationale = (
            f"Frozen advisory/human-review history for {case_id} ({case.get('name')}). "
            f"system_alert_level_in_case={case.get('system_alert_level')}; "
            f"tev1_choice={tev1_choice}; "
            f"human_review={case.get('human_review')}; "
            f"note={case.get('note')}. "
            "Not an official Alert Level event; append-only validation history."
        )
        out.append(
            ValidationJudgmentInput(
                issue_key=str(issue_key),
                audit_type="frozen_backtest",
                verdict=verdict,
                expected_alert_level=expected,
                observed_outcome=f"tev1={tev1_choice}" if tev1_choice else "case_label_only",
                validation_window_start=start,
                validation_window_end=end,
                reviewer="backtest_early_warning",
                reviewed_at=case.get("crisis_start_date"),
                evidence_sufficiency=(case.get("human_review") or {}).get("evidence"),
                rationale=rationale,
                reference_url=f"case://early_warning_backtest/{case_id}",
                source_key=f"frozen_backtest:{case_id}",
            )
        )
    return out


def judgments_from_pending_human_review() -> list[ValidationJudgmentInput]:
    if not PENDING_REVIEW_CSV.exists():
        return []
    out: list[ValidationJudgmentInput] = []
    with PENDING_REVIEW_CSV.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            decision = (row.get("reviewer_decision") or "").strip()
            article_id = (row.get("article_id") or "").strip()
            if not decision or not article_id:
                continue
            raw_issues = (row.get("issue_ids") or "").strip()
            # issue_ids looks like "['Trump_Economy']"
            issue_key = "UNSPECIFIED"
            if raw_issues.startswith("[") and "'" in raw_issues:
                try:
                    import ast

                    parsed = ast.literal_eval(raw_issues)
                    if parsed:
                        issue_key = str(parsed[0])
                except Exception:
                    issue_key = raw_issues
            if is_test_issue_key(issue_key):
                continue
            out.append(
                ValidationJudgmentInput(
                    issue_key=issue_key,
                    audit_type="human_review",
                    verdict=_map_reviewer_decision(decision, row.get("error_type")),
                    expected_alert_level=_normalize_alert_level(row.get("alert_level")),
                    observed_outcome=(row.get("review_status") or "")[:100] or None,
                    reviewer=row.get("reviewer_id") or None,
                    reviewed_at=row.get("reviewed_at") or None,
                    evidence_sufficiency=row.get("evidence_quote_supported") or None,
                    rationale=(
                        f"Human review article_id={article_id}; "
                        f"error_type={row.get('error_type') or 'none'}; "
                        f"detail={(row.get('error_detail') or '').strip() or 'n/a'}; "
                        f"correction={(row.get('correction_note') or '').strip() or 'n/a'}"
                    ),
                    reference_url=row.get("link") or None,
                    source_key=f"human_review:{article_id}",
                )
            )
    return out


def collect_all_judgments() -> list[ValidationJudgmentInput]:
    judgments: list[ValidationJudgmentInput] = []
    judgments.extend(judgments_from_validation_backtest_csv())
    judgments.extend(judgments_from_false_alarm_csv())
    judgments.extend(judgments_from_tev1_and_cases())
    judgments.extend(judgments_from_pending_human_review())
    return judgments


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load frozen validation history into MySQL")
    parser.add_argument("--dry-run", action="store_true", help="Print planned inserts only")
    parser.add_argument("--commit", action="store_true", help="Append judgments to DB")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.commit:
        print("Specify --dry-run or --commit")
        return 2

    judgments = collect_all_judgments()
    print(f"planned judgments: {len(judgments)}")
    for j in judgments:
        print(
            f"  - {j.source_key} | {j.issue_key} | {j.audit_type} | {j.verdict} | "
            f"expected={j.expected_alert_level}"
        )

    if args.dry_run:
        return 0

    conn = get_connection()
    try:
        inserted = append_validation_judgments(conn, judgments, skip_existing_source_keys=True)
        print(f"inserted: {len(inserted)} (skipped existing source_key rows)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
