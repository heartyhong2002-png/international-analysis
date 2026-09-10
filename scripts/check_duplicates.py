"""
check_duplicates.py — international_analysis DB의 중복 데이터 점검
================================================================
PRIMARY KEY / UNIQUE 제약이 걸린 컬럼 조합상으로는 중복이 있을 수 없지만,
"같은 실제 항목인데 값이 미묘하게 달라서 다른 행으로 들어간" 논리적 중복이
있는지(특히 gov_announcements - 과거 MOFA 인코딩 버그로 깨진 제목과 정상
제목이 별도 행으로 남아있을 가능성)를 확인합니다.

사용법:
    python scripts/check_duplicates.py
"""
import os
import sys
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")


def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
    )


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    try:
        conn = get_connection()
    except mysql.connector.Error as e:
        print(f"✗ MySQL 접속 실패: {e}")
        sys.exit(1)

    cur = conn.cursor()
    found_any = False

    # 1. 각 테이블의 PRIMARY/UNIQUE KEY 기준 중복 (스키마상 불가능해야 정상)
    pk_checks = {
        "issue_summary": "issue, collected_date",
        "wikipedia_pageviews": "issue, keyword, date",
        "gov_announcements": "source, title, pub_date",
        "issue_gov_match": "announcement_id, issue",
        "fred_indicators": "indicator, date",
        "sanctions": "country, collected_date",
        "imf_trade": "pair, year, flow, collected_date",
    }
    section("1. PRIMARY/UNIQUE KEY 기준 중복 (정상이면 전부 0건이어야 함)")
    for table, keys in pk_checks.items():
        cur.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT {keys} FROM {table} GROUP BY {keys} HAVING COUNT(*) > 1
            ) t
        """)
        cnt = cur.fetchone()[0]
        status = "✓ 중복 없음" if cnt == 0 else f"⚠ {cnt}개 조합 중복!"
        if cnt != 0:
            found_any = True
        print(f"   {table:<25} ({keys}): {status}")

    # 2. gov_announcements: link(URL) 기준 중복 — link는 제약이 없어서
    #    "제목만 미묘하게 다른 같은 발표"를 잡아낼 수 있음
    section("2. gov_announcements — link(원문 URL) 기준 중복 (진짜 중복 발표 의심)")
    cur.execute("""
        SELECT link, COUNT(*) AS cnt, GROUP_CONCAT(title SEPARATOR ' || ') AS titles
        FROM gov_announcements
        WHERE link IS NOT NULL AND link != ''
        GROUP BY link
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    if rows:
        found_any = True
        for link, cnt, titles in rows:
            print(f"   [{cnt}건] {link}")
            print(f"        제목들: {titles[:200]}")
    else:
        print("   ✓ link 기준 중복 없음")

    # 3. gov_announcements: 깨진 한글(인코딩 오류) 의심 행 — MOFA 버그로
    #    EUC-KR을 UTF-8로 잘못 디코딩하면 한글 대신 이런 글자들이 섞여 나옴
    section("3. gov_announcements — 인코딩 깨짐 의심 행 (과거 MOFA EUC-KR 버그)")
    cur.execute("""
        SELECT id, source, title, pub_date, collected_date
        FROM gov_announcements
        WHERE title REGEXP '[À-ÿ]{2,}|�'
        ORDER BY collected_date
        LIMIT 30
    """)
    rows = cur.fetchall()
    if rows:
        found_any = True
        print(f"   ⚠ {len(rows)}건 발견 (최대 30건 표시) — 아래 title이 깨져 보이면 삭제 후보:")
        for r in rows:
            print(f"   id={r[0]:<6} source={r[1]:<15} title={r[2][:50]!r}  collected={r[4]}")
    else:
        print("   ✓ 깨진 인코딩 의심 행 없음")

    # 4. gov_announcements: 같은 title인데 source/pub_date만 다른 경우
    #    (거의 같은 내용이 재수집으로 살짝 다르게 들어갔을 가능성)
    section("4. gov_announcements — title 기준 반복 등장 (참고용, 정상일 수도 있음)")
    cur.execute("""
        SELECT title, COUNT(*) AS cnt, GROUP_CONCAT(DISTINCT source) AS sources,
               GROUP_CONCAT(DISTINCT collected_date) AS dates
        FROM gov_announcements
        GROUP BY title
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 15
    """)
    rows = cur.fetchall()
    if rows:
        for title, cnt, sources, dates in rows:
            print(f"   [{cnt}건] {title[:60]!r}  source={sources}  collected={dates}")
    else:
        print("   ✓ 없음")

    # 5. 전체 행 수 요약
    section("5. 전체 테이블 행 수 요약")
    for table in pk_checks:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"   {table:<25} {cur.fetchone()[0]}행")

    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    if found_any:
        print("⚠ 위에서 중복/이상 데이터가 발견됐습니다. 섹션 2~4를 확인해주세요.")
    else:
        print("✅ 중복 데이터 없음 — DB가 깨끗합니다.")
    print("=" * 70)


if __name__ == "__main__":
    main()
