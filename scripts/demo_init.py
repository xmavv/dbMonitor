#!/usr/bin/env python3
"""Create the demo schema and load a medium-scale dataset (~500k students by default)."""
import argparse
import random
import string
import sys
import time

import psycopg2.extras

from demo_db import connect, print_banner, run_sql_file

SCALES = {
    "small": {"students": 100_000, "programs": 200, "courses": 200, "bloat_rows": 50_000},
    "medium": {"students": 500_000, "programs": 500, "courses": 500, "bloat_rows": 150_000},
    "large": {"students": 1_000_000, "programs": 1000, "courses": 1000, "bloat_rows": 300_000},
}


def random_token(n=16):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def batch_insert(cur, sql, rows, page_size=5000):
    psycopg2.extras.execute_values(cur, sql, rows, page_size=page_size)


def load_programs(cur, count):
    rows = [(f"Program {i:04d}", random.randint(50, 500)) for i in range(1, count + 1)]
    batch_insert(
        cur,
        "INSERT INTO demo.program (name, student_count) VALUES %s",
        rows,
    )
    cur.execute("SELECT id FROM demo.program ORDER BY id")
    return [r[0] for r in cur.fetchall()]


def load_courses(cur, count):
    rows = [(f"Course {i:04d}", random.randint(2, 6)) for i in range(1, count + 1)]
    batch_insert(
        cur,
        "INSERT INTO demo.course (name, ects) VALUES %s",
        rows,
    )
    cur.execute("SELECT id FROM demo.course ORDER BY id")
    return [r[0] for r in cur.fetchall()]


def load_students(cur, count, program_ids):
    first = ["Jan", "Anna", "Piotr", "Maria", "Tomasz", "Ewa", "Kamil", "Zofia"]
    last = ["Kowalski", "Nowak", "Wisniewski", "Wojcik", "Kaminski", "Lewandowski"]
    batch = []
    for i in range(1, count + 1):
        fn = random.choice(first)
        ln = random.choice(last)
        batch.append(
            (
                i,
                fn,
                ln,
                f"user{i}@demo.local",
                f"tok_{random_token(12)}",
                random.choice(["M", "F"]),
                random.choice(program_ids),
                round(random.uniform(2.0, 5.0), 1),
            )
        )
        if len(batch) >= 5000:
            batch_insert(
                cur,
                """INSERT INTO demo.student
                   (id, first_name, last_name, email, search_token, gender, program_id, gpa)
                   VALUES %s""",
                batch,
            )
            batch.clear()
            if i % 50_000 == 0:
                print(f"  students: {i:,} / {count:,}")
    if batch:
        batch_insert(
            cur,
            """INSERT INTO demo.student
               (id, first_name, last_name, email, search_token, gender, program_id, gpa)
               VALUES %s""",
            batch,
        )


def load_enrollments(cur, student_count, course_ids):
    batch = []
    for sid in range(1, student_count + 1):
        batch.append((sid, random.choice(course_ids)))
        if len(batch) >= 5000:
            batch_insert(
                cur,
                "INSERT INTO demo.enrollment (student_id, course_id) VALUES %s",
                batch,
            )
            batch.clear()
            if sid % 50_000 == 0:
                print(f"  enrollments: {sid:,} / {student_count:,}")
    if batch:
        batch_insert(
            cur,
            "INSERT INTO demo.enrollment (student_id, course_id) VALUES %s",
            batch,
        )


def load_bloat_seed(cur, rows):
    print(f"  bloat_table seed rows: {rows:,}")
    cur.execute(
        """
        INSERT INTO demo.bloat_table (payload, marker)
        SELECT md5(random()::text || g::text), (random() * 1000)::int
        FROM generate_series(1, %s) AS g
        """,
        (rows,),
    )


def load_employees(cur, count=1000):
    batch = [
        (f"Emp{i}", f"Worker{i}") for i in range(1, count + 1)
    ]
    batch_insert(
        cur,
        "INSERT INTO demo.employee (first_name, last_name) VALUES %s",
        batch,
    )


def main():
    parser = argparse.ArgumentParser(description="Initialize demo schema and bulk data.")
    parser.add_argument(
        "--scale",
        choices=list(SCALES),
        default="medium",
        help="Dataset size (default: medium ≈ 500k students)",
    )
    args = parser.parse_args()
    cfg = SCALES[args.scale]

    print_banner(
        "PG Inspector — demo_init.py",
        [
            f"Scale: {args.scale}",
            f"Students: {cfg['students']:,}",
            "Schema: demo",
            "",
            "Next steps (in order):",
            "  psql ... -f scripts/demo_triggers.sql",
            "  psql ... -f scripts/demo_index_usage.sql",
            "  psql ... -f scripts/demo_db_sizes.sql",
            "  psql ... -f scripts/demo_extensions.sql",
            "",
            "Or run each via: python scripts/demo_run_sql.py demo_triggers.sql",
        ],
    )

    started = time.time()
    conn = connect()
    try:
        print("Resetting demo schema…")
        run_sql_file(conn, "demo_reset.sql")
        print("Creating tables…")
        run_sql_file(conn, "demo_schema.sql")

        conn.autocommit = False
        with conn.cursor() as cur:
            print("Loading lookup tables…")
            program_ids = load_programs(cur, cfg["programs"])
            course_ids = load_courses(cur, cfg["courses"])

            print("Loading students…")
            load_students(cur, cfg["students"], program_ids)

            print("Loading enrollments…")
            load_enrollments(cur, cfg["students"], course_ids)

            load_bloat_seed(cur, cfg["bloat_rows"])
            load_employees(cur, 1000)

            cur.execute("ANALYZE demo.student")
            cur.execute("ANALYZE demo.enrollment")
            cur.execute("ANALYZE demo.bloat_table")

        conn.commit()
        elapsed = time.time() - started
        print(f"\nDone in {elapsed:.1f}s.")
        print("Dashboard: refresh DB Sizes — look for demo.student / demo.enrollment.")
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
