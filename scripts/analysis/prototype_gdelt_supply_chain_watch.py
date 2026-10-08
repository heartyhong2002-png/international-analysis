"""
Minimal end-to-end GDELT Cloud supply-chain watch prototype.

현재 실험 범위는 홍해·후티·해상 운송이다. 이 파일은 사건을 예측하거나
사실로 확정하지 않고, GDELT Cloud가 반환한 사건을 사람이 검토할 수 있는
"검증 대기 후보"로 정규화한다. AIS·항만·운임 신호가 붙기 전까지는
Alert Level을 계산하지 않는다.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COLLECTION_DIR = PROJECT_ROOT / "scripts" / "collection"
if str(COLLECTION_DIR) not in sys.path:
    sys.path.insert(0, str(COLLECTION_DIR))

from fetch_gdelt_cloud_events import collect

OUTPUT_DIR = PROJECT_ROOT / "data" / "gdelt_cloud"
WATCH_ID = "red_sea_houthi_shipping"
SEARCH = "Houthi Red Sea shipping vessel port maritime security"


def normalize_event(event: dict, collected_at: str) -> dict:
    articles = event.get("top_articles") or []
    source_urls = [a.get("source_url") for a in articles if a.get("source_url")]
    source_urls = list(dict.fromkeys(source_urls))
    return {
        "watch_id": WATCH_ID,
        "event_id": event.get("id"),
        "title": event.get("title"),
        "summary": event.get("summary"),
        "category": event.get("category"),
        "event_code": event.get("event_code"),
        "event_date": event.get("event_date"),
        "observed_at": event.get("observed_at"),
        "collected_at": collected_at,
        "geo": event.get("geo"),
        "actors": event.get("actors"),
        "source_url": event.get("url") or (source_urls[0] if source_urls else None),
        "cross_source_links": source_urls,
        "source_type": "gdelt_cloud_structured_event",
        "verification_state": "unverified_candidate",
        "risk_relevance": "maritime_supply_chain_review",
        "claim_status": "not_applicable_event_cluster_requires_external_check",
    }


def main() -> int:
    bundle = collect(days=7, limit=10, max_pages=1, search=SEARCH)
    candidates = [normalize_event(event, bundle["collected_at"]) for event in bundle["events"]]
    result = {
        "schema_version": "1.0",
        "prototype": WATCH_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query": SEARCH,
        "coverage": {
            "complete": bundle["complete"],
            "page_count": bundle["page_count"],
            "row_count": bundle["row_count"],
            "note": "Candidate signals only; no alert level until independent sensors are joined.",
        },
        "candidates": candidates,
        "raw_receipt": bundle,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "supply_chain_watch_latest.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] prototype={WATCH_ID} candidates={len(candidates)} complete={bundle['complete']}")
    print(f"  output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

