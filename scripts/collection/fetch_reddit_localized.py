"""
fetch_reddit_localized.py — 국가별 현지어 서브레딧 조기경보 수집기
======================================================================

조기경보 관점:
  r/geopolitics, r/worldnews 같은 영어권 글로벌 커뮤니티는
  서방 시각에 치우쳐 있다. 현지어 서브레딧을 보면 그 국가 국민이
  실제로 무엇을 두려워하고 어떻게 반응하는지 알 수 있다.

  - r/China_irl: 중국인이 VPN으로 나와서 정부 정책·경제·생활을 솔직히 토론
  - r/Россия / r/russia: 러시아인들의 일상·정치 체감도
  - r/iran: 이란 디아스포라 + 국내 VPN 이용자 여론
  - r/taiwan: 양안 관계에 대한 대만 현지 민심
  - r/korea: 한국인들의 안보·경제 체감도 (대조군)

수집 방식:
  - Reddit 공개 RSS(.rss Atom 피드)를 사용한다. API 키 불필요.
  - 키워드 필터로 위험 신호와 무관한 일상 게시물을 사전 제거한다.
  - HTTP 429/403 시 해당 서브레딧만 중단하고 다음으로 넘어간다.
  - 요청 간 최소 6초 딜레이를 지킨다.

저장 위치:
  data/reddit_localized/reddit_localized_latest.csv
  data/reddit_localized/reddit_localized_summary.json
  data/reddit_localized/history/reddit_localized_{timestamp}.csv

사용법:
  python scripts/fetch_reddit_localized.py                   # 전체 서브레딧 수집
  python scripts/fetch_reddit_localized.py --sub China_irl   # 특정 서브레딧만
  python scripts/fetch_reddit_localized.py --limit 20        # 서브레딧당 최대 20건
  python scripts/fetch_reddit_localized.py --no-filter       # 키워드 필터 없이 전체 수집
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ----- 경로 설정 -----
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "reddit_localized"
HISTORY_DIR = DATA_DIR / "history"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

NS = {"atom": "http://www.w3.org/2005/Atom"}

# ======================================================================
# 서브레딧 프로필 정의
# ======================================================================
SUBREDDIT_PROFILES: dict[str, dict] = {
    "China_irl": {
        "country_code": "CN",
        "country_name": "중국",
        "lang": "zh/en",
        "description": "중국인 VPN 이용자·해외교포의 솔직한 여론. '润(Run·이민)'과 경제 불만이 핵심 신호.",
        "risk_keywords": [
            "失业", "润", "移民", "暴跌", "崩溃", "抗议", "封锁", "台湾",
            "emigrate", "collapse", "unemployment", "protest", "blockade",
            "economy", "sanctions", "tariff", "real estate", "youth",
        ],
        "risk_theme": "중국 내부 경제위기·이민 의향·대만 긴장",
        "supply_chain_relevance": "반도체·배터리·희토류 공급망",
    },
    "russia": {
        "country_code": "RU",
        "country_name": "러시아",
        "lang": "ru/en",
        "description": "러시아인들의 전쟁 체감도, 제재 영향, 반정부 감정 포착",
        "risk_keywords": [
            "мобилизация", "санкции", "инфляция", "эмиграция", "арест",
            "mobilization", "sanctions", "protest", "emigration", "war",
            "economy", "ruble", "collapse", "flee", "escape",
        ],
        "risk_theme": "러시아 병역·제재 반응·내부 불만",
        "supply_chain_relevance": "에너지·곡물 공급망",
    },
    "iranian": {
        "country_code": "IR",
        "country_name": "이란",
        "lang": "fa/en",
        "description": "이란 디아스포라 및 국내 VPN 이용자의 경제·정치 체감도",
        "risk_keywords": [
            "inflation", "sanctions", "rial", "protest", "regime",
            "تورم", "اعتراض", "تحریم", "اقتصاد", "دلار",
            "nuclear", "strait", "oil", "war", "revolution",
        ],
        "risk_theme": "이란 경제제재·내부 저항·핵협상",
        "supply_chain_relevance": "에너지·호르무즈 해협",
    },
    "taiwan": {
        "country_code": "TW",
        "country_name": "대만",
        "lang": "zh/en",
        "description": "대만인의 중국 위협 인식, 안보 체감도, 경제 민심",
        "risk_keywords": [
            "war", "invasion", "missile", "blockade", "China",
            "TSMC", "semiconductor", "defense", "military", "threat",
            "兩岸", "戰爭", "封鎖", "飛彈", "國防",
        ],
        "risk_theme": "양안 긴장·대만 안보 체감",
        "supply_chain_relevance": "TSMC·반도체 파운드리 공급망",
    },
    "korea": {
        "country_code": "KR",
        "country_name": "한국 (대조군)",
        "lang": "ko/en",
        "description": "한국인들의 경제·안보 체감도. 공급망 리스크를 한국 측 관점에서 확인.",
        "risk_keywords": [
            "수출", "반도체", "무역", "북한", "도발", "경기침체",
            "export", "semiconductor", "trade", "North Korea", "recession",
            "inflation", "unemployment", "supply chain",
        ],
        "risk_theme": "한국 공급망·안보 체감 (대조군)",
        "supply_chain_relevance": "직접적 한국 공급망 영향 측정",
    },
    "geopolitics": {
        "country_code": "GLOBAL",
        "country_name": "글로벌 (전문가·중립)",
        "lang": "en",
        "description": "지정학 전문가·정책 연구자들의 고품질 분석. 신호 맥락화에 활용.",
        "risk_keywords": [
            "war", "sanctions", "supply chain", "escalation", "conflict",
            "missile", "invasion", "economic", "energy", "trade war",
            "Taiwan", "Ukraine", "Middle East", "OPEC", "semiconductor",
        ],
        "risk_theme": "글로벌 지정학 전문가 담론",
        "supply_chain_relevance": "포괄적 공급망 위험 맥락",
    },
    "worldnews": {
        "country_code": "GLOBAL",
        "country_name": "글로벌 (일반 여론)",
        "lang": "en",
        "description": "글로벌 일반 여론. 이슈 확산성 및 대중 관심도 측정.",
        "risk_keywords": [
            "war", "attack", "oil", "food", "energy crisis",
            "blockade", "sanctions", "military", "nuclear", "inflation",
        ],
        "risk_theme": "글로벌 대중 관심 이슈",
        "supply_chain_relevance": "이슈 대중 확산도 측정",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_subreddit_rss(subreddit: str, limit: int = 15, delay: float = 6.0) -> list[dict]:
    """서브레딧 RSS를 가져와 파싱한다."""
    url = f"https://www.reddit.com/r/{subreddit}/.rss?limit={limit}&sort=hot"
    print(f"  → 접근 중: {url}")

    # 요청 전 짧은 랜덤 대기 (봇 탐지 회피)
    pre_wait = random.uniform(2.0, 5.0)
    time.sleep(pre_wait)

    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=20) as resp:
            xml_bytes = resp.read()
        # 요청 후 딜레이
        post_wait = delay + random.uniform(0.5, 3.0)
        time.sleep(post_wait)
    except HTTPError as e:
        if e.code == 429:
            print(f"  🔴 HTTP 429 Too Many Requests — 이 서브레딧 건너뜀 (다음 서브레딧 전 {delay*3:.0f}초 대기)")
            time.sleep(delay * 3)
        elif e.code == 403:
            print(f"  🔴 HTTP 403 Forbidden — 이 서브레딧 건너뜀")
            time.sleep(delay)
        else:
            print(f"  ⚠️  HTTP {e.code} — 건너뜀")
            time.sleep(delay)
        return []
    except URLError as e:
        print(f"  ⚠️  네트워크 오류: {e.reason} — 건너뜀")
        time.sleep(delay)
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"  ⚠️  XML 파싱 오류: {e}")
        return []

    entries = root.findall("atom:entry", NS)
    posts = []
    for entry in entries:
        title_el = entry.find("atom:title", NS)
        link_el = entry.find("atom:link", NS)
        content_el = entry.find("atom:content", NS)
        updated_el = entry.find("atom:updated", NS)
        author_el = entry.find("atom:author/atom:name", NS)

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        url_val = link_el.get("href", "") if link_el is not None else ""
        content = content_el.text or "" if content_el is not None else ""
        updated = updated_el.text or "" if updated_el is not None else ""
        author = author_el.text or "" if author_el is not None else ""

        # HTML 태그 제거
        import re
        content_clean = re.sub(r"<[^>]+>", " ", content)[:500].strip()

        posts.append({
            "subreddit": subreddit,
            "title": title,
            "url": url_val,
            "author": author,
            "updated": updated,
            "content_preview": content_clean,
        })

    return posts


def filter_by_keywords(posts: list[dict], keywords: list[str]) -> list[dict]:
    """위험 키워드가 포함된 게시물만 필터링한다."""
    if not keywords:
        return posts

    filtered = []
    for post in posts:
        text = (post["title"] + " " + post["content_preview"]).lower()
        for kw in keywords:
            if kw.lower() in text:
                post["matched_keyword"] = kw
                filtered.append(post)
                break

    return filtered


def score_post(post: dict, profile: dict) -> str:
    """게시물의 위험 신호 관련성 점수를 간단히 산출한다."""
    text = (post["title"] + " " + post["content_preview"]).lower()
    high_risk_patterns = [
        "war", "attack", "invasion", "collapse", "protest", "military",
        "missile", "blockade", "embargo", "sanctions", "crisis",
        "전쟁", "도발", "붕괴", "시위", "봉쇄",
        "войн", "протест", "санкц", "мобилизац",
        "战争", "崩溃", "封锁", "抗议",
        "حمله", "جنگ", "اعتراض",
    ]
    matches = sum(1 for p in high_risk_patterns if p in text)
    if matches >= 3:
        return "HIGH"
    elif matches >= 1:
        return "MEDIUM"
    else:
        return "LOW"


def save_results(all_rows: list[dict]) -> None:
    """수집 결과를 CSV + JSON으로 저장한다."""
    if not all_rows:
        print("\n⚠️  저장할 데이터가 없습니다.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fieldnames = [
        "country_code", "country_name", "subreddit", "risk_theme",
        "supply_chain_relevance", "risk_signal_level",
        "title", "matched_keyword", "author", "updated",
        "url", "content_preview", "fetched_at",
    ]

    # 최신본
    latest_csv = DATA_DIR / "reddit_localized_latest.csv"
    with open(latest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n✅ CSV 저장: {latest_csv} ({len(all_rows)}건)")

    # 이력 보관
    history_csv = HISTORY_DIR / f"reddit_localized_{timestamp}.csv"
    with open(history_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    # 요약 JSON
    high_risk_posts = [r for r in all_rows if r.get("risk_signal_level") == "HIGH"]
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_posts": len(all_rows),
        "high_risk_count": len(high_risk_posts),
        "high_risk_posts": high_risk_posts[:10],  # 상위 10건만 저장
        "by_country": {},
    }
    for r in all_rows:
        cc = r["country_code"]
        if cc not in summary["by_country"]:
            summary["by_country"][cc] = {
                "country_name": r["country_name"],
                "total": 0,
                "high_risk": 0,
                "top_titles": [],
            }
        summary["by_country"][cc]["total"] += 1
        if r.get("risk_signal_level") == "HIGH":
            summary["by_country"][cc]["high_risk"] += 1
            summary["by_country"][cc]["top_titles"].append(r["title"][:80])

    summary_json = DATA_DIR / "reddit_localized_summary.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✅ 요약 JSON 저장: {summary_json}")

    # 국가별 결과 출력
    print("\n" + "=" * 60)
    print("📊 국가별 현지어 서브레딧 위험 신호 현황")
    print("=" * 60)
    for cc, info in summary["by_country"].items():
        high = info["high_risk"]
        total = info["total"]
        bar = "🔴" if high >= 3 else ("🟠" if high >= 1 else "🟢")
        print(f"  {bar} [{cc}] {info['country_name']:12s} — HIGH 위험 {high}/{total}건")
        for title in info["top_titles"][:2]:
            print(f"       📌 {title}")


def main() -> None:
    parser = argparse.ArgumentParser(description="국가별 현지어 서브레딧 조기경보 수집기")
    parser.add_argument(
        "--sub", nargs="+",
        default=list(SUBREDDIT_PROFILES.keys()),
        help=f"수집할 서브레딧 (기본: 전체). 선택: {list(SUBREDDIT_PROFILES.keys())}",
    )
    parser.add_argument("--limit", type=int, default=15,
                        help="서브레딧당 최대 수집 게시물 수 (기본: 15)")
    parser.add_argument("--delay", type=float, default=15.0,
                        help="요청 간 딜레이(초). 15초 이상 권장 — Reddit Rate Limit 회피 (기본: 15)")
    parser.add_argument("--no-filter", action="store_true",
                        help="키워드 필터 없이 전체 게시물 수집")
    args = parser.parse_args()

    print("=" * 60)
    print("🗣️  현지어 서브레딧 조기경보 수집 시작")
    print(f"   대상 서브레딧: {args.sub}")
    print(f"   서브레딧당 최대: {args.limit}건 / 딜레이: {args.delay}초")
    print(f"   키워드 필터: {'OFF' if args.no_filter else 'ON'}")
    print("=" * 60)

    all_rows: list[dict] = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for sub_name in args.sub:
        if sub_name not in SUBREDDIT_PROFILES:
            print(f"\n⚠️  알 수 없는 서브레딧: {sub_name}")
            continue

        profile = SUBREDDIT_PROFILES[sub_name]
        print(f"\n[r/{sub_name}] {profile['country_name']} — {profile['description'][:60]}...")

        posts = fetch_subreddit_rss(sub_name, limit=args.limit, delay=args.delay)
        if not posts:
            print(f"  ⚠️  게시물 없음")
            continue

        if not args.no_filter:
            posts = filter_by_keywords(posts, profile["risk_keywords"])
            print(f"  ✓ {len(posts)}건 (키워드 필터 후)")
        else:
            for p in posts:
                p["matched_keyword"] = ""
            print(f"  ✓ {len(posts)}건 (필터 없이 전체)")

        for post in posts:
            post["country_code"] = profile["country_code"]
            post["country_name"] = profile["country_name"]
            post["risk_theme"] = profile["risk_theme"]
            post["supply_chain_relevance"] = profile["supply_chain_relevance"]
            post["risk_signal_level"] = score_post(post, profile)
            post["fetched_at"] = now_str

        all_rows.extend(posts)

        # 샘플 출력 (상위 3건)
        for post in posts[:3]:
            signal = post.get("risk_signal_level", "?")
            icon = "🔴" if signal == "HIGH" else ("🟠" if signal == "MEDIUM" else "⚪")
            kw = post.get("matched_keyword", "")
            print(f"    {icon} [{signal}] {post['title'][:60]}{'...' if len(post['title']) > 60 else ''}")
            if kw:
                print(f"         키워드: '{kw}'")

    save_results(all_rows)


if __name__ == "__main__":
    main()

