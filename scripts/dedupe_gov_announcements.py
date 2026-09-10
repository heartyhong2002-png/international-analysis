"""
dedupe_gov_announcements.py — gov_announcements 테이블 link 기준 중복 정리
================================================================
정리 대상 두 가지:
  1. MOFA 인코딩 버그로 깨진 한글 제목 행 — 같은 link에 정상 버전이 있으면
     깨진 쪽을 삭제
  2. US State Dept 등 크로스포스팅 — 같은 link가 여러 카테고리(source)에
     중복 게시된 경우, link당 1건만 남기고 나머지 삭제

각 link 그룹에서 남길 행을 고르는 규칙:
  - 깨진 인코딩(REGEXP '[À-ÿ]{2,}|�')이 아닌 행을 우선 후보로 삼음
  - 후보가 여러 개면(크로스포스팅) id가 가장 작은 것을 남김
  - 후보가 하나도 없으면(전부 깨진 경우) 그래도 id가 가장 작은 것을 남김
    (데이터가 완전히 사라지지 않도록)

issue_gov_match는 gov_announcements.id를 FOREIGN KEY ... ON DELETE CASCADE로
참조하고 있으므로, 삭제되는 announcement에 딸린 매칭 행도 자동으로 같이
정리됩니다.

삭제 전 삭제 대상 전체를 CSV로 백업합니다 (프로젝트에 이미 있던
deleted_broken_announcements_backup.csv와 같은 패턴).

사용법:
    python scripts/dedupe_gov_announcements.py --dry-run   # 먼저 확인만
    python scripts/dedupe_gov_announcements.py             # 실제로 삭제
"""
import argparse
import csv
import os
import re
import sys
from datetime import datetime

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BROKEN_RE = re.compile(r"[À-ÿ]{2,}|�")  # À-ÿ 2글자 이상, 또는 �


def is_broken(title):
    return bool(BROKEN_RE.search(title or ""))


def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="삭제 없이 대상만 확인")
    args = parser.parse_args()

    try:
        conn = get_connection()
    except mysql.connector.Error as e:
        print(f"✗ MySQL 접속 실패: {e}")
        sys.exit(1)

    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT id, source, title, link, pub_date, description, collected_date, source_file
        FROM gov_announcements
        WHERE link IS NOT NULL AND link != ''
        ORDER BY link, id
    """)
    rows = cur.fetchall()

    groups = {}
    for r in rows:
        groups.setdefault(r["link"], []).append(r)

    to_delete = []
    for link, items in groups.items():
        if len(items) < 2:
            continue
        clean_candidates = [r for r in items if not is_broken(r["title"])]
        keep_pool = clean_candidates if clean_candidates else items
        keep = min(keep_pool, key=lambda r: r["id"])
        for r in items:
            if r["id"] != keep["id"]:
                to_delete.append(r)

    print(f"전체 gov_announcements(link 있는 것): {len(rows)}행")
    print(f"link 기준 중복 그룹: {sum(1 for v in groups.values() if len(v) > 1)}개")
    print(f"삭제 대상: {len(to_delete)}행\n")

    if not to_delete:
        print("✅ 삭제할 중복 없음.")
        cur.close()
        conn.close()
        return

    backup_path = os.path.join(
        _SCRIPT_DIR, "..", f"deleted_gov_announcements_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    with open(backup_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(to_delete[0].keys()))
        writer.writeheader()
        writer.writerows(to_delete)
    print(f"📦 삭제 대상 백업 저장: {os.path.abspath(backup_path)}")

    print("\n삭제될 행 미리보기 (최대 20건):")
    for r in to_delete[:20]:
        title_preview = (r["title"] or "")[:50]
        flag = "🔴 깨진 인코딩" if is_broken(r["title"]) else "🔵 크로스포스팅 중복"
        print(f"   id={r['id']:<6} {flag}  {title_preview!r}")
    if len(to_delete) > 20:
        print(f"   ... 외 {len(to_delete) - 20}건 (백업 CSV에서 전체 확인 가능)")

    if args.dry_run:
        print("\n--dry-run 모드라 실제로 삭제하지 않았습니다. "
              "결과가 맞으면 --dry-run 없이 다시 실행하세요.")
        cur.close()
        conn.close()
        return

    ids_to_delete = [r["id"] for r in to_delete]
    format_strings = ",".join(["%s"] * len(ids_to_delete))
    cur.execute(f"DELETE FROM gov_announcements WHERE id IN ({format_strings})", ids_to_delete)
    conn.commit()
    print(f"\n✅ {cur.rowcount}행 삭제 완료 (issue_gov_match의 딸린 매칭 행도 CASCADE로 함께 정리됨).")

    cur.execute("SELECT COUNT(*) AS c FROM gov_announcements")
    print(f"   현재 gov_announcements 총 행 수: {cur.fetchone()['c']}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
