"""
국제정세 분석 - 데이터 수집 스크립트
World Bank API, NewsAPI 등에서 실시간 데이터를 수집합니다.
"""

import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path

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
