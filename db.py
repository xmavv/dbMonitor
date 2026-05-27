import os
import re
import psycopg2
import psycopg2.extras


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
        ORDER BY total_exec_time DESC
        LIMIT 50;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


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
            pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
            pg_relation_size(indexrelid) AS index_size_bytes
        FROM pg_stat_user_indexes
        ORDER BY idx_scan ASC;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def load_duplicate_indexes(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            indrelid::regclass AS table_name,
            array_agg(indexrelid::regclass::text ORDER BY indexrelid::regclass::text) AS indexes,
            array_agg(pg_size_pretty(pg_relation_size(indexrelid)) ORDER BY indexrelid::regclass::text) AS sizes,
            pg_get_expr(indexprs, indrelid) AS expressions,
            array_agg(pg_relation_size(indexrelid)) AS size_bytes
        FROM pg_index
        GROUP BY indrelid, indkey, indexprs, indpred
        HAVING count(*) > 1
        ORDER BY table_name;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def load_table_health(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            schemaname,
            relname AS table_name,
            n_live_tup,
            n_dead_tup,
            CASE WHEN n_live_tup > 0
                THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 2)
                ELSE 0
            END AS dead_ratio_pct,
            seq_scan,
            idx_scan,
            CASE WHEN (seq_scan + idx_scan) > 0
                THEN round(100.0 * idx_scan / (seq_scan + idx_scan), 2)
                ELSE 0
            END AS idx_ratio_pct,
            n_tup_ins,
            n_tup_upd,
            n_tup_del,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS total_size,
            pg_total_relation_size(schemaname||'.'||relname) AS total_size_bytes
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def load_cache_hit(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            relname AS table_name,
            heap_blks_read,
            heap_blks_hit,
            CASE WHEN (heap_blks_hit + heap_blks_read) > 0
                THEN round(100.0 * heap_blks_hit / (heap_blks_hit + heap_blks_read), 2)
                ELSE NULL
            END AS cache_hit_pct,
            idx_blks_read,
            idx_blks_hit,
            CASE WHEN (idx_blks_hit + idx_blks_read) > 0
                THEN round(100.0 * idx_blks_hit / (idx_blks_hit + idx_blks_read), 2)
                ELSE NULL
            END AS idx_cache_hit_pct
        FROM pg_statio_user_tables
        WHERE (heap_blks_hit + heap_blks_read) > 0
        ORDER BY heap_blks_read DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def load_locks(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            bl.pid AS blocked_pid,
            ba.usename AS blocked_user,
            ba.query AS blocked_query,
            ba.query_start AS blocked_query_start,
            kl.pid AS blocking_pid,
            ka.usename AS blocking_user,
            ka.query AS blocking_query,
            ka.query_start AS blocking_query_start,
            bl.locktype,
            bl.relation::regclass AS relation,
            extract(epoch FROM (now() - ba.query_start))::int AS wait_seconds
        FROM pg_catalog.pg_locks bl
        JOIN pg_catalog.pg_stat_activity ba ON bl.pid = ba.pid
        JOIN pg_catalog.pg_locks kl ON kl.transactionid = bl.transactionid AND kl.pid != bl.pid
        JOIN pg_catalog.pg_stat_activity ka ON kl.pid = ka.pid
        WHERE NOT bl.granted
        ORDER BY wait_seconds DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows

def load_triggers(conn):
    cur = conn.cursor()
    cur.execute("""
                SELECT
                    nsp.nspname AS schema_name,
                    rel.relname AS table_name,
                    tg.tgname AS trigger_name,
                    CASE
                        WHEN tg.tgenabled = 'O' THEN 'ENABLED'
                        WHEN tg.tgenabled = 'D' THEN 'DISABLED'
                        WHEN tg.tgenabled = 'R' THEN 'REPLICA'
                        WHEN tg.tgenabled = 'A' THEN 'ALWAYS'
                        END AS status,
                    pg_get_triggerdef(tg.oid) AS definition
                FROM pg_trigger tg
                         JOIN pg_class rel ON tg.tgrelid = rel.oid
                         JOIN pg_namespace nsp ON rel.relnamespace = nsp.oid
                WHERE NOT tg.tgisinternal
                ORDER BY schema_name, table_name, trigger_name;
                """)
    rows = cur.fetchall()
    cur.close()
    return rows

def load_active_queries(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            pid,
            usename,
            application_name,
            state,
            wait_event_type,
            wait_event,
            query,
            query_start,
            extract(epoch FROM (now() - query_start))::int AS duration_seconds,
            client_addr
        FROM pg_stat_activity
        WHERE state != 'idle'
          AND pid != pg_backend_pid()
        ORDER BY query_start ASC;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def load_database_sizes(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            schemaname,
            relname AS table_name,
            pg_size_pretty(pg_relation_size(schemaname||'.'||relname)) AS table_size,
            pg_relation_size(schemaname||'.'||relname) AS table_size_bytes,
            pg_size_pretty(pg_indexes_size(schemaname||'.'||relname)) AS indexes_size,
            pg_indexes_size(schemaname||'.'||relname) AS indexes_size_bytes,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS total_size,
            pg_total_relation_size(schemaname||'.'||relname) AS total_size_bytes,
            CASE WHEN pg_relation_size(schemaname||'.'||relname) > 0
                THEN round(100.0 * pg_indexes_size(schemaname||'.'||relname) / pg_total_relation_size(schemaname||'.'||relname), 1)
                ELSE 0
            END AS index_overhead_pct
        FROM pg_stat_user_tables
        ORDER BY total_size_bytes DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


TYPE_DEFAULTS = {
    'integer': '1', 'bigint': '1', 'smallint': '1', 'numeric': '1',
    'real': '1', 'double precision': '1', 'text': "''",
    'character varying': "''", 'varchar': "''", 'character': "''",
    'char': "''", 'name': "''", 'date': "DATE '2000-01-01'",
    'timestamp': "TIMESTAMP '2000-01-01'",
    'timestamp without time zone': "TIMESTAMP '2000-01-01'",
    'timestamp with time zone': "TIMESTAMPTZ '2000-01-01'",
    'timestamptz': "TIMESTAMPTZ '2000-01-01'", 'time': "TIME '00:00:00'",
    'interval': "INTERVAL '0'", 'boolean': 'false', 'bool': 'false',
    'uuid': "'00000000-0000-0000-0000-000000000000'::uuid",
    'bytea': "''::bytea", 'json': "'{}'::json", 'jsonb': "'{}'::jsonb",
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
            conn.rollback()
        try:
            cur.execute(f"PREPARE {stmt_name} AS {query};")
        except Exception as e:
            cur.close()
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
        cur.execute(f"EXPLAIN (FORMAT JSON, ANALYZE false) {explain_target}")
        json_plan = cur.fetchone()[0]
        results["plan_json"] = json_plan
    except Exception as e:
        results["plan_json"] = None

    try:
        cur.execute(f"EXPLAIN (FORMAT TEXT) {explain_target}")
        results["with_index"] = [row[0] for row in cur.fetchall()]
    except Exception as e:
        if param_count > 0:
            try:
                cur.execute(f"DEALLOCATE {stmt_name};")
            except Exception:
                conn.rollback()
        cur.close()
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
                conn.rollback()

    cur.close()
    return results
