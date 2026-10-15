"""Bounded ACLED event collector using OAuth credentials from environment."""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
try:
 from dotenv import load_dotenv
 load_dotenv(ROOT / ".env", override=True)
except ImportError:
 pass
OUT=ROOT/"data"/"acled"; OUT.mkdir(parents=True,exist_ok=True)
def main():
 p=argparse.ArgumentParser(); p.add_argument("--country"); p.add_argument("--limit",type=int,default=100); a=p.parse_args()
 rec={"collector":"acled","observed_at":datetime.now(timezone.utc).isoformat(),"complete":False,"rows":0}
 user=os.getenv("ACLED_USERNAME",""); password=os.getenv("ACLED_PASSWORD","")
 if not user or not password: rec.update(status="AUTH_REQUIRED",access_note="Set ACLED_USERNAME and ACLED_PASSWORD"); out={"receipt":rec,"events":[]}
 else:
  try:
   tok=requests.post("https://acleddata.com/oauth/token",data={"username":user,"password":password,"grant_type":"password","client_id":"acled","scope":"authenticated"},timeout=30); tok.raise_for_status(); token=tok.json()["access_token"]
   params={"limit":max(1,min(500,a.limit))};
   if a.country: params["country"]=a.country
   r=requests.get("https://acleddata.com/api/acled/read",params=params,headers={"Authorization":f"Bearer {token}"},timeout=30); rec["status"]=r.status_code; r.raise_for_status(); data=r.json(); rows=data.get("data",[]) if isinstance(data,dict) else []; rec.update(rows=len(rows),complete=True); out={"receipt":rec,"events":rows}
  except Exception as e: rec["error"]=f"{type(e).__name__}: {e}"; out={"receipt":rec,"events":[]}
 (OUT/"latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8"); print(f"ACLED: {rec.get('status')} rows={rec['rows']}")
if __name__=="__main__": main()
