"""
신호 괴리율(Signal Gap) 분석을 위한 3자 교차 검증 RSS 수집기
- 관영 매체(선전)와 망명/독립 언론 간의 논조 차이를 분석하기 위한 텍스트 수집.
"""

import os
import json
from datetime import datetime
from pathlib import Path
import feedparser
from bs4 import BeautifulSoup
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 폴더 설정
DATA_DIR = Path(__file__).parent.parent / "data" / "signal_gap"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 4대 핵심 권역 크롤링 타겟 (관영 매체 vs 망명/독립 언론)
RSS_FEEDS = {
    "Russia": {
        "Official": [
            # TASS (러시아 관영)
            "https://tass.com/rss/v2.xml"
        ],
        "Independent": [
            # Meduza (망명 독립 언론) - handoff 문서 기준
            "https://meduza.io/rss/all"
        ]
    },
    "China": {
        "Official": [
            # 신화통신 / 인민일보 (관영)
            "http://en.people.cn/rss/World.xml"
        ],
        "Independent": [
            # China Digital Times (검열 아카이브) - handoff 문서 기준
            "https://chinadigitaltimes.net/chinese/feed/"
        ]
    },
    "Middle_East": {
        "Official": [
            # Tehran Times (이란 관영)
            "https://www.tehrantimes.com/rss"
        ],
        "Independent": [
            # Iran International 대신 작동이 확인된 Raseef22 사용 (독립 언론)
            "https://raseef22.net/feed/"
        ]
    },
    "Global_South": {
        "Official": [], # Global South는 특정 국가의 관영보다는 서방과의 대척점 역할
        "Independent": [
            # Al Jazeera (알자지라)
            "https://www.aljazeera.com/xml/rss/all.xml"
        ]
    }
}

def clean_html(raw_html):
    """HTML 태그 제거 및 텍스트 정제"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def fetch_rss_data():
    print("📡 글로벌 신호 괴리율(Signal Gap) RSS 데이터 수집 시작...")
    
    collected_data = []
    
    for region, source_types in RSS_FEEDS.items():
        print(f"\n[{region}] 권역 수집 중...")
        
        for source_type, urls in source_types.items():
            for url in urls:
                print(f"  -> {source_type} 매체 접근 중: {url}")
                try:
                    # 일부 언론사(방화벽/Cloudflare) 차단을 막기 위해 requests로 User-Agent 추가하여 호출
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    import requests
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code != 200:
                        print(f"     ⚠️ 서버 응답 에러 ({response.status_code}): {url}")
                        continue
                        
                    # raw xml을 feedparser로 파싱
                    feed = feedparser.parse(response.content)
                    
                    entries = feed.entries[:10]  # 최신 10개만 수집
                    
                    if not entries:
                        print("     ⚠️ 기사가 없습니다. (RSS 형식이 아니거나 차단되었을 수 있음)")
                        continue
                        
                    for entry in entries:
                        # 날짜 파싱 (피드마다 형식이 다를 수 있음)
                        pub_date = entry.get('published', '')
                        
                        collected_data.append({
                            'Region': region,
                            'Source_Type': source_type,
                            'Feed_URL': url,
                            'Title': entry.get('title', ''),
                            'Summary': clean_html(entry.get('summary', '')),
                            'Link': entry.get('link', ''),
                            'Published_Date': pub_date,
                            'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    
                    print(f"     ✓ {len(entries)}개 기사 수집 성공")
                    
                except Exception as e:
                    print(f"     ❌ 수집 실패 ({url}): {e}")

    if collected_data:
        df = pd.DataFrame(collected_data)
        file_path = DATA_DIR / "rss_signal_gap_latest.csv"
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 총 {len(df)}건의 기사 수집 완료! -> {file_path}")
        return df
    else:
        print("\n⚠️ 수집된 데이터가 없습니다.")
        return None

if __name__ == "__main__":
    fetch_rss_data()
