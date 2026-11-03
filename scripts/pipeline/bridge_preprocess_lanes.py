"""
bridge_preprocess_lanes.py
==========================
4대 수집 레인(FAST, CONTEXT, OPINION, BASELINE)에서 수집된 원시 비정형 데이터를
읽어 4단계 지능형 다국어 전처리(preprocess_signals.py)를 수행하고,
다운스트림(교차검증, LLM 분석, DB 적재)이 즉시 소비할 수 있는 표준 정형 스키마
(Canonical Structured Schema)와 배제 감사 영수증(Rejects Receipt)으로 변환·저장합니다.

안전 원칙:
- 수집기(scripts/collection/*) 및 원시 데이터(data/*) 수정 금지 (Read-Only 소비)
- Alert Level 임의 확정 금지 (모든 단일/군집 신호는 verification_state="UNVERIFIED" 유지)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = DATA_DIR / "automation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "automation"))

from preprocess_signals import (  # noqa: E402
    CHOKEPOINT_MAPPINGS,
    SUPPLY_CHAIN_ITEMS,
    run_pipeline_preprocessing,
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_fast_lane() -> List[Dict[str, Any]]:
    """FAST 레인: 백악관 공식 RSS, 연방관보(Federal Register), 주요국 외교부 발표문 로드."""
    records: List[Dict[str, Any]] = []

    # 1. White House Official
    wh_path = DATA_DIR / "whitehouse_official" / "whitehouse_latest.json"
    if wh_path.exists():
        try:
            wh_data = json.loads(wh_path.read_text(encoding="utf-8"))
            for item in wh_data.get("records", []):
                records.append({
                    "title": item.get("title", ""),
                    "summary": item.get("summary", ""),
                    "url": item.get("source_url", ""),
                    "source": item.get("publisher") or item.get("source_id") or "The White House",
                    "source_type": item.get("source_type") or "official_statement",
                    "lane": "FAST",
                    "language": "en",
                    "published_at": item.get("published_at") or item.get("observed_at") or "",
                    "country_or_region": item.get("country", "US"),
                    "raw_ref": "data/whitehouse_official/whitehouse_latest.json",
                })
        except Exception as e:
            print(f"  [WARN] White House 로드 실패: {e}")

    # 2. Federal Register
    fr_path = DATA_DIR / "federal_register" / "federal_register_latest.json"
    if fr_path.exists():
        try:
            fr_list = json.loads(fr_path.read_text(encoding="utf-8"))
            if isinstance(fr_list, list):
                for item in fr_list:
                    records.append({
                        "title": item.get("title", ""),
                        "summary": item.get("abstract", ""),
                        "url": item.get("html_url") or item.get("pdf_url") or "",
                        "source": item.get("agencies") or item.get("source_id") or "Federal Register",
                        "source_type": "regulation_notice",
                        "lane": "FAST",
                        "language": "en",
                        "published_at": item.get("publication_date") or item.get("observed_at") or "",
                        "country_or_region": "US",
                        "raw_ref": "data/federal_register/federal_register_latest.json",
                    })
        except Exception as e:
            print(f"  [WARN] Federal Register 로드 실패: {e}")

    # 3. Government Announcements (가장 최신 all_announcements_*.json 파일 선택)
    gov_dir = DATA_DIR / "gov_announcements"
    if gov_dir.exists():
        gov_files = sorted(gov_dir.glob("all_announcements_*.json"), reverse=True)
        if gov_files:
            latest_gov = gov_files[0]
            try:
                gov_list = json.loads(latest_gov.read_text(encoding="utf-8"))
                if isinstance(gov_list, list):
                    for item in gov_list:
                        records.append({
                            "title": item.get("title", ""),
                            "summary": item.get("description", ""),
                            "url": item.get("link", ""),
                            "source": item.get("source") or "Official Government",
                            "source_type": item.get("source_type") or "official_statement",
                            "lane": "FAST",
                            "language": "",
                            "published_at": item.get("pub_date", ""),
                            "country_or_region": ",".join(item.get("matched_issues") or []),
                            "raw_ref": f"data/gov_announcements/{latest_gov.name}",
                        })
            except Exception as e:
                print(f"  [WARN] Gov Announcements 로드 실패: {e}")

    return records


def load_context_lane() -> List[Dict[str, Any]]:
    """CONTEXT 레인: 4대 권역 신호 괴리 RSS (관영 vs 독립·망명 언론) 로드."""
    records: List[Dict[str, Any]] = []
    sg_path = DATA_DIR / "signal_gap" / "rss_signal_gap_latest.csv"
    if sg_path.exists():
        try:
            with sg_path.open("r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_stype = (row.get("Source_Type") or "").strip().lower()
                    stype = "state_media" if raw_stype == "official" else "independent_media"
                    records.append({
                        "title": row.get("Title", ""),
                        "summary": row.get("Summary", ""),
                        "url": row.get("Link", ""),
                        "source": row.get("Source_ID") or row.get("Feed_URL") or "SignalGap_RSS",
                        "source_type": stype,
                        "lane": "CONTEXT",
                        "language": "",
                        "published_at": row.get("Published_Date") or row.get("Observed_At_UTC") or "",
                        "country_or_region": row.get("Region", ""),
                        "raw_ref": "data/signal_gap/rss_signal_gap_latest.csv",
                    })
        except Exception as e:
            print(f"  [WARN] Signal Gap RSS 로드 실패: {e}")
    return records


def load_opinion_lane() -> List[Dict[str, Any]]:
    """OPINION 레인: 로컬 포럼(PTT), Bluesky Social, GoogleNews 로컬 여론 로드."""
    records: List[Dict[str, Any]] = []
    op_path = DATA_DIR / "local_opinions" / "local_opinions_latest.csv"
    if op_path.exists():
        try:
            with op_path.open("r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        "title": row.get("title_or_text", ""),
                        "summary": "",
                        "collector_theme": row.get("risk_theme", ""),
                        "url": row.get("url", ""),
                        "source": row.get("source_platform") or "Local_Opinion",
                        "source_type": "public_opinion_forum",
                        "lane": "OPINION",
                        "language": "",
                        "published_at": row.get("published_at") or row.get("collected_at") or "",
                        "country_or_region": row.get("country_or_region", ""),
                        "raw_ref": "data/local_opinions/local_opinions_latest.csv",
                    })
        except Exception as e:
            print(f"  [WARN] Local Opinions 로드 실패: {e}")

    x_path = DATA_DIR / "x_public" / "latest.json"
    if x_path.exists():
        try:
            x_data = json.loads(x_path.read_text(encoding="utf-8"))
            for item in x_data.get("records", []):
                records.append({
                    "title": item.get("text", ""),
                    "summary": "",
                    "url": item.get("url", ""),
                    "source": "X_Public_API",
                    "source_type": "online_information_environment_signal",
                    "lane": "OPINION",
                    "language": item.get("lang", ""),
                    "published_at": item.get("created_at", ""),
                    "country_or_region": "GLOBAL",
                    "raw_ref": "data/x_public/latest.json",
                })
        except Exception:
            pass

    return records


def load_baseline_sensor_summary() -> List[Dict[str, Any]]:
    """BASELINE / SENSOR 레인: 해협·운임·에너지 프록시 지표 요약 로드."""
    sensors: List[Dict[str, Any]] = []
    m_path = DATA_DIR / "maritime_chokepoints" / "maritime_latest.csv"
    if m_path.exists():
        try:
            with m_path.open("r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sensors.append({
                        "ticker": row.get("ticker", ""),
                        "asset_name": row.get("asset_name", ""),
                        "category": row.get("category", ""),
                        "latest_price": row.get("latest_price", ""),
                        "daily_change_pct": row.get("daily_change_pct", ""),
                        "risk_signal": row.get("risk_signal", ""),
                        "observed_at": row.get("observed_at", ""),
                    })
        except Exception:
            pass
    return sensors


def run_bridge() -> Dict[str, Any]:
    print("=" * 72)
    print("🌐 [4-Lane 전처리 브릿지] 원시 비정형 데이터 로드 및 표준 정형 스키마 변환 시작")
    print("=" * 72)

    fast_records = load_fast_lane()
    context_records = load_context_lane()
    opinion_records = load_opinion_lane()
    baseline_sensors = load_baseline_sensor_summary()

    all_raw = fast_records + context_records + opinion_records
    print(
        f"📥 [원시 레코드 집계] 총 {len(all_raw)}건 "
        f"(FAST={len(fast_records)}, CONTEXT={len(context_records)}, "
        f"OPINION={len(opinion_records)}, BASELINE_SENSORS={len(baseline_sensors)})"
    )

    clusters, rejects = run_pipeline_preprocessing(all_raw, return_rejects=True)

    # 통계 집계
    reject_reason_counts = dict(Counter(r["reject_reason"] for r in rejects))
    reject_lane_counts = dict(Counter(r.get("lane", "UNSPECIFIED") for r in rejects))

    chokepoint_counts: Counter = Counter()
    supply_counts: Counter = Counter()
    event_counts: Counter = Counter()
    hotspot_counts: Counter = Counter()

    for c in clusters:
        for cp in c.get("chokepoints", []):
            chokepoint_counts[cp["code"]] += 1
        for sp in c.get("supply_chain_tags", []):
            supply_counts[sp] += 1
        for ev in c.get("event_types", []):
            event_counts[ev] += 1
        for hs in c.get("hotspot_regions", []):
            hotspot_counts[hs] += 1

    now_iso = datetime.now(timezone.utc).isoformat()

    canonical_payload = {
        "schema_version": "canonical_signals_v1",
        "generated_at": now_iso,
        "verification_policy": "Single-source signals remain UNVERIFIED; Alert Level is never determined in preprocessing.",
        "alert_level_set": False,
        "input_counts": {
            "total_raw": len(all_raw),
            "FAST": len(fast_records),
            "CONTEXT": len(context_records),
            "OPINION": len(opinion_records),
            "BASELINE_SENSORS": len(baseline_sensors),
        },
        "output_counts": {
            "canonical_clusters": len(clusters),
            "rejected_noise": len(rejects),
            "multi_source_clusters": sum(1 for c in clusters if c["unique_sources_count"] >= 2),
        },
        "baseline_market_sensors": baseline_sensors,
        "signals": clusters,
    }

    rejects_payload = {
        "schema_version": "preprocess_rejects_v1",
        "generated_at": now_iso,
        "total_rejected": len(rejects),
        "reason_breakdown": reject_reason_counts,
        "lane_breakdown": reject_lane_counts,
        "rejects": rejects,
    }

    summary_payload = {
        "schema_version": "preprocess_summary_v1",
        "generated_at": now_iso,
        "alert_level_set": False,
        "verification_state_default": "UNVERIFIED",
        "input_counts": canonical_payload["input_counts"],
        "output_counts": canonical_payload["output_counts"],
        "reject_reason_breakdown": reject_reason_counts,
        "chokepoint_distribution": {
            code: chokepoint_counts.get(code, 0) for code in CHOKEPOINT_MAPPINGS
        },
        "supply_chain_distribution": {
            item: supply_counts.get(item, 0) for item in SUPPLY_CHAIN_ITEMS
        },
        "event_type_distribution": dict(event_counts),
        "hotspot_distribution": dict(hotspot_counts),
    }

    canonical_file = OUT_DIR / "canonical_signals_latest.json"
    rejects_file = OUT_DIR / "preprocess_rejects_latest.json"
    summary_file = OUT_DIR / "preprocess_summary_latest.json"

    canonical_file.write_text(json.dumps(canonical_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rejects_file.write_text(json.dumps(rejects_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_file.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("-" * 72)
    print(f"✅ [산출물 저장 완료]")
    print(f"  1) 표준 정형 신호: {canonical_file.relative_to(ROOT)} ({len(clusters)}개 클러스터)")
    print(f"  2) 배제 감사 영수증: {rejects_file.relative_to(ROOT)} ({len(rejects)}건 배제)")
    print(f"  3) 전처리 요약 통계: {summary_file.relative_to(ROOT)}")
    print(f"📊 [5대 해협 감지 현황]: {dict(chokepoint_counts)}")
    print(f"📦 [한국 6대 공급망 품목 감지 현황]: {dict(supply_counts)}")
    print("=" * 72)

    return summary_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="4대 수집 레인 원시 데이터 -> 표준 정형 신호 전처리 브릿지")
    parser.parse_args()
    run_bridge()
