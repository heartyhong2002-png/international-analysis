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
from collections import Counter
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

# ======================================================================
# Step 1.5. 멀티모달(이미지·영상·문서) 1단계 메타데이터 정형화 & 시각 노이즈 배제 사전
# ======================================================================

VISUAL_NOISE_URL_PATTERNS = [
    r"giphy\.com", r"tenor\.com", r"imgflip\.com", r"9gag\.com", r"knowyourmeme\.com",
    r"doubleclick\.net", r"googlesyndication\.com", r"googleadservices\.com",
    r"gravatar\.com", r"facebook\.com/tr", r"analytics",
    r"(/|_|-)(avatar|emoji|favicon|icon|logo|banner|pixel|spacer|sprite|badge|button)s?(/|_|-|\.)",
    r"\b1x1\b", r"\.svg(\?|$)", r"^data:image/",
]

VISUAL_MEME_OR_CLICKBAIT_KEYWORDS: Set[str] = {
    "meme", "dank meme", "reaction gif", "shitpost", "funny video", "prank video",
    "cat video", "tiktok dance", "viral challenge", "blooper",
    "짤방", "유머짤", "움짤", "웃긴 영상", "낚시 영상",
    "мем", "мемы", "прикол", "смешное видео",
    "梗圖", "搞笑影片", "表情包",
}

VISUAL_MODALITY_KEYWORDS: Dict[str, List[str]] = {
    "SATELLITE_IMAGERY": [
        "satellite image", "satellite imagery", "satellite photo", "sar imagery",
        "maxar", "planet labs", "sentinel-2", "optical satellite",
        "위성사진", "위성 영상", "위성 포착", "спутниковые снимки", "спутниковый снимок",
        "صور الأقمار الصناعية", "衛星照片", "衛星影像",
    ],
    "TACTICAL_MARITIME_MAP": [
        "ais tracking", "marinetraffic", "tankertrackers", "flightradar",
        "frontline map", "battle map", "tactical map", "infographic", "shipping map",
        "전황 지도", "선박 항적", "항적도", "인포그래픽",
        "карта боевых", "инфографика", "خريطة", "航跡圖",
    ],
    "FIELD_PHOTO_VIDEO": [
        "drone footage", "video shows", "photo shows", "caught on camera",
        "cctv footage", "strike video", "dashcam", "eyewitness video",
        "на камеру", "видео удара", "кадры", "فيديو", "مشاهد",
        "현장 영상", "현장 사진", "드론 영상", "畫面", "影片",
    ],
    "OFFICIAL_DOCUMENT_PDF": [
        "federal register pdf", "official gazette", "annex pdf", "entity list pdf",
        "관보 원문", "공식 문서", "공식 관보",
    ],
}

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
    "espionage", "spy", "counterintelligence", "jensen huang", "nvidia", "ai chip", "gpu", "midterm", "congress",
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
    "간첩", "스파이", "기술유출", "엔비디아", "젠슨 황", "젠슨황", "중간선거", "미 의회",
    # 중국어 (ZH)
    "軍事", "海軍", "飛彈", "導彈", "無人機", "空襲", "封鎖", "海峽", "台海", "荷姆茲",
    "紅海", "油輪", "港口", "原油", "天然氣", "能源", "台積電", "半導體", "晶片",
    "稀土", "鋰", "糧食", "制裁", "出口管制", "關稅", "兵推", "國防部", "核打擊",
    "黃仁勳", "英偉達", "輝達", "間諜", "期中選舉",
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


_HTML_IMG_RE = re.compile(r"<img\b[^>]*>", flags=re.IGNORECASE)
_HTML_SRC_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', flags=re.IGNORECASE)
_HTML_ALT_RE = re.compile(r'\balt=["\']([^"\']+)["\']', flags=re.IGNORECASE)
_HTML_VIDEO_IFRAME_RE = re.compile(r"<(?:video|source|iframe)\b[^>]*>", flags=re.IGNORECASE)
_INLINE_MEDIA_URL_RE = re.compile(
    r"""https?://[^\s"'<>]+\.(?:jpg|jpeg|png|webp|gif|mp4|webm|mov|m3u8|pdf)(?:\?[^\s"'<>]*)?""",
    flags=re.IGNORECASE,
)
_HTML_TAG_STRIP_RE = re.compile(r"<[^>]+>")


def is_visual_noise_url(url: str) -> bool:
    """아이콘, 아바타, 배너 광고, 트래킹 픽셀, 밈(Giphy/Tenor 등) URL 여부를 판별합니다."""
    u = (url or "").strip().lower()
    if not u or len(u) < 8:
        return True
    for pat in VISUAL_NOISE_URL_PATTERNS:
        if re.search(pat, u, flags=re.IGNORECASE):
            return True
    return False


def strip_html_tags(text: str) -> str:
    """본문이나 제목에 포함된 Raw HTML 태그를 제거하고 공백을 정규화합니다."""
    if not text:
        return ""
    unescaped = html.unescape(text)
    no_script = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", unescaped, flags=re.IGNORECASE | re.DOTALL)
    no_tags = _HTML_TAG_STRIP_RE.sub(" ", no_script)
    return re.sub(r"\s+", " ", no_tags).strip()


def _classify_media_url_type(url: str, default_type: str = "external_card") -> str:
    u = (url or "").lower().split("?")[0]
    if u.endswith(".pdf"):
        return "document_pdf"
    if u.endswith((".mp4", ".webm", ".mov", ".m3u8")) or any(
        vh in u for vh in ("youtube.com/watch", "youtu.be/", "vimeo.com/", "/video/")
    ):
        return "video"
    if u.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")) or any(
        ih in u for ih in ("pbs.twimg.com/media", "cdn.bsky.app/img", "i.imgur.com/")
    ):
        return "image"
    return default_type


def extract_multimodal_metadata(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    [1단계 무다운로드 멀티모달 전처리]
    원시 레코드에서 이미지·영상·공식문서(PDF) URL과 대체 텍스트(alt_text / external_title)를
    추출·정형화하고, 시각 노이즈(아바타/픽셀/밈 URL) 및 Raw HTML 태그를 제거합니다.
    """
    raw_title = str(record.get("title") or record.get("Title") or record.get("title_or_text") or "")
    raw_summary = str(
        record.get("summary")
        or record.get("Summary")
        or record.get("description")
        or record.get("abstract")
        or ""
    )
    source_name = str(
        record.get("source")
        or record.get("publisher")
        or record.get("Source_ID")
        or record.get("source_platform")
        or ""
    )

    media_attachments: List[Dict[str, str]] = []
    seen_urls: Set[str] = set()
    alt_texts: List[str] = []
    dropped_noise_count = 0

    def _add_attachment(m_url: str, m_type: str, m_alt: str = "") -> None:
        nonlocal dropped_noise_count
        m_url_clean = (m_url or "").strip()
        m_alt_clean = strip_html_tags(m_alt)
        if not m_url_clean:
            if m_alt_clean and len(m_alt_clean) >= 4 and m_alt_clean not in alt_texts:
                alt_texts.append(m_alt_clean)
            return
        if is_visual_noise_url(m_url_clean):
            dropped_noise_count += 1
            return
        if m_url_clean not in seen_urls:
            seen_urls.add(m_url_clean)
            media_attachments.append({
                "type": m_type,
                "url": m_url_clean,
                "alt_text": m_alt_clean[:240],
                "source": source_name,
            })
        if m_alt_clean and len(m_alt_clean) >= 4 and m_alt_clean not in alt_texts:
            alt_texts.append(m_alt_clean[:240])

    # 1) 이미 전달된 media_attachments 처리
    if isinstance(record.get("media_attachments"), list):
        for att in record["media_attachments"]:
            if isinstance(att, dict):
                _add_attachment(
                    att.get("url", ""),
                    att.get("type") or _classify_media_url_type(att.get("url", "")),
                    att.get("alt_text", ""),
                )

    # 2) 명시적 수집기 미디어 필드 처리 (Federal Register pdf_url, Bluesky external_link 등)
    pdf_url = str(record.get("pdf_url") or "").strip()
    if pdf_url:
        _add_attachment(pdf_url, "document_pdf", str(record.get("doc_type") or "Official Gazette PDF"))

    ext_link = str(record.get("external_link") or "").strip()
    ext_title = str(record.get("external_title") or "").strip()
    if ext_link:
        _add_attachment(ext_link, _classify_media_url_type(ext_link, "external_card"), ext_title)
    elif ext_title:
        _add_attachment("", "external_card", ext_title)

    for key_u, m_t in (("image_url", "image"), ("video_url", "video"), ("media_url", "image")):
        val_u = str(record.get(key_u) or "").strip()
        if val_u:
            _add_attachment(val_u, _classify_media_url_type(val_u, m_t), str(record.get("alt_text") or ""))

    if isinstance(record.get("media_urls"), list):
        raw_alts = record.get("alt_texts") if isinstance(record.get("alt_texts"), list) else []
        for idx, u_item in enumerate(record["media_urls"]):
            a_item = raw_alts[idx] if idx < len(raw_alts) else ""
            _add_attachment(str(u_item), _classify_media_url_type(str(u_item), "image"), str(a_item))

    if record.get("alt_text") and isinstance(record.get("alt_text"), str):
        _add_attachment("", "image", record["alt_text"])

    # 3) HTML <img>, <video>, <iframe> 태그 및 인라인 미디어 URL 스캔
    combined_raw = f"{raw_title} {raw_summary}"
    for img_tag in _HTML_IMG_RE.findall(combined_raw):
        src_m = _HTML_SRC_RE.search(img_tag)
        alt_m = _HTML_ALT_RE.search(img_tag)
        _add_attachment(
            src_m.group(1) if src_m else "",
            "image",
            alt_m.group(1) if alt_m else "",
        )

    for vid_tag in _HTML_VIDEO_IFRAME_RE.findall(combined_raw):
        src_m = _HTML_SRC_RE.search(vid_tag)
        if src_m:
            _add_attachment(src_m.group(1), _classify_media_url_type(src_m.group(1), "video"), "")

    for inline_url in _INLINE_MEDIA_URL_RE.findall(combined_raw):
        _add_attachment(inline_url, _classify_media_url_type(inline_url, "image"), "")

    # 4) 본문 HTML 태그 제거
    clean_title = strip_html_tags(raw_title)
    clean_summary = strip_html_tags(raw_summary)

    # 5) 멀티모달 시각 신호 유형(Modality) 태깅
    full_clean_blob = normalize_accents(
        f"{clean_title} {clean_summary} {' '.join(alt_texts)}".lower()
    )
    detected_modalities: List[str] = []
    if any(att["type"] == "document_pdf" for att in media_attachments):
        detected_modalities.append("OFFICIAL_DOCUMENT_PDF")
    if any(att["type"] == "video" for att in media_attachments):
        detected_modalities.append("FIELD_PHOTO_VIDEO")

    for mod_code, mod_kws in VISUAL_MODALITY_KEYWORDS.items():
        if mod_code not in detected_modalities:
            if _count_keyword_hits(full_clean_blob, set(mod_kws)) > 0:
                detected_modalities.append(mod_code)

    return {
        "clean_title": clean_title,
        "clean_summary": clean_summary,
        "has_visual_media": bool(media_attachments or detected_modalities),
        "visual_modalities": detected_modalities,
        "media_attachments": media_attachments,
        "visual_alt_texts": alt_texts,
        "dropped_visual_noise_count": dropped_noise_count,
    }


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
        "jensen huang", "jensen", "b200", "blackwell", "h100", "ai gpu", "ai chip",
        "semi-conducteur", "puce", "semicondutor", "halbleiter",
        "полупроводник", "микросхем", "чип", "أشباه الموصلات", "رقائق",
        "반도체", "웨이퍼", "파운드리", "노광장비", "하이닉스", "엔비디아", "젠슨 황", "젠슨황",
        "台積電", "半導體", "晶片", "晶圓", "艾司摩爾", "黃仁勳", "輝達", "英偉達",
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
        "entity list", "frozen assets", "ofac", "espionage", "spy", "counterintelligence", "leak", "tech leak",
        "sanktionen", "sanciones", "sancoes", "санкции", "санкций", "замороженных", "пошлины",
        "عقوبات", "제재", "수출통제", "관세", "반덤핑", "자산동결", "스파이", "간첩", "기술유출", "방첩", "방첩수사",
        "制裁", "出口管制", "關稅", "間諜", "洩密",
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
        "executive order", "decree", "summit", "bilateral talks", "midterm", "midterms", "congress", "senate",
        "house of representatives", "chips act",
        "election", "victoire", "gouvernement", "eleicao", "eleicoes", "vitoria", "governo",
        "wahl", "regierung", "eleccion", "elecciones", "gobierno",
        "указ", "выборы", "переговоры", "대선", "총선", "정권", "정상회담", "외교장관", "차관",
        "중간선거", "미 의회", "상원", "하원", "반도체법", "期中選舉",
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
    meme_hits = _count_keyword_hits(text_clean, VISUAL_MEME_OR_CLICKBAIT_KEYWORDS)
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

    # 시각 노이즈(밈/짤방/유머 움짤/낚시 영상) 배제
    if (meme_hits > 0 or is_visual_noise_url(url_lower)) and not has_hard_entity:
        return {
            "keep": False,
            "reason": "visual_meme_or_clickbait_noise",
            "relevance_score": rel_score,
            "noise_hits": noise_hits + meme_hits,
            "geo_hits": geo_hits,
        }

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

LANGUAGE_PATTERNS = {
    "ko": (r"[\uac00-\ud7a3]{2,}", "Korean"),
    "ja": (r"[\u3040-\u30ff]{2,}", "Japanese"),
    "ar": (r"[\u0600-\u06ff]{2,}", "Arabic"),
    "ru": (r"[\u0400-\u04ff]{3,}", "Russian"),
    "zh": (r"[\u4e00-\u9fff]{3,}", "Chinese"),
}

LATIN_STOPWORDS = {
    "fr": (r"\b(le|la|les|des|du|dans|avec|pour|est|sont|détroit|pétrole|navire|frappe|attaque)\b", "French"),
    "de": (r"\b(der|die|das|und|mit|auf|fuer|ist|sind|straße|erdöl|schiff|angriff|sanktionen)\b", "German"),
    "es": (r"\b(el|la|los|las|del|por|con|para|estrecho|petróleo|buque|ataque|sanciones)\b", "Spanish"),
    "pt": (r"\b(o|os|as|do|da|dos|das|em|com|para|estreito|petróleo|navio|ataque|sanções|lula)\b", "Portuguese"),
    "en": (r"\b(the|and|for|with|that|strait|tanker|missile|attack|shipping|export|control)\b", "English"),
}


def detect_language_detailed(text: str) -> Dict[str, Any]:
    """
    텍스트의 유니코드 스크립트(한글, CJK한자, 가나, 아랍어, 키릴) 및 기능어(라틴 불용어)를
    통해 ISO 639-1 언어 코드(ko, en, zh, ru, ar, fr, de, es, pt, ja)와 신뢰도를 반환합니다.
    """
    t = (text or "").strip()
    if not t:
        return {"language_code": "unknown", "language_name": "Unknown", "confidence": 0.0}

    # 1. Non-Latin scripts check (CJK, Arabic, Cyrillic)
    for code, (pat, name) in LANGUAGE_PATTERNS.items():
        matches = re.findall(pat, t)
        if matches:
            total_chars = sum(len(m) for m in matches)
            confidence = min(0.99, round(total_chars / max(1, len(t) * 0.4), 2))
            return {
                "language_code": code,
                "language_name": name,
                "confidence": max(0.6, confidence),
            }

    # 2. Latin scripts check
    t_lower = t.lower()
    scores = {}
    for code, (pat, name) in LATIN_STOPWORDS.items():
        matches = re.findall(pat, t_lower)
        if matches:
            scores[code] = (len(matches), name)

    if scores:
        best_code = max(scores.keys(), key=lambda k: scores[k][0])
        hits, name = scores[best_code]
        conf = min(0.95, round(hits / 5.0, 2))
        return {
            "language_code": best_code,
            "language_name": name,
            "confidence": max(0.5, conf),
        }

    return {"language_code": "en", "language_name": "English", "confidence": 0.5}


ACTOR_RULES = [
    (r"\b(irgc|iranian (navy|military|army|forces)|iran|tehran)\b|이란|혁명수비대|طهران|حرس ثوري", "IRAN_MILITARY_OR_GOV", "이란 혁명수비대 / 정부 (IRGC / Iran)"),
    (r"\b(houthi|ansarallah|yahya saree|yemen armed forces)\b|후티|안사룰라|الحوثي|أنصار الله", "HOUTHI_YEMEN", "예멘 후티 반군 (Houthi / Ansarallah)"),
    (r"\b(idf|israeli (military|forces|army|air force)|israel|netanyahu)\b|이스라엘|네타냐후|إسرائيل", "ISRAEL_IDF", "이스라엘 방위군 / 정부 (IDF / Israel)"),
    (r"\b(us|u\.s\.|usa|united states|us navy|pentagon|white house|biden|trump|department of commerce|bis|ofac)\b|미국|미군|백악관|미 상무부|재무부|워싱턴|펜타곤|сша", "US_GOV_OR_MILITARY", "미국 정부 / 군 (US Gov / Military)"),
    (r"\b(russian (military|forces|navy|army)|kremlin|putin|moscow|mod russia)\b|러시아군|크렘린|푸틴|러시아 국방부|минобороны рф|вс рф", "RUSSIA_MILITARY_OR_GOV", "러시아 정부 / 군 (Russia Gov / Military)"),
    (r"\b(ukrainian (armed forces|military)|zelensky|kyiv|afu)\b|우크라이나군|젤렌스키|키이우|всу", "UKRAINE_GOV_OR_MILITARY", "우크라이나 정부 / 군 (Ukraine Gov / Military)"),
    (r"\b(pla|chinese (navy|military)|beijing|china)\b|중국군|해방군|중국 해군|인민해방군|중국", "CHINA_PLA_OR_GOV", "중국 인민해방군 / 정부 (China PLA / Gov)"),
    (r"\b(taiwan (defense ministry|military|navy)|taipei|taiwan)\b|대만 국방부|대만군|타이베이|대만", "TAIWAN_AUTHORITY", "대만 국방부 / 당국 (Taiwan Authority)"),
    (r"\b(tsmc|sk hynix|samsung( electronics)?|asml|nvidia|applied materials|lam research|intel)\b|삼성전자|sk하이닉스|엔비디아|台積電", "SEMICONDUCTOR_CHIPMAKER", "글로벌 반도체 기업 (Semiconductor Enterprise)"),
    (r"\b(maersk|frontline|zim|cosco)\b|머스크|프론트라인", "SHIPPING_CARRIER", "글로벌 해운사 (Shipping Carrier)"),
]

ACTION_RULES = [
    (r"\b(struck|strike|strikes|hit|attack|attacked|attacks|bombed|missile strike|drone attack|airstrike|airstrikes|intercepted|intercept)\b|피격|공습|미사일 공격|드론 공격|격추|ضرب|استهداف|هجوم|قصف|удар|атака", "PHYSICAL_STRIKE", "물리적 공격 / 공습 (Physical Strike / Attack)"),
    (r"\b(exploded|explosion|detonated|mine strike|blew up|on fire|catches fire)\b|폭발|기뢰 피격|화재 발생|انفجار|взрыв|пожар", "EXPLOSION_OR_FIRE", "기뢰 폭발 / 선박 화재 (Explosion / Mine Strike)"),
    (r"\b(seized|seizure|hijacked|boarded|detained|blockade|blockaded|diverted|rerouted|stopped shipping)\b|나포|억류|봉쇄|통항 차단|항로 우회|احتجاز|حصار|задержан|перехват", "SEIZURE_OR_BLOCKADE", "선박 나포 / 통항 봉쇄 (Seizure / Maritime Blockade)"),
    (r"\b(export control|export controls|controls|sanction|sanctions|sanctioned|tariff|tariffs|embargo|blacklist|entity list|countervailing|antidumping|curb)\b|수출통제|제재|관세|엠바고|블랙리스트|규제|عقوبات|санкции|пошлины", "REGULATORY_SANCTION", "수출통제 / 무역제재 (Export Control / Sanctions)"),
    (r"\b(production shutdown|fab halt|shortage|strike halted|disrupted|supply halt)\b|생산 중단|가동 중단|공급 중단|차질|파업|остановка|сбой", "PRODUCTION_DISRUPTION", "생산 중단 / 공급망 차질 (Production Disruption)"),
    (r"\b(drill|drills|exercise|exercises|maneuver|maneuvers|war game)\b|군사훈련|기동훈련|실사격|تدريبات|учения", "MILITARY_EXERCISE", "군사 훈련 / 무력 시위 (Military Exercise)"),
    (r"\b(scandal|investigation|corruption|probe|lawsuit|antitrust)\b|스캔들|수사|조사|반독점|부패", "LEGAL_OR_COMPLIANCE_PROBE", "규제 조사 / 법적 리스크 (Regulatory / Compliance Probe)"),
    (r"\b(dialogue|negotiation|talks|ceasefire|truce|agreement|diplomatic)\b|회담|협상|휴전|외교 대화|مفاوضات|هدنة|переговоры", "DIPLOMATIC_NEGOTIATION", "외교 협상 / 휴전 대화 (Diplomatic Negotiation)"),
]

TARGET_RULES = [
    (r"\b(oil tanker|tanker|tankers|crude tanker|vlcc|petroleum tanker)\b|유조선|원유 운반선|ناقلة نفط|танкер", "CRUDE_OIL_TANKER", "원유 수송 유조선 (Crude Oil Tanker)"),
    (r"\b(lng carrier|gas carrier|methane carrier)\b|lng선|가스 운반선|ناقلة غاز", "LNG_GAS_CARRIER", "LNG 천연가스 운반선 (LNG Carrier)"),
    (r"\b(cargo ship|container ship|freighter|merchant vessel|commercial ship)\b|상선|화물선|컨테이너선|سفينة شحن|судно", "COMMERCIAL_CARGO_SHIP", "상선 / 컨테이너 화물선 (Commercial Cargo Ship)"),
    (r"\b(port|terminal|harbor|dock|refinery|pipeline)\b|항만|터미널|정유소|파이프라인|부두|ميناء|مرفأ|порт|нпз", "PORT_ENERGY_INFRA", "항만 / 정유 / 에너지 인프라 (Port & Energy Infra)"),
    (r"\b(semiconductor|semiconductors|chip|chips|hbm|hbm4|fab|wafer|lithography|euv|gpu)\b|반도체|웨이퍼|팹|노광장비|晶片|полупроводник", "SEMICONDUCTOR_SUPPLY_ASSET", "반도체 칩 / 웨이퍼 / 제조장비 (Semiconductor Asset)"),
    (r"\b(rare earth|rare earths|critical minerals|lithium|nickel|cobalt)\b|희토류|리튬|핵심광물|редкоземельные", "CRITICAL_MINERAL_ASSET", "희토류 / 핵심 광물 자원 (Critical Mineral Asset)"),
    (r"\b(warship|destroyer|frigate|military base|radar|air defense)\b|군함|구축함|군사기지|방공망|военный корабль", "MILITARY_FACILITY_OR_WARSHIP", "군함 / 군사 기지 시설 (Military Asset)"),
]


def extract_event_tuple(
    title: str,
    summary: str = "",
    entities: Optional[Dict[str, Any]] = None,
    published_at: str = "",
) -> Dict[str, Any]:
    """
    [NLP 정보추출(IE) 기반 5W1H 이벤트 튜플 생성]
    비정형 텍스트에서 주체(Who), 행위(Action), 대상(Target), 장소(Where),
    시점(When), 공급망 영향(Impact), 위협 심각도(Severity)를 추출하여 정형 튜플로 반환합니다.
    """
    blob = f"{title} {summary}".strip()
    blob_lower = blob.lower()

    # 1. Who (Actor)
    actor_code = "UNKNOWN_OR_UNSPECIFIED"
    actor_label = "미상 / 민간 다국적 출처 (Unspecified / Multiple Sources)"
    for pat, code, label in ACTOR_RULES:
        if re.search(pat, blob_lower, re.IGNORECASE):
            actor_code = code
            actor_label = label
            break

    # 2. Action (Predicate)
    action_code = "MONITORING_OR_GENERAL_EVENT"
    action_label = "일반 정세 보고 및 모니터링 (General Geopolitical Observation)"
    for pat, code, label in ACTION_RULES:
        if re.search(pat, blob_lower, re.IGNORECASE):
            action_code = code
            action_label = label
            break

    # 3. Target (Patient)
    target_code = "UNSPECIFIED_TARGET"
    target_label = "특정 대상 미상 (Unspecified Target)"
    for pat, code, label in TARGET_RULES:
        if re.search(pat, blob_lower, re.IGNORECASE):
            target_code = code
            target_label = label
            break

    # 4. Where (Location / Chokepoint)
    chokepoints = entities.get("chokepoints", []) if entities else []
    hotspots = entities.get("hotspot_regions", []) if entities else []

    where_parts = []
    if chokepoints:
        for cp in chokepoints:
            where_parts.append(cp.get("name") or cp.get("code"))
    elif hotspots:
        where_parts.extend(hotspots)
    where_label = ", ".join(where_parts) if where_parts else "글로벌 지정학 해역 (Global Maritime / Geopolitical Area)"

    # 5. Supply Impact
    supplies = list(entities.get("supply_chain_tags", [])) if entities else []
    if not supplies:
        if target_code == "CRUDE_OIL_TANKER":
            supplies = ["CRUDE_OIL"]
        elif target_code == "LNG_GAS_CARRIER":
            supplies = ["NATURAL_GAS_LNG"]
        elif target_code == "SEMICONDUCTOR_SUPPLY_ASSET":
            supplies = ["SEMICONDUCTOR"]
        elif target_code == "CRITICAL_MINERAL_ASSET":
            supplies = ["RARE_EARTHS"]

    # 6. Threat Severity
    if action_code in ("PHYSICAL_STRIKE", "EXPLOSION_OR_FIRE") and target_code in (
        "CRUDE_OIL_TANKER", "LNG_GAS_CARRIER", "PORT_ENERGY_INFRA"
    ):
        threat_severity = "CRITICAL_DISRUPTION"
        threat_desc = "🚨 치명적 물리 공격 (실제 해운/에너지 인프라 파괴·피격)"
    elif action_code in ("PHYSICAL_STRIKE", "EXPLOSION_OR_FIRE", "SEIZURE_OR_BLOCKADE"):
        threat_severity = "HIGH_DISRUPTION"
        threat_desc = "⚠️ 고위험 교전·나포·봉쇄 (해상 통항 및 공급망 심각한 지연)"
    elif action_code in ("REGULATORY_SANCTION", "PRODUCTION_DISRUPTION"):
        threat_severity = "HIGH_REGULATORY_DISRUPTION"
        threat_desc = "📋 통상·규제 공급망 타격 (수출통제·생산중단·자산동결)"
    elif action_code == "MILITARY_EXERCISE":
        threat_severity = "ELEVATED_TENSION"
        threat_desc = "⚡ 군사 긴장 고조 (무력시위·군사훈련)"
    elif action_code == "DIPLOMATIC_NEGOTIATION":
        threat_severity = "MONITORING_DEESCALATION"
        threat_desc = "🕊️ 긴장 완화 / 외교적 해결 탐색"
    else:
        threat_severity = "MONITORING"
        threat_desc = "🔍 상시 모니터링 (잠재 위험 징후 추적)"

    return {
        "who": actor_label,
        "who_code": actor_code,
        "action": action_label,
        "action_code": action_code,
        "target": target_label,
        "target_code": target_code,
        "where": where_label,
        "when": published_at or "최근 관측 (Recent Observation)",
        "supply_impact_tags": supplies,
        "threat_severity": threat_severity,
        "threat_description": threat_desc,
    }


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
        # 클러스터 소속 기사들의 멀티모달(이미지·영상·PDF·외부카드) 첨부 및 Alt-Text 병합
        merged_attachments: List[Dict[str, str]] = []
        seen_media_urls: Set[str] = set()
        merged_alt_texts: List[str] = []
        merged_modalities: List[str] = []

        for a in c["articles"]:
            mm = a.get("_multimodal") or extract_multimodal_metadata(a)
            for att in mm.get("media_attachments", []):
                u_key = att.get("url", "")
                if u_key and u_key not in seen_media_urls and len(merged_attachments) < 10:
                    seen_media_urls.add(u_key)
                    merged_attachments.append(att)
            for alt_t in mm.get("visual_alt_texts", []):
                if alt_t and alt_t not in merged_alt_texts and len(merged_alt_texts) < 10:
                    merged_alt_texts.append(alt_t)
            for mod_t in mm.get("visual_modalities", []):
                if mod_t and mod_t not in merged_modalities:
                    merged_modalities.append(mod_t)

        combined_text = " ".join(
            f"{a.get('title', '')} {a.get('summary', '') or a.get('description', '')}"
            for a in c["articles"]
        )
        if merged_alt_texts:
            combined_text = f"{combined_text} {' '.join(merged_alt_texts)}"

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

        # 언어별 라벨링 (Language Labeling)
        article_langs = [
            (a.get("detected_language") or detect_language_detailed(a.get("title", ""))["language_code"])
            for a in c["articles"]
        ]
        lang_counts = Counter(article_langs)
        primary_lang = lang_counts.most_common(1)[0][0] if lang_counts else "en"
        unique_langs = sorted(list(set(article_langs)))
        is_cross_lingual = len(unique_langs) >= 2

        # NLP 정보추출(IE) 기반 5W1H 이벤트 튜플 생성
        event_tuple = extract_event_tuple(
            c["representative_title"],
            combined_text,
            entities,
            published_at=str(c.get("published_at", "")),
        )

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
            "primary_language": primary_lang,
            "detected_languages": unique_langs,
            "is_cross_lingual": is_cross_lingual,
            "purity_tier": purity_tier,
            "relevance_score": rel_score,
            "event_tuple": event_tuple,
            "chokepoints": entities["chokepoints"],
            "supply_chain_tags": entities["supply_chain_tags"],
            "event_types": entities["event_types"],
            "hotspot_regions": entities["hotspot_regions"],
            "has_visual_media": bool(merged_attachments or merged_modalities),
            "visual_modalities": merged_modalities,
            "media_attachments": merged_attachments,
            "visual_alt_texts": merged_alt_texts,
            "visual_verification_state": "UNVERIFIED_METADATA_ONLY",
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
    """다국어 통합 4단계 + 멀티모달 1단계 전처리: 미디어/Alt-Text 추출 및 시각노이즈 배제 → 노이즈 drop → 7개국어 정규화 → 중복 군집화 → 엔티티 태깅."""
    print(f"  [다국어+멀티모달 전처리 (mode={purity_mode})] 총 {len(raw_articles)}개 원시 기사 입력 수신.")

    clean_articles: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    reason_counts: Dict[str, int] = {}
    total_visual_noise_dropped = 0

    for a in raw_articles:
        mm = extract_multimodal_metadata(a)
        total_visual_noise_dropped += mm["dropped_visual_noise_count"]

        title = mm["clean_title"]
        summary_with_alt = mm["clean_summary"]
        if mm["visual_alt_texts"]:
            alt_joined = " ".join(mm["visual_alt_texts"])
            if alt_joined not in summary_with_alt:
                summary_with_alt = f"{summary_with_alt} {alt_joined}".strip()

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

        decision = classify_article(
            title,
            url,
            source,
            summary=summary_with_alt,
            purity_mode=purity_mode,
            lane=lane,
        )
        if decision["keep"]:
            enriched = dict(a)
            enriched["title"] = title
            enriched["summary"] = summary_with_alt
            enriched["url"] = url
            enriched["source"] = source
            enriched["detected_language"] = detect_language_detailed(f"{title} {summary_with_alt}")["language_code"]
            enriched["_multimodal"] = mm
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
    parser.add_argument(
        "--purity-mode",
        choices=["standard", "high"],
        default="standard",
        help="레인 브릿지 전처리 순도 모드 (기본 CLI는 bridge_preprocess_lanes 실행)",
    )
    args = parser.parse_args()
    if args.self_test:
        sys.exit(_run_self_test())

    # Default: run the lane bridge so collectors' data/* artifacts are processed.
    import runpy

    bridge = Path(__file__).resolve().parent.parent / "pipeline" / "bridge_preprocess_lanes.py"
    sys.argv = [str(bridge), f"--purity-mode={args.purity_mode}"]
    runpy.run_path(str(bridge), run_name="__main__")

