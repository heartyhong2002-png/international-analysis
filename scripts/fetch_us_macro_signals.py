"""
fetch_us_macro_signals.py
=========================
미국의 현재 정치, 경제, 금융, 외교 상황을 종합 수집하는 모듈.

4대 수집 영역:
1. [경제 (Economy)]: 인플레이션(CPI), 실업률(UNRATE), 연방기준금리(FEDFUNDS), 소비자심리지수
2. [금융 (Finance)]: 장단기 금리차(T10Y2Y), 10년물 국채(DGS10), 달러 인덱스(DTWEXBGS),
                    하이일드 신용스프레드, 금융스트레스지수(STLFSI4), S&P500, VIX 변동성지수
3. [정치 (Politics)]: 미국 경제/정치 정책 불확실성 지수(USEPUINDXD),
                     연방관보(Federal Register) 백악관 대통령 행정명령(Executive Orders) 및 포고령
4. [외교 (Diplomacy)]: 미 국무부(U.S. State Dept) 공식 보도자료 및 정례 브리핑 RSS,
                      연방관보 대외 제재 및 통상 조치

저장 경로:
- data/us_signals/us_macro_financial_indicators.csv  (시계열 거시/금융 데이터)
- data/us_signals/us_presidential_actions.csv         (백악관 행정명령/정치 조치)
- data/us_signals/us_diplomatic_statements.csv       (국무부 공식 외교 발표)
- data/us_signals/us_comprehensive_snapshot.json     (종합 브리핑 스냅샷)
"""

import os
import sys
import json
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pandas as pd
import requests

# Windows 콘솔 UTF-8 강제
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "us_signals")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 브라우저 위장 헤더 (State Dept 및 연방 사이트 403 차단 방지)
REQUEST_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
}

# ============================================================================
# 1. 미국 거시경제 및 금융 지표 정의 (FRED 공식 시계열)
# ============================================================================
FRED_SERIES = {
    # 경제 지표 (Economy)
    "CPIAUCSL": {"name": "Consumer_Price_Index", "category": "Economy", "unit": "Index 1982-1984=100", "desc": "미국 소비자물가지수 (CPI)"},
    "UNRATE": {"name": "Unemployment_Rate", "category": "Economy", "unit": "%", "desc": "미국 실업률"},
    "FEDFUNDS": {"name": "Federal_Funds_Rate", "category": "Economy", "unit": "%", "desc": "연방기금 유효금리 (기준금리)"},
    
    # 금융 지표 (Finance)
    "T10Y2Y": {"name": "Yield_Curve_Spread_10Y2Y", "category": "Finance", "unit": "%", "desc": "장단기 금리차 (10년-2년, 경기침체 선행지표)"},
    "DGS10": {"name": "Treasury_Yield_10Y", "category": "Finance", "unit": "%", "desc": "미 국채 10년물 금리"},
    "DTWEXBGS": {"name": "Trade_Weighted_USD_Index", "category": "Finance", "unit": "Index Jan 2006=100", "desc": "명목 교역가중 달러 인덱스 (달러 위상)"},
    "BAMLH0A0HYM2": {"name": "High_Yield_Credit_Spread", "category": "Finance", "unit": "%", "desc": "미국 하이일드 채권 스프레드 (기업 부도/신용 리스크)"},
    "STLFSI4": {"name": "Financial_Stress_Index", "category": "Finance", "unit": "Index", "desc": "세인트루이스 연준 금융스트레스지수 (0 이상=스트레스 가중)"},
    "VIXCLS": {"name": "VIX_Volatility_Index", "category": "Finance", "unit": "Index", "desc": "CBOE VIX 변동성지수 (시장 공포 지수)"},
    "SP500": {"name": "SP500_Stock_Index", "category": "Finance", "unit": "Points", "desc": "S&P 500 주가지수"},
    
    # 정치/정책 불확실성 지표 (Politics)
    "USEPUINDXD": {"name": "Economic_Policy_Uncertainty", "category": "Politics", "unit": "Index", "desc": "미국 경제/정치 정책 불확실성 지수"},
}


def fetch_fred_indicators(start_date: str = "2025-01-01") -> tuple[pd.DataFrame, dict]:
    """FRED 무료 공식 엔드포인트에서 11개 핵심 거시/금융/정책 지표 수집"""
    print("\n" + "=" * 60)
    print("📈 [1/3] 미국 경제·금융·정책 지표 수집 (FRED)")
    print("=" * 60)

    all_dfs = []
    latest_snapshot = {}

    for series_id, meta in FRED_SERIES.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        try:
            df = pd.read_csv(url)
            # 결측치(마침표 등) 정리
            df.columns = ["date", "value"]
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna().sort_values("date")
            df = df[df["date"] >= start_date]

            if df.empty:
                print(f"  ⚠️ {series_id} ({meta['name']}): 지정 기간({start_date}~) 데이터 없음")
                continue

            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else last_row

            latest_val = float(last_row["value"])
            prev_val = float(prev_row["value"])
            change = latest_val - prev_val

            df["series_id"] = series_id
            df["indicator_name"] = meta["name"]
            df["category"] = meta["category"]
            all_dfs.append(df)

            latest_snapshot[meta["name"]] = {
                "series_id": series_id,
                "category": meta["category"],
                "value": latest_val,
                "prev_value": prev_val,
                "change": round(change, 4),
                "date": str(last_row["date"]),
                "description": meta["desc"],
                "unit": meta["unit"]
            }

            print(f"  ✓ {meta['desc']}: {latest_val} {meta['unit']} (기준일: {last_row['date']}, 변동: {change:+.3f})")

        except Exception as e:
            print(f"  ✗ {series_id} 수집 실패: {e}")

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        csv_path = os.path.join(OUTPUT_DIR, "us_macro_financial_indicators.csv")
        combined_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"💾 시계열 데이터 저장 완료: {csv_path} ({len(combined_df)}행)")
        return combined_df, latest_snapshot

    return pd.DataFrame(), {}


# ============================================================================
# 2. 미국 정치 상황: 연방관보(Federal Register) 대통령 행정명령 & 조치
# ============================================================================
def fetch_presidential_actions(per_page: int = 25) -> pd.DataFrame:
    """Federal Register 공식 API를 통해 최신 백악관 행정명령, 포고령, 관세/비상사태 조치 수집"""
    print("\n" + "=" * 60)
    print("🏛️ [2/3] 미국 정치 상황: 백악관 대통령 행정명령 & 주요 조치 수집")
    print("=" * 60)

    url = (
        "https://www.federalregister.gov/api/v1/documents.json"
        f"?conditions[type][]=PRESDOCU&per_page={per_page}&order=newest"
    )

    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
        if res.status_code != 200:
            print(f"  ⚠️ 연방관보 API 오류 (HTTP {res.status_code})")
            return pd.DataFrame()

        data = res.json().get("results", [])
        records = []
        for doc in data:
            records.append({
                "date": doc.get("publication_date"),
                "type": doc.get("subtype") or doc.get("type"),
                "title": doc.get("title"),
                "executive_order_number": doc.get("executive_order_number"),
                "abstract": doc.get("abstract") or "",
                "html_url": doc.get("html_url"),
                "pdf_url": doc.get("pdf_url"),
                "source": "Federal_Register_Presidential_Documents"
            })

        df = pd.DataFrame(records)
        csv_path = os.path.join(OUTPUT_DIR, "us_presidential_actions.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        print(f"✓ 최근 대통령 조치 {len(df)}건 수집 완료")
        for idx, row in df.head(5).iterrows():
            eo_tag = f" [EO #{row['executive_order_number']}]" if row['executive_order_number'] else ""
            print(f"  • [{row['date']}] {row['type']}{eo_tag}: {row['title'][:75]}...")

        print(f"💾 행정명령 데이터 저장 완료: {csv_path}")
        return df

    except Exception as e:
        print(f"  ✗ 연방관보 수집 실패: {e}")
        return pd.DataFrame()


# ============================================================================
# 3. 미국 외교 상황: 미 국무부(State Dept) 공식 성명 및 브리핑
# ============================================================================
STATE_DEPT_FEEDS = {
    "Press_Releases": "https://www.state.gov/rss-feed/press-releases/feed/",
    "Press_Briefings": "https://www.state.gov/rss-feed/department-press-briefings/feed/",
    "East_Asia_Pacific": "https://www.state.gov/rss-feed/east-asia-and-the-pacific/feed/",
    "Near_East_Middle_East": "https://www.state.gov/rss-feed/near-east/feed/",
    "Europe_Eurasia": "https://www.state.gov/rss-feed/europe-and-eurasia/feed/",
}


def fetch_state_department_statements(max_per_feed: int = 10) -> pd.DataFrame:
    """미 국무부 공식 RSS 피드에서 최신 외교 브리핑 및 성명 수집"""
    print("\n" + "=" * 60)
    print("🌐 [3/3] 미국 외교 상황: 미 국무부(State Dept) 공식 외교 발표 수집")
    print("=" * 60)

    records = []
    for feed_name, feed_url in STATE_DEPT_FEEDS.items():
        try:
            res = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=15)
            if res.status_code != 200:
                print(f"  ⚠️ {feed_name} 접근 실패 (HTTP {res.status_code})")
                continue

            root = ET.fromstring(res.content)
            channel = root.find("channel")
            if channel is None:
                continue

            items = channel.findall("item")[:max_per_feed]
            for it in items:
                title = it.findtext("title") or ""
                link = it.findtext("link") or ""
                pub_date = it.findtext("pubDate") or ""
                desc = it.findtext("description") or ""

                # 날짜 표준화
                clean_date = pub_date
                try:
                    dt = datetime.strptime(pub_date[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                    clean_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

                records.append({
                    "date": clean_date,
                    "category": feed_name,
                    "title": title.strip(),
                    "link": link.strip(),
                    "description": desc.strip()[:200],
                    "source": "US_Department_of_State"
                })

            print(f"  ✓ {feed_name}: {len(items)}건 수집 완료")

        except Exception as e:
            print(f"  ✗ {feed_name} 수집 실패: {e}")

    df = pd.DataFrame(records)
    if not df.empty:
        # 중복 링크 제거
        df = df.drop_duplicates(subset=["link"]).sort_values("date", ascending=False)
        csv_path = os.path.join(OUTPUT_DIR, "us_diplomatic_statements.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"💾 외교 발표 데이터 저장 완료: {csv_path} (총 {len(df)}건)")
        return df

    return pd.DataFrame()


# ============================================================================
# 메인 실행 및 스냅샷 생성
# ============================================================================
def main():
    start_time = time.time()
    print("\n🇺🇸 [미국 종합 시그널 수집기 가동: 정치·경제·금융·외교]")
    print(f"기준 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 경제 & 금융 지표
    macro_df, latest_macro = fetch_fred_indicators(start_date="2025-01-01")

    # 2. 정치 (백악관 행정명령)
    pres_df = fetch_presidential_actions(per_page=30)

    # 3. 외교 (국무부 성명)
    diplo_df = fetch_state_department_statements(max_per_feed=10)

    # 4. 통합 종합 브리핑 JSON 스냅샷 저장
    snapshot = {
        "updated_at": datetime.now().isoformat(),
        "macro_and_finance": latest_macro,
        "recent_presidential_actions_count": len(pres_df),
        "recent_diplomatic_statements_count": len(diplo_df),
        "recent_top_presidential_actions": pres_df.head(5).to_dict("records") if not pres_df.empty else [],
        "recent_top_diplomatic_statements": diplo_df.head(5).to_dict("records") if not diplo_df.empty else []
    }

    snapshot_path = os.path.join(OUTPUT_DIR, "us_comprehensive_snapshot.json")
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ 미국 종합 데이터 수집 완료! ({elapsed:.1f}초 소요)")
    print(f"📂 저장 위치: {OUTPUT_DIR}")
    print(f"  - 거시/금융 시계열: us_macro_financial_indicators.csv")
    print(f"  - 백악관 행정명령: us_presidential_actions.csv")
    print(f"  - 국무부 외교발표: us_diplomatic_statements.csv")
    print(f"  - 종합 분석 스냅샷: us_comprehensive_snapshot.json")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
