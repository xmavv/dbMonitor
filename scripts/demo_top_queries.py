#!/usr/bin/env python3
"""Generate expensive queries for Top Queries + EXPLAIN demo."""
import argparse
import sys
import time

from demo_db import connect, print_banner, require_schema


def main():
    parser = argparse.ArgumentParser(description="Run slow + fast demo queries.")
    parser.add_argument("--slow-runs", type=int, default=400, help="Seq-scan count (default 400)")
    parser.add_argument("--fast-runs", type=int, default=50, help="Indexed lookup count")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Reset pg_stat_statements before running (recommended for demos)",
    )
    args = parser.parse_args()

    print_banner(
        "PG Inspector — demo_top_queries.py",
        [
            "Docs keywords: top queries, slow, analyze, sequential scan, index",
            "",
            "Requires: demo_init.py + demo_index_usage.sql",
            "",
            "Check: Top Queries → slow SELECT on demo.student (search_token)",
            "       Click Analyze → Seq Scan on large row count",
            "Tip: use --fresh to reset pg_stat_statements before the run",
        ],
    )

    conn = connect()
    require_schema(conn)

    slow_sql = "SELECT count(*) FROM demo.student WHERE search_token = %s"
    fast_sql = "SELECT id FROM demo.student WHERE email = %s LIMIT 1"

    with conn.cursor() as cur:
        if args.fresh:
            print("Resetting pg_stat_statements…")
            cur.execute("SELECT pg_stat_statements_reset()")

        cur.execute("SELECT search_token FROM demo.student WHERE id = 1")
        row = cur.fetchone()
        if not row:
            print("ERROR: demo.student is empty. Run demo_init.py first.", file=sys.stderr)
            sys.exit(1)
        token = row[0]
        email = "user1@demo.local"

        print(f"Running {args.slow_runs} slow seq-scan queries…")
        t0 = time.time()
        for i in range(args.slow_runs):
            cur.execute(slow_sql, (token,))
            cur.fetchone()
            if (i + 1) % 50 == 0:
                print(f"  slow: {i + 1}/{args.slow_runs}")
        slow_elapsed = time.time() - t0

        print(f"Running {args.fast_runs} indexed lookups…")
        for i in range(args.fast_runs):
            cur.execute(fast_sql, (email,))
            cur.fetchone()

    conn.commit()
    conn.close()

    print(f"\nFinished. Slow batch took {slow_elapsed:.1f}s.")
    print("Open dashboard → Top Queries → Refresh.")
    print("Search docs for: analyze")


if __name__ == "__main__":
    main()
