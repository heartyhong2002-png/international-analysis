"""Bounded Media Cloud Search API collector (candidate; not in default pipeline).

Official client (mediacloud/api-client) uses:
  base: https://search.mediacloud.org/api/
  auth: Authorization: Token <MEDIACLOUD_API_KEY>
  story list: GET search/story-list
  required filters: cs (collection ids) and/or ss (source ids)

Legacy host api.mediacloud.org no longer resolves (DNS failure). This collector
stores raw story metadata + a receipt only. It does not set verification_state
or Alert Level. API keys and Authorization headers are never written to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass

OUT = ROOT / "data" / "mediacloud"
OUT.mkdir(parents=True, exist_ok=True)

DEFAULT_BASE = "https://search.mediacloud.org/api/"
DEFAULT_ENDPOINT = "search/story-list"
# Media Cloud rejects story-list without cs/ss (HTTP 422). US National is a
# documented public collection used only as a bounded probe default.
DEFAULT_COLLECTION_IDS = "34412234"
PLATFORM = "onlinenews-mediacloud"
REQUEST_TIMEOUT = 30
USER_AGENT = "international-analysis/early-warning mediacloud-search-client"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def redact(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "[REDACTED]")


def parse_id_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def content_hash(payload: Any) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_params(
    *,
    query: str,
    start: date,
    end: date,
    collection_ids: list[str],
    source_ids: list[str],
    page_size: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "q": query,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "platform": PLATFORM,
        "page_size": page_size,
    }
    if collection_ids:
        params["cs"] = ",".join(collection_ids)
    if source_ids:
        params["ss"] = ",".join(source_ids)
    return params


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded Media Cloud Search API probe")
    parser.add_argument("--query", default='"Red Sea" OR shipping OR Houthi')
    parser.add_argument("--limit", type=int, default=10, help="page_size (1-50)")
    parser.add_argument("--days", type=int, default=7, help="lookback window ending today (UTC)")
    parser.add_argument(
        "--collection-ids",
        default=os.getenv("MEDIACLOUD_COLLECTION_IDS", DEFAULT_COLLECTION_IDS),
        help="comma-separated Media Cloud collection ids (cs)",
    )
    parser.add_argument(
        "--source-ids",
        default=os.getenv("MEDIACLOUD_SOURCE_IDS", ""),
        help="comma-separated Media Cloud source ids (ss)",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("MEDIACLOUD_BASE_URL", DEFAULT_BASE),
        help="Search API base URL ending with /api/",
    )
    args = parser.parse_args()

    key = os.getenv("MEDIACLOUD_API_KEY", "").strip()
    base = args.base_url.rstrip("/") + "/"
    endpoint = base + DEFAULT_ENDPOINT
    collection_ids = parse_id_list(args.collection_ids)
    source_ids = parse_id_list(args.source_ids)
    page_size = max(1, min(50, args.limit))
    end = utc_now().date()
    start = end - timedelta(days=max(1, args.days))
    observed_at = utc_now().isoformat()

    receipt: dict[str, Any] = {
        "collector": "mediacloud",
        "api_version": "search_v4",
        "endpoint": endpoint,
        "query": args.query,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "collection_ids": collection_ids,
        "source_ids": source_ids,
        "page_size": page_size,
        "observed_at": observed_at,
        "complete": False,
        "rows": 0,
        "license_access_note": (
            "Media Cloud Search API; academic/research account with weekly quota. "
            "Use Authorization Token header only. Keep off default pipeline."
        ),
    }

    stories: list[dict[str, Any]] = []

    if not key:
        receipt.update(
            status="AUTH_REQUIRED",
            access_note="Set MEDIACLOUD_API_KEY (profile token). Do not put the key in the URL.",
        )
    elif not collection_ids and not source_ids:
        receipt.update(
            status="PARSE_ERROR",
            access_note="Media Cloud requires cs (collection_ids) and/or ss (source_ids).",
        )
    else:
        params = build_params(
            query=args.query,
            start=start,
            end=end,
            collection_ids=collection_ids,
            source_ids=source_ids,
            page_size=page_size,
        )
        headers = {
            "Authorization": f"Token {key}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            receipt["http_status"] = response.status_code
            if response.status_code == 401:
                receipt.update(status="AUTH_REQUIRED", access_note="Token rejected (HTTP 401).")
            elif response.status_code == 422:
                receipt.update(
                    status="PARSE_ERROR",
                    access_note="Missing or invalid cs/ss filters (HTTP 422).",
                )
            elif response.status_code == 429:
                receipt.update(status="RATE_LIMITED", access_note="Media Cloud rate limit (HTTP 429).")
            else:
                response.raise_for_status()
                data = response.json()
                rows = data.get("stories", []) if isinstance(data, dict) else []
                if not isinstance(rows, list):
                    rows = []
                stories = rows
                receipt.update(
                    status="SUCCESS" if rows else "PARTIAL",
                    rows=len(rows),
                    complete=True,
                    pagination_token_present=bool(
                        isinstance(data, dict) and data.get("pagination_token")
                    ),
                    raw_ref="latest.json",
                    content_hash=content_hash({"stories": rows}),
                )
                if isinstance(data, dict) and data.get("pagination_token"):
                    receipt["complete"] = False
                    receipt["access_note"] = "First page only; pagination_token present."
        except Exception as exc:  # noqa: BLE001 - collector must isolate failures
            msg = redact(f"{type(exc).__name__}: {exc}", key)
            receipt.update(status="BLOCKED" if "Failed to resolve" in msg or "getaddrinfo" in msg else "TIMEOUT" if "Timeout" in type(exc).__name__ else "PARSE_ERROR", error=msg)

    out = {"receipt": receipt, "stories": stories}
    (OUT / "latest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(
        f"Media Cloud: status={receipt.get('status')} http={receipt.get('http_status')} "
        f"rows={receipt['rows']} complete={receipt['complete']}"
    )


if __name__ == "__main__":
    main()
