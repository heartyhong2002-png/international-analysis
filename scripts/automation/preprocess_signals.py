"""
preprocess_signals.py
=====================
무인 글로벌 이상 징후 탐지를 위한 지능형 4단계 전처리 파이프라인.
1. 노이즈 필터링 (연예·스포츠·상업 광고 배제 및 지정학 연관도 필터링)
2. 시맨틱 중복 제거 및 클러스터링 (동일 사건 다수 언론사 보도 압축)
3. 지정학·공급망 엔티티 정규화 (다국어 해협·지명 표준화 및 한국 핵심 공급망 품목 태깅)
4. 경량 구조화 및 신호 패키징 (로컬 16GB RAM 최적화)
"""

from __future__ import annotations

import re
import html
from typing import Any, Dict, List, Set, Tuple


# ======================================================================
# 1. 노이즈 필터링 사전 및 정규식
# ======================================================================

# 비지정학/단순 오락/상업 광고 블랙리스트 단어
NOISE_KEYWORDS = {
    # 연예/오락/가십
    "celebrity", "hollywood", "kardashian", "box office", "trailer", "premiere",
    "red carpet", "oscar", "grammy", "emmy", "singer", "album", "pop star",
    "dating", "romance", "wedding", "divorce", "fashion week", "horoscope",
    "zodiac", "lifestyle", "beauty pageant", "miss universe", "influencer",
    # 스포츠
    "football", "soccer", "champions league", "premier league", "laliga",
    "world cup", "nba", "basketball", "baseball", "mlb", "nfl", "super bowl",
    "tennis", "wimbledon", "formula 1", "f1 grand prix", "olympics medal",
    "fifa", "scoreline", "half-time", "touchdown", "hat-trick",
    # 단순 상업/스팸/금융 프로모션
    "giveaway", "lottery", "jackpot", "crypto airdrop", "meme coin",
    "black friday discount", "promo code", "weight loss", "diet supplement"
}

# 지정학/안보/공급망 화이트리스트 핵심 키워드
GEOPOLITICAL_KEYWORDS = {
    "military", "navy", "naval", "army", "air force", "missile", "drone", "strike",
    "attack", "explosion", "blockade", "chokepoint", "strait", "vessel", "ship",
    "tanker", "cargo", "freight", "port", "terminal", "oil", "gas", "lng", "crude",
    "pipeline", "sanction", "export control", "embargo", "tariff", "trade war",
    "semiconductor", "rare earths", "uranium", "nuclear", "warhead", "defense",
    "conflict", "tensions", "ceasefire", "treaty", "sovereignty", "territory",
    "drills", "exercise", "patrol", "intercept", "casualty", "airspace", "hostage",
    "piracy", "insurgent", "houthi", "irgc", "hezbollah", "hamas", "taiwan strait"
}

NOISE_DOMAINS = {
    "tmz.com", "eonline.com", "variety.com", "hollywoodreporter.com",
    "espn.com", "goal.com", "bleacherreport.com", "marca.com",
    "fashionunited.com", "vogue.com", "cosmopolitan.com"
}


def is_noise(title: str, url: str = "", source: str = "") -> bool:
    """ 연예, 스포츠, 광고 등 노이즈 기사 여부를 판별합니다. """
    text_lower = f"{title} {source}".lower()
    
    # 1. 노이즈 도메인 검사
    url_lower = url.lower()
    for domain in NOISE_DOMAINS:
        if domain in url_lower:
            return True

    # 2. 노이즈 키워드 매칭
    noise_count = sum(1 for kw in NOISE_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))
    geo_count = sum(1 for kw in GEOPOLITICAL_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))

    # 노이즈 단어가 존재하고 지정학 단어보다 압도적으로 많으면 배제
    if noise_count > 0 and geo_count == 0:
        return True
    if noise_count >= 2 and geo_count <= 1:
        return True

    return False


def calculate_relevance(title: str) -> float:
    """ 지정학 및 글로벌 공급망 관련도 점수를 0.0~1.0 사이로 계산합니다. """
    text_lower = title.lower()
    matches = sum(1 for kw in GEOPOLITICAL_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))
    # 4개 이상 매칭 시 최대 1.0
    return min(1.0, round(matches / 4.0, 2))


# ======================================================================
# 2. 지정학 및 공급망 엔티티 정규화
# ======================================================================

# 4대 핵심 해협 및 다국어 매핑
CHOKEPOINT_MAPPINGS = {
    "CHOKEPOINT_HORMUZ": {
        "standard_name": "호르무즈 해협 (Strait of Hormuz)",
        "patterns": [
            r"hormuz", r"strait of hormuz", r"مضيق هرمز", r"تنگه هرمز",
            r"ホルムズ", r"霍尔木兹", r"호르무즈"
        ],
        "primary_supply": ["CRUDE_OIL", "NATURAL_GAS_LNG", "NAPHTHA"],
        "region": "Middle East / Persian Gulf"
    },
    "CHOKEPOINT_BAB_EL_MANDEB": {
        "standard_name": "바브엘만데브 해협 및 홍해 (Bab-el-Mandeb & Red Sea)",
        "patterns": [
            r"bab[- ]el[- ]mandeb", r"bab al-mandab", r"red sea", r"مضيق باب المندب",
            r"البحر الأحمر", r"홍해", r"바브엘만데브", r"红海", r"曼德海峡"
        ],
        "primary_supply": ["CONTAINER_CARGO", "CRUDE_OIL", "EUROPE_EXPORT"],
        "region": "Middle East / Red Sea"
    },
    "CHOKEPOINT_MALACCA": {
        "standard_name": "말라카 해협 (Strait of Malacca)",
        "patterns": [
            r"malacca", r"strait of malacca", r"selat melaka", r"مضيق ملقا",
            r"말라카", r"马六甲", r"マラッカ"
        ],
        "primary_supply": ["CRUDE_OIL", "CONTAINER_CARGO", "COAL"],
        "region": "Southeast Asia"
    },
    "CHOKEPOINT_BOSPHORUS": {
        "standard_name": "보스포루스 및 흑해 해협 (Bosphorus & Turkish Straits)",
        "patterns": [
            r"bosphorus", r"bosporus", r"dardanelles", r"turkish straits",
            r"istanbul bo[gğ]az[ıi]", r"보스포루스", r"다르다넬스", r"흑해 해협",
            r"black sea straits", r"博斯普鲁斯"
        ],
        "primary_supply": ["GRAIN_WHEAT", "CRUDE_OIL", "FERTILIZER"],
        "region": "Eurasia / Black Sea"
    },
    "CHOKEPOINT_TAIWAN_STRAIT": {
        "standard_name": "대만 해협 (Taiwan Strait)",
        "patterns": [
            r"taiwan strait", r"strait of taiwan", r"대만해협", r"대만 해협",
            r"台湾海峡", r"臺灣海峽", r"台湾海峡"
        ],
        "primary_supply": ["SEMICONDUCTOR", "ELECTRONICS", "EAST_ASIA_SHIPPING"],
        "region": "East Asia"
    }
}

# 한국 핵심 공급망 품목(Critical Supply Chain Items) 키워드 매핑
SUPPLY_CHAIN_ITEMS = {
    "CRUDE_OIL": ["oil", "crude", "petroleum", "tanker", "vlcc", "brent", "wti", "원유", "유조선", "석유"],
    "NATURAL_GAS_LNG": ["lng", "gas", "natural gas", "methane", "qatar gas", "천연가스", "가스관"],
    "SEMICONDUCTOR": ["semiconductor", "chip", "foundry", "tsmc", "wafer", "lithography", "euv", "반도체", "웨이퍼"],
    "RARE_EARTHS": ["rare earth", "gallium", "germanium", "graphite", "antimony", "희토류", "갈륨", "게르마늄"],
    "BATTERY_MINERALS": ["lithium", "nickel", "cobalt", "cathode", "battery", "리튬", "니켈", "배터리", "이차전지"],
    "GRAIN_FOOD": ["grain", "wheat", "corn", "fertilizer", "food supply", "곡물", "밀", "옥수수", "비료"]
}

# 주요 지정학적 핫스팟 국가/지역
GEOPOLITICAL_HOTSPOTS = {
    "MIDDLE_EAST": ["iran", "israel", "yemen", "houthi", "gaza", "lebanon", "syria", "iraq", "saudi", "persian gulf"],
    "EAST_ASIA": ["taiwan", "china", "south china sea", "north korea", "dprk", "senkaku", "yellow sea"],
    "EASTERN_EUROPE": ["ukraine", "russia", "crimea", "black sea", "belarus", "baltic", "moldova"],
    "CENTRAL_AFRICA": ["sudan", "red sea coast", "somalia", "congo", "sahel"],
    "SOUTH_AMERICA": ["venezuela", "guyana", "essequibo"]
}


def normalize_entities(text: str) -> Dict[str, Any]:
    """ 텍스트에서 4대 해협, 핵심 공급망 품목, 핫스팟 지역 엔티티를 정규화 추출합니다. """
    text_lower = text.lower()
    
    detected_chokepoints = []
    for code, info in CHOKEPOINT_MAPPINGS.items():
        for pat in info["patterns"]:
            if re.search(pat, text_lower):
                detected_chokepoints.append({
                    "code": code,
                    "name": info["standard_name"],
                    "region": info["region"],
                    "primary_supply": info["primary_supply"]
                })
                break

    detected_supplies = []
    for item, kws in SUPPLY_CHAIN_ITEMS.items():
        if any(re.search(r'\b' + re.escape(kw) + r'\b', text_lower) for kw in kws):
            detected_supplies.append(item)

    detected_hotspots = []
    for spot, kws in GEOPOLITICAL_HOTSPOTS.items():
        if any(re.search(r'\b' + re.escape(kw) + r'\b', text_lower) for kw in kws):
            detected_hotspots.append(spot)

    return {
        "chokepoints": detected_chokepoints,
        "supply_chain_tags": detected_supplies,
        "hotspot_regions": detected_hotspots
    }


# ======================================================================
# 3. 시맨틱 중복 제거 및 클러스터링
# ======================================================================

def tokenize_for_similarity(text: str) -> Set[str]:
    """ 유사도 계산용 토큰 세트 생성 (소문자, 영숫자 2글자 이상, 불용어 제거) """
    text = html.unescape(text).lower()
    # 영문/숫자/한글 단어 추출
    tokens = set(re.findall(r'[a-zA-Z가-힣0-9]{2,}', text))
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "after", "says",
        "over", "into", "amid", "will", "have", "been", "were", "what", "more",
        "about", "news", "report", "reports", "latest", "update", "live", "today"
    }
    return tokens - stopwords


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """ 두 토큰 집합 간의 자카드 유사도를 계산합니다. """
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def deduplicate_and_cluster(articles: List[Dict[str, Any]], similarity_threshold: float = 0.40) -> List[Dict[str, Any]]:
    """
    동일 사건에 대한 다수 언론사 중복 보도를 대표 헤드라인 1건으로 클러스터링합니다.
    로컬 16GB RAM 환경에 최적화된 순수 파이썬 고속 군집화 알고리즘.
    """
    if not articles:
        return []

    clusters: List[Dict[str, Any]] = []

    for art in articles:
        title = art.get("title", "").strip()
        if not title or is_noise(title, art.get("url", ""), art.get("source", "")):
            continue

        tokens = tokenize_for_similarity(title)
        if len(tokens) < 2:
            continue

        matched_cluster = None
        best_sim = 0.0

        for c in clusters:
            sim = jaccard_similarity(tokens, c["token_set"])
            if sim >= similarity_threshold and sim > best_sim:
                best_sim = sim
                matched_cluster = c

        if matched_cluster:
            # 기존 클러스터에 병합
            matched_cluster["articles"].append(art)
            matched_cluster["cluster_size"] += 1
            matched_cluster["token_set"].update(tokens)
            source_name = art.get("source") or art.get("domain") or "Unknown"
            if source_name not in matched_cluster["sources"]:
                matched_cluster["sources"].append(source_name)
            # 더 긴 제목(정보량이 많은 것)을 대표 제목으로 유지
            if len(title) > len(matched_cluster["representative_title"]):
                matched_cluster["representative_title"] = title
                matched_cluster["url"] = art.get("url", matched_cluster["url"])
        else:
            # 신규 클러스터 생성
            source_name = art.get("source") or art.get("domain") or "Unknown"
            clusters.append({
                "representative_title": title,
                "url": art.get("url", ""),
                "published_at": art.get("published_at") or art.get("seendate") or "",
                "token_set": tokens,
                "cluster_size": 1,
                "sources": [source_name],
                "articles": [art]
            })

    # 후처리: 토큰 세트 제거 및 엔티티 정규화 정보 보강
    results = []
    for i, c in enumerate(clusters, start=1):
        entities = normalize_entities(c["representative_title"])
        rel_score = calculate_relevance(c["representative_title"])
        
        results.append({
            "cluster_id": f"CLUST-{i:04d}",
            "representative_title": c["representative_title"],
            "url": c["url"],
            "cluster_size": c["cluster_size"],
            "unique_sources_count": len(c["sources"]),
            "sources": c["sources"][:5],  # 상위 5개 출처만 간추림
            "relevance_score": rel_score,
            "chokepoints": entities["chokepoints"],
            "supply_chain_tags": entities["supply_chain_tags"],
            "hotspot_regions": entities["hotspot_regions"],
            "published_at": c["published_at"]
        })

    # 클러스터 크기(보도 집중도) 및 관련도 순으로 정렬
    results.sort(key=lambda x: (x["cluster_size"], x["relevance_score"]), reverse=True)
    return results


def run_pipeline_preprocessing(raw_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ 전체 4단계 전처리 파이프라인 통합 실행기 """
    print(f"  [전처리] 총 {len(raw_articles)}개 원시 기사 입력 수신.")
    
    # 1. 노이즈 필터링
    clean_articles = [
        a for a in raw_articles 
        if not is_noise(a.get("title", ""), a.get("url", ""), a.get("source", ""))
    ]
    filtered_out = len(raw_articles) - len(clean_articles)
    print(f"  [전처리] 노이즈 기사 필터링: {filtered_out}건 배제, 유효 {len(clean_articles)}건 유지.")
    
    # 2. 시맨틱 중복 제거 & 엔티티 정규화
    clustered = deduplicate_and_cluster(clean_articles)
    print(f"  [전처리] 시맨틱 중복 제거 완료: {len(clean_articles)}건 -> {len(clustered)}개 대표 사건으로 압축.")
    
    return clustered
