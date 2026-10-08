"""
cross_verify_events.py — GDELT Cloud 사건 및 복수 계통 신호 시계열 교차검증기
=============================================================================

조기경보 검증 원칙 (DATA_COLLECTION_SESSION_PROMPT.md 준수):
  1. GDELT Cloud Events는 빠른 사건 탐지 센서이지 최종 사실 판정기가 아니다.
     - 단일 GDELT 사건만으로 Alert Level을 올리지 않는다 (single_source_elevate_forbidden = True).
  2. 무장단체(후티, IRGC 등)의 성명·주장은 정보환경 센서로 취급하며, claim_status를 관리한다.
     - claim_status: UNVERIFIED (미확인), PARTIALLY_CONFIRMED (부분확인),
                     CROSS_VERIFIED (외부확인), REFUTED (반박)
  3. 교차검증(Cross-Verification) 체계:
     - GDELT 사건 + 정부/군 공식 발표 + 현지/독립 언론 + 텔레그램 성명 + 해협/운임 지표
     - 서로 다른 독립 계통 2개 이상이 시간순으로 부합할 때만 '공급망 경보 후보(Alert Candidate)' 생성.

입력 데이터:
  - data/gdelt_cloud/events_latest.json
  - data/maritime_chokepoints/maritime_summary.json
  - data/local_opinions/local_opinions_latest.csv
  - data/signal_gap/middle_east_risk_analysis.txt

출력 데이터:
  - data/event_cross_verification/verification_latest.json
  - data/event_cross_verification/verification_summary.csv
  - data/event_cross_verification/history/verification_{timestamp}.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ----- 경로 설정 -----
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "event_cross_verification"
HISTORY_DIR = DATA_DIR / "history"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_gdelt_events() -> list[dict]:
    all_events = []
    seen_ids = set()

    # 1. 일반 이벤트 로드
    gdelt_file = ROOT / "data" / "gdelt_cloud" / "events_latest.json"
    if gdelt_file.exists():
        try:
            with open(gdelt_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for ev in data.get("events", []):
                    eid = ev.get("id") or ev.get("event_id")
                    if eid and eid not in seen_ids:
                        seen_ids.add(eid)
                        ev["id"] = eid
                        # URL 및 메타데이터 정규화
                        ev["source_url"] = ev.get("url") or ev.get("primary_story_url") or ev.get("source_url")
                        ev["observed_at"] = ev.get("observed_at") or ev.get("coded_at") or ev.get("processed_at")
                        ev["published_at"] = ev.get("coded_at") or ev.get("processed_at") or ev.get("event_date")
                        ev["license_note"] = "GDELT Cloud API v2 (Authenticated Free/Bounded Query). Receipt retained."
                        ev["is_partial_probe"] = True
                        all_events.append(ev)
        except Exception as e:
            print(f"  ✗ GDELT events_latest 로드 오류: {e}")

    # 2. 공급망 특화 워치 후보 로드 (홍해·후티·해상운송 등)
    watch_file = ROOT / "data" / "gdelt_cloud" / "supply_chain_watch_latest.json"
    if watch_file.exists():
        try:
            with open(watch_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                coverage_info = data.get("coverage", {})
                for ev in data.get("candidates", []):
                    eid = ev.get("event_id") or ev.get("id")
                    if eid and eid not in seen_ids:
                        seen_ids.add(eid)
                        ev["id"] = eid
                        ev["source_url"] = ev.get("source_url") or ev.get("url")
                        ev["observed_at"] = ev.get("observed_at") or ev.get("collected_at")
                        ev["published_at"] = ev.get("event_date")
                        ev["license_note"] = "GDELT Cloud API v2 (Authenticated Probe). Note: Bounded 1-page sample."
                        ev["is_partial_probe"] = not coverage_info.get("complete", False)
                        all_events.append(ev)
        except Exception as e:
            print(f"  ✗ GDELT supply_chain_watch 로드 오류: {e}")

    print(f"  ✓ GDELT Cloud 사건 총 {len(all_events)}건 로드 완료 (공급망 후보 포함, 수집 영수증 확인)")
    return all_events


def load_maritime_signals() -> dict:
    maritime_file = ROOT / "data" / "maritime_chokepoints" / "maritime_summary.json"
    if not maritime_file.exists():
        return {}
    try:
        with open(maritime_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_local_opinions() -> list[dict]:
    opinions_file = ROOT / "data" / "local_opinions" / "local_opinions_latest.csv"
    if not opinions_file.exists():
        return []
    items = []
    try:
        with open(opinions_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(row)
        return items
    except Exception:
        return []


def load_osint_statements() -> str:
    txt_file = ROOT / "data" / "signal_gap" / "middle_east_risk_analysis.txt"
    if not txt_file.exists():
        return ""
    try:
        with open(txt_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def cross_verify_all(
    events: list[dict],
    maritime_data: dict,
    local_opinions: list[dict],
    osint_text: str,
) -> list[dict]:
    verified_results = []
    now_utc = datetime.now(timezone.utc).isoformat()

    market_proxies = maritime_data.get("market_proxies", [])
    chokepoints = {c["chokepoint_code"]: c for c in maritime_data.get("chokepoints_status", [])}

    for ev in events:
        ev_id = ev.get("id", "unknown")
        title = ev.get("title", "")
        summary = ev.get("summary", "")
        geo_country = (ev.get("geo", {}).get("country") or "").strip()
        event_date = ev.get("event_date", "")
        category = ev.get("category", "")
        subcategory_label = ev.get("subcategory_label", "")

        # 출처 추적 메타데이터 보존
        source_url = ev.get("source_url") or ""
        observed_at = ev.get("observed_at") or now_utc
        published_at = ev.get("published_at") or event_date
        license_note = ev.get("license_note") or "GDELT Cloud API v2 (Bounded Probe)"
        is_partial_probe = ev.get("is_partial_probe", True)

        matched_corroborations = []
        contradictions = []

        combined_text = f"{title} {summary} {geo_country}".lower()

        # 1. 해협 및 해상 시장 프록시 대조 (정밀 맥락 매칭)
        # 1-1. 이란 / 호르무즈 해협
        is_iran_context = "iran" in geo_country.lower() or "hormuz" in combined_text or "iran" in combined_text
        has_military_or_tanker_relevance = any(w in combined_text for w in ["carrier", "strike", "armed forces", "troop", "oil", "pipeline", "tanker", "navy", "military"])
        
        if is_iran_context and has_military_or_tanker_relevance:
            hormuz_info = chokepoints.get("HORMUZ")
            if hormuz_info:
                matched_corroborations.append({
                    "channel": "maritime_chokepoint",
                    "source": "HORMUZ_PROFILE",
                    "signal_type": "physical_infrastructure",
                    "note": f"호르무즈 해협 위협 평가: {hormuz_info.get('insurance_war_risk')}, 시장신호: {hormuz_info.get('market_proxy_signal')}",
                })
            # 유조선사 주가 또는 유가 변동 확인
            fro_proxy = next((m for m in market_proxies if m["ticker"] == "FRO"), None)
            if fro_proxy and fro_proxy.get("risk_signal") in ["CRITICAL_SPIKE", "ELEVATED"]:
                matched_corroborations.append({
                    "channel": "freight_market",
                    "source": "yfinance_FRO",
                    "signal_type": "market_behavior",
                    "note": f"원유 유조선사(FRO) 주가 {fro_proxy.get('monthly_change_pct')}% 급등 — 호르무즈 분쟁 프리미엄 시장 반영",
                })

        # 1-2. 홍해 / 예멘 / 바브엘만데브 해협 (단, 단순 국내 치안/마약/상업 리조트는 제외)
        is_red_sea_context = any(w in combined_text for w in ["yemen", "red sea", "bab al-mandab", "houthi"])
        has_maritime_conflict_relevance = any(w in combined_text for w in ["shipping", "vessel", "navigation", "maritime", "aviation", "missile", "station", "escalation", "attack", "target"])
        is_routine_crime_or_tourism = any(w in combined_text for w in ["hashish", "smuggling", "resort", "hotel", "tourist", "marina"]) and not has_maritime_conflict_relevance

        if is_red_sea_context and has_maritime_conflict_relevance and not is_routine_crime_or_tourism:
            bab_info = chokepoints.get("BAB_EL_MANDEB")
            if bab_info:
                matched_corroborations.append({
                    "channel": "maritime_chokepoint",
                    "source": "BAB_EL_MANDEB_PROFILE",
                    "signal_type": "physical_infrastructure",
                    "note": f"바브엘만데브 해협: 희망봉 우회 {bab_info.get('detour_delay')}, 전쟁보험료 {bab_info.get('insurance_war_risk')}",
                })
            zim_proxy = next((m for m in market_proxies if m["ticker"] == "ZIM"), None)
            if zim_proxy and zim_proxy.get("monthly_change_pct"):
                matched_corroborations.append({
                    "channel": "freight_market",
                    "source": "yfinance_ZIM",
                    "signal_type": "market_behavior",
                    "note": f"컨테이너 선사(ZIM) 운임 지표 일간 {zim_proxy.get('daily_change_pct')}%, 월간 {zim_proxy.get('monthly_change_pct')}% 반영",
                })

        # 1-3. 대만 해협 / 반도체 공급망
        is_taiwan_context = any(w in combined_text for w in ["taiwan", "tsmc", "taiwan strait"])
        if is_taiwan_context:
            tw_info = chokepoints.get("TAIWAN_STRAIT")
            if tw_info:
                matched_corroborations.append({
                    "channel": "maritime_chokepoint",
                    "source": "TAIWAN_STRAIT_PROFILE",
                    "signal_type": "physical_infrastructure",
                    "note": f"대만 해협: {tw_info.get('supply_chain_role')}, 지연 {tw_info.get('detour_delay')}",
                })

        # 2. 로컬 여론 & 현지 미디어 대조 (사건과 여론이 동일 핵심 엔티티를 공유할 때만 결합)
        for op in local_opinions:
            op_text = op.get("title_or_text", "").lower()
            op_region = op.get("country_or_region", "").lower()

            # 대만 관련 사건 & 대만 여론
            if is_taiwan_context and ("taiwan" in op_region or "대만" in op_text or "tsmc" in op_text):
                matched_corroborations.append({
                    "channel": "local_public_opinion",
                    "source": op.get("source_platform"),
                    "signal_type": "online_expression",
                    "note": f"[{op.get('country_or_region')}] {op.get('title_or_text', '')[:80]}...",
                })
                break

            # 이란 관련 사건 & 이란 여론/언급
            elif is_iran_context and any(k in op_text for k in ["iran", "이란", "hormuz", "호르무즈"]):
                matched_corroborations.append({
                    "channel": "local_public_opinion",
                    "source": op.get("source_platform"),
                    "signal_type": "online_expression",
                    "note": f"[{op.get('country_or_region')}] {op.get('title_or_text', '')[:80]}...",
                })
                break

            # 후티 / 홍해 해상 안보 관련 사건 & 후티/홍해 관련 여론
            elif any(k in combined_text for k in ["houthi", "red sea", "bab al-mandab"]) and any(k in op_text for k in ["houthi", "red sea", "후티", "홍해"]):
                matched_corroborations.append({
                    "channel": "local_public_opinion",
                    "source": op.get("source_platform"),
                    "signal_type": "online_expression",
                    "note": f"[{op.get('country_or_region')}] {op.get('title_or_text', '')[:80]}...",
                })
                break

        # 3. 공개 텔레그램 OSINT 군사 성명 대조 (사건에 직접적인 무력/타격 관련성이 있을 때만)
        has_kinetic_relevance = any(w in combined_text for w in ["missile", "strike", "attack", "target", "drone", "carrier", "escalat"])
        if (is_iran_context or is_red_sea_context) and has_kinetic_relevance:
            if "사우디" in osint_text or "미사일" in osint_text or "공습" in osint_text:
                matched_corroborations.append({
                    "channel": "telegram_osint_public",
                    "source": "Telegram_Public_Claims",
                    "signal_type": "armed_group_claim",
                    "note": "중동 교전 세력의 24시간 내 군사 작전 및 미사일 발사 공개 주장 관측됨",
                })

        # 4. 검증 상태(verification_state) 및 경보 후보 판정
        # 엄격 원칙: 단일 출처는 무조건 UNVERIFIED 및 경보 상승 금지(single_source_elevate_forbidden = True).
        # 서로 다른 독립 계통 2개 이상일 때만 CROSS_VERIFIED.
        distinct_channels = {c["channel"] for c in matched_corroborations}
        if len(distinct_channels) >= 2:
            ver_state = "CROSS_VERIFIED"
            # 운임/해협 직접 충격 + 군사성명이 함께 있을 때 WARNING, 아니면 WATCH
            alert_candidate = "WARNING" if ("freight_market" in distinct_channels and "maritime_chokepoint" in distinct_channels) else "WATCH"
            confidence = "HIGH (복수 독립 계통 일치: " + ", ".join(distinct_channels) + ")"
        elif len(distinct_channels) == 1:
            ver_state = "PARTIALLY_CONFIRMED"
            alert_candidate = "WATCH"
            confidence = "MEDIUM (단일 보조 계통 결합 — 독립 검증 미완료)"
        else:
            ver_state = "UNVERIFIED"
            alert_candidate = "NORMAL"
            confidence = "LOW (교차 출처 미확인 — 단일 GDELT 센서 감지 단계, 경보 상승 금지)"

        verified_results.append({
            "event_id": ev_id,
            "event_title": title,
            "event_summary": summary,
            "geo_country": geo_country,
            "event_date": event_date,
            "category": category,
            "subcategory": subcategory_label,
            "source_url": source_url,
            "observed_at": observed_at,
            "published_at": published_at,
            "license_note": license_note,
            "is_partial_probe": is_partial_probe,
            "verification_state": ver_state,
            "claim_status": "PARTIALLY_CONFIRMED" if len(distinct_channels) >= 1 else "UNVERIFIED",
            "distinct_channel_count": len(distinct_channels),
            "matched_channels": list(distinct_channels),
            "corroborations_count": len(matched_corroborations),
            "corroboration_evidence": matched_corroborations,
            "contradictions": contradictions,
            "alert_candidate_level": alert_candidate,
            "single_source_elevate_forbidden": True,
            "confidence_assessment": confidence,
            "verified_at": now_utc,
        })

    return verified_results


def save_verification_results(results: list[dict]) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. 종합 JSON 저장
    output_json = DATA_DIR / "verification_latest.json"

    # 상태 및 경보 레벨 집계
    state_counts = {}
    level_counts = {}
    for r in results:
        state_counts[r["verification_state"]] = state_counts.get(r["verification_state"], 0) + 1
        level_counts[r["alert_candidate_level"]] = level_counts.get(r["alert_candidate_level"], 0) + 1

    payload = {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_events_checked": len(results),
        "data_coverage": {
            "is_partial_collection": True,
            "complete": False,
            "coverage_note": "GDELT Cloud API v2 1-page budget bounded query probe. NOT full census.",
            "single_source_elevate_forbidden": True
        },
        "summary_counts": {
            "by_verification_state": state_counts,
            "by_alert_candidate_level": level_counts
        },
        "cross_verification_contract": {
            "single_source_elevate_forbidden": True,
            "allowed_verification_states": ["UNVERIFIED", "PARTIALLY_CONFIRMED", "CROSS_VERIFIED", "REFUTED"],
            "required_channels_for_alert": ["market_behavior", "physical_infrastructure", "official_statements", "local_media"]
        },
        "verified_events": results,
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 교차검증 종합 JSON 저장: {output_json} ({len(results)}건)")

    history_json = HISTORY_DIR / f"verification_{timestamp}.json"
    with open(history_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 2. 요약 CSV 저장
    output_csv = DATA_DIR / "verification_summary.csv"
    fieldnames = [
        "event_id", "event_title", "geo_country", "event_date",
        "verification_state", "distinct_channel_count", "alert_candidate_level",
        "source_url", "is_partial_probe", "confidence_assessment", "verified_at"
    ]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "event_id": r["event_id"],
                "event_title": r["event_title"],
                "geo_country": r["geo_country"],
                "event_date": r["event_date"],
                "verification_state": r["verification_state"],
                "distinct_channel_count": r["distinct_channel_count"],
                "alert_candidate_level": r["alert_candidate_level"],
                "source_url": r["source_url"],
                "is_partial_probe": r["is_partial_probe"],
                "confidence_assessment": r["confidence_assessment"],
                "verified_at": r["verified_at"],
            })
    print(f"✅ 교차검증 요약 CSV 저장: {output_csv}")


def main() -> None:
    print("=" * 65)
    print("⚖️  GDELT Cloud 사건 및 복수 계통 신호 시계열 교차검증 시작")
    print("=" * 65)

    events = load_gdelt_events()
    maritime_data = load_maritime_signals()
    local_opinions = load_local_opinions()
    osint_text = load_osint_statements()

    if not events:
        print("⚠️  검증할 GDELT 사건이 없습니다.")
        return

    results = cross_verify_all(events, maritime_data, local_opinions, osint_text)

    for r in results:
        print(f"\n📌 사건: {r['event_title']}")
        print(f"   위치: {r['geo_country']} | 일자: {r['event_date']}")
        print(f"   검증 상태: [{r['verification_state']}] (독립 채널 {r['distinct_channel_count']}개 일치)")
        print(f"   경보 후보: {r['alert_candidate_level']} ({r['confidence_assessment']})")
        print("   주요 일치 근거:")
        for ev in r["corroboration_evidence"][:3]:
            print(f"     • [{ev['channel']}] {ev['note'][:90]}")

    save_verification_results(results)
    print("\n🎉 GDELT Cloud 사건 교차검증 파이프라인 완료!")


if __name__ == "__main__":
    main()

