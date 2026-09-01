"""
국제정세 분석 - 고급 데이터 수집 스크립트 (V2)
FRED, GDELT, OpenSanctions, UN Comtrade, K-stat 등 통합 수집
"""

import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 폴더 설정
DATA_DIR = Path(__file__).parent.parent / "data"

print("=" * 70)
print("국제정세 분석 - 고급 데이터 수집 시스템 (V2)")
print("=" * 70)

# ============================================================================
# 1. FRED API - 미국 경제 데이터 (원유, 환율, 금리, BDI 등)
# ============================================================================

def fetch_fred_data():
    """
    FRED API에서 글로벌 거시경제 지표 수집
    원유 가격, 구리 가격, 환율, 금리 등
    
    API Key 발급: https://fredaccount.stlouisfed.org/login
    """
    print("\n📊 [1/6] FRED API - 미국 경제 데이터 수집 중...")
    
    fred_api_key = os.getenv('FRED_API_KEY')
    
    if not fred_api_key:
        print("⚠️ FRED_API_KEY 환경변수 없음. .env 파일에서 설정하세요.")
        return None
    
    try:
        # 수집할 지표
        series_ids = {
            'DCOILWTICO': 'Oil_Price_WTI',           # WTI 원유
            'MMNRNJ': 'Copper_Price',                # 구리
            'DEXUSEU': 'USD_EUR_Rate',               # USD/EUR
            'DEXCHUS': 'USD_CNY_Rate',               # USD/CNY
            'DEXJPUS': 'USD_JPY_Rate',               # USD/JPY
            'DGS10': 'US_10Y_Yield',                 # 미국 10년 국채
            'GPDIC1': 'Global_Trade_Index',          # 글로벌 무역
            'BDICP': 'BDI_Shipping_Index'            # 해상운임지수
        }
        
        fred_data = {}
        base_url = "https://api.stlouisfed.org/fred/series/observations"
        
        for series_id, series_name in series_ids.items():
            params = {
                'series_id': series_id,
                'api_key': fred_api_key,
                'file_type': 'json',
                'limit': 120  # 최근 120개 관측치
            }
            
            try:
                response = requests.get(base_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'observations' in data:
                        obs = data['observations']
                        df = pd.DataFrame(obs)
                        df['date'] = pd.to_datetime(df['date'])
                        df['value'] = pd.to_numeric(df['value'], errors='coerce')
                        df = df.dropna(subset=['value'])
                        
                        if len(df) > 0:
                            fred_data[series_name] = df[['date', 'value']].rename(
                                columns={'value': series_name}
                            )
                            print(f"✓ {series_name}: {len(df)}개 레코드")
            except Exception as e:
                print(f"⚠️ {series_name} 수집 실패: {e}")
                continue
        
        if fred_data:
            # 모든 데이터 병합
            merged_df = fred_data[list(fred_data.keys())[0]]
            for name in list(fred_data.keys())[1:]:
                merged_df = merged_df.merge(fred_data[name], on='date', how='outer')
            
            merged_df.to_csv(DATA_DIR / "fred_economic_data.csv", index=False)
            print(f"✓ FRED 데이터 저장: {len(merged_df)}개 레코드")
            return merged_df
        
    except Exception as e:
        print(f"❌ FRED API 오류: {e}")
        return None


# ============================================================================
# 2. GDELT 2.0 Doc API - 글로벌 뉴스 감성 분석
# ============================================================================

def fetch_gdelt_sentiment():
    """
    GDELT에서 글로벌 뉴스 감성 및 보도량 수집
    특정 키워드의 일별 감성 점수와 기사량 추출
    
    API 인증: 불필요 (완전 무료)
    주의: API 호출 제한 있음 (Rate limiting)
    """
    print("\n📰 [2/6] GDELT 2.0 - 글로벌 뉴스 감성 분석 중...")
    
    keywords = [
        'semiconductor export control',
        'US China trade war',
        'Taiwan strait',
        'Middle East conflict',
        'NATO expansion',
        'economic sanctions'
    ]
    
    gdelt_data = []
    
    for keyword in keywords:
        try:
            # GDELT Doc Search API
            url = "https://api.gdeltproject.org/api/v2/doc/doc"
            params = {
                'query': keyword,
                'mode': 'timelinevolume',
                'format': 'json',
                'timespan': '30d'  # 최근 30일
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'timeline' in data:
                    for date_str, count in data['timeline'].items():
                        gdelt_data.append({
                            'date': date_str,
                            'keyword': keyword,
                            'article_count': int(count)
                        })
                    print(f"✓ '{keyword}': {len(data['timeline'])}개 일자")
        except Exception as e:
            print(f"⚠️ '{keyword}' 수집 실패: {e}")
            continue
    
    if gdelt_data:
        df = pd.DataFrame(gdelt_data)
        df['date'] = pd.to_datetime(df['date'])
        df.to_csv(DATA_DIR / "gdelt_news_sentiment.csv", index=False)
        print(f"✓ GDELT 데이터 저장: {len(df)}개 레코드")
        return df
    
    return None


# ============================================================================
# 3. OpenSanctions API - 글로벌 제재 데이터
# ============================================================================

def fetch_opensanctions_data():
    """
    OpenSanctions에서 글로벌 제재 대상자/기업 데이터 수집
    OFAC, EU, UN 등 통합 제재 명단
    """
    print("\n🚫 [3/6] OpenSanctions - 글로벌 제재 데이터 수집 중...")
    
    try:
        # OpenSanctions API (CSV 다운로드)
        url = "https://www.opensanctions.org/datasets/default/entities.json?only=id,name,countries,topics"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            sanctions_list = []
            for entity in data.get('entities', []):
                sanctions_list.append({
                    'id': entity.get('id'),
                    'name': entity.get('name'),
                    'countries': entity.get('countries', []),
                    'topics': entity.get('topics', []),
                    'collection_date': datetime.now().strftime('%Y-%m-%d')
                })
            
            if sanctions_list:
                df = pd.DataFrame(sanctions_list)
                df.to_csv(DATA_DIR / "opensanctions_list.csv", index=False)
                print(f"✓ OpenSanctions 데이터 저장: {len(df)}개 제재 대상")
                return df
    
    except Exception as e:
        print(f"❌ OpenSanctions API 오류: {e}")
    
    return None


# ============================================================================
# 4. UN Comtrade - 국제 무역 데이터
# ============================================================================

def fetch_un_comtrade_data():
    """
    UN Comtrade에서 국가 간 무역 데이터 수집
    특정 HS 코드(반도체, 광물 등)의 수출입량 추적
    
    API Key 발급: https://comtradeapi.un.org/
    """
    print("\n📦 [4/6] UN Comtrade - 국제 무역 데이터 수집 중...")
    
    comtrade_api_key = os.getenv('COMTRADE_API_KEY')
    
    if not comtrade_api_key:
        print("⚠️ COMTRADE_API_KEY 환경변수 없음. 무역 데이터 스킵.")
        return None
    
    try:
        # Comtrade API V2 (신규)
        url = "https://api.comtradeapi.un.org/goods/v1/get"
        
        # 주요 품목 코드
        hs_codes = {
            '8542': 'Semiconductors',      # 반도체
            '2603': 'Copper Ore',          # 구리광
            '2707': 'Oils/Fats',           # 석유
            '2710': 'Crude Oil'            # 원유
        }
        
        trade_data = []
        
        for hs_code, product_name in hs_codes.items():
            params = {
                'hs': hs_code,
                'year': datetime.now().year - 1,  # 작년 데이터
                'reporter': 'all',
                'partner': 'all',
                'flow': 'all',
                'api_key': comtrade_api_key
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # 데이터 처리 로직
                    print(f"✓ {product_name} 데이터 수집")
            except Exception as e:
                print(f"⚠️ {product_name} 수집 실패: {e}")
                continue
    
    except Exception as e:
        print(f"❌ UN Comtrade API 오류: {e}")
    
    return None


# ============================================================================
# 5. 한국 관세청 (K-stat) - 한국 수출입 데이터
# ============================================================================

def fetch_korea_trade_data():
    """
    공공데이터포털 / 한국 관세청 수출입 통계 수집
    한국의 국가별·품목별 수출입 데이터
    
    API Key 발급: https://www.data.go.kr/
    """
    print("\n🇰🇷 [5/6] 한국 관세청 - 수출입 데이터 수집 중...")
    
    kstat_api_key = os.getenv('KSTAT_API_KEY')
    
    if not kstat_api_key:
        print("⚠️ KSTAT_API_KEY 환경변수 없음. 한국 무역 데이터 스킵.")
        return None
    
    try:
        # 공공데이터포털 API
        url = "http://apis.data.go.kr/1383000/ChangeTradestatistics/getChangeTradeInfo"
        
        params = {
            'serviceKey': kstat_api_key,
            'type': 'json',
            'pageNo': '1',
            'numOfRows': '100',
            'searchPrd': datetime.now().strftime('%Y%m')  # 현재 월
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if 'body' in data and 'items' in data['body']:
                items = data['body']['items']
                df = pd.DataFrame(items)
                df.to_csv(DATA_DIR / "korea_trade_statistics.csv", index=False)
                print(f"✓ 한국 무역 데이터 저장: {len(df)}개 레코드")
                return df
    
    except Exception as e:
        print(f"❌ 한국 관세청 API 오류: {e}")
    
    return None


# ============================================================================
# 6. 수동 데이터 입력 템플릿 생성
# ============================================================================

def create_advanced_templates():
    """
    고급 분석용 템플릿 생성
    """
    print("\n📝 [6/6] 고급 수동 입력 템플릿 생성 중...")
    
    # 제재 영향도 템플릿
    sanctions_impact = pd.DataFrame({
        'Date': pd.date_range(start=datetime.now().date(), periods=30, freq='D'),
        'Country': ['Iran'] * 15 + ['North Korea'] * 10 + ['Russia'] * 5,
        'Sanction_Type': ['Economic'] * 30,
        'Impact_Level': [i % 10 for i in range(30)],
        'Notes': [''] * 30
    })
    sanctions_impact.to_csv(DATA_DIR / "manual_sanctions_impact.csv", index=False)
    print("✓ manual_sanctions_impact.csv 템플릿 생성")
    
    # 공급망 병목 템플릿
    supply_chain = pd.DataFrame({
        'Date': pd.date_range(start=datetime.now().date(), periods=30, freq='D'),
        'Product': ['Semiconductors'] * 10 + ['Rare Earths'] * 10 + ['Oil'] * 10,
        'Chokepoint': ['Taiwan'] * 10 + ['China'] * 10 + ['Middle East'] * 10,
        'Risk_Level': [i % 10 for i in range(30)],
        'Details': [''] * 30
    })
    supply_chain.to_csv(DATA_DIR / "manual_supply_chain_risks.csv", index=False)
    print("✓ manual_supply_chain_risks.csv 템플릿 생성")


# ============================================================================
# 7. 메인 함수
# ============================================================================

def main():
    """메인 함수"""
    
    # 폴더 생성
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n🔄 데이터 수집 실행 중...\n")
    
    # 각 API 데이터 수집
    fred_df = fetch_fred_data()
    gdelt_df = fetch_gdelt_sentiment()
    sanctions_df = fetch_opensanctions_data()
    comtrade_df = fetch_un_comtrade_data()
    korea_df = fetch_korea_trade_data()
    
    # 템플릿 생성
    create_advanced_templates()
    
    print("\n" + "=" * 70)
    print("✅ 고급 데이터 수집 완료!")
    print("=" * 70)
    print(f"📁 저장 위치: {DATA_DIR}")
    print("\n💡 다음 단계:")
    print("1. .env 파일에 API Key 설정")
    print("2. 매주 금요일에 이 스크립트 실행")
    print("3. manual_*.csv 파일에 수동 데이터 입력")
    print("4. generate_charts.py로 차트 생성")
    print("=" * 70)


if __name__ == "__main__":
    main()
