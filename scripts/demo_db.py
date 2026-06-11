"""Shared DB connection helpers for demo scripts."""
import os
import sys

import psycopg2
import psycopg2.extras

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_db_config():
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "database": os.getenv("POSTGRES_DB", "mydb"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


def connect():
    return psycopg2.connect(**get_db_config())


def sql_path(name):
    return os.path.join(SCRIPT_DIR, name)


def run_sql_file(conn, filename):
    path = sql_path(filename)
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    prev = conn.autocommit
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.autocommit = prev


def print_banner(title, lines=None):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    if lines:
        for line in lines:
            print(line)
    print()


def require_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'demo'"
        )
        if cur.fetchone() is None:
            print("ERROR: schema 'demo' not found. Run demo_init.py first.", file=sys.stderr)
            sys.exit(1)
