import argparse
import html as html_module
from flask import Flask, request
from db import get_db_url, connect, setup_database, load_stats, load_indexes, explain_query

app = Flask(__name__)

conn = None
db_error = None
live_messages = []
setup_messages = []
stats_data = []

@app.route("/refresh", methods=["GET"])
def refresh():
    global stats_data, db_error
    try:
        stats_data = load_stats(conn)
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

    html = """
    <html>
    <body>
    """

    html += "<h1>DB Inspector</h1>"

    html += "<h2>Setup</h2><pre>"
    for msg in setup_messages:
        html += msg + "\n"
    html += "</pre>"

    html += """
       <form action="/refresh" method="get">
           <button type="submit">Refresh stats</button>
       </form>
       <p><a href="/indexes">View Index Usage</a></p>
       """

    html += "<h2>Top Queries</h2><table border=1>"
    html += "<tr><th>No.</th><th>Query</th><th>Calls</th><th>Mean Time</th><th>Total Time</th><th>Rows</th><th>Action</th></tr>"

    for no, row in enumerate(stats_data):
        queryid, query, calls, mean_time, total_time, rows = row
        escaped_query = html_module.escape(query)
        analyze_btn = ""
        if query.strip().upper().startswith("SELECT"):
            analyze_btn = f'''<form action="/analyze" method="post" style="margin:0">
                <input type="hidden" name="query" value="{escaped_query}">
                <button type="submit">Analyze</button>
            </form>'''
        html += f"<tr><td>{no}</td><td>{escaped_query}</td><td>{calls}</td><td>{mean_time:.2f}</td><td>{total_time:.2f}</td><td>{rows}</td><td>{analyze_btn}</td></tr>"

    html += "</table></body></html>"
    return html

@app.route("/indexes")
def indexes():
    if db_error:
        return f"<h1>DB ERROR</h1><pre>{db_error}</pre>"

    try:
        index_data = load_indexes(conn)
    except Exception as e:
        return f"<h1>Error loading indexes</h1><pre>{e}</pre>"

    html = "<html><body>"
    html += "<h1>Index Usage</h1>"
    html += '<p><a href="/">Back to queries</a></p>'
    html += "<table border=1>"
    html += "<tr><th>Schema</th><th>Table</th><th>Index</th><th>Scans</th><th>Tuples Read</th><th>Tuples Fetched</th><th>Size</th></tr>"

    for row in index_data:
        schema, table, index_name, scans, tup_read, tup_fetch, size = row
        style = ' style="background:#fdd"' if scans == 0 else ""
        html += f"<tr{style}><td>{schema}</td><td>{table}</td><td>{index_name}</td><td>{scans}</td><td>{tup_read}</td><td>{tup_fetch}</td><td>{size}</td></tr>"

    html += "</table>"
    html += "<p>Rows highlighted in red have 0 scans (potentially unused indexes).</p>"
    html += "</body></html>"
    return html


@app.route("/analyze", methods=["POST"])
def analyze():
    query = request.form.get("query", "")

    if not query.strip().upper().startswith("SELECT"):
        return "<h1>Error</h1><p>Only SELECT queries can be analyzed.</p><p><a href='/'>Back</a></p>"

    results = explain_query(conn, query)

    html = "<html><body>"
    html += "<h1>Query Analysis</h1>"
    html += f"<h3>Query</h3><pre>{html_module.escape(query)}</pre>"
    html += '<p><a href="/">Back to queries</a></p>'

    if "error" in results:
        html += f"<h2>Error</h2><pre>{html_module.escape(results['error'])}</pre>"
        html += "<p>This may happen with parameterized queries ($1, $2...) from pg_stat_statements.</p>"
        html += "</body></html>"
        return html

    html += "<table border=1 width='100%'><tr>"
    html += "<th width='50%'>With Indexes</th><th width='50%'>Without Indexes</th></tr><tr>"

    html += "<td><pre>"
    for line in results.get("with_index", []):
        html += html_module.escape(line) + "\n"
    html += "</pre></td>"

    html += "<td><pre>"
    if "without_index_error" in results:
        html += html_module.escape(results["without_index_error"])
    else:
        for line in results.get("without_index", []):
            html += html_module.escape(line) + "\n"
    html += "</pre></td>"

    html += "</tr></table></body></html>"
    return html


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url")
    args = parser.parse_args()

    start(args.db_url)
    app.run(host="0.0.0.0", port=5000, debug=True)