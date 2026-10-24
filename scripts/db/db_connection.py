"""Shared MySQL connection helpers for evidence-layer writers.

Reads MYSQL_* from project-root `.env`. Never logs passwords.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")

# Operational / official queries must exclude synthetic regression fixtures.
TEST_RUN_KEY_PREFIX = "TEST-"
TEST_ISSUE_KEY_PREFIX = "TEST_"
TEST_SCORING_VERSION = "test-fixture-v1"
TEST_FIXTURE_RUN_KEY_PREFIX = "TEST-FIXTURE-"


def get_connection(**kwargs):
    params = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "database": MYSQL_DATABASE,
        "autocommit": False,
    }
    params.update(kwargs)
    return mysql.connector.connect(**params)


def is_test_run_key(run_key: str | None) -> bool:
    return bool(run_key) and str(run_key).startswith(TEST_RUN_KEY_PREFIX)


def is_test_issue_key(issue_key: str | None) -> bool:
    return bool(issue_key) and str(issue_key).startswith(TEST_ISSUE_KEY_PREFIX)


def operational_run_predicate_sql(alias: str = "sr") -> str:
    """SQL fragment: completed non-TEST scoring runs only."""
    return (
        f"{alias}.status = 'completed' "
        f"AND {alias}.run_key NOT LIKE '{TEST_RUN_KEY_PREFIX}%' "
        f"AND {alias}.scoring_version <> '{TEST_SCORING_VERSION}'"
    )
