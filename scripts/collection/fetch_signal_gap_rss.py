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
import csv
import requests
import sys
import re

try:
    from bs4 import BeautifulSoup
    def clean_html(raw_html):
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text(separator=" ", strip=True)
except ImportError:
    def clean_html(raw_html):
        if not raw_html:
            return ""
        clean = re.sub(r"<[^>]+>", " ", raw_html)
        return " ".join(clean.split())

sys.stdout.reconfigure(encoding='utf-8')

# 폴더 설정
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "signal_gap"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 6대 핵심 권역 크롤링 타겟 (관영 매체 vs 망명/독립 언론 & 특화 싱크탱크) — source_registry 정렬
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
            },
            {
                "source_id": "ru_istories_rss",
                "url": "https://istories.media/rss/all.xml",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "iStories public RSS; exiled investigative outlet tracking military smuggling."
            },
            {
                "source_id": "ru_insider_rss",
                "url": "https://news.google.com/rss/search?q=site:theins.ru&hl=ru&gl=RU&ceid=RU:ru",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "The Insider Russia public RSS; tracking intelligence operations & hybrid warfare."
            },
            {
                "source_id": "bellingcat_rss",
                "url": "https://www.bellingcat.com/feed/",
                "relationship_role": "other",
                "packet": "C",
                "license_access_note": "Bellingcat public RSS; open-source intelligence and investigative journalism."
            },
            {
                "source_id": "carnegie_russia_eurasia",
                "url": "https://news.google.com/rss/search?q=site:carnegieendowment.org+Russia&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "Carnegie Russia Eurasia Center public RSS (Berlin); independent expert scholarship."
            },
            {
                "source_id": "isw_war_studies",
                "url": "https://news.google.com/rss/search?q=site:understandingwar.org&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "ISW Russian Campaign & Conflict Assessments via Google News targeted RSS."
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
                "source_id": "cn_rfa_rss",
                "url": "https://www.rfa.org/english/RSS",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "Radio Free Asia public RSS; covers Xinjiang, South China Sea, and Chinese censorship."
            },
            {
                "source_id": "csis_global",
                "url": "https://www.csis.org/rss.xml",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "CSIS public RSS; non-partisan security think tank; South China Sea & Taiwan Strait."
            },
            {
                "source_id": "aspi_strategist",
                "url": "https://www.aspistrategist.org.au/feed/",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "ASPI Strategist public RSS; Australian strategic & cyber policy analysis on China."
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
            },
            {
                "source_id": "me_iranwire_rss",
                "url": "https://iranwire.com/en/feed/",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "IranWire public RSS; exiled Iranian journalists and citizen reporter network."
            },
            {
                "source_id": "me_middle_east_eye_rss",
                "url": "https://www.middleeasteye.net/rss",
                "relationship_role": "other",
                "packet": "C",
                "license_access_note": "Middle East Eye public RSS; London-based independent Middle East news outlet."
            }
        ]
    },
    "Latin_America_Mexico": {
        "Official": [],
        "Independent": [
            {
                "source_id": "mx_el_universal_rss",
                "url": "https://www.eluniversal.com.mx/arc/outboundfeeds/rss/?outputType=xml",
                "relationship_role": "other",
                "packet": "B",
                "license_access_note": "El Universal public RSS; major Mexican national daily."
            },
            {
                "source_id": "mx_animal_politico_rss",
                "url": "https://news.google.com/rss/search?q=site:animalpolitico.com&hl=es-419&gl=MX&ceid=MX:es-419",
                "relationship_role": "other",
                "packet": "B",
                "license_access_note": "Animal Político via Google News targeted RSS; premier Mexican investigative outlet."
            },
            {
                "source_id": "wilson_center_mexico",
                "url": "https://news.google.com/rss/search?q=site:wilsoncenter.org&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "Wilson Center Mexico Institute & Latin America via Google News targeted RSS."
            },
            {
                "source_id": "wola_latin_america",
                "url": "https://news.google.com/rss/search?q=site:wola.org&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "other",
                "packet": "B",
                "license_access_note": "WOLA Latin America human rights, cartels, border via Google News targeted RSS."
            },
            {
                "source_id": "ar_clarin_rss",
                "url": "https://www.clarin.com/rss/lo-ultimo/",
                "relationship_role": "other",
                "packet": "B",
                "license_access_note": "Clarín public RSS; major Argentine daily covering Milei administration."
            },
            {
                "source_id": "ar_pagina12_rss",
                "url": "https://news.google.com/rss/search?q=site:pagina12.com.ar&hl=es-419&gl=AR&ceid=AR:es-419",
                "relationship_role": "other",
                "packet": "B",
                "license_access_note": "Página/12 via Google News targeted RSS; Argentine progressive daily."
            },
            {
                "source_id": "br_agencia_publica_rss",
                "url": "https://apublica.org/feed/",
                "relationship_role": "other",
                "packet": "B",
                "license_access_note": "Agência Pública public RSS; Brazilian non-profit investigative journalism."
            },
            {
                "source_id": "ve_armando_info_rss",
                "url": "https://armando.info/feed/",
                "relationship_role": "competitor_adversary_axis",
                "packet": "C",
                "license_access_note": "Armando.info public RSS; Venezuelan exiled investigative journalism."
            },
            {
                "source_id": "inter_american_dialogue",
                "url": "https://www.thedialogue.org/feed/",
                "relationship_role": "other",
                "packet": "B",
                "license_access_note": "Inter-American Dialogue public RSS; Latin America governance & lithium supply chains."
            }
        ]
    },
    "Japan_EastAsia": {
        "Official": [],
        "Independent": [
            {
                "source_id": "jp_mainichi_rss",
                "url": "https://news.google.com/rss/search?q=site:mainichi.jp&hl=ja&gl=JP&ceid=JP:ja",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "Mainichi Shimbun English public RSS; Japanese daily covering LDP politics & defense."
            },
            {
                "source_id": "jp_asahi_rss",
                "url": "https://rss.asahi.com/rss/asahi/newsheadlines.rdf",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "Asahi Shimbun Japanese headlines public RSS; liberal perspective on parliament."
            },
            {
                "source_id": "jp_japan_times_rss",
                "url": "https://www.japantimes.co.jp/feed/",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "The Japan Times public RSS; independent English daily covering Japanese policy."
            },
            {
                "source_id": "jp_bunshun_rss",
                "url": "https://news.google.com/rss/search?q=site:bunshun.jp&hl=ja&gl=JP&ceid=JP:ja",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "Bunshun Online via Google News targeted RSS; political funding & scandal watchdog."
            },
            {
                "source_id": "tokyo_foundation",
                "url": "https://news.google.com/rss/search?q=site:tkfd.or.jp&hl=ja&gl=JP&ceid=JP:ja",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "Tokyo Foundation for Policy Research via Google News targeted RSS."
            }
        ]
    },
    "Global_Trade_Investigative": {
        "Official": [],
        "Independent": [
            {
                "source_id": "global_occrp_rss",
                "url": "https://www.occrp.org/en/feed",
                "relationship_role": "other",
                "packet": "C",
                "license_access_note": "OCCRP public RSS; global reporting on organized crime, shell companies & sanctions."
            },
            {
                "source_id": "us_propublica_rss",
                "url": "https://feeds.propublica.org/propublica/main",
                "relationship_role": "domestic_us",
                "packet": "B",
                "license_access_note": "ProPublica public RSS; non-profit investigative journalism."
            },
            {
                "source_id": "piie_trade_policy",
                "url": "https://news.google.com/rss/search?q=site:piie.com&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "PIIE international economics and tariff/trade policy via Google News targeted RSS."
            },
            {
                "source_id": "rusi_military",
                "url": "https://news.google.com/rss/search?q=site:rusi.org&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "RUSI defense & military analysis via Google News targeted RSS."
            },
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


# clean_html defined above with fallback


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
        file_path = DATA_DIR / "rss_signal_gap_latest.csv"
        fieldnames = list(collected_data[0].keys())
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(collected_data)
        print(f"✅ 총 {len(collected_data)}건의 기사 수집 완료! -> {file_path}")
        return collected_data
    else:
        print("\n⚠️ 수집된 데이터가 없습니다.")
        return None


if __name__ == "__main__":
    fetch_rss_data()
