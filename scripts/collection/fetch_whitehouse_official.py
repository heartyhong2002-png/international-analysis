"""Collect public White House releases from the official RSS feed.

RSS is the primary discovery path.  The sitemap is an optional, bounded
fallback for finding pages that did not appear in the feed.  This collector
stores metadata and raw responses only; it does not decide whether a claim is
true or raise an alert.

Usage::

    python scripts/collection/fetch_whitehouse_official.py
    python scripts/collection/fetch_whitehouse_official.py --days 14 --include-sitemap
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 원시 RSS와 JSON 영수증을 다른 수집기와 분리해 저장한다.
OUTPUT_DIR = PROJECT_ROOT / "data" / "whitehouse_official"
# 백악관 Releases의 공식 RSS. HTML 검색보다 먼저 사용해 요청 수를 줄인다.
RSS_URL = "https://www.whitehouse.gov/releases/feed/"
# RSS에 누락된 공개 URL을 확인할 때만 사용하는 보완 경로다.
SITEMAP_INDEX_URL = "https://www.whitehouse.gov/sitemap_index.xml"
REQUEST_TIMEOUT = 30
# 사이트맵을 켜더라도 대량 크롤링으로 확장되지 않도록 상한을 둔다.
MAX_SITEMAPS = 5
MAX_SITEMAP_URLS = 200
REQUEST_HEADERS = {
    "User-Agent": "international-analysis/early-warning white-house-rss-client",
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
}
ALLOWED_PATHS = ("/releases/", "/briefings-statements/", "/presidential-actions/", "/fact-sheets/", "/remarks/", "/research/")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_date(value: str | None) -> str | None:
    """RSS의 RFC 날짜를 UTC ISO 8601 문자열로 정규화한다."""
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if local_name(child.tag) == name:
            text = "".join(child.itertext()).strip()
            return text or None
    return None


def rss_records(xml_bytes: bytes, *, cutoff: datetime, observed_at: str) -> list[dict[str, Any]]:
    """RSS item을 공통 원시 레코드로 변환한다.

    여기서는 주장 내용의 진위나 위험도를 판단하지 않는다. 해당 작업은
    별도의 교차검증·LLM 세션에서 수행한다.
    """
    root = ET.fromstring(xml_bytes)
    records: list[dict[str, Any]] = []
    for element in root.iter():
        if local_name(element.tag) != "item":
            continue
        published_raw = child_text(element, "pubdate") or child_text(element, "date")
        published_at = parse_date(published_raw)
        if published_at and datetime.fromisoformat(published_at) < cutoff:
            continue
        link = child_text(element, "link")
        if not link:
            continue
        records.append(
            {
                "source_id": "whitehouse_releases_rss",
                "source_type": "official_statement",
                "publisher": "The White House",
                "country": "US",
                "source_url": link,
                "published_at": published_at,
                "observed_at": observed_at,
                "title": child_text(element, "title"),
                "summary": child_text(element, "description") or child_text(element, "encoded"),
                "document_type": child_text(element, "category") or "release",
                "guid": child_text(element, "guid"),
                "raw_ref": "rss_latest.xml",
                "parse_status": "SUCCESS",
                "license_access_note": "Official public White House RSS; retain source URL and respect robots.txt.",
            }
        )
    return records


def sitemap_urls(xml_bytes: bytes) -> list[str]:
    """사이트맵 XML에서 허용된 백악관 문서 경로만 추출한다."""
    root = ET.fromstring(xml_bytes)
    urls: list[str] = []
    for element in root.iter():
        if local_name(element.tag) != "loc":
            continue
        value = (element.text or "").strip()
        if value.endswith(".xml"):
            continue
        if "whitehouse.gov" in value and any(path in value for path in ALLOWED_PATHS):
            urls.append(value)
    return urls[:MAX_SITEMAP_URLS]


def fetch(session: requests.Session, url: str) -> requests.Response:
    """공식 공개 URL만 요청하고 HTTP 오류는 호출자에게 전달한다."""
    response = session.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


def collect(*, days: int, limit: int, include_sitemap: bool) -> dict[str, Any]:
    """RSS를 수집하고 필요할 때 제한된 사이트맵 URL을 보완한다."""
    observed_at = utc_now().isoformat()
    cutoff = utc_now() - timedelta(days=days)
    receipt: dict[str, Any] = {
        "source_id": "whitehouse_official",
        "rss_url": RSS_URL,
        "sitemap_url": SITEMAP_INDEX_URL if include_sitemap else None,
        "observed_at": observed_at,
        "status": "SUCCESS",
        "access_method": "official_rss" if not include_sitemap else "official_rss+official_sitemap",
        "errors": [],
    }
    with requests.Session() as session:
        # 1단계: RSS 원문을 먼저 받아 빠른 신규 발표 감지에 사용한다.
        try:
            rss_response = fetch(session, RSS_URL)
            rss_bytes = rss_response.content
        except requests.RequestException as exc:
            receipt["status"] = "BLOCKED"
            receipt["errors"].append(f"RSS: {type(exc).__name__}")
            return {
                "schema_version": "1.0",
                "source": "whitehouse_official",
                "collected_at": observed_at,
                "query": {"days": days, "limit": limit, "include_sitemap": include_sitemap},
                "receipt": receipt,
                "records": [],
            }

        # 원문 XML을 보존해 나중에 동일 응답을 재검토할 수 있게 한다.
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "rss_latest.xml").write_bytes(rss_bytes)

        try:
            records = rss_records(rss_bytes, cutoff=cutoff, observed_at=observed_at)[:limit]
        except (ET.ParseError, ValueError) as exc:
            receipt["status"] = "PARSE_ERROR"
            receipt["errors"].append(f"RSS parse: {type(exc).__name__}")
            records = []

        # 2단계: 명시적으로 켠 경우에만 사이트맵을 제한적으로 조회한다.
        sitemap_records: list[dict[str, Any]] = []
        if include_sitemap:
            try:
                index_response = fetch(session, SITEMAP_INDEX_URL)
                root = ET.fromstring(index_response.content)
                child_sitemaps = [
                    (element.text or "").strip()
                    for element in root.iter()
                    if local_name(element.tag) == "loc" and (element.text or "").strip().endswith(".xml")
                ][:MAX_SITEMAPS]
                for sitemap_url in child_sitemaps:
                    try:
                        sitemap_response = fetch(session, sitemap_url)
                        for url in sitemap_urls(sitemap_response.content):
                            sitemap_records.append(
                                {
                                    "source_id": "whitehouse_official_sitemap",
                                    "source_type": "official_statement",
                                    "publisher": "The White House",
                                    "country": "US",
                                    "source_url": url,
                                    "published_at": None,
                                    "observed_at": observed_at,
                                    "title": None,
                                    "summary": None,
                                    "document_type": "sitemap_discovery",
                                    "guid": None,
                                    "raw_ref": "sitemap_index.xml",
                                    "parse_status": "SUCCESS",
                                    "license_access_note": "Official public White House sitemap; page content not downloaded by default.",
                                }
                            )
                    except (requests.RequestException, ET.ParseError) as exc:
                        receipt["errors"].append(f"sitemap: {type(exc).__name__}")
            except (requests.RequestException, ET.ParseError) as exc:
                receipt["status"] = "PARTIAL"
                receipt["errors"].append(f"sitemap index: {type(exc).__name__}")

    rss_row_count = len(records)
    # RSS와 사이트맵이 같은 문서를 반환할 수 있으므로 URL로 중복 제거한다.
    known_urls = {record["source_url"] for record in records}
    for record in sitemap_records:
        if record["source_url"] not in known_urls:
            records.append(record)
            known_urls.add(record["source_url"])

    receipt["rss_row_count"] = rss_row_count
    receipt["sitemap_discovery_count"] = len(sitemap_records)
    receipt["content_downloaded"] = False
    return {
        "schema_version": "1.0",
        "source": "whitehouse_official",
        "collected_at": observed_at,
        "query": {"days": days, "limit": limit, "include_sitemap": include_sitemap},
        "receipt": receipt,
        "records": records,
        "raw": {"rss_sha256": sha256_bytes(rss_bytes), "raw_ref": "rss_latest.xml"},
    }


def save(bundle: dict[str, Any]) -> tuple[Path, Path]:
    """타임스탬프 아카이브와 최신 포인터를 함께 저장한다."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(bundle["collected_at"]).strftime("%Y%m%dT%H%M%SZ")
    archive_path = OUTPUT_DIR / f"whitehouse_{stamp}.json"
    latest_path = OUTPUT_DIR / "whitehouse_latest.json"
    serialized = json.dumps(bundle, ensure_ascii=False, indent=2)
    archive_path.write_text(serialized, encoding="utf-8")
    latest_path.write_text(serialized, encoding="utf-8")
    return archive_path, latest_path


def main() -> int:
    """CLI 진입점. 기본값은 RSS만 소량 수집하는 보수적 모드다."""
    parser = argparse.ArgumentParser(description="Collect White House official RSS releases")
    parser.add_argument("--days", type=int, default=7, choices=range(1, 32))
    parser.add_argument("--limit", type=int, default=50, choices=range(1, 501))
    parser.add_argument("--include-sitemap", action="store_true", help="bounded sitemap discovery fallback")
    args = parser.parse_args()

    try:
        bundle = collect(days=args.days, limit=args.limit, include_sitemap=args.include_sitemap)
        # The raw RSS is written during collection; the JSON receipt remains
        # useful even when the source is blocked.
        archive_path, latest_path = save(bundle)
    except (OSError, requests.RequestException, RuntimeError) as exc:
        print(f"[ERROR] White House collector: {type(exc).__name__}: {exc}")
        return 1

    print(f"[{bundle['receipt']['status']}] White House records={len(bundle['records'])}")
    print(f"  archive: {archive_path}")
    print(f"  latest: {latest_path}")
    return 0 if bundle["receipt"]["status"] in {"SUCCESS", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
