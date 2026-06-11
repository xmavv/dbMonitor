#!/usr/bin/env python3
"""Create bloat + cache pressure for Table Health and anomaly log."""
import argparse
import sys
import time

from demo_db import connect, print_banner, require_schema


def main():
    parser = argparse.ArgumentParser(description="Induce table bloat and low cache hit signals.")
    parser.add_argument(
        "--reset-io-stats",
        action="store_true",
        help="Run pg_stat_reset() before cache test (affects whole DB stats)",
    )
    parser.add_argument("--seq-scans", type=int, default=30, help="Full table scans for cache miss")
    args = parser.parse_args()

    print_banner(
        "PG Inspector — demo_table_health.py",
        [
            "Docs keywords: dead tuples, VACUUM, bloat, cache hit, table health",
            "",
            "Requires: demo_init.py + demo_db_sizes.sql (autovacuum off on bloat_table)",
            "",
            "Check: Table Health → demo.bloat_table red dead %",
            "       Summary card 'Bloated Tables' may turn red",
            "       Cache hit badge may drop on demo.student after scans",
        ],
    )

    conn = connect()
    conn.autocommit = True
    require_schema(conn)

    try:
        with conn.cursor() as cur:
            cur.execute(
                "ALTER TABLE demo.bloat_table SET (autovacuum_enabled = false)"
            )

            print("Creating dead tuples (UPDATE ~50% of rows)…")
            cur.execute(
                """
                UPDATE demo.bloat_table
                SET payload = 'dead_' || md5(random()::text)
                WHERE id <= (SELECT max(id) / 2 FROM demo.bloat_table)
                """
            )
            updated = cur.rowcount
            print(f"  updated rows: {updated:,}")

            cur.execute("ANALYZE demo.bloat_table")

            if args.reset_io_stats:
                print("Resetting database IO stats (pg_stat_reset)…")
                cur.execute("SELECT pg_stat_reset()")

            print(f"Running {args.seq_scans} sequential scans on demo.student…")
            cur.execute("SELECT id FROM demo.student WHERE id = 1")
            probe = cur.fetchone()[0]
            for i in range(args.seq_scans):
                cur.execute(
                    "SELECT count(*) FROM demo.student WHERE search_token LIKE %s",
                    ("tok_%",),
                )
                cur.fetchone()
                if (i + 1) % 10 == 0:
                    print(f"  scan {i + 1}/{args.seq_scans}")

            cur.execute(
                """
                SELECT relname,
                       n_dead_tup,
                       n_live_tup,
                       round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2)
                FROM pg_stat_user_tables
                WHERE schemaname = 'demo' AND relname = 'bloat_table'
                """
            )
            stat = cur.fetchone()
            if stat:
                print(
                    f"\nbloat_table stats: dead={stat[1]:,} live={stat[2]:,} dead_ratio={stat[3]}%"
                )

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

    print("\nOpen dashboard → Table Health → Refresh.")
    print("Anomaly log: check logs/db_anomalies.jsonl within ~5–60s.")
    print("Search docs for: dead tuples")


if __name__ == "__main__":
    main()
