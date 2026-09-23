"""
데이터베이스 연결 테스트 스크립트
"""
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")

print("=" * 60)
print("MySQL 데이터베이스 연결 테스트")
print("=" * 60)
print(f"호스트: {MYSQL_HOST}:{MYSQL_PORT}")
print(f"사용자: {MYSQL_USER}")
print(f"데이터베이스: {MYSQL_DATABASE}")
print("=" * 60)

try:
    # 먼저 데이터베이스가 있는지 확인하고 없으면 생성
    print("\n1. MySQL 서버에 연결 시도...")
    conn = mysql.connector.connect(
        host=MYSQL_HOST, 
        port=MYSQL_PORT, 
        user=MYSQL_USER, 
        password=MYSQL_PASSWORD
    )
    print("   ✅ MySQL 서버 연결 성공")
    
    cur = conn.cursor()
    
    # 데이터베이스 존재 여부 확인
    cur.execute(f"SHOW DATABASES LIKE '{MYSQL_DATABASE}'")
    db_exists = cur.fetchone()
    
    if not db_exists:
        print(f"\n2. 데이터베이스 '{MYSQL_DATABASE}' 없음 - 생성 중...")
        cur.execute(
            f"CREATE DATABASE `{MYSQL_DATABASE}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        print(f"   ✅ 데이터베이스 '{MYSQL_DATABASE}' 생성 완료")
    else:
        print(f"\n2. 데이터베이스 '{MYSQL_DATABASE}' 존재 확인")
    
    cur.close()
    conn.close()
    
    # 이제 특정 데이터베이스에 연결
    print(f"\n3. 데이터베이스 '{MYSQL_DATABASE}'에 연결 시도...")
    conn = mysql.connector.connect(
        host=MYSQL_HOST, 
        port=MYSQL_PORT, 
        user=MYSQL_USER, 
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    print("   ✅ 데이터베이스 연결 성공")
    
    cur = conn.cursor()
    
    # 테이블 목록 확인
    print("\n4. 기존 테이블 확인...")
    cur.execute("SHOW TABLES")
    tables = cur.fetchall()
    if tables:
        print(f"   기존 테이블 {len(tables)}개 발견:")
        for table in tables:
            print(f"   - {table[0]}")
    else:
        print("   테이블 없음 (최초 실행)")
    
    # 뷰 목록 확인
    print("\n5. 기존 뷰(View) 확인...")
    cur.execute("SHOW FULL TABLES WHERE TABLE_TYPE LIKE 'VIEW'")
    views = cur.fetchall()
    if views:
        print(f"   기존 뷰 {len(views)}개 발견:")
        for view in views:
            print(f"   - {view[0]}")
    else:
        print("   뷰 없음")
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 모든 연결 테스트 통과")
    print("=" * 60)
    
except mysql.connector.Error as e:
    print("\n" + "=" * 60)
    print("❌ 연결 실패")
    print("=" * 60)
    if e.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("오류: 계정 또는 비밀번호가 올바르지 않습니다")
        print(f"현재 설정: 사용자='{MYSQL_USER}', 비밀번호={'*' * len(MYSQL_PASSWORD) if MYSQL_PASSWORD else '(비어있음)'}")
    elif e.errno == errorcode.ER_BAD_DB_ERROR:
        print(f"오류: 데이터베이스 '{MYSQL_DATABASE}'가 존재하지 않습니다")
    else:
        print(f"오류: {e}")
    print("\n해결 방법:")
    print("1. MySQL 서버가 실행 중인지 확인")
    print("2. .env 파일의 MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD 확인")
    print("3. MySQL 계정 권한 확인")
    print("=" * 60)
    exit(1)
