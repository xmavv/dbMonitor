import os
import psycopg2

def setup_database(conn):
    conn.autocommit = True
    cur = conn.cursor()
    messages = []
    extensions = ["pg_stat_statements", "pg_buffercache"]

    for ext in extensions:
        try:
            cur.execute(f"CREATE EXTENSION IF NOT EXISTS {ext};")
            messages.append(f"{ext} extension OK")
        except Exception as e:
            messages.append(f"Cannot create extension {ext}: {e}")

    try:
        cur.execute(
            "DO $$ BEGIN CREATE USER inspector WITH PASSWORD 'inspector'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
        messages.append("User inspector OK")
    except Exception as e:
        messages.append(f"Cannot create inspector user: {e}")

    # ten user tutaj jest tworzony i nie uzywany w zadnym stopniu
    try:
        cur.execute("ALTER SYSTEM SET logging_collector = on;ALTER SYSTEM SET log_directory = 'log'; ALTER SYSTEM SET log_min_duration_statement = 0;")
        messages.append("Logs altered")
    except Exception as e:
        messages.append(f"Cannot alter logs: {e}")

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

def load_live(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
        datname,
        xact_commit,
        xact_rollback,
        blks_read,
        blks_hit,
        ROUND(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2) AS cache_hit_ratio
        FROM pg_stat_database
        WHERE datname = current_database();
    """)
    return cur.fetchall()

def load_scan(conn):
    cur = conn.cursor()
    cur.execute("""
            SELECT 
        relname,
        seq_scan,
        idx_scan,
        n_live_tup,
        n_dead_tup
        FROM pg_stat_user_tables
        ORDER BY seq_scan DESC;
    """)
    return cur.fetchall()

def load_idx(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
        indexrelname,
        relname,
        idx_scan
        FROM pg_stat_user_indexes
        ORDER BY idx_scan ASC;
    """)
    return cur.fetchall()

def load_statio(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
        relname,
        heap_blks_read,
        heap_blks_hit
        FROM pg_statio_user_tables
        ORDER BY heap_blks_read DESC;
    """)
    return cur.fetchall()

def load_activity(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
        pid,
        usename,
        state,
        query,
        now() - query_start AS duration
        FROM pg_stat_activity
        WHERE state = 'active';
    """)
    return cur.fetchall()

def load_locks(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
        pid,
        locktype,
        relation::regclass,
        mode,
        granted
        FROM pg_locks;
    """)
    return cur.fetchall()

def load_indexes(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
        tablename,
        indexname,
        indexdef
        FROM pg_indexes
        ORDER BY tablename;
    """)
    return cur.fetchall()

def load_extensions(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT extname, extversion
        FROM pg_extension;
    """)
    return cur.fetchall()

def load_cache(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT 
        c.relname,
        count(*) AS buffers
        FROM pg_buffercache b
        JOIN pg_class c ON b.relfilenode = c.relfilenode
        GROUP BY c.relname
        ORDER BY buffers DESC
        LIMIT 10;
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