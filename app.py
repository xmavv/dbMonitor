import argparse
from flask import Flask
from db import get_db_url, connect, setup_database, load_stats

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
           <button type="submit">Odśwież statystyki</button>
       </form>
       """

    html += "<h2>Top Queries</h2><table border=1>"
    html += "<tr><th>No.</th><th>Query</th><th>Calls</th><th>Mean Time</th><th>Total Time</th><th>Rows</th></tr>"

    for no, row in enumerate(stats_data):
        html += f"<tr><td>{no}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"

    html += "</table></body></html>"
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
    app.run(host="0.0.0.0", port=5000)