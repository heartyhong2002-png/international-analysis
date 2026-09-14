"""
prototype_local_expert_sources.py — 현지 언론(local_media) + 전문가 분석(expert_analysis) 수집 프로토타입
================================================================================

⚠️ 컨트롤타워(③) 세션이 만든 프로토타입입니다. 준기님이 "현지 언론이랑 전문가
의견도 수집하고 싶다"고 하셔서, 기존 ADR-001 구조(source_type: official_statement /
state_media_news / news)에 두 레이어를 새로 추가하는 첫 시도입니다.

## 왜 기존 "news" 파이프라인(prototype_all_in_one.py)과 분리했는가

`prototype_all_in_one.py`(②번 오픈소스 LLM 트랙 소유 파일)의 TONE_PROMPT는
ADR-001 addendum(2026-09-14)이 정의한 "비판적 = narrative적으로 특정 주체를
비난할 때만" 기준으로 설계되어 있습니다. 이 기준은 사실 전달형 뉴스에는 잘
맞지만, 싱크탱크 리포트·전문가 칼럼처럼 **원래부터 주장하는 글**에 그대로
적용하면 전문가 의견 대부분이 자동으로 "비판적"에 몰릴 위험이 있습니다
(정부·정책을 비판하는 게 전문가 분석 특유의 기능이기 때문 — 톤을 재는 게
아니라 "무슨 주장을 하는지"를 뽑아내는 게 더 유용함).

그래서 이 프로토타입은 톤 분류 대신, `official_statement`용으로 이미 설계된
`prototype_llm_tone_extraction.py`의 "주장 구조화 추출" 패턴을 재사용해서
전문가 분석 전용 추출 스키마(EXPERT_ANALYSIS_PROMPT)를 새로 만듭니다.
`local_media`는 반대로 일반 뉴스 기사와 성격이 같아서(사실 전달형이 다수),
기존 TONE_PROMPT를 그대로 재사용하되 AllSides가 커버하지 못하는 해외 현지
매체를 위해 별도의 "출처 성향(source_orientation)" 태그를 추가합니다.

## 검증 상태 (2026-09-14, 클라우드 세션에서 WebFetch로 실제 응답 확인)

✅ 검증 완료 — 아래 LOCAL_EXPERT_FEEDS 5개 전부 실제 RSS 2.0(rss/channel/item)
   응답과 최근 게시물 제목까지 확인함 (허위/추정 URL 아님)
✅ 검증 완료 — EXPERT_ANALYSIS_PROMPT 응답 파싱 로직: `--self-test`로 확인 가능
✅ 검증 완료 — `tag_article_with_source_awareness()` 추가 (2026-09-14, 2차 수정):
   실제 5개 소스의 최신 헤드라인 8건으로 1차 프로토타입을 돌려보니 7건(87.5%)이
   `unclassified`로 빠지는 걸 발견함 — 원인은 "국가는 맞지만(예: North Korea,
   China) 이슈 키워드(nuclear test/missile 등)가 너무 좁아서" 매칭이 안 된
   것. `unclassified`는 LLM을 아예 안 부르는 설계라서, 이대로 두면 모처럼
   추가한 전문가/현지언론 소스 상당수가 버려짐. `news`(NPR/BBC)는 완전히
   무관한 기사가 많이 섞이므로 unclassified 필터링이 필요하지만, 이 두
   source_type은 애초에 국제정세 전문 소스를 사람이 골라 붙인 것이라
   "국가만 맞아도" 관련 있을 확률이 훨씬 높다고 판단 — 그래서 `news`는 그대로
   두고 `local_media`/`expert_analysis`에 한해서만 "국가 매칭 + 이슈 키워드
   불일치"를 `unclassified`가 아니라 `ambiguous`(LLM 판단에 맡김)로 승격시킴.
   `tag_article()` 자체(prototype_all_in_one.py, ②번 트랙 소유)는 안 건드리고,
   그 결과를 후처리하는 방식으로 구현 — 아래 self-test로 실제 8건 재현 확인함
   (승격 전 unclassified 7건 → 승격 후 ambiguous 6건, matched 1건, unclassified
   1건[Somalia — COUNTRY_ALIASES에 아예 없는 국가라 국가 매칭 자체가 안 됨,
   의도대로 unclassified 유지]).
❌ 미검증 — 실제 Ollama 호출 (클라우드 세션에는 로컬 Ollama가 없음, 로컬에서
   `ollama serve` 켜고 재검증 필요 — prototype_llm_tone_extraction.py와 동일한 한계)
❌ 미구현 — DB 적재. SCHEMA_DDL_ADDENDUM만 제안, build_database.py는 안 건드림
   (①SQL 트랙 검토 필요 — prototype_llm_tone_extraction.py와 같은 패턴)
❌ 미구현 — prototype_all_in_one.py와의 실제 연결. 이 파일 맨 아래 "②번 LLM
   트랙에 제안하는 통합 방법" 섹션에 정확한 코드 스니펫만 남김 (파일 직접
   수정 안 함 — ②번 트랙 소유 파일이라 규칙상 건드리지 않음)

## 시도했지만 안 된 것 (다음에 또 시도하지 않도록 기록)

- Arms Control Association(armscontrol.org/rss.xml) — 200 응답이지만 실제로는
  RSS가 아니라 일반 HTML 페이지를 반환함 (rss/channel/item 태그 없음)
- Kyiv Independent(kyivindependent.com/feed/) — 404. 실제 피드 경로가 바뀌었거나
  다른 경로일 수 있음, 다음에 재확인 필요
- Haaretz — WebFetch가 robots.txt로 차단함. 클라우드 세션 한정 문제일 수 있으니
  로컬 환경에서 requests + 브라우저형 User-Agent(gov_announcements_collector.py의
  REQUEST_HEADERS 참고)로 재시도 권장
- Times of Israel — gov_announcements_collector.py 주석에도 이미 기록되어 있듯
  Cloudflare 봇 챌린지로 차단됨 (cloudscraper 등 별도 라이브러리 없이는 불가)

## 커버리지에 대한 솔직한 평가

21개 이슈 중 이번에 검증된 5개 피드가 실제로 신호를 채워주는 건 유럽
(Ukraine_War/EU_Russia), 중동(Israel_Palestine/Iran_Nuclear/Middle_East_Energy),
아태(North_Korea_Nuclear), 아프리카 일부(Sudan_Conflict 등 Crisis Group
커버리지)뿐입니다. 남미(Venezuela/Brazil/Argentina)와 나머지 아태 이슈
(Taiwan_Strait/India_Pakistan/South_China_Sea/Japan_Korea/Myanmar_Crisis)는
이번 라운드에 맞는 소스를 못 찾았습니다 — 다음 라운드 후보로 남겨둠.

사용법:
    python scripts/prototype_local_expert_sources.py --self-test
    python scripts/prototype_local_expert_sources.py                # 수집 + 규칙기반 태깅까지
    python scripts/prototype_local_expert_sources.py --with-llm      # + Ollama 구조화 추출 (로컬 전용)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

# ============================================================================
# prototype_all_in_one.py(②번 트랙 소유)의 태깅/편향lookup 로직을 재사용합니다
# (이슈 매칭 로직을 두 군데서 따로 관리하면 반드시 어긋나게 되어 있어서 —
# ISSUE_MATCH_KEYWORDS/ISSUES가 이미 gov_announcements_collector.py와
# prototype_all_in_one.py 두 군데서 별도로 진화한 전례가 있음).
# ⚠️ 이 말은 곧, ②번 트랙이 그 파일의 함수 시그니처(tag_article, match_issues,
# OutletBiasLookup 등)를 바꾸면 이 프로토타입도 같이 깨질 수 있다는 뜻입니다.
# ============================================================================
_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from prototype_all_in_one import (  # noqa: E402
    OutletBiasLookup,
    MODEL_BY_LANGUAGE,
    tag_article,
    _call_ollama,
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

REQUEST_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
}

# ============================================================================
# 검증된 현지언론(local_media) + 전문가분석(expert_analysis) 피드 목록
# ============================================================================
# source_type:
#   - "local_media": 일반 현지 언론. 기존 TONE_PROMPT(narrative 기준)로 톤 분류.
#   - "expert_analysis": 싱크탱크/전문가 칼럼. EXPERT_ANALYSIS_PROMPT로 주장·전망 추출
#     (톤 분류 안 함 — 이유는 파일 상단 docstring 참고).
#
# orientation: AllSides가 커버하지 못하는 해외 매체를 위한 수동 성향 태그.
# 이건 "이 매체가 신뢰할 수 없다"는 뜻이 아니라, "어떤 입장에서 쓰였는지"를
# 분석 단계에서 감안하기 위한 참고 정보입니다(이란 국영매체 IRNA를 state_media로
# 태깅한 것과 같은 취지 — gov_announcements_collector.py 참고).
LOCAL_EXPERT_FEEDS = [
    {
        "name": "The Moscow Times (영문판)",
        "url": "https://www.themoscowtimes.com/rss/news",
        "source_type": "local_media",
        "country": "RU",
        "lang": "en",
        "orientation": "independent-in-exile (2022년 러시아 내 활동 금지 이후 암스테르담/베를린 기반으로 계속 운영)",
        "related_issues": ["Ukraine_War", "EU_Russia", "Baltic_Security"],
        "verified_at": "2026-09-14",
        "notes": "러시아 정부 공식 입장이 아니라 이를 비판적으로 다루는 독립 매체 — EU_Russia 등에서 정부 발표(mid.ru)와 대조군으로 유용.",
    },
    {
        "name": "Al-Monitor (중동 전문 매체)",
        "url": "https://www.al-monitor.com/rss",
        "source_type": "expert_analysis",
        "country": "US",  # 워싱턴 소재, 중동 각국 현지 통신원 네트워크로 운영
        "lang": "en",
        "orientation": "중동 전문 저널리즘 (현지 통신원 기고 모델, 특정 정부 소유 아님)",
        "related_issues": ["Israel_Palestine", "Iran_Nuclear", "Middle_East_Energy"],
        "verified_at": "2026-09-14",
        "notes": "일반 뉴스보다 배경분석/전문가 코멘트 비중이 높아 expert_analysis로 분류. Al Jazeera(국영, state_media_news)와 대조군.",
    },
    {
        "name": "Chatham House — Expert Comment",
        "url": "https://www.chathamhouse.org/path/83/feed.xml",
        "source_type": "expert_analysis",
        "country": "GB",
        "lang": "en",
        "orientation": "영국 소재 초당파 국제정세 싱크탱크",
        "related_issues": [],  # 전 지역 커버 — 이슈 매칭은 규칙기반 태깅에 맡김
        "verified_at": "2026-09-14",
        "notes": "실제 확인한 최신 항목이 Canada 관세, 인도-중국 관계 등 이미 추적 중인 이슈와 바로 겹침(2026-09-14 확인).",
    },
    {
        "name": "International Crisis Group — Global",
        "url": "https://www.crisisgroup.org/rss",
        "source_type": "expert_analysis",
        "country": "BE",  # 브뤼셀 본부
        "lang": "en",
        "orientation": "분쟁 예방 전문 싱크탱크 (CrisisWatch 월간 국가별 추적 운영)",
        "related_issues": ["Sudan_Conflict", "Ethiopia_Crisis", "Congo_Minerals",
                            "Myanmar_Crisis", "Venezuela_Crisis"],
        "verified_at": "2026-09-14",
        "notes": "지역별 세부 피드(rss/1=Africa, rss/30=Asia-Pacific 등)도 있는 것으로 확인됐으나, 이번엔 전체 피드만 검증함.",
    },
    {
        "name": "38 North (북한 전문 분석)",
        "url": "https://www.38north.org/feed/",
        "source_type": "expert_analysis",
        "country": "US",
        "lang": "en",
        "orientation": "Stimson Center 산하 북한 전문 분석 플랫폼",
        "related_issues": ["North_Korea_Nuclear"],
        "verified_at": "2026-09-14",
        "notes": "North_Korea_Nuclear 이슈에 가장 특화된 소스 — 실제 최근 게시물이 북중 경협·경제개발계획 등 이슈와 직결됨.",
    },
]

# review_log.csv에서 outlet_bias(AllSides)가 못 찾는 도메인을 위한 보조 성향 태그.
# LOCAL_EXPERT_FEEDS의 "orientation"과 같은 값을 도메인 기준으로도 조회할 수 있게
# 별도 dict로도 둠 (다른 경로로 수집된 기사의 도메인 매칭에도 재사용 가능하도록).
LOCAL_OUTLET_ORIENTATION = {
    feed["url"].split("/")[2].replace("www.", ""): feed["orientation"]
    for feed in LOCAL_EXPERT_FEEDS
}


def tag_article_with_source_awareness(article: dict) -> dict:
    """`tag_article()`(prototype_all_in_one.py, ②번 트랙 소유)을 그대로 호출하되,
    source_type이 local_media/expert_analysis인 경우엔 "국가는 맞고 이슈
    키워드는 안 맞아서 unclassified로 빠진" 케이스를 ambiguous로 승격시킨다.

    이유는 파일 상단 docstring의 "검증 상태" 섹션(2차 수정) 참고 — 실제
    데이터로 87.5%가 unclassified로 새는 걸 확인하고 추가한 로직이다.

    ⚠️ tag_article() 자체는 안 건드림 — 반환값을 후처리만 한다. news에는
    적용 안 함(②번 트랙의 기존 unclassified 필터링 효과가 news에서는
    여전히 유효하고 필요하기 때문 — ADR-001 관련 대화에서 확인된 "Nicolas
    Cage 싱크홀" 같은 완전 무관 기사가 news에는 섞여 들어오지만, 사람이
    직접 골라 붙인 local_media/expert_analysis 피드에는 그럴 위험이 낮음).
    """
    article = tag_article(article)
    if (
        article.get("source_type") in ("local_media", "expert_analysis")
        and article.get("tag_status") == "unclassified"
        and article.get("countries_involved")
    ):
        article["tag_status"] = "ambiguous"
        article["llm_review_needed"] = True
        article["tag_upgrade_reason"] = "source_aware_upgrade: country matched, issue keyword did not"
    else:
        article["tag_upgrade_reason"] = None
    return article


def fetch_local_expert_articles(feeds: list[dict] | None = None) -> list[dict]:
    """LOCAL_EXPERT_FEEDS를 수집해서 prototype_all_in_one.py의 article dict와
    같은 형태(+source_type/orientation 등 추가 필드)로 반환합니다."""
    feeds = feeds if feeds is not None else LOCAL_EXPERT_FEEDS
    articles = []
    for feed in feeds:
        parsed = feedparser.parse(feed["url"], request_headers=REQUEST_HEADERS)
        if parsed.bozo:
            print(f"[fetch] 경고: {feed['name']} 파싱 중 문제 발생 - {parsed.bozo_exception}")
            continue
        for entry in parsed.entries:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source_url": feed["url"].split("/")[2],
                "source_name": feed["name"],
                "source_type": feed["source_type"],
                "source_orientation": feed["orientation"],
                "language": feed["lang"],
                "country": feed["country"],
            })
        print(f"[fetch] {feed['name']}: {len(parsed.entries)}건 수집")
    return articles


# ============================================================================
# 전문가 분석 전용 추출 스키마 (톤 분류 대신 — 이유는 상단 docstring 참고)
# ============================================================================

EXPERT_ANALYSIS_PROMPT = """다음은 싱크탱크/전문가 분석 글이다. 이 글은 원래부터 주장하는
글이므로 "우호적/중립적/비판적" 같은 톤 분류는 하지 않는다. 대신 아래 항목을 뽑아라.

기사 제목: {title}
기사 본문: {summary}

1. author_or_org: 글쓴이 또는 발행 기관명 (모르면 발행처 이름)
2. key_argument: 이 글의 핵심 주장을 한 문장으로 (narrative 평가 여부와 무관하게 있는 그대로)
3. forecast: 이 글이 명시적으로 예측/전망하는 내용이 있으면 한 문장으로, 없으면 null
4. forecast_horizon: 전망이 가리키는 시점 (예: "3개월 내", "2027년 총선 이후" 등), 없으면 null
5. evidence_basis: 주장의 근거로 든 사실/데이터/사건을 한 가지만 짧게
6. stance_toward: 이 글이 지지하거나 비판하는 대상(국가/기관/인물명), 다수면 대표 1개, 없으면 null

반드시 아래 JSON 형식으로만 답하라. 다른 설명은 절대 붙이지 마라.
{{
  "author_or_org": "...",
  "key_argument": "...",
  "forecast": "..." 또는 null,
  "forecast_horizon": "..." 또는 null,
  "evidence_basis": "...",
  "stance_toward": "..." 또는 null
}}"""

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_EXPECTED_EXPERT_KEYS = {
    "author_or_org", "key_argument", "forecast",
    "forecast_horizon", "evidence_basis", "stance_toward",
}


def parse_expert_response(raw_text: str) -> dict | None:
    """EXPERT_ANALYSIS_PROMPT 응답을 파싱. prototype_llm_tone_extraction.py의
    parse_llm_response()와 같은 방어 로직(코드펜스/군더더기 설명 대응)을 재사용.
    필수 키가 하나라도 없으면 신뢰하지 않고 None을 반환한다."""
    match = _JSON_BLOCK_RE.search(raw_text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not _EXPECTED_EXPERT_KEYS.issubset(data.keys()):
        return None
    return data


def extract_expert_argument(article: dict) -> dict:
    """expert_analysis 기사 하나에 대해 주장/전망 구조화 추출을 수행."""
    model = MODEL_BY_LANGUAGE.get(article.get("language", "en"), "mistral")
    prompt = EXPERT_ANALYSIS_PROMPT.format(
        title=article.get("title", ""),
        summary=(article.get("summary", "") or "")[:1200],
    )
    raw = _call_ollama(model, prompt, temperature=0.3)
    # _call_ollama가 이미 json.loads()까지 하므로(prototype_all_in_one.py 참고),
    # 여기서는 필수 키 검증만 한 번 더 한다.
    if isinstance(raw, dict) and _EXPECTED_EXPERT_KEYS.issubset(raw.keys()):
        article["expert_extraction"] = raw
    else:
        article["expert_extraction"] = None
    return article


def _self_test() -> bool:
    """Ollama 없이 파싱 로직만 검증. mock 응답 4종(정상/코드펜스/키 누락/파싱실패)."""
    print("=" * 60)
    print("🧪 self-test: parse_expert_response()")
    print("=" * 60)

    cases = [
        ("정상 JSON", '''{
          "author_or_org": "Chatham House",
          "key_argument": "캐나다의 보복 관세는 트럼프 무역전략의 시험대다",
          "forecast": "협상이 결렬되면 캐나다산 자동차 관세가 추가로 인상될 것",
          "forecast_horizon": "6개월 내",
          "evidence_basis": "캐나다가 이미 미국산 철강에 보복관세를 부과한 선례",
          "stance_toward": "미국 무역대표부"
        }'''),
        ("코드펜스로 감싸짐", '''```json
        {"author_or_org": "38 North", "key_argument": "북중 경협이 제재 우회 통로로 확대되고 있다",
         "forecast": null, "forecast_horizon": null,
         "evidence_basis": "신규 물류 거점 개통 정황", "stance_toward": null}
        ```'''),
        ("필수 키 누락(신뢰 안 함)", '{"author_or_org": "x", "key_argument": "y"}'),
        ("JSON 아님(파싱 실패)", "이 글은 분석하기 어렵습니다."),
    ]

    all_ok = True
    for name, raw in cases:
        result = parse_expert_response(raw)
        if name in ("정상 JSON", "코드펜스로 감싸짐"):
            ok = result is not None and _EXPECTED_EXPERT_KEYS.issubset(result.keys())
        else:
            ok = result is None
        status = "✓" if ok else "✗"
        if not ok:
            all_ok = False
        print(f"  {status} {name}: {'파싱 성공' if result else '파싱 실패(의도대로)'}")

    print("\n" + ("✅ 전부 통과" if all_ok else "❌ 일부 실패 — parse_expert_response() 점검 필요"))
    return all_ok


# 2026-09-14 실제 WebFetch로 확인한 5개 소스의 진짜 최신 헤드라인 8건.
# tag_article_with_source_awareness()의 회귀 테스트용으로 고정해둔 것 —
# 이 값을 바꾸면 "실제 데이터로 87.5%가 샜다"는 근거 자체가 바뀌니 그대로 둘 것.
_REAL_HEADLINE_SAMPLES = [
    ("expert_analysis", "www.38north.org", "New North Korea-China Link Appears Close to Opening",
     "Analysts say the new cross-border trade facility could ease sanctions pressure on Pyongyang."),
    ("expert_analysis", "www.38north.org", "North Korea Makes Significant Progress on New Trade Facility With China",
     "Satellite imagery shows construction nearing completion at the border crossing."),
    ("expert_analysis", "www.crisisgroup.org", "Israeli Actors Should Face a Choice: Building in E1 or Business with Europe",
     "Crisis Group argues the EU should link settlement expansion to trade ties with Israel."),
    ("expert_analysis", "www.crisisgroup.org", "Somalia's End-of-year Cliffhanger",
     "Analysis of Al-Shabaab offensive and government response."),
    ("expert_analysis", "www.chathamhouse.org", "Canada's retaliatory tariffs put Trump's trade strategy to the test",
     "Chatham House experts assess the risk of an escalating US-Canada tariff war."),
    ("expert_analysis", "www.chathamhouse.org", "North Korea's military partnership with Russia has consequences far beyond Ukraine",
     "The arms-for-technology exchange between Pyongyang and Moscow is reshaping East Asian security."),
    ("expert_analysis", "www.al-monitor.com", "New report of attack on Strait of Hormuz shipping fans fears of threats to oil supplies",
     "Gulf shipping companies report a suspected attack near the strait amid Iran-US tensions."),
    ("expert_analysis", "www.al-monitor.com", "Houthis say hit Saudi base after renewed fighting with Yemeni govt forces",
     "The Houthi movement claimed responsibility for a strike on a Saudi military installation."),
]


def _self_test_tagging() -> bool:
    """tag_article_with_source_awareness()가 실제 헤드라인 8건에 대해 의도한
    대로 동작하는지 확인. 기대값: unclassified가 7건 → 1건(Somalia — 애초에
    COUNTRY_ALIASES에 없는 국가라 국가 매칭 자체가 안 됨, 승격 대상이 아님)으로
    줄고, 그 6건은 ambiguous로 승격, 기존에 matched였던 1건(Canada 관세)은
    그대로 matched 유지."""
    print("=" * 60)
    print("🧪 self-test: tag_article_with_source_awareness() (실제 헤드라인 8건)")
    print("=" * 60)

    results = []
    for source_type, domain, title, summary in _REAL_HEADLINE_SAMPLES:
        article = {
            "title": title, "summary": summary, "source_type": source_type,
            "source_url": domain, "language": "en",
        }
        article = tag_article_with_source_awareness(article)
        results.append(article["tag_status"])
        print(f"  [{article['tag_status']:<12}] {title[:70]}")

    counts = {s: results.count(s) for s in ("matched", "ambiguous", "unclassified")}
    print(f"\n결과: matched={counts['matched']}, ambiguous={counts['ambiguous']}, "
          f"unclassified={counts['unclassified']}")

    expected = {"matched": 1, "ambiguous": 6, "unclassified": 1}
    ok = counts == expected
    print(("✅ 기대값과 일치" if ok else f"❌ 기대값({expected})과 다름 — 로직 또는 기대값 재점검 필요"))
    return ok


# ============================================================================
# 오케스트레이터 — review_log.csv에 이어붙이는 방식 (덮어쓰지 않음)
# ============================================================================
# NOTE: prototype_all_in_one.py의 _write_review_log()는 매 실행마다 review_log.csv를
# 완전히 새로 씀(writer.writeheader() 후 그 실행분만 기록). 이 프로토타입은 독립
# 실행이므로 같은 파일을 덮어쓰지 않도록 별도 파일(local_expert_review_log.csv)에
# append 모드로 쌓습니다 — 두 세션이 review_log.csv를 두고 경쟁하면 위험하다는
# project-handoff.md의 경고를 따른 것입니다. 합치는 건 ②번 트랙이 스키마를
# 최종 확정한 뒤에 하는 게 안전합니다.

LOCAL_EXPERT_LOG_PATH = DATA_DIR / "local_expert_review_log.csv"

LOCAL_EXPERT_LOG_FIELDS = [
    # NOTE (2차 수정): 처음 버전엔 issue_ids/countries_involved/tag_status 등
    # tag_article()이 실제로 만들어내는 필드들이 빠져 있었음(DictWriter의
    # extrasaction="ignore" 때문에 조용히 버려지고 있었음 — CSV를 열어봐야
    # 알 수 있는 종류의 실수라 self-test로는 못 잡았고, 실제 태깅 결과를
    # 눈으로 확인하다가 발견함). review_log.csv(REVIEW_LOG_FIELDS)와 최대한
    # 같은 컬럼명을 씀 — 나중에 두 CSV를 합칠 때 이름이 갈라져 있으면 또
    # ADR001_INTEGRATION_HANDOFF.md의 article_id 사례처럼 조율거리가 생기므로.
    "article_id", "language", "issue_ids", "continent", "countries_involved", "tag_status",
    "tag_upgrade_reason",  # 이 프로토타입에서 새로 추가한 필드 (tag_article_with_source_awareness 참고)
    "llm_review_needed", "source_type", "source_name", "source_url", "source_orientation",
    "outlet_bias", "country", "title", "link",
    # local_media 전용 (기존 TONE_PROMPT 재사용)
    "llm_label", "llm_evidence_quote",
    # expert_analysis 전용
    "author_or_org", "key_argument", "forecast", "forecast_horizon",
    "evidence_basis", "stance_toward",
    "human_label", "correction_note", "reviewed_at", "collected_at",
]


def run(with_llm: bool = False) -> list[dict]:
    articles = fetch_local_expert_articles()
    bias_lookup = OutletBiasLookup()  # AllSides — 이번 소스들은 대부분 매칭 안 될 것으로 예상(정상)

    rows = []
    for article in articles:
        article["article_id"] = str(uuid.uuid4())[:8]
        article["collected_at"] = datetime.now(timezone.utc).isoformat()
        article = tag_article_with_source_awareness(article)  # ②번 트랙의 태깅 + source-aware 승격
        article = bias_lookup.tag_article(article)  # AllSides에 없으면 outlet_bias=None (정상)

        if with_llm:
            try:
                if article["source_type"] == "expert_analysis":
                    article = extract_expert_argument(article)
                    extraction = article.get("expert_extraction") or {}
                    article.update({
                        "author_or_org": extraction.get("author_or_org"),
                        "key_argument": extraction.get("key_argument"),
                        "forecast": extraction.get("forecast"),
                        "forecast_horizon": extraction.get("forecast_horizon"),
                        "evidence_basis": extraction.get("evidence_basis"),
                        "stance_toward": extraction.get("stance_toward"),
                    })
                else:  # local_media -> 기존 톤 분류 재사용
                    from prototype_all_in_one import classify_tone
                    article = classify_tone(article)
            except Exception as e:  # noqa: BLE001 - 프로토타입 단계의 방어적 처리
                print(f"[pipeline] LLM 처리 실패 ({article.get('title', '')[:30]}...): {e}")

        rows.append(article)

    _write_local_expert_log(rows)
    return rows


def _write_local_expert_log(rows: list[dict]) -> None:
    LOCAL_EXPERT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = LOCAL_EXPERT_LOG_PATH.exists()
    with open(LOCAL_EXPERT_LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=LOCAL_EXPERT_LOG_FIELDS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for row in rows:
            row = dict(row)
            row.setdefault("human_label", "")
            row.setdefault("correction_note", "")
            row.setdefault("reviewed_at", "")
            writer.writerow(row)
    print(f"[pipeline] {len(rows)}건을 {LOCAL_EXPERT_LOG_PATH}에 append했습니다. (2차 검수용)")


# ============================================================================
# ①SQL 트랙 검토용 — expert_analysis 추출 결과 저장 DDL 제안 (프로토타입)
# prototype_llm_tone_extraction.py의 SCHEMA_DDL과 같은 패턴, 같은 이유로
# build_database.py는 안 건드림.
# ============================================================================
SCHEMA_DDL_ADDENDUM = """
-- LLM이 전문가 분석 글에서 뽑아낸 주장/전망 (톤 라벨 없음 — 이유는 파일 상단 참고)
CREATE TABLE IF NOT EXISTS expert_analysis_extractions (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    article_id         VARCHAR(20) NOT NULL,   -- local_expert_review_log.csv의 article_id
    source_name        VARCHAR(200),
    author_or_org      VARCHAR(200),
    key_argument       TEXT,
    forecast           TEXT,
    forecast_horizon   VARCHAR(100),
    evidence_basis     TEXT,
    stance_toward      VARCHAR(200),
    extraction_model   VARCHAR(100),
    extracted_at       DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 참고: article_id를 review_log 계열과 어떻게 FK로 묶을지는
-- ADR001_INTEGRATION_HANDOFF.md에 이미 적힌 미해결 이슈(해시 문자열 article_id vs
-- 정수 PK)와 같은 문제라 여기서 새로 풀지 않음 — ①SQL 트랙이 한 번에 정리 권장.
"""


def main():
    parser = argparse.ArgumentParser(
        description="현지언론(local_media)/전문가분석(expert_analysis) 수집 프로토타입"
    )
    parser.add_argument("--self-test", action="store_true", help="Ollama 없이 파싱 로직만 검증")
    parser.add_argument("--with-llm", action="store_true", help="Ollama 호출까지 실행 (로컬 전용)")
    args = parser.parse_args()

    if args.self_test:
        ok_parse = _self_test()
        print()
        ok_tag = _self_test_tagging()
        sys.exit(0 if (ok_parse and ok_tag) else 1)

    run(with_llm=args.with_llm)


if __name__ == "__main__":
    main()


# ============================================================================
# ②번 LLM 트랙에 제안하는 통합 방법 (이 파일은 안 건드리고, 여기 주석으로만 제안)
# ============================================================================
# prototype_all_in_one.py를 이렇게 바꾸면 이 프로토타입 없이도 같은 파이프라인
# 하나로 합칠 수 있습니다 (제가 직접 수정 안 함 — ②번 트랙 소유 파일):
#
# 1. RSS_FEEDS(flat list of str)를 메타데이터 포함 구조로 변경:
#
#    RSS_FEEDS = [
#        {"url": "https://feeds.npr.org/1004/rss.xml", "source_type": "news", "lang": "en"},
#        {"url": "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
#         "source_type": "news", "lang": "en"},
#    ] + LOCAL_EXPERT_FEEDS  # 이 파일에서 import
#
# 2. fetch_articles()가 "language": "en" 하드코딩 대신 feed["lang"]을 쓰도록 수정
#    (지금은 전부 영어라 문제 안 됐지만, LOCAL_EXPERT_FEEDS를 합치면 여전히 전부
#    영어라 당장은 안 깨집니다 — 나중에 비영어 로컬매체 추가 시 필수)
#
# 3. run()의 `article["source_type"] = "news"` 하드코딩(437번째 줄)을
#    `article["source_type"] = feed_meta.get("source_type", "news")`로 변경
#
# 4. run()의 LLM 처리 분기(451번째 줄)에서 source_type == "expert_analysis"면
#    extract_expert_argument()(이 파일에서 import)를, 그 외엔 기존
#    extract_structured()+classify_tone()을 호출하도록 분기 추가
#
# 5. (2차 수정, 2026-09-14 추가) run()의 `article = tag_article(article)` 호출을
#    `tag_article_with_source_awareness(article)`(이 파일에서 import, 또는
#    로직을 그대로 tag_article() 안으로 흡수)로 바꾸면, local_media/
#    expert_analysis 기사가 "국가는 맞는데 이슈 키워드가 안 맞아서"
#    unclassified로 새는 문제(실측 87.5%, self-test 참고)가 줄어듭니다.
#    ⚠️ 이 로직은 news에는 적용하면 안 됨 — news는 무관한 기사를 걸러내는
#    용도로 unclassified가 필요하기 때문입니다.
#
# 이렇게 하면 review_log.csv 스키마에 컬럼 몇 개(source_orientation,
# tag_upgrade_reason, author_or_org, key_argument, forecast, forecast_horizon,
# evidence_basis, stance_toward)만 추가하면 되고, 이 프로토타입 파일(및
# local_expert_review_log.csv)은 폐기해도 됩니다.
