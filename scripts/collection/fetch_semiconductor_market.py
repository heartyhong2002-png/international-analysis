"""
fetch_semiconductor_market.py — 글로벌 반도체 3대 밸류체인(완제품·설비·소재) 지수 및 DRAM 현물가 수집기
========================================================================================================
조기경보 목적:
  - 단순 뉴스 텍스트만으로는 파악하기 어려운 실제 반도체 공급망 충격(주가 급락, 설비 수주 위축, 메모리 현물가 변동)을
    3대 레이어(완제품/지수 ➔ 4대 독점 설비사 ➔ 원소재/실물 DRAM·GDDR 현물가)로 정량 수집한다.
  - 100% 무료 공개 데이터(yfinance + TrendForce DRAMeXchange 공개 고시 테이블)만 사용하며 API 키가 불필요하다.

산출물:
  - data/semiconductor_market/semiconductor_latest.json
  - data/semiconductor_market/semiconductor_latest.csv
  - data/semiconductor_market/receipt_latest.json
"""

from __future__ import annotations

import csv
import json
import re
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
import yfinance as yf
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "semiconductor_market"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON = DATA_DIR / "semiconductor_latest.json"
OUTPUT_CSV = DATA_DIR / "semiconductor_latest.csv"
RECEIPT_JSON = DATA_DIR / "receipt_latest.json"

# 3대 밸류체인 레이어 정의
SEMICONDUCTOR_BASKET: List[Dict[str, str]] = [
    # Layer 1: 글로벌 대표 지수 및 완제품/파운드리
    {
        "ticker": "^SOX",
        "name": "필라델피아 반도체 지수 (SOX)",
        "layer": "1_INDEX_CHIPMAKER",
        "role": "글로벌 반도체 30대 기업 종합 벤치마크",
        "currency": "pt",
    },
    {
        "ticker": "NVDA",
        "name": "NVIDIA (엔비디아)",
        "layer": "1_INDEX_CHIPMAKER",
        "role": "AI GPU(H100·B200) 독점 설계 및 대중 수출통제 핵심 타깃",
        "currency": "USD",
    },
    {
        "ticker": "TSM",
        "name": "TSMC (ADR)",
        "layer": "1_INDEX_CHIPMAKER",
        "role": "글로벌 첨단 파운드리 1위 · 대만해협 지정학 직결",
        "currency": "USD",
    },
    {
        "ticker": "000660.KS",
        "name": "SK하이닉스",
        "layer": "1_INDEX_CHIPMAKER",
        "role": "글로벌 HBM(고대역폭 메모리) 1위 · 한국 공급망 핵심",
        "currency": "KRW",
    },
    {
        "ticker": "005930.KS",
        "name": "삼성전자",
        "layer": "1_INDEX_CHIPMAKER",
        "role": "글로벌 메모리 1위 및 종합반도체(IDM)",
        "currency": "KRW",
    },
    # Layer 2: 4대 독점 반도체 설비·장비사 (Equipment Chokepoints)
    {
        "ticker": "ASML",
        "name": "ASML (네덜란드)",
        "layer": "2_EQUIPMENT_CHOKEPOINT",
        "role": "EUV(극자외선) 노광장비 전 세계 100% 독점 · 대중 제재 핵심",
        "currency": "USD",
    },
    {
        "ticker": "AMAT",
        "name": "Applied Materials (AMAT)",
        "layer": "2_EQUIPMENT_CHOKEPOINT",
        "role": "글로벌 1위 종합 반도체 증착·식각 설비",
        "currency": "USD",
    },
    {
        "ticker": "LRCX",
        "name": "Lam Research (램리서치)",
        "layer": "2_EQUIPMENT_CHOKEPOINT",
        "role": "글로벌 1위 식각(Etch) 및 HBM/3D NAND 수직적층 핵심 설비",
        "currency": "USD",
    },
    {
        "ticker": "KLAC",
        "name": "KLA Corp",
        "layer": "2_EQUIPMENT_CHOKEPOINT",
        "role": "웨이퍼 결함 검사 및 수율 계측(Metrology) 독점 설비",
        "currency": "USD",
    },
    # Layer 3: 핵심 원소재·웨이퍼·희토류 (Materials & Minerals)
    {
        "ticker": "4063.T",
        "name": "신에츠 화학 (Shin-Etsu)",
        "layer": "3_MATERIALS_MINERALS",
        "role": "글로벌 실리콘 웨이퍼(원판) 시장 점유율 1위 (일본)",
        "currency": "JPY",
    },
    {
        "ticker": "MP",
        "name": "MP Materials",
        "layer": "3_MATERIALS_MINERALS",
        "role": "북미 최대 희토류(네오디뮴 등) 광산·정련 공급망",
        "currency": "USD",
    },
]


def fetch_yfinance_basket() -> List[Dict[str, Any]]:
    """yfinance를 통해 반도체 지수·설비·소재 바스켓의 최근 1개월 시세 및 변동률을 수집한다."""
    print("📈 [1/2] 글로벌 반도체 지수·설비·소재 바스켓(yfinance) 수집 중...")
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=35)

    records: List[Dict[str, Any]] = []
    for item in SEMICONDUCTOR_BASKET:
        ticker = item["ticker"]
        try:
            df = yf.download(
                ticker,
                start=start_dt.strftime("%Y-%m-%d"),
                end=(end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                progress=False,
            )
            if df is None or df.empty:
                print(f"  ⚠️ 시세 없음: {item['name']} ({ticker})")
                continue

            close_col = df["Close"]
            if hasattr(close_col, "columns"):
                close_series = close_col[ticker].dropna()
            else:
                close_series = close_col.dropna()

            if len(close_series) < 2:
                continue

            latest_val = float(close_series.iloc[-1])
            prev_val = float(close_series.iloc[-2])
            week_ref = float(close_series.iloc[-6]) if len(close_series) >= 6 else float(close_series.iloc[0])
            month_ref = float(close_series.iloc[0])

            day_pct = ((latest_val - prev_val) / prev_val) * 100.0
            week_pct = ((latest_val - week_ref) / week_ref) * 100.0
            month_pct = ((latest_val - month_ref) / month_ref) * 100.0

            if day_pct <= -3.0 or week_pct <= -7.0:
                status = "⚠️ 급락 주의 (VOLATILE_DROP)"
            elif day_pct >= 3.0 or week_pct >= 7.0:
                status = "🔥 강세 급등 (SURGE)"
            else:
                status = "✅ 안정 (STABLE)"

            latest_date = str(close_series.index[-1])[:10]
            rec = {
                "category": item["layer"],
                "ticker": ticker,
                "name": item["name"],
                "role": item["role"],
                "currency": item["currency"],
                "latest_price": round(latest_val, 2),
                "day_change_pct": round(day_pct, 2),
                "week_change_pct": round(week_pct, 2),
                "month_change_pct": round(month_pct, 2),
                "status_signal": status,
                "observed_date": latest_date,
            }
            records.append(rec)
            print(f"  ✓ {item['name']} ({ticker}): {latest_val:,.2f} {item['currency']} (1일 {day_pct:+.2f}%, 1주 {week_pct:+.2f}%)")
        except Exception as e:
            print(f"  ❌ 오류 ({ticker}): {e}")

    return records


def fetch_dramexchange_spot() -> List[Dict[str, Any]]:
    """TrendForce DRAMeXchange 메인 페이지에서 실시간 DRAM/GDDR/모듈 현물 가격을 수집한다."""
    print("💾 [2/2] TrendForce DRAMeXchange 실물 메모리(DDR5/DDR4/GDDR) 현물가 크롤링 중...")
    url = "https://www.dramexchange.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    spot_items: List[Dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        target_prefixes = ("DDR5", "DDR4", "GDDR5", "GDDR6", "LPDDR")
        seen_names = set()

        for tr in soup.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) >= 7:
                item_name = cells[0]
                if item_name.startswith(target_prefixes) and item_name not in seen_names:
                    seen_names.add(item_name)
                    try:
                        session_avg = float(re.sub(r"[^0-9.]", "", cells[5]) or 0.0)
                    except ValueError:
                        session_avg = 0.0
                    change_str = cells[6]
                    spot_items.append({
                        "item": item_name,
                        "daily_high_usd": cells[1],
                        "daily_low_usd": cells[2],
                        "session_avg_usd": session_avg,
                        "session_change": change_str,
                        "source": "TrendForce_DRAMeXchange",
                    })
                    print(f"  ✓ [현물가] {item_name}: 평균 ${session_avg:.3f} ({change_str})")
    except Exception as e:
        print(f"  ⚠️ DRAMeXchange 스크래핑 실패: {e}")

    return spot_items


def main() -> None:
    now_utc = datetime.now(timezone.utc).isoformat()
    equities = fetch_yfinance_basket()
    spot_prices = fetch_dramexchange_spot()

    payload = {
        "collected_at_utc": now_utc,
        "source_summary": {
            "equities_count": len(equities),
            "spot_memory_count": len(spot_prices),
        },
        "equities_and_indices": equities,
        "memory_spot_prices": spot_prices,
    }

    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV 저장 (주식·지수 바스켓)
    if equities:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(equities[0].keys()))
            writer.writeheader()
            writer.writerows(equities)

    receipt = {
        "collector": "fetch_semiconductor_market.py",
        "collected_at_utc": now_utc,
        "equities_collected": len(equities),
        "spot_items_collected": len(spot_prices),
        "output_json": str(OUTPUT_JSON.relative_to(ROOT)),
        "output_csv": str(OUTPUT_CSV.relative_to(ROOT)),
        "status": "SUCCESS" if (equities or spot_prices) else "EMPTY",
    }
    RECEIPT_JSON.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")

    print("-" * 70)
    print(f"✅ 반도체 밸류체인(지수·설비·소재·현물가) 수집 완료!")
    print(f"   - 지수/설비/소재 종목: {len(equities)}개")
    print(f"   - 실물 메모리 현물가: {len(spot_prices)}개")
    print(f"   - 저장 경로: {OUTPUT_JSON.relative_to(ROOT)}")
    print("-" * 70)


if __name__ == "__main__":
    main()
