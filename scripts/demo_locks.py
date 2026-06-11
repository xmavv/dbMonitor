#!/usr/bin/env python3
"""Hold row-level and idle-in-transaction locks for Lock Monitor demo."""
import argparse
import sys
import threading
import time

import psycopg2

from demo_db import connect, get_db_config, print_banner, require_schema


def hold_row_lock(db_config, duration):
    conn = psycopg2.connect(**db_config)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("UPDATE demo.lock_target SET val = 'blocking' WHERE id = 1")
        print(f"[blocker-row] Lock held for {duration}s — refresh Lock Monitor now")
        time.sleep(duration)
        conn.commit()
    finally:
        cur.close()
        conn.close()


def victim_row_lock(db_config, delay):
    time.sleep(delay)
    conn = psycopg2.connect(**db_config)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        print("[victim-row] Waiting on blocked row…")
        cur.execute("UPDATE demo.lock_target SET val = 'victim' WHERE id = 1")
        conn.commit()
    except Exception as exc:
        print(f"[victim-row] {exc}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def hold_idle_in_transaction(db_config, duration):
    conn = psycopg2.connect(**db_config)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute("UPDATE demo.lock_target SET val = 'idle_tx' WHERE id = 1")
        print(f"[idle-tx] Transaction open for {duration}s")
        time.sleep(duration)
        conn.commit()
    finally:
        cur.close()
        conn.close()


def victim_idle(db_config, delay):
    time.sleep(delay)
    conn = psycopg2.connect(**db_config)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        print("[victim-idle] Waiting on row locked by idle transaction…")
        cur.execute("UPDATE demo.lock_target SET val = 'victim2' WHERE id = 1")
        conn.commit()
    except Exception as exc:
        print(f"[victim-idle] {exc}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Simulate blocking locks.")
    parser.add_argument(
        "--duration",
        type=int,
        default=45,
        help="Seconds to hold each lock scenario (default 45)",
    )
    parser.add_argument(
        "--mode",
        choices=["row", "idle", "both"],
        default="both",
        help="Lock scenario to run",
    )
    args = parser.parse_args()

    print_banner(
        "PG Inspector — demo_locks.py",
        [
            "Docs keywords: lock, blocked, pg_cancel_backend, idle in transaction",
            "",
            "Requires: demo_init.py (demo.lock_target table)",
            "",
            f"Duration per scenario: {args.duration}s",
            "While this script runs → dashboard → Lock Monitor → Refresh",
        ],
    )

    conn = connect()
    require_schema(conn)
    conn.close()

    cfg = get_db_config()

    if args.mode in ("row", "both"):
        print("\n--- Scenario 1: row-level lock ---")
        t_block = threading.Thread(target=hold_row_lock, args=(cfg, args.duration))
        t_victim = threading.Thread(target=victim_row_lock, args=(cfg, 2))
        t_block.start()
        t_victim.start()
        t_block.join()
        t_victim.join()

    if args.mode == "both":
        time.sleep(2)

    if args.mode in ("idle", "both"):
        print("\n--- Scenario 2: idle in transaction ---")
        t_block = threading.Thread(target=hold_idle_in_transaction, args=(cfg, args.duration))
        t_victim = threading.Thread(target=victim_idle, args=(cfg, 2))
        t_block.start()
        t_victim.start()
        t_block.join()
        t_victim.join()

    print("\nDone. Lock Monitor should show green when idle.")
    print("Search docs for: blocked")


if __name__ == "__main__":
    main()
