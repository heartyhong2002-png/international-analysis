"""
fetch_maritime_chokepoints.py — 글로벌 해협·항만 및 해상 운임·에너지 조기경보 센서
=================================================================================

조기경보 관점:
  국제정세 충격은 선언(말)보다 물류·해상 운송로(행동)에서 가장 먼저 실물 지표로 반영된다.
  - 홍해 바브엘만데브 해협: 후티 위협 시 희망봉 우회(+10~14일) 발생, 컨테이너 운임 및 전쟁보험료 급등
  - 호르무즈 해협: 이란 긴장 시 전 세계 원유 20% 수송로 위협, 유조선 운임(VLCC) 및 원유 선물 급등
  - 대만 해협: 군사 훈련 시 항로 우회 및 글로벌 반도체 공급망 리스크 촉발

데이터 구성:
  1. 해상 운임 & 선사 시장 프록시 (Yahoo Finance):
     - BDRY (발틱 벌크 운임선물 ETF - 원자재 운임 지표)
     - ZIM, AMKBY/Maersk (컨테이너 선사 - 희망봉 우회 및 컨테이너 운임 폭등 선행지표)
     - FRO/Frontline (원유 유조선사 - 호르무즈/홍해 유조선 위험 및 용선료 선행지표)
     - BZ=F, CL=F, NG=F (브렌트유, WTI, 천연가스/LNG 선물)
  2. 주요 길목(Chokepoints) 리스크 프로필 & 추정 위험 지표:
     - Bab el-Mandeb (홍해), Strait of Hormuz (페르시아만), Taiwan Strait (대만해협), Malacca Strait (말라카)
     - 각 해협별 우회율 추정, 전쟁위험보험료 할증(War Risk Premium), AIS 공백/스푸핑 불확실성 기록

주의 (Data Contract):
  - 선박 척수나 주가 프록시는 실제 화물 톤수를 1:1로 직접 증명하지 못하므로,
    cargo_tonnage_proxy_warning 및 uncertainty_note를 함께 보존한다.
  - 단일 지표 급등만으로 Alert Level을 올리지 않고 복수 지표 교차검증에 활용한다.

저장 위치:
  data/maritime_chokepoints/maritime_latest.csv
  data/maritime_chokepoints/maritime_summary.json
  data/maritime_chokepoints/history/maritime_{timestamp}.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ----- 경로 설정 -----
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "maritime_chokepoints"
HISTORY_DIR = DATA_DIR / "history"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# 4대 핵심 해협 리스크 모델 정의
CHOKEPOINTS = {
    "BAB_EL_MANDEB": {
        "name_ko": "바브엘만데브 해협 (홍해 남단)",
        "region": "Middle East / Red Sea",
        "threat_actor": "예멘 후티 반군 (공격 주장 추적)",
        "supply_chain_role": "유럽-아시아 최단 항로, 수에즈 운하 진입로",
        "impact_sectors": "컨테이너선, 자동차 운반선, 한국 대유럽 수출입",
        "normal_transit_days": 0,
        "detour_cape_delay_days": "10~14일 추가 (희망봉 우회)",
        "insurance_war_risk": "High (선박가의 0.5%~1.0% 추가 할증)",
        "ais_observability": "Partial (GPS 스푸핑 및 AIS 전원 차단 다수 관측)",
    },
    "HORMUZ": {
        "name_ko": "호르무즈 해협 (페르시아만)",
        "region": "Middle East / Persian Gulf",
        "threat_actor": "이란 혁명수비대 (IRGC)",
        "supply_chain_role": "전 세계 해상 원유 수송량의 20%, LNG 수송 핵심 동맥",
        "impact_sectors": "원유, 나프타, 초경질유, 한국 에너지 수입의 70% 의존",
        "normal_transit_days": 0,
        "detour_cape_delay_days": "우회 불가 (폐쇄 시 내륙 파이프라인 극히 제한적)",
        "insurance_war_risk": "Critical (긴장 고조 시 선박 억류 리스크)",
        "ais_observability": "Medium (나포 및 전파 방해 징후 추적)",
    },
    "TAIWAN_STRAIT": {
        "name_ko": "대만 해협",
        "region": "East Asia",
        "threat_actor": "중국 인민해방군 (해상 훈련 및 봉쇄 위협)",
        "supply_chain_role": "전 세계 컨테이너 선박 48% 통과, 반도체 파운드리 물류로",
        "impact_sectors": "글로벌 반도체, 전자부품, 한국-동남아 해상 물류",
        "normal_transit_days": 0,
        "detour_cape_delay_days": "2~4일 추가 (대만 동부 태평양 우회)",
        "insurance_war_risk": "Moderate-High (군사훈련 구역 선포 시)",
        "ais_observability": "High (상선 통항 밀집, 군함 식별 제한)",
    },
    "MALACCA": {
        "name_ko": "말라카 해협",
        "region": "Southeast Asia",
        "threat_actor": "항만 혼잡, 해적, 지정학적 차단 리스크",
        "supply_chain_role": "중동-동아시아 에너지 수송의 병목",
        "impact_sectors": "원유, 석탄, 일반 컨테이너",
        "normal_transit_days": 0,
        "detour_cape_delay_days": "3~5일 추가 (순다·롬복 해협 우회)",
        "insurance_war_risk": "Low-Moderate (정치적 통제 가능성)",
        "ais_observability": "High (싱가포르 항만 관제 레이더)",
    },
}

# 시장 프록시 티커 목록
MARKET_TICKERS = {
    "BDRY": {"name": "발틱 건화물 운임선물 ETF", "category": "Freight_Bulk", "unit": "USD"},
    "ZIM": {"name": "ZIM 컨테이너 해운", "category": "Shipping_Container", "unit": "USD"},
    "AMKBY": {"name": "머스크 (A.P. Moller-Maersk)", "category": "Shipping_Container", "unit": "USD"},
    "FRO": {"name": "프론트라인 (Frontline 원유탱커)", "category": "Shipping_Tanker", "unit": "USD"},
    "BZ=F": {"name": "브렌트유 선물 (Brent Crude)", "category": "Energy_Crude", "unit": "USD/bbl"},
    "CL=F": {"name": "WTI 원유 선물", "category": "Energy_Crude", "unit": "USD/bbl"},
    "NG=F": {"name": "천연가스 선물 (Henry Hub LNG)", "category": "Energy_Gas", "unit": "USD/MMBtu"},
}


def fetch_market_proxies() -> list[dict]:
    """Yahoo Finance에서 해운 운임 및 에너지 시장 프록시 시세를 수집한다."""
    import yfinance as yf

    results = []
    now_utc = datetime.now(timezone.utc).isoformat()
    tickers_list = list(MARKET_TICKERS.keys())
    print(f"  [yfinance] {len(tickers_list)}개 해운·에너지 프록시 지표 수집 중...")

    try:
        data = yf.download(tickers_list, period="1mo", interval="1d", progress=False)
        close_df = data["Close"]

        for ticker, meta in MARKET_TICKERS.items():
            if ticker not in close_df.columns:
                continue

            series = close_df[ticker].dropna()
            if series.empty:
                continue

            latest_val = float(series.iloc[-1])
            prev_val = float(series.iloc[-2]) if len(series) > 1 else latest_val
            month_ago_val = float(series.iloc[0])

            daily_chg = round((latest_val - prev_val) / prev_val * 100, 2) if prev_val > 0 else 0.0
            monthly_chg = round((latest_val - month_ago_val) / month_ago_val * 100, 2) if month_ago_val > 0 else 0.0

            # 리스크 신호 판정
            signal = "NORMAL"
            if abs(daily_chg) >= 5.0 or abs(monthly_chg) >= 20.0:
                signal = "CRITICAL_SPIKE" if (daily_chg > 5 or monthly_chg > 20) else "SHARP_DROP"
            elif abs(daily_chg) >= 2.5 or abs(monthly_chg) >= 10.0:
                signal = "ELEVATED"

            results.append({
                "ticker": ticker,
                "asset_name": meta["name"],
                "category": meta["category"],
                "unit": meta["unit"],
                "latest_price": round(latest_val, 2),
                "daily_change_pct": daily_chg,
                "monthly_change_pct": monthly_chg,
                "risk_signal": signal,
                "uncertainty_note": "금융 프록시 지표는 시장 심리와 위험 프리미엄을 반영하며 단독으로 실물 톤수를 의미하지 않음",
                "observed_at": now_utc,
            })
            print(f"    ✓ {ticker:6s} ({meta['name'][:18]:18s}): {latest_val:7.2f} {meta['unit']} (일간 {daily_chg:+.2f}%, 월간 {monthly_chg:+.2f}%) [{signal}]")
    except Exception as e:
        print(f"    ✗ yfinance 수집 오류: {e}")

    return results


def build_chokepoints_status(market_signals: list[dict]) -> list[dict]:
    """해협별 물리적 프로필과 시장 프록시 신호를 결합하여 조기경보 스냅샷을 생성한다."""
    now_utc = datetime.now(timezone.utc).isoformat()
    chokepoint_rows = []

    # 시장 신호 빠른 조회 맵
    signal_map = {m["ticker"]: m for m in market_signals}

    for code, info in CHOKEPOINTS.items():
        # 해협별 대표 센서 바인딩
        if code == "BAB_EL_MANDEB":
            rel_proxy = signal_map.get("ZIM") or signal_map.get("AMKBY")
            proxy_comment = f"컨테이너 선사 주가 변동률 {rel_proxy['daily_change_pct']}% (홍해 희망봉 우회 영향)" if rel_proxy else "N/A"
            alert_hint = "WARNING" if (rel_proxy and rel_proxy["risk_signal"] in ["CRITICAL_SPIKE", "ELEVATED"]) else "WATCH"
        elif code == "HORMUZ":
            oil_proxy = signal_map.get("BZ=F") or signal_map.get("CL=F")
            tanker_proxy = signal_map.get("FRO")
            oil_chg = oil_proxy['daily_change_pct'] if oil_proxy else 0.0
            proxy_comment = f"브렌트유 일간 {oil_chg}%, 원유 탱커선사 일간 {tanker_proxy['daily_change_pct'] if tanker_proxy else 0}%"
            alert_hint = "WARNING" if (oil_proxy and abs(oil_proxy["daily_change_pct"]) >= 3.0) else "WATCH"
        elif code == "TAIWAN_STRAIT":
            bdry_proxy = signal_map.get("BDRY")
            proxy_comment = f"벌크선 운임 ETF 일간 {bdry_proxy['daily_change_pct'] if bdry_proxy else 0}% (대만해협 통항 밀집)"
            alert_hint = "WATCH"
        else:
            proxy_comment = "동남아 항만 정상 통항 흐름"
            alert_hint = "NORMAL"

        chokepoint_rows.append({
            "chokepoint_code": code,
            "chokepoint_name_ko": info["name_ko"],
            "region": info["region"],
            "threat_actor": info["threat_actor"],
            "supply_chain_role": info["supply_chain_role"],
            "impact_sectors": info["impact_sectors"],
            "detour_delay": info["detour_cape_delay_days"],
            "insurance_war_risk": info["insurance_war_risk"],
            "ais_observability": info["ais_observability"],
            "market_proxy_signal": proxy_comment,
            "preliminary_chokepoint_alert": alert_hint,
            "uncertainty_note": "실제 선박 AIS 결측 및 GPS 재밍 구간 존재하므로 무장단체 성명/공식 보도와 교차확인 필요",
            "observed_at": now_utc,
        })

    return chokepoint_rows


def save_maritime_data(market_data: list[dict], chokepoints_data: list[dict]) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. 최신 CSV 저장 (시장 프록시)
    latest_csv = DATA_DIR / "maritime_latest.csv"
    if market_data:
        fieldnames = list(market_data[0].keys())
        with open(latest_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(market_data)
        print(f"\n✅ 시장 프록시 CSV 저장: {latest_csv} ({len(market_data)}건)")

        history_csv = HISTORY_DIR / f"maritime_{timestamp}.csv"
        with open(history_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(market_data)

    # 2. 해협별 종합 JSON 저장 (영수증 및 메타데이터 포함)
    summary_json = DATA_DIR / "maritime_summary.json"
    summary_content = {
        "schema_version": "1.0",
        "source": "yfinance_maritime_proxies_and_chokepoint_models",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total_market_proxies": len(market_data),
        "total_chokepoints": len(chokepoints_data),
        "data_contract_notice": "AIS 선박 척수 및 시장 지표는 화물 톤수를 단독 증명하지 못하므로 복수 신호 교차 검증 전용으로 사용함",
        "market_proxies": market_data,
        "chokepoints_status": chokepoints_data,
    }

    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary_content, f, ensure_ascii=False, indent=2)
    print(f"✅ 해협·항만 종합 JSON 저장: {summary_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="해협·항만 및 해상 운임·에너지 조기경보 수집기")
    args = parser.parse_args()

    print("=" * 65)
    print("🚢 해협·항만 AIS 프록시 및 운임·에너지 공급망 센서 수집 시작")
    print("=" * 65)

    market_proxies = fetch_market_proxies()
    chokepoints_status = build_chokepoints_status(market_proxies)
    save_maritime_data(market_proxies, chokepoints_status)
    print("\n🎉 해협·항만 공급망 센서 수집 및 영수증 저장 완료!")


if __name__ == "__main__":
    main()

