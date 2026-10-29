"""
preprocess_signals.py
=====================
무인 글로벌 이상 징후 탐지를 위한 지능형 다국어 4단계 전처리 파이프라인.
1. 노이즈 필터링 (연예·스포츠·상업 광고 배제 및 지정학 연관도 필터링)
2. 다국어(불어·포어·독어·서어·러시아어·아랍어·영어) 악센트 정규화 및 NLTK Snowball Stemming
3. 시맨틱 중복 제거 및 군집화 (동일 사건 다수 언론사 보도 압축)
4. 지정학·공급망 엔티티 정규화 (다국어 해협·지명 표준화 및 한국 핵심 공급망 품목 태깅)
5. 경량 구조화 및 신호 패키징 (로컬 16GB RAM 최적화)
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

# NLTK 다국어 엔진 로딩 (Graceful Fallback 지원)
_NLTK_STEMMERS: Dict[str, Any] = {}
_NLTK_STOPWORDS: Dict[str, Set[str]] = {}

LANG_MAP = {
    "en": "english", "eng": "english",
    "fr": "french", "fra": "french", "fre": "french",
    "de": "german", "deu": "german", "ger": "german",
    "es": "spanish", "spa": "spanish",
    "pt": "portuguese", "por": "portuguese",
    "ru": "russian", "rus": "russian",
    "ar": "arabic", "ara": "arabic"
}

try:
    import nltk
    from nltk.stem.snowball import SnowballStemmer
    from nltk.corpus import stopwords

    for code, full_lang in LANG_MAP.items():
        if full_lang not in _NLTK_STEMMERS:
            try:
                _NLTK_STEMMERS[full_lang] = SnowballStemmer(full_lang)
            except Exception:
                pass
        if full_lang not in _NLTK_STOPWORDS:
            try:
                _NLTK_STOPWORDS[full_lang] = set(stopwords.words(full_lang))
            except Exception:
                pass
except ImportError:
    pass


# ======================================================================
# 1. 노이즈 필터링 사전 및 정규식 (다국어 확장)
# ======================================================================

NOISE_KEYWORDS = {
    # 연예/오락/가십 (EN, FR, DE, ES, PT)
    "celebrity", "hollywood", "kardashian", "box office", "trailer", "premiere",
    "red carpet", "oscar", "grammy", "emmy", "singer", "album", "pop star",
    "dating", "romance", "wedding", "divorce", "fashion week", "horoscope",
    "zodiac", "lifestyle", "beauty pageant", "miss universe", "influencer",
    "célébrité", "chanteur", "mariage", "mode", "horoscope",
    "promi", "schauspieler", "hochzeit", "mode", "horoskop",
    "celebridad", "cantante", "boda", "divorcio", "moda", "horóscopo",
    "celebridade", "cantor", "casamento", "divórcio", "moda", "horóscopo",
    # 스포츠 (EN, FR, DE, ES, PT)
    "football", "soccer", "champions league", "premier league", "laliga",
    "world cup", "nba", "basketball", "baseball", "mlb", "nfl", "super bowl",
    "tennis", "wimbledon", "formula 1", "f1 grand prix", "olympics medal",
    "fifa", "scoreline", "half-time", "touchdown", "hat-trick",
    "ligue 1", "but", "match", "victoire sportive",
    "bundesliga", "tor", "halbzeit",
    "copa libertadores", "fútbol", "gol", "partido",
    "futebol", "gol", "partida", "campeonato",
    # 단순 상업/스팸/금융 프로모션
    "giveaway", "lottery", "jackpot", "crypto airdrop", "meme coin",
    "black friday discount", "promo code", "weight loss", "diet supplement"
}

GEOPOLITICAL_KEYWORDS = {
    # 영어
    "military", "navy", "naval", "army", "air force", "missile", "drone", "strike",
    "attack", "explosion", "blockade", "chokepoint", "strait", "vessel", "ship",
    "tanker", "cargo", "freight", "port", "terminal", "oil", "gas", "lng", "crude",
    "pipeline", "sanction", "sanctions", "export control", "embargo", "tariff", "trade war",
    "semiconductor", "rare earths", "uranium", "nuclear", "warhead", "defense",
    "conflict", "tensions", "ceasefire", "treaty", "sovereignty", "territory",
    "drills", "exercise", "patrol", "intercept", "casualty", "airspace", "hostage",
    "piracy", "insurgent", "houthi", "houthis", "irgc", "hezbollah", "hamas",
    "taiwan", "hormuz", "bosphorus", "malacca", "red sea", "black sea", "ukraine",
    "russia", "china", "israel", "gaza", "yemen", "iran", "protest", "strike", "election",
    # 프랑스어 (FR)
    "militaire", "marine", "armée", "missile", "frappe", "attaque", "détroit", "navire",
    "pétrolier", "port", "pétrole", "gaz", "sanctions", "embargo", "conflit", "tensions",
    "manifestation", "grève", "blocage", "élection", "présidentiel", "protestation",
    # 독일어 (DE)
    "militär", "marine", "rakete", "drohne", "angriff", "straße", "schiff", "tanker",
    "hafen", "erdöl", "gas", "sanktionen", "konflikt", "spannungen", "streik", "protest", "wahl",
    # 스페인어 (ES)
    "militar", "armada", "ejército", "misil", "ataque", "estrecho", "buque", "petrolero",
    "puerto", "petróleo", "gas", "sanciones", "conflicto", "tensiones", "manifestación",
    "huelga", "elecciones", "bloqueo", "protesta",
    # 포르투갈어 (PT)
    "militar", "marinha", "exército", "míssil", "ataque", "estreito", "navio", "petroleiro",
    "porto", "petróleo", "gás", "sanções", "conflito", "tensões", "manifestação",
    "greve", "eleições", "lula", "vitória", "bloqueio", "protesto"
}

NOISE_DOMAINS = {
    "tmz.com", "eonline.com", "variety.com", "hollywoodreporter.com",
    "espn.com", "goal.com", "bleacherreport.com", "marca.com",
    "fashionunited.com", "vogue.com", "cosmopolitan.com", "lequipe.fr", "ge.globo.com"
}


def normalize_accents(text: str) -> str:
    """ 악센트 부호(é, è, ç, ä, ö, ñ, ã 등)를 분리·정규화하여 비교용 베이스 문자열을 반환합니다. """
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def is_noise(title: str, url: str = "", source: str = "") -> bool:
    """ 연예, 스포츠, 광고 등 노이즈 기사 여부를 다국어로 판별합니다. """
    text_lower = f"{title} {source}".lower()
    text_clean = normalize_accents(text_lower)
    
    url_lower = url.lower()
    for domain in NOISE_DOMAINS:
        if domain in url_lower:
            return True

    noise_count = sum(1 for kw in NOISE_KEYWORDS if re.search(r'\b' + re.escape(normalize_accents(kw)) + r'\b', text_clean))
    geo_count = sum(1 for kw in GEOPOLITICAL_KEYWORDS if re.search(r'\b' + re.escape(normalize_accents(kw)) + r'\b', text_clean))

    if noise_count > 0 and geo_count == 0:
        return True
    if noise_count >= 2 and geo_count <= 1:
        return True

    return False


def calculate_relevance(title: str) -> float:
    """ 지정학 및 글로벌 공급망 관련도 점수를 0.0~1.0 사이로 계산합니다 (다국어 지원). """
    text_clean = normalize_accents(title.lower())
    matches = sum(1 for kw in GEOPOLITICAL_KEYWORDS if re.search(r'\b' + re.escape(normalize_accents(kw)) + r'\b', text_clean))
    if matches >= 3:
        return 1.0
    elif matches == 2:
        return 0.8
    elif matches == 1:
        return 0.5
    return 0.2


# ======================================================================
# 2. 지정학 및 공급망 엔티티 정규화 (다국어 확장)
# ======================================================================

CHOKEPOINT_MAPPINGS = {
    "CHOKEPOINT_HORMUZ": {
        "standard_name": "호르무즈 해협 (Strait of Hormuz)",
        "patterns": [
            r"hormuz", r"strait of hormuz", r"d[eé]troit d'ormuz", r"estreito de ormuz",
            r"stra[sß]e von hormus", r"estrecho de ormuz", r"مضيق هرمز", r"تنگه هرمز",
            r"ホルムズ", r"霍尔木兹", r"호르무즈"
        ],
        "primary_supply": ["CRUDE_OIL", "NATURAL_GAS_LNG", "NAPHTHA"],
        "region": "Middle East / Persian Gulf"
    },
    "CHOKEPOINT_BAB_EL_MANDEB": {
        "standard_name": "바브엘만데브 해협 및 홍해 (Bab-el-Mandeb & Red Sea)",
        "patterns": [
            r"bab[- ]el[- ]mandeb", r"bab al-mandab", r"red sea", r"mer rouge",
            r"mar vermelho", r"rotes meer", r"mar rojo", r"مضيق باب المندب",
            r"البحر الأحمر", r"홍해", r"바브엘만데브", r"红海", r"曼德海峡"
        ],
        "primary_supply": ["CONTAINER_CARGO", "CRUDE_OIL", "EUROPE_EXPORT"],
        "region": "Middle East / Red Sea"
    },
    "CHOKEPOINT_MALACCA": {
        "standard_name": "말라카 해협 (Strait of Malacca)",
        "patterns": [
            r"malacca", r"strait of malacca", r"d[eé]troit de malacca", r"estreito de malaca",
            r"stra[sß]e von malakka", r"estrecho de malaca", r"selat melaka", r"مضيق ملقا",
            r"말라카", r"马六甲", r"マラッカ"
        ],
        "primary_supply": ["CRUDE_OIL", "CONTAINER_CARGO", "COAL"],
        "region": "Southeast Asia"
    },
    "CHOKEPOINT_BOSPHORUS": {
        "standard_name": "보스포루스 및 흑해 해협 (Bosphorus & Turkish Straits)",
        "patterns": [
            r"bosphorus", r"bosporus", r"dardanelles", r"d[eé]troit du bosphore",
            r"estreito de b[oó]sforo", r"estrecho del b[oó]sforo", r"turkish straits",
            r"istanbul bo[gğ]az[ıi]", r"black sea", r"mer noire", r"mar negro", r"schwarzes meer",
            r"보스포루스", r"다르다넬스", r"흑해 해협", r"흑해", r"danube", r"danubio"
        ],
        "primary_supply": ["GRAIN_WHEAT", "CRUDE_OIL", "FERTILIZER"],
        "region": "Eurasia / Black Sea"
    },
    "CHOKEPOINT_TAIWAN_STRAIT": {
        "standard_name": "대만 해협 (Taiwan Strait)",
        "patterns": [
            r"taiwan strait", r"strait of taiwan", r"d[eé]troit de ta[iï]wan",
            r"estreito de taiwan", r"formosastra[sß]e", r"estrecho de taiw[aá]n",
            r"대만해협", r"대만 해협", r"台湾海峡", r"臺灣海峽", r"taiwan defense"
        ],
        "primary_supply": ["SEMICONDUCTOR", "ELECTRONICS", "EAST_ASIA_SHIPPING"],
        "region": "East Asia"
    }
}

SUPPLY_CHAIN_ITEMS = {
    "CRUDE_OIL": [
        "oil", "crude", "petroleum", "tanker", "tankers", "vlcc", "brent", "wti",
        "pétrole", "pétrolier", "brut", "petróleo", "petroleiro",
        "erdöl", "rohöl", "petróleo crudo", "petrolero", "원유", "유조선", "석유"
    ],
    "NATURAL_GAS_LNG": [
        "lng", "gas", "natural gas", "methane", "qatar gas",
        "gaz naturel", "gnl", "gazoduc", "gás natural", "gasoduto",
        "erdgas", "gas natural", "천연가스", "가스관"
    ],
    "SEMICONDUCTOR": [
        "semiconductor", "semiconductors", "chip", "chips", "foundry", "tsmc", "wafer", "lithography", "euv",
        "semi-conducteur", "puce", "semicondutor", "halbleiter", "반도체", "웨이퍼"
    ],
    "RARE_EARTHS": [
        "rare earth", "rare earths", "gallium", "germanium", "graphite", "antimony",
        "terres rares", "terras raras", "seltene erden", "tierras raras", "희토류", "갈륨", "게르마늄"
    ],
    "BATTERY_MINERALS": [
        "lithium", "nickel", "cobalt", "cathode", "battery",
        "batterie", "bateria", "batería", "리튬", "니켈", "배터리", "이차전지"
    ],
    "GRAIN_FOOD": [
        "grain", "wheat", "corn", "fertilizer", "food supply",
        "céréales", "blé", "engrais", "grãos", "trigo", "fertilizante",
        "getreide", "weizen", "düngemittel", "granos", "trigo", "곡물", "밀", "옥수수", "비료"
    ]
}

CRISIS_EVENT_TYPES = {
    "PROTEST_STRIKE": [
        "protest", "strike", "riot", "clashes", "demonstration", "blockade",
        "manifestation", "grève", "émeute", "blocage", "protestation",
        "protesto", "greve", "motim", "bloqueio",
        "streik", "proteste", "unruhen", "blockade",
        "manifestación", "huelga", "disturbios", "bloqueo", "시위", "파업", "봉쇄"
    ],
    "ELECTION_GOVERNMENT": [
        "election", "vote", "victory", "lula", "president", "parliament", "coup", "inauguration",
        "élection", "victoire", "président", "gouvernement",
        "eleição", "eleições", "vitória", "tse", "posse", "governo",
        "wahl", "sieg", "regierung",
        "elección", "elecciones", "victoria", "gobierno", "대선", "총선", "승리", "정권"
    ]
}

GEOPOLITICAL_HOTSPOTS = {
    "MIDDLE_EAST": ["iran", "israel", "yemen", "houthi", "houthis", "gaza", "lebanon", "syria", "iraq", "saudi", "persian gulf", "red sea", "moyen-orient", "oriente medio", "naher osten"],
    "EAST_ASIA": ["taiwan", "china", "south china sea", "north korea", "dprk", "senkaku", "yellow sea", "chine", "asie de l'est", "ostasien"],
    "EASTERN_EUROPE": ["ukraine", "russia", "crimea", "black sea", "belarus", "baltic", "moldova", "danube", "russie", "russland", "rusia"],
    "WESTERN_EUROPE": ["france", "germany", "paris", "berlin", "deutschland", "frança", "francia"],
    "LATIN_AMERICA": ["brazil", "brasil", "venezuela", "guyana", "essequibo", "argentina", "amérique latine", "américa latina"],
    "CENTRAL_AFRICA": ["sudan", "red sea coast", "somalia", "congo", "sahel"]
}


def normalize_entities(text: str) -> Dict[str, Any]:
    """ 텍스트에서 4대 해협, 핵심 공급망 품목, 위기 이벤트, 핫스팟 지역 엔티티를 다국어로 정규화 추출합니다. """
    text_lower = text.lower()
    text_clean = normalize_accents(text_lower)
    
    detected_chokepoints = []
    for code, info in CHOKEPOINT_MAPPINGS.items():
        for pat in info["patterns"]:
            if re.search(pat, text_lower) or re.search(normalize_accents(pat), text_clean):
                detected_chokepoints.append({
                    "code": code,
                    "name": info["standard_name"],
                    "region": info["region"],
                    "primary_supply": info["primary_supply"]
                })
                break

    detected_supplies = []
    for item, kws in SUPPLY_CHAIN_ITEMS.items():
        if any(re.search(r'\b' + re.escape(normalize_accents(kw)) + r'\b', text_clean) for kw in kws):
            detected_supplies.append(item)

    detected_events = []
    for evt, kws in CRISIS_EVENT_TYPES.items():
        if any(re.search(r'\b' + re.escape(normalize_accents(kw)) + r'\b', text_clean) for kw in kws):
            detected_events.append(evt)

    detected_hotspots = []
    for spot, kws in GEOPOLITICAL_HOTSPOTS.items():
        if any(re.search(r'\b' + re.escape(normalize_accents(kw)) + r'\b', text_clean) for kw in kws):
            detected_hotspots.append(spot)

    return {
        "chokepoints": detected_chokepoints,
        "supply_chain_tags": detected_supplies,
        "event_types": detected_events,
        "hotspot_regions": detected_hotspots
    }


# ======================================================================
# 3. 다국어 토큰화 및 시맨틱 군집화
# ======================================================================

def detect_language_simple(text: str, default: str = "english") -> str:
    """ 헤드라인의 주요 단어 특징을 기반으로 언어(english, french, german, spanish, portuguese)를 추정합니다. """
    t = text.lower()
    if re.search(r'\b(le|la|les|des|du|dans|avec|pour|est|sont|greve|manifestation)\b', t):
        return "french"
    if re.search(r'\b(der|die|das|und|mit|auf|fuer|ist|sind|streik|gegen)\b', t):
        return "german"
    if re.search(r'\b(el|la|los|las|del|por|con|para|huelga|gobierno|sobre)\b', t):
        return "spanish"
    if re.search(r'\b(o|os|as|do|da|dos|das|em|com|para|greve|eleicao|eleicoes|lula)\b', t):
        return "portuguese"
    if re.search(r'[а-яА-ЯёЁ]{3,}', t):
        return "russian"
    if re.search(r'[\u0600-\u06FF]{3,}', t):
        return "arabic"
    return default


def tokenize_multilingual(text: str, lang: Optional[str] = None) -> Set[str]:
    """ 다국어 악센트 정규화 + NLTK 언어별 불용어 제거 + Snowball Stemming을 적용합니다. """
    text = html.unescape(text)
    full_lang = LANG_MAP.get(lang.lower(), "english") if lang else detect_language_simple(text)
    
    # 1. 2글자 이상 단어 추출
    raw_words = re.findall(r'[a-zA-Z가-힣0-9\u0600-\u06FF\u0400-\u04FF]{2,}', text.lower())
    
    # 2. 언어별 불용어 제거
    stop_set = _NLTK_STOPWORDS.get(full_lang, set())
    if not stop_set:
        stop_set = {
            "the", "and", "for", "with", "that", "this", "from", "after", "says",
            "over", "into", "amid", "will", "have", "been", "were", "what", "more",
            "about", "news", "report", "reports", "latest", "update", "live", "today"
        }

    stemmer = _NLTK_STEMMERS.get(full_lang)
    processed_tokens: Set[str] = set()

    for w in raw_words:
        w_norm = normalize_accents(w)
        if w in stop_set or w_norm in stop_set:
            continue
        if stemmer:
            try:
                stemmed = stemmer.stem(w_norm)
                processed_tokens.add(stemmed)
            except Exception:
                processed_tokens.add(w_norm)
        else:
            processed_tokens.add(w_norm)

    return processed_tokens


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """ 두 토큰 집합 간의 자카드 유사도를 계산합니다. """
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def deduplicate_and_cluster(articles: List[Dict[str, Any]], similarity_threshold: float = 0.25) -> List[Dict[str, Any]]:
    """
    동일 사건에 대한 다국어 중복 보도를 대표 헤드라인 1건으로 정밀 클러스터링합니다.
    """
    if not articles:
        return []

    clusters: List[Dict[str, Any]] = []

    for art in articles:
        title = art.get("title", "").strip()
        lang = art.get("language")
        if not title or is_noise(title, art.get("url", ""), art.get("source", "")):
            continue

        tokens = tokenize_multilingual(title, lang=lang)
        if len(tokens) < 2:
            continue

        entities = normalize_entities(title)
        art_cps = {cp["code"] for cp in entities["chokepoints"]}
        art_spots = set(entities["hotspot_regions"])
        art_events = set(entities["event_types"])

        matched_cluster = None
        best_sim = 0.0

        for c in clusters:
            base_sim = jaccard_similarity(tokens, c["token_set"])
            
            # 엔티티(해협/핫스팟/위기유형) 일치 시 유사도 보너스 부여
            bonus = 0.0
            if art_cps and (art_cps & c["chokepoints_set"]):
                bonus += 0.20
            if art_spots and (art_spots & c["hotspot_set"]):
                bonus += 0.12
            if art_events and (art_events & c["event_set"]):
                bonus += 0.10

            effective_sim = base_sim + bonus

            if effective_sim >= similarity_threshold and effective_sim > best_sim:
                best_sim = effective_sim
                matched_cluster = c

        source_name = art.get("source") or art.get("domain") or "Unknown"

        if matched_cluster:
            matched_cluster["articles"].append(art)
            matched_cluster["cluster_size"] += 1
            matched_cluster["token_set"].update(tokens)
            matched_cluster["chokepoints_set"].update(art_cps)
            matched_cluster["hotspot_set"].update(art_spots)
            matched_cluster["event_set"].update(art_events)
            if source_name not in matched_cluster["sources"]:
                matched_cluster["sources"].append(source_name)
            if len(title) > len(matched_cluster["representative_title"]):
                matched_cluster["representative_title"] = title
                matched_cluster["url"] = art.get("url", matched_cluster["url"])
        else:
            clusters.append({
                "representative_title": title,
                "url": art.get("url", ""),
                "published_at": art.get("published_at") or art.get("seendate") or "",
                "token_set": tokens,
                "chokepoints_set": art_cps,
                "hotspot_set": art_spots,
                "event_set": art_events,
                "cluster_size": 1,
                "sources": [source_name],
                "articles": [art]
            })

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
            "sources": c["sources"][:5],
            "relevance_score": rel_score,
            "chokepoints": entities["chokepoints"],
            "supply_chain_tags": entities["supply_chain_tags"],
            "event_types": entities["event_types"],
            "hotspot_regions": entities["hotspot_regions"],
            "published_at": c["published_at"]
        })

    results.sort(key=lambda x: (x["cluster_size"], x["relevance_score"]), reverse=True)
    return results


def run_pipeline_preprocessing(raw_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ 다국어 통합 4단계 전처리 파이프라인 실행기 """
    print(f"  [다국어 전처리] 총 {len(raw_articles)}개 원시 기사 입력 수신.")
    
    clean_articles = [
        a for a in raw_articles 
        if not is_noise(a.get("title", ""), a.get("url", ""), a.get("source", ""))
    ]
    filtered_out = len(raw_articles) - len(clean_articles)
    print(f"  [다국어 전처리] 노이즈 기사 필터링: {filtered_out}건 배제, 유효 {len(clean_articles)}건 유지.")
    
    clustered = deduplicate_and_cluster(clean_articles)
    print(f"  [다국어 전처리] 시맨틱 중복 제거 완료: {len(clean_articles)}건 -> {len(clustered)}개 대표 사건으로 압축.")
    
    return clustered
