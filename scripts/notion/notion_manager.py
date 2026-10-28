"""
notion_manager.py
=================
Notion 연동 종합 관리자 CLI.
- 연결 및 토큰 유효성 점검 (--check)
- AGENT_SYNC.md 작업 보드 동기화 (--sync-board)
- 조기경보 일일 브리프 발행 (--publish-report)
- 전체 동기화 실행 (--all)
"""

import sys
import argparse
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
from sync_notion_board import sync_board
from publish_notion_report import publish_report

def check_connection():
    print("=" * 60)
    print("🔍 Notion 연동 상태 점검")
    print("=" * 60)
    
    env = load_env()
    token = env.get("NOTION_API_KEY", "")
    hub_page_id = env.get("NOTION_HUB_PAGE_ID", "")
    board_db_id = env.get("NOTION_BOARD_DATABASE_ID", "")
    report_page_id = env.get("NOTION_REPORT_PAGE_ID", "")

    print(f"1. NOTION_API_KEY 설정: {'✓ 설정됨 (' + token[:12] + '...)' if token and token != 'YOUR_NOTION_API_KEY_HERE' else '✗ 미설정 또는 기본값'}")
    print(f"2. NOTION_HUB_PAGE_ID: {hub_page_id or '✗ 미설정'}")
    print(f"3. NOTION_BOARD_DATABASE_ID: {board_db_id or '(동기화 실행 시 자동 생성 예정)'}")
    print(f"4. NOTION_REPORT_PAGE_ID: {report_page_id or '(허브 페이지 하위에 자동 생성 예정)'}")
    print("-" * 60)

    client = NotionClient()
    ok, msg = client.test_connection()
    if ok:
        print(f"✅ Notion API 인증 성공: {msg}")
    else:
        print(f"❌ Notion API 인증 실패: {msg}")
        print("\n💡 해결 방법:")
        print("  1. .env 파일에 올바른 NOTION_API_KEY가 입력되었는지 확인하세요.")
        print("  2. Notion Developers에서 만든 내부 통합 토큰(secret_...)인지 확인하세요.")
        return False

    # 허브 페이지 접근 권한 점검
    if hub_page_id:
        try:
            page = client.get_page(hub_page_id)
            title_prop = page.get("properties", {}).get("title", {})
            title_text = "제목 없음"
            if "title" in title_prop and title_prop["title"]:
                title_text = title_prop["title"][0].get("plain_text", "")
            print(f"✅ 허브 페이지 접근 권한 확인: '{title_text}'")
        except Exception as e:
            print(f"⚠️ 허브 페이지({hub_page_id}) 접근 실패: {e}")
            print("  -> 노션 허브 페이지 우측 상단 '...' > '연결(Connect to)'에서 통합을 추가했는지 확인하세요.")

    return True

def main():
    parser = argparse.ArgumentParser(description="Notion 통합 관리 도구 (작업 보드 동기화 & 보고서 발행)")
    parser.add_argument("--check", action="store_true", help="Notion API 토큰 및 연결 상태 점검")
    parser.add_argument("--sync-board", action="store_true", help="AGENT_SYNC.md의 Active Work Board를 Notion으로 동기화")
    parser.add_argument("--publish-report", action="store_true", help="최신 조기경보 브리프를 Notion 페이지로 발행")
    parser.add_argument("--report-file", type=str, default=None, help="발행할 마크다운 파일 경로 (미지정 시 최신 브리프 자동 탐색)")
    parser.add_argument("--all", action="store_true", help="보드 동기화와 보고서 발행을 모두 수행")

    args = parser.parse_args()

    if not any([args.check, args.sync_board, args.publish_report, args.all]):
        parser.print_help()
        sys.exit(0)

    if args.check:
        check_connection()
    elif args.sync_board:
        sync_board()
    elif args.publish_report:
        publish_report(args.report_file)
    elif args.all:
        print("🚀 [1/2] 작업 보드 동기화 시작...")
        sync_board()
        print("\n🚀 [2/2] 조기경보 보고서 발행 시작...")
        publish_report(args.report_file)
        print("\n🎉 모든 Notion 연동 작업 완료!")

if __name__ == "__main__":
    main()
