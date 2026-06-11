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
    for ext in ("pg_stat_statements", "pg_buffercache"):
        try:
            cur.execute(f"CREATE EXTENSION IF NOT EXISTS {ext};")
            messages.append(f"{ext} extension OK")
        except Exception as e:
            messages.append(f"Cannot create extension {ext}: {e}")
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
            ba.pid AS blocked_pid,
            ba.usename AS blocked_user,
            ba.query AS blocked_query,
            ba.query_start AS blocked_query_start,
            ka.pid AS blocking_pid,
            ka.usename AS blocking_user,
            ka.query AS blocking_query,
            ka.query_start AS blocking_query_start,
            bl.locktype,
            bl.relation::regclass AS relation,
            extract(epoch FROM (now() - ba.query_start))::int AS wait_seconds
        FROM pg_catalog.pg_locks bl
        JOIN pg_catalog.pg_stat_activity ba ON bl.pid = ba.pid
        JOIN pg_catalog.pg_stat_activity ka ON ka.pid = ANY(pg_blocking_pids(ba.pid))
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

def load_extensions(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            e.extname,
            e.extversion,
            n.nspname AS schema_name
        FROM pg_extension e
        JOIN pg_namespace n ON e.extnamespace = n.oid
        ORDER BY e.extname;
    """)
    rows = cur.fetchall()
    cur.close()
    return rows

def load_buffercache(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            c.relname AS table_name,
            count(*) AS buffers,
            pg_size_pretty(count(*) * 8192) AS cached_size,
            round(100.0 * count(*) / NULLIF((SELECT setting::bigint FROM pg_settings WHERE name = 'shared_buffers'), 0), 2) AS pct_of_cache
        FROM pg_buffercache b
        JOIN pg_class c ON b.relfilenode = pg_relation_filenode(c.oid)
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        GROUP BY c.relname
        ORDER BY buffers DESC
        LIMIT 20;
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


def collect_anomaly_events(conn, thresholds=None):
    thresholds = thresholds or {}
    long_query_seconds = int(thresholds.get("long_query_seconds", 30))
    lock_wait_seconds = int(thresholds.get("lock_wait_seconds", 5))
    dead_tuple_ratio_pct = float(thresholds.get("dead_tuple_ratio_pct", 20))
    min_dead_tuples = int(thresholds.get("min_dead_tuples", 100))
    low_cache_hit_pct = float(thresholds.get("low_cache_hit_pct", 90))
    min_cache_reads = int(thresholds.get("min_cache_reads", 100))
    unused_index_min_bytes = int(thresholds.get("unused_index_min_bytes", 10 * 1024 * 1024))
    high_index_overhead_pct = float(thresholds.get("high_index_overhead_pct", 50))

    events = []

    for row in load_locks(conn):
        print(f"Processing time : {row[10]}")
        if row[10] >= lock_wait_seconds:
            events.append({
                "type": "blocked_query",
                "severity": "critical" if row[10] >= 5 else "warning",
                "message": f"Query PID {row[0]} is blocked by PID {row[4]} for {row[10]}s",
                "details": {
                    "blocked_pid": row[0],
                    "blocked_user": row[1],
                    "blocked_query": row[2],
                    "blocking_pid": row[4],
                    "blocking_user": row[5],
                    "blocking_query": row[6],
                    "locktype": row[8],
                    "relation": str(row[9]) if row[9] else None,
                    "wait_seconds": row[10],
                },
            })

    for row in load_active_queries(conn):
        duration = row[8] or 0
        if duration >= long_query_seconds:
            events.append({
                "type": "long_running_query",
                "severity": "critical" if duration >= 1 else "warning",
                "message": f"Query PID {row[0]} has been running for {duration}s",
                "details": {
                    "pid": row[0],
                    "user": row[1],
                    "application": row[2],
                    "state": row[3],
                    "wait_event_type": row[4],
                    "wait_event": row[5],
                    "query": row[6],
                    "query_start": row[7],
                    "duration_seconds": duration,
                    "client": str(row[9]) if row[9] else None,
                },
            })

    for row in load_table_health(conn):
        dead_ratio = float(row[4])
        if dead_ratio >= dead_tuple_ratio_pct and row[3] >= min_dead_tuples:
            events.append({
                "type": "dead_tuples",
                "severity": "warning",
                "message": f"Table {row[0]}.{row[1]} has {dead_ratio}% dead tuples",
                "details": {
                    "schema": row[0],
                    "table": row[1],
                    "live_tuples": row[2],
                    "dead_tuples": row[3],
                    "dead_ratio_pct": dead_ratio,
                    "last_vacuum": row[11],
                    "last_autovacuum": row[12],
                    "last_analyze": row[13],
                    "last_autoanalyze": row[14],
                    "total_size": row[15],
                    "total_size_bytes": row[16],
                },
            })

    for row in load_cache_hit(conn):
        heap_reads = row[1] or 0
        heap_hit_pct = float(row[3]) if row[3] is not None else None
        idx_reads = row[4] or 0
        idx_hit_pct = float(row[6]) if row[6] is not None else None
        if heap_hit_pct is not None and heap_reads >= min_cache_reads and heap_hit_pct < low_cache_hit_pct:
            events.append({
                "type": "low_table_cache_hit",
                "severity": "warning",
                "message": f"Table {row[0]} heap cache hit is {heap_hit_pct}%",
                "details": {
                    "table": row[0],
                    "heap_blocks_read": heap_reads,
                    "heap_blocks_hit": row[2],
                    "cache_hit_pct": heap_hit_pct,
                },
            })
        if idx_hit_pct is not None and idx_reads >= min_cache_reads and idx_hit_pct < low_cache_hit_pct:
            events.append({
                "type": "low_index_cache_hit",
                "severity": "warning",
                "message": f"Table {row[0]} index cache hit is {idx_hit_pct}%",
                "details": {
                    "table": row[0],
                    "index_blocks_read": idx_reads,
                    "index_blocks_hit": row[5],
                    "index_cache_hit_pct": idx_hit_pct,
                },
            })

    for row in load_duplicate_indexes(conn):
        events.append({
            "type": "duplicate_indexes",
            "severity": "warning",
            "message": f"Table {row[0]} has duplicate indexes",
            "details": {
                "table": str(row[0]),
                "indexes": row[1],
                "sizes": row[2],
                "size_bytes": row[4],
            },
        })

    for row in load_indexes(conn):
        if row[3] == 0 and row[7] >= unused_index_min_bytes:
            events.append({
                "type": "unused_large_index",
                "severity": "info",
                "message": f"Index {row[2]} on {row[0]}.{row[1]} has no scans",
                "details": {
                    "schema": row[0],
                    "table": row[1],
                    "index": row[2],
                    "scans": row[3],
                    "size": row[6],
                    "size_bytes": row[7],
                },
            })

    for row in load_database_sizes(conn):
        if float(row[8]) >= high_index_overhead_pct:
            events.append({
                "type": "high_index_overhead",
                "severity": "info",
                "message": f"Table {row[0]}.{row[1]} has {float(row[8])}% index overhead",
                "details": {
                    "schema": row[0],
                    "table": row[1],
                    "table_size": row[2],
                    "table_size_bytes": row[3],
                    "indexes_size": row[4],
                    "indexes_size_bytes": row[5],
                    "total_size": row[6],
                    "total_size_bytes": row[7],
                    "index_overhead_pct": float(row[8]),
                },
            })

    return events


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
    with_lines = results.get("with_index") or []
    without_lines = results.get("without_index") or []
    results["indexes_matter"] = with_lines != without_lines
    return results
