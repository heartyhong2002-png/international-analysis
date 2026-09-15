"""
정부 발표 수집 모듈 (초안 v1)
==============================

목적: Wikipedia Pageviews(대중 관심도) + FRED/IMF(경제 지표)에 이어서,
"각국 정부가 이 이슈에 대해 공식적으로 뭐라고 말했는가"라는 세 번째 신호를
추가합니다. 나중에 LLM(SOLAR 등)에 이 발표문들을 같이 넣어주면
"신호 vs 실제 발표"를 비교해서 정부 의도를 역추적하는 근거 자료가 됩니다.

검증된 RSS 피드 (브라우저로 직접 접속해서 실데이터 확인함):
  - 한국 외교부 보도자료: http://www.mofa.go.kr/www/brd/rss.do?brdId=235 (2026-09-05 확인,
    2026-09-08 재확인 시 인코딩이 EUC-KR -> UTF-8로 바뀐 걸 발견 — fetch_rss_feed()가
    XML 선언에서 자동 감지하니 참고만 할 것, encoding 필드는 이제 fallback일 뿐)
  - 미국 국무부(State Dept): www.state.gov/rss-feed/.../feed/ (2026-09-05 확인)
      * 표준 WordPress RSS, UTF-8, 지역별(동아시아·유럽·중동·아프리카 등)
        피드가 따로 있어서 이슈 매칭 정확도를 높일 수 있습니다.
  - IRNA (이란 국영 통신사, 영문): https://en.irna.ir/rss (2026-09-08 확인)
      * 이란 정부가 직접 운영하는 공식 국영 통신사라, Iran_Nuclear 이슈에서
        MOFA/State Dept급으로 "정부 공식 목소리"에 가장 가까운 소스입니다.
  - Al Jazeera (카타르 국영 방송사, 영문): https://www.aljazeera.com/xml/rss/all.xml
    (2026-09-08 확인)
      * 중동 전역(이스라엘-팔레스타인, 걸프, 이란 등)을 폭넓게 다루는 전체 뉴스
        피드라, Middle_East_Energy/Israel_Palestine 커버리지를 채워줍니다.
        완전 독립언론은 아니고 카타르 정부 소유라는 점은 참고.
  - 영국 FCDO (외교·영연방·개발부) 보도자료: 준기님이 업로드하신
    "서방_중동_주요국_정부_데이터_API_조사.md"(2026-09-14, 다른 트랙 작성)의
    조사 결과를 제가 직접 재검증해서 추가함 (2026-09-14 확인).
      * https://www.gov.uk/search/news-and-communications.atom?organisations%5B%5D=foreign-commonwealth-development-office
      * ⚠️ RSS 2.0이 아니라 **Atom 1.0**입니다 (root가 <rss>가 아니라 <feed>,
        <item> 대신 <entry>, <pubDate> 대신 <updated>, <description> 대신
        <summary>, <link>는 텍스트가 아니라 href 속성). fetch_rss_feed()에
        format="atom" 분기를 새로 추가해서 처리합니다 (실제 응답 캡처해서
        파싱 로직 검증 완료 — 아래 v1.6 NOTE 참고).
  - 독일 외교부(Auswärtiges Amt) 보도자료·연설문 RSS: 같은 조사 보고서 기반,
    직접 재검증 (2026-09-14 확인).
      * https://www.auswaertiges-amt.de/static/includes/rss/Presse-RSS-Feed.xml
      * ⚠️ 보고서에 적힌 `.../newsletter/rss` URL은 실제 피드가 아니라 "RSS가
        뭔지 설명하고 진짜 피드 링크를 안내하는" HTML 소개 페이지였습니다.
        진짜 피드는 위 `/static/includes/rss/...xml` 경로입니다. 표준 RSS 2.0,
        UTF-8, 독일어 원문.
  - 확인해봤지만 안 되는 것들 (다음에 또 시도하지 않도록 기록):
      * Saudi Press Agency(SPA, spa.gov.sa) — RSS로 추정되는 경로들이 실제로는
        전부 일반 HTML 페이지를 반환함 (200이지만 content-type이 rss 아님).
        진짜 RSS 엔드포인트를 못 찾음.
      * Times of Israel (timesofisrael.com) — Cloudflare 봇 챌린지 페이지가
        떠서 requests로는 막힘. cloudscraper 같은 별도 라이브러리 없이는 불가.
      * 튀르키예 외교부(mfa.gov.tr) RSS — 조사 보고서에 `mfa.gov.tr/rss.en.mfa`로
        적혀있었는데, 이것도 독일과 마찬가지로 실제 피드가 아니라 안내 페이지였음
        (2026-09-14 확인). 안내 페이지에서 실제 링크
        (`en.rss.mfa?<UUID>` 형태, 예:
        `https://www.mfa.gov.tr/en.rss.mfa?ad9093da-8e71-4678-a1b6-05f297baadc4`)를
        찾아서 다시 요청해봤지만 빈 응답만 돌아옴 — URL에 붙은 UUID가 페이지
        로드시마다 발급되는 세션성 토큰이라 고정 API 엔드포인트로 쓸 수 없는
        것으로 추정됨. 자동화 파이프라인에는 넣지 않음 (나중에 requests 세션으로
        먼저 안내 페이지를 받고 그 안의 링크를 매번 새로 파싱하는 2단계 방식이면
        될 수도 있으나, 지금은 우선순위 낮음으로 보류).

아직 "초안"인 이유 (다음에 더 다듬을 것):
  1. 이슈 매칭이 단순 키워드 포함 여부라 오탐/누락이 있을 수 있음
     (issue_data_collector.py의 ISSUE_KEYWORDS와 통합해서 관리하는 게 이상적)
  2. 한국 외교부 외에 다른 나라 정부 발표(중국 외교부, 일본 외무성 등)는
     아직 없음 - 대부분 RSS가 아니라 웹스크래핑이 필요해서 별도 작업 필요
  3. issue_data_collector.py의 main() 파이프라인에는 아직 연결 안 함
     (독립 실행 가능한 상태로만 우선 만듦 - 검증되면 5번째 스텝으로 추가)

사용법:
    python scripts/gov_announcements_collector.py
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import json
import os
import re
import time

# NOTE (수정 사항 v1.2 — 작업 디렉터리 문제): issue_data_collector.py와
# 똑같은 이유로, DATA_DIR을 실행 위치에 상관없이 이 스크립트 파일 기준
# (scripts/data/gov_announcements)으로 고정합니다. 터미널을 어디서 열었든,
# VS Code Run 버튼으로 돌리든 항상 같은 폴더를 씁니다.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_SCRIPT_DIR, "data", "gov_announcements")
os.makedirs(DATA_DIR, exist_ok=True)

# NOTE (수정 사항 v1.1): 첫 실행에서 State Dept 피드 8개가 전부 403으로
# 막혔습니다. 브라우저로 접속했을 땐 멀쩡했던 걸 보면, state.gov의 방화벽이
# 우리가 붙인 리서치용 User-Agent를 "봇"으로 감지해서 차단한 것으로
# 보입니다 (외교부는 이 UA로도 문제없이 통과됨). 일반 브라우저처럼 보이는
# User-Agent와 Accept 헤더로 바꿔서 우회합니다.
REQUEST_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
}

# ============================================================================
# 검증된 정부 RSS 피드 목록
# ============================================================================
# NOTE (수정 사항 v1.5 — ADR-001 연동): 오픈소스 LLM 트랙이 2026-09-10에 작성한
# ADR-001("LLM 역할정의 및 감성분석 휴먼인더루프")의 2번 결정 — "정부 공식
# 보도자료는 뉴스와 분리된 '공식 입장' 레이어로 저장" — 을 따르기 위해
# source_type을 추가합니다.
#   - "official_statement": 정부 기관이 직접 운영하는 보도자료 채널
#     (외교부/국무부). LLM은 이걸 "발표주체·날짜·상대국·핵심주장·정책액션"으로
#     구조화 추출하는 입력으로 씁니다.
#   - "state_media_news": 국영/국가 소유 매체지만 보도자료 채널이 아니라
#     광범위한 주제를 다루는 뉴스 매체(IRNA, Al Jazeera). ADR의 "뉴스" 레이어에
#     더 가깝습니다 — 실제로 Iran_Nuclear 키워드 과매칭 버그도 IRNA가 핵과 무관한
#     일반 뉴스까지 쏟아내서 생긴 문제였습니다(주제 범위가 진짜 보도자료 채널과
#     다름을 데이터로 확인한 셈).
GOV_FEEDS = {
    "한국 외교부 보도자료": {
        "url": "http://www.mofa.go.kr/www/brd/rss.do?brdId=235",
        "encoding": "euc-kr",  # 중요: UTF-8 아님! (본문 상단 NOTE 참고)
        "country": "KR",
        "lang": "ko",
        "source_type": "official_statement",
    },
    "US State Dept - Press Releases": {
        "url": "https://www.state.gov/rss-feed/press-releases/feed/",
        "encoding": "utf-8",
        "country": "US",
        "lang": "en",
        "source_type": "official_statement",
    },
    "US State Dept - East Asia & Pacific": {
        "url": "https://www.state.gov/rss-feed/east-asia-and-the-pacific/feed/",
        "encoding": "utf-8",
        "country": "US",
        "lang": "en",
        "source_type": "official_statement",
    },
    "US State Dept - Europe & Eurasia": {
        "url": "https://www.state.gov/rss-feed/europe-and-eurasia/feed/",
        "encoding": "utf-8",
        "country": "US",
        "lang": "en",
        "source_type": "official_statement",
    },
    "US State Dept - Near East": {
        "url": "https://www.state.gov/rss-feed/near-east/feed/",
        "encoding": "utf-8",
        "country": "US",
        "lang": "en",
        "source_type": "official_statement",
    },
    "US State Dept - Africa": {
        "url": "https://www.state.gov/rss-feed/africa/feed/",
        "encoding": "utf-8",
        "country": "US",
        "lang": "en",
        "source_type": "official_statement",
    },
    "US State Dept - South & Central Asia": {
        "url": "https://www.state.gov/rss-feed/south-and-central-asia/feed/",
        "encoding": "utf-8",
        "country": "US",
        "lang": "en",
        "source_type": "official_statement",
    },
    "US State Dept - Western Hemisphere": {
        "url": "https://www.state.gov/rss-feed/western-hemisphere/feed/",
        "encoding": "utf-8",
        "country": "US",
        "lang": "en",
        "source_type": "official_statement",
    },
    "US State Dept - Press Briefings": {
        "url": "https://www.state.gov/rss-feed/department-press-briefings/feed/",
        "encoding": "utf-8",
        "country": "US",
        "lang": "en",
        "source_type": "official_statement",
    },
    "IRNA (이란 국영 통신사)": {
        "url": "https://en.irna.ir/rss",
        "encoding": "utf-8",
        "country": "IR",
        "lang": "en",
        "source_type": "state_media_news",
    },
    "Al Jazeera": {
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "encoding": "utf-8",
        "country": "QA",
        "lang": "en",
        "source_type": "state_media_news",
    },
    # NOTE (수정 사항 v1.6 — 서방·중동 6개국 조사 반영, 2026-09-14): 다른 트랙이
    # 작성한 조사 보고서를 컨트롤타워가 직접 재검증해서 추가. 영국/독일 외에
    # 이스라엘·이란·사우디·튀르키예도 조사됐지만: 이스라엘/이란/사우디는 외교부
    # 자체 RSS가 없어서(웹크롤링 필요, 지금 범위 밖) 이번엔 보류, 튀르키예는
    # 바로 위 "확인해봤지만 안 되는 것들"에 적은 이유로 제외.
    "영국 FCDO (외교·영연방·개발부)": {
        "url": "https://www.gov.uk/search/news-and-communications.atom?organisations%5B%5D=foreign-commonwealth-development-office",
        "encoding": "utf-8",
        "format": "atom",  # RSS 2.0이 아니라 Atom 1.0 — fetch_rss_feed()가 이 필드로 분기
        "country": "GB",
        "lang": "en",
        "source_type": "official_statement",
    },
    "독일 외교부 (Auswärtiges Amt)": {
        "url": "https://www.auswaertiges-amt.de/static/includes/rss/Presse-RSS-Feed.xml",
        "encoding": "utf-8",
        "country": "DE",
        "lang": "de",
        "source_type": "official_statement",
    },
}

# 이슈 매칭용 키워드. issue_data_collector.py의 ISSUE_KEYWORDS와 같은 이슈
# 체계를 쓰되, 여기서는 "기사 제목/요약에 이 단어가 있으면 이 이슈다"라는
# 더 느슨한 매칭용 키워드라서 형태가 조금 다릅니다.
# (나중에 두 파일을 공통 config.py/json으로 합치는 걸 추천합니다.)
#
# NOTE (수정 사항 v1.1): 첫 실행에서 외교부 보도자료 29건이 전부
# 매칭 실패로 나왔는데, 원인은 키워드가 전부 영어라서 였습니다.
# 외교부 보도자료는 당연히 한글이니까 영어 키워드론 하나도 안 걸립니다.
# -> 소스 언어에 상관없이 매칭되도록 한글 키워드를 같이 넣었습니다.
# "핵"처럼 너무 짧고 흔한 한글자는 Iran_Nuclear/North_Korea_Nuclear가
# 서로 오염시키니까 피하고, "북한 핵"/"이란 핵"처럼 묶어서 씁니다.
ISSUE_MATCH_KEYWORDS = {
    "US_Canada_Trade": ["canada", "usmca", "캐나다"],
    "US_Mexico_Migration": ["mexico", "migration", "border", "immigration", "deportation",
                             "멕시코", "불법 이민", "국경"],
    "Trump_Economy": ["tariff", "trade war", "economic policy", "관세", "무역전쟁", "트럼프 행정부"],
    "Venezuela_Crisis": ["venezuela", "maduro", "베네수엘라", "마두로"],
    "Brazil_Politics": ["brazil", "lula", "브라질", "룰라"],
    "Argentina_Economy": ["argentina", "milei", "아르헨티나", "밀레이"],
    "Ukraine_War": ["ukraine", "russian invasion", "우크라이나"],
    "EU_Russia": ["russia", "sanctions", "european union", "러시아 제재", "유럽연합", "대러 제재"],
    "Baltic_Security": ["baltic", "nato", "nordic", "발트", "나토", "북유럽 안보"],
    # NOTE (수정 사항 v1.4 — Iran_Nuclear 과매칭 버그): 원래 "iran"이라는 단어
    # 하나만 있어도 매칭되게 해놨었는데, IRNA(이란 국영 통신사)를 새 소스로
    # 추가하고 나니 IRNA가 내는 기사는 주제가 뭐든 거의 다 "Iran"이 들어가서
    # 핵/우라늄과 무관한 일반 이란 뉴스까지 전부 Iran_Nuclear로 잡혀버렸음
    # (실측: issue_gov_match 80건 중 37건이 Iran_Nuclear, 이 중 대부분이 IRNA
    # 30건 전량 + Al Jazeera 일부로 추정됨). "iran"만 있으면 매칭되던 것을
    # "iran"과 "핵 관련 단어"가 같이 있어야 매칭되게 구(句) 단위로 좁힘.
    "Iran_Nuclear": ["iran nuclear", "iranian nuclear", "iran's nuclear", "nuclear enrichment",
                      "uranium enrichment", "이란 핵", "이란 우라늄", "이란 협상"],
    "Israel_Palestine": ["israel", "palestin", "gaza", "hamas", "이스라엘", "팔레스타인", "가자", "하마스"],
    "Middle_East_Energy": ["opec", "oil price", "saudi", "석유", "사우디", "오펙"],
    "Sudan_Conflict": ["sudan", "수단"],
    "Ethiopia_Crisis": ["ethiopia", "에티오피아"],
    "Congo_Minerals": ["congo", "cobalt", "coltan", "콩고", "코발트"],
    "North_Korea_Nuclear": ["north korea", "dprk", "kim jong", "북한 핵", "북핵", "김정은"],
    "Taiwan_Strait": ["taiwan", "cross-strait", "cross strait", "대만", "양안"],
    "India_Pakistan": ["india", "pakistan", "kashmir", "인도", "파키스탄", "카슈미르"],
    "South_China_Sea": ["south china sea", "freedom of navigation", "남중국해"],
    "Japan_Korea": ["japan", "일본", "한일"],
    "Myanmar_Crisis": ["myanmar", "burma", "미얀마"],
}


_XML_PROLOG_ENCODING_RE = re.compile(rb'<\?xml[^>]*encoding=["\']([\w-]+)["\']', re.IGNORECASE)

# NOTE (수정 사항 v1.6): 영국 FCDO가 RSS 2.0이 아니라 Atom 1.0을 쓰길래
# 추가함. Atom은 네임스페이스가 붙은 <entry>/<title>/<link>/<updated>/<summary>
# 구조라 기존 "<item>" 기반 파싱과 태그 이름·구조가 다름 (특히 link는 텍스트가
# 아니라 href 속성). feed_info에 "format": "atom"이 있으면 이 네임스페이스로
# 파싱하고, 없으면(기본값) 기존 RSS 2.0 방식을 그대로 씁니다.
_ATOM_NS = "{http://www.w3.org/2005/Atom}"


def fetch_rss_feed(name, feed_info, timeout=20, max_retries=3):
    """
    RSS(또는 Atom) 피드 하나를 받아서 [{title, link, pub_date, description}, ...] 형태로 파싱.

    NOTE (수정 사항 v1.3 — 인코딩 재확인): 원래는 feed_info에 미리 적어둔 인코딩
    (외교부는 "euc-kr")을 무조건 믿고 그걸로 디코딩했는데, 실제로 브라우저에서
    직접 외교부 RSS를 다시 받아보니 XML 선언 자체가
    <?xml version="1.0" encoding="UTF-8"?> 로 바뀌어 있었습니다 (예전에 EUC-KR로
    확인했던 게 그 사이에 바뀐 것으로 보임). 그런데도 코드는 여전히 EUC-KR로
    강제 디코딩하고 있어서, 한글 제목이 전부 깨진 채로 DB에까지 들어가고
    있었습니다 (issue_gov_match에서 한글 키워드 매칭도 당연히 안 됐을 것).

    같은 실수가 다른 피드나 나중에 또 재발하지 않도록, feed_info의 encoding을
    무조건 믿지 않고 응답 바이트의 XML 선언(<?xml ... encoding="...">)을 먼저
    읽어서 그게 있으면 그걸 최우선으로 씁니다. XML 선언에 명시가 없을 때만
    feed_info에 적어둔 값(또는 기본 utf-8)으로 대체합니다.
    """
    url = feed_info["url"]
    fallback_encoding = feed_info.get("encoding", "utf-8")

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
            r.raise_for_status()

            prolog_match = _XML_PROLOG_ENCODING_RE.match(r.content[:200])
            encoding = prolog_match.group(1).decode("ascii").lower() if prolog_match else fallback_encoding

            # requests가 자동 감지한 인코딩(r.encoding)은 신뢰하지 않고, 위에서 정한
            # (XML 선언 우선, 없으면 feed_info) 인코딩으로 디코딩합니다.
            raw = r.content.decode(encoding, errors="replace")

            root = ET.fromstring(raw)
            items = []

            if feed_info.get("format") == "atom":
                for entry in root.findall(f"{_ATOM_NS}entry"):
                    title = (entry.findtext(f"{_ATOM_NS}title") or "").strip()
                    link = ""
                    for link_el in entry.findall(f"{_ATOM_NS}link"):
                        # rel 속성이 없으면 기본이 "alternate"(사람이 읽는 HTML 페이지).
                        # self/다른 rel도 섞여 나올 수 있어서 alternate만 골라 씀.
                        if link_el.get("rel", "alternate") == "alternate":
                            link = link_el.get("href", "").strip()
                            break
                    pub_date = (entry.findtext(f"{_ATOM_NS}updated") or "").strip()
                    desc = entry.findtext(f"{_ATOM_NS}summary") or entry.findtext(f"{_ATOM_NS}content") or ""
                    items.append({
                        "source": name,
                        "source_type": feed_info.get("source_type", "unknown"),
                        "title": title,
                        "link": link,
                        "pub_date": pub_date,
                        "description": desc[:500],
                    })
            else:
                for item in root.findall(".//item"):
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    pub_date = (item.findtext("pubDate") or "").strip()
                    desc = item.findtext("description") or ""
                    items.append({
                        "source": name,
                        "source_type": feed_info.get("source_type", "unknown"),
                        "title": title,
                        "link": link,
                        "pub_date": pub_date,
                        "description": desc[:500],
                    })
            return items

        except (requests.exceptions.RequestException, ET.ParseError) as e:
            print(f"  ✗ {name} 시도 {attempt}/{max_retries} 실패: {str(e)[:150]}")
            if attempt < max_retries:
                time.sleep(3 * attempt)

    return []


def match_issue(title, description):
    """
    기사 제목+요약에 어떤 이슈 키워드가 들어있는지 확인해서
    매칭되는 이슈 이름 리스트를 반환합니다. (여러 이슈에 매칭될 수 있음)
    """
    text = f"{title} {description}".lower()
    matched = []
    for issue_name, keywords in ISSUE_MATCH_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            matched.append(issue_name)
    return matched


def collect_all_gov_announcements():
    """
    전체 정부 RSS 피드를 수집하고, 이슈별로 매칭해서 저장합니다.
    """
    print("\n" + "=" * 60)
    print("🏛  Government Announcements Collection (초안 v1)")
    print("=" * 60)

    all_items = []
    for name, feed_info in GOV_FEEDS.items():
        print(f"\n📡 수집 중: {name}")
        print(f"   {feed_info['url']}")
        items = fetch_rss_feed(name, feed_info)
        print(f"   ✓ {len(items)}건 수집")
        for item in items:
            item["matched_issues"] = match_issue(item["title"], item["description"])
        all_items.extend(items)
        time.sleep(1.0)  # 매너 있게 요청 사이 간격 두기

    # 이슈별로 재구성 -- 어떤 정부가 어떤 이슈에 대해 언제 뭐라고 했는지
    by_issue = {}
    for item in all_items:
        for issue in item["matched_issues"]:
            by_issue.setdefault(issue, []).append(item)

    today = datetime.now().strftime("%Y%m%d")

    all_path = f"{DATA_DIR}/all_announcements_{today}.json"
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 전체 {len(all_items)}건 저장: {all_path}")

    by_issue_path = f"{DATA_DIR}/by_issue_{today}.json"
    with open(by_issue_path, "w", encoding="utf-8") as f:
        json.dump(by_issue, f, ensure_ascii=False, indent=2)
    print(f"✓ 이슈별 매칭 결과 저장: {by_issue_path}")

    unmatched = [item for item in all_items if not item["matched_issues"]]
    print(f"\n📊 이슈별 매칭 건수 (매칭 안 된 {len(unmatched)}건 제외):")
    for issue, items in sorted(by_issue.items(), key=lambda x: -len(x[1])):
        print(f"   • {issue}: {len(items)}건")

    return all_items, by_issue


if __name__ == "__main__":
    collect_all_gov_announcements()
