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
    },
    "United_States_Policy_Tech": {
        "Official": [
            {
                "source_id": "us_state_dept_press",
                "url": "https://news.google.com/rss/search?q=site:state.gov+briefing+OR+statement&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "ally",
                "packet": "A",
                "license_access_note": "US State Department briefings and official statements."
            },
            {
                "source_id": "us_commerce_bis",
                "url": "https://news.google.com/rss/search?q=%22Bureau+of+Industry+and+Security%22+export+control+OR+%22Entity+List%22&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "ally",
                "packet": "A",
                "license_access_note": "US Commerce BIS export control updates on semiconductors & AI hardware."
            }
        ],
        "Independent": [
            {
                "source_id": "us_politico_congress",
                "url": "https://rss.politico.com/congress.xml",
                "relationship_role": "domestic_us",
                "packet": "B",
                "license_access_note": "Politico Congress RSS; US midterm elections, legislation, CHIPS Act scrutiny."
            },
            {
                "source_id": "us_thehill_tech",
                "url": "https://thehill.com/policy/technology/feed/",
                "relationship_role": "domestic_us",
                "packet": "B",
                "license_access_note": "The Hill Technology policy; tech espionage, AI regulation, and antitrust."
            },
            {
                "source_id": "us_csis_tech_semiconductors",
                "url": "https://news.google.com/rss/search?q=site:csis.org+%22semiconductor%22+OR+%22CHIPS%22+OR+%22NVIDIA%22&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "ally",
                "packet": "B",
                "license_access_note": "CSIS strategic technology research; export controls, NVIDIA & chip chokepoints."
            },
            {
                "source_id": "us_chips_supplychain_osint",
                "url": "https://news.google.com/rss/search?q=%22Jensen+Huang%22+OR+%22NVIDIA%22+export+control+OR+espionage&hl=en-US&gl=US&ceid=US:en",
                "relationship_role": "other",
                "packet": "B",
                "license_access_note": "Targeted Google News RSS on NVIDIA CEO Jensen Huang, export control compliance & security rumors."
            }
        ]
    }
}


# clean_html defined above with fallback

_NOISE_MEDIA_URL_RE = re.compile(
    r"(/|_|-)(avatar|emoji|favicon|icon|logo|banner|pixel|spacer|sprite|badge|button)s?(/|_|-|\.)"
    r"|\b1x1\b|\.svg(\?|$)|^data:image/|giphy\.com|tenor\.com|9gag\.com"
    r"|doubleclick\.net|googlesyndication\.com|googleadservices\.com|gravatar\.com|lh3\.googleusercontent\.com/J6_coFbogxhRI9iM864NL_liGXvsQp2AupsKei7z0cNNfDvGUmWUy20nuUhkREQyrpY4bEeIBuc",
    re.IGNORECASE,
)
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_VID_TAG_RE = re.compile(r"<(?:video|source|iframe)\b[^>]*>", re.IGNORECASE)
_SRC_ATTR_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
_ALT_ATTR_RE = re.compile(r'\balt=["\']([^"\']+)["\']', re.IGNORECASE)
_PDF_URL_RE = re.compile(r'https?://[^\s"\'<>]+\.pdf(?:\?[^\s"\'<>]*)?', re.IGNORECASE)


def is_clean_rss_media_url(url: str) -> bool:
    u = (url or "").strip()
    if not u or len(u) < 10 or not u.startswith(("http://", "https://")):
        return False
    if _NOISE_MEDIA_URL_RE.search(u):
        return False
    return True


def extract_entry_multimodal(entry, title: str, raw_summary: str) -> dict:
    """
    0-Byte 무다운로드 원칙에 따라 RSS entry의 <media:content>, <media:thumbnail>,
    <enclosure>, 그리고 본문 HTML 내 <img>/<video>/PDF 링크와 alt_text를 추출한다.
    아바타, 로고, 1x1 트래킹 픽셀, 이모지 아이콘은 즉시 배제한다.
    """
    media_urls: list[str] = []
    video_urls: list[str] = []
    pdf_urls: list[str] = []
    alt_texts: list[str] = []

    def _register_url(u: str, m_kind: str = "image", alt: str = "") -> None:
        u_clean = (u or "").strip()
        if not is_clean_rss_media_url(u_clean):
            return
        u_lower = u_clean.lower().split("?")[0]
        if u_lower.endswith(".pdf") or m_kind == "pdf":
            if u_clean not in pdf_urls:
                pdf_urls.append(u_clean)
        elif u_lower.endswith((".mp4", ".webm", ".mov", ".m3u8")) or m_kind == "video":
            if u_clean not in video_urls:
                video_urls.append(u_clean)
        else:
            if u_clean not in media_urls:
                media_urls.append(u_clean)
        alt_clean = clean_html(alt).strip()
        if alt_clean and len(alt_clean) >= 4 and alt_clean not in alt_texts:
            alt_texts.append(alt_clean[:240])

    # 1. <media:content>
    for mc in entry.get("media_content", []) or []:
        if isinstance(mc, dict):
            m_url = mc.get("url") or ""
            m_type = str(mc.get("type") or mc.get("medium") or "").lower()
            kind = "video" if "video" in m_type else ("pdf" if "pdf" in m_type else "image")
            _register_url(m_url, kind, str(mc.get("title") or ""))

    # 2. <media:thumbnail>
    for mt in entry.get("media_thumbnail", []) or []:
        if isinstance(mt, dict):
            _register_url(mt.get("url") or "", "image", "")

    # 3. <enclosure> 및 links
    for enc in entry.get("enclosures", []) or []:
        if isinstance(enc, dict):
            e_url = enc.get("href") or enc.get("url") or ""
            e_type = str(enc.get("type") or "").lower()
            if "audio" in e_type:
                continue
            kind = "video" if "video" in e_type else ("pdf" if "pdf" in e_type else "image")
            _register_url(e_url, kind, "")

    for lnk in entry.get("links", []) or []:
        if isinstance(lnk, dict):
            l_href = str(lnk.get("href") or "").strip()
            l_rel = str(lnk.get("rel") or "").lower()
            l_type = str(lnk.get("type") or "").lower()
            if l_href.lower().split("?")[0].endswith(".pdf") or "pdf" in l_type:
                _register_url(l_href, "pdf", str(lnk.get("title") or "Official Document PDF"))
            elif l_rel == "enclosure" and "audio" not in l_type:
                kind = "video" if "video" in l_type else "image"
                _register_url(l_href, kind, str(lnk.get("title") or ""))

    # 4. Raw HTML (summary + content 블록) 스캔
    content_html = ""
    for c_item in entry.get("content", []) or []:
        if isinstance(c_item, dict):
            content_html += " " + str(c_item.get("value") or "")
    combined_html = f"{raw_summary} {content_html}"

    for img_tag in _IMG_TAG_RE.findall(combined_html):
        src_m = _SRC_ATTR_RE.search(img_tag)
        alt_m = _ALT_ATTR_RE.search(img_tag)
        if src_m:
            _register_url(src_m.group(1), "image", alt_m.group(1) if alt_m else "")

    for vid_tag in _VID_TAG_RE.findall(combined_html):
        src_m = _SRC_ATTR_RE.search(vid_tag)
        if src_m:
            _register_url(src_m.group(1), "video", "")

    for pdf_u in _PDF_URL_RE.findall(combined_html):
        _register_url(pdf_u, "pdf", "Official Document PDF")

    primary_media = media_urls[0] if media_urls else ""
    primary_video = video_urls[0] if video_urls else ""
    primary_pdf = pdf_urls[0] if pdf_urls else ""
    primary_alt = " | ".join(alt_texts)[:240]
    has_media = bool(primary_media or primary_video or primary_pdf)

    # 전처리 브릿지(bridge_preprocess_lanes.py)가 Summary 컬럼에서 멀티모달 태그를
    # 유실 없이 파싱할 수 있도록 정제된 요약문 끝에 보존용 멀티모달 태그 스니펫 부착
    preserved_tags: list[str] = []
    if primary_media:
        safe_alt = (alt_texts[0] if alt_texts else clean_html(title)[:120]).replace('"', "'")
        preserved_tags.append(f'<img src="{primary_media}" alt="{safe_alt}">')
    if primary_video:
        preserved_tags.append(f'<video src="{primary_video}"></video>')
    if primary_pdf:
        preserved_tags.append(primary_pdf)

    return {
        "media_url": primary_media,
        "video_url": primary_video,
        "pdf_url": primary_pdf,
        "alt_text": primary_alt,
        "has_media": has_media,
        "preserved_snippet": " ".join(preserved_tags),
    }


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

                    feed_media_count = 0
                    for entry in entries:
                        pub_date = entry.get('published', '')
                        link = entry.get('link', '')
                        title = entry.get('title', '')
                        raw_summary = entry.get('summary', '')
                        cleaned_summary = clean_html(raw_summary)[:500]
                        mm = extract_entry_multimodal(entry, title, raw_summary)
                        if mm["has_media"]:
                            feed_media_count += 1
                        summary_with_media = (
                            f"{cleaned_summary} {mm['preserved_snippet']}".strip()
                            if mm["preserved_snippet"]
                            else cleaned_summary
                        )
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
                            'Summary': summary_with_media,
                            'Link': link,
                            'Media_URL': mm["media_url"],
                            'Video_URL': mm["video_url"],
                            'PDF_URL': mm["pdf_url"],
                            'Alt_Text': mm["alt_text"],
                            'Has_Media': mm["has_media"],
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
                        "media_items_collected": feed_media_count,
                        "license_access_note": license_note,
                    })
                    print(f"     ✓ {len(entries)}개 기사 수집 성공 (멀티모달 첨부: {feed_media_count}건)")

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
