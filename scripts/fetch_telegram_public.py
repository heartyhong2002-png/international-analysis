"""
텔레그램 공개 채널(Public Web) OSINT 데이터 수집 프로토타입
- 계정 로그인이나 API 해킹 없이 100% 합법적인 공개 웹 뷰(t.me/s/...)를 스크래핑합니다.
- 저작권법 학술 연구 목적 공정 이용(Fair Use) 준수
"""

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent.parent / "data" / "signal_gap"
OUTPUT_FILE = DATA_DIR / "telegram_osint_latest.csv"

# 타겟 텔레그램 공개 채널 (OSINT 주요 소스)
TELEGRAM_CHANNELS = {
    "Russia_Rybar": "rybar",      # 러시아 최대 군사/지정학 블로거 (관영 매체와 다른 실제 전황 정보)
    "Ukraine_Live": "UaOnlii",    # 우크라이나 현지 속보 채널
    "Iran_IRGC_Proxy": "sepah_pasdaran", # 이란 혁명수비대 공식/준공식 채널 (sabereen 차단 대비)
    "Saudi_AlArabiya": "AlArabiya", # 사우디아라비아 국영 자본 대표 뉴스 (수니파 맹주 시각)
    "Yemen_Houthi": "army21ye" # 예멘 후티 반군 군사 대변인(야히야 사리) 공식 채널
}

def fetch_telegram_public():
    print("🕵️‍♂️ 텔레그램 공개 채널 OSINT 크롤링 시작 (API 불필요, 합법적 Web View)...")
    
    collected_data = []
    # 모바일이나 봇 차단을 피하기 위한 일반적인 브라우저 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    }

    for region, channel_id in TELEGRAM_CHANNELS.items():
        url = f"https://t.me/s/{channel_id}"
        print(f"\n[{region}] 채널 접속 중: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"  ⚠️ 채널 접속 실패 (HTTP {response.status_code})")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 텔레그램 웹 뷰의 메시지 텍스트를 담고 있는 HTML 클래스
            messages = soup.find_all('div', class_='tgme_widget_message_text')
            
            if not messages:
                print("  ⚠️ 메시지를 찾을 수 없습니다. 채널이 비공개로 전환되었거나 구조가 변경되었을 수 있습니다.")
                continue
            
            # 최신 메시지 5개만 추출 (하단에 있을수록 최신)
            recent_messages = messages[-5:]
            
            for idx, msg in enumerate(recent_messages):
                text_content = msg.get_text(separator=" ", strip=True)
                # 너무 짧은 이모티콘 메시지 등은 제외
                if len(text_content) > 10:
                    collected_data.append({
                        'Region': region,
                        'Channel_ID': channel_id,
                        'Message_Content': text_content,
                        'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            print(f"  ✓ {region} 채널에서 {len(recent_messages)}개의 최신 텍스트 수집 완료!")
            
        except Exception as e:
            print(f"  ❌ 에러 발생: {e}")

    if collected_data:
        df = pd.DataFrame(collected_data)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"\n✅ 텔레그램 OSINT 데이터 수집 완료! -> {OUTPUT_FILE}")
        return df
    else:
        print("\n⚠️ 수집된 데이터가 없습니다.")
        return None

if __name__ == "__main__":
    fetch_telegram_public()
