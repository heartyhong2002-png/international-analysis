"""
fetch_govinfo.py — 미국 정부 공식 간행물(GovInfo API) 수집기 (Packet A)
=======================================================================

공식 문서: https://api.govinfo.gov/docs/
인증 방식: .env 환경변수 GOVINFO_API_KEY (X-Api-Key 헤더)

수집 대상 (컬렉션별 독립 호출):
1. GAOREPORTS — 미국 회계감사원(GAO) 정부 공식 보고서
2. CHRG       — 미국 의회 청문회 (Congressional Hearings)
3. CREC       — 미국 의회 기록 (Congressional Record)
4. PLAW       — 공법 및 법률 (Public and Private Laws)
5. CPD        — 대통령 문서 (Compilation of Presidential Documents)

설계 원칙:
- 기존 official_raw_v1 스키마 호환 (data/govinfo/govinfo_latest.json, .csv, receipt_latest.json)
- 컬렉션별 독립 호출 및 오류 격리
- packageId 기반 중복 수집 방지
- API Rate Limit 준수 (요청 간 슬립 + bounded pageSize)
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
from datetime import datetime, timedelta, timezone
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

DATA_DIR = ROOT / "data" / "govinfo"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_ID = "us_govinfo_api"
RELATIONSHIP_ROLE = "domestic_us"
PACKET = "A"
BASE_URL = "https://api.govinfo.gov"
LICENSE_NOTE = "GovInfo API (U.S. GPO); API key required via GOVINFO_API_KEY. US government work; retain source URL + packageId."

COLLECTIONS = [
    ("GAOREPORTS", "gao_report", "미국 회계감사원(GAO) 공식 보고서"),
    ("CHRG", "congressional_hearing", "미국 의회 청문회"),
    ("CREC", "congressional_record", "미국 의회 기록"),
    ("PLAW", "public_law", "미국 공법·법률"),
    ("CPD", "presidential_document", "미국 대통령 공식 문서"),
]

ISSUE_TAG_RULES = {
    "US_Trade_Tariff": [r"tariff", r"trade", r"customs", r"import", r"export"],
    "US_Export_Control": [r"export control", r"semiconductor", r"chips", r"technology", r"supply chain"],
    "US_Sanctions_OFAC": [r"sanction", r"iran", r"russia", r"china", r"north korea"],
    "US_Defense_Security": [r"defense", r"national security", r"military", r"taiwan", r"ukraine", r"foreign"],
    "US_Presidential_Action": [r"executive order", r"proclamation", r"memorandum", r"president"],
}


def tag_issue(title: str, doc_type: str) -> list[str]:
    text = f"{title} {doc_type}".lower()
    tags = [tag for tag, pats in ISSUE_TAG_RULES.items() if any(re.search(p, text) for p in pats)]
    return tags or ["US_Gov_Document"]


def _fetch_collection(
    session: requests.Session,
    collection_code: str,
    start_iso: str,
    api_key: str,
    page_size: int,
) -> tuple[dict[str, Any] | None, str | None, int | None]:
    """단일 GovInfo 컬렉션을 독립 호출한다."""
    url = f"{BASE_URL}/collections/{collection_code}/{start_iso}"
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "InternationalAnalysisBot/1.0 (OSINT Research)",
    }
    params = {"pageSize": page_size, "offsetMark": "*"}
    try:
        resp = session.get(url, params=params, headers=headers, timeout=25)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:160]}", resp.status_code
        return resp.json(), None, 200
    except requests.RequestException as exc:
        return None, f"{type(exc).__name__}: {exc}", None
    except ValueError as exc:
        return None, f"JSONParseError: {exc}", None


def fetch_govinfo_documents(days: int = 14, page_size: int = 15) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """GovInfo API에서 5대 공식 컬렉션을 독립적으로 수집한다."""
    observed_at = datetime.now(timezone.utc).isoformat()
    start_dt = datetime.now(timezone.utc) - timedelta(days=days)
    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    api_key = (os.getenv("GOVINFO_API_KEY") or "").strip()

    collection_receipts: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    seen_pkg_ids: set[str] = set()

    if not api_key:
        print(f"[{SOURCE_ID}] ⚠️ GOVINFO_API_KEY가 .env에 설정되지 않았습니다 (AUTH_REQUIRED).")
        return documents, {
            "status": "AUTH_REQUIRED",
            "collections": collection_receipts,
            "error": "GOVINFO_API_KEY not set in environment/.env",
        }

    print(f"[{SOURCE_ID}] GovInfo API 호출 중 (최근 {days}일, 컬렉션당 최대 {page_size}건)...")

    with requests.Session() as session:
        for col_code, doc_type, desc in COLLECTIONS:
            data, err, status_code = _fetch_collection(session, col_code, start_iso, api_key, page_size)
            if err:
                print(f"  ⚠️ [{col_code}] {desc} 수집 실패: {err}")
                collection_receipts.append({
                    "collection": col_code,
                    "http_status": status_code,
                    "status": "FAILED",
                    "items": 0,
                    "error": err[:160],
                })
            else:
                packages = data.get("packages", []) if isinstance(data, dict) else []
                added = 0
                for pkg in packages:
                    pkg_id = str(pkg.get("packageId") or "").strip()
                    if not pkg_id or pkg_id in seen_pkg_ids:
                        continue
                    seen_pkg_ids.add(pkg_id)

                    title = (pkg.get("title") or "").strip()
                    date_issued = (pkg.get("dateIssued") or pkg.get("lastModified") or "")[:10]
                    last_mod = pkg.get("lastModified") or ""
                    pkg_link = pkg.get("packageLink") or ""
                    source_url = f"https://www.govinfo.gov/app/details/{pkg_id}"
                    pdf_url = f"https://www.govinfo.gov/content/pkg/{pkg_id}/pdf/{pkg_id}.pdf"
                    congress = str(pkg.get("congress") or "")
                    doc_class = pkg.get("docClass") or col_code
                    summary = f"[{col_code} | {desc}] Issued: {date_issued} | Package: {pkg_id}".strip()

                    content_hash = hashlib.sha256(f"{pkg_id}|{last_mod}|{title}".encode("utf-8", errors="ignore")).hexdigest()[:16]
                    documents.append({
                        "source_id": SOURCE_ID,
                        "relationship_role": RELATIONSHIP_ROLE,
                        "packet": PACKET,
                        "package_id": pkg_id,
                        "collection_code": col_code,
                        "doc_type": doc_type,
                        "doc_class": str(doc_class),
                        "congress": congress,
                        "title": title,
                        "publication_date": date_issued,
                        "last_modified": last_mod,
                        "summary": summary,
                        "source_url": source_url,
                        "pdf_url": pdf_url,
                        "api_url": pkg_link,
                        "issue_tags": ";".join(tag_issue(title, doc_type)),
                        "content_hash": content_hash,
                        "observed_at": observed_at,
                        "license_access_note": LICENSE_NOTE,
                    })
                    added += 1
                print(f"  ✓ [{col_code}] {desc}: {added}건 수집 완료")
                collection_receipts.append({
                    "collection": col_code,
                    "http_status": 200,
                    "status": "SUCCESS",
                    "items": added,
                    "error": None,
                })

            time.sleep(0.3)  # Rate limit 준수

    any_ok = any(c["status"] == "SUCCESS" for c in collection_receipts)
    overall_status = "SUCCESS" if (any_ok and all(c["status"] == "SUCCESS" for c in collection_receipts)) else ("PARTIAL" if any_ok else "FAILED")
    return documents, {"status": overall_status, "collections": collection_receipts, "error": None}


def save_documents_and_receipt(documents: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    observed_at = datetime.now(timezone.utc).isoformat()
    json_path = DATA_DIR / "govinfo_latest.json"
    csv_path = DATA_DIR / "govinfo_latest.csv"
    receipt_path = DATA_DIR / "receipt_latest.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    fieldnames = list(documents[0].keys()) if documents else [
        "source_id", "relationship_role", "packet", "package_id", "collection_code",
        "doc_type", "doc_class", "congress", "title", "publication_date",
        "last_modified", "summary", "source_url", "pdf_url", "api_url",
        "issue_tags", "content_hash", "observed_at", "license_access_note",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if documents:
            writer.writerows(documents)

    receipt = {
        "collector": "scripts/collection/fetch_govinfo.py",
        "source_id": SOURCE_ID,
        "relationship_role": RELATIONSHIP_ROLE,
        "packet": PACKET,
        "observed_at": observed_at,
        "total_items_collected": len(documents),
        "status": meta["status"],
        "collections": meta["collections"],
        "error": meta["error"],
        "alert_level_set": False,
        "verification_state_set": False,
        "notes": "GovInfo API ingestion under official_raw_v1 contract. No API key stored in artifacts.",
    }
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)

    print(f"\n[{meta['status']}] GovInfo 수집 완료: 총 {len(documents)}건")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV:  {csv_path}")
    print(f"  - 영수증: {receipt_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="GovInfo Official Publications Ingestion (Packet A)")
    parser.add_argument("--days", type=int, default=14, help="최근 며칠 변경분 조회 (기본: 14일)")
    parser.add_argument("--page-size", type=int, default=15, help="컬렉션당 최대 수집 건수 (기본: 15)")
    args = parser.parse_args()

    docs, meta = fetch_govinfo_documents(days=args.days, page_size=args.page_size)
    save_documents_and_receipt(docs, meta)
    return 0 if meta["status"] in {"SUCCESS", "PARTIAL", "AUTH_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
