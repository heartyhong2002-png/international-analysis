"""Bounded official X API recent-search collector (optional; not default).

Access (confirm in developer.x.com before spending credits):
  - Product: X API v2 recent search
  - Endpoint: GET https://api.x.com/2/tweets/search/recent
  - Auth: Authorization: Bearer <X_BEARER_TOKEN>
  - Billing: pay-per-use post reads (not free). Do not call from the default
    pipeline. Prefer --max-results 10 and a narrow query.

This collector stores public post metadata + a receipt only. Posts are
`online_information_environment_signal`, not national opinion, ground truth,
or an Alert Level input by themselves. Private accounts, invite-only spaces,
login bypass, and scraping outside the official API are out of scope.

Usage::

    python scripts/collection/fetch_x_public.py
    python scripts/collection/fetch_x_public.py --query "Red Sea shipping" --max-results 10
    python scripts/run_pipeline.py --collect-only --with-x
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass

OUT = ROOT / "data" / "x_public"
RAW_DIR = OUT / "raw"
OUT.mkdir(parents=True, exist_ok=True)

API_URL = "https://api.x.com/2/tweets/search/recent"
SOURCE_ID = "x_public_api"
LICENSE_NOTE = (
    "Official X API v2 recent search only. Pay-per-use credits apply. "
    "Bearer token stays in the Authorization header and is never written to "
    "receipts. Public posts only; online_information_environment_signal, not "
    "national opinion or alert basis. Not called by the default pipeline."
)
DEFAULT_QUERY = '("Red Sea" OR Hormuz OR Houthi) (shipping OR tanker OR strait) -is:retweet lang:en'
SECRET_QUERY = re.compile(
    r"(?i)(?:(bearer\s+)([A-Za-z0-9_\-\.%]{16,})|(oauth_token=|access_token=)([^\s\"']{8,}))"
)
USER_AGENT = "international-analysis/early-warning x-api-recent-search"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_bearer() -> str:
    return (
        os.getenv("X_BEARER_TOKEN", "").strip()
        or os.getenv("TWITTER_BEARER_TOKEN", "").strip()
        or os.getenv("X_API_BEARER_TOKEN", "").strip()
    )


def redact(text: str, secret: str) -> str:
    cleaned = text
    if secret:
        cleaned = cleaned.replace(secret, "[REDACTED]")

    def _sub(match: re.Match[str]) -> str:
        if match.group(1):
            return f"{match.group(1)}[REDACTED]"
        return f"{match.group(3)}[REDACTED]"

    return SECRET_QUERY.sub(_sub, cleaned)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def post_hash(post: dict[str, Any]) -> str:
    blob = json.dumps(post, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def base_receipt(query: str, observed_at: str) -> dict[str, Any]:
    return {
        "collector": "x_public",
        "source_id": SOURCE_ID,
        "endpoint": API_URL,
        "auth_method": "HTTP Authorization Bearer; token not stored",
        "query": query,
        "observed_at": observed_at,
        "complete": False,
        "rows": 0,
        "status": "DISABLED",
        "http_status": None,
        "content_hash": None,
        "raw_ref": None,
        "access_note": None,
        "license_access_note": LICENSE_NOTE,
        "signal_class": "online_information_environment_signal",
        "error": None,
    }


def normalize_post(
    tweet: dict[str, Any],
    *,
    users: dict[str, dict[str, Any]],
    observed_at: str,
    raw_ref: str,
) -> dict[str, Any]:
    author_id = str(tweet.get("author_id") or "")
    user = users.get(author_id, {})
    post_id = str(tweet.get("id") or "")
    username = user.get("username")
    source_url = f"https://x.com/{username}/status/{post_id}" if username and post_id else None
    return {
        "source_id": SOURCE_ID,
        "source_type": "online_expression",
        "signal_class": "online_information_environment_signal",
        "post_id": post_id or None,
        "author_id": author_id or None,
        "author_username": username,
        "author_type": "public_account",
        "text": tweet.get("text"),
        "language": tweet.get("lang"),
        "created_at": tweet.get("created_at"),
        "public_metrics": tweet.get("public_metrics"),
        "referenced_posts": tweet.get("referenced_tweets") or [],
        "source_url": source_url,
        "published_at": tweet.get("created_at"),
        "observed_at": observed_at,
        "content_hash": post_hash(tweet),
        "raw_ref": raw_ref,
        "parse_status": "SUCCESS",
        "license_access_note": LICENSE_NOTE,
    }


def response_note(response: requests.Response, secret: str) -> str:
    note = ""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                first = errors[0] if isinstance(errors[0], dict) else {}
                note = str(first.get("message") or first.get("detail") or first.get("title") or "")
            else:
                note = str(payload.get("detail") or payload.get("title") or payload.get("note") or "")
    except ValueError:
        note = ""
    cleaned = redact(note, secret).strip()
    return cleaned[:240] or f"HTTP {response.status_code}"


def collect(query: str, max_results: int, timeout: float) -> dict[str, Any]:
    observed_at = utc_now().isoformat()
    receipt = base_receipt(query, observed_at)
    receipt["max_results"] = max_results
    secret = load_bearer()
    if not secret:
        receipt["status"] = "AUTH_REQUIRED"
        receipt["access_note"] = (
            "Set X_BEARER_TOKEN (or TWITTER_BEARER_TOKEN) from the X Developer Portal. "
            "No request was sent. Recent search is pay-per-use."
        )
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}

    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,lang,public_metrics,referenced_tweets,author_id",
        "expansions": "author_id",
        "user.fields": "username,name,verified",
    }
    headers = {
        "Authorization": f"Bearer {secret}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=timeout)
    except requests.Timeout:
        receipt["status"] = "TIMEOUT"
        receipt["error"] = "Timeout"
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}
    except requests.RequestException as exc:
        receipt["status"] = "BLOCKED"
        receipt["error"] = redact(type(exc).__name__, secret)
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}

    receipt["http_status"] = response.status_code
    if response.status_code in {401, 403}:
        receipt["status"] = "AUTH_REQUIRED"
        receipt["access_note"] = (
            "X API rejected the bearer token or product access. "
            "Confirm developer app, recent-search entitlement, and prepaid credits. Header not stored."
        )
        receipt["error"] = response_note(response, secret)
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}
    if response.status_code == 429:
        receipt["status"] = "RATE_LIMITED"
        receipt["access_note"] = "X API rate limit. No automatic retry in this collector."
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}
    if response.status_code == 402:
        receipt["status"] = "AUTH_REQUIRED"
        receipt["access_note"] = "Payment or prepaid credits required. No further pages requested."
        receipt["error"] = response_note(response, secret)
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}
    if response.status_code != 200:
        receipt["status"] = "PARSE_ERROR" if response.status_code < 500 else "BLOCKED"
        receipt["error"] = response_note(response, secret)
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}

    raw_bytes = response.content
    if secret.encode("utf-8") in raw_bytes:
        receipt["status"] = "PARSE_ERROR"
        receipt["error"] = "Refusing to store a response that contains the bearer token"
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}

    content_hash = sha256_bytes(raw_bytes)
    raw_name = f"{content_hash}.json"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / raw_name).write_bytes(raw_bytes)
    receipt["content_hash"] = content_hash
    receipt["raw_ref"] = f"data/x_public/raw/{raw_name}"

    try:
        payload = response.json()
    except ValueError:
        receipt["status"] = "PARSE_ERROR"
        receipt["error"] = "Response was not JSON"
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}

    tweets = payload.get("data") if isinstance(payload, dict) else None
    if tweets is None:
        tweets = []
    if not isinstance(tweets, list):
        receipt["status"] = "PARSE_ERROR"
        receipt["error"] = "Missing data[]"
        return {"schema_version": "1.0", "receipt": receipt, "posts": []}

    includes = payload.get("includes") if isinstance(payload, dict) else {}
    users_list = includes.get("users", []) if isinstance(includes, dict) else []
    users = {
        str(user.get("id")): user
        for user in users_list
        if isinstance(user, dict) and user.get("id") is not None
    }
    records = [
        normalize_post(tweet, users=users, observed_at=observed_at, raw_ref=receipt["raw_ref"])
        for tweet in tweets
        if isinstance(tweet, dict)
    ]
    meta = payload.get("meta") if isinstance(payload, dict) else {}
    next_token = meta.get("next_token") if isinstance(meta, dict) else None
    receipt["rows"] = len(records)
    receipt["more_pages"] = bool(next_token)
    receipt["complete"] = not bool(next_token)
    receipt["status"] = "PARTIAL" if next_token else "SUCCESS"
    receipt["access_note"] = (
        "One recent-search page only. next_token was not followed to limit pay-per-use cost. "
        "Results are public posts, not population opinion."
    )
    # Do not persist next_token; it is a pagination cursor, not a secret, but
    # leaving it out keeps receipts smaller and avoids accidental multi-page loops.
    return {"schema_version": "1.0", "receipt": receipt, "posts": records}


def save(bundle: dict[str, Any], secret: str) -> Path:
    latest = OUT / "latest.json"
    serialized = redact(json.dumps(bundle, ensure_ascii=False, indent=2), secret)
    if secret and secret in serialized:
        raise RuntimeError("Refusing to write a receipt that still contains the bearer token")
    latest.write_text(serialized, encoding="utf-8")
    return latest


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect one page of public X posts via official recent search")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="X recent-search query (public posts only)")
    parser.add_argument("--max-results", type=int, default=10, help="Posts to request (10-25; API allows up to 100)")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    max_results = max(10, min(25, args.max_results))
    secret = load_bearer()
    bundle = collect(args.query, max_results, args.timeout)
    latest = save(bundle, secret)
    receipt = bundle["receipt"]
    print(
        f"X public: status={receipt['status']} http={receipt['http_status']} rows={receipt['rows']}"
    )
    print(f"  latest: {latest}")
    if receipt.get("access_note"):
        print(f"  note: {receipt['access_note']}")
    return 0 if receipt["status"] in {"SUCCESS", "PARTIAL", "AUTH_REQUIRED", "DISABLED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
