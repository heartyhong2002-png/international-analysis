"""
fetch_bluesky_public.py — 블루스카이(Bluesky AT Protocol) 공개 지정학·공급망 신호 수집기 (0-Byte 멀티모달 확장)
=============================================================================================================

설계 원칙 (Data Contract):
1. 조기경보 목적:
   - 유료화된 X(트위터)의 핵심 대안이자 외교·안보 연구자/기자들이 밀집한 Bluesky(AT Protocol)의
     완전 무료 공개 검색 API(https://api.bsky.app/xrpc/app.bsky.feed.searchPosts)를 통해
     5대 해협, 6대 핵심 공급망 품목, 수출통제·제재·분쟁 관련 실시간 온라인 신호를 수집한다.
2. 0-Byte 무다운로드 멀티모달 메타데이터 수집:
   - 원본 이미지/영상 바이너리를 다운로드하지 않고, post.embed 및 record.embed 내부의
     `media_urls` (embed.images[].thumb / fullsize / video playlist),
     `alt_texts` (embed.images[].alt 대체 텍스트 설명),
     `has_video` (app.bsky.embed.video 포함 여부),
     `external_link` / `external_title` 만 추출한다.
   - 전처리기는 `alt_texts`에서 5대 해협 및 6대 공급망 엔티티를 복원한다.
3. 정보환경 신호 한계 규정 (DATA_COLLECTION_GUIDE.md §3.2):
   - 소셜 미디어 포스트는 절대 '국민 전체 여론'이나 '객관적 사실(Ground Truth)'로 단정하지 않는다.
   - 반드시 `signal_class: online_information_environment_signal` 및 `verification_state: UNVERIFIED`로 기록하며,
     단독으로 Alert Level을 격상하지 않는다.
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
    "0-byte multimodal metadata only. Online information-environment signal only, never ground truth."
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


def _unwrap_embed_layer(embed_obj: dict) -> dict:
    """recordWithMedia 래퍼일 경우 내부 media 객체를 반환한다."""
    if not isinstance(embed_obj, dict):
        return {}
    etype = str(embed_obj.get("$type") or "")
    if "recordWithMedia" in etype and isinstance(embed_obj.get("media"), dict):
        return embed_obj["media"]
    return embed_obj


def _extract_bsky_multimodal(post: dict, record: dict, author_did: str) -> dict:
    """
    post.embed (Hydrated View) 및 record.embed (Raw Record) 양쪽에서
    외부 링크 카드, 이미지 thumb/fullsize URL, alt_texts, 비디오 포함 여부를 추출한다.
    """
    view_embed = _unwrap_embed_layer(post.get("embed") or {})
    rec_embed = _unwrap_embed_layer(record.get("embed") or {})

    view_type = str(view_embed.get("$type") or "")
    rec_type = str(rec_embed.get("$type") or "")

    # 1. 외부 링크 카드 (app.bsky.embed.external)
    ext_view = view_embed.get("external") if isinstance(view_embed.get("external"), dict) else {}
    ext_rec = rec_embed.get("external") if isinstance(rec_embed.get("external"), dict) else {}
    external_uri = str(ext_view.get("uri") or ext_rec.get("uri") or "").strip()
    external_title = str(ext_view.get("title") or ext_rec.get("title") or "").replace("\r", " ").replace("\n", " ").strip()
    external_desc = str(ext_view.get("description") or ext_rec.get("description") or "").replace("\r", " ").replace("\n", " ").strip()

    media_urls: list[str] = []
    alt_texts: list[str] = []

    # 2. 이미지 리스트 (app.bsky.embed.images)
    view_images = view_embed.get("images") if isinstance(view_embed.get("images"), list) else []
    rec_images = rec_embed.get("images") if isinstance(rec_embed.get("images"), list) else []

    for idx, img_item in enumerate(view_images):
        if not isinstance(img_item, dict):
            continue
        img_url = str(img_item.get("thumb") or img_item.get("fullsize") or "").strip()
        img_alt = str(img_item.get("alt") or "").replace("\r", " ").replace("\n", " ").strip()
        if not img_alt and idx < len(rec_images) and isinstance(rec_images[idx], dict):
            img_alt = str(rec_images[idx].get("alt") or "").replace("\r", " ").replace("\n", " ").strip()

        if img_url and img_url not in media_urls:
            media_urls.append(img_url)
        if img_alt and img_alt not in alt_texts:
            alt_texts.append(img_alt[:300])

    # view_images가 비어있으나 rec_images에만 존재하는 경우 폴백 복원
    if not view_images and rec_images:
        for img_item in rec_images:
            if not isinstance(img_item, dict):
                continue
            img_alt = str(img_item.get("alt") or "").replace("\r", " ").replace("\n", " ").strip()
            blob = img_item.get("image") if isinstance(img_item.get("image"), dict) else {}
            ref = blob.get("ref") if isinstance(blob.get("ref"), dict) else {}
            cid = str(ref.get("$link") or "").strip()
            if author_did and cid:
                constructed_url = f"https://cdn.bsky.app/img/feed_thumbnail/plain/{author_did}/{cid}@jpeg"
                if constructed_url not in media_urls:
                    media_urls.append(constructed_url)
            if img_alt and img_alt not in alt_texts:
                alt_texts.append(img_alt[:300])

    # 3. 비디오 포함 여부 (app.bsky.embed.video)
    has_video = (
        "app.bsky.embed.video" in view_type
        or "app.bsky.embed.video" in rec_type
        or bool(view_embed.get("playlist"))
    )
    if has_video:
        vid_url = str(view_embed.get("playlist") or view_embed.get("thumbnail") or "").strip()
        vid_alt = str(view_embed.get("alt") or rec_embed.get("alt") or "").replace("\r", " ").replace("\n", " ").strip()
        if vid_url and vid_url not in media_urls:
            media_urls.append(vid_url)
        if vid_alt and vid_alt not in alt_texts:
            alt_texts.append(vid_alt[:300])

    # 외부 카드 썸네일이나 설명이 있고 alt_texts가 비어 있으면 보조 설명으로 보존
    if external_desc and len(external_desc) >= 8 and not alt_texts:
        alt_texts.append(external_desc[:240])

    return {
        "external_link": external_uri,
        "external_title": external_title[:200],
        "media_urls": media_urls,
        "alt_texts": alt_texts,
        "alt_text": " | ".join(alt_texts)[:300],
        "has_video": has_video,
        "has_media": bool(media_urls or has_video or external_uri),
    }


def fetch_bluesky_posts(limit_per_query: int = 8) -> tuple[list[dict], list[dict]]:
    """Bluesky 공개 XRPC API를 통해 전략 쿼리별 최신 포스트와 멀티모달 메타데이터를 수집한다."""
    observed_at = datetime.now(timezone.utc).isoformat()
    headers = {
        "User-Agent": "InternationalAnalysisOSINT/1.0 (Academic/SupplyChain EarlyWarning)",
        "Accept": "application/json",
    }

    deduped_posts: dict[str, dict] = {}
    query_receipts: list[dict] = []

    print(f"[{SOURCE_ID}] Bluesky AT Protocol 공개 API 수집 시작 ({len(WATCH_QUERIES)}개 감시 쿼리, 멀티모달 메타데이터 포함)...")

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
            q_media_count = 0

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

                mm = _extract_bsky_multimodal(post, record, did)
                if not text and not mm["has_media"]:
                    continue

                created_at = record.get("createdAt", observed_at)
                langs = record.get("langs") or []
                lang_str = langs[0] if isinstance(langs, list) and langs else "unknown"

                rkey = uri.split("/")[-1] if "/" in uri else ""
                post_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else "https://bsky.app"

                content_hash = hashlib.sha256(
                    f"{uri}|{created_at}|{text[:120]}".encode("utf-8", errors="ignore")
                ).hexdigest()[:16]

                if mm["has_media"]:
                    q_media_count += 1

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
                        "external_link": mm["external_link"],
                        "external_title": mm["external_title"],
                        "media_urls": mm["media_urls"],
                        "alt_texts": mm["alt_texts"],
                        "alt_text": mm["alt_text"],
                        "has_video": mm["has_video"],
                        "has_media": mm["has_media"],
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
                "media_items_fetched": q_media_count,
            })
            print(f"  ✓ '{q_str}': {len(posts)}건 수신 (미디어/외부카드 포함: {q_media_count}건)")

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
            for p in posts:
                row_copy = dict(p)
                if isinstance(row_copy.get("media_urls"), list):
                    row_copy["media_urls"] = ";".join(row_copy["media_urls"])
                if isinstance(row_copy.get("alt_texts"), list):
                    row_copy["alt_texts"] = " | ".join(row_copy["alt_texts"])
                writer.writerow(row_copy)

    media_post_count = sum(1 for p in posts if p.get("media_urls") or p.get("has_video"))
    ext_card_count = sum(1 for p in posts if p.get("external_link"))

    receipt = {
        "collector": "scripts/collection/fetch_bluesky_public.py",
        "source_id": SOURCE_ID,
        "signal_class": "online_information_environment_signal",
        "multimodal_zero_byte_mode": True,
        "observed_at": observed_at,
        "total_unique_posts": len(posts),
        "posts_with_images_or_video": media_post_count,
        "posts_with_external_cards": ext_card_count,
        "queries_executed": len(query_receipts),
        "alert_level_set": False,
        "verification_state_set": False,
        "query_receipts": query_receipts,
        "license_access_note": LICENSE_NOTE,
    }
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)

    print(
        f"\n✅ Bluesky 공개 신호 수집 완료: 고유 포스트 {len(posts)}건 "
        f"(이미지/비디오: {media_post_count}건, 외부 링크카드: {ext_card_count}건)"
    )
    print(f"  - JSON: {json_path}")
    print(f"  - CSV: {csv_path}")
    print(f"  - 영수증: {receipt_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bluesky AT Protocol 공개 지정학·공급망 신호 수집기")
    parser.add_argument("--limit-per-query", type=int, default=8, help="쿼리당 최대 수집 건수 (기본 8)")
    args = parser.parse_args()

    posts, receipts = fetch_bluesky_posts(limit_per_query=args.limit_per_query)
    save_outputs(posts, receipts)
    return 0 if posts else 1


if __name__ == "__main__":
    raise SystemExit(main())
