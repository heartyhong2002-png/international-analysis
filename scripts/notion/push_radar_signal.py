"""
push_radar_signal.py
====================
무인 글로벌 이상 징후 스캐너(auto_anomaly_scanner.py)가 포착한
비정상 이상 신호(Anomaly Spike)를 Notion 실시간 레이더 데이터베이스에 전송하는 모듈.
"""

import sys
import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from notion_client_base import NotionClient, load_env

def send_radar_alert(
    title: str,
    anomaly_score: str,
    risk_level: str = "WARNING",
    axis: str = "중동 에너지·해운",
    impact_items: list = None,
    evidence: str = "",
    status: str = "자동 탐지됨"
):
    env = load_env()
    client = NotionClient()
    radar_id = client._clean_id(env.get("NOTION_RADAR_PAGE_ID", ""))
    
    if not radar_id:
        print("❌ NOTION_RADAR_PAGE_ID가 .env에 설정되지 않았습니다.")
        return None
        
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d")
    impact_list = [{"name": item} for item in (impact_items or ["원유/LNG"])]
    
    card_payload = {
        "parent": {"database_id": radar_id},
        "properties": {
            "이름": {"title": [{"text": {"content": title}}]},
            "Anomaly Score": {"rich_text": [{"text": {"content": str(anomaly_score)}}]},
            "Risk Level": {"select": {"name": risk_level}},
            "Surveillance Axis": {"select": {"name": axis}},
            "Supply Chain Impact": {"multi_select": impact_list},
            "Detected At": {"date": {"start": now_iso}},
            "Status": {"select": {"name": status}},
            "Key Evidence": {"rich_text": [{"text": {"content": evidence[:2000]}}]}
        }
    }
    
    try:
        res = client.request("POST", "pages", card_payload)
        url = res.get("url", f"https://notion.so/{res.get('id', '').replace('-', '')}")
        print(f"✅ Notion 레이더 경보 등록 완료: {title}")
        print(f"🔗 페이지 URL: {url}")
        return url
    except Exception as e:
        print(f"❌ Notion 레이더 전송 실패: {e}")
        return None

if __name__ == "__main__":
    # CLI 테스트 실행용
    send_radar_alert(
        title="🚨 [대만해협] 인민해방군 동부전구 해협 침범 빈도 급증",
        anomaly_score="Z-Score 3.15 (평소 대비 280% 상승)",
        risk_level="WARNING",
        axis="동아시아 군사·기술",
        impact_items=["반도체", "해상운임"],
        evidence="대만 국방부 항적 발표 + PTT 검색 트렌드 급등 + GDELT 대만해협 갈등 점수 악화"
    )
