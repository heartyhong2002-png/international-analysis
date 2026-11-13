"""Orthogonal Multi-Judge Validation Audit Runner (VALIDATION_PLAN.md §10.4).

Runs the 3-judge orthogonal validation suite sequentially on 16GB RAM:
  1. tev1:latest     -> alert stage verdict (formula alert masked)
  2. gemma2:9b       -> claim-level evidence grounding (factuality only)
  3. deepseek-r1:7b  -> inference & leap critic (overstatement/leap only)

Evaluates T1-T8 human-review triggers without majority-vote averaging or auto-accept.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "signal_gap" / "signal_gap_analysis.json"
DEFAULT_OUTPUT = ROOT / "data" / "validation" / "multi_judge_audit_latest.json"

OLLAMA_BASE = "http://localhost:11434"
SYSTEMONE_URL = f"{OLLAMA_BASE}/v1/systemone"
CHAT_URL = f"{OLLAMA_BASE}/api/chat"

STAGE_OPTIONS = {
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

STAGE_RANK = {"NORMAL": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3, "INSUFFICIENT_EVIDENCE": -1}
FACT_WORST_ORDER = {"unsupported": 3, "unverifiable_source_missing": 2, "partial": 1, "supported": 0}
VALID_FACT_VERDICTS = set(FACT_WORST_ORDER.keys())
VALID_INFERENCE_VERDICTS = {"supported", "overstated", "insufficient"}


def _post_json(url: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    data["_latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return data


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
        if match:
            cleaned = match.group(1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return json.loads(cleaned[start : end + 1])


def _unload_model(model: str) -> None:
    """Explicitly release a loaded Ollama model from memory before the next model."""
    for url, payload in (
        (CHAT_URL, {"model": model, "keep_alive": 0, "messages": []}),
        (f"{OLLAMA_BASE}/api/generate", {"model": model, "keep_alive": 0}),
    ):
        try:
            _post_json(url, payload, timeout=15)
            return
        except Exception:
            continue


def _call_chat_json(
    model: str,
    system_prompt: str,
    user_prompt: str,
    validator,
    max_retries: int = 1,
    keep_alive: str | int = "15s",
) -> tuple[dict[str, Any] | None, str | None, str | None, float]:
    total_ms = 0.0
    last_err: str | None = None
    err_kind: str | None = None
    for _ in range(max_retries + 1):
        payload = {
            "model": model,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {"num_ctx": 4096, "temperature": 0.1},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            resp = _post_json(CHAT_URL, payload, timeout=240)
            total_ms += resp.get("_latency_ms", 0.0)
            content = resp.get("message", {}).get("content", "")
            parsed = _extract_json_object(content)
            validated = validator(parsed)
            return validated, None, None, round(total_ms, 1)
        except (ValueError, json.JSONDecodeError) as exc:
            err_kind = "schema_error"
            last_err = str(exc)
        except Exception as exc:
            err_kind = "call_error"
            last_err = str(exc)
            time.sleep(2.0)
    return None, err_kind, last_err, round(total_ms, 1)


def run_tev1_stage(item: dict[str, Any], keep_alive: str | int = "15s") -> dict[str, Any]:
    """Evaluate alert stage ONLY. Formula alert_level is strictly masked."""
    state = {
        "risk_signal_score": item.get("risk_signal_score") or 0.0,
        "evidence_coverage": round((item.get("evidence_coverage") or 0.0) / 100.0, 2),
        "source_diversity": item.get("source_diversity") or 0,
        "signal_gap_score": round((item.get("signal_gap_score") or 0.0) / 100.0, 2),
        "source_item_count": item.get("source_item_count") or 0,
        "evidence_count": len(item.get("evidence_phrases") or []),
    }
    payload = {
        "model": "tev1:latest",
        "state": state,
        "keep_alive": keep_alive,
        "options": {"num_ctx": 2048},
        "questions": {
            "alert_status": {
                "type": "choice",
                "instructions": "Which alert status best matches the structured risk state?",
                "criteria": STAGE_OPTIONS,
            }
        },
    }
    try:
        res = _post_json(SYSTEMONE_URL, payload, timeout=180)
        ans = res["answers"]["alert_status"]
        return {
            "alert_id": item["alert_id"],
            "schema_version": "v1",
            "model_id": "tev1:latest",
            "input_snapshot_id": item["snapshot_id"],
            "stage_verdict": ans.get("choice"),
            "confidence": ans.get("confidence"),
            "probabilities": ans.get("probabilities", {}),
            "basis_fields": list(state.keys()),
            "latency_ms": res.get("_latency_ms"),
            "status": "ok",
        }
    except Exception as exc:
        return {
            "alert_id": item["alert_id"],
            "schema_version": "v1",
            "model_id": "tev1:latest",
            "input_snapshot_id": item["snapshot_id"],
            "stage_verdict": None,
            "status": "error",
            "error": str(exc),
        }


def _validate_gemma(obj: dict[str, Any]) -> dict[str, Any]:
    claims = obj.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("Missing non-empty 'claims' list")
    cleaned = []
    for idx, c in enumerate(claims, 1):
        verdict = str(c.get("fact_verdict", "")).strip()
        if verdict not in VALID_FACT_VERDICTS:
            raise ValueError(f"Invalid fact_verdict: {verdict}")
        cleaned.append({
            "id": str(c.get("id") or f"E-{idx:02d}"),
            "fact_verdict": verdict,
            "matched_span": str(c.get("matched_span", ""))[:200],
            "gap_type": str(c.get("gap_type", "none")),
        })
    return {"claims": cleaned}


def run_gemma_grounding(item: dict[str, Any], keep_alive: str | int = "15s") -> dict[str, Any]:
    """Evaluate claim-level evidence grounding ONLY. No alert stage or leap check."""
    evidence = item.get("evidence_phrases") or []
    if not evidence:
        return {
            "alert_id": item["alert_id"],
            "schema_version": "v1",
            "model_id": "gemma2:9b",
            "input_snapshot_id": item["snapshot_id"],
            "claims": [
                {
                    "id": "E-01",
                    "fact_verdict": "unverifiable_source_missing",
                    "matched_span": "",
                    "gap_type": "missing_evidence",
                }
            ],
            "worst_verdict": "unverifiable_source_missing",
            "latency_ms": 0.0,
            "status": "ok",
        }
    ev_lines = "\n".join(f"- E-{i:02d}: {txt}" for i, txt in enumerate(evidence, 1))
    claim_text = item.get("narrative_differences_en") or item.get("narrative_differences") or ""
    system_prompt = (
        "You are a strict evidence-grounding auditor. Judge ONLY whether each cited evidence snippet "
        "actually supports the regional claim/summary (entity match, topic match, modality match). "
        "Do NOT judge alert severity or geopolitical policy. "
        "Allowed fact_verdict values: supported, partial, unsupported, unverifiable_source_missing. "
        "Return ONLY valid JSON: "
        '{"claims":[{"id":"E-01","fact_verdict":"...","matched_span":"...","gap_type":"..."}]}'
    )
    user_prompt = (
        f"Region: {item['region']}\n"
        f"Claim Summary:\n{claim_text}\n\n"
        f"Cited Evidence Snippets:\n{ev_lines}\n\n"
        "Output JSON only."
    )
    parsed, err_kind, err, ms = _call_chat_json(
        "gemma2:9b", system_prompt, user_prompt, _validate_gemma, keep_alive=keep_alive
    )
    if parsed is None:
        return {
            "alert_id": item["alert_id"],
            "schema_version": "v1",
            "model_id": "gemma2:9b",
            "input_snapshot_id": item["snapshot_id"],
            "claims": [],
            "worst_verdict": None,
            "latency_ms": ms,
            "status": err_kind or "schema_error",
            "error": err,
        }
    worst = max(parsed["claims"], key=lambda c: FACT_WORST_ORDER[c["fact_verdict"]])["fact_verdict"]
    return {
        "alert_id": item["alert_id"],
        "schema_version": "v1",
        "model_id": "gemma2:9b",
        "input_snapshot_id": item["snapshot_id"],
        "claims": parsed["claims"],
        "worst_verdict": worst,
        "latency_ms": ms,
        "status": "ok",
    }


def _validate_deepseek(obj: dict[str, Any]) -> dict[str, Any]:
    verdict = str(obj.get("inference_verdict", "")).strip()
    if verdict not in VALID_INFERENCE_VERDICTS:
        raise ValueError(f"Invalid inference_verdict: {verdict}")
    return {
        "inference_verdict": verdict,
        "leap_type": str(obj.get("leap_type", "none")),
        "cited_evidence_ids": [str(x) for x in (obj.get("cited_evidence_ids") or [])],
        "note": str(obj.get("note", ""))[:300],
    }


def run_deepseek_critic(item: dict[str, Any], keep_alive: str | int = "15s") -> dict[str, Any]:
    """Evaluate inference leaps / overstatement ONLY. Does not re-judge raw truth."""
    evidence = item.get("evidence_phrases") or []
    ev_lines = (
        "\n".join(f"- E-{i:02d}: {txt}" for i, txt in enumerate(evidence, 1))
        if evidence
        else "- E-01: (NO EVIDENCE PHRASES PROVIDED)"
    )
    claim_text = item.get("narrative_differences_en") or item.get("narrative_differences") or ""
    system_prompt = (
        "You are an adversarial inference & leap critic. Given the issued alert stage, summary, "
        "and evidence snippets, judge ONLY whether the conclusion overstates or makes an unjustified "
        "causal/scope leap beyond the evidence (e.g., jumping from domestic/routine news to supply-chain disruption). "
        "Allowed inference_verdict: supported, overstated, insufficient. "
        "Return ONLY valid JSON: "
        '{"inference_verdict":"...","leap_type":"none|causal_leap|scope_leap|missing_bridge","cited_evidence_ids":["E-01"],"note":"..."}'
    )
    user_prompt = (
        f"Region: {item['region']}\n"
        f"Issued Alert Stage: {item['formula_alert_en']} ({item.get('alert_level')})\n"
        f"Summary:\n{claim_text}\n\n"
        f"Evidence:\n{ev_lines}\n\n"
        "Output JSON only."
    )
    parsed, err_kind, err, ms = _call_chat_json(
        "deepseek-r1:7b", system_prompt, user_prompt, _validate_deepseek, keep_alive=keep_alive
    )
    if parsed is None:
        return {
            "alert_id": item["alert_id"],
            "schema_version": "v1",
            "model_id": "deepseek-r1:7b",
            "input_snapshot_id": item["snapshot_id"],
            "inference_verdict": None,
            "latency_ms": ms,
            "status": err_kind or "schema_error",
            "error": err,
        }
    return {
        "alert_id": item["alert_id"],
        "schema_version": "v1",
        "model_id": "deepseek-r1:7b",
        "input_snapshot_id": item["snapshot_id"],
        **parsed,
        "latency_ms": ms,
        "status": "ok",
    }


def evaluate_triggers(
    formula_en: str,
    tev1_res: dict[str, Any],
    gemma_res: dict[str, Any],
    deepseek_res: dict[str, Any],
) -> dict[str, Any]:
    triggers: list[str] = []
    tev1_stage = tev1_res.get("stage_verdict")
    gemma_worst = gemma_res.get("worst_verdict")
    ds_verdict = deepseek_res.get("inference_verdict")

    if tev1_res.get("status") != "ok" or gemma_res.get("status") != "ok" or deepseek_res.get("status") != "ok":
        triggers.append("SCHEMA_OR_CALL_ERROR")

    if tev1_stage and tev1_stage != formula_en:
        triggers.append("T1")
    if gemma_worst in {"unsupported", "unverifiable_source_missing"}:
        triggers.append("T2")

    is_warning_plus = (
        STAGE_RANK.get(formula_en, -1) >= STAGE_RANK["WARNING"]
        or STAGE_RANK.get(tev1_stage or "", -1) >= STAGE_RANK["WARNING"]
    )
    if is_warning_plus and gemma_worst == "partial":
        triggers.append("T3")

    invalidated_by_fact = gemma_worst == "unsupported"
    if is_warning_plus and ds_verdict in {"overstated", "insufficient"} and not invalidated_by_fact:
        triggers.append("T4")
    if gemma_worst and ds_verdict and gemma_worst != "supported" and ds_verdict != "supported":
        triggers.append("T5")
    if tev1_stage == "INSUFFICIENT_EVIDENCE":
        triggers.append("T6")

    only_normal_watch_diff = (
        triggers == ["T1"]
        and {formula_en, tev1_stage} == {"NORMAL", "WATCH"}
        and gemma_worst == "supported"
        and ds_verdict == "supported"
    )

    return {
        "triggers": triggers,
        "needs_human_review": bool(triggers),
        "priority": "low" if only_normal_watch_diff else ("high" if triggers else "normal"),
        "invalidated_by_unsupported_fact": invalidated_by_fact,
        "auto_accept": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run §10.4 Multi-Judge Orthogonal Audit.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--regions", type=str, default="", help="Comma-separated region keys to audit.")
    args = parser.parse_args()

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    selected = {r.strip() for r in args.regions.split(",") if r.strip()} if args.regions else None

    items: list[dict[str, Any]] = []
    for region, body in raw.items():
        if selected and region not in selected:
            continue
        snap_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        items.append({
            **body,
            "region": region,
            "alert_id": f"SG-{region}",
            "snapshot_id": snap_hash,
            "formula_alert_en": KO_TO_EN_ALERT.get(body.get("alert_level", ""), "INSUFFICIENT_EVIDENCE"),
        })

    # Sequential per-model execution to keep peak RAM <= ~5.4GB on 16GB systems
    tev1_results = {it["region"]: run_tev1_stage(it, keep_alive="15s") for it in items}
    _unload_model("tev1:latest")
    gemma_results = {it["region"]: run_gemma_grounding(it, keep_alive="15s") for it in items}
    _unload_model("gemma2:9b")
    deepseek_results = {it["region"]: run_deepseek_critic(it, keep_alive="15s") for it in items}
    _unload_model("deepseek-r1:7b")

    audit_rows: list[dict[str, Any]] = []
    all_pass_indices: list[int] = []
    for idx, it in enumerate(items):
        reg = it["region"]
        t_eval = evaluate_triggers(
            it["formula_alert_en"],
            tev1_results[reg],
            gemma_results[reg],
            deepseek_results[reg],
        )
        if not t_eval["triggers"]:
            all_pass_indices.append(idx)
        audit_rows.append({
            "alert_id": it["alert_id"],
            "region": reg,
            "formula_alert_ko": it.get("alert_level"),
            "formula_alert_en": it["formula_alert_en"],
            "risk_signal_score": it.get("risk_signal_score"),
            "tev1": tev1_results[reg],
            "gemma2": gemma_results[reg],
            "deepseek_r1": deepseek_results[reg],
            "governance": t_eval,
        })

    # T8: Random >=15% sample of all-pass items
    if all_pass_indices:
        k = max(1, round(len(all_pass_indices) * 0.15))
        for idx in random.Random(20261114).sample(all_pass_indices, min(k, len(all_pass_indices))):
            audit_rows[idx]["governance"]["triggers"].append("T8")
            audit_rows[idx]["governance"]["needs_human_review"] = True
            audit_rows[idx]["governance"]["random_audit_sample"] = True

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "multi_judge_audit_v1",
        "source_file": str(args.input),
        "total_audited": len(audit_rows),
        "needs_human_review_count": sum(1 for r in audit_rows if r["governance"]["needs_human_review"]),
        "results": audit_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== §10.4 Multi-Judge Orthogonal Audit ({len(audit_rows)} regions) ===")
    for r in audit_rows:
        gov = r["governance"]
        print(
            f"- {r['region']:28s} | Formula={r['formula_alert_en']:21s} | "
            f"tev1={str(r['tev1'].get('stage_verdict')):21s} | "
            f"Gemma={str(r['gemma2'].get('worst_verdict')):26s} | "
            f"DeepSeek={str(r['deepseek_r1'].get('inference_verdict')):12s} | "
            f"Triggers={gov['triggers']}"
        )
    print(f"\nSaved audit report to: {args.output}")


if __name__ == "__main__":
    main()
