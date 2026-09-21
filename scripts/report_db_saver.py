"""
report_db_saver.py — 보고서 데스크톱 저장 및 MySQL DB 적재 공통 모듈
=====================================================================

역할:
  1. 생성된 모든 분석 보고서(.md)를 사용자가 요청한 데스크톱 경로
     (C:\\Users\\홍준기\\Desktop\\분석보고서)로 자동 저장
  2. MySQL international_analysis 데이터베이스의 analysis_reports 테이블에
     메타데이터 및 마크다운 전문(LONGTEXT)을 영구 적재
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Windows 콘솔 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 보고서 저장 기본 경로 (프로젝트 폴더 내 분석보고서)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "분석보고서"
DESKTOP_REPORTS_DIR = Path(os.getenv("DESKTOP_REPORTS_DIR", str(DEFAULT_REPORTS_DIR)))

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")


def get_db_connection():
    """MySQL 데이터베이스 연결을 생성하여 반환합니다."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci"
        )
        return conn
    except Exception as e:
        print(f"⚠️  [DB 연결 실패] {e}")
        return None


def ensure_reports_table():
    """analysis_reports 테이블이 없으면 생성합니다."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        create_sql = """
        CREATE TABLE IF NOT EXISTS `analysis_reports` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `report_type` VARCHAR(50) NOT NULL COMMENT '보고서 유형 (e.g. gao_issue_ko, gao_issue_en, daily_signals 등)',
            `title` VARCHAR(255) NOT NULL COMMENT '보고서 제목',
            `issue_key` VARCHAR(100) NOT NULL DEFAULT 'ALL' COMMENT '대상 이슈 (개별 이슈 코드 또는 ALL)',
            `intensity` INT DEFAULT NULL COMMENT '위험도 지수 (0~100)',
            `file_path` VARCHAR(500) NOT NULL COMMENT '저장된 파일 경로',
            `content` LONGTEXT NOT NULL COMMENT '마크다운 전문',
            `collected_date` VARCHAR(20) NOT NULL COMMENT '기준 날짜 (YYYY-MM-DD)',
            `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY `uk_report_type_issue_date` (`report_type`, `issue_key`, `collected_date`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cur.execute(create_sql)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️  [테이블 생성 실패] {e}")
        if conn:
            conn.close()
        return False


def save_report_to_desktop_and_db(
    filename: str,
    title: str,
    content: str,
    report_type: str = "gao_issue_ko",
    issue_key: str = "ALL",
    intensity: int = None,
    collected_date: str = None
) -> dict:
    """
    보고서를 데스크톱 디렉토리에 파일로 저장하고 MySQL DB에 적재합니다.
    """
    if not collected_date:
        collected_date = datetime.now().strftime("%Y-%m-%d")

    # 1. 데스크톱 폴더 확인 및 생성 (텍스트 파일인 경우에만 write, 바이너리 PDF는 건너뜀)
    desktop_file_path = DESKTOP_REPORTS_DIR / filename
    saved_file = str(desktop_file_path)
    try:
        DESKTOP_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        is_binary = filename.lower().endswith(".pdf") or filename.lower().endswith(".docx")
        if not is_binary:
            with open(desktop_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  📁 [데스크톱 저장 완료] {saved_file}")
        else:
            if desktop_file_path.exists():
                print(f"  📁 [데스크톱 바이너리 파일 확인 완료] {saved_file}")
    except Exception as e:
        print(f"  ⚠️ [데스크톱 저장 실패] {e}")
        saved_file = filename

    # 2. MySQL DB 적재
    db_saved = False
    try:
        ensure_reports_table()
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            upsert_sql = """
            REPLACE INTO `analysis_reports` 
            (`report_type`, `title`, `issue_key`, `intensity`, `file_path`, `content`, `collected_date`, `created_at`)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cur.execute(upsert_sql, (
                report_type,
                title,
                issue_key,
                intensity,
                saved_file,
                content,
                collected_date
            ))
            conn.commit()
            cur.close()
            conn.close()
            db_saved = True
            print(f"  💾 [DB 적재 완료] Table: analysis_reports | Type: {report_type} | Issue: {issue_key}")
    except Exception as e:
        print(f"  ⚠️ [DB 적재 실패] {e}")

    return {
        "file_path": saved_file,
        "db_saved": db_saved
    }
