"""
clean_orphan_broken.py — 정상 버전이 아예 없이 깨진 인코딩으로만 남은
gov_announcements 행 정리
================================================================
dedupe_gov_announcements.py는 "같은 link에 정상 버전이 있을 때만" 깨진
행을 지웠습니다. 이 스크립트는 그 나머지 — 애초에 정상 버전이 수집된 적
없이 깨진 채로만 유일하게 존재하는 행 — 을 백업 후 삭제합니다.
(제목이 인코딩 깨짐으로 못 쓰는 상태라 재수집 전에는 복구 불가능합니다.)

사용법:
    python scripts/clean_orphan_broken.py --dry-run
    python scripts/clean_orphan_broken.py
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
BROKEN_RE = re.compile(r"[À-ÿ]{2,}|�")


def is_broken(title):
    return bool(BROKEN_RE.search(title or ""))


def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
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
        WHERE title REGEXP '[À-ÿ]{2,}|�'
    """)
    to_delete = cur.fetchall()

    print(f"인코딩 깨짐 행: {len(to_delete)}건 발견")
    if not to_delete:
        print("✅ 없음 — 정리할 게 없습니다.")
        cur.close()
        conn.close()
        return

    backup_path = os.path.join(
        _SCRIPT_DIR, "..", f"deleted_orphan_broken_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    with open(backup_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(to_delete[0].keys()))
        writer.writeheader()
        writer.writerows(to_delete)
    print(f"📦 백업 저장: {os.path.abspath(backup_path)}")

    for r in to_delete:
        print(f"   id={r['id']:<6} {r['title'][:50]!r}  link={r['link']}")

    if args.dry_run:
        print("\n--dry-run 모드라 삭제하지 않았습니다.")
        cur.close()
        conn.close()
        return

    ids = [r["id"] for r in to_delete]
    format_strings = ",".join(["%s"] * len(ids))
    cur.execute(f"DELETE FROM gov_announcements WHERE id IN ({format_strings})", ids)
    conn.commit()
    print(f"\n✅ {cur.rowcount}행 삭제 완료.")

    cur.execute("SELECT COUNT(*) AS c FROM gov_announcements")
    print(f"   현재 gov_announcements 총 행 수: {cur.fetchone()['c']}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
