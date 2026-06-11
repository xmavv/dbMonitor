#!/usr/bin/env python3
"""Run a demo .sql file using project DB env vars."""
import argparse
import sys

from demo_db import connect, print_banner, run_sql_file


def main():
    parser = argparse.ArgumentParser(description="Execute a demo SQL file.")
    parser.add_argument("sql_file", help="e.g. demo_triggers.sql")
    args = parser.parse_args()

    print_banner(f"Running {args.sql_file}")
    conn = connect()
    try:
        run_sql_file(conn, args.sql_file)
        print("OK")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
