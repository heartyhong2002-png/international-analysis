"""Bounded Media Cloud search collector; endpoint/key are configurable."""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
try:
 from dotenv import load_dotenv
 load_dotenv(ROOT / ".env")
except ImportError:
 pass

OUT=ROOT/"data"/"mediacloud"; OUT.mkdir(parents=True,exist_ok=True)
DEFAULT_URL="https://api.mediacloud.org/api/v2/stories_public/list"
def main():
 p=argparse.ArgumentParser(); p.add_argument("--query",default='"Red Sea" shipping'); p.add_argument("--limit",type=int,default=25); a=p.parse_args()
 key=os.getenv("MEDIACLOUD_API_KEY",""); url=os.getenv("MEDIACLOUD_SEARCH_URL",DEFAULT_URL)
 rec={"collector":"mediacloud","endpoint":url,"query":a.query,"observed_at":datetime.now(timezone.utc).isoformat(),"complete":False,"rows":0}
 if not key:
  rec.update(status="AUTH_REQUIRED",access_note="Set MEDIACLOUD_API_KEY after account/API approval"); out={"receipt":rec,"stories":[]}
 else:
  try:
   r=requests.get(url,params={"q":a.query,"limit":max(1,min(100,a.limit)),"key":key},timeout=30); rec["status"]=r.status_code; r.raise_for_status(); data=r.json(); rows=data.get("stories",data.get("results",[])) if isinstance(data,dict) else []; rec.update(rows=len(rows),complete=True); out={"receipt":rec,"stories":rows}
  except Exception as e:
   # Never persist API keys that requests may include in an exception URL.
   msg=str(e).replace(key, "[REDACTED]")
   rec["error"]=f"{type(e).__name__}: {msg}"; out={"receipt":rec,"stories":[]}
 (OUT/"latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8"); print(f"Media Cloud: {rec.get('status')} rows={rec['rows']}")
if __name__=="__main__": main()
