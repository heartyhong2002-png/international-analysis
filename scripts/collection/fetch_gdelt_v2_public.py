"""Bounded collector for the public GDELT 2.0 DOC API."""
from __future__ import annotations
import argparse, json, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "gdelt_v2_public"
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://api.gdeltproject.org/api/v2/doc/doc"

def collect(query: str, maxrecords: int = 25, retries: int = 2) -> dict:
    params = {"query": query, "mode": "artlist", "format": "json", "maxrecords": maxrecords, "sort": "datedesc"}
    receipt = {"collector":"gdelt_v2_public", "endpoint":URL, "query":query, "params":params,
               "observed_at":datetime.now(timezone.utc).isoformat(), "complete":False, "status":None, "rows":0}
    last_error = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(URL, params=params, timeout=30, headers={"User-Agent":"international-analysis/collector"})
            receipt["status"] = r.status_code
            if r.status_code == 429:
                wait = min(30, int(r.headers.get("Retry-After", "5")))
                last_error = "rate_limited"
                if attempt < retries:
                    time.sleep(wait); continue
            r.raise_for_status()
            payload = r.json()
            articles = payload.get("articles", []) if isinstance(payload, dict) else []
            receipt.update({"rows":len(articles), "complete":True, "error":None})
            return {"receipt":receipt, "articles":articles}
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries: time.sleep(min(10, 2 ** attempt))
    receipt["error"] = last_error
    return {"receipt":receipt, "articles":[]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--query", default='"Red Sea" shipping'); p.add_argument("--maxrecords", type=int, default=25)
    a=p.parse_args(); result=collect(a.query, max(1,min(250,a.maxrecords)))
    path=OUT/"latest.json"; path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"GDELT v2: {result['receipt']['status']} rows={result['receipt']['rows']} complete={result['receipt']['complete']} saved={path}")

if __name__ == "__main__": main()
