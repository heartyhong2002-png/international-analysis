"""
텔레그램 공개 채널(Public Web) OSINT 데이터 수집기 (0-Byte 무다운로드 멀티모달 확장)
======================================================================================
- 계정 로그인이나 비공개 채널 잠입 없이 100% 합법적인 공개 웹 프리뷰(t.me/s/...)만 수집합니다.
- 원본 이미지(.jpg, .png)나 영상(.mp4) 바이너리를 절대 로컬 디스크나 Git에 다운로드하지 않고,
  프리뷰 HTML에 존재하는 Photo_URL, Video_URL, Media_URLs, Has_Media 메타데이터만 추출합니다.
- 전황 지도나 현장 사진만 올라오고 텍스트가 10자 미만으로 짧은 게시물이라도,
  Photo_URL이나 Video_URL이 존재하면 유실 없이 수집합니다.
- 소셜/채널 게시물은 online_information_environment_signal로만 기록하며,
  단독으로 Alert Level을 격상하거나 객관적 사실(Ground Truth)로 확정하지 않습니다.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "signal_gap"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV = DATA_DIR / "telegram_osint_latest.csv"
OUTPUT_JSON = DATA_DIR / "telegram_osint_latest.json"
RECEIPT_FILE = DATA_DIR / "telegram_receipt_latest.json"

# 타겟 텔레그램 공개 채널 (OSINT 주요 소스 — 공개 웹 프리뷰 허용 채널만)
TELEGRAM_CHANNELS = {
    "Russia_Rybar": {
        "channel_id": "rybar",
        "issue_tags": "Ukraine_War;EU_Russia",
        "desc": "러시아 군사/지정학 밀블로거 (전황 지도 및 실물 관측)",
    },
    "Ukraine_Live": {
        "channel_id": "UaOnlii",
        "issue_tags": "Ukraine_War;Baltic_Security",
        "desc": "우크라이나 현지 실시간 속보 채널",
    },
    "Iran_IRGC_Proxy": {
        "channel_id": "sepah_pasdaran",
        "issue_tags": "Iran_Nuclear;Middle_East_Energy",
        "desc": "이란 혁명수비대(IRGC) 관련 공개 채널",
    },
    "Saudi_AlArabiya": {
        "channel_id": "AlArabiya",
        "issue_tags": "Middle_East_Energy;Israel_Palestine",
        "desc": "사우디아라비아 알Arabiya 공개 뉴스 채널",
    },
    "Yemen_Houthi": {
        "channel_id": "army21ye",
        "issue_tags": "Middle_East_Energy;Red_Sea_Disruption",
        "desc": "예멘 후티 반군 대변인 공개 성명 채널",
    },
}

_BG_URL_RE = re.compile(r"background-image\s*:\s*url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)", re.IGNORECASE)
_NOISE_URL_PATTERNS = re.compile(
    r"(/|_|-)(avatar|emoji|favicon|icon|logo|pixel|spacer|sprite|badge)s?(/|_|-|\.)|\b1x1\b|\.svg(\?|$)|^data:image/",
    re.IGNORECASE,
)


def _is_clean_media_url(url: str) -> bool:
    u = (url or "").strip()
    if not u or len(u) < 10 or not u.startswith(("http://", "https://")):
        return False
    if _NOISE_URL_PATTERNS.search(u):
        return False
    return True


def _extract_bg_url(tag) -> str:
    if not tag:
        return ""
    style_str = tag.get("style") or ""
    m = _BG_URL_RE.search(style_str)
    if m:
        candidate = m.group(1).strip()
        if _is_clean_media_url(candidate):
            return candidate
    return ""


def fetch_telegram_public():
    print("🕵️‍♂️ 텔레그램 공개 채널 OSINT 수집 시작 (0-Byte 무다운로드 멀티모달 메타데이터 모드)...")

    observed_at = datetime.now(timezone.utc).isoformat()
    collected_data: list[dict] = []
    channel_receipts: list[dict] = []
    total_media_posts = 0

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    for region, meta in TELEGRAM_CHANNELS.items():
        channel_id = meta["channel_id"]
        url = f"https://t.me/s/{channel_id}"
        print(f"\n[{region}] 공개 프리뷰 접근 중: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code != 200:
                print(f"  ⚠️ 채널 접속 실패 (HTTP {response.status_code})")
                channel_receipts.append({
                    "region": region,
                    "channel_id": channel_id,
                    "source_url": url,
                    "http_status": response.status_code,
                    "parse_status": "HTTP_ERROR",
                    "items_collected": 0,
                    "media_items_collected": 0,
                })
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            msg_wraps = soup.find_all("div", class_="tgme_widget_message_wrap")
            if not msg_wraps:
                msg_wraps = soup.find_all("div", class_="tgme_widget_message")

            if not msg_wraps:
                print("  ⚠️ 공개 프리뷰 메시지 블록을 찾을 수 없습니다.")
                channel_receipts.append({
                    "region": region,
                    "channel_id": channel_id,
                    "source_url": url,
                    "http_status": 200,
                    "parse_status": "EMPTY_PREVIEW",
                    "items_collected": 0,
                    "media_items_collected": 0,
                })
                continue

            recent_wraps = msg_wraps[-10:]
            channel_count = 0
            channel_media_count = 0

            for wrap in recent_wraps:
                msg_box = (
                    wrap
                    if "tgme_widget_message" in (wrap.get("class") or [])
                    else wrap.find("div", class_="tgme_widget_message")
                ) or wrap

                # 1. 개별 메시지 고유 링크(data-post) 및 발행 시각 추출
                data_post = msg_box.get("data-post", "")
                post_url = f"https://t.me/{data_post}" if data_post else url

                time_tag = msg_box.find("time")
                pub_time = (
                    time_tag.get("datetime")
                    if time_tag and time_tag.get("datetime")
                    else observed_at
                )

                # 2. 본문 텍스트 추출
                text_div = msg_box.find("div", class_="tgme_widget_message_text")
                text_content = text_div.get_text(separator=" ", strip=True) if text_div else ""

                # 3. Photo_URL 추출 (a.tgme_widget_message_photo_wrap 배경 이미지)
                photo_urls: list[str] = []
                for p_wrap in msg_box.find_all("a", class_="tgme_widget_message_photo_wrap"):
                    p_url = _extract_bg_url(p_wrap)
                    if p_url and p_url not in photo_urls:
                        photo_urls.append(p_url)

                # 4. Video_URL 추출 (video 태그 src 또는 i.tgme_widget_message_video_thumb 배경 썸네일)
                video_urls: list[str] = []
                for v_tag in msg_box.find_all("video"):
                    v_src = (v_tag.get("src") or "").strip()
                    if _is_clean_media_url(v_src) and v_src not in video_urls:
                        video_urls.append(v_src)

                for v_thumb in msg_box.find_all("i", class_="tgme_widget_message_video_thumb"):
                    vt_url = _extract_bg_url(v_thumb)
                    if vt_url and vt_url not in video_urls:
                        video_urls.append(vt_url)

                # 5. 문서/첨부파일 제목 확인
                doc_title_div = msg_box.find("div", class_="tgme_widget_message_document_title")
                doc_title = doc_title_div.get_text(strip=True) if doc_title_div else ""

                photo_url = photo_urls[0] if photo_urls else ""
                video_url = video_urls[0] if video_urls else ""
                has_media = bool(photo_url or video_url or doc_title)

                # (핵심 규칙) 텍스트가 10자 이상이거나, 짧더라도 Photo_URL/Video_URL이 존재하면 유실 없이 수집!
                if len(text_content) < 10 and not has_media:
                    continue

                # 텍스트가 없거나 20자 미만인 지도/사진 단독 게시물의 경우 전처리 엔티티 복원을 위해 맥락 보강
                effective_text = text_content
                if has_media and len(effective_text) < 20:
                    media_kind = "Tactical Map / Photo" if photo_url else "Field Video"
                    tag_hint = meta["issue_tags"].replace(";", ", ")
                    prefix = f"{effective_text} ".strip()
                    effective_text = (
                        f"{prefix}[Telegram {media_kind} OSINT | {region} ({tag_hint}) | {meta['desc']}]"
                    ).strip()

                hash_seed = f"{channel_id}|{post_url}|{effective_text[:120]}|{photo_url}|{video_url}"
                content_hash = hashlib.sha256(
                    hash_seed.encode("utf-8", errors="ignore")
                ).hexdigest()[:16]

                if has_media:
                    channel_media_count += 1
                    total_media_posts += 1

                collected_data.append({
                    "Source_ID": "telegram_osint_public",
                    "Signal_Class": "online_information_environment_signal",
                    "Verification_State": "UNVERIFIED",
                    "Region": region,
                    "Channel_ID": f"@{channel_id}",
                    "Channel_Desc": meta["desc"],
                    "Issue_Tags": meta["issue_tags"],
                    "Source_URL": post_url,
                    "Message_Content": effective_text[:600],
                    "Photo_URL": photo_url,
                    "Video_URL": video_url,
                    "Media_URL": photo_url or video_url,
                    "Media_URLs": ";".join(photo_urls + video_urls),
                    "Document_Title": doc_title,
                    "Has_Media": has_media,
                    "Published_At": pub_time,
                    "Scraped_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Observed_At_UTC": observed_at,
                    "Content_Hash": content_hash,
                })
                channel_count += 1

            channel_receipts.append({
                "region": region,
                "channel_id": channel_id,
                "source_url": url,
                "http_status": 200,
                "parse_status": "SUCCESS",
                "items_collected": channel_count,
                "media_items_collected": channel_media_count,
            })
            print(
                f"  ✓ {region} (@{channel_id}): {channel_count}건 수집 완료 "
                f"(멀티모달 첨부: {channel_media_count}건)"
            )

        except Exception as e:
            print(f"  ❌ 에러 발생 (@{channel_id}): {e}")
            channel_receipts.append({
                "region": region,
                "channel_id": channel_id,
                "source_url": url,
                "http_status": None,
                "parse_status": "ERROR",
                "items_collected": 0,
                "media_items_collected": 0,
                "error": str(e)[:160],
            })

    receipt_payload = {
        "collector": "scripts/collection/fetch_telegram_public.py",
        "source_id": "telegram_osint_public",
        "signal_class": "online_information_environment_signal",
        "multimodal_zero_byte_mode": True,
        "observed_at": observed_at,
        "total_items_collected": len(collected_data),
        "total_media_items_collected": total_media_posts,
        "alert_level_set": False,
        "verification_state_set": False,
        "channels": channel_receipts,
        "license_access_note": (
            "Public Telegram web preview (t.me/s/) only; 0-byte metadata extraction "
            "(Photo_URL/Video_URL without binary download)."
        ),
    }
    with open(RECEIPT_FILE, "w", encoding="utf-8") as f:
        json.dump(receipt_payload, f, ensure_ascii=False, indent=2)

    if collected_data:
        fieldnames = list(collected_data[0].keys())
        with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(collected_data)

        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(collected_data, f, ensure_ascii=False, indent=2)

        print(
            f"\n✅ 텔레그램 공개 OSINT 수집 완료: 총 {len(collected_data)}건 "
            f"(멀티모달 사진/영상 포함: {total_media_posts}건)"
        )
        print(f"  - CSV: {OUTPUT_CSV}")
        print(f"  - JSON: {OUTPUT_JSON}")
        print(f"  - 영수증: {RECEIPT_FILE}")
        return collected_data
    else:
        print("\n⚠️ 수집된 데이터가 없습니다.")
        return []


if __name__ == "__main__":
    fetch_telegram_public()
