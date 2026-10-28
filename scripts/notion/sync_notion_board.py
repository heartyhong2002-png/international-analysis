"""
sync_notion_board.py
====================
AGENT_SYNC.md의 Active Work Board 테이블을 파싱하여
Notion 프로젝트 허브의 작업 보드(Database)로 실시간 동기화합니다.
만약 Notion에 작업 보드 DB가 없다면 허브 페이지 아래에 자동 생성합니다.
"""

import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 모듈 경로 추가
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from notion_client_base import NotionClient, load_env

AGENT_SYNC_PATH = REPO_ROOT / "AGENT_SYNC.md"
ENV_PATH = REPO_ROOT / ".env"

def parse_agent_sync_board():
    """ AGENT_SYNC.md에서 Active Work Board 표를 파싱 """
    if not AGENT_SYNC_PATH.exists():
        raise FileNotFoundError(f"{AGENT_SYNC_PATH} 파일을 찾을 수 없습니다.")

    with open(AGENT_SYNC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    board_match = re.search(r"## Active Work Board\s*\n.*?\n\|(.*?)\|\s*\n\|[-|\s]+\|\s*\n(.*?)(?=\n\n|\n##|\Z)", content, re.DOTALL)
    if not board_match:
        raise ValueError("AGENT_SYNC.md에서 Active Work Board 테이블을 찾을 수 없습니다.")

    rows_text = board_match.group(2).strip().split("\n")
    tasks = []
    for r in rows_text:
        parts = [p.strip() for p in r.split("|")[1:-1]]
        if len(parts) >= 6:
            status, owner, area, files, task, updated = parts[:6]
            tasks.append({
                "status": status,
                "owner": owner,
                "area": area,
                "files": files,
                "task": task,
                "updated": updated
            })
    return tasks

def save_env_key(key, value):
    """ .env 파일에 새 키/값을 기록하거나 업데이트 """
    lines = []
    found = False
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    os.environ[key] = value

def ensure_database(client, hub_page_id, db_id=None):
    """ 기존 DB 확인 또는 허브 페이지 하위에 자동 생성 """
    clean_hub = client._clean_id(hub_page_id)
    clean_db = client._clean_id(db_id) if db_id else ""

    if clean_db and clean_db != clean_hub:
        try:
            db = client.get_database(clean_db)
            title = db.get('title', [{}])[0].get('plain_text', clean_db) if db.get('title') else clean_db
            print(f"✓ 기존 Notion 작업 보드 확인됨: {title}")
            return clean_db
        except Exception as e:
            print(f"⚠ 기존 DB ID 접근 실패 ({e}), 허브 하위에 새 DB 생성을 시도합니다.")

    if not clean_hub:
        raise ValueError("NOTION_HUB_PAGE_ID가 설정되어 있지 않아 DB를 생성할 수 없습니다.")

    print(f"🚀 Notion 허브({clean_hub}) 아래에 새 'AI 세션 작업 동기화 보드' 데이터베이스를 생성합니다...")
    properties = {
        "Task": {"title": {}},
        "Status": {
            "select": {
                "options": [
                    {"name": "done", "color": "green"},
                    {"name": "in-progress", "color": "blue"},
                    {"name": "open", "color": "gray"},
                    {"name": "review-needed", "color": "yellow"},
                    {"name": "blocked", "color": "red"}
                ]
            }
        },
        "Owner": {"select": {}},
        "Area": {"select": {}},
        "Files": {"rich_text": {}},
        "Last Updated": {"rich_text": {}},
        "Task Key": {"rich_text": {}}
    }
    
    new_db = client.create_database(hub_page_id, "📋 AI 세션 작업 동기화 보드 (Active Work Board)", properties)
    new_db_id = new_db["id"]
    save_env_key("NOTION_BOARD_DATABASE_ID", new_db_id)
    print(f"✓ Notion 작업 보드 DB 생성 완료! ID: {new_db_id}")
    return new_db_id

def sync_board():
    env = load_env()
    client = NotionClient()
    
    ok, msg = client.test_connection()
    if not ok:
        print(f"❌ Notion 연결 실패: {msg}")
        return False

    print(f"🔗 {msg}")
    
    hub_page_id = env.get("NOTION_HUB_PAGE_ID", "3eede224b44181f0bd20ea55620bf5c4")
    board_db_id = env.get("NOTION_BOARD_DATABASE_ID", "")
    
    db_id = ensure_database(client, hub_page_id, board_db_id)
    tasks = parse_agent_sync_board()
    print(f"📖 AGENT_SYNC.md에서 {len(tasks)}개의 작업 항목을 읽었습니다.")

    # 기존 항목 조회
    query_res = client.query_database(db_id)
    existing_items = {}
    for page in query_res.get("results", []):
        props = page.get("properties", {})
        key_prop = props.get("Task Key", {}).get("rich_text", [])
        if key_prop:
            key = key_prop[0].get("plain_text", "")
            existing_items[key] = page["id"]
        else:
            title_prop = props.get("Task", {}).get("title", [])
            if title_prop:
                key = title_prop[0].get("plain_text", "")
                existing_items[key] = page["id"]

    created_count = 0
    updated_count = 0

    for t in tasks:
        task_key = f"{t['owner']}_{t['area']}_{t['task'][:30]}"
        props = {
            "Task": {"title": [{"text": {"content": t["task"]}}]},
            "Status": {"select": {"name": t["status"]}},
            "Owner": {"select": {"name": t["owner"].split("/")[0].strip()}},
            "Area": {"select": {"name": t["area"].split("/")[0].strip()[:50]}},
            "Files": {"rich_text": [{"text": {"content": t["files"][:2000]}}]},
            "Last Updated": {"rich_text": [{"text": {"content": t["updated"]}}]},
            "Task Key": {"rich_text": [{"text": {"content": task_key}}]}
        }

        if task_key in existing_items or t["task"] in existing_items:
            page_id = existing_items.get(task_key) or existing_items.get(t["task"])
            client.update_page(page_id, props)
            updated_count += 1
        else:
            client.create_page({"database_id": client._clean_id(db_id)}, props)
            created_count += 1

    print(f"✅ Notion 동기화 완료! (신규 등록: {created_count}건, 갱신: {updated_count}건)")
    return True

if __name__ == "__main__":
    sync_board()
