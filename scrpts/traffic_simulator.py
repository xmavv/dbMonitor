import time
import threading
import random
import os
import psycopg2

def get_db_url():
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "mydb")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


DB_URL = get_db_url()

def run_query(query, sleep_after=0):
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        print(f"[{threading.current_thread().name}] Executing...")
        cur.execute(query)
        if sleep_after > 0:
            print(f"[{threading.current_thread().name}] Sleeping for {sleep_after}s (holding lock!)...")
            time.sleep(sleep_after)
        conn.commit()
        print(f"[{threading.current_thread().name}] Done (Commit).")
    except Exception as e:
        print(f"[{threading.current_thread().name}] Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def simulate_background_traffic():
    """Generates continuous traffic that fills up pg_stat_statements"""
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    while True:
        try:
            cur.execute("SELECT * FROM student_program_v LIMIT 50;")
            cur.execute(f"UPDATE course SET ects = {random.randint(1,10)} WHERE id = 5;")
            cur.execute("SELECT count(*) FROM enrollment;")
            time.sleep(0.5)
        except:
            pass

def simulate_row_lock():
    print("\n--- SCENARIO 1: Deadlock / Row-level Lock on student (15s) ---")

    def blocker():
        run_query("UPDATE student SET gpa = 5.0 WHERE index_number = 123456;", sleep_after=15)

    def victim():
        time.sleep(2)
        run_query("UPDATE student SET first_name = 'Locked' WHERE index_number = 123456;")

    t1 = threading.Thread(target=blocker, name="RowBlocker")
    t2 = threading.Thread(target=victim, name="RowVictim")
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def simulate_table_lock():
    print("\n--- SCENARIO 2: Table-level Lock on enrollment (15s) ---")

    def blocker():
        run_query("LOCK TABLE enrollment IN ACCESS EXCLUSIVE MODE;", sleep_after=15)

    def victim():
        time.sleep(2)
        run_query("INSERT INTO enrollment (student_id, course_id) VALUES (123456, 5);")

    t1 = threading.Thread(target=blocker, name="TableBlocker")
    t2 = threading.Thread(target=victim, name="TableVictim")
    t1.start()
    t2.start()
    t1.join()
    t2.join()

if __name__ == "__main__":
    print("Starting database simulation.")

    traffic_thread = threading.Thread(target=simulate_background_traffic, daemon=True)
    traffic_thread.start()

    simulate_row_lock()
    time.sleep(2)
    simulate_table_lock()

    print("\nLocks finished. Background queries keep generating traffic for stats for a moment.")
    time.sleep(5)
