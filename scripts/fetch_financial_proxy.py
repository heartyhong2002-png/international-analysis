"""
권위주의 국가 금융 대체 지표(Financial Proxy) 수집 프로토타입
- 검열로 인해 텍스트(SNS) 여론 수집이 불가능한 경우, 금융 시장의 자본 흐름(주가, 환율)을 분석하여 '실제 대중의 경제 불안도'를 측정합니다.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent.parent / "data" / "signal_gap"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "financial_proxy_latest.csv"

# 수집할 금융 티커(Ticker) 설정
PROXY_ASSETS = {
    "China_Stock_CSI300_ETF": "ASHR",  # 중국 본토 증시 추종 ETF (000300.SS 대체, 경제 신뢰도)
    "USD_CNY_Exchange": "CNY=X",        # 달러 대비 위안화 환율 (자본 유출 및 화폐 가치 불신)
    "Safe_Haven_Gold": "GC=F"           # 금 선물 (안전자산 선호도 척도)
}

def fetch_financial_proxy():
    print("📈 검열 우회용 금융 대체 지표(Financial Proxy) 수집 시작...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # 최근 1개월 데이터 비교
    
    results = []
    
    for name, ticker in PROXY_ASSETS.items():
        print(f"  -> {name} ({ticker}) 데이터 다운로드 중...")
        try:
            data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
            
            if data.empty:
                print(f"     ⚠️ 데이터를 불러오지 못했습니다: {ticker}")
                continue
                
            # 'Close'가 MultiIndex 컬럼일 수 있으므로 안전하게 추출
            if isinstance(data.columns, pd.MultiIndex):
                close_prices = data['Close'][ticker]
            else:
                close_prices = data['Close']

            oldest_price = close_prices.iloc[0]
            latest_price = close_prices.iloc[-1]
            
            # 1개월 간의 변동률 계산
            change_pct = ((latest_price - oldest_price) / oldest_price) * 100
            
            # 리스크 평가 로직 (프로토타입 단순화)
            risk_signal = "안정적 (Stable)"
            if name == "China_Stock_CSI300_ETF" and change_pct < -5.0:
                risk_signal = "⚠️ 자본 이탈/경제 불신 심각 (주가 급락)"
            elif name == "USD_CNY_Exchange" and change_pct > 2.0:
                risk_signal = "⚠️ 화폐가치 하락/환율 급등 (자본 유출 징후)"
            elif name == "Safe_Haven_Gold" and change_pct > 5.0:
                risk_signal = "⚠️ 안전자산(금) 쏠림 심화 (내부 불안정)"
                
            results.append({
                "Asset_Name": name,
                "Ticker": ticker,
                "Price_1_Month_Ago": round(float(oldest_price), 2),
                "Price_Latest": round(float(latest_price), 2),
                "Monthly_Change_Percent": round(float(change_pct), 2),
                "Risk_Signal": risk_signal,
                "Updated_At": end_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            print(f"     ✓ 수집 성공 (변동률: {change_pct:.2f}%) -> {risk_signal}")
            
        except Exception as e:
            print(f"     ❌ 에러 발생 ({ticker}): {e}")

    if results:
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"\n✅ 금융 프록시 지표 분석 완료! -> {OUTPUT_FILE}")
        return df
    else:
        print("\n⚠️ 수집된 금융 데이터가 없습니다.")
        return None

if __name__ == "__main__":
    fetch_financial_proxy()
