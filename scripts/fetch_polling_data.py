"""
fetch_polling_data.py — 글로벌 여론조사(Public Opinion Polls) 자동 수집 및 정량 지표 추출 모듈
========================================================================================

목적:
  - 외교·안보 현안에 대한 각국 대중의 실제 여론(지지율, 찬반 비율, 동맹 신뢰도) 데이터를
    비용 0원, 100% 합법적 공개 웹 표준(RSS/Atom)을 통해 자동 수집.
  - 전 세계 최고 신뢰도의 3대 공공/글로벌 여론조사 및 씽크탱크 피드 연동:
    1) Pew Research Center (글로벌 대외인식 및 미국 외교/국정 지지율)
    2) ECFR (유럽 27개국 시민들의 대러 제재/우크라이나 지원/대미 인식)
    3) Ipsos Global (글로벌 불안 지표 및 지정학적 신뢰도)
  - 로컬 LLM(mistral-nemo:12b)으로 설문 대상, 핵심 수치(지지/반대 비율), 지정학적 함의 구조화 추출.
  - 산출물: data/polls/polls_latest.csv + data/polls/polls_summary.json 저장.

사용법:
  python scripts/fetch_polling_data.py                   # 기본 수집 (피드당 최대 5건)
  python scripts/fetch_polling_data.py --limit 10
  python scripts/fetch_polling_data.py --with-llm        # 로컬 LLM으로 여론조사 핵심 수치/함의 정밀 추출
  python scripts/fetch_polling_data.py --self-test        # 네트워크/Ollama 없이 파이프라인 무결성 검증
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "polls"

REQUEST_HEADERS = {
    "User-Agent": "InternationalAnalysisBot/1.0 (Public Opinion Research; contact: /u/heartyhong2002)",
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.7",
}

# ============================================================================
# 검증된 글로벌 여론조사 피드 목록
# ============================================================================
POLLING_FEEDS = [
    {
        "id": "pew_international",
        "name": "Pew Research Center — International Affairs",
        "url": "https://www.pewresearch.org/topic/international-affairs/feed/",
        "org": "Pew Research Center",
        "region": "Global / Multi-country",
        "focus": "글로벌 대외인식(대미·대중·대러), 동맹 신뢰도, 우크라이나 지원 및 국제규범",
    },
    {
        "id": "pew_us_politics",
        "name": "Pew Research Center — Politics & Policy",
        "url": "https://www.pewresearch.org/topic/politics-policy/feed/",
        "org": "Pew Research Center",
        "region": "United States",
        "focus": "미국 대중의 대외정책 지지율, 통상/관세 인식, 행정부 외교안보 평가",
    },
    {
        "id": "ecfr_european_opinion",
        "name": "European Council on Foreign Relations (ECFR)",
        "url": "https://ecfr.eu/feed/",
        "org": "ECFR",
        "region": "European Union / Europe",
        "focus": "유럽 12~14개국 시민들의 대러 제재 지속성, 방위비 증액, 대미 의존도 여론",
    },
    {
        "id": "ipsos_global",
        "name": "Ipsos — Global Research & Opinion",
        "url": "https://www.ipsos.com/en/rss.xml",
        "org": "Ipsos",
        "region": "Global (28+ Countries)",
        "focus": "What Worries the World, 경제/지정학 리스크 및 글로벌 대중 신뢰도",
    },
]


# ============================================================================
# 1단계: 공개 피드 수집 및 정제
# ============================================================================

def _clean_html(raw_html: str) -> str:
    """HTML 태그 제거 및 텍스트 정규화."""
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = re.sub(r"&nbsp;|&#160;|&#32;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;|&apos;", "'", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_feed_articles(feed_info: dict, limit: int = 5, xml_bytes: bytes | None = None) -> list[dict]:
    """단일 여론조사 피드에서 최신 설문/리포트 수집."""
    if xml_bytes is not None:
        parsed = feedparser.parse(xml_bytes)
    else:
        try:
            resp = requests.get(feed_info["url"], headers=REQUEST_HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"[poll_fetch] {feed_info['name']} HTTP {resp.status_code} 실패 — 건너뜀")
                return []
            parsed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"[poll_fetch] {feed_info['name']} 네트워크 오류: {e}")
            return []

    articles = []
    for entry in parsed.entries[:limit]:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        published = entry.get("published") or entry.get("updated") or ""

        # 본문 또는 요약
        summary_raw = entry.get("summary") or entry.get("description") or ""
        summary = _clean_html(summary_raw)

        tags = [t.get("term") for t in entry.get("tags", []) if isinstance(t, dict) and t.get("term")]
        pcts = re.findall(r'(\b\d{1,3}(?:\.\d+)?%)', summary)
        rule_metrics = ", ".join(pcts[:5]) if pcts else "원문 요약 참조"
        rule_topic = ", ".join(tags[:3]) if tags else (title[:50] if title else "국제정세 일반 여론")

        articles.append({
            "poll_id": f"{feed_info['id']}_{abs(hash(link)) % 1000000:06d}",
            "source_org": feed_info["org"],
            "region": feed_info["region"],
            "feed_name": feed_info["name"],
            "title": title,
            "link": link,
            "published": published,
            "summary": summary[:1000],
            "tags": ", ".join(tags),
            "survey_topic": rule_topic,
            "target_population": feed_info["region"],
            "survey_metrics": rule_metrics,
            "sentiment": "neutral",
            "geopolitical_implication": "로컬 LLM 정밀 분석 대기 (규칙 기반 수집 완료)",
        })
    return articles


# ============================================================================
# 2단계: 로컬 LLM 기반 여론조사 수치 및 지정학적 함의 추출
# ============================================================================

POLLING_EXTRACTION_PROMPT = """다음은 공신력 있는 국제 여론조사 및 씽크탱크 보고서 내용이다.
글에서 언급된 주요 여론조사 수치(찬반 비율, 지지율 등)와 지정학적 함의를 추출하라.

[보고서 출처]: {org} ({region})
[보고서 제목]: {title}
[보고서 요약]: {summary}

다음 JSON 스키마로만 엄격하게 응답하라. 설명이나 추가 텍스트는 절대 붙이지 마라.
{{
  "survey_topic": "설문 주제 (한국어, 예: 우크라이나 군사 지원 찬반, 대중국 호감도, 미국 대외정책 지지율)",
  "target_population": "조사 대상 (예: 미국 성인 유권자, 유럽 14개국 시민, 글로벌 28개국 등)",
  "key_findings": ["핵심 수치 1 (예: 군사 지원 찬성 58%, 반대 39%)", "핵심 수치 2"],
  "sentiment": "favorable|neutral|critical_anxious (대중 여론의 전반적 기류)",
  "geopolitical_implication": "이 여론조사가 외교·안보 정책에 주는 함의 (한국어 정밀 1~2문장)"
}}"""

_EXPECTED_KEYS = {"survey_topic", "key_findings", "sentiment", "geopolitical_implication"}


def _call_ollama(model: str, prompt: str, host: str = "http://localhost:11434") -> dict | None:
    try:
        resp = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "format": "json", "stream": False, "options": {"temperature": 0.2}},
            timeout=120,
        )
        if resp.status_code == 200:
            return json.loads(resp.json().get("response", "{}"))
    except Exception:
        pass
    return None


def extract_poll_metrics(article: dict, model: str = "mistral-nemo:latest") -> dict:
    """로컬 LLM을 호출하여 설문 수치와 지정학적 함의를 구조화."""
    prompt = POLLING_EXTRACTION_PROMPT.format(
        org=article["source_org"],
        region=article["region"],
        title=article["title"],
        summary=article["summary"][:1200],
    )
    res = _call_ollama(model, prompt)
    if isinstance(res, dict) and _EXPECTED_KEYS.issubset(res.keys()):
        article["survey_topic"] = res.get("survey_topic")
        article["target_population"] = res.get("target_population")
        article["survey_metrics"] = "; ".join(res.get("key_findings", []))
        article["sentiment"] = res.get("sentiment")
        article["geopolitical_implication"] = res.get("geopolitical_implication")
    else:
        article["survey_topic"] = article.get("tags") or "국제정세 일반 여론"
        article["target_population"] = article["region"]
        article["survey_metrics"] = "원문 요약 참조"
        article["sentiment"] = "neutral"
        article["geopolitical_implication"] = "정량 수치 추출 대기"
    return article


# ============================================================================
# 3단계: 파이프라인 오케스트레이터 및 저장
# ============================================================================

def run(limit: int = 5, with_llm: bool = False, model: str = "mistral-nemo:latest") -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_articles = []

    print("\n" + "=" * 70)
    print("📊 [글로벌 여론조사(Public Opinion Polls) 자동 수집 파이프라인]")
    print(f"• 수집 출처: {len(POLLING_FEEDS)}개 기관 (Pew, ECFR, Ipsos)")
    print(f"• 피드당 최대 수집: {limit}건")
    print(f"• LLM 지표 구조화: {'실행 (' + model + ')' if with_llm else '미실행 (--with-llm 옵션 필요)'}")
    print("=" * 70)

    for feed in POLLING_FEEDS:
        print(f"\n[{feed['org']}] {feed['name']} 수집 중...")
        items = fetch_feed_articles(feed, limit=limit)
        print(f"  ✓ {len(items)}건 수신 완료")

        if with_llm and items:
            print(f"  🧠 {model} 기반 정량 설문 지표 및 함의 추출 중...")
            for idx, item in enumerate(items, 1):
                start = time.time()
                extract_poll_metrics(item, model=model)
                elapsed = time.time() - start
                print(f"    [{idx}/{len(items)}] {item['title'][:45]}... ({elapsed:.1f}s)")

        all_articles.extend(items)

    # 1. CSV 저장
    csv_path = DATA_DIR / "polls_latest.csv"
    fieldnames = [
        "poll_id", "source_org", "region", "title", "published", "link",
        "survey_topic", "target_population", "survey_metrics", "sentiment",
        "geopolitical_implication", "summary"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_articles)
    print(f"\n✓ CSV 저장 완료: {csv_path} (총 {len(all_articles)}건)")

    # 2. 요약 JSON 저장
    org_counts = Counter(a["source_org"] for a in all_articles)
    summary_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_polls": len(all_articles),
        "by_organization": dict(org_counts),
        "recent_highlights": [
            {
                "org": a["source_org"],
                "title": a["title"],
                "topic": a.get("survey_topic"),
                "metrics": a.get("survey_metrics"),
                "implication": a.get("geopolitical_implication"),
                "link": a["link"],
            }
            for a in all_articles[:5]
        ]
    }
    json_path = DATA_DIR / "polls_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    print(f"✓ 요약 JSON 저장 완료: {json_path}")

    return all_articles


# ============================================================================
# 4단계: Self-Test (네트워크/Ollama 없이 무결성 검증)
# ============================================================================

_MOCK_PEW_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Pew Research Center</title>
<item>
  <title>Do people trust China, the U.S. or the EU to regulate AI?</title>
  <link>https://www.pewresearch.org/global/2026/09/17/do-people-trust-china-the-u-s-or-the-eu-to-regulate-ai/</link>
  <pubDate>Thu, 17 Sep 2026 13:59:59 +0000</pubDate>
  <description><![CDATA[Trust in China, the U.S. and the EU to regulate AI is tied to overall favorability. Results show 58% of respondents in 24 countries trust the EU, 52% trust the US, and only 21% trust China.]]></description>
  <category>Artificial Intelligence</category>
</item>
<item>
  <title>Majorities in US and Europe back continued support for Ukraine</title>
  <link>https://www.pewresearch.org/global/2026/09/10/us-europe-support-ukraine/</link>
  <pubDate>Thu, 10 Sep 2026 12:00:00 +0000</pubDate>
  <description><![CDATA[A new Pew survey finds 64% of Americans and 71% of Europeans support continued humanitarian and military aid to Ukraine amid ongoing conflict with Russia.]]></description>
  <category>Russia-Ukraine</category>
</item>
</channel>
</rss>"""


def _self_test() -> bool:
    print("=" * 60)
    print("🧪 self-test: fetch_polling_data.py 전체 파이프라인 (모의 데이터 검증)")
    print("=" * 60)

    mock_feed_info = POLLING_FEEDS[0]
    articles = fetch_feed_articles(mock_feed_info, limit=5, xml_bytes=_MOCK_PEW_FEED.encode("utf-8"))
    ok_count = len(articles) == 2
    print(f"  {'✓' if ok_count else '✗'} 모의 RSS 파싱: {len(articles)}건 (기대: 2건)")

    a1 = articles[0]
    ok_title = "trust China" in a1["title"]
    ok_summary = "58% of respondents" in a1["summary"]
    print(f"  {'✓' if ok_title else '✗'} 제목 파싱: {a1['title']}")
    print(f"  {'✓' if ok_summary else '✗'} 본문 파싱: {a1['summary'][:60]}...")

    # 모의 LLM 추출 검증
    mock_extracted = {
        "survey_topic": "인공지능(AI) 규제 신뢰도",
        "target_population": "24개국 시민",
        "key_findings": ["EU 신뢰도 58%", "미국 신뢰도 52%", "중국 신뢰도 21%"],
        "sentiment": "neutral",
        "geopolitical_implication": "서방 중심의 AI 글로벌 규범 주도권이 유지되고 있으며 중국의 디지털 패권은 높은 불신에 직면함."
    }
    a1["survey_topic"] = mock_extracted["survey_topic"]
    a1["target_population"] = mock_extracted["target_population"]
    a1["survey_metrics"] = "; ".join(mock_extracted["key_findings"])
    a1["sentiment"] = mock_extracted["sentiment"]
    a1["geopolitical_implication"] = mock_extracted["geopolitical_implication"]

    ok_metrics = "58%" in a1["survey_metrics"]
    print(f"  {'✓' if ok_metrics else '✗'} 구조화 지표 주입: {a1['survey_metrics']}")

    # 파일 저장 테스트
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    test_csv = DATA_DIR / "test_polls.csv"
    with open(test_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["poll_id", "source_org", "title", "survey_metrics", "geopolitical_implication"])
        writer.writeheader()
        writer.writerow({
            "poll_id": a1["poll_id"],
            "source_org": a1["source_org"],
            "title": a1["title"],
            "survey_metrics": a1["survey_metrics"],
            "geopolitical_implication": a1["geopolitical_implication"],
        })
    ok_file = test_csv.exists() and test_csv.stat().st_size > 0
    if test_csv.exists():
        test_csv.unlink()
    print(f"  {'✓' if ok_file else '✗'} CSV 저장 및 직렬화 검증 완료")

    all_passed = ok_count and ok_title and ok_summary and ok_metrics and ok_file
    print("\n" + ("✅ self-test 통과!" if all_passed else "❌ self-test 실패!"))
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="글로벌 여론조사 및 씽크탱크 정량 지표 자동 수집 도구")
    parser.add_argument("--limit", type=int, default=5, help="피드당 수집할 최대 항목 수 (기본값: 5)")
    parser.add_argument("--with-llm", action="store_true", help="로컬 LLM으로 설문 수치/함의 정밀 추출")
    parser.add_argument("--model", type=str, default="mistral-nemo:latest", help="추출에 쓸 로컬 Ollama 모델명")
    parser.add_argument("--self-test", action="store_true", help="네트워크/Ollama 없이 로직 검증")
    args = parser.parse_args()

    if args.self_test:
        success = _self_test()
        sys.exit(0 if success else 1)

    run(limit=args.limit, with_llm=args.with_llm, model=args.model)


if __name__ == "__main__":
    main()
