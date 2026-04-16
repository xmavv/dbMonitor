import argparse
from flask import Flask
from db import get_db_url, connect, setup_database, load_stats, load_live, load_scan, load_idx, load_cache, load_locks, load_statio, load_extensions, load_indexes, load_activity

app = Flask(__name__)

conn = None
db_error = None
live_messages = []
setup_messages = []
stats_data = []
live_data = []
scan_data = []
idx_data = []
statio_data = []
activity_data = []
locks_data = []
indexes_data = []
extensions_data = []
cache_data = []

@app.route("/refresh", methods=["GET"])
def refresh():
    global stats_data, db_error, live_data, scan_data, idx_data, statio_data, activity_data, locks_data, indexes_data, extensions_data, cache_data

    try:
        stats_data = load_stats(conn)
        live_data = load_live(conn)
        scan_data = load_scan(conn)
        idx_data = load_idx(conn)
        statio_data = load_statio(conn)
        activity_data = load_activity(conn)
        locks_data = load_locks(conn)
        indexes_data = load_indexes(conn)
        extensions_data = load_extensions(conn)
        cache_data = load_cache(conn)
        db_error = None
    except Exception as e:
        db_error = str(e)

    return """
    <html>
      <head>
        <meta http-equiv="refresh" content="0; url=/" />
      </head>
      <body>
        Odświeżanie...
      </body>
    </html>
    """

@app.route("/")
def index():
    if db_error:
        return f"<h1>DB ERROR</h1><pre>{db_error}</pre>"

    global stats_data, live_data, scan_data, idx_data, statio_data, activity_data, locks_data, indexes_data, extensions_data, cache_data

    stats_data = load_stats(conn)
    live_data = load_live(conn)
    scan_data = load_scan(conn)
    idx_data = load_idx(conn)
    statio_data = load_statio(conn)
    activity_data = load_activity(conn)
    locks_data = load_locks(conn)
    indexes_data = load_indexes(conn)
    extensions_data = load_extensions(conn)
    cache_data = load_cache(conn)

    html = """
    <html>
    <head>
    <meta http-equiv="refresh" content="1">
    </head>
    <body>
    """

    html += "<h1>DB Inspector</h1>"

    html += "<h2>Setup</h2><pre>"
    for msg in setup_messages:
        html += msg + "\n"
    html += "</pre>"

    html += """
       <form action="/refresh" method="get">
           <button type="submit">Odśwież statystyki</button>
       </form>
       """

    html += "<h2>Top Queries</h2><table border=1>"
    html += "<tr><th>No.</th><th>Query</th><th>Calls</th><th>Mean Time</th><th>Total Time</th><th>Rows</th></tr>"
    for no, row in enumerate(stats_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"
    html += "</table>"

    html += "<h2>Database Stats</h2><table border=1>"
    html += "<tr><th>No.</th><th>DB</th><th>Commits</th><th>Rollbacks</th><th>Reads</th><th>Hits</th><th>Cache Hit %</th></tr>"
    for no, row in enumerate(live_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td>{row[5]}</td></tr>"
    html += "</table>"

    html += "<h2>Table Scans</h2><table border=1>"
    html += "<tr><th>No.</th><th>Table</th><th>Seq Scan</th><th>Idx Scan</th><th>Live Rows</th><th>Dead Rows</th></tr>"
    for no, row in enumerate(scan_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"
    html += "</table>"

    html += "<h2>Index Usage</h2><table border=1>"
    html += "<tr><th>No.</th><th>Index</th><th>Table</th><th>Scans</th></tr>"
    for no, row in enumerate(idx_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>"
    html += "</table>"

    html += "<h2>IO Stats</h2><table border=1>"
    html += "<tr><th>No.</th><th>Table</th><th>Disk Reads</th><th>Cache Hits</th></tr>"
    for no, row in enumerate(statio_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>"
    html += "</table>"

    html += "<h2>Live Queries</h2><table border=1>"
    html += "<tr><th>No.</th><th>PID</th><th>User</th><th>State</th><th>Query</th><th>Duration</th></tr>"
    for no, row in enumerate(activity_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"
    html += "</table>"

    html += "<h2>Locks</h2><table border=1>"
    html += "<tr><th>No.</th><th>PID</th><th>Type</th><th>Relation</th><th>Mode</th><th>Granted</th></tr>"
    for no, row in enumerate(locks_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"
    html += "</table>"

    html += "<h2>Indexes</h2><table border=1>"
    html += "<tr><th>No.</th><th>Table</th><th>Index</th><th>Definition</th></tr>"
    for no, row in enumerate(indexes_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>"
    html += "</table>"

    html += "<h2>Extensions</h2><table border=1>"
    html += "<tr><th>No.</th><th>Name</th><th>Version</th></tr>"
    for no, row in enumerate(extensions_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td></tr>"
    html += "</table>"

    html += "<h2>Buffer Cache</h2><table border=1>"
    html += "<tr><th>No.</th><th>Table</th><th>Buffers</th></tr>"
    for no, row in enumerate(cache_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td></tr>"
    html += "</table>"

    html += "</body></html>"
    return html

def start(cli_db_url=None):
    global conn, db_error, setup_messages, stats_data, live_data, scan_data, idx_data, statio_data, activity_data, locks_data, indexes_data, extensions_data, cache_data

    db_url = get_db_url(cli_db_url)

    if not db_url:
        db_error = "No DB URL provided (CLI or ENV)"
        return

    try:
        conn = connect(db_url)
        setup_messages = setup_database(conn)
        stats_data = load_stats(conn)
        live_data = load_live(conn)
        scan_data = load_scan(conn)
        idx_data = load_idx(conn)
        statio_data = load_statio(conn)
        activity_data = load_activity(conn)
        locks_data = load_locks(conn)
        indexes_data = load_indexes(conn)
        extensions_data = load_extensions(conn)
        cache_data = load_cache(conn)
    except Exception as e:
        db_error = str(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url")
    args = parser.parse_args()

    start(args.db_url)
    app.run(host="0.0.0.0", port=5000)