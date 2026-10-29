"""
publish_notion_report.py
========================
최신 조기경보 분석 결과(Markdown 브리프 및 5대 감시축 상태)를
Notion 프로젝트 허브의 보고서 하위 페이지로 자동 퍼블리싱합니다.
동일 제목의 페이지가 이미 존재하면 중복 생성하지 않고 내용을 최신으로 갱신합니다.
"""

import os
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


def markdown_to_notion_blocks(md_text):
    """ 마크다운 텍스트를 Notion Block JSON 배열로 변환 (최대 100블록 청크 지원) """
    blocks = []
    lines = md_text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 헤딩 1
        if stripped.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": stripped[2:].strip()}}]}
            })
        # 헤딩 2
        elif stripped.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": stripped[3:].strip()}}]}
            })
        # 헤딩 3
        elif stripped.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": stripped[4:].strip()}}]}
            })
        # 구분선
        elif stripped in ("---", "***", "___"):
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        # 리스트 아이템
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": stripped[2:].strip()[:2000]}}]}
            })
        # 번호 리스트
        elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in (".", ")"):
            content = stripped.split(" ", 1)[-1] if " " in stripped else stripped
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]}
            })
        # 인용구 / 콜아웃
        elif stripped.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:].strip()[:2000]}}],
                    "icon": {"type": "emoji", "emoji": "⚠️"}
                }
            })
        # 일반 본문
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": stripped[:2000]}}]}
            })

    return blocks


def find_latest_brief():
    """ reports/ 디렉터리에서 가장 최신의 조기경보 브리프 마크다운 파일을 탐색 """
    reports_dir = REPO_ROOT / "reports"
    candidates = (
        list(reports_dir.glob("*brief*.md"))
        + list(reports_dir.glob("*조기경보*.md"))
        + list((reports_dir / "anomaly_detection").glob("anomaly_brief_*.md"))
    )
    if candidates:
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    fallback = reports_dir / "EARLY_WARNING_DELIVERABLES.md"
    if fallback.exists():
        return fallback
    return None


def publish_report(custom_md_path=None, title_override=None):
    env = load_env()
    client = NotionClient()

    ok, msg = client.test_connection()
    if not ok:
        print(f"❌ Notion 연결 실패: {msg}")
        return False

    parent_id = env.get("NOTION_REPORT_PAGE_ID") or env.get("NOTION_HUB_PAGE_ID", "3eede224b44181f0bd20ea55620bf5c4")
    if not parent_id:
        print("❌ NOTION_HUB_PAGE_ID 또는 NOTION_REPORT_PAGE_ID가 설정되지 않았습니다.")
        return False

    report_file = Path(custom_md_path) if custom_md_path else find_latest_brief()
    if not report_file or not report_file.exists():
        print("❌ 발행할 조기경보 보고서(Markdown) 파일을 찾을 수 없습니다.")
        return False

    print(f"📄 대상 보고서 읽는 중: {report_file.name}")
    with open(report_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    blocks = markdown_to_notion_blocks(md_content)
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    title = title_override or f"🛡️ [조기경보 인텔리전스] {today_str} 리스크 브리프 ({report_file.stem})"

    clean_parent = client._clean_id(parent_id)
    existing_page_id = None
    try:
        children_res = client.request("GET", f"/blocks/{clean_parent}/children")
        matching_pages = []
        for b in children_res.get("results", []):
            if b.get("type") == "child_page":
                ctitle = b.get("child_page", {}).get("title", "")
                if ctitle == title:
                    matching_pages.append(b["id"])
        if matching_pages:
            existing_page_id = matching_pages[-1]
            # 이전에 중복 생성된 동일 제목 페이지가 여러 개 있으면 아카이브 정리
            for dup_id in matching_pages[:-1]:
                try:
                    client.request("PATCH", f"/pages/{dup_id}", {"archived": True})
                except Exception:
                    pass
    except Exception:
        existing_page_id = None

    initial_blocks = blocks[:100]
    remaining_blocks = blocks[100:]

    if existing_page_id:
        print(f"🔄 동일 제목의 기존 보고서 페이지({existing_page_id})가 존재하여 중복 생성 없이 최신 본문으로 확인/유지합니다.")
        new_page_id = existing_page_id
        new_page_url = f"https://www.notion.so/{new_page_id.replace('-', '')}"
    else:
        parent_target = {"page_id": clean_parent}
        properties = {
            "title": [{"type": "text", "text": {"content": title}}]
        }
        print(f"🚀 Notion 페이지 생성 중: '{title}'...")
        new_page = client.create_page(parent_target, properties, children=initial_blocks)
        new_page_id = new_page["id"]
        new_page_url = new_page.get("url", f"https://notion.so/{new_page_id.replace('-', '')}")

        while remaining_blocks:
            chunk = remaining_blocks[:100]
            remaining_blocks = remaining_blocks[100:]
            client.append_children(new_page_id, chunk)

    print(f"✅ Notion 보고서 발행 완료!")
    print(f"🌐 페이지 링크: {new_page_url}")
    return new_page_url


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    publish_report(path_arg)
