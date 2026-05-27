import argparse
import json

from flask import Flask, request

from db import (
    get_db_url, connect, setup_database, load_stats, load_indexes,
    load_duplicate_indexes, load_table_health, load_cache_hit,
    load_locks, load_active_queries, load_database_sizes, explain_query, load_triggers
)

app = Flask(__name__)

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

# ── Main SPA shell ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if db_error:
        return f"<h1 style='color:red'>DB ERROR</h1><pre>{db_error}</pre>"
    return SPA_HTML


# ── Start ──────────────────────────────────────────────────────────────────────

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


# ── SPA HTML ──────────────────────────────────────────────────────────────────

SPA_HTML = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PG Inspector</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

  :root {
    --bg: #0d0f14;
    --surface: #13161e;
    --surface2: #1a1e29;
    --border: #252a38;
    --border2: #2f3548;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --warn: #f59e0b;
    --danger: #ef4444;
    --success: #22c55e;
    --text: #e2e8f0;
    --text2: #94a3b8;
    --text3: #475569;
    --mono: 'IBM Plex Mono', monospace;
    --sans: 'IBM Plex Sans', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    font-size: 14px;
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  /* ── Sidebar ── */
  #sidebar {
    width: 220px;
    min-width: 220px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 0;
  }

  #sidebar-logo {
    padding: 20px 20px 16px;
    border-bottom: 1px solid var(--border);
  }
  #sidebar-logo .logo-text {
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.05em;
  }
  #sidebar-logo .logo-sub {
    font-size: 10px;
    color: var(--text3);
    margin-top: 2px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .nav-section {
    padding: 16px 12px 8px;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text3);
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 16px;
    cursor: pointer;
    color: var(--text2);
    font-size: 13px;
    font-weight: 400;
    border-left: 2px solid transparent;
    transition: all 0.15s;
  }
  .nav-item:hover { background: var(--surface2); color: var(--text); }
  .nav-item.active {
    background: var(--surface2);
    color: var(--accent);
    border-left-color: var(--accent);
    font-weight: 600;
  }
  .nav-icon { width: 16px; text-align: center; font-size: 15px; }

  #sidebar-footer {
    margin-top: auto;
    padding: 16px;
    border-top: 1px solid var(--border);
  }
  #refresh-btn {
    width: 100%;
    padding: 8px;
    background: transparent;
    border: 1px solid var(--border2);
    color: var(--text2);
    font-family: var(--mono);
    font-size: 11px;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.15s;
    letter-spacing: 0.05em;
  }
  #refresh-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* ── Main ── */
  #main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  #topbar {
    height: 48px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 24px;
    gap: 16px;
    background: var(--surface);
    flex-shrink: 0;
  }
  #page-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: 0.02em;
  }
  #status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--success);
    box-shadow: 0 0 6px var(--success);
    margin-left: auto;
  }

  #content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  /* ── Views ── */
  .view { display: none; }
  .view.active { display: block; }

  /* ── Cards ── */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    margin-bottom: 20px;
    overflow: hidden;
  }
  .card-header {
    padding: 14px 18px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text2);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .card-body { padding: 18px; }

  /* ── Tables ── */
  .data-table { width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: 12px; }
  .data-table th {
    text-align: left;
    padding: 8px 12px;
    background: var(--surface2);
    color: var(--text3);
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  .data-table td {
    padding: 9px 12px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    vertical-align: top;
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .data-table tr:last-child td { border-bottom: none; }
  .data-table tr:hover td { background: var(--surface2); }
  .data-table td.wrap { white-space: pre-wrap; word-break: break-all; max-width: 400px; }

  /* ── Badges ── */
  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    font-family: var(--mono);
    letter-spacing: 0.05em;
  }
  .badge-danger { background: rgba(239,68,68,0.15); color: var(--danger); border: 1px solid rgba(239,68,68,0.3); }
  .badge-warn { background: rgba(245,158,11,0.15); color: var(--warn); border: 1px solid rgba(245,158,11,0.3); }
  .badge-ok { background: rgba(34,197,94,0.15); color: var(--success); border: 1px solid rgba(34,197,94,0.3); }
  .badge-info { background: rgba(0,212,255,0.12); color: var(--accent); border: 1px solid rgba(0,212,255,0.25); }

  /* ── Metrics row ── */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
  }
  .metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 16px 18px;
  }
  .metric-label { font-size: 10px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); margin-bottom: 8px; }
  .metric-value { font-family: var(--mono); font-size: 22px; font-weight: 600; color: var(--text); }
  .metric-sub { font-size: 11px; color: var(--text3); margin-top: 3px; }

  /* ── Query plan tree ── */
  #plan-modal {
    display: none;
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.75);
    z-index: 100;
    align-items: center;
    justify-content: center;
  }
  #plan-modal.open { display: flex; }
  #plan-box {
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: 8px;
    width: 90vw; max-width: 1200px;
    height: 85vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  #plan-header {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
  }
  #plan-header h2 { font-size: 13px; font-weight: 600; color: var(--text); flex: 1; }
  #plan-close {
    background: none; border: none; color: var(--text2);
    font-size: 20px; cursor: pointer; line-height: 1;
  }
  #plan-tabs {
    display: flex;
    border-bottom: 1px solid var(--border);
    padding: 0 20px;
    background: var(--surface2);
  }
  .plan-tab {
    padding: 10px 16px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text3);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    letter-spacing: 0.05em;
  }
  .plan-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  #plan-content {
    flex: 1;
    overflow: auto;
    padding: 20px;
  }

  /* Tree nodes */
  .tree-node {
    margin: 4px 0;
    font-family: var(--mono);
    font-size: 12px;
  }
  .tree-node-header {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 4px;
    background: var(--surface2);
    border: 1px solid var(--border);
    cursor: pointer;
    transition: border-color 0.15s;
    white-space: nowrap;
  }
  .tree-node-header:hover { border-color: var(--border2); }
  .tree-node-header.critical { border-color: rgba(239,68,68,0.5); background: rgba(239,68,68,0.06); }
  .tree-node-header.warn { border-color: rgba(245,158,11,0.4); background: rgba(245,158,11,0.05); }
  .node-type { font-weight: 600; color: var(--accent); }
  .node-type.join { color: var(--accent2); }
  .node-type.scan { color: #34d399; }
  .node-type.sort { color: #fb923c; }
  .node-cost { color: var(--text3); font-size: 11px; }
  .node-rows { color: var(--warn); font-size: 11px; }
  .node-time { color: var(--success); font-size: 11px; }
  .tree-children {
    margin-left: 28px;
    padding-left: 12px;
    border-left: 1px dashed var(--border2);
    margin-top: 3px;
  }
  .tree-toggle { color: var(--text3); cursor: pointer; user-select: none; font-size: 10px; }

  pre.plan-text {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text);
    white-space: pre-wrap;
    line-height: 1.6;
  }

  /* ── Lock graph ── */
  .lock-item {
    background: var(--surface2);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 6px;
    padding: 16px;
    margin-bottom: 12px;
  }
  .lock-arrow {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 10px 0;
  }
  .lock-pid {
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: 4px;
    padding: 8px 14px;
    font-family: var(--mono);
    font-size: 12px;
  }
  .lock-pid .pid-num { color: var(--accent); font-weight: 600; }
  .lock-pid .pid-user { color: var(--text2); font-size: 11px; }
  .lock-arrow-line {
    flex: 1;
    height: 2px;
    background: linear-gradient(90deg, var(--danger), transparent);
    position: relative;
  }
  .lock-arrow-line::after {
    content: '▶';
    position: absolute;
    right: 0;
    top: -7px;
    color: var(--danger);
    font-size: 12px;
  }

  /* ── Sizes treemap-like bars ── */
  .size-bar-row { margin-bottom: 10px; }
  .size-bar-label { display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px; }
  .size-bar-name { font-family: var(--mono); color: var(--text); }
  .size-bar-val { font-family: var(--mono); color: var(--text2); font-size: 11px; }
  .size-bar-full { background: var(--surface2); border-radius: 4px; height: 20px; overflow: hidden; display: flex; }
  .size-bar-data { background: rgba(0,212,255,0.35); height: 100%; }
  .size-bar-idx { background: rgba(124,58,237,0.5); height: 100%; }

  /* ── Loading ── */
  .loader {
    display: flex; align-items: center; gap: 10px;
    color: var(--text3); font-family: var(--mono); font-size: 12px;
    padding: 40px 0;
  }
  .spinner {
    width: 16px; height: 16px;
    border: 2px solid var(--border2);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Query cell ── */
  .query-cell {
    font-family: var(--mono); font-size: 11px; color: var(--text2);
    max-width: 380px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    cursor: pointer;
  }
  .query-cell:hover { color: var(--accent); }

  .btn {
    padding: 4px 10px;
    font-family: var(--mono);
    font-size: 11px;
    background: transparent;
    border: 1px solid var(--border2);
    color: var(--text2);
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .btn:hover { border-color: var(--accent); color: var(--accent); }
  .btn-danger:hover { border-color: var(--danger); color: var(--danger); }

  .empty-state {
    padding: 40px;
    text-align: center;
    color: var(--text3);
    font-size: 13px;
  }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text3); }
</style>
</head>
<body>

<nav id="sidebar">
  <div id="sidebar-logo">
    <div class="logo-text">▶ PG Inspector</div>
    <div class="logo-sub">PostgreSQL Analytics</div>
  </div>
  <div class="nav-section">Queries</div>
  <div class="nav-item active" onclick="showView('queries')">
    Top Queries
  </div>
  <div class="nav-section">Storage</div>
  <div class="nav-item" onclick="showView('tables')">
    Table Health
  </div>
  <div class="nav-item" onclick="showView('sizes')">
    DB Sizes
  </div>
  <div class="nav-section">Indexes</div>
  <div class="nav-item" onclick="showView('indexes')">
    Index Usage
  </div>
  <div class="nav-section">Runtime</div>
  <div class="nav-item" onclick="showView('locks')">
    Lock Monitor
  </div>
  <div class="nav-section">Trgrs</div>
  <div class="nav-item" onclick="showView('triggers')">
    Triggers
  </div>
  <div id="sidebar-footer">
    <button id="refresh-btn" onclick="refreshCurrent()">↺ Refresh</button>
  </div>
</nav>

<div id="main">
  <div id="topbar">
    <span id="page-title">Top Queries</span>
    <span id="status-dot"></span>
  </div>
  <div id="content">

    <div id="view-queries" class="view active">
      <div id="queries-content"><div class="loader"><div class="spinner"></div>Loading query stats…</div></div>
    </div>

    <div id="view-tables" class="view">
      <div id="tables-content"><div class="loader"><div class="spinner"></div>Loading table health…</div></div>
    </div>

    <div id="view-sizes" class="view">
      <div id="sizes-content"><div class="loader"><div class="spinner"></div>Loading sizes…</div></div>
    </div>

    <div id="view-indexes" class="view">
      <div id="indexes-content"><div class="loader"><div class="spinner"></div>Loading indexes…</div></div>
    </div>

    <div id="view-locks" class="view">
      <div id="locks-content"><div class="loader"><div class="spinner"></div>Loading locks…</div></div>
    </div>

    <div id="view-triggers" class="view">
      <div id="triggers-content"><div class="loader"><div class="spinner"></div>Ładowanie triggerów…</div></div>
    </div>
    
  </div>
</div>

<div id="plan-modal">
  <div id="plan-box">
    <div id="plan-header">
      <h2>Query Execution Plan</h2>
      <button id="plan-close" onclick="closePlan()">✕</button>
    </div>
    <div id="plan-tabs">
      <div class="plan-tab active" onclick="switchPlanTab('tree')">Tree View</div>
      <div class="plan-tab" onclick="switchPlanTab('with')">With Indexes</div>
      <div class="plan-tab" onclick="switchPlanTab('without')">Without Indexes</div>
    </div>
    <div id="plan-content"></div>
  </div>
</div>

<script>
// ── State ─────────────────────────────────────────────────────────────────────
let currentView = 'queries';
let planData = null;
let currentPlanTab = 'tree';
const loaded = {};

// ── Navigation ────────────────────────────────────────────────────────────────
function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  event.currentTarget.classList.add('active');
  document.getElementById('page-title').textContent = {
    queries: 'Top Queries', tables: 'Table Health',
    sizes: 'Database Sizes', indexes: 'Index Usage', locks: 'Lock Monitor',
    triggers: 'Triggers'
  }[name];
  currentView = name;
  if (!loaded[name]) loadView(name);
}

function refreshCurrent() { loaded[currentView] = false; loadView(currentView); }

function loadView(name) {
  loaded[name] = true;
  const loaders = {
    queries: loadQueries, tables: loadTables,
    sizes: loadSizes, indexes: loadIndexes, locks: loadLocks,
    triggers: loadTriggers
  };
  loaders[name]?.();
}

async function loadTriggers() {
  const container = document.getElementById('triggers-content');
  try {
    const res = await fetch('/api/triggers');
    const data = await res.json();
    
    if (data.error) {
      container.innerHTML = `<div class="empty-state">Błąd: ${data.error}</div>`;
      return;
    }
    
    if (!data.length) {
      container.innerHTML = `<div class="empty-state">No triggers defined in database.</div>`;
      return;
    }

    let html = `
      <div class="card">
        <div class="card-header">Configured triggers</div>
        <table class="data-table">
          <tr>
            <th>Schemat</th>
            <th>Tabela</th>
            <th>Nazwa Triggera</th>
            <th>Status</th>
            <th>Definicja (Kod)</th>
          </tr>`;

    data.forEach(t => {
      // Używamy istniejących klas CSS z Twojej aplikacji do ładnego formatowania badge'y
      const statusClass = t.status === 'ENABLED' ? 'badge-ok' : (t.status === 'DISABLED' ? 'badge-danger' : 'badge-warn');
      html += `<tr>
        <td>${t.schema}</td>
        <td><strong>${t.table}</strong></td>
        <td>${t.trigger}</td>
        <td><span class="badge ${statusClass}">${t.status}</span></td>
        <td class="wrap" style="font-size: 11px;">${t.definition}</td>
      </tr>`;
    });

    html += `</table></div>`;
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="empty-state">Błąd połączenia z API.</div>`;
  }
}
window.addEventListener('load', () => loadView('queries'));

// ── Helpers ───────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
function fmt(n, dec=2) { return n == null ? '—' : Number(n).toFixed(dec); }
function fmtNum(n) { if (n == null) return '—'; if (n >= 1e6) return (n/1e6).toFixed(1)+'M'; if (n >= 1e3) return (n/1e3).toFixed(1)+'K'; return n; }

function badgeForPct(pct, reverse=false) {
  if (pct == null) return '<span class="badge badge-info">N/A</span>';
  const hi = reverse ? pct < 5 : pct > 95;
  const mid = reverse ? pct < 20 : pct > 80;
  const cls = hi ? 'badge-ok' : mid ? 'badge-warn' : 'badge-danger';
  return `<span class="badge ${cls}">${fmt(pct,1)}%</span>`;
}

function elapsed(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d) / 1000);
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  if (s < 86400) return Math.floor(s/3600) + 'h ago';
  return Math.floor(s/86400) + 'd ago';
}

// ── QUERIES ───────────────────────────────────────────────────────────────────
async function loadQueries() {
  const el = $('queries-content');
  el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
  const res = await fetch('/api/stats');
  const data = await res.json();
  if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

  const maxTotal = Math.max(...data.map(r => r.total_time));

  let html = `<div class="card">
    <div class="card-header">Top Queries by Total Time</div>
    <div style="overflow-x: auto;">
    <table class="data-table">
    <thead><tr>
      <th>#</th><th>Query</th><th>Calls</th>
      <th>Mean (ms)</th><th>Total (ms)</th><th>Rows</th><th>Action</th>
    </tr></thead><tbody>`;

  data.forEach((r, i) => {
    const pct = (r.total_time / maxTotal * 100).toFixed(1);
    const isSelect = r.query.trim().toUpperCase().startsWith('SELECT');
    html += `<tr>
      <td style="color:var(--text3);font-family:var(--mono)">${i+1}</td>
      <td><div class="query-cell" title="${escHtml(r.query)}" onclick="showQueryFull('${escAttr(r.query)}')">${escHtml(r.query)}</div></td>
      <td style="font-family:var(--mono)">${fmtNum(r.calls)}</td>
      <td style="font-family:var(--mono)">${fmt(r.mean_time,2)}</td>
      <td style="font-family:var(--mono)">${fmt(r.total_time,0)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.rows)}</td>
      <td>${isSelect ? `<button class="btn" onclick="analyzePlan('${escAttr(r.query)}')">Analyze</button>` : ''}</td>
    </tr>`;
  });

  html += '</tbody></table></div></div>';
  el.innerHTML = html;
}

function showQueryFull(q) {
  alert(q);
}

// ── PLAN ──────────────────────────────────────────────────────────────────────
async function analyzePlan(query) {
  planData = null;
  currentPlanTab = 'tree';
  $('plan-modal').classList.add('open');
  $('plan-content').innerHTML = '<div class="loader"><div class="spinner"></div>Running EXPLAIN…</div>';
  switchPlanTab('tree', true);

  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query})
  });
  planData = await res.json();
  renderPlanTab(currentPlanTab);
}

function closePlan() { $('plan-modal').classList.remove('open'); }

function switchPlanTab(tab, noRender=false) {
  currentPlanTab = tab;
  document.querySelectorAll('.plan-tab').forEach((t,i) => {
    t.classList.toggle('active', ['tree','with','without'][i] === tab);
  });
  if (!noRender && planData) renderPlanTab(tab);
}

function renderPlanTab(tab) {
  const el = $('plan-content');
  if (!planData) return;
  if (planData.error) {
    el.innerHTML = `<pre style="color:var(--danger)">${escHtml(planData.error)}</pre>`; return;
  }
  if (tab === 'tree') {
    if (planData.plan_json) {
      const plan = planData.plan_json[0] || planData.plan_json;
      el.innerHTML = '';
      el.appendChild(renderTreeNode(plan['Plan'], 0));
    } else {
      el.innerHTML = '<pre class="plan-text">' + escHtml((planData.with_index||[]).join('\n')) + '</pre>';
    }
  } else if (tab === 'with') {
    el.innerHTML = '<pre class="plan-text">' + escHtml((planData.with_index||[]).join('\n')) + '</pre>';
  } else {
    const txt = planData.without_index_error
      ? planData.without_index_error
      : (planData.without_index||[]).join('\n');
    el.innerHTML = '<pre class="plan-text">' + escHtml(txt) + '</pre>';
  }
}

function renderTreeNode(node, depth) {
  if (!node) return document.createElement('div');
  const wrap = document.createElement('div');
  wrap.className = 'tree-node';

  const type = node['Node Type'] || '?';
  const startCost = node['Startup Cost'] || 0;
  const totalCost = node['Total Cost'] || 0;
  const planRows = node['Plan Rows'] || 0;
  const actualRows = node['Actual Rows'];
  const actualTime = node['Actual Total Time'];
  const relation = node['Relation Name'] ? ` on ${node['Relation Name']}` : '';
  const alias = node['Alias'] && node['Alias'] !== node['Relation Name'] ? ` (${node['Alias']})` : '';
  const indexName = node['Index Name'] ? ` [${node['Index Name']}]` : '';
  const filter = node['Filter'] || node['Join Filter'] || node['Hash Cond'] || node['Index Cond'] || '';

  // Classify severity
  let severity = '';
  if (totalCost > 10000) severity = 'critical';
  else if (totalCost > 1000) severity = 'warn';

  // Classify node type color
  let typeClass = '';
  if (type.includes('Join') || type.includes('Loop')) typeClass = 'join';
  else if (type.includes('Scan')) typeClass = 'scan';
  else if (type.includes('Sort') || type.includes('Aggregate')) typeClass = 'sort';

  const rowDiff = actualRows != null ? Math.abs(actualRows - planRows) / (planRows || 1) : 0;

  const header = document.createElement('div');
  header.className = `tree-node-header ${severity}`;
  header.innerHTML = `
    <span class="node-type ${typeClass}">${type}${relation}${alias}${indexName}</span>
    <span class="node-cost">cost=${startCost.toFixed(2)}..${totalCost.toFixed(2)}</span>
    <span class="node-rows">${rowDiff > 2 ? '⚠ ' : ''}rows=${fmtNum(planRows)}${actualRows != null ? '→'+fmtNum(actualRows) : ''}</span>
    ${actualTime != null ? `<span class="node-time">${actualTime.toFixed(2)}ms</span>` : ''}
    ${filter ? `<span style="color:var(--text3);font-size:10px">${escHtml(filter.substring(0,60))}${filter.length>60?'…':''}</span>` : ''}
  `;
  wrap.appendChild(header);

  const plans = node['Plans'];
  if (plans && plans.length) {
    const childrenWrap = document.createElement('div');
    childrenWrap.className = 'tree-children';
    plans.forEach(child => childrenWrap.appendChild(renderTreeNode(child, depth+1)));
    wrap.appendChild(childrenWrap);
  }
  return wrap;
}

// ── TABLE HEALTH ──────────────────────────────────────────────────────────────
async function loadTables() {
  const el = $('tables-content');
  el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
  const res = await fetch('/api/table-health');
  const data = await res.json();
  if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

  // Summary metrics
  const avgCache = data.filter(r => r.cache_hit_pct != null);
  const avgCacheVal = avgCache.length ? (avgCache.reduce((s,r)=>s+r.cache_hit_pct,0)/avgCache.length).toFixed(1) : 'N/A';
  const bloatTables = data.filter(r => r.dead_ratio_pct > 10).length;
  const seqScanHeavy = data.filter(r => r.seq_scan > 100 && r.idx_ratio_pct < 50).length;

  let html = `<div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Tables</div>
      <div class="metric-value">${data.length}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Avg Cache Hit</div>
      <div class="metric-value" style="color:${avgCacheVal>95?'var(--success)':avgCacheVal>80?'var(--warn)':'var(--danger)'}">${avgCacheVal}%</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">High Bloat Tables</div>
      <div class="metric-value" style="color:${bloatTables>0?'var(--danger)':'var(--success)'}">${bloatTables}</div>
      <div class="metric-sub">&gt;10% dead tuples</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Seq Scan Heavy</div>
      <div class="metric-value" style="color:${seqScanHeavy>0?'var(--warn)':'var(--success)'}">${seqScanHeavy}</div>
      <div class="metric-sub">low index ratio</div>
    </div>
  </div>`;

  html += `<div class="card">
    <div class="card-header">Table Health Dashboard</div>
    <div style="overflow-x: auto;">
    <table class="data-table"><thead><tr>
      <th>Schema</th><th>Table</th><th>Size</th>
      <th>Live Tup</th><th>Dead Tup</th>
      <th>Ins</th><th>Upd</th><th>Del</th>
      <th>Cache Hit</th><th>Idx Cache Hit</th>
      <th>Dead Tup %</th><th>Idx Usage %</th>
      <th>Seq Scans</th><th>Idx Scans</th>
      <th>Last Vacuum</th><th>Last Analyze</th>
    </tr></thead><tbody>`;

  data.forEach(r => {
    const deadBad = r.dead_ratio_pct > 10;
    const idxBad = r.idx_ratio_pct < 50 && r.seq_scan > 10;
    const cacheBad = r.cache_hit_pct != null && r.cache_hit_pct < 90;
    const rowStyle = (deadBad || idxBad || cacheBad) ? 'background:rgba(239,68,68,0.04)' : '';
    html += `<tr style="${rowStyle}">
      <td style="color:var(--text3)">${escHtml(r.schema)}</td>
      <td style="font-family:var(--mono);font-weight:600">${escHtml(r.table)}</td>
      <td style="font-family:var(--mono)">${r.total_size}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.live_tup)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.dead_tup)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.ins)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.upd)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.del)}</td>
      <td>${badgeForPct(r.cache_hit_pct)}</td>
      <td>${badgeForPct(r.idx_cache_hit_pct)}</td>
      <td>${badgeForPct(r.dead_ratio_pct)}</td>
      <td>${badgeForPct(r.idx_ratio_pct)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.seq_scan)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.idx_scan)}</td>
      <td style="color:var(--text3)">${elapsed(r.last_autovacuum || r.last_vacuum)}</td>
      <td style="color:var(--text3)">${elapsed(r.last_autoanalyze || r.last_analyze)}</td>
    </tr>`;
  });
  html += '</tbody></table></div></div>';
  el.innerHTML = html;
}

// ── SIZES ────────────────────────────────────────────────────────────────────
async function loadSizes() {
  const el = $('sizes-content');
  el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
  const res = await fetch('/api/sizes');
  const data = await res.json();
  if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

  const maxBytes = Math.max(...data.map(r => r.total_size_bytes), 1);
  const totalDB = data.reduce((s,r)=>s+r.total_size_bytes, 0);

  let html = `<div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Total DB Size</div>
      <div class="metric-value" style="font-size:18px">${fmtBytes(totalDB)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Tables</div>
      <div class="metric-value">${data.length}</div>
    </div>
  </div>`;

  html += `<div class="card"><div class="card-header">Size Distribution</div><div class="card-body">`;
  data.forEach(r => {
    const dataW = (r.table_size_bytes / maxBytes * 100).toFixed(1);
    const idxW = (r.indexes_size_bytes / maxBytes * 100).toFixed(1);
    html += `<div class="size-bar-row">
      <div class="size-bar-label">
        <span class="size-bar-name"><span style="color:var(--text3)">${escHtml(r.schema)}.</span>${escHtml(r.table)}</span>
        <span class="size-bar-val">
          <span style="color:var(--accent)">data: ${r.table_size}</span>
          &nbsp;+&nbsp;
          <span style="color:#a78bfa">idx: ${r.indexes_size}</span>
          &nbsp;=&nbsp;${r.total_size}
          ${r.index_overhead_pct > 50 ? `<span class="badge badge-warn" style="margin-left:8px">idx ${r.index_overhead_pct}%</span>` : ''}
        </span>
      </div>
      <div class="size-bar-full">
        <div class="size-bar-data" style="width:${dataW}%"></div>
        <div class="size-bar-idx" style="width:${idxW}%"></div>
      </div>
    </div>`;
  });
  html += '</div></div>';

  html += `<div class="card">
    <div class="card-header">Detailed Breakdown</div>
    <div style="overflow-x: auto;">
    <table class="data-table"><thead><tr>
      <th>Schema</th><th>Table</th><th>Data Size</th><th>Index Size</th><th>Total</th><th>Index Overhead</th>
    </tr></thead><tbody>`;
  data.forEach(r => {
    const overHigh = r.index_overhead_pct > 60;
    html += `<tr>
      <td style="color:var(--text3)">${escHtml(r.schema)}</td>
      <td style="font-family:var(--mono);font-weight:600">${escHtml(r.table)}</td>
      <td style="font-family:var(--mono)">${r.table_size}</td>
      <td style="font-family:var(--mono)">${r.indexes_size}</td>
      <td style="font-family:var(--mono);font-weight:600">${r.total_size}</td>
      <td>${overHigh ? `<span class="badge badge-warn">${r.index_overhead_pct}%</span>` : `<span class="badge badge-ok">${r.index_overhead_pct}%</span>`}</td>
    </tr>`;
  });
  html += '</tbody></table></div></div>';
  el.innerHTML = html;
}

function fmtBytes(b) {
  if (b >= 1e9) return (b/1e9).toFixed(2) + ' GB';
  if (b >= 1e6) return (b/1e6).toFixed(1) + ' MB';
  if (b >= 1e3) return (b/1e3).toFixed(0) + ' KB';
  return b + ' B';
}

// ── INDEXES ───────────────────────────────────────────────────────────────────
async function loadIndexes() {
  const el = $('indexes-content');
  el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
  const res = await fetch('/api/indexes');
  const data = await res.json();
  if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

  const unused = data.indexes.filter(i => i.scans === 0).length;
  const dupes = data.duplicates.length;

  let html = `<div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Total Indexes</div>
      <div class="metric-value">${data.indexes.length}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Unused (0 scans)</div>
      <div class="metric-value" style="color:${unused>0?'var(--warn)':'var(--success)'}">${unused}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Duplicate Groups</div>
      <div class="metric-value" style="color:${dupes>0?'var(--danger)':'var(--success)'}">${dupes}</div>
    </div>
  </div>`;

  if (dupes > 0) {
    html += `<div class="card"><div class="card-header" style="color:var(--danger)">⚠ Duplicate Indexes</div><div class="card-body">`;
    data.duplicates.forEach(d => {
      html += `<div style="margin-bottom:12px;padding:12px;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);border-radius:4px">
        <div style="font-family:var(--mono);font-size:12px;color:var(--text2);margin-bottom:6px">Table: <strong style="color:var(--text)">${escHtml(d.table)}</strong></div>
        ${d.indexes.map((n,i) => `<span class="badge badge-danger" style="margin-right:6px">${escHtml(n)}</span><span style="font-size:11px;color:var(--text3)">${d.sizes[i]}</span>&nbsp;&nbsp;`).join('')}
      </div>`;
    });
    html += '</div></div>';
  }

  html += `<div class="card">
    <div class="card-header">Index Usage</div>
    <div style="overflow-x: auto;">
    <table class="data-table"><thead><tr>
      <th>Schema</th><th>Table</th><th>Index</th><th>Scans</th>
      <th>Tuples Read</th><th>Tuples Fetched</th><th>Size</th><th>Status</th>
    </tr></thead><tbody>`;

  data.indexes.forEach(r => {
    const isUnused = r.scans === 0;
    const isDupe = r.is_duplicate;
    html += `<tr style="${isUnused?'background:rgba(245,158,11,0.04)':''}">
      <td style="color:var(--text3)">${escHtml(r.schema)}</td>
      <td style="font-family:var(--mono)">${escHtml(r.table)}</td>
      <td style="font-family:var(--mono);color:${isDupe?'var(--danger)':isUnused?'var(--warn)':'var(--text)'}">${escHtml(r.index)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.scans)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.tup_read)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.tup_fetch)}</td>
      <td style="font-family:var(--mono)">${r.size}</td>
      <td>
        ${isDupe ? '<span class="badge badge-danger">DUPLICATE</span>' : ''}
        ${isUnused && !isDupe ? '<span class="badge badge-warn">UNUSED</span>' : ''}
        ${!isDupe && !isUnused ? '<span class="badge badge-ok">OK</span>' : ''}
      </td>
    </tr>`;
  });
  html += '</tbody></table></div></div>';
  el.innerHTML = html;
}

// ── LOCKS ─────────────────────────────────────────────────────────────────────
async function loadLocks() {
  const el = $('locks-content');
  el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
  const res = await fetch('/api/locks');
  const data = await res.json();
  if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

  let html = '';

  // Lock chains
  if (data.locks.length === 0) {
    html += `<div class="card"><div class="card-body"><div class="empty-state">✓ No active locks detected</div></div></div>`;
  } else {
    html += `<div class="card"><div class="card-header" style="color:var(--danger)">Active Lock Chains (${data.locks.length})</div><div class="card-body">`;
    data.locks.forEach(l => {
      html += `<div class="lock-item">
        <div style="font-size:11px;color:var(--text3);margin-bottom:8px">
          Type: <strong style="color:var(--text)">${l.locktype}</strong>
          ${l.relation ? ` on <strong style="color:var(--accent)">${l.relation}</strong>` : ''}
          &nbsp;·&nbsp; Waiting: <strong style="color:var(--danger)">${l.wait_seconds}s</strong>
        </div>
        <div class="lock-arrow">
          <div class="lock-pid">
            <div class="pid-num">PID ${l.blocking_pid}</div>
            <div class="pid-user">${l.blocking_user}</div>
          </div>
          <div class="lock-arrow-line"></div>
          <div style="font-size:10px;color:var(--danger);white-space:nowrap">BLOCKS</div>
          <div class="lock-arrow-line" style="background:linear-gradient(90deg,transparent,var(--danger))"></div>
          <div class="lock-pid" style="border-color:var(--danger)">
            <div class="pid-num">PID ${l.blocked_pid}</div>
            <div class="pid-user">${l.blocked_user}</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px">
          <div>
            <div style="font-size:10px;color:var(--text3);margin-bottom:3px">BLOCKING QUERY</div>
            <pre style="font-size:11px;color:var(--text2);white-space:pre-wrap;word-break:break-all;background:var(--surface);padding:6px 8px;border-radius:4px;max-height:80px;overflow:auto">${escHtml((l.blocking_query||'').substring(0,200))}</pre>
          </div>
          <div>
            <div style="font-size:10px;color:var(--danger);margin-bottom:3px">BLOCKED QUERY</div>
            <pre style="font-size:11px;color:var(--text2);white-space:pre-wrap;word-break:break-all;background:var(--surface);padding:6px 8px;border-radius:4px;max-height:80px;overflow:auto">${escHtml((l.blocked_query||'').substring(0,200))}</pre>
          </div>
        </div>
      </div>`;
    });
    html += '</div></div>';
  }

  // Active queries
  html += `<div class="card">
    <div class="card-header">⚙ Active Queries (${data.active.length})</div>
    <div style="overflow-x: auto;">
    <table class="data-table"><thead><tr>
      <th>PID</th><th>User</th><th>App</th><th>Client</th><th>State</th><th>Wait</th><th>Duration</th><th>Query</th>
    </tr></thead><tbody>`;

  if (data.active.length === 0) {
    html += '<tr><td colspan="8" class="empty-state">No active queries</td></tr>';
  }

  data.active.forEach(r => {
    const durCls = r.duration_seconds > 30 ? 'var(--danger)' : r.duration_seconds > 5 ? 'var(--warn)' : 'var(--text)';
    html += `<tr>
      <td style="font-family:var(--mono)">${r.pid}</td>
      <td style="font-family:var(--mono)">${escHtml(r.user||'')}</td>
      <td style="color:var(--text3)">${escHtml(r.app||'')}</td>
      <td style="font-family:var(--mono)">${escHtml(r.client||'')}</td>
      <td><span class="badge ${r.state==='active'?'badge-ok':r.state?.includes('transaction')?'badge-danger':'badge-warn'}">${r.state}</span></td>
      <td style="font-size:11px;color:var(--text3)">${r.wait_event_type ? `${r.wait_event_type}/${r.wait_event}` : '—'}</td>
      <td style="font-family:var(--mono);color:${durCls}">${r.duration_seconds != null ? r.duration_seconds + 's' : '—'}</td>
      <td><div class="query-cell">${escHtml((r.query||'').substring(0,120))}</div></td>
    </tr>`;
  });
  html += '</tbody></table></div></div>';
  el.innerHTML = html;
}

// ── Escape helpers ─────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) {
  return String(s||'').replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/"/g,'&quot;').replace(/\n/g,'\\n');
}
</script>
</body>
</html>"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url")
    args = parser.parse_args()
    start(args.db_url)
    app.run(host="0.0.0.0", port=5001, debug=False)