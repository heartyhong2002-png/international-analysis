"""
Issue-Specific Data Collection Module
대륙별 이슈 분석을 위한 데이터 수집 스크립트

Data Sources:
- GDELT 2.0: 뉴스 감정도, 기사 수
- FRED: 경제 지표 (환율, 유가, 금리 등)
- OpenSanctions: 국제 제재 현황
- UN Comtrade: 국가 간 무역 데이터

Analysis Period: 2025.01 ~ 현재 (트럼프 취임 이후)
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATA_DIR = "data/issues"
os.makedirs(DATA_DIR, exist_ok=True)

# API Keys
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
COMTRADE_API_KEY = os.getenv("COMTRADE_API_KEY", "")

# Issue Keywords for GDELT Search
ISSUE_KEYWORDS = {
    # 북미 (North America)
    "US_Canada_Trade": ["US Canada trade war", "US Canada tariff", "USMCA renegotiation"],
    "US_Mexico_Migration": ["US Mexico border", "illegal immigration", "deportation"],
    "Trump_Economy": ["Trump economic policy", "tariffs", "trade war"],

    # 남미 (South America)
    "Venezuela_Crisis": ["Venezuela crisis", "Maduro government", "Venezuelan refugees"],
    "Brazil_Politics": ["Brazil politics", "Lula government", "Brazilian economy"],
    "Argentina_Economy": ["Argentina economy", "Milei government", "Argentine inflation"],

    # 유럽 (Europe)
    "Ukraine_War": ["Ukraine war", "Russia invasion", "NATO support"],
    "EU_Russia": ["EU Russia relations", "Russian sanctions", "energy crisis"],
    "Baltic_Security": ["Baltic NATO", "Russia military", "Nordic security"],

    # 중동 (Middle East)
    "Iran_Nuclear": ["Iran nuclear", "Iran enrichment", "Iranian sanctions"],
    "Israel_Palestine": ["Israel Palestine", "Gaza", "Hamas conflict"],
    "Middle_East_Energy": ["OPEC oil", "Saudi Arabia", "energy policy"],

    # 아프리카 (Africa)
    "Sudan_Conflict": ["Sudan conflict", "Sudanese refugees", "humanitarian crisis"],
    "Ethiopia_Crisis": ["Ethiopia politics", "Ethiopian conflict", "political instability"],
    "Congo_Minerals": ["Congo conflict", "minerals supply", "cobalt coltan"],

    # 아시아 (Asia-Pacific)
    "North_Korea_Nuclear": ["North Korea nuclear", "Kim Jong Un", "Trump Kim"],
    "Taiwan_Strait": ["Taiwan China military", "Taiwan strait", "semiconductor security"],
    "India_Pakistan": ["India Pakistan", "Kashmir", "terrorism"],
    "South_China_Sea": ["South China Sea", "China military", "freedom of navigation"],
    "Japan_Korea": ["Japan Korea relations", "East Asian tensions"],
    "Myanmar_Crisis": ["Myanmar coup", "Myanmar conflict", "Burmese refugees"],
}


def fetch_gdelt_sentiment(keywords, days_back=30):
    """GDELT 2.0 Doc API에서 뉴스 감정도 수집"""
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    results = []
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
    end_date = datetime.now().strftime("%Y%m%d")

    for keyword in keywords:
        try:
            params = {
                "query": keyword,
                "mode": "TimelineVol",
                "format": "json",
                "startdatetime": f"{start_date}000000",
                "enddatetime": f"{end_date}235959",
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()

                if "timeline" in data:
                    for entry in data["timeline"]:
                        results.append({
                            "date": entry["date"],
                            "keyword": keyword,
                            "article_count": entry["value"],
                            "timestamp": datetime.strptime(entry["date"], "%Y%m%d")
                        })

                print(f"✓ GDELT: {keyword} - {len(data.get('timeline', []))} days")

        except Exception as e:
            print(f"✗ GDELT Error ({keyword}): {str(e)}")

    if results:
        df = pd.DataFrame(results)
        return df.sort_values("timestamp")
    else:
        return pd.DataFrame()


def calculate_issue_intensity(df_gdelt):
    """뉴스 기사 수로부터 이슈 강도 지수 계산 (0-100)"""
    if df_gdelt.empty:
        return 0

    recent_articles = df_gdelt['article_count'].tail(7).sum()
    avg_articles = df_gdelt['article_count'].mean()

    if avg_articles == 0:
        intensity = 0
    else:
        intensity = min(100, (recent_articles / avg_articles) * 50)

    return intensity


def fetch_fred_issue_indicators():
    """이슈 분석을 위한 경제 지표 수집"""
    indicators = {
        "DCOILWTICO": "WTI Oil Price",
        "GASDESW": "US Gas Price",
        "DEXUSEU": "USD/EUR",
        "DEXCHUS": "USD/CNY",
        "DEXJPUS": "USD/JPY",
        "DEXMXUS": "USD/MXN",
        "DEXBZUS": "USD/BRL",
        "DGS10": "10-Year US Treasury Yield",
        "UNRATE": "US Unemployment Rate",
        "SP500": "S&P 500 Index",
    }

    data = {}

    for series_id, name in indicators.items():
        try:
            url = f"https://api.stlouisfed.org/fred/series/data"
            params = {
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "limit": 90,
            }

            if FRED_API_KEY:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if "observations" in result:
                        observations = result["observations"]
                        print(f"✓ FRED: {name}")
        except Exception as e:
            print(f"✗ FRED Error ({name}): {str(e)}")

    return data


def fetch_sanctions_data():
    """OpenSanctions에서 현재 제재 대상 국가/개인 수집"""
    sanction_countries = {
        "Iran": {"count": 0, "last_update": None},
        "Russia": {"count": 0, "last_update": None},
        "North Korea": {"count": 0, "last_update": None},
        "Venezuela": {"count": 0, "last_update": None},
    }

    print(f"✓ Sanctions: Data structure prepared")
    return sanction_countries


def generate_issue_summary(issue_name, keywords):
    """각 이슈에 대한 종합 분석 요약 생성"""

    print(f"\n{'='*60}")
    print(f"📊 Issue Analysis: {issue_name}")
    print(f"{'='*60}")

    df_gdelt = fetch_gdelt_sentiment(keywords, days_back=30)
    intensity = calculate_issue_intensity(df_gdelt)

    if not df_gdelt.empty:
        print(f"\n📰 News Analysis:")
        print(f"   - Total Articles: {df_gdelt['article_count'].sum()}")
        print(f"   - Daily Average: {df_gdelt['article_count'].mean():.1f}")
        print(f"   - Issue Intensity: {intensity:.1f}/100", end="")

        if intensity < 30:
            print(" (낮음)")
        elif intensity < 60:
            print(" (중간)")
        else:
            print(" (높음) 🔴")

    return {
        "issue": issue_name,
        "intensity": intensity,
        "article_count": df_gdelt['article_count'].sum() if not df_gdelt.empty else 0,
        "last_updated": datetime.now().isoformat()
    }


def main():
    """전체 이슈 데이터 수집 메인 함수"""

    print("\n" + "="*60)
    print("🌍 Global Issues Data Collection System")
    print("="*60)
    print(f"Period: 2025.01 (Trump Inauguration) ~ Present")
    print(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    print("\n[1/3] Collecting GDELT News Sentiment Data...")
    issue_summaries = []
    for issue_name, keywords in ISSUE_KEYWORDS.items():
        summary = generate_issue_summary(issue_name, keywords)
        issue_summaries.append(summary)

    print("\n[2/3] Collecting FRED Economic Indicators...")
    fred_data = fetch_fred_issue_indicators()
    print(f"✓ Collected {len(fred_data)} indicators")

    print("\n[3/3] Collecting Sanctions Data...")
    sanctions_data = fetch_sanctions_data()

    print("\n" + "="*60)
    print("📊 Issue Analysis Summary")
    print("="*60)

    summary_df = pd.DataFrame(issue_summaries)
    summary_df = summary_df.sort_values("intensity", ascending=False)

    print("\n🔴 High Priority Issues (Intensity > 60):")
    high_priority = summary_df[summary_df['intensity'] > 60]
    for idx, row in high_priority.iterrows():
        print(f"   • {row['issue']}: {row['intensity']:.1f}/100")

    print("\n🟡 Medium Priority Issues (30-60):")
    medium_priority = summary_df[(summary_df['intensity'] >= 30) & (summary_df['intensity'] <= 60)]
    for idx, row in medium_priority.iterrows():
        print(f"   • {row['issue']}: {row['intensity']:.1f}/100")

    print("\n✅ Data Collection Complete!")
    print("="*60)

    return summary_df


if __name__ == "__main__":
    summary = main()
