"""
신호 괴리율(Signal Gap) 분석을 위한 3자 교차 검증 RSS 수집기 (Packet C 연동)
- 관영 매체(공식 서사)와 망명/독립 언론 간의 논조 차이를 분석하기 위한 원시 텍스트 수집.
- config/source_registry/ (government_sources.yaml, local_media_feeds.yaml)의
  source_id, relationship_role(competitor_adversary_axis / other), packet(C / legacy) 및
  수집 영수증(receipt_latest.json)을 함께 보존한다.
- 이 수집기는 원시 센서 데이터만 저장하며 Alert Level이나 verification_state를 판정하지 않는다.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import feedparser
from bs4 import BeautifulSoup
import pandas as pd
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 폴더 설정
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "signal_gap"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 4대 핵심 권역 크롤링 타겟 (관영 매체 vs 망명/독립 언론) — source_registry Packet C 정렬
RSS_FEEDS = {
    "Russia": {
        "Official": [
            {
                "source_id": "ru_tass_en_rss",
                "url": "https://tass.com/rss/v2.xml",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "TASS public RSS; Russian state media narrative layer, never ground truth."
            }
        ],
        "Independent": [
            {
                "source_id": "ru_meduza_rss",
                "url": "https://meduza.io/rss/all",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "Meduza public RSS; independent Russian-language exiled media."
            }
        ]
    },
    "China": {
        "Official": [
            {
                "source_id": "cn_people_daily_world_rss",
                "url": "http://en.people.cn/rss/World.xml",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "People's Daily English World RSS; Chinese state media narrative layer."
            }
        ],
        "Independent": [
            {
                "source_id": "cn_china_digital_times_rss",
                "url": "https://chinadigitaltimes.net/chinese/feed/",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "China Digital Times Chinese feed; independent censorship-archive aggregator."
            }
        ]
    },
    "Middle_East": {
        "Official": [
            {
                "source_id": "ir_tehran_times_rss",
                "url": "https://www.tehrantimes.com/rss",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "Tehran Times public RSS; Iranian state-aligned narrative layer."
            }
        ],
        "Independent": [
            {
                "source_id": "me_raseef22_rss",
                "url": "https://raseef22.net/feed/",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "Raseef22 Arabic public RSS; independent pan-Arab media network."
            }
        ]
    },
    "Global_South": {
        "Official": [],  # Global South는 특정 국가의 관영보다는 다극화/비서방 대척점 역할
        "Independent": [
            {
                "source_id": "al_jazeera_all",
                "url": "https://www.aljazeera.com/xml/rss/all.xml",
                "relationship_role": "other",
                "packet": "legacy",
                "license_access_note": "Public Al Jazeera RSS; Qatari state-affiliated broadcaster."
            }
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
    print("📡 글로벌 신호 괴리율(Signal Gap) RSS 데이터 수집 시작 (Packet C 레지스트리 연동)...")

    collected_data = []
    source_receipts = []
    observed_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for region, source_types in RSS_FEEDS.items():
        print(f"\n[{region}] 권역 수집 중...")

        for source_type, feeds in source_types.items():
            for feed_meta in feeds:
                if isinstance(feed_meta, str):
                    url = feed_meta
                    source_id = "legacy_signal_gap_feed"
                    relationship_role = "competitor_adversary_axis" if region != "Global_South" else "other"
                    packet = "C" if region != "Global_South" else "legacy"
                    license_note = "Public RSS feed."
                else:
                    url = feed_meta["url"]
                    source_id = feed_meta["source_id"]
                    relationship_role = feed_meta["relationship_role"]
                    packet = feed_meta["packet"]
                    license_note = feed_meta["license_access_note"]

                print(f"  -> {source_type} 매체 접근 중 [{source_id} / {relationship_role}]: {url}")
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response = requests.get(url, headers=headers, timeout=10)

                    if response.status_code != 200:
                        print(f"     ⚠️ 서버 응답 에러 ({response.status_code}): {url}")
                        source_receipts.append({
                            "source_id": source_id,
                            "region": region,
                            "source_type": source_type,
                            "relationship_role": relationship_role,
                            "packet": packet,
                            "source_url": url,
                            "observed_at": observed_at_utc,
                            "http_status": response.status_code,
                            "parse_status": "BLOCKED" if response.status_code in (401, 403) else "PARSE_ERROR",
                            "items_collected": 0,
                            "license_access_note": license_note,
                        })
                        continue

                    feed = feedparser.parse(response.content)
                    entries = feed.entries[:10]

                    if not entries:
                        print("     ⚠️ 기사가 없습니다. (RSS 형식이 아니거나 차단되었을 수 있음)")
                        source_receipts.append({
                            "source_id": source_id,
                            "region": region,
                            "source_type": source_type,
                            "relationship_role": relationship_role,
                            "packet": packet,
                            "source_url": url,
                            "observed_at": observed_at_utc,
                            "http_status": response.status_code,
                            "parse_status": "PARSE_ERROR",
                            "items_collected": 0,
                            "license_access_note": license_note,
                        })
                        continue

                    for entry in entries:
                        pub_date = entry.get('published', '')
                        link = entry.get('link', '')
                        title = entry.get('title', '')
                        summary = clean_html(entry.get('summary', ''))
                        content_hash = hashlib.sha256(
                            f"{source_id}|{link}|{title}".encode("utf-8", errors="ignore")
                        ).hexdigest()[:16]

                        collected_data.append({
                            'Region': region,
                            'Source_Type': source_type,
                            'Source_ID': source_id,
                            'Relationship_Role': relationship_role,
                            'Packet': packet,
                            'Feed_URL': url,
                            'Title': title,
                            'Summary': summary,
                            'Link': link,
                            'Published_Date': pub_date,
                            'Scraped_At': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'Observed_At_UTC': observed_at_utc,
                            'Content_Hash': content_hash,
                            'License_Access_Note': license_note,
                        })

                    source_receipts.append({
                        "source_id": source_id,
                        "region": region,
                        "source_type": source_type,
                        "relationship_role": relationship_role,
                        "packet": packet,
                        "source_url": url,
                        "observed_at": observed_at_utc,
                        "http_status": response.status_code,
                        "parse_status": "SUCCESS",
                        "items_collected": len(entries),
                        "license_access_note": license_note,
                    })
                    print(f"     ✓ {len(entries)}개 기사 수집 성공")

                except requests.exceptions.Timeout as e:
                    print(f"     ❌ 타임아웃 ({url}): {e}")
                    source_receipts.append({
                        "source_id": source_id,
                        "region": region,
                        "source_type": source_type,
                        "relationship_role": relationship_role,
                        "packet": packet,
                        "source_url": url,
                        "observed_at": observed_at_utc,
                        "http_status": None,
                        "parse_status": "TIMEOUT",
                        "items_collected": 0,
                        "error": str(e)[:160],
                        "license_access_note": license_note,
                    })
                except Exception as e:
                    print(f"     ❌ 수집 실패 ({url}): {e}")
                    source_receipts.append({
                        "source_id": source_id,
                        "region": region,
                        "source_type": source_type,
                        "relationship_role": relationship_role,
                        "packet": packet,
                        "source_url": url,
                        "observed_at": observed_at_utc,
                        "http_status": None,
                        "parse_status": "TIMEOUT" if "timed out" in str(e).lower() else "PARSE_ERROR",
                        "items_collected": 0,
                        "error": str(e)[:160],
                        "license_access_note": license_note,
                    })

    receipt_path = DATA_DIR / "receipt_latest.json"
    receipt_payload = {
        "collector": "scripts/collection/fetch_signal_gap_rss.py",
        "observed_at": observed_at_utc,
        "packet": "C",
        "alert_level_set": False,
        "verification_state_set": False,
        "total_items_collected": len(collected_data),
        "sources": source_receipts,
    }
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt_payload, f, ensure_ascii=False, indent=2)
    print(f"\n🧾 수집 영수증 저장: {receipt_path}")

    if collected_data:
        df = pd.DataFrame(collected_data)
        file_path = DATA_DIR / "rss_signal_gap_latest.csv"
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"✅ 총 {len(df)}건의 기사 수집 완료! -> {file_path}")
        return df
    else:
        print("\n⚠️ 수집된 데이터가 없습니다.")
        return None


if __name__ == "__main__":
    fetch_rss_data()
