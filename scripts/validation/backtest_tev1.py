"""Run a small, auditable Tev1/decision-model backtest.

This is an advisory comparison only. It does not change the official alert
view or replace human review. Inputs are the frozen, structured features from
the existing early-warning case template.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "tev1_backtest_results.json"
ENDPOINT = "http://localhost:11434/v1/systemone"

OPTIONS = {
    "NORMAL": "Low or absent risk signals.",
    "WATCH": "Early or limited signals that need monitoring.",
    "WARNING": "Multiple meaningful signals with partial or cross-source support.",
    "CRITICAL": "Strong, cross-verified and immediate operational risk signals.",
    "INSUFFICIENT_EVIDENCE": "Evidence is too weak or incomplete to classify.",
}

CASES = [
    {
        "case_id": "BT-2022-UKR",
        "issue_id": "ukraine_security",
        "risk_signal_score": 92,
        "evidence_coverage": 0.90,
        "source_diversity": 4,
        "verification_state": "CROSS_VERIFIED",
        "signal_gap_score": 0.92,
        "expected_review": "accept",
    },
    {
        "case_id": "BT-2024-TWN",
        "issue_id": "taiwan_strait",
        "risk_signal_score": 75,
        "evidence_coverage": 0.75,
        "source_diversity": 3,
        "verification_state": "PARTIALLY_CONFIRMED",
        "signal_gap_score": 0.75,
        "expected_review": "accept",
    },
    {
        "case_id": "BT-2024-REDSEA",
        "issue_id": "red_sea_shipping",
        "risk_signal_score": 45,
        "evidence_coverage": 0.30,
        "source_diversity": 1,
        "verification_state": "UNVERIFIED",
        "signal_gap_score": 0.45,
        "expected_review": "revise",
    },
    {
        "case_id": "BT-2018-USCN",
        "issue_id": "us_china_trade",
        "risk_signal_score": 82,
        "evidence_coverage": 0.88,
        "source_diversity": 3,
        "verification_state": "CROSS_VERIFIED",
        "signal_gap_score": 0.82,
        "expected_review": "accept",
    },
]


def call_tev1(case: dict) -> dict:
    state = {
        "risk_signal_score": case["risk_signal_score"],
        "evidence_coverage": case["evidence_coverage"],
        "source_diversity": case["source_diversity"],
        "verification_state": case["verification_state"],
        "signal_gap_score": case["signal_gap_score"],
    }
    payload = {
        "model": "tev1",
        "state": state,
        "questions": {
            "alert_status": {
                "type": "choice",
                "instructions": "Which alert status best matches the structured risk state?",
                "criteria": OPTIONS,
            }
        },
    }
    request = Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return result


def main() -> None:
    rows = []
    for case in CASES:
        try:
            result = call_tev1(case)
            answer = result["answers"]["alert_status"]
            rows.append({
                **case,
                "tev1_choice": answer.get("choice"),
                "probabilities": answer.get("probabilities", {}),
                "confidence": answer.get("confidence"),
                "latency_ms": result.get("latency_ms"),
                "status": "ok",
            })
        except Exception as exc:  # preserve the case-level failure for audit
            rows.append({**case, "status": "error", "error": str(exc)})

    ok = [row for row in rows if row["status"] == "ok"]
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "tev1",
        "endpoint": ENDPOINT,
        "purpose": "advisory comparison; not the official alert source",
        "case_count": len(rows),
        "successful_calls": len(ok),
        "results": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "case_count": len(rows),
        "successful_calls": len(ok),
        "choices": {row["case_id"]: row.get("tev1_choice") for row in ok},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
