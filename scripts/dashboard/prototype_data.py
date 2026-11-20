"""Shared loader for integrated early-warning & multi-judge prototype dashboards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIGNAL_GAP_PATH = PROJECT_ROOT / "data" / "signal_gap" / "signal_gap_analysis.json"
MULTI_JUDGE_PATH = PROJECT_ROOT / "data" / "validation" / "multi_judge_audit_latest.json"
CANONICAL_PATH = PROJECT_ROOT / "data" / "automation" / "canonical_signals_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_signal_gap() -> dict[str, Any]:
    return _read_json(SIGNAL_GAP_PATH)


def load_multi_judge_audit() -> dict[str, Any]:
    return _read_json(MULTI_JUDGE_PATH)


def load_canonical_summary() -> dict[str, Any]:
    data = _read_json(CANONICAL_PATH)
    clusters = data.get("signals") or data.get("clusters") or data.get("items") or []
    return {
        "available": bool(data),
        "generated_at": data.get("generated_at") or data.get("timestamp") or "",
        "cluster_count": len(clusters) if isinstance(clusters, list) else 0,
    }


def build_integrated_region_rows() -> list[dict[str, Any]]:
    """Merge signal_gap_analysis.json and multi_judge_audit_latest.json by region."""
    sg = load_signal_gap()
    audit = load_multi_judge_audit()
    audit_by_region = {r.get("region"): r for r in audit.get("results", []) if r.get("region")}

    regions = list(sg.keys()) or list(audit_by_region.keys())
    rows: list[dict[str, Any]] = []
    for reg in regions:
        s_item = sg.get(reg, {})
        a_item = audit_by_region.get(reg, {})
        tev1 = a_item.get("tev1", {})
        gemma = a_item.get("gemma2", {})
        critic = a_item.get("deepseek_r1", {})
        presiding = a_item.get("presiding_judge", {})
        nim = a_item.get("nim_escalation", {})
        gov = a_item.get("governance", {})

        rows.append({
            "region": reg,
            "alert_level_ko": s_item.get("alert_level") or a_item.get("formula_alert_ko") or "-",
            "formula_alert_en": a_item.get("formula_alert_en") or "-",
            "risk_signal_score": s_item.get("risk_signal_score", a_item.get("risk_signal_score", 0.0)),
            "signal_gap_score": s_item.get("signal_gap_score", 0.0),
            "evidence_coverage": s_item.get("evidence_coverage", 0.0),
            "source_diversity": s_item.get("source_diversity", 0),
            "tev1_verdict": tev1.get("stage_verdict") or tev1.get("status") or "-",
            "gemma2_verdict": gemma.get("worst_verdict") or gemma.get("status") or "-",
            "critic_model": critic.get("model_id") or "-",
            "critic_verdict": critic.get("inference_verdict") or critic.get("status") or "-",
            "critic_note": critic.get("note") or "",
            "presiding_model": presiding.get("model_id") or "-",
            "presiding_decision": presiding.get("recommended_decision") or presiding.get("status") or "-",
            "presiding_dispute": presiding.get("key_dispute") or "",
            "presiding_rationale": presiding.get("ruling_rationale") or "",
            "nim_model": nim.get("model_id") or "-",
            "nim_status": nim.get("status") or "-",
            "nim_fact": nim.get("fact_verdict") or "-",
            "nim_inference": nim.get("inference_verdict") or "-",
            "nim_leap": nim.get("leap_type") or "-",
            "nim_note": nim.get("note") or nim.get("error") or "",
            "triggers": gov.get("triggers", []),
            "needs_human_review": bool(gov.get("needs_human_review", False)),
            "narrative": s_item.get("narrative_differences") or s_item.get("narrative_differences_en") or "",
            "evidence_phrases": s_item.get("evidence_phrases") or [],
        })
    return rows
