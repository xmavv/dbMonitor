import os
import re
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
        SELECT queryid, query, calls, mean_exec_time, total_exec_time, rows
        FROM pg_stat_statements
        ORDER BY total_exec_time DESC;
    """)
    return cur.fetchall()


def load_indexes(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            schemaname,
            relname AS table_name,
            indexrelname AS index_name,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
        FROM pg_stat_user_indexes
        ORDER BY idx_scan ASC;
    """)
    return cur.fetchall()


TYPE_DEFAULTS = {
    'integer': '1',
    'bigint': '1',
    'smallint': '1',
    'numeric': '1',
    'real': '1',
    'double precision': '1',
    'text': "''",
    'character varying': "''",
    'varchar': "''",
    'character': "''",
    'char': "''",
    'name': "''",
    'date': "DATE '2000-01-01'",
    'timestamp': "TIMESTAMP '2000-01-01'",
    'timestamp without time zone': "TIMESTAMP '2000-01-01'",
    'timestamp with time zone': "TIMESTAMPTZ '2000-01-01'",
    'timestamptz': "TIMESTAMPTZ '2000-01-01'",
    'time': "TIME '00:00:00'",
    'interval': "INTERVAL '0'",
    'boolean': 'false',
    'bool': 'false',
    'uuid': "'00000000-0000-0000-0000-000000000000'::uuid",
    'bytea': "''::bytea",
    'json': "'{}'::json",
    'jsonb': "'{}'::jsonb",
}


def _dummy_for_type(pg_type):
    return TYPE_DEFAULTS.get(pg_type.lower(), f"NULL::{pg_type}")


def explain_query(conn, query):
    cur = conn.cursor()
    results = {}

    param_numbers = [int(m) for m in re.findall(r'\$(\d+)', query)]
    param_count = max(param_numbers) if param_numbers else 0
    stmt_name = "_dbmonitor_analyze_stmt"

    if param_count > 0:
        try:
            cur.execute(f"DEALLOCATE {stmt_name};")
        except Exception:
            pass
        try:
            cur.execute(f"PREPARE {stmt_name} AS {query};")
        except Exception as e:
            return {"error": str(e)}

        cur.execute(
            "SELECT unnest(parameter_types)::text FROM pg_prepared_statements WHERE name = %s",
            (stmt_name,),
        )
        param_types = [row[0] for row in cur.fetchall()]
        dummies = [_dummy_for_type(t) for t in param_types]
        explain_target = f"EXECUTE {stmt_name}({', '.join(dummies)})"
    else:
        explain_target = query

    try:
        cur.execute(f"EXPLAIN (FORMAT TEXT) {explain_target}")
        results["with_index"] = [row[0] for row in cur.fetchall()]
    except Exception as e:
        if param_count > 0:
            try:
                cur.execute(f"DEALLOCATE {stmt_name};")
            except Exception:
                pass
        return {"error": str(e)}

    try:
        cur.execute("SET enable_indexscan = off;")
        cur.execute("SET enable_bitmapscan = off;")
        cur.execute(f"EXPLAIN (FORMAT TEXT) {explain_target}")
        results["without_index"] = [row[0] for row in cur.fetchall()]
    except Exception as e:
        results["without_index_error"] = str(e)
    finally:
        cur.execute("SET enable_indexscan = on;")
        cur.execute("SET enable_bitmapscan = on;")
        if param_count > 0:
            try:
                cur.execute(f"DEALLOCATE {stmt_name};")
            except Exception:
                pass

    cur.close()
    return results

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