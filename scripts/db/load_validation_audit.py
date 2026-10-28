"""
load_validation_audit.py — 검증 CSV/사람 검수 → alert_validation_audit
======================================================================

원본 CSV는 읽기만 하고 덮어쓰지 않는다. DB에는 append-only로 적재한다.

지원 입력:
  1) data/validation_backtest_log.csv  (VALIDATION_PLAN 스키마)
  2) data/review_log.csv 중 human_label이 채워진 행 (톤 검수 → 잠정 판정 매핑)
  3) data/false_alarm_missed_signal_log.csv (오류 후보)

TEST fixture 행은 기본 제외(--include-fixtures로만 포함).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from evidence_writer import (
    ValidationInput,
    append_validation_audits,
    is_test_fixture_issue,
)

_ROOT = Path(__file__).resolve().parents[2]

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DECISION_TO_VERDICT = {
    "accept": "confirmed",
    "revise": "insufficient_evidence",
    "reject": "false_alarm",
    "confirmed": "confirmed",
    "false_alarm": "false_alarm",
    "missed_signal": "missed_signal",
    "insufficient_evidence": "insufficient_evidence",
    "pending_review": "pending_review",
    "pending": "pending_review",
}

# review_log.csv tone labels → provisional validation verdicts (not final alert QA)
HUMAN_LABEL_TO_VERDICT = {
    "critical": "pending_review",
    "negative": "pending_review",
    "neutral": "pending_review",
    "positive": "pending_review",
    "accept": "confirmed",
    "revise": "insufficient_evidence",
    "reject": "false_alarm",
}

ERROR_TYPE_TO_VERDICT = {
    "false_alarm_candidate": "false_alarm",
    "missed_signal_candidate": "missed_signal",
    "evidence_gap": "insufficient_evidence",
}


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _map_verdict(raw: str) -> Optional[str]:
    key = (raw or "").strip().lower()
    return DECISION_TO_VERDICT.get(key)


def from_backtest_log(
    path: Path,
    *,
    include_fixtures: bool = False,
) -> List[ValidationInput]:
    rows = _read_csv(path)
    out: List[ValidationInput] = []
    for r in rows:
        issue = (r.get("issue_id") or r.get("issue_key") or "").strip()
        if not issue:
            continue
        if not include_fixtures and is_test_fixture_issue(issue):
            continue
        decision = (
            r.get("alert_decision")
            or r.get("reviewer_decision")
            or r.get("verdict")
            or ""
        ).strip()
        verdict = _map_verdict(decision)
        if not verdict:
            continue
        reviewed_at = (r.get("reviewed_at") or r.get("reference_date") or "").strip()
        if not reviewed_at:
            continue
        rationale_parts = [
            f"backtest_id={r.get('backtest_id') or ''}",
            f"evidence_support={r.get('evidence_support') or r.get('evidence_quote_supported') or ''}",
            f"source_quality={r.get('source_quality') or ''}",
            f"interpretation={r.get('interpretation_assessment') or ''}",
            f"limitations={r.get('limitations') or ''}",
            f"post_note={r.get('post_reference_note') or r.get('post_event_notes') or ''}",
        ]
        alert_level = (r.get("alert_level") or "").strip().upper() or None
        if alert_level and alert_level not in {"WATCH", "WARNING", "CRITICAL"}:
            alert_level = None
        out.append(
            ValidationInput(
                issue_key=issue,
                audit_type="frozen_backtest",
                verdict=verdict,
                reviewed_at=reviewed_at,
                rationale="; ".join(p for p in rationale_parts if not p.endswith("=")),
                expected_alert_level=alert_level,
                observed_outcome=(r.get("post_reference_note") or "")[:100] or None,
                validation_window_start=(r.get("observation_start") or None),
                validation_window_end=(r.get("observation_end") or None),
                reviewer=(r.get("reviewer_id") or "backtest_csv") or None,
                evidence_sufficiency=(r.get("evidence_support") or None),
                reference_url=(r.get("evidence_urls") or None),
            )
        )
    return out


def from_review_log(
    path: Path,
    *,
    include_fixtures: bool = False,
) -> List[ValidationInput]:
    """사람 톤 검수 완료 행만 잠정 pending/판정으로 연결. review_log.csv는 수정하지 않음."""
    rows = _read_csv(path)
    out: List[ValidationInput] = []
    for r in rows:
        human = (r.get("human_label") or "").strip()
        if not human:
            continue
        issue_raw = (r.get("issue_ids") or "").strip()
        # issue_ids may be like "['Trump_Economy']" or empty
        issue = issue_raw.strip("[]'\" ")
        if "," in issue:
            issue = issue.split(",")[0].strip("[]'\" ")
        if not issue:
            issue = f"review_article:{(r.get('article_id') or 'unknown')}"
        if not include_fixtures and is_test_fixture_issue(issue):
            continue
        verdict = HUMAN_LABEL_TO_VERDICT.get(human.lower())
        if not verdict:
            verdict = "pending_review"
        reviewed_at = (r.get("reviewed_at") or r.get("collected_at") or "").strip()
        if not reviewed_at:
            continue
        # Normalize timezone-ish strings for MySQL DATETIME
        reviewed_at = reviewed_at.replace("Z", "").split("+")[0]
        rationale = (
            f"source=review_log.csv; article_id={r.get('article_id')}; "
            f"human_label={human}; llm_label={r.get('llm_label')}; "
            f"correction_note={r.get('correction_note') or ''}; "
            f"provisional_tone_review_not_alert_qa=1"
        )
        out.append(
            ValidationInput(
                issue_key=issue,
                audit_type="human_tone_review",
                verdict=verdict,
                reviewed_at=reviewed_at,
                rationale=rationale,
                reviewer="review_log",
                evidence_sufficiency="partial" if r.get("llm_evidence_quote") else "unknown",
                reference_url=(r.get("source_url") or r.get("link") or None),
            )
        )
    return out


def from_error_log(
    path: Path,
    *,
    include_fixtures: bool = False,
) -> List[ValidationInput]:
    rows = _read_csv(path)
    out: List[ValidationInput] = []
    for r in rows:
        issue = (r.get("issue_id") or r.get("issue_key") or "").strip()
        if not issue:
            continue
        if not include_fixtures and is_test_fixture_issue(issue):
            continue
        rtype = (r.get("record_type") or r.get("error_type") or "").strip().lower()
        verdict = ERROR_TYPE_TO_VERDICT.get(rtype)
        if not verdict:
            continue
        reviewed_at = (r.get("discovered_at") or r.get("recheck_date") or "").strip()
        if not reviewed_at:
            continue
        rationale = (
            f"source=false_alarm_missed_signal_log.csv; record_id={r.get('record_id')}; "
            f"why_flagged={r.get('why_flagged')}; hypothesis={r.get('root_cause_hypothesis')}; "
            f"status={r.get('status')}; notes={r.get('notes')}"
        )
        out.append(
            ValidationInput(
                issue_key=issue,
                audit_type="error_candidate",
                verdict=verdict,
                reviewed_at=reviewed_at,
                rationale=rationale,
                expected_alert_level=(r.get("alert_level_at_time") or None),
                observed_outcome=(r.get("status") or None),
                validation_window_start=(r.get("observation_start") or None),
                validation_window_end=(r.get("observation_end") or None),
                reviewer=(r.get("owner") or "error_log"),
                reference_url=(r.get("available_evidence_urls") or None),
            )
        )
    return out


def collect_rows(
    *,
    backtest_path: Path,
    review_path: Path,
    error_path: Path,
    sources: Iterable[str],
    include_fixtures: bool,
) -> List[ValidationInput]:
    rows: List[ValidationInput] = []
    src = set(sources)
    if "backtest" in src:
        rows.extend(from_backtest_log(backtest_path, include_fixtures=include_fixtures))
    if "review" in src:
        rows.extend(from_review_log(review_path, include_fixtures=include_fixtures))
    if "error" in src:
        rows.extend(from_error_log(error_path, include_fixtures=include_fixtures))
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Append validation CSVs into alert_validation_audit")
    parser.add_argument(
        "--sources",
        default="backtest,review,error",
        help="Comma list: backtest,review,error",
    )
    parser.add_argument("--backtest-csv", default=str(_ROOT / "data" / "validation_backtest_log.csv"))
    parser.add_argument("--review-csv", default=str(_ROOT / "data" / "review_log.csv"))
    parser.add_argument(
        "--error-csv",
        default=str(_ROOT / "data" / "false_alarm_missed_signal_log.csv"),
    )
    parser.add_argument("--include-fixtures", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args(argv)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    rows = collect_rows(
        backtest_path=Path(args.backtest_csv),
        review_path=Path(args.review_csv),
        error_path=Path(args.error_csv),
        sources=sources,
        include_fixtures=args.include_fixtures,
    )
    print(f"mapped_rows={len(rows)} sources={sources} dry_run={args.dry_run}")
    if not rows and not args.allow_empty:
        print("No rows to load (CSV empty or no human_label/decision). Nothing written.")
        return 0

    result = append_validation_audits(rows, dry_run=args.dry_run, skip_duplicates=True)
    print(
        f"inserted={result['inserted']} skipped_duplicates={result['skipped_duplicates']} "
        f"dry_run={result['dry_run']}"
    )
    print("NOTE: source CSV files were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
