"""
db_conn.py — PostgreSQL(Docker pgvector) 우선 / MySQL 폴백 공용 DB 커넥터
==========================================================================

환경변수 `DB_BACKEND`로 백엔드를 선택합니다:
  - `postgres` (기본값): Docker PostgreSQL (`POSTGRES_*`) 연결
  - `mysql`: 로컬 MySQL (`MYSQL_*`) 연결

`UnifiedConnection`은 `conn.cursor(dictionary=True)` 인터페이스를
PostgreSQL(`psycopg.rows.dict_row`)과 MySQL(`mysql.connector`) 양쪽에서
동일하게 제공합니다.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class UnifiedConnection:
    """psycopg / mysql.connector 공통 인터페이스 래퍼."""

    def __init__(self, raw_conn, backend: str):
        self._conn = raw_conn
        self.backend = backend

    @property
    def raw(self):
        return self._conn

    def cursor(self, dictionary: bool = False):
        if self.backend == "postgres":
            if dictionary:
                from psycopg.rows import dict_row
                return self._conn.cursor(row_factory=dict_row)
            return self._conn.cursor()
        return self._conn.cursor(dictionary=dictionary)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_backend() -> str:
    return os.getenv("DB_BACKEND", "postgres").strip().lower()


def _connect_postgres() -> UnifiedConnection:
    import psycopg

    conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "intl_admin"),
        password=os.getenv("POSTGRES_PASSWORD", "intl_pg_password_2026"),
        dbname=os.getenv("POSTGRES_DATABASE", "international_analysis"),
    )
    return UnifiedConnection(conn, "postgres")


def _connect_mysql() -> UnifiedConnection:
    import mysql.connector

    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "international_analysis"),
    )
    return UnifiedConnection(conn, "mysql")


def get_connection(backend: str | None = None, fallback: bool = True) -> UnifiedConnection:
    """공용 DB 연결 반환. 기본값은 PostgreSQL, 실패 시 선택적으로 MySQL 폴백."""
    target = (backend or get_backend()).strip().lower()
    if target == "postgres":
        try:
            return _connect_postgres()
        except Exception as pg_err:
            if not fallback:
                raise
            try:
                return _connect_mysql()
            except Exception:
                raise pg_err
    if target == "mysql":
        return _connect_mysql()
    raise ValueError(f"Unsupported DB_BACKEND: {target!r} (use 'postgres' or 'mysql')")


def read_sql_df(sql: str, conn: UnifiedConnection):
    """psycopg / mysql.connector 어느 쪽이든 pandas 경고 없이 DataFrame 반환."""
    import pandas as pd

    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        if not rows:
            cols = [desc[0] for desc in (cur.description or [])]
            return pd.DataFrame(columns=cols)
        return pd.DataFrame(rows)
    finally:
        cur.close()
