"""
prototype_all_in_one.py
========================
국제정세 분석 1차 프로토타입 (미국 소식 범위) — 파일 하나로 합친 버전.
원래 5개 파일(outlet_bias / issue_tagger / rss_fetch / ollama_client / pipeline)로
나눠서 만들었던 걸, 프로토타입 단계에서는 관리하기 번거로워서 한 파일로 합쳤다.
섹션별로 원래 파일명을 주석으로 남겨뒀으니, 나중에 다시 나눠도 그대로 옮기면 된다.

실행:
    pip install feedparser pandas requests
    python prototype_all_in_one.py              # 규칙 기반 태깅까지 (LLM 없이)
    python prototype_all_in_one.py --with-llm    # + Ollama 구조화추출/톤분류 (노트북에서 ollama serve 필요)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import pandas as pd
import requests

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"


# ============================================================
# [원래 outlet_bias.py] 출처 편향 태깅 — AllSides 데이터, 로컬 캐시
# ============================================================

ALLSIDES_CSV_URL = (
    "https://raw.githubusercontent.com/favstats/AllSideR/master/data/allsides_data.csv"
)
OUTLET_BIAS_CACHE = DATA_DIR / "outlet_bias.csv"

# 주의: AllSides는 같은 언론사도 'OO Editorial(오피니언)'과 'OO Online News(스트레이트 뉴스)'를
# 별개 항목으로 평가해둔 경우가 많다(등급이 서로 다름). RSS는 스트레이트 뉴스이므로
# 반드시 뉴스 쪽 항목으로 매핑해야 한다 - 아래는 8개 매체에 대해 직접 확인해서 맞춰둔 것.
DOMAIN_TO_ALLSIDES_NAME = {
    "npr.org": "NPR Online News",
    "bbci.co.uk": "BBC News",
    "bbc.co.uk": "BBC News",
    "bbc.com": "BBC News",
    "reuters.com": "Reuters",
    "apnews.com": "Associated Press",
    "foxnews.com": "Fox Online News",
    "cnn.com": "CNN (Web News)",
    "nytimes.com": "New York Times - News",
    "wsj.com": "Wall Street Journal - News",
}


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def refresh_outlet_bias_table(dest: Path = OUTLET_BIAS_CACHE) -> pd.DataFrame:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(ALLSIDES_CSV_URL, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    df = pd.read_csv(dest)
    print(f"[outlet_bias] {len(df)}개 언론사 편향 등급을 {dest}에 저장했습니다.")
    return df


class OutletBiasLookup:
    def __init__(self, csv_path: Path = OUTLET_BIAS_CACHE):
        self.csv_path = csv_path
        if not self.csv_path.exists():
            refresh_outlet_bias_table(self.csv_path)
        self.df = pd.read_csv(self.csv_path)
        self._by_name = {
            _normalize_name(str(row["news_source"])): row.to_dict()
            for _, row in self.df.iterrows()
            if str(row.get("news_source", "")) not in ("", "nan")
        }

    def get(self, source_url_or_domain: str) -> dict | None:
        domain = source_url_or_domain.lower().replace("www.", "").split("/")[0]
        # 실제 review_log.csv에서 확인된 문제: RSS 피드 URL의 도메인은
        # "feeds.npr.org", "feeds.bbci.co.uk"처럼 서브도메인이 붙어 있어서
        # 정확히 일치(==)하는 매핑만 찾던 이전 버전은 전부 놓쳤다.
        # -> 알려진 도메인으로 '끝나는지'(suffix)로 판단하도록 수정.
        mapped_name = None
        for known_domain, name in DOMAIN_TO_ALLSIDES_NAME.items():
            if domain == known_domain or domain.endswith("." + known_domain):
                mapped_name = name
                break
        if mapped_name:
            hit = self._by_name.get(_normalize_name(mapped_name))
            if hit:
                return hit
        return self._by_name.get(_normalize_name(source_url_or_domain))

    def tag_article(self, article: dict) -> dict:
        match = self.get(article.get("source_url", article.get("link", "")))
        article["outlet_bias"] = match.get("rating") if match else None
        article["outlet_bias_source"] = "AllSides" if match else "unmatched"
        return article


# ============================================================
# [원래 issue_tagger.py] 국가/이슈 태깅 — 규칙 기반 1차 분류
# ============================================================

@dataclass
class IssueDef:
    issue_id: str
    continent: str
    title: str
    countries: list[str]
    keywords: list[str]


COUNTRY_ALIASES = {
    "USA": ["united states", "u.s.", "us ", "washington", "white house", "trump administration"],
    "Canada": ["canada", "canadian", "ottawa"],
    "Mexico": ["mexico", "mexican"],
    # 2026-09-14: 나머지 18개 이슈 추가하면서 필요한 국가/지역 별칭도 같이 추가함.
    "Venezuela": ["venezuela", "venezuelan", "caracas", "maduro"],
    "Brazil": ["brazil", "brazilian", "brasilia", "lula"],
    "Argentina": ["argentina", "argentine", "buenos aires", "milei"],
    "Ukraine": ["ukraine", "ukrainian", "kyiv", "zelensky"],
    "Russia": ["russia", "russian", "moscow", "kremlin", "putin"],
    "Baltic States": ["estonia", "latvia", "lithuania", "baltic"],
    "Iran": ["iran", "iranian", "tehran"],
    "Israel": ["israel", "israeli", "jerusalem", "netanyahu", "idf"],
    "Palestine": ["palestine", "palestinian", "gaza", "west bank", "hamas"],
    "Saudi Arabia": ["saudi arabia", "saudi", "riyadh"],
    "Sudan": ["sudan", "sudanese", "khartoum", "darfur"],
    "Ethiopia": ["ethiopia", "ethiopian", "addis ababa", "tigray"],
    "DR Congo": ["congo", "drc", "kinshasa", "m23"],
    "North Korea": ["north korea", "pyongyang", "kim jong un", "dprk"],
    "Taiwan": ["taiwan", "taiwanese", "taipei"],
    "China": ["china", "chinese", "beijing"],
    "India": ["india", "indian", "new delhi", "modi"],
    "Pakistan": ["pakistan", "pakistani", "islamabad"],
    "Japan": ["japan", "japanese", "tokyo"],
    "South Korea": ["south korea", "seoul"],
    "Myanmar": ["myanmar", "burma", "burmese", "naypyidaw"],
}

# 대륙별_이슈_분석_프레임워크.md 원문 기준 이슈 목록. 참고: 이 문서 제목에는 "18개"라고
# 되어 있지만 실제로 나열된 항목은 21개(북미3/남미3/유럽3/중동3/아프리카3/아태6)다 — 원본
# 문서 자체의 숫자 오기로 보이며, 여기서는 실제로 나열된 21개를 전부 반영했다.
# issue_id 네이밍: 2026-09-13 컨트롤타워(③번) 트랙과 조율해서 na-N 대륙코드 스타일을 폐기하고
# 서술형(snake_case) 이름으로 통일함(ADR001_INTEGRATION_HANDOFF.md의 21개 매핑표 그대로 사용).
# keywords는 현재 영어 RSS(NPR/BBC)만 수집하므로 전부 영어로 작성함 — 다른 언어 피드를 추가하면
# 그 언어의 키워드도 추가해야 한다.
ISSUES: list[IssueDef] = [
    # 북미
    IssueDef("US_Canada_Trade", "북미", "미-캐 무역 및 이민 갈등", ["USA", "Canada"],
             ["tariff", "trade war", "border", "immigration", "usmca"]),
    IssueDef("US_Mexico_Migration", "북미", "미-멕 이민 및 마약 정책", ["USA", "Mexico"],
             ["border wall", "cartel", "fentanyl", "migrant", "asylum"]),
    IssueDef("Trump_Economy", "북미", "트럼프 미국 경제 정책", ["USA"],
             ["federal reserve", "inflation", "tax cut", "gdp", "unemployment", "trump"]),
    # 남미
    IssueDef("Venezuela_Crisis", "남미", "베네수엘라 정치-경제 위기", ["Venezuela"],
             ["migration", "refugee", "economic crisis", "sanctions", "maduro"]),
    IssueDef("Brazil_Politics", "남미", "브라질 정치 & 경제", ["Brazil"],
             ["election", "congress", "amazon", "bolsonaro", "lula"]),
    IssueDef("Argentina_Economy", "남미", "아르헨티나 경제 위기", ["Argentina"],
             ["inflation", "peso", "imf", "austerity", "milei"]),
    # 유럽
    IssueDef("Ukraine_War", "유럽", "우크라이나 전쟁", ["Ukraine", "Russia"],
             ["war", "invasion", "military aid", "ceasefire", "offensive"]),
    IssueDef("EU_Russia", "유럽", "EU-러시아 관계", ["Russia"],
             ["sanctions", "gas supply", "european union", "eu "]),
    IssueDef("Baltic_Security", "유럽", "북유럽 안보 (NATO 확대)", ["Baltic States", "Russia"],
             ["nato", "troop deployment", "baltic"]),
    # 중동
    IssueDef("Iran_Nuclear", "중동", "이란 핵협상 & 긴장", ["Iran"],
             ["nuclear program", "jcpoa", "enrichment", "irgc"]),
    IssueDef("Israel_Palestine", "중동", "이스라엘-팔레스타인", ["Israel", "Palestine"],
             ["gaza", "ceasefire", "hamas", "west bank"]),
    IssueDef("Middle_East_Energy", "중동", "중동 에너지 정책 (OPEC 영향)", ["Saudi Arabia"],
             ["opec", "oil production", "oil price", "energy policy"]),
    # 아프리카
    IssueDef("Sudan_Conflict", "아프리카", "수단 분쟁 (인도주의 위기)", ["Sudan"],
             ["civil war", "rsf", "paramilitary", "darfur", "humanitarian crisis"]),
    IssueDef("Ethiopia_Crisis", "아프리카", "에티오피아 정치 불안정", ["Ethiopia"],
             ["civil war", "famine", "political unrest", "tigray"]),
    IssueDef("Congo_Minerals", "아프리카", "콩고 분쟁 (광물 공급 불안)", ["DR Congo"],
             ["cobalt", "mineral", "conflict minerals", "mining", "m23"]),
    # 아시아-태평양
    IssueDef("North_Korea_Nuclear", "아태", "북한 핵 & 트럼프-김정은", ["North Korea"],
             ["nuclear test", "missile launch", "denuclearization"]),
    IssueDef("Taiwan_Strait", "아태", "대만 해협 긴장 (반도체 공급)", ["Taiwan", "China"],
             ["taiwan strait", "semiconductor", "tsmc", "reunification"]),
    IssueDef("India_Pakistan", "아태", "인도-파키스탄 (카슈미르 분쟁)", ["India", "Pakistan"],
             ["kashmir", "line of control", "border clash"]),
    IssueDef("South_China_Sea", "아태", "남중국해 영유권 (항행의 자유)", ["China"],
             ["south china sea", "spratly", "freedom of navigation"]),
    IssueDef("Japan_Korea", "아태", "일본-한국 관계 (경제 & 외교)", ["Japan", "South Korea"],
             ["trade dispute", "comfort women", "gsomia", "export controls"]),
    IssueDef("Myanmar_Crisis", "아태", "미얀마 정치 위기 (쿠데타 이후)", ["Myanmar"],
             ["coup", "junta", "military rule"]),
]


def _text_contains_any(text: str, phrases: list[str]) -> bool:
    text = text.lower()
    return any(p.lower() in text for p in phrases)


def match_countries(text: str) -> list[str]:
    return [c for c, aliases in COUNTRY_ALIASES.items() if _text_contains_any(text, aliases)]


def match_issues(text: str) -> list[IssueDef]:
    matched = []
    for issue in ISSUES:
        detected = match_countries(text)
        countries_ok = any(c in detected for c in issue.countries)
        keyword_ok = _text_contains_any(text, issue.keywords)
        if countries_ok and keyword_ok:
            matched.append(issue)
    return matched


def tag_article(article: dict) -> dict:
    """실제 review_log.csv를 받아보니, 0개 매칭(우리 18개 이슈랑 아예 무관한 기사 -
    Nicolas Cage 싱크홀, 호주 SNS 법안 등)과 2개 이상 매칭(진짜 애매해서 LLM 판단이
    필요한 경우)이 둘 다 llm_review_needed=True로 뭉뚱그려져 있었다.
    이러면 우리 범위 밖 기사까지 LLM한테 매번 물어보게 되어 비효율적이다.
    -> tag_status로 셋을 구분: matched(자동 확정) / ambiguous(LLM 판단 필요) /
       unclassified(우리 18개 이슈 범위 밖 - LLM 호출 없이 낮은 우선순위로 건너뜀).
    """
    text = f"{article.get('title', '')} {article.get('summary', '')}"
    countries = match_countries(text)
    issues = match_issues(text)
    article["countries_involved"] = countries
    article["issue_ids"] = [i.issue_id for i in issues]
    article["continent"] = issues[0].continent if len(issues) == 1 else None

    if len(issues) == 1:
        article["tag_status"] = "matched"
        article["llm_review_needed"] = False
    elif len(issues) >= 2:
        article["tag_status"] = "ambiguous"
        article["llm_review_needed"] = True
    else:
        article["tag_status"] = "unclassified"
        article["llm_review_needed"] = False  # 범위 밖 -> LLM 자원 아낌
    return article


# ============================================================
# [원래 rss_fetch.py] RSS 수집
# ============================================================

RSS_FEEDS = [
    "https://feeds.npr.org/1004/rss.xml",
    "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
]


def fetch_articles(feed_urls: list[str] | None = None) -> list[dict]:
    feed_urls = feed_urls or RSS_FEEDS
    articles = []
    for feed_url in feed_urls:
        parsed_feed = feedparser.parse(feed_url)
        if parsed_feed.bozo:
            print(f"[rss_fetch] 경고: {feed_url} 파싱 중 문제 발생 - {parsed_feed.bozo_exception}")
            continue
        source_domain = urlparse(feed_url).netloc.replace("www.", "")
        for entry in parsed_feed.entries:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source_url": source_domain,
                "language": "en",
            })
    print(f"[rss_fetch] 총 {len(articles)}건 수집")
    return articles


# ============================================================
# [원래 ollama_client.py] LLM 구조화 추출 + 톤 분류 (노트북 전용)
# ============================================================

OLLAMA_HOST = "http://localhost:11434"

MODEL_BY_LANGUAGE = {
    "en": "mistral",
    "ko": "exaone3.5:7.8b",
    "zh": "qwen2.5:7b",
    "ja": "dsasai/llama3-elyza-jp-8b",
    # cyberlis/saiga-mistral:7b-lora-q4_K는 구식 raw-completion 템플릿 방식이라
    # Ollama 0.34.0의 템플릿 파서와 호환이 안 돼 모든 요청에서 서버가 패닉하는 걸 확인
    # (2026-09-14, ollama serve 로그의 "interface conversion: parse.Node is nil" 스택트레이스로
    # 원인 규명). ChatML 스타일 템플릿을 쓰는 이 모델로 교체함 — 크래시는 해결됨, 지시 이해력은
    # 검증 중 (test_language_models.py로 확인).
    "ru": "wavecut/vikhr:7b-instruct_0.4-Q4_1",
    "ar": "hf.co/Solshine/jais-adapted-7b-chat-Q4_K_M-GGUF",
}

EXTRACTION_PROMPT = """다음 뉴스 기사를 읽고, 아래 JSON 형식으로만 답하시오. 설명이나 다른 텍스트는 쓰지 마시오.

기사 제목: {title}
기사 본문: {summary}

{{
  "key_facts": ["핵심 사실 1", "핵심 사실 2"],
  "quotes": ["기사에 등장하는 인용문 원문"],
  "countries_mentioned": ["언급된 국가명"],
  "date_mentioned": "기사에서 언급된 날짜 (없으면 빈 문자열)"
}}"""

# 라벨은 반드시 이 3개 영어 토큰 중 하나로만 받는다 (한국어 3글자 단어를 그대로 만들어내라고
# 하면 일부 언어 특화 모델(예: 일본어 모델)이 자국어로 답하거나, 능력이 부족한 모델(예: 아랍어
# 모델)이 프롬프트의 설명 문구 자체를 그대로 베껴 쓰는 문제가 실제로 발생했다 — 실제 노트북
# 테스트로 확인됨. 영어 고정 토큰 3개 중 하나만 고르게 하면 이 문제를 크게 줄일 수 있다.
# 최종적으로 사람이 보는 CSV에는 LABEL_EN_TO_KO로 한국어 라벨을 매핑해서 저장한다.
# 모델에 따라 정확히 지정한 3개 토큰 대신 흔한 동의어를 쓰는 경우가 실제로 확인됨
# (예: vikhr 모델이 critical 대신 negative를 씀) — 의미가 같은 동의어는 매핑해서 받아준다.
LABEL_EN_TO_KO = {
    "positive": "우호적",
    "favorable": "우호적",
    "neutral": "중립적",
    "neutrality": "중립적",
    "critical": "비판적",
    "negative": "비판적",
    "criticism": "비판적",
}

TONE_PROMPT = """다음 뉴스 기사의 논조를 분류하시오.

판단 기준은 딱 하나뿐이다: **이 기사의 문장이 특정 주체(정부·인물·기업·국가)의 행동·정책·
능력을 narrative(서술) 차원에서 비난하거나 부정적으로 평가하는 표현을 쓰는가?**
- 그렇다 → critical
- 아니다(사건·통계·예측·발표를 그대로 전달할 뿐이다) → neutral. **이때 그 사건 자체가 전쟁,
  관세, 물가 상승, 사망, 경제위기처럼 나쁜 소식이어도 상관없다 — "나쁜 소식 = critical"이 아니다.**
  "전문가들이 우려한다", "가격이 올랐다", "협상이 결렬됐다" 같은 문장은 그 자체로는 누구도
  비난하지 않으므로 neutral이다.
- positive는 특정 주체를 긍정적으로 평가하거나 띄워주는 서술일 때만 쓴다.
판단이 애매하면 neutral을 기본값으로 택할 것 (사실 전달형 기사가 뉴스의 다수이기 때문).

label 필드는 반드시 정확히 이 3개 단어 중 하나만 써야 한다: positive, neutral, critical.
그 외의 단어, 설명, 번역, 원문 복사는 절대 쓰지 말 것.

evidence_quote는 기사 제목/본문을 그대로 복사하지 말고, 판단에 실제로 영향을 준 특정 표현이나
단어를 짧게 뽑을 것. 원문에 마땅한 표현이 없으면 "특별한 편향 표현 없음, 사실 전달형"이라고 쓸 것.

--- 예시 입력/출력 (형식 참고용, 실제 판단은 아래 실제 기사에 대해서 할 것) ---
예시 1 (부정적 사건 + 예측 인용이지만 neutral — 실제로 여러 모델이 이 유형을 critical로
잘못 판단했던 사례이니 특히 주의할 것):
기사 제목: US raises tariffs on imports
기사 본문: The US government announced higher tariffs on imported goods. Analysts warn of
price increases.
출력: {{"label": "neutral", "evidence_quote": "특별한 편향 표현 없음, 사실 전달형"}}
(이유: 관세 인상과 물가 상승 우려라는 사건 자체는 부정적이지만, 이 문장은 정부의 발표와
애널리스트의 예측을 그대로 전달할 뿐 정부를 무능하다거나 잘못했다고 narrative적으로 평가하지
않는다.)

예시 2 (같은 소재라도 narrative적 비난이 들어가면 critical):
기사 제목: A상원의원, 예산안 협상 실패로 비판 직면
기사 본문: A상원의원의 무능한 협상 전략 탓에 예산안 협상이 결렬됐다는 비판이 나온다.
출력: {{"label": "critical", "evidence_quote": "무능한 협상 전략 탓이라는 비판"}}
(이유: "무능한"이라는 표현으로 특정 인물의 능력을 narrative적으로 깎아내리고 있다.)
--- 예시 끝 ---

이제 아래 실제 기사를 판단하시오.

기사 제목: {title}
기사 본문: {summary}

반드시 아래 JSON 형식으로만 답하시오 (label은 positive/neutral/critical 중 하나):
{{"label": "...", "evidence_quote": "..."}}"""


def _call_ollama(model: str, prompt: str, temperature: float = 0.3) -> dict:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature},
        },
        # 프롬프트에 few-shot 예시 2개를 추가한 뒤로 처리할 토큰 수가 늘어나서, CPU 환경의
        # 느린 모델(예: vikhr)이 120초 안에 못 끝내고 타임아웃 나는 경우가 실제로 확인됨 → 늘림.
        timeout=240,
    )
    resp.raise_for_status()
    return json.loads(resp.json()["response"])


def extract_structured(article: dict) -> dict:
    model = MODEL_BY_LANGUAGE.get(article.get("language", "en"), "mistral")
    prompt = EXTRACTION_PROMPT.format(title=article.get("title", ""), summary=article.get("summary", ""))
    article["llm_extraction"] = _call_ollama(model, prompt, temperature=0.3)
    return article


def classify_tone(article: dict) -> dict:
    model = MODEL_BY_LANGUAGE.get(article.get("language", "en"), "mistral")
    prompt = TONE_PROMPT.format(title=article.get("title", ""), summary=article.get("summary", ""))
    result = _call_ollama(model, prompt, temperature=0.3)
    raw_label = str(result.get("label", "")).strip().lower()
    # 모델이 정확히 positive/neutral/critical 중 하나를 안 쓰고 다른 걸 뱉으면(예: 프롬프트
    # 설명문 복사, 다른 언어로 번역 등) 한국어로 매핑하지 않고 raw 값을 그대로 남겨서
    # 2차 검수 때 "이 모델이 이번에도 형식을 못 지켰다"는 걸 바로 알아볼 수 있게 한다.
    article["llm_label"] = LABEL_EN_TO_KO.get(raw_label, f"[형식오류] {raw_label[:40]}")
    article["llm_evidence_quote"] = result.get("evidence_quote")
    return article


# ============================================================
# [원래 pipeline.py] 오케스트레이터 — 전체 흐름 연결 + CSV 저장
# ============================================================

REVIEW_LOG_PATH = DATA_DIR / "review_log.csv"

REVIEW_LOG_FIELDS = [
    "article_id", "language", "issue_ids", "continent", "countries_involved", "tag_status",
    "llm_review_needed", "source_type", "source_url", "outlet_bias", "title", "link",
    "llm_label", "llm_evidence_quote", "human_label", "correction_note", "reviewed_at", "collected_at",
]


def run(with_llm: bool = False, articles: list[dict] | None = None) -> list[dict]:
    articles = articles if articles is not None else fetch_articles()
    bias_lookup = OutletBiasLookup()

    rows = []
    for article in articles:
        article["article_id"] = str(uuid.uuid4())[:8]
        article["source_type"] = "news"
        article["collected_at"] = datetime.now(timezone.utc).isoformat()

        article = tag_article(article)
        article = bias_lookup.tag_article(article)

        # tag_status가 'unclassified'(우리 18개 이슈 범위 밖)인 기사는 LLM을 아예 부르지 않는다.
        # 실제 수집 결과(review_log.csv)를 보면 NPR+BBC 32건 중 27건이 여기 해당했다 -
        # 이걸 다 LLM에 태우면 7B 모델 기준 건당 15~45초씩 낭비하는 셈이라 자원 낭비가 크다.
        if with_llm and article["tag_status"] != "unclassified":
            try:
                article = extract_structured(article)
                article = classify_tone(article)
            except Exception as e:  # noqa: BLE001 - 프로토타입 단계의 방어적 처리
                print(f"[pipeline] LLM 처리 실패 ({article.get('title', '')[:30]}...): {e}")
                article["llm_label"] = None
                article["llm_evidence_quote"] = None
        else:
            article["llm_label"] = None
            article["llm_evidence_quote"] = None

        rows.append(article)

    _write_review_log(rows)
    return rows


def _write_review_log(rows: list[dict]) -> None:
    REVIEW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_LOG_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_LOG_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["human_label"] = ""
            row["correction_note"] = ""
            row["reviewed_at"] = ""
            writer.writerow(row)
    print(f"[pipeline] {len(rows)}건을 {REVIEW_LOG_PATH}에 저장했습니다. (2차 검수용)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-llm", action="store_true", help="Ollama 호출까지 실행 (노트북 전용)")
    args = parser.parse_args()
    run(with_llm=args.with_llm)
