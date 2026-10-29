"""
notion_client_base.py
=====================
외부 라이브러리 설치 의존성 없이 표준 라이브러리(urllib) 및 requests를 활용하여
Notion API v1과 통신하는 기본 클라이언트 모듈.
"""

import os
import re
import json
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def load_env():
    """ .env 파일에서 환경변수를 로드합니다. """
    env_file = REPO_ROOT / ".env"
    env_vars = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    env_vars[k] = v
                    if k not in os.environ:
                        os.environ[k] = v
    return env_vars

class NotionClient:
    API_BASE = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def __init__(self, token=None):
        env_vars = load_env()
        self.token = token or os.environ.get("NOTION_API_KEY", "")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION
        }

    def _clean_id(self, raw_id):
        """ URL 또는 32자리/UUID 포맷에서 32자리 hex를 추출하여 Notion UUID 포맷(8-4-4-4-12)으로 변환 """
        if not raw_id:
            return ""
        raw_id = raw_id.strip()
        # 1) 하이픈 포함 UUID 매칭
        uuid_match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", raw_id)
        if uuid_match:
            return uuid_match.group(1).lower()
        # 2) 32자리 연속 hex 매칭 (URL 경로 등)
        hex_match = re.search(r"([0-9a-fA-F]{32})", raw_id)
        if hex_match:
            h = hex_match.group(1).lower()
            return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
        return raw_id

    def request(self, method, endpoint, payload=None):
        url = f"{self.API_BASE}/{endpoint.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                res_body = resp.read().decode("utf-8")
                return json.loads(res_body) if res_body else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_body)
                msg = err_json.get("message", err_body)
            except Exception:
                msg = err_body
            raise RuntimeError(f"Notion API Error [{e.code}]: {msg}")
        except Exception as e:
            raise RuntimeError(f"Notion Connection Error: {e}")

    def test_connection(self):
        """ API 키 및 봇 인증 유효성 확인 """
        if not self.token or self.token == "YOUR_NOTION_API_KEY_HERE":
            return False, "NOTION_API_KEY가 .env에 설정되지 않았습니다."
        try:
            res = self.request("GET", "users/me")
            bot_name = res.get("name", "Unknown Bot")
            return True, f"성공! 연결된 봇 이름: {bot_name} (ID: {res.get('id')})"
        except Exception as e:
            return False, str(e)

    def get_page(self, page_id):
        clean_id = self._clean_id(page_id)
        return self.request("GET", f"pages/{clean_id}")

    def get_database(self, database_id):
        clean_id = self._clean_id(database_id)
        return self.request("GET", f"databases/{clean_id}")

    def query_database(self, database_id, filter_obj=None, sorts=None):
        clean_id = self._clean_id(database_id)
        payload = {}
        if filter_obj:
            payload["filter"] = filter_obj
        if sorts:
            payload["sorts"] = sorts
        return self.request("POST", f"databases/{clean_id}/query", payload)

    def create_page(self, parent, properties, children=None):
        payload = {
            "parent": parent,
            "properties": properties
        }
        if children:
            payload["children"] = children
        return self.request("POST", "pages", payload)

    def update_page(self, page_id, properties):
        clean_id = self._clean_id(page_id)
        return self.request("PATCH", f"pages/{clean_id}", {"properties": properties})

    def get_block_children(self, block_id):
        clean_id = self._clean_id(block_id)
        return self.request("GET", f"blocks/{clean_id}/children")

    def append_children(self, block_id, children):
        clean_id = self._clean_id(block_id)
        return self.request("PATCH", f"blocks/{clean_id}/children", {"children": children})

    def create_database(self, parent_page_id, title, properties):
        clean_id = self._clean_id(parent_page_id)
        payload = {
            "parent": {"type": "page_id", "page_id": clean_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties
        }
        return self.request("POST", "databases", payload)
