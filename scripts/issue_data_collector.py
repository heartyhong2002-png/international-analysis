"""
Issue-Specific Data Collection Module
대륙별 이슈 분석을 위한 데이터 수집 스크립트

Data Sources:
- Wikipedia Pageviews: 이슈별 대중 관심도 (뉴스 기사량의 대체 지표)
- FRED: 경제 지표 (환율, 유가, 금리 등)
- OpenSanctions: 국제 제재 현황
- IMF IMTS: 국가 간 무역 데이터 (구 DOTS / UN Comtrade 대체, API 키 불필요)

Analysis Period: 2025.01 ~ 현재 (트럼프 취임 이후)

============================================================================
NOTE (수정 사항 v5 — GDELT 완전 제거, Wikipedia Pageviews로 교체):

v4까지 GDELT 타임아웃에 대해 타임아웃 최소값 강제 / 사전 연결 테스트 /
회로 차단기 / --resume 옵션까지 다 넣었지만, 최종적으로 원인이 코드가
아니라 **네트워크 자체**였던 것으로 확정됐습니다:

  - api.gdeltproject.org(Google Cloud 컴퓨트 인스턴스, 104.197.47.124)로
    가는 TCP 연결이 IPv4로도, VPN 없이도, 다른 네트워크(모바일 핫스팟)로도
    전부 타임아웃 (curl 테스트로 재현 확인)
  - 반면 같은 GDELT 프로젝트의 www./blog. 서브도메인, FRED, IMF API 등은
    전부 정상 작동 — GDELT API 서버(이 특정 GCP IP)로 가는 경로만 막힘
  - 여러 네트워크·여러 우회 수단으로도 뚫리지 않아, 사용자 판단 하에
    GDELT는 완전히 포기하고 대체 데이터 소스로 교체하기로 결정

**대체 데이터 소스: Wikipedia Pageviews API**
  - https://wikimedia.org/api/rest_v1/metrics/pageviews/...
  - API 키 불필요, 요청 제한 거의 없음, 2015년부터 일별 데이터 존재
  - "이슈에 대한 대중 관심도"의 프록시 지표로 학계에서도 실제 사용되는
    방법론 (위키백과 문서 조회수 ↔ 뉴스 기사량은 개념적으로 유사)
  - 이 네트워크에서 실제 브라우저로 검증 완료 (수단 내전 문서 7일간
    39,810회, 북핵 문서 3,757회 등 정상 데이터 확인)

동작 방식:
  1. 이슈 키워드 → Wikipedia 검색 API로 실제 존재하는 문서 찾기
  2. 리다이렉트를 최종 canonical 제목으로 정규화 (예: "Sudan civil war"
     검색 → "Sudanese civil war (2023–present)" 로 정규화)
  3. 그 문서의 일별 조회수를 Pageviews API로 수집
  4. 기존 calculate_issue_intensity()와 동일한 방식(최근 조회수 대비
     평균 배수)으로 이슈 강도 계산 — 다운스트림 코드는 거의 그대로 재사용

(GDELT용으로 만들었던 타임아웃 강제/회로 차단기/--resume 로직은 Wikipedia
API가 훨씬 안정적이라 대부분 불필요해졌지만, --resume 옵션 자체는 계속
유용해서 남겨뒀습니다.)
============================================================================
"""

import os
import sys
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from urllib.parse import quote
import requests
from dotenv import load_dotenv

# Windows 콘솔의 기본 인코딩(cp949)이 이모지/특수문자를 표현하지 못해
# UnicodeEncodeError가 나는 것을 방지하기 위해 UTF-8로 강제 설정합니다.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# Configuration
DATA_DIR = "data/issues"
os.makedirs(DATA_DIR, exist_ok=True)

RESUME_MODE = "--resume" in sys.argv

# API Keys
FRED_API_KEY = os.getenv("FRED_API_KEY")
# IMF DOTS는 API 키가 필요 없습니다
# OpenSanctions는 2025년경부터 모든 요청에 API 키가 필수로 바뀌었습니다.
# https://www.opensanctions.org/docs/api/ 에서 회원가입 후 발급받으세요.
# (언론/시민단체/학술 목적은 무료 키 발급 가능, 그 외에는 비즈니스 이메일로 가입 시 무료 체험 키 제공)
OPENSANCTIONS_API_KEY = os.getenv("OPENSANCTIONS_API_KEY")

# Issue Keywords (Wikipedia 문서 검색용 — 각 이슈를 대표하는 키워드 몇 개씩)
ISSUE_KEYWORDS = {
    # 북미 (North America)
    "US_Canada_Trade": ["US Canada trade war", "US Canada tariff", "USMCA renegotiation"],
    "US_Mexico_Migration": ["US Mexico border", "illegal immigration", "deportation"],
    "Trump_Economy": ["Trump economic policy", "tariffs", "trade war"],

    # 남미 (South America)
    "Venezuela_Crisis": ["Venezuela crisis", "Maduro government", "Venezuelan refugees"],
    "Brazil_Politics": ["Brazil politics", "Lula government", "Brazilian economy"],
    "Argentina_Economy": ["Argentina economy", "Milei government", "Argentine inflation"],

    # 유럽 (Europe)
    "Ukraine_War": ["Ukraine war", "Russia invasion", "NATO support"],
    "EU_Russia": ["EU Russia relations", "Russian sanctions", "energy crisis"],
    "Baltic_Security": ["Baltic NATO", "Russia military", "Nordic security"],

    # 중동 (Middle East)
    "Iran_Nuclear": ["Iran nuclear", "Iran enrichment", "Iranian sanctions"],
    "Israel_Palestine": ["Israel Palestine", "Gaza", "Hamas conflict"],
    "Middle_East_Energy": ["OPEC oil", "Saudi Arabia", "energy policy"],

    # 아프리카 (Africa)
    "Sudan_Conflict": ["Sudan conflict", "Sudanese refugees", "humanitarian crisis"],
    "Ethiopia_Crisis": ["Ethiopia politics", "Ethiopian conflict", "political instability"],
    "Congo_Minerals": ["Congo conflict", "minerals supply", "cobalt coltan"],

    # 아시아 (Asia-Pacific)
    "North_Korea_Nuclear": ["North Korea nuclear", "Kim Jong Un", "Trump Kim"],
    "Taiwan_Strait": ["Taiwan China military", "Taiwan strait", "semiconductor security"],
    "India_Pakistan": ["India Pakistan", "Kashmir", "terrorism"],
    "South_China_Sea": ["South China Sea", "China military", "freedom of navigation"],
    "Japan_Korea": ["Japan Korea relations", "East Asian tensions"],
    "Myanmar_Crisis": ["Myanmar coup", "Myanmar conflict", "Burmese refugees"],
}

# ============================================================================
# 1. Wikipedia Pageviews - 이슈별 대중 관심도 (GDELT 대체)
# ============================================================================

WIKI_SEARCH_API = "https://en.wikipedia.org/w/api.php"
WIKI_PAGEVIEWS_API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
# Wikimedia는 API 호출 시 식별 가능한 User-Agent를 요구합니다.
# (https://meta.wikimedia.org/wiki/User-Agent_policy)
WIKI_USER_AGENT = "international-affairs-research-project/1.0 (educational/personal geopolitical analysis)"
# NOTE (수정 사항 v5.1): 첫 실행에서 0.3초 간격으로 돌렸더니 중간부터
# 위키미디어가 429(Too Many Requests)를 뱉기 시작했고, 그걸 아래
# resolve_wikipedia_title()의 뭉뚱그린 except가 "문서 없음"으로 잘못
# 캐싱해버리는 바람에 Ukraine war, Gaza, North Korea nuclear처럼 명백히
# 존재하는 문서들까지 전부 "no_matching_article"로 잘못 기록됐습니다.
# -> 간격을 늘리고, 429는 별도로 감지해서 Retry-After(또는 백오프)만큼
#    기다렸다가 재시도하도록 고쳤습니다.
WIKI_REQUEST_DELAY_SEC = 1.0
WIKI_MAX_RETRIES = 4

_wiki_title_cache = {}  # 같은 키워드를 여러 이슈에서 재사용할 때 중복 검색 방지 (성공한 경우만 캐싱)
_wiki_failed_keywords = []  # [{"issue":..., "keyword":..., "reason":...}, ...]


def _wiki_request(url, params=None, timeout=20):
    """
    공통 요청 헬퍼.
    - 타임아웃/연결 오류: 짧게 재시도
    - HTTP 429: Retry-After 헤더(있으면 그 값, 없으면 지수 백오프)만큼 기다렸다가 재시도
    - 그 외 상태 코드는 그대로 반환 (호출부에서 판단)
    """
    last_err = None
    for attempt in range(1, WIKI_MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": WIKI_USER_AGENT}, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            if attempt < WIKI_MAX_RETRIES:
                time.sleep(2 * attempt)
            continue

        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else min(5 * (2 ** (attempt - 1)), 60)
            except ValueError:
                wait = min(5 * (2 ** (attempt - 1)), 60)
            if attempt < WIKI_MAX_RETRIES:
                print(f"  ⏳ Wikipedia 429(요청 과다) - {wait:.0f}초 후 재시도 ({attempt}/{WIKI_MAX_RETRIES})")
                time.sleep(wait)
                continue
            last_err = requests.exceptions.HTTPError(f"429 Too Many Requests (재시도 {WIKI_MAX_RETRIES}회 소진)")
            continue

        return r  # 200, 404 등 — 호출부에서 처리

    raise last_err if last_err else RuntimeError("Wikipedia 요청이 원인 불명으로 실패했습니다")


def resolve_wikipedia_title(query):
    """
    검색어 → 실제 존재하는 위키백과 문서의 canonical 제목으로 정규화.

    단순히 opensearch(자동완성)만 쓰면 리다이렉트 문서나 특수문자(en-dash 등)
    차이로 조회수 API가 404를 내는 경우가 많아, 다음 두 단계를 거칩니다:
      1) action=query&list=search 로 실제 존재하는 문서 찾기
      2) action=query&redirects=1 로 리다이렉트를 최종 제목으로 정규화

    Returns:
        (title, reason): title은 성공 시 문자열, 실패 시 None.
        reason은 실패했을 때만 채워지며 "no_matching_article"(진짜로 문서가
        없음) 과 그 외 에러 메시지(요청 실패 등)를 구분합니다.
        실패가 요청 오류일 때는 캐싱하지 않아 다음 실행(--resume)에서
        다시 시도할 수 있습니다.
    """
    if query in _wiki_title_cache:
        cached = _wiki_title_cache[query]
        return cached, (None if cached is not None else "no_matching_article")

    return _resolve_wikipedia_title_impl(query, depth=0)


def _mw_api_error_code(json_body):
    """
    MediaWiki action API는 요청 제한(rate limit)에 걸려도 HTTP 상태 코드는
    200을 그대로 주고, 본문에 {"error": {"code": "ratelimited", ...}} 형태로만
    에러를 표시합니다. status_code만 보면 절대 못 잡아내고, hits가 그냥
    비어있는 것처럼 보여서 "문서 없음"으로 오분류하게 됩니다.
    이 헬퍼가 그 API 레벨 에러 코드를 뽑아냅니다 (없으면 None).
    """
    if not isinstance(json_body, dict):
        return None
    return json_body.get("error", {}).get("code")


def _resolve_wikipedia_title_impl(query, depth=0):
    """
    NOTE (수정 사항 v5.2 — 'Gaza', 'Ukraine war', 'North Korea nuclear'처럼
    명백히 존재하는 문서들까지 전부 no_matching_article로 잘못 기록되던 문제
    원인 파악:
      1) list=search(전문 검색) API는 익명 사용자에게 훨씬 엄격한 자체
         요청 제한(rate limit)이 걸려 있는데, 이 제한에 걸려도 HTTP 200 +
         본문에 {"error":{"code":"ratelimited"}}로만 응답합니다. 기존 코드는
         status_code만 봤기 때문에 이걸 못 잡고 "검색 결과 없음"으로 처리했습니다.
      2) 기숙사 공유기(CGNAT, 같은 IP를 여러 명이 공유)라서 이 제한에 훨씬
         빨리 걸렸을 가능성이 높습니다.

    수정: (a) list=search보다 훨씬 관대한 '직접 제목 조회'를 먼저 시도하고
    (실제로 "Gaza", "North Korea" 등은 이걸로 바로 성공), 그게 안 맞을 때만
    검색으로 폴백. (b) 200 응답이어도 본문의 API 에러 코드를 확인해서
    rate limit이면 문서없음이 아니라 재시도 대상으로 처리.
    """
    try:
        # 1) 직접 제목 조회 먼저 (list=search 대비 요청 제한이 훨씬 느슨함)
        r_direct = _wiki_request(WIKI_SEARCH_API, params={
            "action": "query", "titles": query, "redirects": 1, "format": "json",
        })
        if r_direct.status_code == 200:
            body = r_direct.json()
            err = _mw_api_error_code(body)
            if err:
                if "limit" in err.lower() and depth < 2:
                    wait = 10 * (depth + 1)
                    print(f"  ⏳ Wikipedia API 요청 제한(직접 조회) - {wait}초 후 재시도")
                    time.sleep(wait)
                    return _resolve_wikipedia_title_impl(query, depth=depth + 1)
                if "limit" not in err.lower():
                    return None, f"api_error_{err}"
            else:
                pages = list(body.get("query", {}).get("pages", {}).values())
                direct_hit = next((p for p in pages if "missing" not in p), None)
                if direct_hit:
                    resolved = direct_hit["title"]
                    _wiki_title_cache[query] = resolved
                    return resolved, None
        # 직접 조회가 안 맞으면(비-200 또는 missing) 검색으로 폴백

        # 2) 검색 API 폴백 (요청 제한이 더 엄격하므로 추가로 대기)
        time.sleep(WIKI_REQUEST_DELAY_SEC)
        r = _wiki_request(WIKI_SEARCH_API, params={
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": 1, "format": "json",
        })
        if r.status_code != 200:
            return None, f"search_http_{r.status_code}"

        body = r.json()
        err = _mw_api_error_code(body)
        if err:
            if "limit" in err.lower() and depth < 2:
                wait = 15 * (depth + 1)
                print(f"  ⏳ Wikipedia API 요청 제한(검색) - {wait}초 후 재시도")
                time.sleep(wait)
                return _resolve_wikipedia_title_impl(query, depth=depth + 1)
            return None, f"api_error_{err}"

        hits = body.get("query", {}).get("search", [])
        if not hits:
            _wiki_title_cache[query] = None  # 진짜로 문서가 없는 경우만 캐싱
            return None, "no_matching_article"
        candidate = hits[0]["title"]

        r2 = _wiki_request(WIKI_SEARCH_API, params={
            "action": "query", "titles": candidate, "redirects": 1, "format": "json",
        })
        if r2.status_code != 200:
            return None, f"redirect_http_{r2.status_code}"

        pages = list(r2.json().get("query", {}).get("pages", {}).values())
        resolved = pages[0]["title"] if pages else candidate

        _wiki_title_cache[query] = resolved
        return resolved, None

    except Exception as e:
        # 요청 자체가 실패한 경우(타임아웃, 429 소진 등) — 캐싱하지 않음
        return None, str(e)[:150]


def fetch_wikipedia_interest(keywords, days_back=30, issue_name=""):
    """
    키워드별로 위키백과 문서를 찾아 일별 조회수(대중 관심도)를 수집.

    GDELT의 fetch_gdelt_sentiment()와 동일한 출력 스키마를 유지해서,
    calculate_issue_intensity() 등 하위 로직을 그대로 재사용합니다.

    Args:
        keywords (list): 검색 키워드
        days_back (int): 며칠 전부터 수집할 것인가
        issue_name (str): 실패 로그 기록용 이슈 이름

    Returns:
        pd.DataFrame: 컬럼 = date, keyword, wiki_title, article_count(=조회수), timestamp
    """
    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    start_str, end_str = start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

    for keyword in keywords:
        time.sleep(WIKI_REQUEST_DELAY_SEC)
        title, reason = resolve_wikipedia_title(keyword)
        if not title:
            if reason == "no_matching_article":
                print(f"  ⚠ Wikipedia: '{keyword}'에 해당하는 문서를 찾지 못함 (건너뜀)")
            else:
                print(f"  ✗ Wikipedia: '{keyword}' 제목 조회 실패 - {reason} (건너뜀, 재시도 가능)")
            _wiki_failed_keywords.append({
                "issue": issue_name, "keyword": keyword, "reason": reason or "unknown_error"
            })
            continue

        encoded_title = quote(title.replace(" ", "_"), safe="")
        url = f"{WIKI_PAGEVIEWS_API}/en.wikipedia/all-access/user/{encoded_title}/daily/{start_str}/{end_str}"

        try:
            time.sleep(WIKI_REQUEST_DELAY_SEC)
            r = _wiki_request(url)

            if r.status_code == 404:
                print(f"  ⚠ Wikipedia: '{title}' 조회수 데이터 없음 (건너뜀)")
                _wiki_failed_keywords.append({
                    "issue": issue_name, "keyword": keyword, "reason": f"no_pageview_data: {title}"
                })
                continue
            r.raise_for_status()

            items = r.json().get("items", [])
            for it in items:
                ts_str = it.get("timestamp", "")[:8]
                try:
                    ts = datetime.strptime(ts_str, "%Y%m%d")
                except ValueError:
                    continue
                results.append({
                    "date": ts_str,
                    "keyword": keyword,
                    "wiki_title": title,
                    "article_count": it.get("views", 0),  # 이름은 유지하되 실제로는 '일별 조회수'
                    "timestamp": ts,
                })

            print(f"✓ Wikipedia: {keyword} → '{title}' - {len(items)}일치 조회수 수집")

        except Exception as e:
            print(f"✗ Wikipedia Error ({keyword} → {title}): {str(e)[:150]}")
            _wiki_failed_keywords.append({
                "issue": issue_name, "keyword": keyword, "reason": str(e)[:150]
            })

    if results:
        df = pd.DataFrame(results)
        return df.sort_values("timestamp")
    else:
        return pd.DataFrame()


def calculate_issue_intensity(df_interest):
    """
    조회수(구 GDELT 기사 수)로부터 이슈 강도 지수 계산 (0-100)

    기간별 관심도를 정규화하여 이슈의 강도 평가
    """
    if df_interest.empty:
        return 0

    # 최근 7일 관심도
    recent = df_interest['article_count'].tail(7).sum()

    # 전체 기간 평균 대비 배수
    avg = df_interest['article_count'].mean()

    if avg == 0:
        intensity = 0
    else:
        intensity = min(100, (recent / avg) * 50)  # 최대 100

    return intensity


# ============================================================================
# 2. FRED Economic Indicators
# ============================================================================

def fetch_fred_issue_indicators():
    """
    이슈 분석을 위한 경제 지표 수집

    포함 지표:
    - 유가 (WTI): 중동 이슈 연관
    - 환율: 각국 경제 상황
    - 금리: 미국 정책 영향
    - 에너지: 유럽-러시아 관계
    """

    indicators = {
        # 유가 (에너지)
        "DCOILWTICO": "WTI Oil Price",           # 중동 이슈
        "GASDESW": "US Gas Price",              # 에너지 정책

        # 환율
        "DEXUSEU": "USD/EUR",                   # 유럽 경제
        "DEXCHUS": "USD/CNY",                   # 중국 경제
        "DEXJPUS": "USD/JPY",                   # 일본/한국 경제
        "DEXMXUS": "USD/MXN",                   # 멕시코 경제
        "DEXBZUS": "USD/BRL",                   # 브라질 경제

        # 금리
        "DGS10": "10-Year US Treasury Yield",    # 미국 정책 금리
        "UNRATE": "US Unemployment Rate",        # 경제 상황

        # 주가
        "SP500": "S&P 500 Index",               # 미국 시장 심리도

        # NOTE: 기존에 있던 "MMNRNUST"(Global Trade Index)는 FRED에 존재하지
        # 않는 시리즈 ID로 확인되어 제거했습니다. FRED에는 "글로벌 무역"을
        # 나타내는 단일 통합 지표가 없으며, 국가 간 무역액은 4번(IMF DOTS)에서
        # 별도로 수집합니다.
    }

    data = {}

    for series_id, name in indicators.items():
        try:
            # NOTE: 기존 코드는 "fred/series/data"였는데 이는 존재하지 않는
            # 엔드포인트입니다(항상 404). FRED 공식 문서 기준 실제 관측치를
            # 가져오는 엔드포인트는 "fred/series/observations"입니다.
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "limit": 90,  # 최근 90일
            }

            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                result = response.json()

                if "observations" in result:
                    observations = result["observations"]
                    dates = [obs["date"] for obs in observations]
                    values = [float(obs["value"]) if obs["value"] != "." else np.nan
                             for obs in observations]

                    data[name] = {
                        "dates": dates,
                        "values": values
                    }

                    print(f"✓ FRED: {name} - {len(observations)} observations")
            else:
                # 이전에는 실패 시(주로 잘못된 API 키) 아무 메시지도 출력되지
                # 않고 조용히 건너뛰어서 원인 파악이 어려웠습니다.
                print(f"✗ FRED Error ({name}): HTTP {response.status_code} - {response.text[:200]}")

        except Exception as e:
            print(f"✗ FRED Error ({name}): {str(e)}")

    return data


# ============================================================================
# 3. OpenSanctions - 국제 제재 현황
# ============================================================================

def fetch_sanctions_data():
    """
    OpenSanctions에서 현재 제재 대상 국가/개인 수집

    NOTE (수정 사항):
    1. 기존 URL "https://api.opensanctions.org/matches"는 존재하지 않는
       엔드포인트입니다. 공식 문서 기준 검색용 엔드포인트는
       "/search/<dataset>" (기본 데이터셋은 "default")입니다.
    2. OpenSanctions는 현재 모든 요청에 API 키를 요구합니다
       (Authorization: ApiKey <키> 헤더). 키가 없으면 이전에는 이유도 없이
       그냥 데이터가 0으로만 채워졌는데, 이제는 명확히 에러를 출력합니다.
       https://www.opensanctions.org/docs/api/ 에서 무료로 발급받아
       .env 파일에 OPENSANCTIONS_API_KEY=... 로 넣어주세요.
    """
    if not OPENSANCTIONS_API_KEY:
        print("✗ OpenSanctions: OPENSANCTIONS_API_KEY가 .env에 없어 건너뜁니다. "
              "https://www.opensanctions.org/docs/api/ 에서 무료 키를 발급받으세요.")
        return {
            country: {"count": None, "last_update": None, "status": "missing_api_key"}
            for country in ["Iran", "Russia", "North Korea", "Venezuela", "Syria"]
        }

    url = "https://api.opensanctions.org/search/default"
    headers = {"Authorization": f"ApiKey {OPENSANCTIONS_API_KEY}"}

    # OpenSanctions 검색은 국가명을 별도 필터가 아닌 자유 검색어(q)로 받는 것이
    # 문서상 확실히 보장된 방식이라, ISO2 국가코드도 함께 시도하되 q로도 검색합니다.
    sanction_countries = {
        "Iran": {"iso2": "ir", "count": 0, "last_update": None},
        "Russia": {"iso2": "ru", "count": 0, "last_update": None},
        "North Korea": {"iso2": "kp", "count": 0, "last_update": None},
        "Venezuela": {"iso2": "ve", "count": 0, "last_update": None},
        "Syria": {"iso2": "sy", "count": 0, "last_update": None},
    }

    for country, info in sanction_countries.items():
        try:
            params = {
                "q": country,
                "countries": info["iso2"],  # 지원되지 않으면 무시되고 q만 적용됩니다
                "limit": 10,
            }

            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                result = response.json()
                # 응답 스키마가 top-level "total" 또는 "results" 배열일 수 있어 둘 다 대응합니다.
                if isinstance(result.get("total"), dict):
                    count = result["total"].get("value", 0)
                else:
                    count = result.get("total") or len(result.get("results", []))

                sanction_countries[country]["count"] = count
                sanction_countries[country]["last_update"] = datetime.now().isoformat()

                print(f"✓ Sanctions: {country} - {sanction_countries[country]['count']} sanctioned entities")
            else:
                print(f"✗ Sanctions Error ({country}): HTTP {response.status_code} - {response.text[:200]}")

        except Exception as e:
            print(f"✗ Sanctions Error ({country}): {str(e)}")

    return sanction_countries


# ============================================================================
# 4. IMF IMTS - 국가 간 무역 데이터 (구 DOTS / UN Comtrade 대체)
# ============================================================================
#
# NOTE (수정 사항 v4 — IMF API 이전):
# 기존에 쓰던 http://dataservices.imf.org/REST/SDMX_JSON.svc/... 는 IMF가
# 서비스를 폐지해서 이제 DNS 조회조차 실패합니다
# ("Failed to resolve 'dataservices.imf.org'"). 이건 우리 네트워크 문제가
# 아니라 IMF가 서버를 내린 것입니다.
#
# IMF는 새 SDMX 3.0 API(api.imf.org)로 이전했고, 구 DOTS(Direction of Trade
# Statistics)에 해당하는 데이터셋은 이제 IMTS(International Trade in Goods
# by partner country)입니다. 실제 응답을 확인해서 아래를 검증했습니다:
#
#   - 엔드포인트: https://api.imf.org/external/sdmx/3.0/data/dataflow/
#                 IMF.STA/IMTS/1.0.0/{국가}.{지표}.{상대국}.{빈도}
#   - 국가 코드: ISO3 그대로 사용 (KOR, CHN, USA...) — 예전처럼 IMF 2자리
#                코드로 변환할 필요가 없어졌습니다
#   - 지표 코드: XG_FOB_USD(수출), MG_CIF_USD(수입), TBG_USD(무역수지)
#                ※ 예전 TXG_FOB_USD / TMG_CIF_USD 에서 이름이 바뀌었습니다
#   - 빈도: A(연간), Q(분기), M(월간)
#   - CSV 응답(Accept: application/vnd.sdmx.data+csv)이 JSON보다 파싱이
#     훨씬 단순해서 CSV를 씁니다
#   - startPeriod 파라미터는 무시되는 것으로 확인되어, 받아온 뒤 연도로
#     직접 필터링합니다
#   - OBS_VALUE는 배율 없는 실제 USD 금액입니다
#     (검증: 2024년 KOR->CHN 수출 = 132,902,972,288 USD ≈ 1,329억 달러)

IMF_API_BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/IMTS/1.0.0"

# 새 API는 ISO3 코드를 그대로 받으므로 별도 매핑이 필요 없습니다.
IMF_INDICATORS = {
    "exports": "XG_FOB_USD",   # 수출 (FOB, USD)
    "imports": "MG_CIF_USD",   # 수입 (CIF, USD)
    "balance": "TBG_USD",      # 무역수지 (USD)
}


def fetch_imf_trade_data(reporter, partner, start_year, end_year, freq="A"):
    """
    IMF IMTS API로 양국 간 무역 데이터 조회 (수출/수입 동시 조회)

    Args:
        reporter (str): 보고국 ISO3 코드 (예: "KOR")
        partner (str): 상대국 ISO3 코드 (예: "CHN")
        start_year (int): 조회 시작 연도
        end_year (int): 조회 종료 연도
        freq (str): 빈도 - "A"(연간), "Q"(분기), "M"(월간)

    Returns:
        list[dict]: [{"year", "indicator", "flow", "value_usd"}, ...] (실패 시 None)
    """
    import io

    # 수출+수입을 한 번에 요청 ("+"로 여러 지표를 묶을 수 있습니다)
    indicators = f"{IMF_INDICATORS['exports']}+{IMF_INDICATORS['imports']}"
    url = f"{IMF_API_BASE}/{reporter}.{indicators}.{partner}.{freq}"

    try:
        response = requests.get(
            url,
            headers={"Accept": "application/vnd.sdmx.data+csv"},
            timeout=30,
        )
        if response.status_code != 200:
            print(f"  ✗ IMF Error ({reporter}->{partner}): HTTP {response.status_code}")
            return None

        df = pd.read_csv(io.StringIO(response.text))
        if df.empty or "TIME_PERIOD" not in df.columns:
            print(f"  ✗ IMF Error ({reporter}->{partner}): 응답에 데이터 없음")
            return None

        # startPeriod가 무시되므로 여기서 직접 연도 필터링
        df["_year"] = pd.to_numeric(df["TIME_PERIOD"].astype(str).str[:4], errors="coerce")
        df = df[(df["_year"] >= start_year) & (df["_year"] <= end_year)]

        flow_name = {v: k for k, v in IMF_INDICATORS.items()}
        records = []
        for _, row in df.iterrows():
            records.append({
                "year": int(row["_year"]),
                "indicator": row["INDICATOR"],
                "flow": flow_name.get(row["INDICATOR"], row["INDICATOR"]),
                "value_usd": float(row["OBS_VALUE"]),
            })
        return records if records else None

    except Exception as e:
        print(f"  ✗ IMF Error ({reporter}->{partner}): {str(e)}")
        return None


# 구버전 이름으로 호출하던 코드와의 호환용 별칭
fetch_imf_dots_trade_data = fetch_imf_trade_data


def fetch_critical_trade_pairs():
    """
    주요 이슈 관련 국가 간 무역 데이터 수집 (IMF IMTS 경유)

    예:
    - 미-중 무역 (대만 해협 / 미중 갈등)
    - 러-유럽 에너지 무역 (우크라이나)
    - 이란 석유 수출 (이란 제재)
    """

    # 분석할 무역 쌍 (ISO3 코드 — 새 IMF API가 ISO3를 그대로 받습니다)
    trade_pairs = [
        # (보고국, 상대국, 설명)
        ("USA", "CHN", "US-China Trade"),
        ("RUS", "USA", "Russia-US Trade"),
        ("IRN", "CHN", "Iran-China Oil Trade"),
        ("RUS", "DEU", "Russia-EU(Germany) Energy"),
        ("CHN", "RUS", "China-Russia Trade"),
        ("KOR", "USA", "Korea-US Trade"),
        ("KOR", "CHN", "Korea-China Trade"),
    ]

    trade_data = {}
    end_year = datetime.now().year
    start_year = end_year - 2  # 최근 2~3년

    for reporter, partner, desc in trade_pairs:
        records = fetch_imf_trade_data(reporter, partner, start_year, end_year)

        if records:
            trade_data[f"{reporter}_{partner}"] = {
                "description": desc,
                "data": records,
                "years": f"{start_year}-{end_year}",
            }
            # 가장 최근 연도의 수출/수입을 한 줄로 보여줍니다
            latest_year = max(r["year"] for r in records)
            latest = {r["flow"]: r["value_usd"] for r in records if r["year"] == latest_year}
            parts = []
            if "exports" in latest:
                parts.append(f"수출 ${latest['exports']/1e9:.1f}B")
            if "imports" in latest:
                parts.append(f"수입 ${latest['imports']/1e9:.1f}B")
            detail = f" [{latest_year}: {', '.join(parts)}]" if parts else ""
            print(f"  ✓ Trade Pair: {desc} - {len(records)}건 수집{detail}")
        else:
            trade_data[f"{reporter}_{partner}"] = {
                "description": desc,
                "data": None,
                "years": f"{start_year}-{end_year}",
                "status": "failed",
            }
            print(f"  ⚠ Trade Pair: {desc} - 수집 실패 (건너뜀)")

    # v4: 무역 데이터를 CSV로도 저장 (리포트에서 바로 쓸 수 있도록)
    rows = []
    for pair_key, info in trade_data.items():
        if not info.get("data"):
            continue
        for rec in info["data"]:
            rows.append({
                "pair": pair_key,
                "description": info["description"],
                "year": rec["year"],
                "flow": rec["flow"],
                "value_usd": rec["value_usd"],
            })
    if rows:
        trade_df = pd.DataFrame(rows)
        trade_path = f"{DATA_DIR}/imf_trade_pairs.csv"
        trade_df.to_csv(trade_path, index=False)
        print(f"  ✓ 무역 데이터 저장: {trade_path} ({len(rows)}행)")

    return trade_data


# ============================================================================
# 5. Issue Analysis Summary
# ============================================================================

def generate_issue_summary(issue_name, keywords):
    """
    각 이슈에 대한 종합 분석 요약 생성
    """

    csv_path = f"{DATA_DIR}/{issue_name}_wikipedia_30days.csv"

    # --resume 모드에서는 이미 저장된 CSV가 있으면 건너뛰어서, 중간에
    # 끊긴 실행을 처음부터 다시 돌리지 않고 이어서 할 수 있게 합니다.
    if RESUME_MODE and os.path.exists(csv_path):
        print(f"\n⏭  {issue_name}: 기존 CSV 발견, 건너뜀 (--resume 모드) -> {csv_path}")
        df_existing = pd.read_csv(csv_path)
        intensity = calculate_issue_intensity(df_existing) if not df_existing.empty else 0
        return {
            "issue": issue_name,
            "intensity": intensity,
            "article_count": df_existing['article_count'].sum() if not df_existing.empty else 0,
            "last_updated": datetime.now().isoformat()
        }

    print(f"\n{'='*60}")
    print(f"📊 Issue Analysis: {issue_name}")
    print(f"{'='*60}")

    # Wikipedia 문서 조회수 (GDELT 뉴스 기사량의 대체 지표)
    df_interest = fetch_wikipedia_interest(keywords, days_back=30, issue_name=issue_name)
    intensity = calculate_issue_intensity(df_interest)

    # 요약 통계
    if not df_interest.empty:
        print(f"\n📰 Interest Analysis (Wikipedia Pageviews):")
        print(f"   - Total Views (30 days): {df_interest['article_count'].sum()}")
        print(f"   - Daily Average: {df_interest['article_count'].mean():.1f}")
        print(f"   - Issue Intensity: {intensity:.1f}/100", end="")

        if intensity < 30:
            print(" (낮음)")
        elif intensity < 60:
            print(" (중간)")
        else:
            print(" (높음) 🔴")

    # CSV로 저장
    if not df_interest.empty:
        df_interest.to_csv(csv_path, index=False)
        print(f"   - Data saved: {csv_path}")

    return {
        "issue": issue_name,
        "intensity": intensity,
        "article_count": df_interest['article_count'].sum() if not df_interest.empty else 0,
        "last_updated": datetime.now().isoformat()
    }


def retry_failed_wikipedia_keywords(issue_summaries):
    """
    NOTE (수정 사항 v5.2 — 자동 재시도):
    1차 수집에서 실패한 키워드 중, 문서가 진짜로 없는 경우("no_matching_article")
    는 제외하고, 요청 오류(429, API rate limit, 타임아웃 등)로 실패한 것만
    모아서 잠시 대기한 뒤 자동으로 한 번 더 시도합니다.

    사용자가 매번 --resume을 손으로 다시 돌리지 않아도, 한 번 실행으로
    최대한 많은 이슈의 데이터를 채우는 게 목적입니다. (그래도 재시도 후
    남는 실패는 여전히 --resume으로 다시 시도 가능합니다.)
    """
    retryable = [
        f for f in _wiki_failed_keywords
        if f["reason"] != "no_matching_article"
        and not str(f["reason"]).startswith("no_pageview_data")
    ]
    if not retryable:
        return issue_summaries

    print(f"\n{'='*60}")
    print(f"🔁 자동 재시도: 요청 오류로 실패한 키워드 {len(retryable)}개")
    print(f"   (문서가 진짜 없는 건 재시도하지 않습니다)")
    print(f"{'='*60}")
    print("   30초 대기 후 재시도합니다 (Wikipedia 요청 제한이 풀릴 시간을 줍니다)...")
    time.sleep(30)

    # 재시도할 (issue, keyword) 쌍은 실패 목록에서 먼저 제거해두고,
    # 재시도 결과(성공 or 재실패)로 다시 채웁니다. 그래야 최종
    # _wiki_failed_keywords가 "재시도 후에도 진짜 실패한 것"만 남습니다.
    retry_pairs = {(f["issue"], f["keyword"]) for f in retryable}
    _wiki_failed_keywords[:] = [
        f for f in _wiki_failed_keywords if (f["issue"], f["keyword"]) not in retry_pairs
    ]

    by_issue = {}
    for issue_name, keyword in retry_pairs:
        by_issue.setdefault(issue_name, []).append(keyword)

    summary_by_issue = {s["issue"]: s for s in issue_summaries}

    for issue_name, keywords in by_issue.items():
        print(f"\n🔁 재시도 중: {issue_name} — {keywords}")
        df_retry = fetch_wikipedia_interest(keywords, days_back=30, issue_name=issue_name)
        if df_retry.empty:
            print(f"   ✗ 재시도 후에도 데이터 없음")
            continue

        csv_path = f"{DATA_DIR}/{issue_name}_wikipedia_30days.csv"
        if os.path.exists(csv_path):
            df_existing = pd.read_csv(csv_path)
            df_combined = pd.concat([df_existing, df_retry], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=["date", "keyword"])
        else:
            df_combined = df_retry

        if "timestamp" in df_combined.columns:
            df_combined = df_combined.sort_values("timestamp")
        df_combined.to_csv(csv_path, index=False)

        new_intensity = calculate_issue_intensity(df_combined)
        new_article_count = df_combined['article_count'].sum()

        if issue_name in summary_by_issue:
            summary_by_issue[issue_name]["intensity"] = new_intensity
            summary_by_issue[issue_name]["article_count"] = new_article_count
            summary_by_issue[issue_name]["last_updated"] = datetime.now().isoformat()

        print(f"   ✓ 재시도 후: intensity={new_intensity:.1f}, article_count={new_article_count:.0f}")

    return list(summary_by_issue.values())


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """
    전체 이슈 데이터 수집 메인 함수
    """

    print("\n" + "="*60)
    print("🌍 Global Issues Data Collection System")
    print("="*60)
    print(f"Period: 2025.01 (Trump Inauguration) ~ Present")
    print(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if RESUME_MODE:
        print("Mode: --resume (기존 CSV 있는 이슈는 건너뜀)")
    print("="*60)

    # 1. 각 이슈별 Wikipedia 관심도 데이터 수집
    print("\n[1/4] Collecting Wikipedia Pageviews (Issue Interest) Data...")
    issue_summaries = []
    for issue_name, keywords in ISSUE_KEYWORDS.items():
        summary = generate_issue_summary(issue_name, keywords)
        issue_summaries.append(summary)

    # 요청 오류로 실패한 키워드만 자동으로 한 번 더 시도 (문서가 진짜 없는
    # 건 재시도하지 않음). 이 단계가 issue_summaries의 intensity/article_count를
    # 재시도 성공분만큼 갱신합니다.
    issue_summaries = retry_failed_wikipedia_keywords(issue_summaries)

    # 실패한 키워드 목록 저장 (재시도까지 마친 뒤 최종적으로 남은 실패만)
    if _wiki_failed_keywords:
        failed_path = f"{DATA_DIR}/_wikipedia_failed_keywords.json"
        with open(failed_path, "w", encoding="utf-8") as f:
            json.dump(_wiki_failed_keywords, f, ensure_ascii=False, indent=2)
        print(f"\n⚠ Wikipedia 실패 키워드 {len(_wiki_failed_keywords)}개를 {failed_path}에 저장했습니다.")

    # 2. 경제 지표 수집 (FRED)
    print("\n[2/4] Collecting FRED Economic Indicators...")
    fred_data = fetch_fred_issue_indicators()
    print(f"✓ Collected {len(fred_data)} economic indicators")

    # 3. 국제 제재 현황
    print("\n[3/4] Collecting Sanctions Data...")
    sanctions_data = fetch_sanctions_data()

    # 4. 주요 국가 간 무역 데이터 (IMF IMTS - 구 DOTS / UN Comtrade 대체)
    print("\n[4/4] Collecting Trade Data (via IMF IMTS)...")
    trade_data = fetch_critical_trade_pairs()

    # 종합 요약 저장
    print("\n" + "="*60)
    print("📊 Issue Analysis Summary")
    print("="*60)

    summary_df = pd.DataFrame(issue_summaries)
    summary_df = summary_df.sort_values("intensity", ascending=False)

    print("\n🔴 High Priority Issues (Intensity > 60):")
    high_priority = summary_df[summary_df['intensity'] > 60]
    for idx, row in high_priority.iterrows():
        print(f"   • {row['issue']}: {row['intensity']:.1f}/100 ({row['article_count']:.0f} articles)")

    print("\n🟡 Medium Priority Issues (30-60):")
    medium_priority = summary_df[(summary_df['intensity'] >= 30) & (summary_df['intensity'] <= 60)]
    for idx, row in medium_priority.iterrows():
        print(f"   • {row['issue']}: {row['intensity']:.1f}/100 ({row['article_count']:.0f} articles)")

    print("\n🟢 Low Priority Issues (< 30):")
    low_priority = summary_df[summary_df['intensity'] < 30]
    for idx, row in low_priority.iterrows():
        print(f"   • {row['issue']}: {row['intensity']:.1f}/100 ({row['article_count']:.0f} articles)")

    # 종합 요약 CSV 저장
    summary_filename = f"{DATA_DIR}/issues_summary_{datetime.now().strftime('%Y%m%d')}.csv"
    summary_df.to_csv(summary_filename, index=False)
    print(f"\n✓ Summary saved: {summary_filename}")

    print("\n" + "="*60)
    print("✅ Data Collection Complete!")
    if _wiki_failed_keywords:
        print(f"   (Wikipedia 실패 {len(_wiki_failed_keywords)}건 — "
              f"'python scripts/issue_data_collector.py --resume' 로 나머지만 재시도 가능)")
    print("="*60)

    return summary_df


if __name__ == "__main__":
    summary = main()
