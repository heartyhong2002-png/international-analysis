"""
fetch_congress_gov.py — 미국 의회(Congress.gov API v3) 공식 입법·법안·CRS 보고서 수집기 (Packet A)
================================================================================================

공식 문서: https://api.congress.gov/
인증 방식: .env 환경변수 CONGRESS_GOV_API_KEY (X-Api-Key 헤더)

수집 대상:
1. /v3/bill      — 미국 의회 법안, 입법 동향, 최신 법안 처리 현황(latestAction)
2. /v3/crsreport — 의회조사국(CRS) 공식 정책·안보·통상 보고서

설계 원칙:
- 기존 official_raw_v1 스키마 호환 (data/congress_gov/congress_gov_latest.json, .csv, receipt_latest.json)
- 엔드포인트별 독립 호출 및 오류 격리
- document_id / source_url 기반 중복 수집 방지
- API Rate Limit 준수 (요청 간 슬립 + bounded limit)
- API Key는 절대 로그/영수증/산출물에 기록하지 않음
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data" / "congress_gov"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_ID = "us_congress_gov_api"
RELATIONSHIP_ROLE = "domestic_us"
PACKET = "A"
BASE_URL = "https://api.congress.gov/v3"
LICENSE_NOTE = "Congress.gov API v3; API key required via CONGRESS_GOV_API_KEY. US government work; retain source URL."

ISSUE_TAG_RULES = {
    "US_Trade_Tariff": [r"tariff", r"trade", r"section 301", r"customs", r"import", r"export"],
    "US_Export_Control": [r"export control", r"semiconductor", r"chips", r"entity list", r"dual-use", r"ai "],
    "US_Sanctions_OFAC": [r"sanction", r"ofac", r"iran", r"russia", r"china", r"north korea", r"blocking"],
    "US_Defense_Security": [r"defense", r"ndaa", r"national security", r"military", r"taiwan", r"ukraine", r"nato"],
    "US_Debt_Budget": [r"appropriation", r"debt ceiling", r"budget", r"fiscal", r"continuing resolution"],
}


def tag_issue(title: str, summary: str) -> list[str]:
    text = f"{title} {summary}".lower()
    tags = [tag for tag, pats in ISSUE_TAG_RULES.items() if any(re.search(p, text) for p in pats)]
    return tags or ["US_Legislative_Policy"]


def _web_bill_url(congress: Any, bill_type: str, bill_number: Any, fallback_api_url: str) -> str:
    """Congress.gov 웹 원문 URL을 생성한다."""
    type_map = {
        "HR": "house-bill",
        "S": "senate-bill",
        "HJRES": "house-joint-resolution",
        "SJRES": "senate-joint-resolution",
        "HCONRES": "house-concurrent-resolution",
        "SCONRES": "senate-concurrent-resolution",
        "HRES": "house-resolution",
        "SRES": "senate-resolution",
    }
    bt = (bill_type or "").upper()
    slug = type_map.get(bt)
    if congress and slug and bill_number:
        return f"https://www.congress.gov/bill/{congress}th-congress/{slug}/{bill_number}"
    return fallback_api_url


def _fetch_endpoint(
    session: requests.Session,
    endpoint: str,
    api_key: str,
    params: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, int | None]:
    """단일 Congress.gov API 엔드포인트를 독립 호출한다."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "InternationalAnalysisBot/1.0 (OSINT Research)",
    }
    try:
        resp = session.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:160]}", resp.status_code
        return resp.json(), None, 200
    except requests.RequestException as exc:
        return None, f"{type(exc).__name__}: {exc}", None
    except ValueError as exc:
        return None, f"JSONParseError: {exc}", None


def fetch_congress_documents(limit: int = 20) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Congress.gov API v3에서 의회 법안(/bill)과 CRS 보고서(/crsreport)를 독립 수집한다."""
    observed_at = datetime.now(timezone.utc).isoformat()
    api_key = (os.getenv("CONGRESS_GOV_API_KEY") or "").strip()

    endpoint_receipts: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if not api_key:
        print(f"[{SOURCE_ID}] ⚠️ CONGRESS_GOV_API_KEY가 .env에 설정되지 않았습니다 (AUTH_REQUIRED).")
        return documents, {
            "status": "AUTH_REQUIRED",
            "endpoints": endpoint_receipts,
            "error": "CONGRESS_GOV_API_KEY not set in environment/.env",
        }

    print(f"[{SOURCE_ID}] Congress.gov API v3 호출 중 (엔드포인트당 최대 {limit}건)...")

    with requests.Session() as session:
        # 1. 의회 법안 및 처리 현황 (/v3/bill)
        data, err, status_code = _fetch_endpoint(
            session,
            "bill",
            api_key,
            {"format": "json", "limit": limit, "sort": "updateDate desc"},
        )
        if err:
            print(f"  ⚠️ [/bill] 수집 실패: {err}")
            endpoint_receipts.append({"endpoint": "/v3/bill", "http_status": status_code, "status": "FAILED", "items": 0, "error": err[:160]})
        else:
            bills = data.get("bills", []) if isinstance(data, dict) else []
            added = 0
            for b in bills:
                congress = b.get("congress")
                bill_type = (b.get("type") or "").upper()
                bill_num = b.get("number")
                doc_id = f"{congress}-{bill_type}-{bill_num}"
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)

                title = (b.get("title") or "").strip()
                latest_action = b.get("latestAction") or {}
                action_date = latest_action.get("actionDate") or ""
                action_text = (latest_action.get("text") or "").strip()
                update_date = b.get("updateDate") or action_date
                origin_chamber = b.get("originChamber") or ""
                api_url = b.get("url") or ""
                source_url = _web_bill_url(congress, bill_type, bill_num, api_url)
                summary = f"[{origin_chamber} {bill_type} {bill_num}] Latest Action ({action_date}): {action_text}".strip()

                content_hash = hashlib.sha256(f"{doc_id}|{update_date}|{title}".encode("utf-8", errors="ignore")).hexdigest()[:16]
                documents.append({
                    "source_id": SOURCE_ID,
                    "relationship_role": RELATIONSHIP_ROLE,
                    "packet": PACKET,
                    "document_id": doc_id,
                    "doc_type": "congress_bill",
                    "congress": str(congress or ""),
                    "chamber": origin_chamber,
                    "title": title,
                    "publication_date": str(action_date or update_date)[:10],
                    "latest_action": action_text,
                    "summary": summary,
                    "source_url": source_url,
                    "api_url": api_url,
                    "issue_tags": ";".join(tag_issue(title, summary)),
                    "content_hash": content_hash,
                    "observed_at": observed_at,
                    "license_access_note": LICENSE_NOTE,
                })
                added += 1
            print(f"  ✓ [/bill] {added}건 수집 완료")
            endpoint_receipts.append({"endpoint": "/v3/bill", "http_status": 200, "status": "SUCCESS", "items": added, "error": None})

        time.sleep(0.25)  # Rate limit 준수

        # 2. CRS 의회조사국 보고서 (/v3/crsreport)
        data, err, status_code = _fetch_endpoint(
            session,
            "crsreport",
            api_key,
            {"format": "json", "limit": limit},
        )
        if err:
            print(f"  ⚠️ [/crsreport] 수집 실패: {err}")
            endpoint_receipts.append({"endpoint": "/v3/crsreport", "http_status": status_code, "status": "FAILED", "items": 0, "error": err[:160]})
        else:
            reports = data.get("CRSReports", []) if isinstance(data, dict) else []
            added = 0
            for r in reports:
                rep_id = str(r.get("id") or "").strip()
                doc_id = f"CRS-{rep_id}" if rep_id else ""
                if doc_id and doc_id in seen_ids:
                    continue
                if doc_id:
                    seen_ids.add(doc_id)

                title = (r.get("title") or "").strip()
                pub_date = (r.get("publishDate") or r.get("updateDate") or "")[:10]
                status = r.get("status") or ""
                content_type = r.get("contentType") or "CRS Report"
                api_url = r.get("url") or ""
                source_url = f"https://crsreports.congress.gov/product/details?prodcode={rep_id}" if rep_id else api_url
                summary = f"[{content_type} | {status}] {title}".strip()

                content_hash = hashlib.sha256(f"{doc_id}|{pub_date}|{title}".encode("utf-8", errors="ignore")).hexdigest()[:16]
                documents.append({
                    "source_id": SOURCE_ID,
                    "relationship_role": RELATIONSHIP_ROLE,
                    "packet": PACKET,
                    "document_id": doc_id,
                    "doc_type": "crs_report",
                    "congress": "",
                    "chamber": "CRS",
                    "title": title,
                    "publication_date": pub_date,
                    "latest_action": status,
                    "summary": summary,
                    "source_url": source_url,
                    "api_url": api_url,
                    "issue_tags": ";".join(tag_issue(title, summary)),
                    "content_hash": content_hash,
                    "observed_at": observed_at,
                    "license_access_note": LICENSE_NOTE,
                })
                added += 1
            print(f"  ✓ [/crsreport] {added}건 수집 완료")
            endpoint_receipts.append({"endpoint": "/v3/crsreport", "http_status": 200, "status": "SUCCESS", "items": added, "error": None})

    any_ok = any(ep["status"] == "SUCCESS" for ep in endpoint_receipts)
    overall_status = "SUCCESS" if (any_ok and all(ep["status"] == "SUCCESS" for ep in endpoint_receipts)) else ("PARTIAL" if any_ok else "FAILED")
    return documents, {"status": overall_status, "endpoints": endpoint_receipts, "error": None}


def save_documents_and_receipt(documents: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    observed_at = datetime.now(timezone.utc).isoformat()
    json_path = DATA_DIR / "congress_gov_latest.json"
    csv_path = DATA_DIR / "congress_gov_latest.csv"
    receipt_path = DATA_DIR / "receipt_latest.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    fieldnames = list(documents[0].keys()) if documents else [
        "source_id", "relationship_role", "packet", "document_id", "doc_type",
        "congress", "chamber", "title", "publication_date", "latest_action",
        "summary", "source_url", "api_url", "issue_tags", "content_hash",
        "observed_at", "license_access_note",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if documents:
            writer.writerows(documents)

    receipt = {
        "collector": "scripts/collection/fetch_congress_gov.py",
        "source_id": SOURCE_ID,
        "relationship_role": RELATIONSHIP_ROLE,
        "packet": PACKET,
        "observed_at": observed_at,
        "total_items_collected": len(documents),
        "status": meta["status"],
        "endpoints": meta["endpoints"],
        "error": meta["error"],
        "alert_level_set": False,
        "verification_state_set": False,
        "notes": "Congress.gov API v3 ingestion under official_raw_v1 contract. No API key stored in artifacts.",
    }
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)

    print(f"\n[{meta['status']}] Congress.gov 수집 완료: 총 {len(documents)}건")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV:  {csv_path}")
    print(f"  - 영수증: {receipt_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Congress.gov API v3 Official Legislative Ingestion (Packet A)")
    parser.add_argument("--limit", type=int, default=20, help="엔드포인트당 최대 수집 건수 (기본: 20)")
    args = parser.parse_args()

    docs, meta = fetch_congress_documents(limit=args.limit)
    save_documents_and_receipt(docs, meta)
    return 0 if meta["status"] in {"SUCCESS", "PARTIAL", "AUTH_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
