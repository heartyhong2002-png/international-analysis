"""
국제정세 분석 - 데이터 수집 스크립트
World Bank API, NewsAPI 등에서 실시간 데이터를 수집합니다.
"""

import pandas as pd
import requests
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Windows 터미널에서 이모지 출력 시 발생하는 cp949 인코딩 에러 방지
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드 (부모 폴더에 위치한 .env)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# 폴더 설정
DATA_DIR = Path(__file__).parent.parent / "data"

# ============================================================================
# 1. World Bank API - 경제 데이터
# ============================================================================

def fetch_world_bank_data():
    """
    World Bank API에서 경제 데이터 수집
    GDP, 실업률, 인플레이션 등의 지표
    """
    print("📊 World Bank 데이터 수집 중...")
    
    try:
        # 수집할 지표 코드
        indicators = {
            'NY.GDP.MKTP.CD': 'GDP',           # 국내 총생산 (현재 USD)
            'NY.GDP.PCAP.CD': 'GDP_per_capita', # 1인당 GDP
            'FP.CPI.TOTL.ZG': 'Inflation',     # 인플레이션
            'SP.URB.TOTL.IN.ZS': 'Urban_Pop'   # 도시 인구
        }
        
        countries = ['USA', 'GBR', 'DEU', 'FRA', 'CHN', 'IRN', 'ISR']
        
        data = []
        
        for country in countries:
            for indicator_code, indicator_name in indicators.items():
                url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator_code}"
                params = {'format': 'json', 'per_page': 60}
                
                try:
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        if len(result) > 1 and result[1]:
                            for record in result[1]:
                                if record['value']:
                                    data.append({
                                        'Country': country,
                                        'Indicator': indicator_name,
                                        'Year': int(record['date']),
                                        'Value': float(record['value'])
                                    })
                except Exception as e:
                    print(f"⚠️ {country}-{indicator_name} 수집 실패: {e}")
                    continue
        
        if data:
            df = pd.DataFrame(data)
            print(f"✓ {len(df)}개 레코드 수집 완료")
            return df
        else:
            print("⚠️ World Bank 데이터 없음")
            return None
            
    except Exception as e:
        print(f"❌ World Bank API 오류: {e}")
        return None


# ============================================================================
# 1.5 NewsAPI - 뉴스 데이터 수집
# ============================================================================

def fetch_news_data():
    """
    NewsAPI에서 주요 국제정세 관련 뉴스를 수집합니다.
    """
    print("\n📰 NewsAPI 데이터 수집 중...")
    
    api_key = os.environ.get("NEWSAPI_API_KEY")
    if not api_key:
        print("⚠️ .env 파일에 NEWSAPI_API_KEY가 설정되지 않았습니다.")
        return None
        
    try:
        url = "https://newsapi.org/v2/everything"
        # 검색 키워드: 미국 국제 정책, 중동 분쟁, 미중 무역
        query = "(USA AND international policy) OR (Middle East AND conflict) OR (US AND China AND trade)"
        
        # 최근 7일 기사 검색
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        params = {
            'q': query,
            'from': from_date,
            'sortBy': 'relevancy',
            'apiKey': api_key,
            'language': 'en',
            'pageSize': 20
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            articles = result.get('articles', [])
            
            data = []
            for article in articles:
                data.append({
                    'Date': article.get('publishedAt', '')[:10],
                    'Title': article.get('title'),
                    'Source': article.get('source', {}).get('name'),
                    'URL': article.get('url')
                })
                
            if data:
                df = pd.DataFrame(data)
                df.to_csv(DATA_DIR / "news_data.csv", index=False)
                print(f"✓ {len(df)}개 뉴스 기사 수집 완료 (news_data.csv 저장됨)")
                return df
            else:
                print("⚠️ 수집된 뉴스 기사가 없습니다.")
                return None
        else:
            print(f"⚠️ NewsAPI 호출 실패: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ NewsAPI 오류: {e}")
        return None

# ============================================================================
# 1.6 여론조사 데이터 수집 (RealClearPolling)
# ============================================================================

def fetch_polling_data():
    """
    Playwright를 사용해 RealClearPolling에서 미국 대통령 지지율(RCP Average)을 수집합니다.
    """
    print("\n📈 여론조사 데이터 수집 중 (RealClearPolling)...")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("⚠️ playwright 라이브러리가 설치되지 않았습니다. 터미널에서 설치를 진행해주세요.")
        return None
        
    try:
        with sync_playwright() as p:
            # 브라우저 실행 (headless=True 시 화면에 안 보임)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # User-Agent 설정 (봇 차단 우회)
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            
            url = "https://www.realclearpolling.com/polls/approval/joe-biden/approval-rating"
            page.goto(url, wait_until="networkidle")
            
            # pandas를 이용해 HTML 내의 모든 표(Table) 가져오기
            try:
                from io import StringIO
                dfs = pd.read_html(StringIO(page.content()))
                rcp_df = None
                
                # 'RCP Average' 문구가 포함된 표를 찾음
                for df in dfs:
                    if df.apply(lambda row: row.astype(str).str.contains('RCP Average', case=False).any(), axis=1).any():
                        rcp_df = df
                        break
                        
                if rcp_df is not None:
                    # 데이터 저장
                    rcp_df.to_csv(DATA_DIR / "rcp_approval_polls.csv", index=False)
                    print(f"✓ 여론조사 데이터 수집 완료 (rcp_approval_polls.csv 저장됨)")
                    
                    # 가장 최근 RCP Average 출력
                    try:
                        avg_row = rcp_df[rcp_df.apply(lambda row: row.astype(str).str.contains('RCP Average', case=False).any(), axis=1)].iloc[0]
                        print(f"   ➔ 현재 RCP 지지율 평균: 찬성 {avg_row[3]}% / 반대 {avg_row[4]}%")
                    except:
                        pass
                        
                    return rcp_df
                else:
                    print("⚠️ 여론조사 표를 찾을 수 없습니다.")
                    
            except Exception as e:
                print(f"⚠️ 표 파싱 오류 (lxml 라이브러리가 필요합니다): {e}")
                
            browser.close()
            return None
            
    except Exception as e:
        print(f"❌ 여론조사 수집 오류: {e}")
        return None

# ============================================================================
# 2. 수동 데이터 입력 템플릿 생성
# ============================================================================

def create_manual_template():
    """
    사용자가 직접 입력할 수 있는 템플릿 생성
    """
    print("\n📝 수동 입력 템플릿 생성 중...")
    
    # USA/Western 데이터 템플릿
    usa_template = pd.DataFrame({
        'Date': pd.date_range(start=datetime.now().date(), periods=30, freq='D'),
        'USA_Influence_Index': [70 + (i % 5) for i in range(30)],
        'NATO_Strength': [85 + (i % 3) for i in range(30)],
        'EU_Stability': [75 + (i % 4) for i in range(30)],
        'Notes': [''] * 30
    })
    usa_template.to_csv(DATA_DIR / "manual_usa_west.csv", index=False)
    print("✓ manual_usa_west.csv 템플릿 생성")
    
    # Middle East 데이터 템플릿
    me_template = pd.DataFrame({
        'Date': pd.date_range(start=datetime.now().date(), periods=30, freq='D'),
        'Tension_Level': [72 + (i % 8) for i in range(30)],
        'Stability_Index': [45 + (i % 6) for i in range(30)],
        'Major_Events': [''] * 30
    })
    me_template.to_csv(DATA_DIR / "manual_middle_east.csv", index=False)
    print("✓ manual_middle_east.csv 템플릿 생성")
    
    # Trade/Economics 데이터 템플릿
    trade_template = pd.DataFrame({
        'Date': pd.date_range(start=datetime.now().date(), periods=30, freq='D'),
        'Global_Trade_Index': [100 + (i % 5 - 2) for i in range(30)],
        'Tariff_Tension': [45 + (i % 10) for i in range(30)],
        'Exchange_Rate_USD_CNY': [7.0 + (i * 0.01) for i in range(30)],
        'Oil_Price_USD': [85 + (i % 5) for i in range(30)]
    })
    trade_template.to_csv(DATA_DIR / "manual_trade_economics.csv", index=False)
    print("✓ manual_trade_economics.csv 템플릿 생성")


# ============================================================================
# 3. 데이터 병합 및 정제
# ============================================================================

def merge_and_clean_data():
    """
    API 데이터와 수동 데이터 병합
    """
    print("\n🔄 데이터 병합 및 정제 중...")
    
    try:
        # 기존 CSV 파일 읽기 (있으면)
        if (DATA_DIR / "usa_west.csv").exists():
            usa_df = pd.read_csv(DATA_DIR / "usa_west.csv")
            print(f"✓ USA/Western 데이터: {len(usa_df)}개 레코드")
        
        if (DATA_DIR / "middle_east.csv").exists():
            me_df = pd.read_csv(DATA_DIR / "middle_east.csv")
            print(f"✓ Middle East 데이터: {len(me_df)}개 레코드")
        
        if (DATA_DIR / "trade_economics.csv").exists():
            trade_df = pd.read_csv(DATA_DIR / "trade_economics.csv")
            print(f"✓ Trade/Economics 데이터: {len(trade_df)}개 레코드")
            
    except Exception as e:
        print(f"⚠️ 데이터 병합 오류: {e}")


# ============================================================================
# 4. 메인 함수
# ============================================================================

def main():
    """메인 함수"""
    print("=" * 60)
    print("국제정세 분석 - 데이터 수집 시작")
    print(f"수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 폴더 생성
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. World Bank 데이터 수집
        wb_data = fetch_world_bank_data()
        
        # 1.5 NewsAPI 뉴스 수집
        news_data = fetch_news_data()
        
        # 1.6 RealClearPolling 여론조사 수집 (Playwright 기반)
        polling_data = fetch_polling_data()
        
        # 2. 수동 입력 템플릿 생성
        create_manual_template()
        
        # 3. 데이터 병합 및 정제
        merge_and_clean_data()
        
        print("\n" + "=" * 60)
        print("✅ 데이터 수집 완료!")
        print(f"📁 저장 위치: {DATA_DIR}")
        print("=" * 60)
        print("\n💡 팁:")
        print("1. manual_*.csv 파일을 열어서 직접 데이터를 입력하세요")
        print("2. 매주 금요일에 이 스크립트를 실행하세요")
        print("3. CSV 파일을 편집 후 generate_charts.py를 실행하면 차트가 생성됩니다")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
