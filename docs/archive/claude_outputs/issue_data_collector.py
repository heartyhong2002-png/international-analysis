"""
Issue-Specific Data Collection Module
대륙별 이슈 분석을 위한 데이터 수집 스크립트

Data Sources:
- GDELT 2.0: 뉴스 감정도, 기사 수
- FRED: 경제 지표 (환율, 유가, 금리 등)
- OpenSanctions: 국제 제재 현황
- IMF DOTS: 국가 간 무역 데이터 (UN Comtrade 대체, API 키 불필요)

Analysis Period: 2025.01 ~ 현재 (트럼프 취임 이후)

============================================================================
NOTE (수정 사항 v4 — GDELT 반복 타임아웃 대응):

v3까지 고친 쿼리 문법/파싱 버그는 실제로 맞았지만, 그 이후로도 계속
"Read timed out" / "Max retries exceeded"가 반복된다는 리포트를 받고
다음을 추가했습니다.

1. 타임아웃 최소값 강제(floor). 로그에 "read timeout=10.0"이 찍힌 적이
   있었는데, 이는 코드 기본값(45초)이 아니라 .env의 GDELT_READ_TIMEOUT_SEC가
   더 낮은 값으로 설정되어 있었기 때문으로 보입니다. timelinevolraw는 날짜
   범위가 넓거나 GDELT 서버가 바쁠 때 45초도 종종 넘기므로, .env에 무엇을
   넣든 최소 30초(connect)/30초(read) 밑으로는 못 내려가게 막습니다.
2. 시작할 때 실제 적용되는 타임아웃/간격 설정을 화면에 출력합니다.
   (.env가 뭘 하고 있는지 더 이상 추측할 필요가 없게)
3. 본 수집을 시작하기 전에 아주 가벼운 연결 테스트를 1회 먼저 해서,
   GDELT 자체가 지금 응답 불가 상태인지 먼저 빠르게 판별합니다.
   (21개 이슈 x 3개 키워드를 몇 분씩 재시도하며 다 돌고 나서야 "전부
   실패했다"는 걸 알게 되는 상황을 피하기 위함)
4. 회로 차단기(circuit breaker): 같은 실행 중 GDELT 키워드가 연속으로
   N번(기본 3번) 완전히 실패(모든 재시도 소진)하면, 이는 개별 키워드
   문제가 아니라 네트워크/GDELT 서버 자체가 지금 응답하지 않는 상황일
   가능성이 높다고 보고, 남은 GDELT 요청은 건너뛰고 바로 FRED/OpenSanctions/
   IMF DOTS 단계로 넘어갑니다. (안 그러면 네트워크가 끊긴 상태로 수십 분을
   그냥 재시도만 하다가 끝날 수 있음)
5. --resume 옵션: 이미 CSV가 저장된 이슈는 건너뛰어서, 중간에 끊겨도
   처음부터 다시 돌릴 필요 없이 이어서 할 수 있게 했습니다.
6. 실패한 키워드 목록을 data/issues/_gdelt_failed_keywords.json에 저장해서
   나중에 그것만 골라 재시도할 수 있게 했습니다.
============================================================================
"""

import os
import sys
import json
import time
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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

# Issue Keywords for GDELT Search
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
# 1. GDELT News Sentiment Analysis
# ============================================================================

GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
# GDELT Doc API throttles by client IP.  The documented minimum is 5 seconds,
# but a longer default leaves room for another job sharing the same network.
GDELT_MIN_INTERVAL_SEC = float(os.getenv("GDELT_MIN_INTERVAL_SEC", "10"))
GDELT_MAX_RETRIES = int(os.getenv("GDELT_MAX_RETRIES", "4"))

# v4: .env가 이 값들을 아무리 낮게 설정해도 이 밑으로는 못 내려가게 강제합니다.
# timelinevolraw는 날짜 범위가 넓을 때 45초도 종종 넘기므로, 너무 짧은
# read timeout은 "GDELT가 느릴 뿐인데 우리 쪽에서 먼저 끊어버리는" 가짜
# 타임아웃을 계속 만들어 냅니다.
_MIN_CONNECT_TIMEOUT = 15.0
_MIN_READ_TIMEOUT = 30.0
GDELT_TIMEOUT = (
    max(float(os.getenv("GDELT_CONNECT_TIMEOUT_SEC", "20")), _MIN_CONNECT_TIMEOUT),
    max(float(os.getenv("GDELT_READ_TIMEOUT_SEC", "60")), _MIN_READ_TIMEOUT),
)
_gdelt_last_request_at = 0.0

# v4: 회로 차단기. 같은 키워드 하나가 모든 재시도(GDELT_MAX_RETRIES)를
# 소진하고 완전히 실패할 때마다 +1, 성공하면 0으로 리셋. 이 값이
# GDELT_CIRCUIT_BREAKER_THRESHOLD에 도달하면 "지금은 GDELT 자체가 응답
# 불가"로 판단하고 남은 GDELT 요청을 전부 건너뜁니다.
GDELT_CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("GDELT_CIRCUIT_BREAKER_THRESHOLD", "3"))
_gdelt_consecutive_failures = 0
_gdelt_circuit_open = False
_gdelt_failed_keywords = []  # [(issue_name, keyword, reason), ...]


def _gdelt_wait_for_slot():
    """Keep requests from this process apart without delaying the first one."""
    global _gdelt_last_request_at
    remaining = GDELT_MIN_INTERVAL_SEC - (time.monotonic() - _gdelt_last_request_at)
    if remaining > 0:
        time.sleep(remaining)
    _gdelt_last_request_at = time.monotonic()


def _gdelt_retry_delay(response, attempt):
    """Prefer the server-provided cooldown; otherwise use capped backoff."""
    retry_after = response.headers.get("Retry-After") if response is not None else None
    try:
        return min(float(retry_after), 300) if retry_after else min(15 * (2 ** (attempt - 1)), 120)
    except ValueError:
        return min(15 * (2 ** (attempt - 1)), 120)


def _gdelt_build_query(keyword):
    """
    GDELT Doc API 쿼리 문자열 정규화.

    NOTE (수정 사항 v3): GDELT는 검색어의 각 '단어'가 3글자 이상이어야 하며,
    그렇지 않으면 HTTP 200 을 주면서 본문에 "Your search contained a keyword
    that was too short." 라는 (JSON 이 아닌) 텍스트 에러를 돌려줍니다.
    "US Canada trade war", "EU Russia relations", "OPEC oil" 처럼 2글자 토큰이
    섞인 키워드가 전부 여기에 걸려서 GDELT 수집이 통째로 실패하고 있었습니다.
    -> 여러 단어로 된 키워드는 통짜 구문(phrase) 검색으로 큰따옴표로 감쌉니다.
       (구문 검색은 짧은 단어 제한을 받지 않는 것을 확인했습니다.)
    """
    kw = keyword.strip()
    if kw.startswith('"') and kw.endswith('"'):
        return kw
    if " " in kw:
        return f'"{kw}"'
    return kw


def gdelt_connectivity_check():
    """
    v4: 본 수집(21개 이슈 x 3개 키워드)을 시작하기 전에, 아주 가벼운 쿼리
    하나로 GDELT가 지금 이 네트워크에서 응답하는지 먼저 확인합니다.

    이걸 안 하면: 네트워크가 지금 막혀 있을 경우 첫 이슈부터 각 키워드마다
    (최대 GDELT_MAX_RETRIES번 재시도 x 최대 120초 대기)를 거치며 몇 분씩
    허비한 뒤에야 "다 실패했다"는 걸 알게 됩니다.

    Returns:
        (성공 여부: bool, 진단 메시지: str)
    """
    test_params = {
        "query": "test",
        "mode": "artlist",
        "format": "json",
        "maxrecords": 1,
        "timespan": "1d",
    }
    try:
        resp = requests.get(
            GDELT_DOC_API_URL,
            params=test_params,
            timeout=(15.0, 20.0),
            headers={"User-Agent": "international-analysis/1.0 (connectivity check)"},
        )
        if resp.status_code == 200:
            try:
                resp.json()
                return True, "OK"
            except ValueError:
                # 200인데 JSON이 아니어도, 최소한 서버가 응답은 했다는 뜻이므로
                # 네트워크 자체는 살아있다고 판단합니다.
                return True, "OK (non-JSON 200, but server is reachable)"
        else:
            return False, f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout as e:
        return False, f"연결 시간 초과: {e}"
    except requests.exceptions.ConnectionError as e:
        return False, f"연결 실패: {e}"
    except Exception as e:
        return False, f"알 수 없는 오류: {e}"


def fetch_gdelt_sentiment(keywords, days_back=7, issue_name=""):
    """
    GDELT 2.0 Doc API에서 뉴스 기사량(Timeline) 수집

    Args:
        keywords (list): 검색 키워드
        days_back (int): 몇 일 전부터 수집할 것인가
        issue_name (str): 실패 로그 기록용 이슈 이름

    Returns:
        pd.DataFrame: 날짜별 기사 수 (컬럼: date, keyword, article_count, timestamp)
    """
    global _gdelt_consecutive_failures, _gdelt_circuit_open

    results = []
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
    end_date = datetime.now().strftime("%Y%m%d")

    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "international-analysis/1.0 (GDELT data collection)",
    })

    for keyword in keywords:
        if _gdelt_circuit_open:
            print(f"  ⏭  GDELT 건너뜀 ({keyword}): 회로 차단기 작동 중 (네트워크/GDELT 응답 불가로 판단됨)")
            _gdelt_failed_keywords.append({
                "issue": issue_name, "keyword": keyword, "reason": "circuit_breaker_open"
            })
            continue

        query = _gdelt_build_query(keyword)
        keyword_succeeded = False

        for attempt in range(1, GDELT_MAX_RETRIES + 1):

            try:
                params = {
                    "query": query,
                    # NOTE (수정 사항 v3): 기존 "TimelineVol"은 "기사 수"가 아니라
                    # 전체 대비 비율(Volume Intensity, 소수점 %) 을 돌려줍니다.
                    # article_count 라는 이름과 맞지 않으므로, 실제 매칭 기사 수를
                    # 주는 "timelinevolraw"(series="Article Count", value=기사수)로
                    # 변경합니다.
                    "mode": "timelinevolraw",
                    "format": "json",
                    "startdatetime": f"{start_date}000000",
                    "enddatetime": f"{end_date}235959",
                }

                _gdelt_wait_for_slot()
                response = session.get(GDELT_DOC_API_URL, params=params, timeout=GDELT_TIMEOUT)

                if response.status_code == 200:
                    # NOTE (수정 사항 v3): GDELT는 쿼리 오류 시에도 HTTP 200 +
                    # (JSON 이 아닌) 평문 에러를 돌려줍니다. 기존 코드는 200이면
                    # 무조건 response.json() 을 호출해서 JSONDecodeError -> 하단의
                    # generic except -> "GDELT Error" -> break 로 빠졌습니다.
                    # 이게 사실상 모든 키워드가 실패하던 진짜 원인이었습니다.
                    try:
                        data = response.json()
                    except ValueError:
                        msg = response.text.strip().replace("\n", " ")[:200]
                        print(f"✗ GDELT Error ({keyword}): 쿼리 거부됨 - {msg}")
                        _gdelt_failed_keywords.append({
                            "issue": issue_name, "keyword": keyword, "reason": f"query_rejected: {msg}"
                        })
                        break  # 쿼리 자체 문제라 재시도 무의미

                    # timeline 구조:
                    #   [{"series": "Article Count",
                    #     "data": [{"date": "20260804T000000Z", "value": 84, ...}]}]
                    timeline = data.get("timeline", [])
                    points = []
                    for series in timeline:
                        points.extend(series.get("data", []))

                    for d in points:
                        raw_date = d.get("date", "")
                        try:
                            ts = datetime.strptime(raw_date[:8], "%Y%m%d")
                        except ValueError:
                            continue
                        results.append({
                            "date": raw_date[:8],
                            "keyword": keyword,
                            "article_count": d.get("value", 0),
                            "timestamp": ts,
                        })

                    print(f"✓ GDELT: {keyword} - {len(points)} data points collected")
                    keyword_succeeded = True
                    break  # 성공, 재시도 불필요

                elif response.status_code == 429:
                    if attempt < GDELT_MAX_RETRIES:
                        wait = _gdelt_retry_delay(response, attempt) + random.uniform(0, 2)
                        print(f"  ⏳ GDELT 429(요청 과다) 재시도 {attempt}/{GDELT_MAX_RETRIES - 1} "
                              f"({keyword}) - {wait:.0f}초 후 재시도")
                        time.sleep(wait)
                    else:
                        print(f"✗ GDELT Error ({keyword}): {GDELT_MAX_RETRIES}번 시도 모두 429(요청 과다) - "
                              f"{response.text[:200]}")
                        _gdelt_failed_keywords.append({
                            "issue": issue_name, "keyword": keyword, "reason": "http_429_exhausted"
                        })
                    # continue: 다음 attempt로 (break 하지 않음)

                else:
                    print(f"✗ GDELT Error ({keyword}): HTTP {response.status_code} - {response.text[:200]}")
                    _gdelt_failed_keywords.append({
                        "issue": issue_name, "keyword": keyword,
                        "reason": f"http_{response.status_code}"
                    })
                    break  # 429가 아닌 다른 오류는 재시도해도 의미 없으므로 다음 키워드로

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < GDELT_MAX_RETRIES:
                    wait = _gdelt_retry_delay(None, attempt) + random.uniform(0, 2)
                    print(f"  ⏳ GDELT 재시도 {attempt}/{GDELT_MAX_RETRIES - 1} ({keyword}) - {wait:.0f}초 후 재시도: {str(e)[:120]}")
                    time.sleep(wait)
                else:
                    print(f"✗ GDELT Error ({keyword}): {GDELT_MAX_RETRIES}번 시도 모두 타임아웃/연결실패 - {str(e)[:150]}")
                    _gdelt_failed_keywords.append({
                        "issue": issue_name, "keyword": keyword,
                        "reason": f"timeout_or_connection: {str(e)[:150]}"
                    })
            except Exception as e:
                print(f"✗ GDELT Error ({keyword}): {str(e)}")
                _gdelt_failed_keywords.append({
                    "issue": issue_name, "keyword": keyword, "reason": str(e)
                })
                break

        # v4: 회로 차단기 카운터 갱신
        if keyword_succeeded:
            _gdelt_consecutive_failures = 0
        else:
            _gdelt_consecutive_failures += 1
            if _gdelt_consecutive_failures >= GDELT_CIRCUIT_BREAKER_THRESHOLD:
                _gdelt_circuit_open = True
                print(f"\n  🔴 회로 차단기 작동: 키워드 {GDELT_CIRCUIT_BREAKER_THRESHOLD}개 연속 완전 실패.")
                print(f"     지금 이 네트워크에서 GDELT가 응답하지 않는 것으로 보입니다.")
                print(f"     남은 이슈의 GDELT 수집은 건너뛰고, FRED/OpenSanctions/IMF DOTS는 계속 진행합니다.")
                print(f"     (실패한 키워드는 data/issues/_gdelt_failed_keywords.json 에 저장되어, "
                      f"네트워크 복구 후 재시도할 수 있습니다.)\n")

    if results:
        df = pd.DataFrame(results)
        return df.sort_values("timestamp")
    else:
        return pd.DataFrame()


def calculate_issue_intensity(df_gdelt):
    """
    뉴스 기사 수로부터 이슈 강도 지수 계산 (0-100)

    기간별 기사 수를 정규화하여 이슈의 강도 평가
    """
    if df_gdelt.empty:
        return 0

    # 최근 7일 기사 수
    recent_articles = df_gdelt['article_count'].tail(7).sum()

    # 전체 기간 평균 대비 배수
    avg_articles = df_gdelt['article_count'].mean()

    if avg_articles == 0:
        intensity = 0
    else:
        intensity = min(100, (recent_articles / avg_articles) * 50)  # 최대 100

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
# 4. IMF DOTS (Direction of Trade Statistics) - 국가 간 무역 데이터
#    (UN Comtrade 대체)
# ============================================================================
#
# UN Comtrade와 이를 재제공하는 WITS 모두 UN Comtrade 원본 서버 장애로
# 이용이 불가능하여, IMF(국제통화기금)가 직접 운영하는 완전히 독립적인
# 데이터 소스인 DOTS(Direction of Trade Statistics)를 사용합니다.
# API 키가 필요 없으며 국가 간 수출입 금액(USD)을 월/분기/연간으로 제공합니다.
#
# IMF는 자체 2자리 국가 코드를 사용합니다 (ISO와 유사하지만 동일하지 않음).

IMF_DOTS_BASE_URL = "http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/DOT"

# IMF 국가 코드 매핑 (필요한 국가만)
IMF_COUNTRY_CODES = {
    "USA": "US",
    "CHN": "CN",
    "RUS": "RU",
    "IRN": "IR",
    "DEU": "DE",
    "KOR": "KR",
    "SAU": "SA",
}


def fetch_imf_dots_trade_data(reporter, partner, start_year, end_year, freq="A"):
    """
    IMF DOTS API로 양국 간 무역 데이터 조회 (UN Comtrade 완전 대체)

    Args:
        reporter (str): 수출국 IMF 코드 (예: "US")
        partner (str): 상대국 IMF 코드 (예: "CN")
        start_year (int): 조회 시작 연도
        end_year (int): 조회 종료 연도
        freq (str): 빈도 - "A"(연간), "Q"(분기), "M"(월간)

    Returns:
        dict: 무역 데이터 (실패 시 None)
    """
    # TXG_FOB_USD = 수출(FOB, USD), TMG_CIF_USD = 수입(CIF, USD)
    indicator = "TXG_FOB_USD"
    url = f"{IMF_DOTS_BASE_URL}/{freq}.{reporter}.{indicator}.{partner}"
    params = {
        "startPeriod": start_year,
        "endPeriod": end_year,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"  ✗ IMF DOTS Error ({reporter}->{partner}): HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"  ✗ IMF DOTS Error ({reporter}->{partner}): {str(e)}")
        return None


def fetch_critical_trade_pairs():
    """
    주요 이슈 관련 국가 간 무역 데이터 수집 (IMF DOTS 경유)

    예:
    - 미-중 반도체 무역 (대만 해협)
    - 러-유럽 에너지 무역 (우크라이나)
    - 이란 석유 수출 (이란 제재)
    """

    # 분석할 무역 쌍 (ISO3 코드로 표기, 내부적으로 IMF 코드로 변환)
    trade_pairs = [
        # (수출국, 수입국, 설명)
        ("USA", "CHN", "US-China Trade (Semiconductors 포함)"),
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
        imf_reporter = IMF_COUNTRY_CODES.get(reporter)
        imf_partner = IMF_COUNTRY_CODES.get(partner)

        if not imf_reporter or not imf_partner:
            print(f"  ⚠ Trade Pair: {desc} - IMF 국가 코드 없음 (건너뜀)")
            continue

        result = fetch_imf_dots_trade_data(imf_reporter, imf_partner, start_year, end_year)

        if result:
            trade_data[f"{reporter}_{partner}"] = {
                "description": desc,
                "data": result,
                "years": f"{start_year}-{end_year}"
            }
            print(f"  ✓ Trade Pair: {desc} - 수집 완료")
        else:
            trade_data[f"{reporter}_{partner}"] = {
                "description": desc,
                "data": None,
                "years": f"{start_year}-{end_year}",
                "status": "failed"
            }
            print(f"  ⚠ Trade Pair: {desc} - 수집 실패 (건너뜀)")

    return trade_data


# ============================================================================
# 5. Issue Analysis Summary
# ============================================================================

def generate_issue_summary(issue_name, keywords):
    """
    각 이슈에 대한 종합 분석 요약 생성
    """

    csv_path = f"{DATA_DIR}/{issue_name}_gdelt_30days.csv"

    # v4: --resume 모드에서는 이미 저장된 CSV가 있으면 건너뛰어서, 중간에
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

    # GDELT 뉴스 감정도
    df_gdelt = fetch_gdelt_sentiment(keywords, days_back=30, issue_name=issue_name)
    intensity = calculate_issue_intensity(df_gdelt)

    # 요약 통계
    if not df_gdelt.empty:
        print(f"\n📰 News Analysis:")
        print(f"   - Total Articles (30 days): {df_gdelt['article_count'].sum()}")
        print(f"   - Daily Average: {df_gdelt['article_count'].mean():.1f}")
        print(f"   - Issue Intensity: {intensity:.1f}/100", end="")

        if intensity < 30:
            print(" (낮음)")
        elif intensity < 60:
            print(" (중간)")
        else:
            print(" (높음) 🔴")

    # CSV로 저장
    if not df_gdelt.empty:
        df_gdelt.to_csv(csv_path, index=False)
        print(f"   - Data saved: {csv_path}")

    return {
        "issue": issue_name,
        "intensity": intensity,
        "article_count": df_gdelt['article_count'].sum() if not df_gdelt.empty else 0,
        "last_updated": datetime.now().isoformat()
    }


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

    # v4: 실제 적용되는 GDELT 설정을 출력 — .env가 뭘 하고 있는지 바로 확인 가능
    print(f"\n[GDELT 설정]")
    print(f"  connect_timeout = {GDELT_TIMEOUT[0]:.0f}s, read_timeout = {GDELT_TIMEOUT[1]:.0f}s")
    print(f"  요청 간 최소 간격 = {GDELT_MIN_INTERVAL_SEC:.0f}s, 키워드당 최대 재시도 = {GDELT_MAX_RETRIES}")
    print(f"  회로 차단기 임계값 = 연속 {GDELT_CIRCUIT_BREAKER_THRESHOLD}번 완전 실패 시 GDELT 건너뛰기")

    # v4: 본격적인 수집 전에 GDELT가 지금 응답하는지 먼저 빠르게 확인
    print(f"\n[사전 점검] GDELT 연결 테스트 중...")
    ok, msg = gdelt_connectivity_check()
    if ok:
        print(f"  ✓ GDELT 연결 정상 ({msg})")
    else:
        print(f"  ✗ GDELT 연결 실패: {msg}")
        print(f"  ⚠ 지금 이 네트워크에서 GDELT(api.gdeltproject.org)에 접속할 수 없는 것으로 보입니다.")
        print(f"     - VPN을 사용 중이라면 꺼보고 다시 시도해보세요 (또는 그 반대로 켜보세요)")
        print(f"     - 아래 명령으로 직접 확인해보세요:")
        print(f'       curl -v --connect-timeout 15 --max-time 30 "https://api.gdeltproject.org/api/v2/doc/doc?query=test&mode=artlist&format=json&maxrecords=1"')
        print(f"     - GDELT 수집은 전부 건너뛰고 FRED/OpenSanctions/IMF DOTS만 진행합니다.\n")
        global _gdelt_circuit_open
        _gdelt_circuit_open = True

    # 1. 각 이슈별 GDELT 데이터 수집
    print("\n[1/4] Collecting GDELT News Sentiment Data...")
    issue_summaries = []
    for issue_name, keywords in ISSUE_KEYWORDS.items():
        summary = generate_issue_summary(issue_name, keywords)
        issue_summaries.append(summary)

    # v4: 실패한 키워드 목록 저장 (네트워크 복구 후 재시도용)
    if _gdelt_failed_keywords:
        failed_path = f"{DATA_DIR}/_gdelt_failed_keywords.json"
        with open(failed_path, "w", encoding="utf-8") as f:
            json.dump(_gdelt_failed_keywords, f, ensure_ascii=False, indent=2)
        print(f"\n⚠ GDELT 실패 키워드 {len(_gdelt_failed_keywords)}개를 {failed_path}에 저장했습니다.")

    # 2. 경제 지표 수집 (FRED)
    print("\n[2/4] Collecting FRED Economic Indicators...")
    fred_data = fetch_fred_issue_indicators()
    print(f"✓ Collected {len(fred_data)} economic indicators")

    # 3. 국제 제재 현황
    print("\n[3/4] Collecting Sanctions Data...")
    sanctions_data = fetch_sanctions_data()

    # 4. 주요 국가 간 무역 데이터 (IMF DOTS - UN Comtrade 대체)
    print("\n[4/4] Collecting Trade Data (via IMF DOTS)...")
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
    if _gdelt_failed_keywords:
        print(f"   (GDELT 실패 {len(_gdelt_failed_keywords)}건 — 네트워크 복구 후 "
              f"'python scripts/issue_data_collector.py --resume' 로 나머지만 재시도 가능)")
    print("="*60)

    return summary_df


if __name__ == "__main__":
    summary = main()
