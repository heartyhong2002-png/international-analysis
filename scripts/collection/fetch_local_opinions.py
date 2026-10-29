"""
fetch_local_opinions.py — 레딧 대체 5대 로컬 여론·위험 센서 통합 수집기
======================================================================

조기경보 관점:
  서구 편향 및 잦은 HTTP 429 차단이 발생하는 레딧을 대체하여,
  차단이 없고 검열을 우회할 수 있는 5개 실질 로컬 채널에서
  각국 민심과 공급망 리스크 신호를 실시간 수집·통합한다.

5대 수집 채널:
  1. 대만 PTT (대만판 레딧/디시): 양안 긴장, 대만 내 안보 체감, TSMC 파운드리 민심
  2. 중국 핀충 (品葱, Pincong): 검열 없는 중국 내부 경제 불만, 청년 실업, 이민(润) 의향
  3. 블루스카이 (Bluesky Public API): 차단 없는 차세대 분산형 SNS 지정학 포스트
  4. 구글 뉴스 로컬 RSS: 대만·러시아·중동 현지 독립·전문지 심층 보도
  5. 텔레그램 OSINT: 후티 반군, 이란 혁명수비대, 러시아 전선 밀블로거 군사 속보

저장 위치:
  data/local_opinions/local_opinions_latest.csv
  data/local_opinions/local_opinions_summary.json
  data/local_opinions/history/local_opinions_{timestamp}.csv

사용법:
  python scripts/fetch_local_opinions.py
  python scripts/fetch_local_opinions.py --sources ptt pincong bsky
  python scripts/fetch_local_opinions.py --limit 10
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# ----- 경로 설정 -----
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "local_opinions"
HISTORY_DIR = DATA_DIR / "history"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
}


# ======================================================================
# 1. 대만 PTT 수집 (Military & Gossiping)
# ======================================================================
def fetch_ptt(boards: list[str] = ["Military", "Gossiping"], limit: int = 10) -> list[dict]:
    items = []
    print("  [PTT] 대만 로컬 BBS 수집 중...")
    for board in boards:
        url = f"https://www.ptt.cc/bbs/{board}/index.html"
        try:
            req = urllib.request.Request(
                url,
                headers={**COMMON_HEADERS, "Cookie": "over18=1"}
            )
            with urllib.request.urlopen(req, timeout=12) as r:
                html = r.read().decode("utf-8", errors="ignore")
                matches = re.findall(r'<div class="title">\s*<a href="([^"]+)">([^<]+)</a>', html)
                count = 0
                for link, title in matches:
                    clean_title = title.strip()
                    if "[公告]" in clean_title:
                        continue
                    items.append({
                        "source_platform": f"PTT_{board}",
                        "country_or_region": "TW",
                        "title_or_text": clean_title,
                        "url": f"https://www.ptt.cc{link}",
                        "author": "PTT_User",
                        "published_at": datetime.now().strftime("%Y-%m-%d"),
                        "risk_theme": "양안 긴장·대만 방위·반도체 민심",
                        "supply_chain_impact": "대만 해협 봉쇄 리스크 및 TSMC 파운드리 영향 체감",
                    })
                    count += 1
                    if count >= limit:
                        break
                print(f"    ✓ PTT {board}: {count}건 수집 완료")
        except Exception as e:
            print(f"    ✗ PTT {board} 오류: {e}")
        time.sleep(1.0)
    return items


# ======================================================================
# 2. 중국 핀충 (品葱, Pincong) 수집
# ======================================================================
def fetch_pincong(limit: int = 15) -> list[dict]:
    items = []
    print("  [Pincong] 중국 검열 우회 비판 포럼(品葱) 수집 중...")
    url = "https://pincong.rocks/"
    try:
        req = urllib.request.Request(
            url,
            headers={**COMMON_HEADERS, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            html = r.read().decode("utf-8", errors="ignore")
            matches = re.findall(r'<a[^>]+href="(/question/\d+)"[^>]*>([^<]+)</a>', html)
            seen = set()
            for link, title in matches:
                clean_title = title.strip()
                if clean_title in seen or len(clean_title) < 4:
                    continue
                seen.add(clean_title)
                items.append({
                    "source_platform": "Pincong_Forum",
                    "country_or_region": "CN",
                    "title_or_text": clean_title,
                    "url": f"https://pincong.rocks{link}",
                    "author": "Pincong_User",
                    "published_at": datetime.now().strftime("%Y-%m-%d"),
                    "risk_theme": "중국 내부 경제 위기·청년 실업·이민(润)·체제 불만",
                    "supply_chain_impact": "중국 내수 경기 침체 및 제조업·부동산 리스크 조기 감지",
                })
                if len(items) >= limit:
                    break
            print(f"    ✓ 핀충: {len(items)}건 수집 완료")
    except Exception as e:
        print(f"    ✗ 핀충 오류: {e}")
    return items


# ======================================================================
# 3. 블루스카이 (Bluesky Public Search API)
# ======================================================================
def fetch_bluesky(queries: list[str] = ["Taiwan semiconductor", "Houthi Red Sea", "China economy"], limit_per_query: int = 5) -> list[dict]:
    items = []
    print("  [Bluesky] AT Protocol 공개 검색 API 수집 중...")
    for q in queries:
        encoded_q = urllib.parse.quote(q)
        url = f"https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={encoded_q}&limit={limit_per_query}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                posts = data.get("posts", [])
                for p in posts:
                    handle = p.get("author", {}).get("handle", "unknown")
                    record = p.get("record", {})
                    text = record.get("text", "").replace("\n", " ").strip()
                    created_at = record.get("createdAt", "")[:10]
                    uri = p.get("uri", "")
                    rkey = uri.split("/")[-1] if "/" in uri else ""
                    post_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else ""

                    if not text:
                        continue

                    items.append({
                        "source_platform": "Bluesky_Social",
                        "country_or_region": "GLOBAL",
                        "title_or_text": text[:200],
                        "url": post_url,
                        "author": f"@{handle}",
                        "published_at": created_at or datetime.now().strftime("%Y-%m-%d"),
                        "risk_theme": f"글로벌 지정학 소셜 담론 ({q})",
                        "supply_chain_impact": "반도체, 해상 물류, 글로벌 무역 제재 소셜 확산 모니터링",
                    })
                print(f"    ✓ Bluesky ('{q}'): {len(posts)}건 수집")
        except Exception as e:
            print(f"    ✗ Bluesky ('{q}') 오류: {e}")
        time.sleep(1.0)
    return items


# ======================================================================
# 4. 구글 뉴스 로컬 타겟팅 RSS
# ======================================================================
def fetch_google_news_local(limit_per_feed: int = 8) -> list[dict]:
    items = []
    print("  [Google News Local] 대만·러시아·브라질 로컬 언론 RSS 수집 중...")
    feeds = [
        {
            "name": "Taiwan_CrossStrait",
            "country": "TW",
            "theme": "양안 위기·TSMC 방위",
            "impact": "대만 반도체 생산기지 및 해상 운송로 안보",
            "url": "https://news.google.com/rss/search?q=%E5%8F%B0%E6%B5%B7+%E5%8D%B1%E6%A9%9F+TSMC&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        },
        {
            "name": "Russia_Sanctions_Deficit",
            "country": "RU",
            "theme": "러시아 물가·제재·공급난",
            "impact": "에너지·곡물·희유금속 공급망 교란",
            "url": "https://news.google.com/rss/search?q=%D0%B4%D0%B5%D1%84%D0%B8%D1%86%D0%B8%D1%82+%D1%86%D0%B5%D0%BD%D1%8B+%D1%81%D0%B0%D0%BD%D0%BA%D1%86%D0%B8%D0%B8&hl=ru&gl=RU&ceid=RU:ru"
        },
        {
            "name": "Brazil_Lula_Petrobras",
            "country": "BR",
            "theme": "브라질 대선·룰라 정부·페트로브라스 공급망",
            "impact": "중남미 원유·원자재·곡물(대두/옥수수) 수출선 및 무역 정책",
            "url": "https://news.google.com/rss/search?q=Lula+Petrobras+greve+elei%C3%A7%C3%A3o&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        }
    ]

    for f in feeds:
        try:
            req = urllib.request.Request(f["url"], headers=COMMON_HEADERS)
            with urllib.request.urlopen(req, timeout=12) as r:
                root = ET.fromstring(r.read())
                entries = root.findall(".//item")
                count = 0
                for e in entries:
                    title = e.find("title").text if e.find("title") is not None else ""
                    link = e.find("link").text if e.find("link") is not None else ""
                    pub = e.find("pubDate").text if e.find("pubDate") is not None else ""
                    source = e.find("source").text if e.find("source") is not None else f["name"]

                    items.append({
                        "source_platform": f"GoogleNews_{f['country']}",
                        "country_or_region": f["country"],
                        "title_or_text": title,
                        "url": link,
                        "author": source,
                        "published_at": pub[:16] if pub else datetime.now().strftime("%Y-%m-%d"),
                        "risk_theme": f["theme"],
                        "supply_chain_impact": f["impact"],
                    })
                    count += 1
                    if count >= limit_per_feed:
                        break
                print(f"    ✓ Google News {f['name']}: {count}건 수집")
        except Exception as e:
            print(f"    ✗ Google News {f['name']} 오류: {e}")
        time.sleep(1.0)
    return items


# ======================================================================
# 5. 텔레그램 OSINT 공개 웹뷰 수집
# ======================================================================
def fetch_telegram_osint(channels: list[dict] = None, limit: int = 5) -> list[dict]:
    items = []
    print("  [Telegram OSINT] 후티·러시아 전선 속보 채널 수집 중...")
    if channels is None:
        channels = [
            {"id": "army21ye", "region": "ME", "name": "예멘 후티 반군 공식 성명", "theme": "홍해 해상 물류 피격·사우디 아람코 타격"},
            {"id": "rybar", "region": "RU", "name": "러시아 군사 밀블로거(Rybar)", "theme": "동유럽 전선 동향 및 서방 무기 타격 속보"},
        ]

    for ch in channels:
        url = f"https://t.me/s/{ch['id']}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                html = r.read().decode("utf-8", errors="ignore")
                msgs = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
                count = 0
                for m in reversed(msgs):
                    clean_text = re.sub(r'<[^>]+>', ' ', m).strip().replace('\n', ' ')
                    clean_text = re.sub(r'\s+', ' ', clean_text)
                    if len(clean_text) < 15:
                        continue
                    items.append({
                        "source_platform": f"Telegram_@{ch['id']}",
                        "country_or_region": ch["region"],
                        "title_or_text": clean_text[:250],
                        "url": f"https://t.me/{ch['id']}",
                        "author": ch["name"],
                        "published_at": datetime.now().strftime("%Y-%m-%d"),
                        "risk_theme": ch["theme"],
                        "supply_chain_impact": "홍해 항로 봉쇄, 원유 수송선 및 지정학 인프라 직접 충격",
                    })
                    count += 1
                    if count >= limit:
                        break
                print(f"    ✓ 텔레그램 @{ch['id']}: {count}건 수집")
        except Exception as e:
            print(f"    ✗ 텔레그램 @{ch['id']} 오류: {e}")
        time.sleep(1.0)
    return items


# ======================================================================
# 저장 및 요약
# ======================================================================
def save_local_opinions(all_items: list[dict]) -> None:
    if not all_items:
        print("\n⚠️  저장할 데이터가 없습니다.")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for item in all_items:
        item["collected_at"] = now_str

    fieldnames = [
        "source_platform", "country_or_region", "title_or_text",
        "url", "author", "published_at", "risk_theme",
        "supply_chain_impact", "collected_at"
    ]

    latest_csv = DATA_DIR / "local_opinions_latest.csv"
    with open(latest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_items)
    print(f"\n✅ 최신 CSV 저장: {latest_csv} (총 {len(all_items)}건)")

    history_csv = HISTORY_DIR / f"local_opinions_{timestamp}.csv"
    with open(history_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_items)

    # 요약 JSON
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_count": len(all_items),
        "by_platform": {},
        "by_region": {},
        "featured_signals": all_items[:12],
    }

    for item in all_items:
        plat = item["source_platform"]
        reg = item["country_or_region"]
        summary["by_platform"][plat] = summary["by_platform"].get(plat, 0) + 1
        summary["by_region"][reg] = summary["by_region"].get(reg, 0) + 1

    summary_json = DATA_DIR / "local_opinions_summary.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✅ 요약 JSON 저장: {summary_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="대안 로컬 여론 5대 센서 통합 수집기")
    parser.add_argument(
        "--sources", nargs="+",
        default=["ptt", "pincong", "bsky", "gnews", "telegram"],
        help="수집할 소스 (기본: ptt pincong bsky gnews telegram)"
    )
    parser.add_argument("--limit", type=int, default=10, help="소스별 기본 수집 상한")
    args = parser.parse_args()

    print("=" * 65)
    print("🌐 레딧 대체 5대 로컬 여론·위험 센서 통합 수집 파이프라인 가동")
    print(f"   선택된 소스: {args.sources} (소스별 상한: {args.limit}건)")
    print("=" * 65)

    all_records: list[dict] = []

    if "ptt" in args.sources:
        all_records.extend(fetch_ptt(limit=args.limit))
    if "pincong" in args.sources:
        all_records.extend(fetch_pincong(limit=args.limit))
    if "bsky" in args.sources:
        all_records.extend(fetch_bluesky(limit_per_query=max(3, args.limit // 2)))
    if "gnews" in args.sources:
        all_records.extend(fetch_google_news_local(limit_per_feed=args.limit))
    if "telegram" in args.sources:
        all_records.extend(fetch_telegram_osint(limit=args.limit))

    save_local_opinions(all_records)
    print("\n🎉 모든 로컬 여론 센서 수집 완료!")


if __name__ == "__main__":
    main()

