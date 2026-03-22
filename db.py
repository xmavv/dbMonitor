import os
import psycopg2

def setup_database(conn):
    conn.autocommit = True
    cur = conn.cursor()
    messages = []

    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
        messages.append("pg_stat_statements extension OK")
    except Exception as e:
        messages.append(f"Cannot create extension: {e}")

    try:
        cur.execute("DO $$ BEGIN CREATE USER inspector WITH PASSWORD 'inspector'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
        messages.append("User inspector OK")
    except Exception as e:
        messages.append(f"Cannot create inspector user: {e}")

    try:
        cur.execute("GRANT pg_read_all_stats TO inspector;")
        messages.append("Granted pg_read_all_stats")
    except Exception as e:
        messages.append(f"Cannot grant stats permission: {e}")

    cur.close()
    return messages

def load_stats(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT query, calls, mean_exec_time, total_exec_time, rows
        FROM pg_stat_statements
        ORDER BY total_exec_time DESC;
    """)
    return cur.fetchall()

def get_db_url(cli_db_url=None):
    if cli_db_url:
        return cli_db_url

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB")

    if user and password and db:
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    return None


def connect(db_url):
    return psycopg2.connect(db_url)