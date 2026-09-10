"""
build_database.py — 산발적인 CSV/JSON 수집 결과를 MySQL로 통합
================================================================

지금까지 issue_data_collector.py / gov_announcements_collector.py가
쏟아낸 결과물은 각자 다른 폴더에 CSV/JSON으로 흩어져 있습니다:

    data/issues/issues_summary_{date}.csv
    data/issues/{issue}_wikipedia_30days.csv
    data/issues/imf_trade_pairs.csv
    data/issues/fred_indicators_{date}.csv       (v5.3에서 새로 저장되기 시작)
    data/issues/sanctions_{date}.csv             (v5.3에서 새로 저장되기 시작)
    data/gov_announcements/all_announcements_{date}.json

이 스크립트는 이 파일들을 전부 읽어서 정규화된 MySQL 데이터베이스로
합칩니다. 목적은 두 가지:

  1. 흩어진 CSV들을 JOIN/GROUP BY로 바로 질의할 수 있게 만들기
     (포트폴리오에서 "SQL 다룰 줄 안다"를 실제로 보여줄 자료)
  2. 매번 실행마다 덮어써지던 데이터(issues_summary, fred, sanctions는
     날짜별 파일이라 이미 누적되지만, wikipedia/imf_trade는 파일 자체가
     매번 덮어써짐)를 DB에 축적해서, 나중에 "시간에 따른 추세"까지
     분석할 수 있는 기반을 만들기.

설계 원칙:
  - 모든 테이블에 collected_date(그 데이터가 어느 실행에서 왔는지)와
    source_file(어느 파일에서 왔는지)을 남겨서 이력 추적이 가능하게 함.
  - PRIMARY KEY / UNIQUE 제약을 걸고 REPLACE INTO / INSERT IGNORE를 써서,
    이 스크립트를 여러 번 실행해도(=재수집 후 재실행) 중복이 쌓이지 않고
    최신 값으로 안전하게 덮어쓰이도록 함(멱등성).

중복 데이터 자동 정리 (v1.3):
  gov_announcements는 (1) 같은 발표가 여러 source 카테고리에 크로스포스팅
  되거나 (2) 과거 MOFA RSS 인코딩 버그로 제목이 깨진 채 들어오는 두 가지
  이유로 중복이 생길 수 있었습니다. 이제 매 실행마다 자동으로:
    1. dedupe_gov_announcements() — 기존 중복/깨진 행을 감지해서 CSV로
       백업한 뒤 삭제 (정상 버전이 아예 없이 깨진 채로만 남은 행은 유일한
       데이터라 자동 삭제하지 않고 경고만 출력합니다)
    2. ensure_gov_link_unique() — gov_announcements.link에 UNIQUE 제약을
       걸어서, 이후로는 크로스포스팅 중복이 DB 레벨에서 자동 차단되게 함
  더 이상 scripts/check_duplicates.py 등을 손으로 돌릴 필요 없이, 이
  스크립트(=run_pipeline.py) 실행 한 번으로 다 처리됩니다.

준비물 (최초 1회):
    pip install mysql-connector-python python-dotenv

    .env 파일에 아래 항목 추가 (없으면 기본값 사용):
        MYSQL_HOST=localhost
        MYSQL_PORT=3306
        MYSQL_USER=root
        MYSQL_PASSWORD=여기에_비밀번호
        MYSQL_DATABASE=international_analysis   (없으면 자동으로 이 이름으로 생성)

사용법:
    python scripts/build_database.py
"""

import argparse
import csv
import glob
import json
import os
import re
import sys
from datetime import datetime

import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv

load_dotenv()

# NOTE (수정 사항 v1.1 — 작업 디렉터리 문제): issue_data_collector.py /
# gov_announcements_collector.py와 동일하게, 실행 위치에 상관없이 이 스크립트
# 파일 기준(scripts/data/...)으로 고정합니다. 실제로 사용자 환경에서
# "issues_summary 0행, gov_announcements 0건"으로 나온 원인이 바로 이거였습니다
# — 터미널을 프로젝트 루트에서 열었을 때와 scripts 폴더에서 열었을 때
# "data/issues"가 서로 다른 곳을 가리켜서, 실제 수집 데이터(scripts/data/)와
# build_database.py가 찾는 곳(당시 작업 디렉터리 기준)이 어긋났습니다.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ISSUES_DIR = os.path.join(_SCRIPT_DIR, "data", "issues")
GOV_DIR = os.path.join(_SCRIPT_DIR, "data", "gov_announcements")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")

DATE_IN_FILENAME_RE = re.compile(r"(\d{8})")

# (수정 사항 v1.3 — 자동 중복/인코딩 정리) 과거 MOFA EUC-KR 오디코딩 버그처럼
# 제목이 깨진 경우를 잡아내는 패턴. À-ÿ가 2글자 이상 연속되거나 치환문자(�)가
# 있으면 인코딩이 깨진 것으로 간주.
BROKEN_TITLE_RE = re.compile(r"[À-ÿ]{2,}|�")


def is_broken_title(title):
    return bool(BROKEN_TITLE_RE.search(title or ""))


def extract_date_from_filename(path):
    """
    파일명에 박힌 YYYYMMDD를 뽑아서 'YYYY-MM-DD'로 반환.
    날짜가 없는 파일(예: imf_trade_pairs.csv)은 파일의 수정 시각을
    collected_date로 대신 사용합니다 (그래도 "언제 수집된 스냅샷인지"는
    남겨야 하니까).
    """
    m = DATE_IN_FILENAME_RE.search(os.path.basename(path))
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")


def clean(v):
    """
    pandas가 만드는 NaN/NaT나 numpy 스칼라 타입을 MySQL 커넥터가 그대로
    못 받는 경우가 있어서, 파라미터로 넘기기 전에 전부 순수 파이썬
    None/int/float/str로 정리합니다.
    """
    try:
        import pandas as pd
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):  # numpy.int64, numpy.float64 등
        return v.item()
    return v


def ensure_database_exists():
    """
    MYSQL_DATABASE가 없으면 생성합니다. (server에는 접속하되 아직
    database는 선택하지 않은 커넥션을 씀)
    """
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD,
    )
    cur = conn.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    conn.commit()
    cur.close()
    conn.close()


def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )


def create_schema(conn):
    cur = conn.cursor()

    # 컬럼 길이는 utf8mb4(글자당 4바이트) 기준으로 복합 PRIMARY/UNIQUE KEY가
    # InnoDB 인덱스 길이 제한(기본 3072바이트)을 넘지 않도록 여유 있게 잡았습니다.
    statements = [
        """
        CREATE TABLE IF NOT EXISTS issue_summary (
            issue           VARCHAR(100) NOT NULL,
            collected_date  VARCHAR(10)  NOT NULL,
            intensity       DOUBLE,
            article_count   DOUBLE,
            last_updated    VARCHAR(50),
            source_file     VARCHAR(500),
            PRIMARY KEY (issue, collected_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS wikipedia_pageviews (
            issue           VARCHAR(100) NOT NULL,
            keyword         VARCHAR(150) NOT NULL,
            date            VARCHAR(10)  NOT NULL,
            wiki_title      VARCHAR(300),
            article_count   INT,
            collected_date  VARCHAR(10)  NOT NULL,
            source_file     VARCHAR(500),
            PRIMARY KEY (issue, keyword, date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS gov_announcements (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            source          VARCHAR(100) NOT NULL,
            title           VARCHAR(255) NOT NULL,
            link            TEXT,
            pub_date        VARCHAR(60)  NOT NULL,
            description     TEXT,
            collected_date  VARCHAR(10)  NOT NULL,
            source_file     VARCHAR(500),
            UNIQUE KEY uniq_announcement (source, title, pub_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS issue_gov_match (
            announcement_id INT NOT NULL,
            issue           VARCHAR(100) NOT NULL,
            PRIMARY KEY (announcement_id, issue),
            FOREIGN KEY (announcement_id) REFERENCES gov_announcements(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS fred_indicators (
            indicator       VARCHAR(100) NOT NULL,
            date            VARCHAR(10)  NOT NULL,
            value           DOUBLE,
            collected_date  VARCHAR(10)  NOT NULL,
            source_file     VARCHAR(500),
            PRIMARY KEY (indicator, date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS sanctions (
            country         VARCHAR(50) NOT NULL,
            collected_date  VARCHAR(10) NOT NULL,
            iso2            VARCHAR(5),
            count           INT,
            last_update     VARCHAR(50),
            status          VARCHAR(50),
            source_file     VARCHAR(500),
            PRIMARY KEY (country, collected_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS imf_trade (
            pair            VARCHAR(20) NOT NULL,
            year            INT         NOT NULL,
            flow            VARCHAR(20) NOT NULL,
            collected_date  VARCHAR(10) NOT NULL,
            description     VARCHAR(200),
            value_usd       DOUBLE,
            source_file     VARCHAR(500),
            PRIMARY KEY (pair, year, flow, collected_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]
    for stmt in statements:
        cur.execute(stmt)
    conn.commit()
    cur.close()


def load_issue_summary(conn):
    import pandas as pd
    cur = conn.cursor()
    files = sorted(glob.glob(f"{ISSUES_DIR}/issues_summary_*.csv"))
    total = 0
    for path in files:
        collected_date = extract_date_from_filename(path)
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            cur.execute("""
                REPLACE INTO issue_summary
                    (issue, collected_date, intensity, article_count, last_updated, source_file)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (clean(row["issue"]), collected_date, clean(row.get("intensity")),
                  clean(row.get("article_count")), clean(row.get("last_updated")), path))
            total += 1
    conn.commit()
    cur.close()
    print(f"  ✓ issue_summary: {total}행 적재 ({len(files)}개 파일)")


def load_wikipedia_pageviews(conn):
    import pandas as pd
    cur = conn.cursor()
    files = sorted(glob.glob(f"{ISSUES_DIR}/*_wikipedia_30days.csv"))
    total = 0
    for path in files:
        issue_name = os.path.basename(path).replace("_wikipedia_30days.csv", "")
        collected_date = extract_date_from_filename(path)
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            date_val = str(row["date"])
            if len(date_val) == 8 and date_val.isdigit():
                date_val = f"{date_val[:4]}-{date_val[4:6]}-{date_val[6:]}"
            article_count = clean(row.get("article_count"))
            cur.execute("""
                REPLACE INTO wikipedia_pageviews
                    (issue, keyword, date, wiki_title, article_count, collected_date, source_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (issue_name, clean(row["keyword"]), date_val, clean(row.get("wiki_title")),
                  int(article_count) if article_count is not None else None,
                  collected_date, path))
            total += 1
    conn.commit()
    cur.close()
    print(f"  ✓ wikipedia_pageviews: {total}행 적재 ({len(files)}개 이슈 파일)")


def load_gov_announcements(conn):
    cur = conn.cursor()

    # NOTE (수정 사항 v1.2 — issue_gov_match 스테일 데이터 버그): 이 테이블은
    # JSON의 matched_issues를 그대로 옮겨 적은 "파생 데이터"라서, 원본 텍스트가
    # 아니라 매칭 로직(키워드 리스트)이 바뀌면 예전에 잘못 매칭된 행도 같이
    # 지워져야 함. 근데 지금까지는 INSERT IGNORE만 써서, 키워드를 고쳐도(예:
    # Iran_Nuclear에서 bare "iran" 제거) 예전에 이미 들어간 잘못된 매칭 행이
    # 안 지워지고 그대로 남아있었음. issue_gov_match는 gov_announcements를
    # 참조만 하는 쪽이라(다른 테이블이 얘를 참조하지 않음) TRUNCATE해도 안전
    # 하니, 매번 실행할 때마다 완전히 비우고 현재 JSON 기준으로 다시 채움.
    cur.execute("TRUNCATE TABLE issue_gov_match")
    conn.commit()

    files = sorted(glob.glob(f"{GOV_DIR}/all_announcements_*.json"))
    total_items, total_matches = 0, 0
    for path in files:
        collected_date = extract_date_from_filename(path)
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            source = (item.get("source") or "")[:100]
            title = (item.get("title") or "")[:255]
            pub_date = (item.get("pub_date") or "")[:60]

            cur.execute("""
                INSERT IGNORE INTO gov_announcements
                    (source, title, link, pub_date, description, collected_date, source_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (source, title, item.get("link"), pub_date,
                  item.get("description"), collected_date, path))
            total_items += 1

            # NOTE (수정 사항 v1.3): link에 UNIQUE 제약이 걸려 있으면(두 번째
            # 실행부터), 같은 발표가 다른 source 카테고리로 재수집될 때 INSERT
            # IGNORE가 link 충돌로 무시됩니다. 그러면 이 아래 SELECT를
            # source+title+pub_date로 하면(그 source로는 애초에 안 들어갔으니)
            # 못 찾아서 issue_gov_match 매칭을 놓치게 됩니다. link가 있으면
            # link로 먼저 찾고, 없을 때만 기존 방식으로 폴백합니다.
            link_val = item.get("link")
            if link_val:
                cur.execute("SELECT id FROM gov_announcements WHERE link = %s", (link_val,))
            else:
                cur.execute("""
                    SELECT id FROM gov_announcements WHERE source = %s AND title = %s AND pub_date = %s
                """, (source, title, pub_date))
            row = cur.fetchone()
            if not row:
                continue
            announcement_id = row[0]
            for issue in item.get("matched_issues", []):
                cur.execute("""
                    INSERT IGNORE INTO issue_gov_match (announcement_id, issue)
                    VALUES (%s, %s)
                """, (announcement_id, issue))
                total_matches += 1
    conn.commit()
    cur.close()
    print(f"  ✓ gov_announcements: {total_items}건 처리, issue_gov_match {total_matches}건 매칭 "
          f"({len(files)}개 파일)")


def dedupe_gov_announcements(conn):
    """
    (수정 사항 v1.3 — 자동 중복/인코딩 정리) 매 실행마다 gov_announcements를
    자동으로 정리합니다. 예전엔 scripts/check_duplicates.py로 직접 확인하고
    scripts/dedupe_gov_announcements.py / clean_orphan_broken.py를 손으로
    돌려야 했는데, 이제 파이프라인 안에서 매번 자동으로 처리합니다.

    정리 기준 두 가지:
      1. 같은 link(원문 URL)가 여러 source 카테고리에 크로스포스팅되어
         중복 적재된 경우 — id가 가장 작은 1건만 남기고 나머지 삭제.
         (깨진 제목이 섞여 있으면 정상 제목을 우선 남김)
      2. 과거 MOFA 인코딩 버그처럼 제목이 깨진 행 — 같은 link에 정상 버전이
         있으면 깨진 쪽만 삭제.

    정상 버전이 아예 없이 깨진 채로만 유일하게 존재하는 행(orphan)은 그
    자체가 유일한 데이터라서 자동으로 지우지 않고 경고만 출력합니다 —
    재수집 전에는 복구가 안 되니 사람이 보고 판단해야 함.

    삭제 대상은 실행 전에 항상 CSV로 백업합니다.
    """
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
        clean_candidates = [r for r in items if not is_broken_title(r["title"])]
        if not clean_candidates:
            continue  # 전부 깨짐 → orphan 경고 단계에서 별도로 다룸
        keep = min(clean_candidates, key=lambda r: r["id"])
        for r in items:
            if r["id"] != keep["id"]:
                to_delete.append(r)

    if to_delete:
        backup_path = os.path.join(
            _SCRIPT_DIR, "..",
            f"auto_deleted_gov_duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        with open(backup_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(to_delete[0].keys()))
            writer.writeheader()
            writer.writerows(to_delete)
        ids = [r["id"] for r in to_delete]
        format_strings = ",".join(["%s"] * len(ids))
        cur.execute(f"DELETE FROM gov_announcements WHERE id IN ({format_strings})", ids)
        conn.commit()
        print(f"  🧹 자동 정리: 중복/깨진 행 {len(to_delete)}건 삭제 "
              f"(백업: {os.path.basename(backup_path)})")
    else:
        print("  🧹 자동 정리: 삭제할 중복 없음")

    # orphan(정상 버전 없이 깨진 채로만 남은 행) — 삭제하지 않고 경고만
    deleted_ids = {r["id"] for r in to_delete}
    cur.execute("""
        SELECT id, title, link, collected_date FROM gov_announcements
        WHERE title REGEXP '[À-ÿ]{2,}|�'
    """)
    remaining_broken = [r for r in cur.fetchall() if r["id"] not in deleted_ids]
    if remaining_broken:
        ids_preview = ", ".join(str(r["id"]) for r in remaining_broken[:10])
        print(f"  ⚠ 정상 버전 없이 깨진 채로만 남은 행 {len(remaining_broken)}건 발견 — "
              f"유일한 데이터라 자동 삭제하지 않았습니다. id: {ids_preview}"
              f"{' ...' if len(remaining_broken) > 10 else ''}")
        print("     → 재수집으로 정상 버전이 들어오면 다음 실행 때 자동으로 정리됩니다.")

    cur.close()


def ensure_gov_link_unique(conn):
    """
    (수정 사항 v1.3) gov_announcements.link에 UNIQUE 인덱스를 걸어서, 이후로는
    같은 발표가 여러 source 카테고리로 재수집돼도 DB가 스키마 레벨에서 자동
    차단하도록 합니다 (INSERT IGNORE가 알아서 무시함) — 이게 근본 해결책이고,
    dedupe_gov_announcements()는 이미 들어간 과거 데이터를 치우는 사후 처리.

    link가 TEXT 컬럼이라 prefix length가 필요합니다 (768자 = utf8mb4 기준
    InnoDB 인덱스 3072바이트 한도). 기존 중복이 남아있으면 ALTER가 실패하니
    반드시 dedupe_gov_announcements() 다음에 호출해야 합니다.
    이미 제약이 있으면 아무것도 하지 않고 조용히 넘어갑니다.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.statistics
        WHERE table_schema = %s AND table_name = 'gov_announcements' AND index_name = 'uniq_link'
    """, (MYSQL_DATABASE,))
    if cur.fetchone()[0] > 0:
        cur.close()
        return
    try:
        cur.execute("ALTER TABLE gov_announcements ADD UNIQUE KEY uniq_link (link(768))")
        conn.commit()
        print("  🔒 gov_announcements.link에 UNIQUE 제약 추가 완료 "
              "— 앞으로 크로스포스팅 중복은 DB가 자동 차단합니다")
    except mysql.connector.Error as e:
        print(f"  ⚠ link UNIQUE 제약 추가 실패 (중복이 아직 남아있을 수 있음): {e}")
    cur.close()


def load_fred_indicators(conn):
    import pandas as pd
    cur = conn.cursor()
    files = sorted(glob.glob(f"{ISSUES_DIR}/fred_indicators_*.csv"))
    total = 0
    for path in files:
        collected_date = extract_date_from_filename(path)
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            date_val = str(row["date"])[:10]
            cur.execute("""
                REPLACE INTO fred_indicators
                    (indicator, date, value, collected_date, source_file)
                VALUES (%s, %s, %s, %s, %s)
            """, (clean(row["indicator"]), date_val, clean(row.get("value")),
                  collected_date, path))
            total += 1
    conn.commit()
    cur.close()
    print(f"  ✓ fred_indicators: {total}행 적재 ({len(files)}개 파일)")


def load_sanctions(conn):
    import pandas as pd
    cur = conn.cursor()
    files = sorted(glob.glob(f"{ISSUES_DIR}/sanctions_*.csv"))
    total = 0
    for path in files:
        collected_date = extract_date_from_filename(path)
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            count_val = clean(row.get("count"))
            cur.execute("""
                REPLACE INTO sanctions
                    (country, collected_date, iso2, count, last_update, status, source_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (clean(row["country"]), collected_date, clean(row.get("iso2")),
                  int(count_val) if count_val is not None else None,
                  clean(row.get("last_update")), clean(row.get("status")), path))
            total += 1
    conn.commit()
    cur.close()
    print(f"  ✓ sanctions: {total}행 적재 ({len(files)}개 파일)")


def load_imf_trade(conn):
    import pandas as pd
    cur = conn.cursor()
    files = sorted(glob.glob(f"{ISSUES_DIR}/imf_trade_pairs.csv"))
    total = 0
    for path in files:
        collected_date = extract_date_from_filename(path)
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            cur.execute("""
                REPLACE INTO imf_trade
                    (pair, year, flow, collected_date, description, value_usd, source_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (clean(row["pair"]), int(row["year"]), clean(row["flow"]), collected_date,
                  clean(row.get("description")), clean(row.get("value_usd")), path))
            total += 1
    conn.commit()
    cur.close()
    print(f"  ✓ imf_trade: {total}행 적재 ({len(files)}개 파일)")


def print_verification_queries(conn):
    """
    적재가 끝난 뒤, 실제로 JOIN/GROUP BY가 되는지 보여주는 샘플 쿼리 몇 개를
    바로 실행해서 출력합니다 (포트폴리오에서 SQL 스크린샷/설명 자료로 바로
    쓸 수 있게).
    """
    cur = conn.cursor()

    print("\n" + "=" * 60)
    print("📊 검증 쿼리 1: 이슈별 최신 intensity Top 5")
    print("=" * 60)
    cur.execute("""
        SELECT issue, intensity, article_count, collected_date
        FROM issue_summary
        WHERE collected_date = (SELECT MAX(collected_date) FROM issue_summary)
        ORDER BY intensity DESC
        LIMIT 5
    """)
    for row in cur.fetchall():
        print(f"   {row[0]:<30} intensity={row[1]:.1f}  articles={row[2]:.0f}  ({row[3]})")

    print("\n" + "=" * 60)
    print("📊 검증 쿼리 2: 이슈별 정부 발표 매칭 건수 (JOIN)")
    print("=" * 60)
    cur.execute("""
        SELECT m.issue, COUNT(*) AS matched_count
        FROM issue_gov_match m
        JOIN gov_announcements g ON g.id = m.announcement_id
        GROUP BY m.issue
        ORDER BY matched_count DESC
    """)
    rows = cur.fetchall()
    if rows:
        for row in rows:
            print(f"   {row[0]:<30} {row[1]}건")
    else:
        print("   (아직 매칭된 정부 발표 없음 — gov_announcements_collector.py 실행 결과가 필요합니다)")

    print("\n" + "=" * 60)
    print("📊 검증 쿼리 3: intensity와 정부 발표 매칭 건수 비교 (대중 관심 vs 공식 반응)")
    print("=" * 60)
    cur.execute("""
        SELECT s.issue, s.intensity,
               COALESCE(g.matched_count, 0) AS gov_matches
        FROM issue_summary s
        LEFT JOIN (
            SELECT issue, COUNT(*) AS matched_count
            FROM issue_gov_match
            GROUP BY issue
        ) g ON g.issue = s.issue
        WHERE s.collected_date = (SELECT MAX(collected_date) FROM issue_summary)
        ORDER BY s.intensity DESC
        LIMIT 10
    """)
    for row in cur.fetchall():
        gap = "🔴 관심은 높은데 정부 발표 없음" if row[1] and row[1] > 50 and row[2] == 0 else ""
        print(f"   {row[0]:<30} intensity={row[1]:.1f}  gov_matches={row[2]}  {gap}")

    cur.close()


def main():
    parser = argparse.ArgumentParser(description="흩어진 CSV/JSON 수집 결과를 MySQL로 통합")
    parser.parse_args()  # 지금은 옵션 없음 — 접속 정보는 .env에서 읽음

    print("\n" + "=" * 60)
    print("🗄  Building MySQL Database")
    print("=" * 60)
    print(f"접속: {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")

    try:
        ensure_database_exists()
        conn = get_connection()
    except mysql.connector.Error as e:
        if e.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("✗ MySQL 접속 실패: 계정/비밀번호를 확인하세요 (.env의 MYSQL_USER / MYSQL_PASSWORD).")
        else:
            print(f"✗ MySQL 접속 실패: {e}")
        print("  MySQL 서버가 켜져 있는지, .env에 MYSQL_HOST/PORT/USER/PASSWORD가 맞게 있는지 확인해주세요.")
        sys.exit(1)  # NOTE: 그냥 return하면 종료 코드가 0(성공)이 되어서, run_pipeline.py처럼
                     # 이 스크립트를 subprocess로 호출하는 쪽에서 실패를 못 알아챕니다.

    create_schema(conn)

    print("\n[적재 중]")
    load_issue_summary(conn)
    load_wikipedia_pageviews(conn)
    load_gov_announcements(conn)

    print("\n[자동 정리 — 중복/인코딩 깨짐]")
    dedupe_gov_announcements(conn)
    ensure_gov_link_unique(conn)

    load_fred_indicators(conn)
    load_sanctions(conn)
    load_imf_trade(conn)

    print_verification_queries(conn)

    print("\n" + "=" * 60)
    print(f"✅ 완료 — MySQL DB '{MYSQL_DATABASE}'")
    print("   MySQL Workbench, DataGrip, 또는 PyCharm의 Database 도구창으로 연결해서")
    print("   직접 쿼리 날려보세요.")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
