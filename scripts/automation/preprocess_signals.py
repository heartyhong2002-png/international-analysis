"""
preprocess_signals.py
=====================
공급망·지정학 리스크 조기경보 시스템을 위한 지능형 다국어 4단계 전처리 파이프라인.
(사건 예측이 아닌 비정형 공개 신호 정제·구조화 전담 모듈)

1. Step 1 (다국어 노이즈 필터링):
   - 연예·스포츠·패션·상업 광고·가십 배제 (7개 국어 + 한/중/일 CJK 확장)
   - 의례적 외교 수사(단순 의전, 축전, 만찬, 문화 행사, 박람회 홍보)와 실질적 위기 신호 분리
2. Step 2 (7개 국어 텍스트 정규화):
   - EN, FR, PT, DE, ES, RU, AR 유니코드 NFKD 악센트 제거 및 아랍어(Tashkeel/Alef)·키릴어(ё→е) 정규화
   - NLTK 언어별 Stopwords + 내장 다국어 불용어(Zero-Crash Fallback) 및 SnowballStemmer 어간 추출
3. Step 3 (시맨틱 중복 보도 군집화):
   - Jaccard 유사도 + 엔티티(해협/공급망/핫스팟/이벤트) 보너스 + 시간창(72h) 가드 기반 군집화
   - 동일 이슈는 대표 사건 1건으로 압축하고 sources=[...], source_types, observed_lanes 누적 보존
4. Step 4 (지정학·공급망 엔티티 태깅 및 표준 정형 스키마 변환):
   - 5대 해상 병목 표준코드(CHOKEPOINT_HORMUZ, CHOKEPOINT_BAB_EL_MANDEB, CHOKEPOINT_MALACCA,
     CHOKEPOINT_BOSPHORUS, CHOKEPOINT_PANAMA) 및 대만해협(CHOKEPOINT_TAIWAN_STRAIT) 매핑
   - 한국 6대 핵심 공급망 품목(CRUDE_OIL, NATURAL_GAS_LNG, SEMICONDUCTOR, RARE_EARTHS,
     BATTERY_MINERALS, GRAIN_FOOD) 다국어 사전 태깅
   - 모든 산출물은 verification_state="UNVERIFIED", alert_level_set=False 원칙 준수
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ======================================================================
# NLTK 다국어 엔진 및 내장 불용어 Fallback (7개 국어 완벽 지원)
# ======================================================================

LANG_MAP: Dict[str, str] = {
    "en": "english", "eng": "english", "english": "english",
    "fr": "french", "fra": "french", "fre": "french", "french": "french",
    "de": "german", "deu": "german", "ger": "german", "german": "german",
    "es": "spanish", "spa": "spanish", "spanish": "spanish",
    "pt": "portuguese", "por": "portuguese", "portuguese": "portuguese",
    "ru": "russian", "rus": "russian", "russian": "russian",
    "ar": "arabic", "ara": "arabic", "arabic": "arabic",
}

_FALLBACK_STOPWORDS: Dict[str, Set[str]] = {
    "english": {
        "the", "and", "for", "with", "that", "this", "from", "after", "says", "said",
        "over", "into", "amid", "will", "have", "has", "had", "been", "were", "was",
        "are", "what", "more", "about", "news", "report", "reports", "latest", "update",
        "live", "today", "their", "they", "them", "which", "would", "could", "should",
        "also", "between", "under", "during", "before", "through", "where", "while",
    },
    "french": {
        "le", "la", "les", "un", "une", "des", "du", "de", "dans", "avec", "pour",
        "sur", "par", "plus", "est", "sont", "ete", "etre", "avoir", "aux", "ces",
        "cette", "cet", "son", "sa", "ses", "leur", "leurs", "mais", "ou", "donc",
        "comme", "contre", "entre", "apres", "avant", "depuis", "selon", "tout", "tous",
    },
    "german": {
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "einem",
        "einen", "und", "mit", "auf", "fur", "fuer", "ist", "sind", "war", "waren",
        "von", "aus", "bei", "nach", "uber", "ueber", "unter", "gegen", "durch",
        "auch", "als", "wie", "noch", "wird", "werden", "wurde", "hat", "haben",
    },
    "spanish": {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "del", "al", "por",
        "con", "para", "sobre", "entre", "hasta", "desde", "hacia", "contra", "segun",
        "como", "mas", "pero", "sus", "este", "esta", "estos", "estas", "son", "fue",
        "han", "habia", "ser", "estar", "tiene", "tienen", "todo", "todos", "ante",
    },
    "portuguese": {
        "o", "a", "os", "as", "um", "uma", "uns", "umas", "do", "da", "dos", "das",
        "no", "na", "nos", "nas", "ao", "aos", "em", "com", "para", "por", "sobre",
        "entre", "contra", "como", "mais", "mas", "seu", "sua", "seus", "suas", "foi",
        "sao", "esta", "estao", "ter", "tem", "apos", "ante", "pelo", "pela", "pelos",
    },
    "russian": {
        "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то",
        "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за",
        "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "еще", "нет",
        "о", "из", "ему", "теперь", "когда", "даже", "ну", "вдруг", "ли", "если",
        "уже", "или", "ни", "быть", "был", "него", "до", "вас", "нибудь", "опять",
        "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей", "может", "они",
        "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем", "была",
        "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет",
        "при", "об", "этом", "это", "этого", "после", "через", "между", "против",
    },
    "arabic": {
        "في", "من", "على", "الى", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "تلك",
        "التي", "الذي", "الذين", "ما", "لا", "ان", "أن", "إن", "كان", "كانت", "بين",
        "بعد", "قبل", "حول", "خلال", "ضد", "كل", "بعض", "او", "أو", "ثم", "قد", "لم",
        "لن", "هو", "هي", "هم", "كما", "اي", "أي", "عند", "منذ", "حتى", "غير", "دون",
    },
}

_NLTK_STEMMERS: Dict[str, Any] = {}
_NLTK_STOPWORDS: Dict[str, Set[str]] = {
    lang: set(words) for lang, words in _FALLBACK_STOPWORDS.items()
}

try:
    from nltk.corpus import stopwords
    from nltk.stem.snowball import SnowballStemmer

    for _code, _full_lang in LANG_MAP.items():
        if _full_lang not in _NLTK_STEMMERS:
            try:
                _NLTK_STEMMERS[_full_lang] = SnowballStemmer(_full_lang)
            except Exception:
                pass
        try:
            _nltk_words = set(stopwords.words(_full_lang))
            _NLTK_STOPWORDS[_full_lang] = _NLTK_STOPWORDS.get(_full_lang, set()) | _nltk_words
        except Exception:
            pass
except ImportError:
    pass


# ======================================================================
# Step 1. 다국어 노이즈 필터링 & 의례적 외교 수사 배제 사전
# ======================================================================

NOISE_KEYWORDS: Set[str] = {
    # 영어 (EN) - 연예/스포츠/패션/상업/가십
    "celebrity", "celebs", "hollywood", "kardashian", "box office", "trailer", "premiere",
    "red carpet", "oscar", "grammy", "emmy", "singer", "album", "pop star",
    "dating", "romance", "wedding", "divorce", "fashion week", "horoscope",
    "zodiac", "lifestyle", "beauty pageant", "miss universe", "influencer",
    "reality show", "netflix series", "k-pop", "idol", "gossip", "nightclub",
    "football", "soccer", "champions league", "premier league", "laliga",
    "world cup", "nba", "basketball", "baseball", "mlb", "nfl", "super bowl",
    "tennis", "wimbledon", "formula 1", "f1 grand prix", "olympics medal", "olympic stars",
    "gymnastics", "ice hockey", "iihf", "fifa", "scoreline", "half-time", "touchdown", "hat-trick",
    "giveaway", "lottery", "jackpot", "crypto airdrop", "meme coin",
    "black friday discount", "promo code", "weight loss", "diet supplement",
    "sponsored content", "partner content", "shop now", "buy now",
    "limited offer", "click here", "subscribe now", "coupon",
    # 프랑스어 (FR)
    "celebrite", "célébrité", "chanteur", "mariage", "mode", "horoscope",
    "ligue 1", "victoire sportive", "championnat sportif", "telenovela",
    # 독일어 (DE)
    "promi", "schauspieler", "hochzeit", "horoskop", "bundesliga", "halbzeit",
    # 스페인어 (ES)
    "celebridad", "cantante", "boda", "divorcio", "moda", "horoscopo", "horóscopo",
    "copa libertadores", "futbol", "fútbol", "partido amistoso", "farándula",
    # 포르투갈어 (PT)
    "celebridade", "cantor", "casamento", "divorcio", "divórcio", "futebol", "campeonato",
    "fofoca", "novela", "bbb",
    # 러시아어 (RU) - 스포츠/연예/가십/광고
    "шоу-бизнес", "знаменитости", "сплетни", "гороскоп", "мода", "свадьба",
    "футбол", "хоккей", "большой хоккей", "чемпионат мира по хоккею", "спортивный суд",
    "фигурное катание", "олимпиада", "биатлон", "теннис", "матч", "сборная россии по хоккею",
    "промокод", "скидка", "распродажа", "лотерея",
    # 아랍어 (AR) - 스포츠/연예/가십/광고
    "مشاهير", "موضة", "أبراج", "حظك اليوم", "كرة القدم", "مباراة", "دوري أبطال",
    "الفنانة", "مسلسل", "أغنية", "تسوق الآن", "كود خصم",
    # 한국어 (KO)
    "연예", "연예인", "아이돌", "드라마", "예능", "열애", "결혼설", "이혼설",
    "가십", "패션위크", "호러스코프", "운세", "축구", "야구", "농구", "하키",
    "스포츠", "경기결과", "우승후보", "이적설", "감독선임", "광고", "프로모션",
    "할인코드", "이벤트 응모", "협찬",
    # 중국어/대만 로컬 포럼 (ZH / PTT Gossiping 노이즈)
    "演藝圈", "長青樹", "夜店", "吧台", "喝酒", "搭訕", "緋聞", "綜藝", "偶像",
    "星座", "運勢", "職棒", "籃球", "世足", "球賽", "促銷", "優惠碼", "抽獎",
    "鬼切計程", "綠色零食", "如聽一席話", "降落傘",
}

# 의례적 외교 수사 (단순 의전, 축전, 만찬, 문화 행사, 엑스포/박람회 홍보 등)
DIPLOMATIC_PROTOCOL_KEYWORDS: Set[str] = {
    "congratulatory message", "congratulatory letter", "congratulatory telegram",
    "birthday wishes", "national day reception", "cultural festival",
    "cultural exchange week", "art exhibition", "photo exhibition",
    "state banquet menu", "floral tribute", "wreath laying", "courtesy call",
    "goodwill visit", "sister city", "world's fair", "international expo",
    "expo 2017", "tourism promotion", "culinary diplomacy",
    "축전", "생일 축하", "국경일 리셉션", "문화주간", "미술전", "사진전",
    "친선교류", "자매결연", "화환 헌화", "만찬 메뉴", "관광 홍보",
    "поздравительная телеграмма", "культурный обмен", "выставка искусств",
    "برقية تهنئة", "مهرجان ثقافي", "تبادل ثقافي",
}

# 과거사 회고 / 자서전·도서 출간 / 가정법 잡담 / 부고·추모 (비실시간 신호 배제)
RETROSPECTIVE_OR_NON_CURRENT_KEYWORDS: Set[str] = {
    # 책 출간/회고록/자서전
    "memoir", "autobiography", "published a book", "new book", "book release", "book signing",
    "вышла книга", "книга политика", "автобиография", "мемуары", "издательстве",
    "출간", "회고록", "자서전", "신간", "도서 출간", "出書", "回憶錄", "自傳",
    # 과거사 가정법 / 잡담
    "if i were president", "if he were president", "当年是总统", "當年是總統",
    # 부고 / 추모
    "passes away", "passed away", "dies at age", "obituary", "tribute to",
    "умер в плену", "умер бывший", "скончался", "погиб в аварии",
    "별세", "부고", "타계", "사망 소식", "추모", "逝世", "訃告",
}

AD_SPONSOR_PATTERNS = [
    r"\b(sponsored|advertisement|advertorial|promo code|coupon code)\b",
    r"\b(shop now|buy now|limited[- ]time offer|click here to|we sponsor this channel)\b",
    r"\b(affiliate link|partner content|brand partner)\b",
    r"(광고|협찬|스폰서|프로모션|할인코드)",
    r"[?&](utm_campaign|utm_source)=",
]

SOFT_NEWS_SECTION_HINTS = [
    r"/entertainment/", r"/sports/", r"/sport/", r"/celebrity/",
    r"/lifestyle/", r"/fashion/", r"/horoscope/", r"/culture/celebrity",
    r"/gossip/", r"/movies/", r"/music/", r"/tvshow", r"/espn/",
    r"/연예/", r"/스포츠/", r"/라이프/", r"/연애/",
]

GEOPOLITICAL_KEYWORDS: Set[str] = {
    # 영어 (EN)
    "military", "navy", "naval", "army", "air force", "missile", "drone", "strike",
    "airstrike", "airstrikes", "attack", "explosion", "blockade", "chokepoint", "strait",
    "straits", "vessel", "ship", "shipping", "tanker", "cargo", "freight", "port",
    "terminal", "oil", "gas", "lng", "crude", "diesel", "refinery", "pipeline",
    "sanction", "sanctions", "export control", "export controls", "embargo", "tariff",
    "tariffs", "antidumping", "less-than-fair-value", "countervailing", "trade war",
    "semiconductor", "semiconductors", "hbm", "hbm4", "tsmc", "wafer", "rare earths",
    "lithium", "cobalt", "nickel", "uranium", "nuclear", "warhead", "defense",
    "conflict", "tensions", "ceasefire", "treaty", "sovereignty", "territory",
    "drills", "exercise", "patrol", "intercept", "casualty", "airspace", "hostage",
    "piracy", "insurgent", "houthi", "houthis", "irgc", "hezbollah", "hamas",
    "taiwan", "hormuz", "bosphorus", "malacca", "red sea", "black sea", "panama canal",
    "ukraine", "russia", "china", "israel", "gaza", "yemen", "iran", "protest",
    "election", "national security", "supply chain", "geopolitics", "diplomacy",
    "diplomatic", "cyberattack", "hackers", "central bank", "frozen assets",
    # 프랑스어 (FR)
    "militaire", "marine", "armee", "armée", "missile", "frappe", "attaque", "detroit",
    "détroit", "navire", "petrolier", "pétrolier", "port", "petrole", "pétrole", "gaz",
    "sanctions", "embargo", "conflit", "tensions", "manifestation", "greve", "grève",
    "blocage", "election", "élection", "protestation", "douane",
    # 독일어 (DE)
    "militar", "militär", "marine", "rakete", "drohne", "angriff", "strasse", "straße",
    "schiff", "tanker", "hafen", "erdol", "erdöl", "gas", "sanktionen", "konflikt",
    "spannungen", "streik", "protest", "wahl", "zoll", "halbleiter", "exportkontrolle",
    # 스페인어 (ES)
    "militar", "armada", "ejercito", "ejército", "misil", "ataque", "estrecho", "buque",
    "petrolero", "puerto", "petroleo", "petróleo", "gas", "sanciones", "conflicto",
    "tensiones", "manifestacion", "manifestación", "huelga", "elecciones", "bloqueo",
    "protesta", "aranceles",
    # 포르투갈어 (PT)
    "militar", "marinha", "exercito", "exército", "missil", "míssil", "ataque", "estreito",
    "navio", "petroleiro", "porto", "petroleo", "petróleo", "gas", "gás", "sancoes",
    "sanções", "conflito", "tensoes", "tensões", "manifestacao", "manifestação",
    "greve", "eleicoes", "eleições", "lula", "bloqueio", "protesto",
    # 러시아어 (RU)
    "военный", "военные", "война", "войной", "войны", "армия", "флот", "крейсер", "ракета", "дрон", "бпла", "удар", "атака",
    "блокада", "пролив", "танкер", "судно", "порт", "нефть", "газ", "спг", "дизель",
    "бензин", "топливо", "санкции", "санкций", "эмбарго", "пошлины", "экспорт",
    "полупроводник", "редкоземельные", "литий", "ядерный", "оружие", "конфликт",
    "напряженность", "переговоры", "перемирие", "перемирия", "безопасность", "хакерской", "дата-центров",
    "эвакуировали", "эвакуации", "всу", "плен", "запорожье", "ормуз", "красное море",
    # 아랍어 (AR)
    "عسكري", "بحرية", "جيش", "صاروخ", "مسيرة", "طائرات", "استهداف", "تدمير", "ضرب", "مدرعات",
    "هجوم", "قصف", "غارة", "حصار", "مضيق", "حرب", "الحرب", "سعودي", "السعودي", "لبنان",
    "هرمز", "باب المندب", "البحر الأحمر", "سفينة", "ناقلة", "ميناء", "نفط", "غاز",
    "عقوبات", "حظر", "تعريفة", "أشباه الموصلات", "نووي", "صراع", "توتر", "الحوثي",
    # 한국어 (KO)
    "군사", "해군", "공습", "미사일", "드론", "봉쇄", "해협", "호르무즈", "홍해",
    "말라카", "보스포루스", "파나마", "선박", "유조선", "항만", "운임", "원유", "석유",
    "천연가스", "반도체", "희토류", "배터리", "리튬", "곡물", "제재", "수출통제",
    "관세", "반덤핑", "공급망", "외교장관", "안보", "전략대화",
    # 중국어 (ZH)
    "軍事", "海軍", "飛彈", "導彈", "無人機", "空襲", "封鎖", "海峽", "台海", "荷姆茲",
    "紅海", "油輪", "港口", "原油", "天然氣", "能源", "台積電", "半導體", "晶片",
    "稀土", "鋰", "糧食", "制裁", "出口管制", "關稅", "兵推", "國防部", "核打擊",
}

NOISE_DOMAINS: Set[str] = {
    "tmz.com", "eonline.com", "variety.com", "hollywoodreporter.com",
    "people.com", "usmagazine.com", "pagesix.com", "dailymail.co.uk/tvshowbiz",
    "espn.com", "goal.com", "bleacherreport.com", "marca.com", "cbssports.com",
    "skysports.com", "foxsports.com", "nba.com", "nfl.com", "mlb.com",
    "fashionunited.com", "vogue.com", "cosmopolitan.com", "lequipe.fr", "ge.globo.com",
    "entertainment.cnn.com", "hollywood.yahoo.com", "sports.yahoo.com",
}

OFFICIAL_SOURCE_HINTS = (
    "white house", "whitehouse.gov", "state.gov", "federalregister", "federal register",
    "ofac", "bis.doc.gov", "commerce.gov", "treasury.gov", "defense.gov",
    "nato.", "un.org", "imf.org", "worldbank", "wto.org",
    "mofa", "ministry of foreign", "foreign ministry", "department of state", "외교부",
    "gov.br", "gov.uk", "gouv.fr", "bund.de", "go.jp", "go.kr", "fcdo",
)

MIN_RELEVANCE_SCORE = 0.5


# ======================================================================
# Step 2. 7개 국어 텍스트 정규화 (NFKD 악센트 + 아랍어/키릴 문자 정규화)
# ======================================================================

_ARABIC_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670\u0640]")


def normalize_accents(text: str) -> str:
    """
    7개 국어(EN, FR, PT, DE, ES, RU, AR) 텍스트 정규화:
    1) 라틴계 악센트(é, è, ç, ä, ö, ñ, ã 등) NFKD 분리·제거
    2) 러시아어 키릴 문자 ё -> е 정규화
    3) 아랍어 Tashkeel(모음 부호) 제거 및 Alef(أ, إ, آ -> ا), Teh Marbuta(ة -> ه) 정규화
    """
    if not text:
        return ""
    # 아랍어 정규화
    text = _ARABIC_DIACRITICS_RE.sub("", text)
    text = re.sub(r"[أإآ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    # 러시아어 ё -> е
    text = text.replace("ё", "е").replace("Ё", "Е")
    # 유니코드 NFKD 분리 후 결합 문자(악센트) 제거 (단, 키릴 й 등은 보존되도록 라틴 악센트 위주 제거)
    nfkd_form = unicodedata.normalize("NFKD", text)
    cleaned_chars = []
    for c in nfkd_form:
        if unicodedata.combining(c):
            continue
        cleaned_chars.append(c)
    return "".join(cleaned_chars)


def _count_keyword_hits(text_clean: str, keywords: Set[str]) -> int:
    hits = 0
    for kw in keywords:
        kw_norm = normalize_accents(kw.lower())
        if not kw_norm:
            continue
        # 한글·아랍어·키릴어·한자는 단어경계(\b) 또는 부분 문자열 매칭을 유연하게 처리
        if re.search(r"[\uac00-\ud7a3\u0600-\u06ff\u4e00-\u9fff]", kw_norm):
            if kw_norm in text_clean:
                hits += 1
        elif re.search(r"[\u0400-\u04ff]", kw_norm):
            # 러시아어는 어미 변화를 고려해 단어 시작 경계 매칭 허용
            if re.search(r"(?<![а-яa-z0-9])" + re.escape(kw_norm), text_clean):
                hits += 1
        else:
            if re.search(r"\b" + re.escape(kw_norm) + r"\b", text_clean):
                hits += 1
    return hits


def _is_official_or_wire_source(url: str = "", source: str = "") -> bool:
    blob = f"{url} {source}".lower()
    return any(hint in blob for hint in OFFICIAL_SOURCE_HINTS)


def _has_ad_or_soft_section(title: str, url: str = "") -> bool:
    blob = f"{title} {url}".lower()
    for pat in AD_SPONSOR_PATTERNS:
        if re.search(pat, blob, flags=re.IGNORECASE):
            return True
    for pat in SOFT_NEWS_SECTION_HINTS:
        if re.search(pat, (url or "").lower()):
            return True
    return False


# ======================================================================
# Step 4. 5대 해협 표준코드 및 한국 6대 핵심 공급망 품목 엔티티 정규화 사전
# ======================================================================

CHOKEPOINT_MAPPINGS: Dict[str, Dict[str, Any]] = {
    "CHOKEPOINT_HORMUZ": {
        "standard_name": "호르무즈 해협 (Strait of Hormuz)",
        "patterns": [
            r"hormuz", r"strait of hormuz", r"detroit d'ormuz", r"d[eé]troit d'ormuz",
            r"estreito de ormuz", r"stra[sß]e von hormus", r"estrecho de ormuz",
            r"ормузск", r"مضيق هرمز", r"تنگه هرمز", r"هرمز",
            r"ホルムズ", r"霍尔木兹", r"荷姆茲", r"호르무즈",
        ],
        "primary_supply": ["CRUDE_OIL", "NATURAL_GAS_LNG"],
        "region": "Middle East / Persian Gulf",
    },
    "CHOKEPOINT_BAB_EL_MANDEB": {
        "standard_name": "바브엘만데브 해협 및 홍해 (Bab-el-Mandeb & Red Sea)",
        "patterns": [
            r"bab[- ]el[- ]mandeb", r"bab al-mandab", r"red sea", r"mer rouge",
            r"mar vermelho", r"rotes meer", r"mar rojo", r"баб-эль-мандеб",
            r"красно[ем] мор", r"مضيق باب المندب", r"البحر الأحمر", r"البحر الاحمر",
            r"홍해", r"바브엘만데브", r"红海", r"紅海", r"曼德海峡", r"hudaydah", r"ras issa",
        ],
        "primary_supply": ["CRUDE_OIL", "NATURAL_GAS_LNG", "SEMICONDUCTOR"],
        "region": "Middle East / Red Sea",
    },
    "CHOKEPOINT_MALACCA": {
        "standard_name": "말라카 해협 (Strait of Malacca)",
        "patterns": [
            r"malacca", r"strait of malacca", r"detroit de malacca", r"d[eé]troit de malacca",
            r"estreito de malaca", r"stra[sß]e von malakka", r"estrecho de malaca",
            r"selat melaka", r"малаккск", r"مضيق ملقا",
            r"말라카", r"马六甲", r"麻六甲", r"マラッカ",
        ],
        "primary_supply": ["CRUDE_OIL", "NATURAL_GAS_LNG", "SEMICONDUCTOR"],
        "region": "Southeast Asia",
    },
    "CHOKEPOINT_BOSPHORUS": {
        "standard_name": "보스포루스 및 흑해 해협 (Bosphorus & Turkish Straits)",
        "patterns": [
            r"bosphorus", r"bosporus", r"dardanelles", r"detroit du bosphore",
            r"d[eé]troit du bosphore", r"estreito de b[oó]sforo", r"estrecho del b[oó]sforo",
            r"turkish straits", r"istanbul bo[gğ]az[ıi]", r"black sea", r"mer noire",
            r"mar negro", r"schwarzes meer", r"босфор", r"дарданелл", r"черно[ем] мор",
            r"البوسفور", r"البحر الأسود", r"보스포루스", r"다르다넬스", r"흑해 해협", r"흑해",
        ],
        "primary_supply": ["GRAIN_FOOD", "CRUDE_OIL"],
        "region": "Eurasia / Black Sea",
    },
    "CHOKEPOINT_PANAMA": {
        "standard_name": "파나마 운하 (Panama Canal)",
        "patterns": [
            r"panama canal", r"canal de panam[aá]", r"canal do panam[aá]",
            r"panamakanal", r"панамск[ийог]+ канал", r"قناة بنما",
            r"파나마\s*운하", r"巴拿马运河", r"巴拿馬運河",
        ],
        "primary_supply": ["NATURAL_GAS_LNG", "GRAIN_FOOD"],
        "region": "Americas / Latin America",
    },
    "CHOKEPOINT_TAIWAN_STRAIT": {
        "standard_name": "대만 해협 (Taiwan Strait)",
        "patterns": [
            r"taiwan strait", r"strait of taiwan", r"detroit de taiwan",
            r"d[eé]troit de ta[iï]wan", r"estreito de taiwan", r"formosastra[sß]e",
            r"estrecho de taiw[aá]n", r"тайваньск[ийог]+ пролив", r"مضيق تايوان",
            r"대만해협", r"대만 해협", r"台湾海峡", r"臺灣海峽", r"台海",
        ],
        "primary_supply": ["SEMICONDUCTOR", "BATTERY_MINERALS"],
        "region": "East Asia",
    },
}

# 한국 6대 핵심 공급망 품목 다국어 사전
SUPPLY_CHAIN_ITEMS: Dict[str, List[str]] = {
    "CRUDE_OIL": [
        "oil", "crude", "petroleum", "tanker", "tankers", "vlcc", "brent", "wti", "petrobras",
        "diesel", "gasoline", "refinery", "naphtha", "opec",
        "petrole", "petrolier", "brut", "petroleo", "petroleiro",
        "erdol", "rohol", "нефть", "нефти", "танкер", "дизель", "дизеля", "бензин", "топливо",
        "نفط", "بترول", "ناقلة نفط", "원유", "유조선", "석유", "정유", "나프타", "디젤",
        "原油", "石油", "油輪", "油價",
    ],
    "NATURAL_GAS_LNG": [
        "lng", "natural gas", "methane", "qatar gas", "henry hub", "gas pipeline", "gas supplies",
        "gaz naturel", "gnl", "gazoduc", "gas natural", "gasoduto", "erdgas",
        "спг", "природный газ", "газопровод", "غاز طبيعي", "الغاز المسال",
        "천연가스", "액화천연가스", "가스관", "天然氣", "液化天然氣",
    ],
    "SEMICONDUCTOR": [
        "semiconductor", "semiconductors", "chip", "chips", "foundry", "tsmc", "wafer",
        "lithography", "euv", "hbm", "hbm4", "dram", "nand", "nvidia", "asml", "sk hynix",
        "semi-conducteur", "puce", "semicondutor", "halbleiter",
        "полупроводник", "микросхем", "чип", "أشباه الموصلات", "رقائق",
        "반도체", "웨이퍼", "파운드리", "노광장비", "하이닉스",
        "台積電", "半導體", "晶片", "晶圓", "艾司摩爾",
    ],
    "RARE_EARTHS": [
        "rare earth", "rare earths", "gallium", "germanium", "graphite", "antimony",
        "neodymium", "dysprosium", "permanent magnet",
        "terres rares", "terras raras", "seltene erden", "tierras raras",
        "редкоземельн", "галлий", "германий", "сурьма", "معادن نادرة",
        "희토류", "갈륨", "게르마늄", "안티몬", "네오디뮴", "영구자석",
        "稀土", "鎵", "鍺", "石墨",
    ],
    "BATTERY_MINERALS": [
        "lithium", "nickel", "cobalt", "cathode", "anode", "battery", "ev battery",
        "litio", "minerio de ferro", "batterie", "bateria",
        "литий", "никель", "кобальт", "аккумулятор", "ليثيوم", "بطارية",
        "리튬", "수산화리튬", "니켈", "코발트", "배터리", "이차전지", "양극재", "음극재",
        "鋰", "鎳", "鈷", "電池",
    ],
    "GRAIN_FOOD": [
        "grain", "wheat", "corn", "soybean", "soya", "soja", "fertilizer", "urea", "food supply",
        "cereales", "ble", "engrais", "graos", "trigo", "fertilizante", "milho", "maiz",
        "getreide", "weizen", "dungemittel", "granos",
        "зерно", "пшениц", "кукуруз", "удобрен", "соя", "قمح", "حبوب", "أسمدة",
        "곡물", "소맥", "대두", "옥수수", "비료", "요소수", "요소",
        "糧食", "小麥", "大豆", "玉米", "肥料",
    ],
}

CRISIS_EVENT_TYPES: Dict[str, List[str]] = {
    "MILITARY_CONFLICT": [
        "airstrike", "airstrikes", "missile", "drone", "bombardment", "shelling", "attack",
        "warhead", "nuclear strike", "naval blockade", "intercept", "troops", "military buildup",
        "frappe", "attaque militaire", "angriff", "ataque militar",
        "военный", "удар", "бпла", "ракета", "ядерный удар", "крейсер", "всу", "殲敵", "核打擊", "兵推",
        "استهداف", "طائرات", "تدمير", "ضرب", "مدرعات", "قصف",
        "공습", "미사일", "교전", "폭격", "핵타격", "군사훈련",
    ],
    "SANCTIONS_EXPORT_CONTROL": [
        "sanction", "sanctions", "export control", "export controls", "embargo", "tariff",
        "tariffs", "antidumping", "less-than-fair-value", "countervailing", "blacklist",
        "entity list", "frozen assets", "ofac",
        "sanktionen", "sanciones", "sancoes", "санкции", "санкций", "замороженных", "пошлины",
        "عقوبات", "제재", "수출통제", "관세", "반덤핑", "자산동결", "制裁", "出口管制", "關稅",
    ],
    "INFRA_LOGISTICS_DISRUPTION": [
        "blockade", "port closure", "Grounded", "cyberattack", "hackers", "outage", "shortage",
        "fuel shortage", "power outage", "data center", "requisition", "bankruptcy", "collapse",
        "хакерской", "дефицит", "перебои", "краха банка", "дата-центров",
        "봉쇄", "운항중단", "해킹", "정전", "공급난", "파산", "斷電", "斷供", "能源封鎖",
    ],
    "PROTEST_STRIKE": [
        "protest", "strike", "riot", "clashes", "demonstration",
        "manifestation", "greve", "emeute", "blocage", "protestation",
        "protesto", "motim", "bloqueio", "streik", "proteste", "unruhen",
        "manifestacion", "huelga", "disturbios", "протест", "забастовка",
        "시위", "파업", "폭동", "抗議", "罷工",
    ],
    "ELECTION_GOVERNMENT": [
        "election", "vote", "victory", "lula", "president", "parliament", "coup", "inauguration",
        "executive order", "decree", "summit", "bilateral talks",
        "election", "victoire", "gouvernement", "eleicao", "eleicoes", "vitoria", "governo",
        "wahl", "regierung", "eleccion", "elecciones", "gobierno",
        "указ", "выборы", "переговоры", "대선", "총선", "정권", "정상회담", "외교장관", "차관",
    ],
}

GEOPOLITICAL_HOTSPOTS: Dict[str, List[str]] = {
    "MIDDLE_EAST": [
        "iran", "israel", "yemen", "houthi", "houthis", "gaza", "lebanon", "syria", "iraq",
        "saudi", "persian gulf", "red sea", "hudaydah", "hormuz", "moyen-orient", "oriente medio",
        "naher osten", "иран", "израиль", "йемен", "хусит",
        "إيران", "إسرائيل", "اليمن", "غزة", "السعودي", "الجوف", "لبنان",
        "이란", "이스라엘", "예멘", "후티", "가자", "사우디", "중동", "伊朗", "以色列",
    ],
    "EAST_ASIA": [
        "taiwan", "china", "south china sea", "north korea", "dprk", "senkaku", "yellow sea",
        "japan", "korea", "beijing", "tokyo", "seoul", "chine", "asie de l'est", "ostasien",
        "китай", "тайвань", "япония", "корея", "الصين", "تايوان",
        "대만", "중국", "북한", "일본", "한일", "양안", "남중국해", "台灣", "台海", "中共", "北京",
    ],
    "EASTERN_EUROPE": [
        "ukraine", "russia", "crimea", "black sea", "belarus", "baltic", "moldova", "danube",
        "kiev", "kyiv", "zaporozhye", "kherson", "serbia", "estonia", "nato",
        "russie", "russland", "rusia", "россия", "россии", "украин", "киев", "запорожье",
        "алешек", "сербии", "эстония", "러시아", "우크라이나", "나토", "烏俄", "烏軍", "普丁",
    ],
    "WESTERN_EUROPE": [
        "france", "germany", "uk", "britain", "european union", "paris", "berlin", "london",
        "deutschland", "franca", "francia", "европ", "유럽", "영국", "독일", "프랑스", "EU",
    ],
    "LATIN_AMERICA": [
        "brazil", "brasil", "venezuela", "guyana", "essequibo", "argentina", "chile", "panama",
        "colombia", "mexico", "amerique latine", "america latina", "latam", "mercosur", "lula",
        "petrobras", "bolsonaro", "브라질", "베네수엘라", "멕시코", "파나마", "중남미",
    ],
    "NORTH_AMERICA": [
        "united states", "white house", "washington", "pentagon", "commerce department",
        "federal register", "trump", "biden", "сша", "трамп", "미국", "백악관", "워싱턴", "川普", "華府",
    ],
    "CENTRAL_AFRICA": [
        "sudan", "red sea coast", "somalia", "congo", "sahel", "수단", "소말리아", "사헬",
    ],
}


def normalize_entities(text: str) -> Dict[str, Any]:
    """
    텍스트에서 5대 해협(+대만해협), 한국 6대 핵심 공급망 품목,
    5대 위기 이벤트 유형, 핫스팟 지역 엔티티를 다국어로 정규화 추출합니다.
    """
    text_lower = (text or "").lower()
    text_clean = normalize_accents(text_lower)

    detected_chokepoints: List[Dict[str, Any]] = []
    for code, info in CHOKEPOINT_MAPPINGS.items():
        for pat in info["patterns"]:
            pat_clean = normalize_accents(pat.lower())
            if re.search(pat, text_lower) or (pat_clean and re.search(pat_clean, text_clean)):
                detected_chokepoints.append({
                    "code": code,
                    "name": info["standard_name"],
                    "region": info["region"],
                    "primary_supply": info["primary_supply"],
                })
                break

    detected_supplies: List[str] = []
    for item, kws in SUPPLY_CHAIN_ITEMS.items():
        if _count_keyword_hits(text_clean, set(kws)) > 0:
            detected_supplies.append(item)

    detected_events: List[str] = []
    for evt, kws in CRISIS_EVENT_TYPES.items():
        if _count_keyword_hits(text_clean, set(kws)) > 0:
            detected_events.append(evt)

    detected_hotspots: List[str] = []
    for spot, kws in GEOPOLITICAL_HOTSPOTS.items():
        if _count_keyword_hits(text_clean, set(kws)) > 0:
            detected_hotspots.append(spot)

    return {
        "chokepoints": detected_chokepoints,
        "supply_chain_tags": detected_supplies,
        "event_types": detected_events,
        "hotspot_regions": detected_hotspots,
    }


def calculate_relevance(title: str) -> float:
    """지정학 및 글로벌 공급망 관련도 점수를 0.0~1.0 사이로 계산합니다 (다국어 지원)."""
    text_clean = normalize_accents((title or "").lower())
    matches = _count_keyword_hits(text_clean, GEOPOLITICAL_KEYWORDS)
    if matches >= 3:
        return 1.0
    elif matches == 2:
        return 0.8
    elif matches == 1:
        return 0.5
    return 0.2


def classify_article(
    title: str,
    url: str = "",
    source: str = "",
    summary: str = "",
    *,
    purity_mode: str = "standard",
    lane: str = "UNSPECIFIED",
) -> Dict[str, Any]:
    """
    기사를 keep/drop으로 분류하고 사유를 반환합니다.
    purity_mode:
      - "standard": 광범위 탐지 (기본값)
      - "high": 하드 엔티티(해협·핵심공급망·제재·군사충돌) 필수 + 회고/가정법/부고 배제 고순도 정제
    drop 우선순위:
      1) 빈 제목 또는 의미 없는 기호 나열 (empty_title)
      2) 노이즈 도메인 (noise_domain)
      3) 광고/스폰서/소프트뉴스 섹션 (ad_or_soft_section)
      4) 과거 회고·자서전 출간·가정법·부고 (retrospective_or_non_current_noise)
      5) 의례적 외교 수사/의전/박람회 홍보 (diplomatic_protocol_noise)
      6) 연예·스포츠·가십 노이즈 (entertainment_sports_noise / noise_outweighs_geo)
      7) 고순도 모드 공급망/해협 하드 엔티티 미달 (high_purity_missing_hard_entity)
      8) 지정학·공급망 관련도 미달 (low_geopolitical_relevance)
    """
    title_str = (title or "").strip()
    alpha_chars = re.findall(r"[a-zA-Z가-힣\u0400-\u04FF\u0600-\u06FF\u4E00-\u9FFF]", title_str)
    if not title_str or len(alpha_chars) < 3:
        return {
            "keep": False,
            "reason": "empty_title",
            "relevance_score": 0.0,
            "noise_hits": 0,
            "geo_hits": 0,
        }

    full_text = f"{title_str} {summary or ''}".strip()
    text_lower = f"{full_text} {source}".lower()
    text_clean = normalize_accents(text_lower)
    title_clean = normalize_accents(title_str.lower())
    url_lower = (url or "").lower()

    if any(
        re.search(r"(^|//|\.)" + re.escape(domain) + r"(/|$|\?)", url_lower)
        for domain in NOISE_DOMAINS
    ):
        return {
            "keep": False,
            "reason": "noise_domain",
            "relevance_score": 0.0,
            "noise_hits": 1,
            "geo_hits": 0,
        }

    if _has_ad_or_soft_section(full_text, url):
        if not _is_official_or_wire_source(url, source):
            return {
                "keep": False,
                "reason": "ad_or_soft_section",
                "relevance_score": 0.0,
                "noise_hits": 1,
                "geo_hits": 0,
            }

    noise_hits = _count_keyword_hits(text_clean, NOISE_KEYWORDS)
    protocol_hits = _count_keyword_hits(text_clean, DIPLOMATIC_PROTOCOL_KEYWORDS)
    retro_hits = _count_keyword_hits(text_clean, RETROSPECTIVE_OR_NON_CURRENT_KEYWORDS)
    geo_hits = _count_keyword_hits(text_clean, GEOPOLITICAL_KEYWORDS)
    rel_score = calculate_relevance(full_text)
    entities = normalize_entities(full_text)

    has_supply_or_chokepoint = bool(entities["chokepoints"] or entities["supply_chain_tags"])
    has_hard_conflict_or_sanction = bool(
        any(evt in ("MILITARY_CONFLICT", "SANCTIONS_EXPORT_CONTROL", "INFRA_LOGISTICS_DISRUPTION")
            for evt in entities["event_types"])
    )
    has_hard_entity = has_supply_or_chokepoint or has_hard_conflict_or_sanction or (
        "PROTEST_STRIKE" in entities["event_types"]
    )
    has_any_entity = bool(has_hard_entity or entities["event_types"] or entities["hotspot_regions"])

    # 과거사 회고 / 도서 출간 / 가정법 / 부고 배제
    if retro_hits > 0 and not has_supply_or_chokepoint:
        return {
            "keep": False,
            "reason": "retrospective_or_non_current_noise",
            "relevance_score": rel_score,
            "noise_hits": noise_hits + retro_hits,
            "geo_hits": geo_hits,
        }

    # 의례적 외교 수사(단순 축전, 문화행사, 엑스포 홍보 등) 배제
    if protocol_hits > 0 and not has_hard_entity:
        return {
            "keep": False,
            "reason": "diplomatic_protocol_noise",
            "relevance_score": rel_score,
            "noise_hits": noise_hits + protocol_hits,
            "geo_hits": geo_hits,
        }

    # 연예·스포츠·가십 노이즈 배제
    title_noise_hits = _count_keyword_hits(title_clean, NOISE_KEYWORDS)
    if title_noise_hits > 0 and not has_hard_entity:
        return {
            "keep": False,
            "reason": "entertainment_sports_noise",
            "relevance_score": rel_score,
            "noise_hits": noise_hits,
            "geo_hits": geo_hits,
        }

    if noise_hits > 0 and geo_hits == 0 and not has_any_entity:
        return {
            "keep": False,
            "reason": "entertainment_sports_noise",
            "relevance_score": rel_score,
            "noise_hits": noise_hits,
            "geo_hits": geo_hits,
        }

    if noise_hits >= 2 and geo_hits <= 1 and not has_hard_entity:
        return {
            "keep": False,
            "reason": "noise_outweighs_geo",
            "relevance_score": rel_score,
            "noise_hits": noise_hits,
            "geo_hits": geo_hits,
        }

    # [고순도 모드 (High-Purity Mode) 관문]
    if purity_mode == "high":
        # 1. 5대 해협 또는 한국 6대 공급망 또는 긴급 제재/군사충돌 하드 엔티티가 반드시 존재해야 함
        if not (has_supply_or_chokepoint or has_hard_conflict_or_sanction):
            return {
                "keep": False,
                "reason": "high_purity_missing_hard_entity",
                "relevance_score": rel_score,
                "noise_hits": noise_hits,
                "geo_hits": geo_hits,
            }
        # 2. 소셜·포럼(OPINION 레인)은 신뢰도 관문 강화 (관련도 0.8 이상이거나 하드 엔티티 2개 이상)
        if lane == "OPINION":
            entity_count = len(entities["chokepoints"]) + len(entities["supply_chain_tags"])
            if rel_score < 0.8 and entity_count < 2:
                return {
                    "keep": False,
                    "reason": "high_purity_social_threshold_unmet",
                    "relevance_score": rel_score,
                    "noise_hits": noise_hits,
                    "geo_hits": geo_hits,
                }

    # 지정학·공급망 신호가 거의 없으면 drop (공식 정부·규제 발표는 예외)
    if rel_score < MIN_RELEVANCE_SCORE and not has_any_entity:
        if _is_official_or_wire_source(url, source):
            return {
                "keep": True,
                "reason": "official_source_bypass",
                "relevance_score": rel_score,
                "noise_hits": noise_hits,
                "geo_hits": geo_hits,
            }
        return {
            "keep": False,
            "reason": "low_geopolitical_relevance",
            "relevance_score": rel_score,
            "noise_hits": noise_hits,
            "geo_hits": geo_hits,
        }

    return {
        "keep": True,
        "reason": "geopolitical_relevant",
        "relevance_score": rel_score,
        "noise_hits": noise_hits,
        "geo_hits": geo_hits,
    }


def is_noise(title: str, url: str = "", source: str = "", *, purity_mode: str = "standard") -> bool:
    """연예·스포츠·광고·의례수사·비지정학 기사면 True (하위 호환 래퍼)."""
    return not classify_article(title, url, source, purity_mode=purity_mode)["keep"]


# ======================================================================
# Step 3. 다국어 토큰화 및 Jaccard + 엔티티 보너스 기반 중복 보도 군집화
# ======================================================================

def detect_language_simple(text: str, default: str = "english") -> str:
    """텍스트의 문자 체계 및 기능어를 기반으로 7개 국어를 추정합니다."""
    t = (text or "").lower()
    if re.search(r"[\u0600-\u06FF]{2,}", t):
        return "arabic"
    if re.search(r"[а-яА-ЯёЁ]{2,}", t):
        return "russian"
    if re.search(r"\b(le|la|les|des|du|dans|avec|pour|est|sont|greve|manifestation)\b", t):
        return "french"
    if re.search(r"\b(der|die|das|und|mit|auf|fuer|ist|sind|streik|gegen|ueber)\b", t):
        return "german"
    if re.search(r"\b(el|la|los|las|del|por|con|para|huelga|gobierno|sobre)\b", t):
        return "spanish"
    if re.search(r"\b(o|os|as|do|da|dos|das|em|com|para|greve|eleicao|eleicoes|lula)\b", t):
        return "portuguese"
    return default


def tokenize_multilingual(text: str, lang: Optional[str] = None) -> Set[str]:
    """
    7개 국어 NFKD/아랍/키릴 정규화 + 언어별 불용어(NLTK + Built-in) 제거 +
    SnowballStemmer 어간 추출을 수행합니다.
    """
    text_unescaped = html.unescape(text or "")
    full_lang = LANG_MAP.get((lang or "").lower(), "") or detect_language_simple(text_unescaped)

    # 라틴, 한글, 키릴, 아랍, 한자(CJK) 토큰 추출
    raw_words = re.findall(
        r"[a-zA-Z가-힣0-9\u0600-\u06FF\u0400-\u04FF\u4E00-\u9FFF]{2,}",
        text_unescaped.lower(),
    )

    stop_set = _NLTK_STOPWORDS.get(full_lang, _FALLBACK_STOPWORDS["english"])
    stemmer = _NLTK_STEMMERS.get(full_lang)
    processed_tokens: Set[str] = set()

    for w in raw_words:
        w_norm = normalize_accents(w)
        if not w_norm or w in stop_set or w_norm in stop_set:
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
    """두 토큰 집합 간의 자카드 유사도를 계산합니다."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _parse_timestamp_utc(ts_str: str) -> Optional[datetime]:
    """다양한 형식(ISO 8601, RFC 2822, YYYY-MM-DD 등)의 발행 시각을 UTC datetime으로 변환합니다."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    s = ts_str.strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1] + "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def _within_time_window(ts1: Optional[datetime], ts2: Optional[datetime], max_hours: float = 72.0) -> bool:
    """두 기사의 발행 시각 차이가 max_hours 이내인지 확인합니다 (시각 미상 시 True)."""
    if ts1 is None or ts2 is None:
        return True
    diff_hours = abs((ts1 - ts2).total_seconds()) / 3600.0
    return diff_hours <= max_hours


def _score_headline_quality(title: str, url: str = "", source: str = "") -> float:
    """대표 헤드라인 선정 점수: 공식/주요 출처 가중치 + 적정 길이(35~140자) + 엔티티 밀도."""
    score = 0.0
    length = len(title or "")
    if 35 <= length <= 140:
        score += 0.4
    elif 20 <= length < 35 or 140 < length <= 200:
        score += 0.2
    if _is_official_or_wire_source(url, source):
        score += 0.35
    ents = normalize_entities(title)
    score += 0.15 * (
        len(ents["chokepoints"])
        + len(ents["supply_chain_tags"])
        + len(ents["event_types"])
    )
    return score


def deduplicate_and_cluster(
    articles: List[Dict[str, Any]],
    similarity_threshold: float = 0.25,
    max_time_window_hours: float = 72.0,
    *,
    purity_mode: str = "standard",
) -> List[Dict[str, Any]]:
    """
    동일 사건에 대한 다국어 중복 보도를 대표 사건 1건으로 클러스터링하고
    sources=[...], source_types=[...], observed_lanes=[...], purity_tier를 누적합니다.
    """
    if not articles:
        return []

    clusters: List[Dict[str, Any]] = []

    for art in articles:
        title = (art.get("title") or "").strip()
        summary = (art.get("summary") or art.get("description") or "").strip()
        url = art.get("url") or art.get("link") or art.get("source_url") or ""
        source_name = (
            art.get("source")
            or art.get("publisher")
            or art.get("source_platform")
            or art.get("domain")
            or "Unknown"
        )
        source_type = art.get("source_type") or "unclassified"
        lane = art.get("lane") or "UNSPECIFIED"
        lang = art.get("language")
        pub_raw = (
            art.get("published_at")
            or art.get("pub_date")
            or art.get("Published_Date")
            or art.get("publication_date")
            or art.get("seendate")
            or ""
        )

        if not title or is_noise(title, url, source_name, purity_mode=purity_mode):
            continue

        tokens = tokenize_multilingual(title, lang=lang)
        if len(tokens) < 2:
            # CJK 단문 헤드라인은 2글자 이상 토큰 1개라도 엔티티가 있으면 허용
            ents_check = normalize_entities(f"{title} {summary}")
            if not (ents_check["chokepoints"] or ents_check["supply_chain_tags"]):
                continue

        entities = normalize_entities(f"{title} {summary}")
        art_cps = {cp["code"] for cp in entities["chokepoints"]}
        art_supplies = set(entities["supply_chain_tags"])
        art_spots = set(entities["hotspot_regions"])
        art_events = set(entities["event_types"])
        art_dt = _parse_timestamp_utc(str(pub_raw))

        matched_cluster = None
        best_sim = 0.0

        for c in clusters:
            if not _within_time_window(art_dt, c["published_dt"], max_hours=max_time_window_hours):
                continue

            base_sim = jaccard_similarity(tokens, c["token_set"])

            # 엔티티(5대 해협/6대 공급망/핫스팟/위기유형) 동시 일치 시 보너스 부여
            bonus = 0.0
            if art_cps and (art_cps & c["chokepoints_set"]):
                bonus += 0.18
            if art_supplies and (art_supplies & c["supply_set"]):
                bonus += 0.10
            if art_spots and (art_spots & c["hotspot_set"]):
                bonus += 0.08
            if art_events and (art_events & c["event_set"]):
                bonus += 0.06

            if base_sim == 0.0 and not (art_cps and (art_cps & c["chokepoints_set"]) and (art_events & c["event_set"])):
                effective_sim = 0.0
            else:
                effective_sim = base_sim + bonus

            if effective_sim >= similarity_threshold and effective_sim > best_sim:
                best_sim = effective_sim
                matched_cluster = c

        hq_score = _score_headline_quality(title, url, source_name)

        if matched_cluster:
            matched_cluster["articles"].append(art)
            matched_cluster["cluster_size"] += 1
            matched_cluster["token_set"].update(tokens)
            matched_cluster["chokepoints_set"].update(art_cps)
            matched_cluster["supply_set"].update(art_supplies)
            matched_cluster["hotspot_set"].update(art_spots)
            matched_cluster["event_set"].update(art_events)
            if source_name not in matched_cluster["sources"]:
                matched_cluster["sources"].append(source_name)
            if source_type and source_type not in matched_cluster["source_types"]:
                matched_cluster["source_types"].append(source_type)
            if lane and lane not in matched_cluster["observed_lanes"]:
                matched_cluster["observed_lanes"].append(lane)
            if hq_score > matched_cluster["best_hq_score"]:
                matched_cluster["best_hq_score"] = hq_score
                matched_cluster["representative_title"] = title
                matched_cluster["url"] = url or matched_cluster["url"]
        else:
            clusters.append({
                "representative_title": title,
                "best_hq_score": hq_score,
                "url": url,
                "published_at": str(pub_raw),
                "published_dt": art_dt,
                "token_set": set(tokens),
                "chokepoints_set": set(art_cps),
                "supply_set": set(art_supplies),
                "hotspot_set": set(art_spots),
                "event_set": set(art_events),
                "cluster_size": 1,
                "sources": [source_name],
                "source_types": [source_type] if source_type else [],
                "observed_lanes": [lane] if lane else [],
                "articles": [art],
            })

    now_iso = datetime.now(timezone.utc).isoformat()
    results: List[Dict[str, Any]] = []

    for i, c in enumerate(clusters, start=1):
        combined_text = " ".join(
            f"{a.get('title', '')} {a.get('summary', '') or a.get('description', '')}"
            for a in c["articles"]
        )
        entities = normalize_entities(combined_text)
        rel_score = max(
            calculate_relevance(c["representative_title"]),
            calculate_relevance(combined_text),
        )

        has_multi_source = len(c["sources"]) >= 2
        is_official_lane = "FAST" in c["observed_lanes"] or any(
            _is_official_or_wire_source(a.get("url", ""), a.get("source", "")) for a in c["articles"]
        )
        has_direct_supply_or_cp = bool(entities["chokepoints"] or entities["supply_chain_tags"])

        if has_multi_source or (is_official_lane and has_direct_supply_or_cp):
            purity_tier = "TIER_1_CORROBORATED"
        elif has_direct_supply_or_cp:
            purity_tier = "TIER_2_VERIFIED_ENTITY"
        else:
            purity_tier = "TIER_3_SINGLE_SOURCE"

        # 고순도 모드에서는 TIER_1 및 TIER_2만 통과
        if purity_mode == "high" and purity_tier == "TIER_3_SINGLE_SOURCE":
            continue

        results.append({
            "cluster_id": f"CLUST-{i:04d}",
            "signal_id": f"SIG-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{i:04d}",
            "representative_title": c["representative_title"],
            "canonical_title": c["representative_title"],
            "url": c["url"],
            "cluster_size": c["cluster_size"],
            "unique_sources_count": len(c["sources"]),
            "sources": c["sources"],
            "source_types": c["source_types"],
            "observed_lanes": c["observed_lanes"],
            "purity_tier": purity_tier,
            "relevance_score": rel_score,
            "chokepoints": entities["chokepoints"],
            "supply_chain_tags": entities["supply_chain_tags"],
            "event_types": entities["event_types"],
            "hotspot_regions": entities["hotspot_regions"],
            "published_at": c["published_at"],
            "verification_state": "UNVERIFIED",
            "alert_level_set": False,
            "preprocessed_at": now_iso,
        })

    results.sort(
        key=lambda x: (
            1 if x.get("purity_tier") == "TIER_1_CORROBORATED" else (2 if x.get("purity_tier") == "TIER_2_VERIFIED_ENTITY" else 3),
            -x["unique_sources_count"],
            -x["cluster_size"],
            -(len(x["chokepoints"]) + len(x["supply_chain_tags"])),
            -x["relevance_score"],
        )
    )
    return results


def run_pipeline_preprocessing(
    raw_articles: List[Dict[str, Any]],
    *,
    purity_mode: str = "standard",
    return_rejects: bool = False,
) -> List[Dict[str, Any]] | Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """다국어 통합 4단계 전처리: 노이즈/의례수사/비관련 drop → 7개국어 정규화 → 중복 군집화 → 5대해협·6대공급망 태깅."""
    print(f"  [다국어 전처리 (mode={purity_mode})] 총 {len(raw_articles)}개 원시 기사 입력 수신.")

    clean_articles: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    reason_counts: Dict[str, int] = {}

    for a in raw_articles:
        title = a.get("title") or a.get("Title") or a.get("title_or_text") or ""
        summary = a.get("summary") or a.get("Summary") or a.get("description") or a.get("abstract") or ""
        url = a.get("url") or a.get("link") or a.get("Link") or a.get("source_url") or a.get("html_url") or ""
        source = (
            a.get("source")
            or a.get("publisher")
            or a.get("Source_ID")
            or a.get("source_platform")
            or a.get("domain")
            or ""
        )
        lane = a.get("lane", "UNSPECIFIED")

        decision = classify_article(title, url, source, summary=summary, purity_mode=purity_mode, lane=lane)
        if decision["keep"]:
            enriched = dict(a)
            enriched["title"] = title
            enriched["summary"] = summary
            enriched["url"] = url
            enriched["source"] = source
            enriched["_filter_reason"] = decision["reason"]
            enriched["_relevance_score"] = decision["relevance_score"]
            clean_articles.append(enriched)
        else:
            reason_counts[decision["reason"]] = reason_counts.get(decision["reason"], 0) + 1
            if return_rejects:
                rejected.append({
                    "title": title,
                    "url": url,
                    "source": source,
                    "lane": lane,
                    "reject_reason": decision["reason"],
                    "relevance_score": decision["relevance_score"],
                })

    filtered_out = len(raw_articles) - len(clean_articles)
    reason_summary = ", ".join(f"{k}={v}" for k, v in sorted(reason_counts.items())) or "none"
    print(
        f"  [다국어 전처리] 노이즈·비관련 필터링: {filtered_out}건 배제, "
        f"유효 {len(clean_articles)}건 유지 ({reason_summary})."
    )

    clustered = deduplicate_and_cluster(clean_articles, purity_mode=purity_mode)
    before_rel = len(clustered)
    clustered = [
        c for c in clustered
        if c.get("relevance_score", 0) >= MIN_RELEVANCE_SCORE
        or c.get("chokepoints")
        or c.get("supply_chain_tags")
        or c.get("event_types")
        or c.get("hotspot_regions")
        or _is_official_or_wire_source(
            c.get("url", ""),
            " ".join(str(s) for s in (c.get("sources") or [])),
        )
    ]
    if before_rel != len(clustered):
        print(
            f"  [다국어 전처리] 클러스터 관련도 재필터: {before_rel} → {len(clustered)} "
            f"(min_relevance={MIN_RELEVANCE_SCORE})."
        )
    print(
        f"  [다국어 전처리] 시맨틱 중복 제거 완료: "
        f"{len(clean_articles)}건 -> {len(clustered)}개 대표 사건으로 압축 (mode={purity_mode})."
    )

    if return_rejects:
        return clustered, rejected
    return clustered


def _run_self_test() -> int:
    """7개 국어 + CJK 샘플을 대상으로 4단계 전처리 자체 검증을 수행합니다."""
    sample_inputs = [
        # 1. 노이즈 (러시아 스포츠 하키, 대만 PTT 가십, 연예, 의례적 외교 박람회)
        {
            "title": "Спортивный суд обязал немедленно вернуть Россию в большой хоккей",
            "url": "https://meduza.io/feature/2026/11/02/sportivnyy-sud-hokkey",
            "source": "ru_meduza_rss",
            "lane": "CONTEXT",
        },
        {
            "title": "[問卦] 在夜店吧台喝酒的女生要怎麼搭訕？",
            "url": "https://www.ptt.cc/bbs/Gossiping/1.html",
            "source": "PTT_Gossiping",
            "lane": "OPINION",
        },
        {
            "title": "Expo 2017 to bring Kazakhstan under global spotlight: Kazakh FM",
            "url": "http://english.people.com.cn/8065488.html",
            "source": "cn_people_daily_world_rss",
            "lane": "CONTEXT",
        },
        # 2. 유효 지정학·공급망 신호 (동일 이슈 다중 출처 중복 군집화 검증 포함)
        {
            "title": "Iran-US mediated dialogue proceeds actively; Iran's terms on opening Strait of Hormuz",
            "url": "https://tass.com/world/2212029",
            "source": "TASS",
            "source_type": "state_media",
            "lane": "CONTEXT",
            "published_at": "2026-11-02T18:20:07Z",
        },
        {
            "title": "Iranian minister says negotiations depend on Strait of Hormuz oil shipping terms",
            "url": "https://reuters.com/world/middle-east/hormuz-talks",
            "source": "Reuters",
            "source_type": "wire_service",
            "lane": "FAST",
            "published_at": "2026-11-02T19:10:00Z",
        },
        {
            "title": "SK Hynix begins HBM4 production as Taiwan tightens export controls on advanced semiconductors",
            "url": "https://bsky.app/profile/semi/post/1",
            "source": "Bluesky_Social",
            "source_type": "opinion",
            "lane": "OPINION",
            "published_at": "2026-11-02T15:00:00Z",
        },
        {
            "title": "Saudi airstrikes hit Ras Issa oil port on the Red Sea in Houthi-controlled Yemen",
            "url": "https://bsky.app/profile/globaleye/post/2",
            "source": "Bluesky_Social",
            "source_type": "opinion",
            "lane": "OPINION",
            "published_at": "2026-11-02T12:00:00Z",
        },
    ]

    clusters, rejects = run_pipeline_preprocessing(sample_inputs, return_rejects=True)
    print(f"  [Self-Test] Rejects={len(rejects)}건, Clusters={len(clusters)}건")
    for r in rejects:
        print(f"    - DROP ({r['reject_reason']}): {r['title'][:60]}")
    for c in clusters:
        cps = [cp["code"] for cp in c["chokepoints"]]
        print(
            f"    - KEEP [{c['cluster_id']}] (size={c['cluster_size']}, sources={c['sources']}): "
            f"{c['representative_title'][:65]} | 해협={cps} | 공급망={c['supply_chain_tags']} | "
            f"verification={c['verification_state']}"
        )
    assert len(rejects) == 3, f"Expected 3 rejects, got {len(rejects)}"
    assert len(clusters) == 3, f"Expected 3 clusters (2 Hormuz merged + 1 Semi + 1 Red Sea), got {len(clusters)}"
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="지능형 다국어 4단계 전처리 파이프라인")
    parser.add_argument("--self-test", action="store_true", help="내장 다국어 샘플로 4단계 파이프라인 검증")
    args = parser.parse_args()
    if args.self_test:
        sys.exit(_run_self_test())
    sys.exit(_run_self_test())
