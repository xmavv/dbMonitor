import argparse
import datetime
import json
import os
import threading
from flask import Flask, request, render_template, abort

from docs_renderer import render_page, get_nav_sections, search_index_json

from db import (
    get_db_url, connect, setup_database, load_stats, load_indexes,
    load_duplicate_indexes, load_table_health, load_cache_hit,
    load_locks, load_active_queries, load_database_sizes, explain_query, load_triggers,
    load_extensions, load_buffercache, collect_anomaly_events
)

app = Flask(__name__, template_folder='templates', static_folder='static')

conn = None
db_error = None
setup_messages = []
stats_data = []
log_thread = None
log_stop_event = threading.Event()

def _json_serial(obj):
    import datetime
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _api(data):
    return json.dumps(data, default=_json_serial), 200, {"Content-Type": "application/json"}


def _int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float_env(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _anomaly_thresholds():
    return {
        "long_query_seconds": _int_env("DBMONITOR_LONG_QUERY_SECONDS", 30),
        "lock_wait_seconds": _int_env("DBMONITOR_LOCK_WAIT_SECONDS", 2),
        "dead_tuple_ratio_pct": _float_env("DBMONITOR_DEAD_TUPLE_RATIO_PCT", 20),
        "min_dead_tuples": _int_env("DBMONITOR_MIN_DEAD_TUPLES", 100),
        "low_cache_hit_pct": _float_env("DBMONITOR_LOW_CACHE_HIT_PCT", 90),
        "min_cache_reads": _int_env("DBMONITOR_MIN_CACHE_READS", 100),
        "unused_index_min_bytes": _int_env("DBMONITOR_UNUSED_INDEX_MIN_BYTES", 10 * 1024 * 1024),
        "high_index_overhead_pct": _float_env("DBMONITOR_HIGH_INDEX_OVERHEAD_PCT", 50),
    }


SEVERITY_LEVELS = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
}


def _severity_value(severity):
    return SEVERITY_LEVELS.get(str(severity).lower(), SEVERITY_LEVELS["info"])


def _event_fingerprint(event):
    return json.dumps({
        "type": event.get("type"),
        "severity": event.get("severity"),
        "message": event.get("message"),
        "details": event.get("details", {}),
    }, default=_json_serial, sort_keys=True, ensure_ascii=False)


def _should_log_event(event, min_severity, last_logged_at, now, repeat_seconds):
    if _severity_value(event.get("severity")) < min_severity:
        return False

    fingerprint = _event_fingerprint(event)
    previous = last_logged_at.get(fingerprint)
    if previous is not None and (now - previous).total_seconds() < repeat_seconds:
        return False

    last_logged_at[fingerprint] = now
    return True


def _write_anomaly_log_entry(log_path, payload):
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, default=_json_serial, ensure_ascii=False) + "\n")


def _run_anomaly_logger(db_url):
    interval = max(1, _int_env("DBMONITOR_LOG_INTERVAL_SECONDS", 60))
    log_path = os.getenv("DBMONITOR_ANOMALY_LOG_FILE", "logs/db_anomalies.jsonl")
    thresholds = _anomaly_thresholds()
    min_severity = _severity_value(os.getenv("DBMONITOR_LOG_MIN_SEVERITY", "warning"))
    repeat_seconds = max(interval, _int_env("DBMONITOR_LOG_REPEAT_SECONDS", 300))
    last_logged_at = {}

    while not log_stop_event.is_set():
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp = now.isoformat()
        sample_conn = None
        try:
            sample_conn = connect(db_url)
            events = collect_anomaly_events(sample_conn, thresholds)
            for event in events:
                if not _should_log_event(event, min_severity, last_logged_at, now, repeat_seconds):
                    continue
                event["timestamp"] = timestamp
                _write_anomaly_log_entry(log_path, event)
        except Exception as e:
            _write_anomaly_log_entry(log_path, {
                "timestamp": timestamp,
                "type": "monitoring_error",
                "severity": "error",
                "message": str(e),
                "details": {},
            })
        finally:
            if sample_conn:
                sample_conn.close()
        log_stop_event.wait(interval)


def _start_anomaly_logger(db_url):
    global log_thread
    if log_thread and log_thread.is_alive():
        return
    log_stop_event.clear()
    log_thread = threading.Thread(target=_run_anomaly_logger, args=(db_url,), daemon=True)
    log_thread.start()


@app.route("/api/stats")
def api_stats():
    try:
        data = load_stats(conn)
        return _api([
            {"queryid": r[0], "query": r[1], "calls": r[2],
             "mean_time": round(r[3], 3), "total_time": round(r[4], 3), "rows": r[5]}
            for r in data
        ])
    except Exception as e:
        return _api({"error": str(e)})


@app.route("/api/indexes")
def api_indexes():
    try:
        data = load_indexes(conn)
        dupes = load_duplicate_indexes(conn)
        dupe_names = set()
        for row in dupes:
            for name in row[1]:
                dupe_names.add(name)
        return _api({
            "indexes": [
                {"schema": r[0], "table": r[1], "index": r[2],
                 "scans": r[3], "tup_read": r[4], "tup_fetch": r[5],
                 "size": r[6], "size_bytes": r[7],
                 "is_duplicate": r[2] in dupe_names}
                for r in data
            ],
            "duplicates": [
                {"table": str(r[0]), "indexes": r[1], "sizes": r[2]}
                for r in dupes
            ]
        })
    except Exception as e:
        return _api({"error": str(e)})


@app.route("/api/table-health")
def api_table_health():
    try:
        health = load_table_health(conn)
        cache = load_cache_hit(conn)
        cache_map = {r[0]: {"heap_hit_pct": float(r[3]) if r[3] else None,
                            "idx_hit_pct": float(r[6]) if r[6] else None}
                     for r in cache}
        return _api([
            {
                "schema": r[0], "table": r[1],
                "live_tup": r[2], "dead_tup": r[3],
                "dead_ratio_pct": float(r[4]),
                "seq_scan": r[5], "idx_scan": r[6],
                "idx_ratio_pct": float(r[7]),
                "ins": r[8], "upd": r[9], "del": r[10],
                "last_vacuum": r[11], "last_autovacuum": r[12],
                "last_analyze": r[13], "last_autoanalyze": r[14],
                "total_size": r[15], "total_size_bytes": r[16],
                "cache_hit_pct": cache_map.get(r[1], {}).get("heap_hit_pct"),
                "idx_cache_hit_pct": cache_map.get(r[1], {}).get("idx_hit_pct"),
            }
            for r in health
        ])
    except Exception as e:
        return _api({"error": str(e)})


@app.route("/api/locks")
def api_locks():
    try:
        locks = load_locks(conn)
        active = load_active_queries(conn)
        return _api({
            "locks": [
                {"blocked_pid": r[0], "blocked_user": r[1], "blocked_query": r[2],
                 "blocked_since": r[3], "blocking_pid": r[4], "blocking_user": r[5],
                 "blocking_query": r[6], "blocking_since": r[7],
                 "locktype": r[8], "relation": str(r[9]) if r[9] else None,
                 "wait_seconds": r[10]}
                for r in locks
            ],
            "active": [
                {"pid": r[0], "user": r[1], "app": r[2], "state": r[3],
                 "wait_event_type": r[4], "wait_event": r[5], "query": r[6],
                 "query_start": r[7], "duration_seconds": r[8], "client": str(r[9]) if r[9] else None}
                for r in active
            ]
        })
    except Exception as e:
        return _api({"error": str(e)})


@app.route("/api/sizes")
def api_sizes():
    try:
        data = load_database_sizes(conn)
        return _api([
            {"schema": r[0], "table": r[1],
             "table_size": r[2], "table_size_bytes": r[3],
             "indexes_size": r[4], "indexes_size_bytes": r[5],
             "total_size": r[6], "total_size_bytes": r[7],
             "index_overhead_pct": float(r[8])}
            for r in data
        ])
    except Exception as e:
        return _api({"error": str(e)})


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json()
    query = data.get("query", "")
    if not query.strip().upper().startswith("SELECT"):
        return _api({"error": "Only SELECT queries can be analyzed."})
    results = explain_query(conn, query)
    return _api(results)

@app.route("/api/triggers")
def api_triggers():
    try:
        data = load_triggers(conn)
        return _api([
            {"schema": r[0], "table": r[1], "trigger": r[2],
             "status": r[3], "definition": r[4]}
            for r in data
        ])
    except Exception as e:
        return _api({"error": str(e)})


@app.route("/api/extensions")
def api_extensions():
    try:
        data = load_extensions(conn)
        return _api([
            {"name": r[0], "version": r[1], "schema": r[2]}
            for r in data
        ])
    except Exception as e:
        return _api({"error": str(e)})


def _anomaly_log_path():
    return os.getenv("DBMONITOR_ANOMALY_LOG_FILE", "logs/db_anomalies.jsonl")


def load_anomaly_log(limit=200):
    log_path = _anomaly_log_path()
    if not os.path.isfile(log_path):
        return {"path": log_path, "entries": [], "total": 0}

    entries = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    total = len(entries)
    if limit and len(entries) > limit:
        entries = entries[-limit:]
    entries.reverse()
    return {"path": log_path, "entries": entries, "total": total}


@app.route("/api/anomalies")
def api_anomalies():
    try:
        limit = _int_env("DBMONITOR_ANOMALY_LOG_READ_LIMIT", 200)
        query_limit = request.args.get("limit")
        if query_limit is not None:
            try:
                limit = max(1, min(1000, int(query_limit)))
            except (TypeError, ValueError):
                pass
        return _api(load_anomaly_log(limit))
    except Exception as e:
        return _api({"error": str(e)})


@app.route("/api/cache")
def api_cache():
    try:
        data = load_buffercache(conn)
        return _api([
            {"table": r[0], "buffers": r[1], "cached_size": r[2],
             "pct_of_cache": float(r[3]) if r[3] is not None else None}
            for r in data
        ])
    except Exception as e:
        return _api({"error": str(e)})


@app.route("/")
def index():
    if db_error:
        return f"<h1 style='color:red'>DB ERROR</h1><pre>{db_error}</pre>"
    return render_template("index.html")


def _render_docs(slug):
    rendered = render_page(slug)
    if rendered is None:
        abort(404)
    page = rendered["page"]
    return render_template(
        "docs/page.html",
        page=page,
        page_title=page["title"],
        current_slug=page["slug"],
        content_html=rendered["html"],
        nav_sections=get_nav_sections(),
        search_index_json=search_index_json(),
    )


@app.route("/docs")
@app.route("/docs/")
def docs_index():
    return _render_docs(None)


@app.route("/docs/<slug>")
def docs_page(slug):
    return _render_docs(slug)

def start(cli_db_url=None):
    global conn, db_error, setup_messages, stats_data
    db_url = get_db_url(cli_db_url)
    if not db_url:
        db_error = "No DB URL provided (CLI or ENV)"
        return
    try:
        conn = connect(db_url)
        setup_messages = setup_database(conn)
        stats_data = load_stats(conn)
        _start_anomaly_logger(db_url)
    except Exception as e:
        db_error = str(e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url")
    args = parser.parse_args()
    start(args.db_url)
    app.run(host="0.0.0.0", port=5001, debug=False)
