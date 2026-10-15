"""Optional Event Registry supplementary collector."""
from __future__ import annotations
import argparse,json,os
from datetime import datetime,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent.parent
try:
 from dotenv import load_dotenv
 load_dotenv(ROOT / ".env")
except ImportError:
 pass
OUT=ROOT/"data"/"event_registry"; OUT.mkdir(parents=True,exist_ok=True)
def main():
 p=argparse.ArgumentParser(); p.add_argument("--query",default="Red Sea shipping"); p.add_argument("--count",type=int,default=25); a=p.parse_args(); key=os.getenv("EVENT_REGISTRY_API_KEY","")
 rec={"collector":"event_registry","observed_at":datetime.now(timezone.utc).isoformat(),"query":a.query,"complete":False,"rows":0}
 if not key: rec.update(status="AUTH_REQUIRED",access_note="Academic access or API subscription required"); out={"receipt":rec,"articles":[]}
 else:
  try:
   body={"apiKey":key,"resultType":"articles","articlesCount":max(1,min(100,a.count)),"keyword":a.query,"articlesSortBy":"date"}; r=requests.post("https://eventregistry.org/api/v1/article/getArticles",json=body,timeout=30); rec["status"]=r.status_code; r.raise_for_status(); data=r.json(); rows=data.get("articles",{}).get("results",[]) if isinstance(data,dict) else []; rec.update(rows=len(rows),complete=True); out={"receipt":rec,"articles":rows}
  except Exception as e: rec["error"]=f"{type(e).__name__}: {e}"; out={"receipt":rec,"articles":[]}
 (OUT/"latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8"); print(f"Event Registry: {rec.get('status')} rows={rec['rows']}")
if __name__=="__main__": main()
