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
        print(f"[{threading.current_thread().name}] Wykonywanie...")
        cur.execute(query)
        if sleep_after > 0:
            print(f"[{threading.current_thread().name}] Usypianie na {sleep_after}s (trzymam locka!)...")
            time.sleep(sleep_after)
        conn.commit()
        print(f"[{threading.current_thread().name}] Zakończono (Commit).")
    except Exception as e:
        print(f"[{threading.current_thread().name}] Błąd: {e}")
        conn.rollback()
    finally:
        conn.close()

def simulate_background_traffic():
    """Generuje ciągły ruch zapychający statystyki pg_stat_statements"""
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    while True:
        try:
            cur.execute("SELECT * FROM student_kierunek_v LIMIT 50;")
            cur.execute(f"UPDATE przedmiot SET ects = {random.randint(1,10)} WHERE id = 5;")
            cur.execute("SELECT count(*) FROM zapisy_na_przedmioty;")
            time.sleep(0.5)
        except:
            pass

def simulate_row_lock():
    print("\n--- SCENARIUSZ 1: Deadlock / Row-level Lock na studencie (15s) ---")

    def blocker():
        run_query("UPDATE student SET srednia_ocen = 5.0 WHERE numer_indeksu = 123456;", sleep_after=15)

    def victim():
        time.sleep(2)
        run_query("UPDATE student SET imie = 'Locked' WHERE numer_indeksu = 123456;")

    t1 = threading.Thread(target=blocker, name="RowBlocker")
    t2 = threading.Thread(target=victim, name="RowVictim")
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def simulate_table_lock():
    print("\n--- SCENARIUSZ 2: Table-level Lock na zapisach (15s) ---")

    def blocker():
        run_query("LOCK TABLE zapisy_na_przedmioty IN ACCESS EXCLUSIVE MODE;", sleep_after=15)

    def victim():
        time.sleep(2)
        run_query("INSERT INTO zapisy_na_przedmioty (student_id, przedmiot_id) VALUES (123456, 5);")

    t1 = threading.Thread(target=blocker, name="TableBlocker")
    t2 = threading.Thread(target=victim, name="TableVictim")
    t1.start()
    t2.start()
    t1.join()
    t2.join()

if __name__ == "__main__":
    print("Rozpoczęcie symulacji bazy danych.")

    traffic_thread = threading.Thread(target=simulate_background_traffic, daemon=True)
    traffic_thread.start()

    simulate_row_lock()
    time.sleep(2)
    simulate_table_lock()

    print("\nKoniec blokad. Przez chwilę zapytania tła jeszcze generują ruch dla statystyk.")
    time.sleep(5)
