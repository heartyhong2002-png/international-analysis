"""
글로벌 금융사(IB) 및 신용평가사 리포트/인사이트 수집 프로토타입
- 글로벌 자본의 시각에서 거시경제 및 지정학(공급망) 리스크를 평가하기 위한 데이터 수집기
"""

import os
import requests
import feedparser
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).parent.parent / "data" / "signal_gap"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "global_ib_insights.csv"

# 타겟 금융사 리스트 (RSS 및 웹 크롤링)
IB_SOURCES = {
    "ING_Think": {
        "type": "rss",
        "url": "https://think.ing.com/rss",
        "desc": "네덜란드계 거대 금융사 ING의 거시경제/지정학 전문 리서치"
    },
    "Fitch_Ratings": {
        "type": "rss",
        "url": "https://www.fitchratings.com/site/rss/fitch-wire",
        "desc": "글로벌 3대 신용평가사 Fitch의 경제 코멘터리 (Fitch Wire)"
    },
    "S_and_P_Global": {
        "type": "rss",
        "url": "https://www.spglobal.com/en/research-insights/rss",
        "desc": "S&P Global 거시경제 및 리스크 인사이트"
    },
    "Nomura_Research": {
        "type": "html",
        "url": "https://www.nomuraconnects.com/",
        "desc": "일본 1위 증권사 노무라의 아시아/공급망 리서치"
    },
    "UBS_Insights": {
        "type": "html",
        "url": "https://www.ubs.com/global/en/wealth-management/insights.html",
        "desc": "스위스 최대 은행 UBS의 글로벌 자산관리 인사이트"
    }
}

def clean_text(html_text):
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def fetch_ib_insights():
    print("🏦 글로벌 투자은행(IB) 및 신용평가사 리서치 수집 시작...")
    
    collected_data = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    }

    for name, info in IB_SOURCES.items():
        print(f"\n[{name}] 데이터 접근 중... ({info['desc']})")
        
        try:
            response = requests.get(info['url'], headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"  ⚠️ 차단됨 또는 접근 불가 (HTTP {response.status_code}): {info['url']}")
                continue

            if info['type'] == 'rss':
                feed = feedparser.parse(response.content)
                entries = feed.entries[:5]  # 각 기관별 최신 리포트 5개
                
                if not entries:
                    print("  ⚠️ RSS 파싱 실패 또는 게시글 없음")
                    continue
                    
                for entry in entries:
                    collected_data.append({
                        'Institution': name,
                        'Title': entry.get('title', ''),
                        'Summary': clean_text(entry.get('summary', '')),
                        'Link': entry.get('link', ''),
                        'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                print(f"  ✓ {len(entries)}건의 리포트 요약본 수집 완료!")

            elif info['type'] == 'html':
                # 일반 웹페이지 HTML 파싱 (기사 제목과 링크 위주 추출)
                soup = BeautifulSoup(response.content, 'html.parser')
                # <a> 태그 중 제목처럼 보이는 텍스트가 20자 이상인 것을 추출 (프로토타입용 단순화 로직)
                links = soup.find_all('a', href=True)
                valid_links = [l for l in links if len(l.get_text(strip=True)) > 20][:5]
                
                if not valid_links:
                    print("  ⚠️ 페이지 내 리포트 제목을 찾을 수 없습니다.")
                    continue
                    
                for link in valid_links:
                    collected_data.append({
                        'Institution': name,
                        'Title': clean_text(link.get_text()),
                        'Summary': "웹 크롤링 데이터 (본문 확인 필요)",
                        'Link': link['href'] if link['href'].startswith('http') else "https://" + name.split('_')[0].lower() + ".com" + link['href'],
                        'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                print(f"  ✓ {len(valid_links)}건의 웹 기사 제목 수집 완료!")
                
        except Exception as e:
            print(f"  ❌ 크롤링 에러 발생: {e}")

    if collected_data:
        df = pd.DataFrame(collected_data)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"\n✅ 총 {len(df)}건의 IB 리포트 수집 완료! -> {OUTPUT_FILE}")
        return df
    else:
        print("\n⚠️ 수집된 데이터가 없습니다.")
        return None

if __name__ == "__main__":
    fetch_ib_insights()
