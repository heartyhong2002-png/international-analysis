"""Risk Signal Score pipeline → atomic DB evidence writer.

Runs a 3-model consensus (Mistral-NeMo, Qwen2.5, EXAONE) over official vs
independent RSS narratives, computes Risk Signal Score / alert assessment,
and persists via ``write_scoring_bundle``.

Hard rules:
  - Never invent Alert Level from article counts alone.
  - Alert events are written only when the assessment maps to WATCH/WARNING/CRITICAL.
  - Prediction language is forbidden; outputs are risk signals + evidence +
    verification_state framing only.
  - tev1 is optional auxiliary comparison — never the official Alert Level.

Usage:
  python scripts/analysis/run_risk_scoring.py --smoke --dry-run
  python scripts/analysis/run_risk_scoring.py --smoke --commit
  python scripts/analysis/run_risk_scoring.py --region Russia --commit
  python scripts/analysis/run_risk_scoring.py --smoke --commit --with-tev1-aux
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd
import requests

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "scripts"
_ANALYSIS = _SCRIPTS / "analysis"
_DB = _SCRIPTS / "db"
for _p in (_ROOT, _SCRIPTS, _ANALYSIS, _DB):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from alert_level_map import should_raise_alert, to_db_alert_level  # noqa: E402
from analyze_signal_gap import (  # noqa: E402
    SCORING_VERSION,
    calculate_alert_assessment,
)
from db_connection import get_connection  # noqa: E402
from evidence_writer import (  # noqa: E402
    AlertEventInput,
    EvidenceInput,
    RiskScoreInput,
    ScoringBundle,
    SignalGapInput,
    ValidationJudgmentInput,
    bundle_to_dict,
    write_scoring_bundle,
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_GENERATE = f"{OLLAMA_URL}/api/generate"
TEV1_ENDPOINT = f"{OLLAMA_URL}/v1/systemone"
TEV1_MODEL = os.getenv("TEV1_MODEL", "tev1:latest")

CONSENSUS_MODELS = [
    "mistral-nemo:latest",
    "qwen2.5:7b",
    "exaone3.5:7.8b",
]

INPUT_CSV = _ROOT / "data" / "signal_gap" / "rss_signal_gap_latest.csv"
OUTPUT_DIR = _ROOT / "data" / "signal_gap"
OUTPUT_JSON = OUTPUT_DIR / "risk_scoring_latest.json"

PIPELINE_SCORING_VERSION = "risk-signal-consensus-v1"
GAP_METHOD_VERSION = "gap-method-consensus-v1"

DISCREPANCY_PROMPT = """You are a geopolitical risk-signal analyst.
Compare ONLY the supplied Official vs Independent narratives.

[Official State Media]
{official_text}

[Independent / Non-official Media]
{independent_text}

Task:
1. Compute a Signal Gap Discrepancy Score from 0 to 100
   (0 = same narrative, 100 = opposing narratives or extreme information gap).
2. Summarize observed differences in 2-3 sentences.
3. Cite up to two short evidence phrases copied from the supplied text.
4. Set verification_state to one of:
   UNVERIFIED | PARTIALLY_CONFIRMED | CROSS_VERIFIED | INSUFFICIENT_EVIDENCE
5. Do NOT predict future events. Do NOT claim outcomes are certain.
   Use only risk-signal / evidence / confirmation-needed language.

Respond with JSON only (no markdown):
{{
  "discrepancy_score": 0,
  "narrative_differences": "...",
  "evidence_phrases": ["..."],
  "verification_state": "PARTIALLY_CONFIRMED"
}}
"""

FORBIDDEN_PREDICTION_RE = re.compile(
    r"\b(will (happen|occur|escalate)|guaranteed forecast|prediction accuracy|"
    r"future event prediction|반드시 발생|예측 성공|확정된 예보)\b",
    re.IGNORECASE,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _issue_key_for_region(region: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", region.strip()).strip("_").upper()
    return f"RSS_{cleaned}" if cleaned else "RSS_UNKNOWN"


def _list_available_models() -> set[str]:
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=15)
        res.raise_for_status()
        names = {m.get("name", "") for m in res.json().get("models", [])}
        return {n for n in names if n}
    except Exception as exc:
        print(f"⚠ Ollama /api/tags failed: {exc}")
        return set()


def _resolve_consensus_models(available: set[str]) -> list[str]:
    resolved: list[str] = []
    for wanted in CONSENSUS_MODELS:
        if wanted in available:
            resolved.append(wanted)
            continue
        base = wanted.split(":")[0]
        alt = next((n for n in available if n == base or n.startswith(base + ":")), None)
        if alt:
            resolved.append(alt)
    return resolved


def call_ollama_json(model: str, prompt: str, timeout: int = 180) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
    }
    try:
        res = requests.post(OLLAMA_GENERATE, json=payload, timeout=timeout)
        if res.status_code != 200:
            return {"error": f"HTTP {res.status_code}", "model": model}
        raw = (res.json().get("response") or "").strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return {"error": "JSON parse failed", "model": model, "raw": raw[:400]}
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            return {"error": "non-object JSON", "model": model}
        parsed["model"] = model
        return parsed
    except Exception as exc:
        return {"error": str(exc), "model": model}


def call_tev1_aux(assessment: dict[str, Any], verification_state: str) -> dict[str, Any]:
    """Optional advisory tev1 call — never used as official Alert Level.

    Uses Ollama decision API ``POST /v1/systemone`` (tev1 has capability
    ``decision`` and does not support ``/api/generate``). Payload shape:
    ``{model, state, questions.<id>.{type, instructions, criteria}}``.
    """
    coverage = float(assessment.get("evidence_coverage") or 0.0) / 100.0
    state = {
        "risk_signal_score": float(assessment.get("risk_signal_score") or 0.0),
        "evidence_coverage": round(coverage, 4),
        "source_diversity": int(assessment.get("source_diversity") or 0),
        "verification_state": verification_state,
        "signal_gap_score": float(assessment.get("signal_gap_score") or 0.0) / 100.0,
    }
    payload = {
        "model": TEV1_MODEL,
        "state": state,
        "questions": {
            "alert_status": {
                "type": "choice",
                "instructions": (
                    "Advisory only. Which status best matches the structured "
                    "risk-signal state? Do not treat this as an official Alert Level."
                ),
                "criteria": {
                    "NORMAL": "Low or absent risk signals.",
                    "WATCH": "Early or limited signals that need monitoring.",
                    "WARNING": "Multiple meaningful signals with partial support.",
                    "CRITICAL": "Strong cross-verified operational risk signals.",
                    "INSUFFICIENT_EVIDENCE": "Evidence too weak to classify.",
                },
            }
        },
    }
    request_meta = {
        "endpoint": TEV1_ENDPOINT,
        "model": TEV1_MODEL,
        "payload_keys": sorted(payload.keys()),
        "state_keys": sorted(state.keys()),
    }
    try:
        req = Request(
            TEV1_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        answer = (body.get("answers") or {}).get("alert_status") or {}
        choice = answer.get("choice")
        return {
            "ok": True,
            "tev1_choice": choice,
            "confidence": answer.get("confidence"),
            "probabilities": answer.get("probabilities"),
            "raw_keys": sorted(body.keys()),
            "advisory_only": True,
            "request": request_meta,
        }
    except HTTPError as exc:
        err_text = ""
        try:
            err_text = exc.read().decode("utf-8", errors="replace")[:800]
        except Exception:
            err_text = ""
        hint = None
        err_msg = err_text
        try:
            parsed = json.loads(err_text) if err_text else {}
            if isinstance(parsed, dict) and parsed.get("error"):
                err_msg = str(parsed["error"])
                low = err_msg.lower()
                if "no longer supported" in low or "re-download" in low:
                    hint = (
                        "tev1 GGUF blob is outdated for this Ollama build; "
                        "re-pull via POST http://localhost:11434/api/pull "
                        '{"name":"tev1:latest"} (or `ollama pull tev1:latest`).'
                    )
        except json.JSONDecodeError:
            pass
        out: dict[str, Any] = {
            "ok": False,
            "error": f"HTTP {exc.code}: {err_msg or exc.reason}",
            "advisory_only": True,
            "request": request_meta,
        }
        if hint:
            out["hint"] = hint
        return out
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "advisory_only": True,
            "request": request_meta,
        }


def _sanitize_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = str(text).strip()
    if FORBIDDEN_PREDICTION_RE.search(cleaned):
        cleaned = FORBIDDEN_PREDICTION_RE.sub("[risk-signal framing]", cleaned)
    return cleaned


def consensus_discrepancy(
    official_text: str,
    independent_text: str,
    models: list[str],
) -> dict[str, Any]:
    prompt = DISCREPANCY_PROMPT.format(
        official_text=official_text[:3500],
        independent_text=independent_text[:3500],
    )
    model_outputs: list[dict[str, Any]] = []
    for model in models:
        print(f"    🤖 consensus call: {model}")
        out = call_ollama_json(model, prompt)
        model_outputs.append(out)

    valid_scores: list[float] = []
    evidence: list[str] = []
    narratives: list[str] = []
    verification_states: list[str] = []
    errors: list[dict[str, Any]] = []

    for out in model_outputs:
        if "error" in out:
            errors.append({"model": out.get("model"), "error": out["error"]})
            continue
        try:
            score = float(out.get("discrepancy_score"))
            score = max(0.0, min(100.0, score))
            valid_scores.append(score)
        except (TypeError, ValueError):
            errors.append({"model": out.get("model"), "error": "bad discrepancy_score"})
            continue
        phrases = out.get("evidence_phrases") or []
        if isinstance(phrases, list):
            evidence.extend(str(p).strip() for p in phrases if str(p).strip())
        nd = _sanitize_text(out.get("narrative_differences"))
        if nd:
            narratives.append(nd)
        vs = str(out.get("verification_state") or "").strip().upper()
        if vs:
            verification_states.append(vs)

    if not valid_scores:
        return {
            "status": "FAILED",
            "discrepancy_score": None,
            "agreement_ratio": 0.0,
            "evidence_phrases": [],
            "narrative_differences": "모델 합의 실패 — 확인 필요",
            "verification_state": "INSUFFICIENT_EVIDENCE",
            "model_outputs": model_outputs,
            "errors": errors,
            "models_used": models,
        }

    median_score = round(statistics.median(valid_scores), 1)
    if len(valid_scores) == 1:
        agreement = 1.0 / max(len(models), 1)
        status = "SINGLE"
    else:
        # Scores within 15 points of the median count as agreeing.
        agree_n = sum(1 for s in valid_scores if abs(s - median_score) <= 15.0)
        agreement = round(agree_n / len(valid_scores), 3)
        if agree_n == len(valid_scores) and len(valid_scores) >= 3:
            status = "UNANIMOUS"
        elif agree_n >= 2:
            status = "MAJORITY"
        else:
            status = "SPLIT"

    # Majority verification_state among valid responses.
    vs_final = "PARTIALLY_CONFIRMED"
    if verification_states:
        vs_final = max(set(verification_states), key=verification_states.count)

    # Deduplicate evidence, keep order.
    seen: set[str] = set()
    uniq_evidence: list[str] = []
    for phrase in evidence:
        if phrase not in seen:
            seen.add(phrase)
            uniq_evidence.append(phrase)

    narrative = narratives[0] if narratives else "신호 괴리 요약 없음 — 확인 필요"
    return {
        "status": status,
        "discrepancy_score": median_score,
        "score_distribution": valid_scores,
        "agreement_ratio": agreement,
        "evidence_phrases": uniq_evidence[:6],
        "narrative_differences": narrative,
        "verification_state": vs_final,
        "model_outputs": model_outputs,
        "errors": errors,
        "models_used": models,
    }


def load_region_texts(csv_path: Path, region: str) -> tuple[str, str, int, int, list[dict]]:
    df = pd.read_csv(csv_path)
    region_df = df[df["Region"] == region]
    official = region_df[region_df["Source_Type"] == "Official"]
    independent = region_df[region_df["Source_Type"] == "Independent"]
    off_rows = official.head(5)
    ind_rows = independent.head(5)
    off_text = "\n".join(
        f"{r.Title}: {r.Summary}" for r in off_rows.itertuples() if pd.notna(r.Summary)
    )
    ind_text = "\n".join(
        f"{r.Title}: {r.Summary}" for r in ind_rows.itertuples() if pd.notna(r.Summary)
    )
    evidence_meta = []
    for r in list(off_rows.itertuples())[:2]:
        evidence_meta.append(
            {
                "family": "official",
                "title": getattr(r, "Title", ""),
                "url": getattr(r, "Link", None),
                "quote": str(getattr(r, "Summary", "") or "")[:280],
            }
        )
    for r in list(ind_rows.itertuples())[:2]:
        evidence_meta.append(
            {
                "family": "independent",
                "title": getattr(r, "Title", ""),
                "url": getattr(r, "Link", None),
                "quote": str(getattr(r, "Summary", "") or "")[:280],
            }
        )
    return off_text, ind_text, len(official), len(independent), evidence_meta


def build_bundle_for_issue(
    *,
    issue_key: str,
    region: str,
    consensus: dict[str, Any],
    assessment: dict[str, Any],
    evidence_meta: list[dict],
    official_count: int,
    independent_count: int,
    tev1_aux: dict[str, Any] | None,
    run_key: str,
    executed_at: datetime,
) -> ScoringBundle:
    """Build ScoringBundle. Alert Level comes only from explicit assessment mapping."""
    display_level = assessment["alert_level"]
    db_level = to_db_alert_level(display_level)
    risk = float(assessment["risk_signal_score"])
    gap = float(assessment["signal_gap_score"])
    coverage = float(assessment["evidence_coverage"])
    agreement = assessment.get("consensus_agreement")
    agreement_f = float(agreement) if agreement is not None else 0.0

    # Split contribution across families (sum ≈ risk_signal_score).
    official_contrib = round(risk * 0.35, 2)
    independent_contrib = round(risk * 0.40, 2)
    llm_contrib = round(risk - official_contrib - independent_contrib, 2)

    scores = [
        RiskScoreInput(
            issue_key=issue_key,
            signal_family="official",
            metric_name="official_item_count",
            observed_at=executed_at,
            raw_value=float(official_count),
            normalized_score=min(100.0, official_count / 15.0 * 100.0),
            contribution_score=official_contrib,
            confidence_score=round(agreement_f / 100.0, 4) if agreement is not None else None,
            evidence_count=min(official_count, 5),
            quality_status="usable" if official_count else "missing",
            component_key=f"{issue_key}|official|official_item_count",
            evidence_summary=f"Official RSS items observed for {region}: {official_count}",
        ),
        RiskScoreInput(
            issue_key=issue_key,
            signal_family="independent",
            metric_name="independent_item_count",
            observed_at=executed_at,
            raw_value=float(independent_count),
            normalized_score=min(100.0, independent_count / 15.0 * 100.0),
            contribution_score=independent_contrib,
            confidence_score=round(agreement_f / 100.0, 4) if agreement is not None else None,
            evidence_count=min(independent_count, 5),
            quality_status="usable" if independent_count else "missing",
            component_key=f"{issue_key}|independent|independent_item_count",
            evidence_summary=f"Independent RSS items observed for {region}: {independent_count}",
        ),
        RiskScoreInput(
            issue_key=issue_key,
            signal_family="llm",
            metric_name="consensus_discrepancy",
            observed_at=executed_at,
            raw_value=float(consensus.get("discrepancy_score") or 0.0),
            normalized_score=float(consensus.get("discrepancy_score") or 0.0),
            contribution_score=llm_contrib,
            confidence_score=round(float(consensus.get("agreement_ratio") or 0.0), 4),
            evidence_count=len(consensus.get("evidence_phrases") or []),
            quality_status="usable" if consensus.get("discrepancy_score") is not None else "failed",
            component_key=f"{issue_key}|llm|consensus_discrepancy",
            evidence_summary=(
                f"3-model consensus status={consensus.get('status')}; "
                f"verification_state={consensus.get('verification_state')}"
            ),
        ),
    ]

    gaps = [
        SignalGapInput(
            issue_key=issue_key,
            snapshot_at=executed_at,
            official_score=round(min(100.0, official_count / 15.0 * 100.0), 1),
            independent_score=round(min(100.0, independent_count / 15.0 * 100.0), 1),
            public_score=None,
            market_score=None,
            gap_score=gap,
            evidence_coverage_pct=coverage,
            source_diversity=int(assessment.get("source_diversity") or 0),
            methodology_version=GAP_METHOD_VERSION,
            narrative_summary=_sanitize_text(consensus.get("narrative_differences")),
        )
    ]

    alerts: list[AlertEventInput] = []
    judgments: list[ValidationJudgmentInput] = []

    # Explicit Alert Level only — never invent from article counts.
    if db_level and should_raise_alert(display_level):
        evidence_rows: list[EvidenceInput] = []
        for meta in evidence_meta:
            family = meta["family"]
            component = (
                f"{issue_key}|official|official_item_count"
                if family == "official"
                else f"{issue_key}|independent|independent_item_count"
            )
            evidence_rows.append(
                EvidenceInput(
                    evidence_role="supporting" if family == "official" else "corroborating",
                    source_table="rss_signal_gap_latest",
                    source_record_key=f"{region}:{family}:{hashlib.sha1((meta.get('url') or meta.get('title') or '').encode()).hexdigest()[:12]}",
                    source_url=meta.get("url"),
                    evidence_quote=(meta.get("quote") or "")[:500] or None,
                    relevance_score=0.75,
                    observed_at=executed_at,
                    score_component_key=component,
                )
            )
        for phrase in (consensus.get("evidence_phrases") or [])[:2]:
            evidence_rows.append(
                EvidenceInput(
                    evidence_role="supporting",
                    source_table="llm_consensus",
                    source_record_key=f"{issue_key}:phrase:{hashlib.sha1(phrase.encode()).hexdigest()[:12]}",
                    evidence_quote=phrase[:500],
                    relevance_score=0.7,
                    observed_at=executed_at,
                    score_component_key=f"{issue_key}|llm|consensus_discrepancy",
                )
            )

        local_key = f"{issue_key}|raised"
        rationale = (
            f"display_alert={display_level}; db_alert={db_level}; "
            f"risk_signal_score={risk}; signal_gap={gap}; "
            f"consensus={consensus.get('status')}; "
            f"verification_state={consensus.get('verification_state')}; "
            f"reason={assessment.get('alert_reason')}"
        )
        if tev1_aux and tev1_aux.get("ok"):
            rationale += f"; tev1_aux={tev1_aux.get('tev1_choice')} (advisory only)"

        alerts.append(
            AlertEventInput(
                issue_key=issue_key,
                event_type="raised",
                alert_level=db_level,
                decision_rationale=rationale[:1900],
                lifecycle_status=(
                    "held_for_review"
                    if assessment.get("human_review_required")
                    else "active"
                ),
                triggered_at=executed_at,
                requires_human_review=bool(assessment.get("human_review_required")),
                evidence=evidence_rows,
                local_key=local_key,
            )
        )
        judgments.append(
            ValidationJudgmentInput(
                issue_key=issue_key,
                audit_type="llm_scoring_pending_review",
                verdict="pending_review",
                rationale=(
                    "Automated scoring run queued for human review. "
                    "Not a prediction outcome; risk-signal persistence only."
                ),
                expected_alert_level=db_level,
                observed_outcome=(
                    f"verification_state={consensus.get('verification_state')}; "
                    f"consensus={consensus.get('status')}"
                ),
                reviewer="run_risk_scoring",
                reviewed_at=executed_at,
                evidence_sufficiency=(
                    "sufficient"
                    if not assessment.get("human_review_required")
                    else "pending"
                ),
                source_key=f"llm-score:{run_key}:{issue_key}",
                alert_local_key=local_key,
            )
        )
    else:
        # Persist a judgment that we intentionally withheld an alert.
        judgments.append(
            ValidationJudgmentInput(
                issue_key=issue_key,
                audit_type="llm_scoring_withheld_alert",
                verdict="insufficient_evidence"
                if display_level == "확인 필요"
                else "pending_review",
                rationale=(
                    f"No alert_event written. display_alert={display_level}; "
                    f"reason={assessment.get('alert_reason')}. "
                    "Alert Level was not invented from article counts."
                ),
                expected_alert_level=None,
                observed_outcome=f"withheld; risk_signal_score={risk}",
                reviewer="run_risk_scoring",
                reviewed_at=executed_at,
                evidence_sufficiency="insufficient"
                if display_level == "확인 필요"
                else "pending",
                source_key=f"llm-score-withheld:{run_key}:{issue_key}",
                alert_local_key=None,
            )
        )

    config_payload = {
        "models": consensus.get("models_used"),
        "pipeline": PIPELINE_SCORING_VERSION,
        "base_scoring": SCORING_VERSION,
        "gap_method": GAP_METHOD_VERSION,
    }
    config_hash = hashlib.sha256(
        json.dumps(config_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    notes = (
        f"Risk Signal Score consensus run for region={region}. "
        f"display_alert={display_level}; db_alert={db_level or 'none'}; "
        f"prediction language forbidden."
    )
    if tev1_aux:
        notes += f" tev1_aux={tev1_aux.get('tev1_choice') or tev1_aux.get('error')} (advisory)."

    return ScoringBundle(
        run_key=run_key,
        scoring_version=PIPELINE_SCORING_VERSION,
        config_hash=config_hash,
        window_start=executed_at,
        window_end=executed_at,
        executed_at=executed_at,
        status="completed" if consensus.get("discrepancy_score") is not None or display_level == "확인 필요" else "partial",
        notes=notes[:1900],
        scores=scores,
        gaps=gaps,
        alerts=alerts,
        judgments=judgments,
    )


def score_region(
    region: str,
    *,
    models: list[str],
    with_tev1: bool = False,
) -> dict[str, Any]:
    off_text, ind_text, off_n, ind_n, evidence_meta = load_region_texts(INPUT_CSV, region)
    issue_key = _issue_key_for_region(region)

    if not off_text or not ind_text:
        consensus = {
            "status": "FAILED",
            "discrepancy_score": None,
            "agreement_ratio": 0.0,
            "evidence_phrases": [],
            "narrative_differences": "공식 또는 독립 신호가 부족해 비교 확인이 필요함",
            "verification_state": "INSUFFICIENT_EVIDENCE",
            "models_used": models,
        }
    else:
        consensus = consensus_discrepancy(off_text, ind_text, models)

    assessment = calculate_alert_assessment(
        discrepancy_score=consensus.get("discrepancy_score") or 0,
        official_count=off_n,
        independent_count=ind_n,
        evidence_count=len(consensus.get("evidence_phrases") or []),
        consensus_agreement=round(float(consensus.get("agreement_ratio") or 0.0) * 100.0, 1),
    )

    tev1_aux = None
    if with_tev1:
        print("    🔎 tev1 auxiliary (advisory only)...")
        tev1_aux = call_tev1_aux(
            assessment,
            str(consensus.get("verification_state") or "INSUFFICIENT_EVIDENCE"),
        )

    return {
        "region": region,
        "issue_key": issue_key,
        "official_count": off_n,
        "independent_count": ind_n,
        "consensus": consensus,
        "assessment": assessment,
        "evidence_meta": evidence_meta,
        "tev1_aux": tev1_aux,
        "db_alert_level": to_db_alert_level(assessment["alert_level"]),
    }


def run(
    *,
    regions: list[str],
    commit: bool,
    with_tev1: bool,
) -> int:
    if not INPUT_CSV.exists():
        print(f"❌ missing input CSV: {INPUT_CSV}")
        return 1

    available = _list_available_models()
    models = _resolve_consensus_models(available)
    if len(models) < 2:
        print(f"❌ need ≥2 consensus models available; found {models}")
        print(f"   Ollama models: {sorted(available)}")
        return 1
    print(f"✓ consensus models ({len(models)}): {models}")

    df = pd.read_csv(INPUT_CSV)
    all_regions = sorted(df["Region"].dropna().unique().tolist())
    selected = [r for r in regions if r in all_regions]
    if not selected:
        print(f"❌ none of {regions} found in CSV. available={all_regions}")
        return 1

    executed_at = _utc_now()
    # run_key must be ≤36 chars (CHAR(36))
    run_key = f"RS-{executed_at.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    assert len(run_key) <= 36

    issue_results: list[dict[str, Any]] = []
    for region in selected:
        print(f"\n[{region}] scoring...")
        result = score_region(region, models=models, with_tev1=with_tev1)
        print(
            f"    risk={result['assessment']['risk_signal_score']} "
            f"display={result['assessment']['alert_level']} "
            f"db={result['db_alert_level'] or 'none'} "
            f"consensus={result['consensus']['status']}"
        )
        issue_results.append(result)

    # One ScoringBundle per run, multiple issues.
    all_scores: list[RiskScoreInput] = []
    all_gaps: list[SignalGapInput] = []
    all_alerts: list[AlertEventInput] = []
    all_judgments: list[ValidationJudgmentInput] = []

    for result in issue_results:
        partial = build_bundle_for_issue(
            issue_key=result["issue_key"],
            region=result["region"],
            consensus=result["consensus"],
            assessment=result["assessment"],
            evidence_meta=result["evidence_meta"],
            official_count=result["official_count"],
            independent_count=result["independent_count"],
            tev1_aux=result.get("tev1_aux"),
            run_key=run_key,
            executed_at=executed_at,
        )
        all_scores.extend(partial.scores)
        all_gaps.extend(partial.gaps)
        all_alerts.extend(partial.alerts)
        all_judgments.extend(partial.judgments)
        # Prefer config/notes from last partial — rebuild once below.

    config_payload = {
        "models": models,
        "pipeline": PIPELINE_SCORING_VERSION,
        "regions": selected,
        "base_scoring": SCORING_VERSION,
    }
    bundle = ScoringBundle(
        run_key=run_key,
        scoring_version=PIPELINE_SCORING_VERSION,
        config_hash=hashlib.sha256(
            json.dumps(config_payload, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        window_start=executed_at,
        window_end=executed_at,
        executed_at=executed_at,
        status="completed",
        notes=(
            f"Risk Signal Score consensus for regions={selected}. "
            "Alert Level explicitly mapped from assessment; never from article counts. "
            "Prediction language forbidden."
        ),
        scores=all_scores,
        gaps=all_gaps,
        alerts=all_alerts,
        judgments=all_judgments,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    serializable = {
        "run_key": run_key,
        "scoring_version": PIPELINE_SCORING_VERSION,
        "executed_at": executed_at.isoformat() + "Z",
        "regions": selected,
        "models": models,
        "issues": [
            {
                "issue_key": r["issue_key"],
                "region": r["region"],
                "assessment": r["assessment"],
                "db_alert_level": r["db_alert_level"],
                "consensus_status": r["consensus"].get("status"),
                "verification_state": r["consensus"].get("verification_state"),
                "discrepancy_score": r["consensus"].get("discrepancy_score"),
                "tev1_aux": r.get("tev1_aux"),
                "will_raise_alert": bool(r["db_alert_level"]),
            }
            for r in issue_results
        ],
        "bundle_summary": {
            "score_count": len(bundle.scores),
            "gap_count": len(bundle.gaps),
            "alert_count": len(bundle.alerts),
            "judgment_count": len(bundle.judgments),
        },
    }
    OUTPUT_JSON.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✓ wrote {OUTPUT_JSON}")

    if not commit:
        print("DRY-RUN: skipping DB write (--commit to persist via write_scoring_bundle)")
        print(json.dumps(serializable["bundle_summary"], indent=2))
        for issue in serializable["issues"]:
            print(
                f"  - {issue['issue_key']}: display={issue['assessment']['alert_level']} "
                f"db={issue['db_alert_level'] or 'none'} raise={issue['will_raise_alert']}"
            )
        return 0

    conn = get_connection()
    try:
        result = write_scoring_bundle(conn, bundle)
        print("✓ write_scoring_bundle OK:", json.dumps(bundle_to_dict(result), indent=2))
    finally:
        conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Risk Signal Score → DB evidence writer")
    parser.add_argument(
        "--region",
        action="append",
        dest="regions",
        help="Region name from rss_signal_gap_latest.csv (repeatable)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Score a single default region (Russia if present) for end-to-end smoke",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist via write_scoring_bundle (default is dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit dry-run (default when --commit is absent)",
    )
    parser.add_argument(
        "--with-tev1-aux",
        action="store_true",
        help="Call tev1 as advisory comparison only (not official Alert Level)",
    )
    args = parser.parse_args(argv)

    regions = list(args.regions or [])
    if args.smoke and not regions:
        regions = ["Russia"]
    if not regions:
        parser.error("provide --region and/or --smoke")

    commit = bool(args.commit) and not bool(args.dry_run)
    return run(regions=regions, commit=commit, with_tev1=bool(args.with_tev1_aux))


if __name__ == "__main__":
    raise SystemExit(main())
