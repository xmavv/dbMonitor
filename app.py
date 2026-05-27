import json

from flask import Flask, request, render_template

from db import (
    get_db_url, connect, setup_database, load_stats, load_indexes,
    load_duplicate_indexes, load_table_health, load_cache_hit,
    load_locks, load_active_queries, load_database_sizes, explain_query, load_triggers
)

app = Flask(__name__, template_folder='templates', static_folder='static')

conn = None
db_error = None
setup_messages = []
stats_data = []

def _json_serial(obj):
    import datetime
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _api(data):
    return json.dumps(data, default=_json_serial), 200, {"Content-Type": "application/json"}


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


@app.route("/")
def index():
    if db_error:
        return f"<h1 style='color:red'>DB ERROR</h1><pre>{db_error}</pre>"
    return render_template("index.html")

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
    except Exception as e:
        db_error = str(e)

if __name__ == "__main__":
    start()
    app.run(host="0.0.0.0", port=5001, debug=False)