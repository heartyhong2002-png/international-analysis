"""Run a 10-case auditable Tev1/decision-model backtest and formula discrepancy audit.

This is an advisory comparison only. It does not change the official alert
view or replace human review. Inputs are frozen, structured features across the
5 core surveillance axes, including source URLs, human review labels, and
comparison against the deterministic Risk Signal Score formula.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from analyze_signal_gap import calculate_alert_assessment

OUTPUT = ROOT / "data" / "tev1_backtest_results.json"
ENDPOINT = "http://localhost:11434/v1/systemone"

OPTIONS = {
    "NORMAL": "Low or absent risk signals.",
    "WATCH": "Early or limited signals that need monitoring.",
    "WARNING": "Multiple meaningful signals with partial or cross-source support.",
    "CRITICAL": "Strong, cross-verified and immediate operational risk signals.",
    "INSUFFICIENT_EVIDENCE": "Evidence is too weak or incomplete to classify.",
}

KO_TO_EN_ALERT = {
    "관찰": "NORMAL",
    "주의": "WATCH",
    "경보": "WARNING",
    "고경보": "CRITICAL",
    "확인 필요": "INSUFFICIENT_EVIDENCE",
}

CASES = [
    {
        "case_id": "BT-2022-UKR-01",
        "issue_axis": "russia_ukraine_europe",
        "issue_id": "ukraine_security",
        "frozen_date": "2022-02-20",
        "frozen_excerpt": "Official Russian statements deny invasion plans while independent satellite and border imagery confirm field hospitals and tactical battalion deployment.",
        "evidence_url": "https://meduza.io/feature/2026/09/23/voyna",
        "discrepancy_score": 92,
        "official_count": 5,
        "independent_count": 6,
        "public_count": 4,
        "evidence_count": 6,
        "consensus_agreement": 100.0,
        "verification_state": "CROSS_VERIFIED",
        "human_review_label": "accept",
    },
    {
        "case_id": "BT-2026-UKR-02",
        "issue_axis": "russia_ukraine_europe",
        "issue_id": "russia_sanctions_energy",
        "frozen_date": "2026-09-23",
        "frozen_excerpt": "TASS emphasizes financial stability and digital ruble rollout while Meduza reports Polish airspace incident and EU sanctions court disputes.",
        "evidence_url": "https://tass.com/politics/2191713",
        "discrepancy_score": 85,
        "official_count": 10,
        "independent_count": 10,
        "public_count": 0,
        "evidence_count": 4,
        "consensus_agreement": 66.7,
        "verification_state": "PARTIALLY_CONFIRMED",
        "human_review_label": "accept",
    },
    {
        "case_id": "BT-2024-TWN-01",
        "issue_axis": "east_asia_military_tech",
        "issue_id": "taiwan_strait",
        "frozen_date": "2024-05-23",
        "frozen_excerpt": "Official mainland statements describe routine deterrence patrols while Taiwan MND and regional outlets report joint blockade exercises around shipping lanes.",
        "evidence_url": "https://www.reuters.com/world/asia-pacific/",
        "discrepancy_score": 78,
        "official_count": 4,
        "independent_count": 5,
        "public_count": 3,
        "evidence_count": 4,
        "consensus_agreement": 66.7,
        "verification_state": "PARTIALLY_CONFIRMED",
        "human_review_label": "accept",
    },
    {
        "case_id": "BT-2026-TWN-02",
        "issue_axis": "east_asia_military_tech",
        "issue_id": "semiconductor_supply_chain",
        "frozen_date": "2026-09-15",
        "frozen_excerpt": "Customs filings and industry reports show minor lead-time adjustments in lithography components without official embargo escalation.",
        "evidence_url": "https://comtradeplus.un.org/",
        "discrepancy_score": 42,
        "official_count": 3,
        "independent_count": 4,
        "public_count": 1,
        "evidence_count": 3,
        "consensus_agreement": 66.7,
        "verification_state": "PARTIALLY_CONFIRMED",
        "human_review_label": "accept",
    },
    {
        "case_id": "BT-2024-REDSEA-01",
        "issue_axis": "middle_east_energy_shipping",
        "issue_id": "red_sea_shipping",
        "frozen_date": "2024-01-12",
        "frozen_excerpt": "Unverified single-channel Telegram claim of vessel seizure without official naval confirmation or independent media corroboration.",
        "evidence_url": "https://t.me/s/osint_sample",
        "discrepancy_score": 55,
        "official_count": 0,
        "independent_count": 1,
        "public_count": 2,
        "evidence_count": 1,
        "consensus_agreement": 33.3,
        "verification_state": "UNVERIFIED",
        "human_review_label": "revise",
    },
    {
        "case_id": "BT-2026-HORMUZ-02",
        "issue_axis": "middle_east_energy_shipping",
        "issue_id": "hormuz_iran_tension",
        "frozen_date": "2026-09-23",
        "frozen_excerpt": "Iran official media states Hormuz talks remain conditional while independent outlets and tanker proxies (FRO +21%) indicate heightened maritime risk premium.",
        "evidence_url": "https://tass.com/world/2191697",
        "discrepancy_score": 85,
        "official_count": 6,
        "independent_count": 6,
        "public_count": 3,
        "evidence_count": 5,
        "consensus_agreement": 100.0,
        "verification_state": "CROSS_VERIFIED",
        "human_review_label": "accept",
    },
    {
        "case_id": "BT-2018-USCN-01",
        "issue_axis": "us_china_strategic_trade",
        "issue_id": "us_china_trade",
        "frozen_date": "2018-07-06",
        "frozen_excerpt": "USTR and MOFCOM issue opposing tariff notices while customs and manufacturing orders show immediate bilateral shipment contraction.",
        "evidence_url": "https://ustr.gov/",
        "discrepancy_score": 88,
        "official_count": 5,
        "independent_count": 6,
        "public_count": 3,
        "evidence_count": 5,
        "consensus_agreement": 100.0,
        "verification_state": "CROSS_VERIFIED",
        "human_review_label": "accept",
    },
    {
        "case_id": "BT-2026-USCN-02",
        "issue_axis": "us_china_strategic_trade",
        "issue_id": "export_controls_bis",
        "frozen_date": "2026-09-20",
        "frozen_excerpt": "Official state portal posts general industrial self-reliance slogan; independent trade impact data is not yet available.",
        "evidence_url": "http://en.people.cn/",
        "discrepancy_score": 60,
        "official_count": 4,
        "independent_count": 0,
        "public_count": 0,
        "evidence_count": 1,
        "consensus_agreement": None,
        "verification_state": "UNVERIFIED",
        "human_review_label": "revise",
    },
    {
        "case_id": "BT-2026-ALLY-01",
        "issue_axis": "us_allies_relations",
        "issue_id": "us_korea_tariff_defense",
        "frozen_date": "2026-09-18",
        "frozen_excerpt": "Official diplomatic readout highlights alliance solidarity while local economic press and trade associations flag tariff exemption uncertainty.",
        "evidence_url": "https://www.whitehouse.gov/releases/feed/",
        "discrepancy_score": 64,
        "official_count": 4,
        "independent_count": 5,
        "public_count": 2,
        "evidence_count": 4,
        "consensus_agreement": 66.7,
        "verification_state": "PARTIALLY_CONFIRMED",
        "human_review_label": "accept",
    },
    {
        "case_id": "BT-2026-ALLY-02",
        "issue_axis": "us_allies_relations",
        "issue_id": "nato_europe_defense",
        "frozen_date": "2026-09-10",
        "frozen_excerpt": "Routine joint logistics procurement announcement reported consistently across both official ministry releases and independent defense media.",
        "evidence_url": "https://www.nato.int/",
        "discrepancy_score": 15,
        "official_count": 2,
        "independent_count": 2,
        "public_count": 0,
        "evidence_count": 2,
        "consensus_agreement": 33.3,
        "verification_state": "CROSS_VERIFIED",
        "human_review_label": "accept",
    },
]


def call_tev1(state: dict) -> dict:
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
    discrepancy_count = 0

    for case in CASES:
        formula = calculate_alert_assessment(
            discrepancy_score=case["discrepancy_score"],
            official_count=case["official_count"],
            independent_count=case["independent_count"],
            public_count=case["public_count"],
            consensus_agreement=case["consensus_agreement"],
            evidence_count=case["evidence_count"],
        )
        formula_en = KO_TO_EN_ALERT.get(formula["alert_level"], "INSUFFICIENT_EVIDENCE")

        state = {
            "risk_signal_score": formula["risk_signal_score"],
            "evidence_coverage": round(formula["evidence_coverage"] / 100.0, 2),
            "source_diversity": formula["source_diversity"],
            "verification_state": case["verification_state"],
            "signal_gap_score": round(formula["signal_gap_score"] / 100.0, 2),
        }

        try:
            result = call_tev1(state)
            answer = result["answers"]["alert_status"]
            tev1_choice = answer.get("choice")
            is_discrepant = tev1_choice != formula_en
            if is_discrepant:
                discrepancy_count += 1

            rows.append({
                "case_id": case["case_id"],
                "issue_axis": case["issue_axis"],
                "issue_id": case["issue_id"],
                "frozen_date": case["frozen_date"],
                "frozen_excerpt": case["frozen_excerpt"],
                "evidence_url": case["evidence_url"],
                "verification_state": case["verification_state"],
                "human_review_label": case["human_review_label"],
                "formula_assessment": formula,
                "formula_alert_en": formula_en,
                "tev1_choice": tev1_choice,
                "tev1_probabilities": answer.get("probabilities", {}),
                "tev1_confidence": answer.get("confidence"),
                "formula_vs_tev1_discrepancy": is_discrepant,
                "human_review_required": bool(formula["human_review_required"] or is_discrepant),
                "latency_ms": result.get("latency_ms"),
                "status": "ok",
            })
        except Exception as exc:
            rows.append({
                "case_id": case["case_id"],
                "issue_axis": case["issue_axis"],
                "issue_id": case["issue_id"],
                "formula_assessment": formula,
                "formula_alert_en": formula_en,
                "status": "error",
                "error": str(exc),
            })

    ok = [row for row in rows if row["status"] == "ok"]
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "tev1",
        "endpoint": ENDPOINT,
        "purpose": "advisory comparison & discrepancy audit against deterministic Risk Signal Score; not the official alert source",
        "case_count": len(rows),
        "successful_calls": len(ok),
        "agreement_with_formula_count": len(ok) - discrepancy_count,
        "discrepancy_with_formula_count": discrepancy_count,
        "results": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "case_count": len(rows),
        "successful_calls": len(ok),
        "agreement_count": len(ok) - discrepancy_count,
        "discrepancy_count": discrepancy_count,
        "comparison": {
            row["case_id"]: {
                "formula": f"{row['formula_assessment']['alert_level']} ({row['formula_alert_en']})",
                "tev1": row.get("tev1_choice"),
                "discrepancy": row.get("formula_vs_tev1_discrepancy"),
            }
            for row in ok
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
