"""
fetch_bluesky_public.py — 블루스카이(Bluesky AT Protocol) 공개 지정학·공급망 신호 수집기
======================================================================================

설계 원칙 (Data Contract):
1. 조기경보 목적:
   - 유료화된 X(트위터)의 핵심 대안이자 외교·안보 연구자/기자들이 밀집한 Bluesky(AT Protocol)의
     완전 무료 공개 검색 API(https://api.bsky.app/xrpc/app.bsky.feed.searchPosts)를 통해
     5대 해협, 6대 핵심 공급망 품목, 수출통제·제재·분쟁 관련 실시간 온라인 신호를 수집한다.
2. 정보환경 신호 한계 규정 (DATA_COLLECTION_GUIDE.md §3.2):
   - 소셜 미디어 포스트는 절대 '국민 전체 여론'이나 '객관적 사실(Ground Truth)'로 단정하지 않는다.
   - 반드시 `signal_class: online_information_environment_signal` 및 `verification_state: UNVERIFIED`로 기록하며,
     단독으로 Alert Level을 격상하지 않는다.
3. 안전성 & 경량성:
   - API 키·로그인 불필요 (100% 공개 XRPC 엔드포인트).
   - 비공개 계정 접근이나 우회 스크래핑 없음.
   - 무거운 C 컴파일 라이브러리(pandas/lxml/selenium) 없이 순수 requests + csv 표준 모듈로 구현하여
     메인 PC(Airflow) 및 갤럭시 S20 울트라(Termux 엣지 노드) 양쪽에서 100% 호환 동작한다.
4. 산출물:
   - data/bluesky_public/bluesky_latest.json
   - data/bluesky_public/bluesky_latest.csv
   - data/bluesky_public/receipt_latest.json (수집 영수증)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

# 콘솔 인코딩 안전화
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "bluesky_public"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_ID = "bluesky_public_search"
API_ENDPOINT = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"
LICENSE_NOTE = (
    "Public Bluesky AT Protocol searchPosts API (no auth required). "
    "Online information-environment signal only, never national opinion or ground truth."
)

# 8대 전략 감시 쿼리 (5대 해협 + 6대 공급망 품목 + 미국 통상/제재 + 주요 분쟁)
WATCH_QUERIES = [
    {
        "query": "Strait of Hormuz oil tanker",
        "issue_tags": ["Middle_East_Energy", "Iran_Nuclear"],
        "chokepoint": "HORMUZ",
        "commodity": "Crude_Oil_LNG",
    },
    {
        "query": "Red Sea Houthi shipping",
        "issue_tags": ["Middle_East_Energy", "Red_Sea_Disruption"],
        "chokepoint": "BAB_EL_MANDEB",
        "commodity": "Container_Shipping",
    },
    {
        "query": "Taiwan Strait semiconductor TSMC",
        "issue_tags": ["Taiwan_Strait", "US_Industrial_Policy_CHIPS"],
        "chokepoint": "TAIWAN_STRAIT",
        "commodity": "Semiconductor",
    },
    {
        "query": "Panama Canal shipping drought",
        "issue_tags": ["Panama_Canal_Bottleneck", "Global_Grain_Trade"],
        "chokepoint": "PANAMA_CANAL",
        "commodity": "LNG_Grain",
    },
    {
        "query": "Malacca Strait shipping tanker",
        "issue_tags": ["South_China_Sea", "Maritime_Security"],
        "chokepoint": "MALACCA",
        "commodity": "Crude_Oil_Container",
    },
    {
        "query": "US export control tariff China semiconductor",
        "issue_tags": ["US_Export_Control", "US_Trade_Tariff", "US_Industrial_Policy_CHIPS"],
        "chokepoint": "NONE",
        "commodity": "Semiconductor",
    },
    {
        "query": "OFAC sanctions Russia Iran oil",
        "issue_tags": ["US_Sanctions_OFAC", "EU_Russia", "Middle_East_Energy"],
        "chokepoint": "NONE",
        "commodity": "Crude_Oil_LNG",
    },
    {
        "query": "rare earths critical minerals supply chain",
        "issue_tags": ["US_Export_Control", "Critical_Minerals_Supply"],
        "chokepoint": "NONE",
        "commodity": "Rare_Earths_Battery",
    },
]


def fetch_bluesky_posts(limit_per_query: int = 8) -> tuple[list[dict], list[dict]]:
    """Bluesky 공개 XRPC API를 통해 전략 쿼리별 최신 포스트를 수집하고 중복을 제거한다."""
    observed_at = datetime.now(timezone.utc).isoformat()
    headers = {
        "User-Agent": "InternationalAnalysisOSINT/1.0 (Academic/SupplyChain EarlyWarning)",
        "Accept": "application/json",
    }

    deduped_posts: dict[str, dict] = {}
    query_receipts: list[dict] = []

    print(f"[{SOURCE_ID}] Bluesky AT Protocol 공개 API 수집 시작 ({len(WATCH_QUERIES)}개 감시 쿼리)...")

    for q_meta in WATCH_QUERIES:
        q_str = q_meta["query"]
        params = {
            "q": q_str,
            "limit": min(max(1, limit_per_query), 25),
            "sort": "latest",
        }

        try:
            resp = requests.get(API_ENDPOINT, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"  ⚠️ 쿼리 실패 ('{q_str}'): HTTP {resp.status_code}")
                query_receipts.append({
                    "query": q_str,
                    "http_status": resp.status_code,
                    "parse_status": "HTTP_ERROR",
                    "items_fetched": 0,
                })
                continue

            payload = resp.json()
            posts = payload.get("posts", [])

            for post in posts:
                uri = post.get("uri", "")
                if not uri:
                    continue

                author = post.get("author", {}) or {}
                handle = author.get("handle", "unknown")
                display_name = (author.get("displayName") or handle).strip()
                did = author.get("did", "")

                record = post.get("record", {}) or {}
                text = (record.get("text") or "").replace("\r", " ").replace("\n", " ").strip()
                if not text:
                    continue

                created_at = record.get("createdAt", observed_at)
                langs = record.get("langs") or []
                lang_str = langs[0] if isinstance(langs, list) and langs else "unknown"

                # 외부 뉴스 링크(embed.external) 추출
                embed = record.get("embed", {}) or {}
                ext = embed.get("external", {}) if isinstance(embed, dict) else {}
                external_uri = ext.get("uri", "") if isinstance(ext, dict) else ""
                external_title = (ext.get("title") or "").strip() if isinstance(ext, dict) else ""

                rkey = uri.split("/")[-1] if "/" in uri else ""
                post_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else "https://bsky.app"

                content_hash = hashlib.sha256(
                    f"{uri}|{created_at}|{text[:120]}".encode("utf-8", errors="ignore")
                ).hexdigest()[:16]

                if uri not in deduped_posts:
                    deduped_posts[uri] = {
                        "source_id": SOURCE_ID,
                        "source_type": "online_expression",
                        "signal_class": "online_information_environment_signal",
                        "verification_state": "UNVERIFIED",
                        "query_matched": q_str,
                        "issue_tags": ";".join(q_meta["issue_tags"]),
                        "chokepoint_tag": q_meta["chokepoint"],
                        "commodity_tag": q_meta["commodity"],
                        "post_uri": uri,
                        "post_url": post_url,
                        "author_did": did,
                        "author_handle": f"@{handle}",
                        "author_display_name": display_name,
                        "language": lang_str,
                        "text": text[:500],
                        "external_link": external_uri,
                        "external_title": external_title[:200],
                        "like_count": int(post.get("likeCount") or 0),
                        "repost_count": int(post.get("repostCount") or 0),
                        "reply_count": int(post.get("replyCount") or 0),
                        "published_at": created_at,
                        "observed_at": observed_at,
                        "content_hash": content_hash,
                        "license_access_note": LICENSE_NOTE,
                    }

            query_receipts.append({
                "query": q_str,
                "http_status": 200,
                "parse_status": "SUCCESS",
                "items_fetched": len(posts),
            })
            print(f"  ✓ '{q_str}': {len(posts)}건 수신")

        except Exception as e:
            print(f"  ❌ 쿼리 예외 ('{q_str}'): {e}")
            query_receipts.append({
                "query": q_str,
                "http_status": None,
                "parse_status": "ERROR",
                "items_fetched": 0,
                "error": str(e)[:160],
            })

        time.sleep(0.5)

    return list(deduped_posts.values()), query_receipts


def save_outputs(posts: list[dict], query_receipts: list[dict]) -> None:
    """수집된 블루스카이 포스트와 수집 영수증을 저장한다."""
    observed_at = datetime.now(timezone.utc).isoformat()
    json_path = DATA_DIR / "bluesky_latest.json"
    csv_path = DATA_DIR / "bluesky_latest.csv"
    receipt_path = DATA_DIR / "receipt_latest.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    if posts:
        fieldnames = list(posts[0].keys())
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(posts)

    receipt = {
        "collector": "scripts/collection/fetch_bluesky_public.py",
        "source_id": SOURCE_ID,
        "signal_class": "online_information_environment_signal",
        "observed_at": observed_at,
        "total_unique_posts": len(posts),
        "queries_executed": len(query_receipts),
        "alert_level_set": False,
        "verification_state_set": False,
        "query_receipts": query_receipts,
        "license_access_note": LICENSE_NOTE,
    }
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Bluesky 수집 완료: 고유 포스트 {len(posts)}건")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV:  {csv_path}")
    print(f"  - 영수증: {receipt_path}")


def main():
    parser = argparse.ArgumentParser(description="Bluesky Public AT Protocol Collector")
    parser.add_argument("--limit-per-query", type=int, default=8, help="쿼리당 최대 수집 건수 (기본: 8)")
    args = parser.parse_args()

    posts, receipts = fetch_bluesky_posts(limit_per_query=args.limit_per_query)
    save_outputs(posts, receipts)


if __name__ == "__main__":
    main()
