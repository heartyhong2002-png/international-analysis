"""
human_blind_review.py — §10.4.3 블라인드 2단계 사람 검수 CLI 및 시트 생성기
===========================================================================

VALIDATION_PLAN.md §10.4.3(사람 검수 Stage 1 / Stage 2 블라인드) 규약을 구현합니다.

핵심 원칙:
  1. Stage 1 (모델 출력 마스킹):
     - data_cutoff 이전 원문·출처·근거 문장·산식 경보 단계·경보 요약만 노출.
     - tev1, gemma2, deepseek-r1 출력 및 트리거는 완전히 가림.
     - 사람 5항목(reviewer_decision, evidence_quote_supported, source_quality,
       interpretation_assessment, error_type) + domain_review_needed 작성 후
       stage1_locked=true 로 영구 잠금 (이후 덮어쓰기 금지).
  2. Stage 2 (잠금 후 모델 출력 공개):
     - stage1_locked=true 확인 뒤에만 3모델 감사 결과를 공개.
     - 판단 번복 시 Stage 1 원본은 보존하고 human_final_* 별도 필드 + 변경 사유 기록.
  3. 1인 검수 표기:
     - 단독 검수 시 review_mode='single_reviewer_provisional' 자동 기록.

사용법:
    # 1) Stage 1 블라인드 검수용 CSV 시트 내보내기 (모델 출력 완전 마스킹)
    .venv\\Scripts\\python.exe scripts/validation/human_blind_review.py --export

    # 2) 터미널에서 대화형으로 Stage 1(블라인드) -> 잠금 -> Stage 2(모델 비교) 진행
    .venv\\Scripts\\python.exe scripts/validation/human_blind_review.py --interactive --reviewer jungi

    # 3) 엑셀 등에서 작성 완료한 Stage 1 CSV를 잠금 처리하고 Stage 2 비교 시트 생성
    .venv\\Scripts\\python.exe scripts/validation/human_blind_review.py --reveal data/validation/pending_blind_review_stage1.csv

    # 4) 현재 검수 진행 현황 및 §10.4.6 KPI 요약 출력
    .venv\\Scripts\\python.exe scripts/validation/human_blind_review.py --status
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = REPO_ROOT / "data" / "validation" / "multi_judge_audit_latest.json"
SIGNAL_GAP_PATH = REPO_ROOT / "data" / "signal_gap" / "signal_gap_analysis.json"
STAGE1_CSV_PATH = REPO_ROOT / "data" / "validation" / "pending_blind_review_stage1.csv"
STAGE2_CSV_PATH = REPO_ROOT / "data" / "validation" / "stage2_comparison_sheet.csv"
REVIEW_JSON_PATH = REPO_ROOT / "data" / "validation" / "human_blind_reviews.json"
REVIEW_LOG_CSV_PATH = REPO_ROOT / "data" / "validation" / "human_blind_review_log.csv"

VALID_DECISIONS = ("accept", "revise", "reject")
VALID_EVIDENCE = ("supported", "partial", "unsupported")
VALID_SOURCE_QUALITY = ("primary", "reputable_secondary", "unknown")
VALID_INTERPRETATION = ("supported", "overstated", "insufficient")
VALID_ERROR_TYPES = (
    "none",
    "evidence_gap",
    "overclaim",
    "false_alarm_candidate",
    "missed_signal_candidate",
)
VALID_YN = ("no", "yes")

STAGE1_CSV_COLUMNS = [
    "alert_id",
    "region",
    "analyzed_at",
    "formula_alert_ko",
    "formula_alert_en",
    "risk_signal_score",
    "source_item_count",
    "source_diversity",
    "evidence_coverage",
    "korean_headline",
    "korean_briefing",
    "alert_reason",
    "evidence_phrases_text",
    "reviewer_id",
    "reviewer_decision",
    "evidence_quote_supported",
    "source_quality",
    "interpretation_assessment",
    "error_type",
    "domain_review_needed",
    "stage1_note",
]

REVIEW_LOG_COLUMNS = [
    "alert_id",
    "region",
    "reviewer_id",
    "review_mode",
    "stage1_locked",
    "stage1_locked_at",
    "reviewer_decision",
    "evidence_quote_supported",
    "source_quality",
    "interpretation_assessment",
    "error_type",
    "domain_review_needed",
    "stage1_note",
    "stage2_reviewed_at",
    "stage2_overridden",
    "human_final_decision",
    "human_final_evidence_quote_supported",
    "human_final_interpretation_assessment",
    "human_final_error_type",
    "stage2_override_reason",
    "tev1_verdict",
    "gemma2_worst",
    "deepseek_verdict",
    "critic_model",
    "judge_recommended_decision",
    "judge_key_dispute",
    "judge_ruling_rationale",
    "triggers",
]


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_reviews() -> Dict[str, Dict[str, Any]]:
    if not REVIEW_JSON_PATH.exists():
        return {}
    data = _load_json(REVIEW_JSON_PATH)
    return data.get("reviews", {})


def _save_reviews(reviews: Dict[str, Dict[str, Any]]) -> None:
    REVIEW_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "human_blind_review_v1",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_locked": sum(1 for r in reviews.values() if r.get("stage1_locked")),
        "reviews": reviews,
    }
    with open(REVIEW_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(REVIEW_LOG_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_LOG_COLUMNS)
        writer.writeheader()
        for alert_id in sorted(reviews.keys()):
            rec = reviews[alert_id]
            row = {col: rec.get(col, "") for col in REVIEW_LOG_COLUMNS}
            if isinstance(row.get("triggers"), list):
                row["triggers"] = "|".join(row["triggers"])
            writer.writerow(row)


def _format_evidence_phrases(raw_phrases: Any) -> str:
    if not raw_phrases:
        return "(근거 문장 없음)"
    parts = []
    for idx, item in enumerate(raw_phrases, start=1):
        if isinstance(item, dict):
            phrase = item.get("phrase") or item.get("text") or json.dumps(item, ensure_ascii=False)
            src = item.get("source") or item.get("url") or ""
            parts.append(f"[E-{idx:02d}] {phrase}" + (f" (출처: {src})" if src else ""))
        else:
            parts.append(f"[E-{idx:02d}] {item}")
    return " || ".join(parts)


def _build_stage1_context(audit_item: Dict[str, Any], sg_data: Dict[str, Any]) -> Dict[str, Any]:
    region = audit_item["region"]
    sg = sg_data.get(region, {})
    return {
        "alert_id": audit_item["alert_id"],
        "region": region,
        "analyzed_at": sg.get("analyzed_at", ""),
        "formula_alert_ko": audit_item.get("formula_alert_ko", sg.get("alert_level", "")),
        "formula_alert_en": audit_item.get("formula_alert_en", ""),
        "risk_signal_score": audit_item.get("risk_signal_score", sg.get("risk_signal_score", "")),
        "source_item_count": sg.get("source_item_count", ""),
        "source_diversity": sg.get("source_diversity", ""),
        "evidence_coverage": sg.get("evidence_coverage", ""),
        "korean_headline": sg.get("korean_headline", ""),
        "korean_briefing": sg.get("korean_briefing", ""),
        "alert_reason": sg.get("alert_reason", ""),
        "evidence_phrases_text": _format_evidence_phrases(sg.get("evidence_phrases", [])),
    }


def export_stage1_csv() -> Path:
    audit = _load_json(AUDIT_PATH)
    sg_data = _load_json(SIGNAL_GAP_PATH)
    existing_reviews = _load_reviews()

    STAGE1_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STAGE1_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=STAGE1_CSV_COLUMNS)
        writer.writeheader()
        for item in audit.get("results", []):
            ctx = _build_stage1_context(item, sg_data)
            locked = existing_reviews.get(ctx["alert_id"], {})
            row = {col: ctx.get(col, "") for col in STAGE1_CSV_COLUMNS}
            if locked.get("stage1_locked"):
                for k in (
                    "reviewer_id",
                    "reviewer_decision",
                    "evidence_quote_supported",
                    "source_quality",
                    "interpretation_assessment",
                    "error_type",
                    "domain_review_needed",
                    "stage1_note",
                ):
                    row[k] = locked.get(k, "")
            writer.writerow(row)

    print(f"✅ Stage 1 블라인드 검수 시트 생성 완료 (모델 출력 완전 마스킹): {STAGE1_CSV_PATH}")
    print(f"   대상 건수: {len(audit.get('results', []))}건")
    return STAGE1_CSV_PATH


def _validate_stage1_fields(row: Dict[str, str]) -> List[str]:
    errors = []
    if not row.get("reviewer_id", "").strip():
        errors.append("reviewer_id 누락")
    checks = [
        ("reviewer_decision", VALID_DECISIONS),
        ("evidence_quote_supported", VALID_EVIDENCE),
        ("source_quality", VALID_SOURCE_QUALITY),
        ("interpretation_assessment", VALID_INTERPRETATION),
        ("error_type", VALID_ERROR_TYPES),
        ("domain_review_needed", VALID_YN),
    ]
    for field, allowed in checks:
        val = row.get(field, "").strip().lower()
        if val not in allowed:
            errors.append(f"{field}='{val}' (허용값: {', '.join(allowed)})")
    return errors


def _extract_model_summary(audit_item: Dict[str, Any]) -> Dict[str, Any]:
    tev1 = audit_item.get("tev1", {})
    gemma = audit_item.get("gemma2", {})
    deepseek = audit_item.get("deepseek_r1", {})
    judge = audit_item.get("presiding_judge") or {}
    gov = audit_item.get("governance", {})
    return {
        "tev1_verdict": tev1.get("stage_verdict") or tev1.get("status", "error"),
        "gemma2_worst": gemma.get("worst_verdict") or gemma.get("status", "error"),
        "critic_model": deepseek.get("model_id", "nemotron-3-nano:4b"),
        "deepseek_verdict": deepseek.get("inference_verdict") or deepseek.get("status", "error"),
        "deepseek_note": deepseek.get("note", ""),
        "judge_model_id": judge.get("model_id", "mistral:7b"),
        "judge_recommended_decision": judge.get("recommended_decision") or judge.get("status", ""),
        "judge_key_dispute": judge.get("key_dispute", ""),
        "judge_ruling_rationale": judge.get("ruling_rationale", ""),
        "triggers": gov.get("triggers", []),
    }


def reveal_from_csv(csv_path: Path, dual_blind: bool = False) -> None:
    audit = _load_json(AUDIT_PATH)
    audit_by_id = {item["alert_id"]: item for item in audit.get("results", [])}
    reviews = _load_reviews()

    locked_new = 0
    skipped_incomplete = 0
    already_locked = 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alert_id = row.get("alert_id", "").strip()
            if not alert_id or alert_id not in audit_by_id:
                continue

            if reviews.get(alert_id, {}).get("stage1_locked"):
                already_locked += 1
                continue

            errs = _validate_stage1_fields(row)
            if errs:
                skipped_incomplete += 1
                print(f"⚠️ [{alert_id}] 미작성/오류로 잠금 보류: {'; '.join(errs)}")
                continue

            msum = _extract_model_summary(audit_by_id[alert_id])
            reviews[alert_id] = {
                "alert_id": alert_id,
                "region": audit_by_id[alert_id]["region"],
                "reviewer_id": row["reviewer_id"].strip(),
                "review_mode": "dual_blind" if dual_blind else "single_reviewer_provisional",
                "stage1_locked": True,
                "stage1_locked_at": datetime.now(timezone.utc).isoformat(),
                "reviewer_decision": row["reviewer_decision"].strip().lower(),
                "evidence_quote_supported": row["evidence_quote_supported"].strip().lower(),
                "source_quality": row["source_quality"].strip().lower(),
                "interpretation_assessment": row["interpretation_assessment"].strip().lower(),
                "error_type": row["error_type"].strip().lower(),
                "domain_review_needed": row["domain_review_needed"].strip().lower(),
                "stage1_note": row.get("stage1_note", "").strip(),
                "stage2_reviewed_at": "",
                "stage2_overridden": False,
                "human_final_decision": row["reviewer_decision"].strip().lower(),
                "human_final_evidence_quote_supported": row["evidence_quote_supported"].strip().lower(),
                "human_final_interpretation_assessment": row["interpretation_assessment"].strip().lower(),
                "human_final_error_type": row["error_type"].strip().lower(),
                "stage2_override_reason": "",
                **msum,
            }
            locked_new += 1

    _save_reviews(reviews)
    _write_stage2_sheet(reviews, audit_by_id)
    print(f"\n🔒 Stage 1 잠금 결과: 신규 잠금 {locked_new}건 | 기존 잠금 보존 {already_locked}건 | 미완료 보류 {skipped_incomplete}건")
    print(f"📊 Stage 2 비교 시트(잠금 건만 모델 출력 공개): {STAGE2_CSV_PATH}")


def _write_stage2_sheet(reviews: Dict[str, Dict[str, Any]], audit_by_id: Dict[str, Any]) -> None:
    cols = [
        "alert_id",
        "region",
        "stage1_locked",
        "reviewer_decision",
        "evidence_quote_supported",
        "interpretation_assessment",
        "error_type",
        "tev1_verdict",
        "gemma2_worst",
        "deepseek_verdict",
        "critic_model_id",
        "judge_recommended_decision",
        "judge_key_dispute",
        "judge_ruling_rationale",
        "triggers",
        "deepseek_note",
        "stage2_overridden",
        "human_final_decision",
        "human_final_evidence_quote_supported",
        "human_final_interpretation_assessment",
        "human_final_error_type",
        "stage2_override_reason",
    ]
    with open(STAGE2_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for alert_id, item in audit_by_id.items():
            rec = reviews.get(alert_id, {})
            if not rec.get("stage1_locked"):
                continue
            row = {c: rec.get(c, "") for c in cols}
            if isinstance(row.get("triggers"), list):
                row["triggers"] = "|".join(row["triggers"])
            writer.writerow(row)


def _prompt_choice(label: str, options: tuple[str, ...], default: Optional[str] = None) -> str:
    opts_str = " / ".join(f"{i+1}:{opt}" for i, opt in enumerate(options))
    while True:
        suffix = f" [기본 {default}]" if default else ""
        raw = input(f"  - {label} ({opts_str}){suffix}: ").strip()
        if not raw and default:
            return default
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        if raw.lower() in options:
            return raw.lower()
        print("    ⚠️ 잘못된 입력입니다. 번호 또는 정확한 영문 값을 입력하세요.")


def run_interactive(reviewer_id: str, dual_blind: bool = False) -> None:
    audit = _load_json(AUDIT_PATH)
    sg_data = _load_json(SIGNAL_GAP_PATH)
    reviews = _load_reviews()
    audit_by_id = {item["alert_id"]: item for item in audit.get("results", [])}

    pending = [item for item in audit.get("results", []) if not reviews.get(item["alert_id"], {}).get("stage1_locked")]
    if not pending:
        print("✅ 모든 7개 권역의 Stage 1 잠금이 이미 완료되었습니다. (--status로 현황 확인)")
        return

    print("=" * 72)
    print(f"🛡️ §10.4.3 블라인드 사람 검수 시작 (검수자: {reviewer_id}, 미검수: {len(pending)}건)")
    print("   [규칙] Stage 1에서는 모델 출력이 완전히 가려집니다. 잠금 후 Stage 2가 열립니다.")
    print("=" * 72)

    for idx, item in enumerate(pending, start=1):
        ctx = _build_stage1_context(item, sg_data)
        print(f"\n[{idx}/{len(pending)}] 권역: {ctx['region']} ({ctx['alert_id']})")
        print("-" * 72)
        print(f"• 수집/분석 시각   : {ctx['analyzed_at']}")
        print(f"• 산식 경보 단계   : {ctx['formula_alert_ko']} ({ctx['formula_alert_en']}) | score={ctx['risk_signal_score']}")
        print(f"• 출처 수 / 다양성 : {ctx['source_item_count']}건 / 다양성 {ctx['source_diversity']} | 근거 커버리지 {ctx['evidence_coverage']}%")
        print(f"• 헤드라인         : {ctx['korean_headline']}")
        print(f"• 브리핑           : {ctx['korean_briefing']}")
        print(f"• 산식 사유        : {ctx['alert_reason']}")
        print(f"• 근거 문장        : {ctx['evidence_phrases_text']}")
        print("-" * 72)
        print("▶ [Stage 1 블라인드 판정 입력] (중단하려면 Ctrl+C)")

        decision = _prompt_choice("경보 단계 (reviewer_decision)", VALID_DECISIONS)
        ev_support = _prompt_choice("근거 문장 (evidence_quote_supported)", VALID_EVIDENCE)
        src_qual = _prompt_choice("출처 품질 (source_quality)", VALID_SOURCE_QUALITY)
        interp = _prompt_choice("해석 수위 (interpretation_assessment)", VALID_INTERPRETATION)
        err_type = _prompt_choice("오류 유형 (error_type)", VALID_ERROR_TYPES, default="none")
        domain_req = _prompt_choice("도메인 전문가 검토 필요 (domain_review_needed)", VALID_YN, default="no")
        s1_note = input("  - Stage 1 메모 (선택): ").strip()

        msum = _extract_model_summary(item)
        rec = {
            "alert_id": ctx["alert_id"],
            "region": ctx["region"],
            "reviewer_id": reviewer_id,
            "review_mode": "dual_blind" if dual_blind else "single_reviewer_provisional",
            "stage1_locked": True,
            "stage1_locked_at": datetime.now(timezone.utc).isoformat(),
            "reviewer_decision": decision,
            "evidence_quote_supported": ev_support,
            "source_quality": src_qual,
            "interpretation_assessment": interp,
            "error_type": err_type,
            "domain_review_needed": domain_req,
            "stage1_note": s1_note,
            **msum,
        }

        print("\n🔒 Stage 1 잠금 완료! 이제 [Stage 2] 모델 감사 및 재판관 권고안을 공개합니다:")
        print(f"   • tev1:latest       : {msum['tev1_verdict']}")
        print(f"   • gemma2:9b         : {msum['gemma2_worst']}")
        print(f"   • {msum['critic_model']:18s}: {msum['deepseek_verdict']}")
        if msum["deepseek_note"]:
            print(f"   • critic 메모       : {msum['deepseek_note'][:220]}")
        if msum.get("judge_recommended_decision"):
            print(f"   • 재판관({msum['judge_model_id']}) 권고: {msum['judge_recommended_decision']}")
            if msum.get("judge_key_dispute"):
                print(f"   • 재판관 쟁점 요약  : {msum['judge_key_dispute']}")
            if msum.get("judge_ruling_rationale"):
                print(f"   • 재판관 판결문 초안: {msum['judge_ruling_rationale']}")
        print(f"   • Trigger Flags     : {msum['triggers']}")

        override = _prompt_choice("Stage 2에서 Stage 1 판정을 번복하시겠습니까?", VALID_YN, default="no")
        rec["stage2_reviewed_at"] = datetime.now(timezone.utc).isoformat()
        rec["stage2_overridden"] = override == "yes"
        if override == "yes":
            rec["human_final_decision"] = _prompt_choice("최종 경보 단계", VALID_DECISIONS, default=decision)
            rec["human_final_evidence_quote_supported"] = _prompt_choice("최종 근거 지원", VALID_EVIDENCE, default=ev_support)
            rec["human_final_interpretation_assessment"] = _prompt_choice("최종 해석 수위", VALID_INTERPRETATION, default=interp)
            rec["human_final_error_type"] = _prompt_choice("최종 오류 유형", VALID_ERROR_TYPES, default=err_type)
            rec["stage2_override_reason"] = input("  - 번복 사유 (필수): ").strip() or "Stage 2 모델 대조 후 수정"
        else:
            rec["human_final_decision"] = decision
            rec["human_final_evidence_quote_supported"] = ev_support
            rec["human_final_interpretation_assessment"] = interp
            rec["human_final_error_type"] = err_type
            rec["stage2_override_reason"] = ""

        reviews[ctx["alert_id"]] = rec
        _save_reviews(reviews)
        _write_stage2_sheet(reviews, audit_by_id)
        print(f"💾 [{ctx['region']}] 저장 완료.")


def print_status() -> None:
    audit = _load_json(AUDIT_PATH)
    reviews = _load_reviews()
    total = len(audit.get("results", []))
    locked = [r for r in reviews.values() if r.get("stage1_locked")]
    overridden = [r for r in locked if r.get("stage2_overridden")]

    print("=" * 68)
    print("📊 §10.4.3 블라인드 사람 검수 현황 및 §10.4.6 KPI 요약")
    print("=" * 68)
    print(f"• 전체 감사 대상 권역 : {total}건")
    print(f"• Stage 1 잠금 완료   : {len(locked)}건 / {total}건")
    print(f"• Stage 1→2 번복 건수 : {len(overridden)}건" + (f" ({len(overridden)/len(locked)*100:.1f}%)" if locked else ""))

    if locked:
        dec_counts = {}
        for r in locked:
            d = r.get("human_final_decision", r.get("reviewer_decision", "unknown"))
            dec_counts[d] = dec_counts.get(d, 0) + 1
        print(f"• 최종 사람 판정 분포 : {dec_counts}")
    else:
        print("• 아직 완료된 사람 검수가 없습니다. (--export 또는 --interactive 로 시작하세요)")
    print("=" * 68)


def main() -> None:
    parser = argparse.ArgumentParser(description="§10.4.3 블라인드 2단계 사람 검수 CLI")
    parser.add_argument("--export", action="store_true", help="Stage 1 블라인드 검수용 CSV 생성")
    parser.add_argument("--interactive", action="store_true", help="터미널 대화형 Stage 1→2 검수 실행")
    parser.add_argument("--reviewer", type=str, default="reviewer_1", help="검수자 ID (기본: reviewer_1)")
    parser.add_argument("--dual-blind", action="store_true", help="2인 블라인드 검수 모드 표기")
    parser.add_argument("--reveal", type=Path, help="작성 완료한 Stage 1 CSV를 잠금 처리하고 Stage 2 시트 생성")
    parser.add_argument("--status", action="store_true", help="현재 사람 검수 현황 및 KPI 출력")

    args = parser.parse_args()
    if not any([args.export, args.interactive, args.reveal, args.status]):
        parser.print_help()
        return

    if args.export:
        export_stage1_csv()
    if args.reveal:
        reveal_from_csv(args.reveal, dual_blind=args.dual_blind)
    if args.interactive:
        run_interactive(reviewer_id=args.reviewer, dual_blind=args.dual_blind)
    if args.status:
        print_status()


if __name__ == "__main__":
    main()
