"""
fetch_federal_register.py — 미국 연방관보(Federal Register) 정책·통상·수출통제 공식 고시 수집기 (Packet A)
========================================================================================================

설계 원칙 (Data Contract):
1. 조기경보 목적:
   - 미국 정부의 행정명령, 대중/대러 수출통제(BIS Entity List), 제재(OFAC), 관세/통상(USTR/ITA) 규칙을
     공식 REST API를 통해 신속하고 안정적으로 포착한다.
2. 스키마 준수 (shared_schema: official_raw_v1):
   - document_number, title, publication_date, agencies, action, type, abstract, html_url, pdf_url,
     source_id, relationship_role, packet, observed_at, content_hash 보존.
3. 안전성 & 경량성:
   - 별도 API 키 불필요 (Public US Gov API).
   - pandas/yfinance 등 무거운 C 빌드 없이 순수 requests + csv 표준 모듈로 구현 (스마트폰/엣지 노드 호환).
   - 단일 출처로 Alert Level을 산출하거나 선거 승패를 예측하지 않는다.
4. 산출물:
   - data/federal_register/federal_register_latest.json
   - data/federal_register/federal_register_latest.csv
   - data/federal_register/receipt_latest.json (수집 영수증)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
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
DATA_DIR = ROOT / "data" / "federal_register"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_ID = "us_federal_register_documents_api"
RELATIONSHIP_ROLE = "domestic_us"
PACKET = "A"
LICENSE_NOTE = "Public Federal Register REST API; no API key. US government work; retain source URL + document number."

BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"

# 조기경보 감시 핵심 기관 슬러그 (통상, 수출통제, 제재, 외교, 안보)
WATCH_AGENCIES = [
    "industry-and-security-bureau",          # 상무부 산업안보국 (수출통제, Entity List)
    "international-trade-administration",     # 상무부 국제무역청 (반덤핑, 상계관세)
    "foreign-assets-control-office",          # 재무부 해외자산통제국 (OFAC 제재)
    "trade-representative-office-of-united-states",  # 미 무역대표부 (USTR 관세, 301조)
    "customs-and-border-protection",          # 관세국경보호청 (CBP 강제노동 수입금지)
    "state-department",                       # 국무부 (방위물자수출, 제재)
]

# 이슈 태그 분류 규칙 (구문/단어 경계 — 짧은 토큰 부분문자열 오탐 방지)
ISSUE_TAG_RULES = {
    "US_Export_Control": [
        r"export administration regulations",
        r"entity list",
        r"\bbis\b",
        r"export control",
        r"unverified list",
        r"bureau of industry and security",
    ],
    "US_Trade_Tariff": [
        r"tariff",
        r"anti-dumping",
        r"countervailing",
        r"section 301",
        r"trade representative",
        r"import relief",
    ],
    "US_Sanctions_OFAC": [
        r"sanctions",
        r"specially designated",
        r"\bsdn\b",
        r"\bofac\b",
        r"blocking property",
        r"russian harmful",
    ],
    "US_Industrial_Policy_CHIPS": [
        r"chips act",
        r"semiconductor",
        r"science act",
        r"critical minerals",
        r"supply chain",
    ],
    "US_Immigration_Border": [
        r"border protection",
        r"\bcustoms\b",
        r"withhold release",
        r"forced labor",
        r"uyghur",
    ],
}


def tag_issue(title: str, abstract: str) -> list[str]:
    """문서 제목 및 초록을 기반으로 조기경보 감시 이슈 태그를 결정론적으로 매핑한다."""
    text = f"{title} {abstract}".lower()
    tags = []
    for tag, patterns in ISSUE_TAG_RULES.items():
        if any(re.search(pat, text) for pat in patterns):
            tags.append(tag)
    return tags or ["US_General_Policy"]


def fetch_federal_register_documents(per_page: int = 20, max_pages: int = 1) -> list[dict]:
    """Federal Register 공식 REST API를 호출하여 최신 정책·규칙 문서를 수집한다."""
    observed_at = datetime.now(timezone.utc).isoformat()
    all_documents = []
    headers = {
        "User-Agent": "InternationalAnalysisBot/1.0 (OSINT Research; mailto:contact@example.com)"
    }

    params = {
        "conditions[type][]": ["RULE", "PRORULE", "NOTICE"],
        "conditions[agencies][]": WATCH_AGENCIES,
        "order": "newest",
        "per_page": per_page,
    }

    print(f"[{SOURCE_ID}] Federal Register 공식 API 호출 중 (최신 {per_page * max_pages}건 한도)...")

    for page in range(1, max_pages + 1):
        params["page"] = page
        try:
            resp = requests.get(BASE_URL, params=params, headers=headers, timeout=20)
            if resp.status_code != 200:
                print(f"  ⚠️ HTTP 오류 ({resp.status_code}): {resp.text[:120]}")
                break

            data = resp.json()
            results = data.get("results", [])
            if not results:
                print("  ℹ️ 추가 문서가 없습니다.")
                break

            for doc in results:
                doc_num = doc.get("document_number", "")
                title = doc.get("title", "").strip()
                abstract = (doc.get("abstract") or "").strip()
                pub_date = doc.get("publication_date", "")
                html_url = doc.get("html_url", "")
                pdf_url = doc.get("pdf_url", "")
                doc_type = doc.get("type", "")
                action = doc.get("action", "")
                agencies = [a.get("name", "") for a in doc.get("agencies", []) if isinstance(a, dict)]
                agency_names = "; ".join(agencies)

                # 고유 식별 해시 (문서번호 + 공표일 + 제목)
                content_hash = hashlib.sha256(
                    f"{doc_num}|{pub_date}|{title}".encode("utf-8", errors="ignore")
                ).hexdigest()[:16]

                issue_tags = tag_issue(title, abstract)

                record = {
                    "source_id": SOURCE_ID,
                    "relationship_role": RELATIONSHIP_ROLE,
                    "packet": PACKET,
                    "document_number": doc_num,
                    "title": title,
                    "publication_date": pub_date,
                    "agencies": agency_names,
                    "action": action,
                    "doc_type": doc_type,
                    "abstract": abstract,
                    "html_url": html_url,
                    "pdf_url": pdf_url,
                    "issue_tags": ";".join(issue_tags),
                    "content_hash": content_hash,
                    "observed_at": observed_at,
                    "license_access_note": LICENSE_NOTE,
                }
                all_documents.append(record)

            print(f"  ✓ {page}페이지 수집 완료: {len(results)}건")

        except Exception as e:
            print(f"  ❌ API 요청 실패 (page {page}): {e}")
            break

    return all_documents


def save_documents_and_receipt(documents: list[dict]) -> None:
    """수집된 문서들을 JSON, CSV 및 감사 영수증(receipt)으로 저장한다."""
    observed_at = datetime.now(timezone.utc).isoformat()
    json_path = DATA_DIR / "federal_register_latest.json"
    csv_path = DATA_DIR / "federal_register_latest.csv"
    receipt_path = DATA_DIR / "receipt_latest.json"

    # 1. JSON 저장
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    # 2. CSV 저장 (빈 결과여도 헤더만 써 JSON과 동기화 — stale CSV 방지)
    fieldnames = list(documents[0].keys()) if documents else [
        "source_id", "relationship_role", "packet", "document_number", "title",
        "publication_date", "agencies", "action", "doc_type", "abstract",
        "html_url", "pdf_url", "issue_tags", "content_hash", "observed_at",
        "license_access_note",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if documents:
            writer.writerows(documents)

    # 3. 수집 영수증(Receipt) 저장
    receipt = {
        "collector": "scripts/collection/fetch_federal_register.py",
        "source_id": SOURCE_ID,
        "relationship_role": RELATIONSHIP_ROLE,
        "packet": PACKET,
        "observed_at": observed_at,
        "total_items_collected": len(documents),
        "status": "SUCCESS" if documents else "EMPTY",
        "alert_level_set": False,
        "verification_state_set": False,
        "notes": "Federal Register public documents ingested under official_raw_v1 contract. No alert escalation performed.",
    }
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 수집 완료: 총 {len(documents)}건")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV:  {csv_path}")
    print(f"  - 영수증: {receipt_path}")


def main():
    parser = argparse.ArgumentParser(description="Federal Register Official Policy Ingestion (Packet A)")
    parser.add_argument("--per-page", type=int, default=20, help="페이지당 수집 문서 수 (기본: 20)")
    parser.add_argument("--pages", type=int, default=1, help="수집 페이지 수 (기본: 1)")
    args = parser.parse_args()

    docs = fetch_federal_register_documents(per_page=args.per_page, max_pages=args.pages)
    save_documents_and_receipt(docs)


if __name__ == "__main__":
    main()
