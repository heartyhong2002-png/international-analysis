"""
GDELT Cloud v2 Events bounded collector.

역할:
  - GDELT Cloud의 공개 뉴스 사건 구조화 데이터를 조기경보 센서로 저장한다.
  - 원시 사건과 수집 영수증(receipt)을 함께 보존해 부분 수집을 숨기지 않는다.
  - API 키는 GDELT_CLOUD_API_KEY 환경변수에서만 읽는다.

이 스크립트는 DB·대시보드에 직접 연결하지 않는다. 다음 단계에서
source_url, published/observed_at, coverage, verification_state를 가진
파생 신호로 연결한다.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from gdelt_cloud_budget import GDELTCloudBudget, GDELTCloudBudgetExceeded


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "gdelt_cloud"
API_URL = "https://gdeltcloud.com/api/v2/events"
MAX_LIMIT = 50
MAX_PAGES = 10
MAX_RETRIES = 2
QUOTA_STATE_PATH = OUTPUT_DIR / "quota_state.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _retry_after(response: requests.Response) -> float:
    value = response.headers.get("Retry-After", "1")
    try:
        return min(max(float(value), 0.0), 30.0)
    except ValueError:
        return 1.0


def request_page(
    session: requests.Session,
    params: dict[str, Any],
    api_key: str,
    budget: GDELTCloudBudget,
) -> dict[str, Any]:
    """Request one page and fail loudly on auth, plan, quota, or schema errors."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "international-analysis/early-warning gdelt-cloud-client",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        budget.wait_for_interval()
        budget.reserve(reason=f"events page attempt {attempt}")
        response = session.get(API_URL, params=params, headers=headers, timeout=30)
        if response.status_code == 429 and attempt < MAX_RETRIES:
            time.sleep(_retry_after(response))
            continue
        if response.status_code != 200:
            # Do not include Authorization or the full response in routine logs.
            try:
                detail = response.json().get("error", "unknown API error")
            except ValueError:
                detail = response.text[:200]
            raise RuntimeError(f"GDELT Cloud HTTP {response.status_code}: {detail}")

        payload = response.json()
        if payload.get("success") is not True or not isinstance(payload.get("data"), list):
            raise RuntimeError("GDELT Cloud response schema missing success=true and data[]")
        return payload

    raise RuntimeError("GDELT Cloud rate limit retries exhausted")


def collect(
    *,
    days: int,
    limit: int,
    max_pages: int,
    country: str | None = None,
    search: str | None = None,
    category: str | None = None,
    actor_country: str | None = None,
    event_type: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GDELT_CLOUD_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GDELT_CLOUD_API_KEY is not set")
    if not api_key.startswith("gdelt_sk_"):
        raise RuntimeError("GDELT_CLOUD_API_KEY does not have the expected gdelt_sk_ prefix")

    params: dict[str, Any] = {"days": days, "limit": limit}
    optional = {
        "country": country,
        "search": search,
        "category": category,
        "actor_country": actor_country,
        "event_type": event_type,
        "date": date,
    }
    params.update({key: value for key, value in optional.items() if value})

    all_rows: list[dict[str, Any]] = []
    page_receipts: list[dict[str, Any]] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    started_at = _utc_now()

    with requests.Session() as session:
        budget = GDELTCloudBudget(QUOTA_STATE_PATH)
        for page_number in range(1, max_pages + 1):
            page_params = dict(params)
            if cursor:
                page_params["cursor"] = cursor
            payload = request_page(session, page_params, api_key, budget)
            rows = payload["data"]
            all_rows.extend(rows)

            pagination = payload.get("pagination") or {}
            next_cursor = pagination.get("next_cursor")
            page_receipts.append(
                {
                    "page": page_number,
                    "row_count": len(rows),
                    "limit": pagination.get("limit"),
                    "cursor": cursor,
                    "next_cursor_present": bool(next_cursor),
                }
            )

            if not next_cursor:
                complete = True
                break
            if next_cursor in seen_cursors or next_cursor == cursor:
                raise RuntimeError("GDELT Cloud returned a repeated/non-advancing cursor")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        else:
            complete = False

    finished_at = _utc_now()
    return {
        "schema_version": "1.0",
        "source": "gdelt_cloud",
        "endpoint": API_URL,
        "query": params,
        "collected_at": finished_at.isoformat(),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "page_count": len(page_receipts),
        "row_count": len(all_rows),
        "complete": complete,
        "pages": page_receipts,
        "events": all_rows,
        "quota_guard": budget.snapshot(),
    }


def save_receipt(bundle: dict[str, Any], output_dir: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(bundle["collected_at"]).strftime("%Y%m%dT%H%M%SZ")
    archive_path = output_dir / f"events_{stamp}.json"
    latest_path = output_dir / "events_latest.json"
    serialized = json.dumps(bundle, ensure_ascii=False, indent=2)
    archive_path.write_text(serialized, encoding="utf-8")
    latest_path.write_text(serialized, encoding="utf-8")
    return archive_path, latest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded GDELT Cloud v2 Events collector")
    parser.add_argument("--days", type=int, default=1, choices=range(1, 31))
    parser.add_argument("--limit", type=int, default=10, choices=range(1, MAX_LIMIT + 1))
    parser.add_argument("--max-pages", type=int, default=1, choices=range(1, MAX_PAGES + 1))
    parser.add_argument("--country", help="Human-readable country, e.g. Yemen or Saudi Arabia")
    parser.add_argument("--search", help="Semantic search query")
    parser.add_argument("--category", help="Use only a documented GDELT category value")
    parser.add_argument("--actor-country", dest="actor_country")
    parser.add_argument("--event-type", dest="event_type")
    parser.add_argument("--date", help="UTC anchor date YYYY-MM-DD")
    args = parser.parse_args()

    try:
        bundle = collect(
            days=args.days,
            limit=args.limit,
            max_pages=args.max_pages,
            country=args.country,
            search=args.search,
            category=args.category,
            actor_country=args.actor_country,
            event_type=args.event_type,
            date=args.date,
        )
        archive_path, latest_path = save_receipt(bundle)
    except (OSError, requests.RequestException, RuntimeError, GDELTCloudBudgetExceeded) as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(
        f"[OK] GDELT Cloud events: rows={bundle['row_count']}, "
        f"pages={bundle['page_count']}, complete={bundle['complete']}"
    )
    print(f"  archive: {archive_path}")
    print(f"  latest:  {latest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

