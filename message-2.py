import os
import time
import threading
import psycopg2
from db import get_db_url

# Pobieranie URL bazy danych w ten sam sposób co apliakcja
DB_URL = get_db_url(os.getenv("DATABASE_URL")) or "postgresql://postgres:postgres@localhost:5432/mydb"

def run_query(query, sleep_after=0):
    """Pomocnicza funkcja do uruchamiania zapytań z opcjonalnym usypianiem trzymając transakcję"""
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        print(f"[{threading.current_thread().name}] Executing: {query}")
        cur.execute(query)
        
        if sleep_after > 0:
            print(f"[{threading.current_thread().name}] Sleeping for {sleep_after} seconds (holding lock)...")
            time.sleep(sleep_after)
            
        conn.commit()
        print(f"[{threading.current_thread().name}] Committed.")
    except Exception as e:
        print(f"[{threading.current_thread().name}] Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def setup_db():
    print("Setting up test table...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS lock_demo (id INT PRIMARY KEY, value TEXT);")
    cur.execute("INSERT INTO lock_demo (id, value) VALUES (1, 'initial') ON CONFLICT (id) DO NOTHING;")
    conn.close()
    print("Table setup completed.\n")

def simulate_row_lock():
    print(">>> SCENARIO 1: Row-level Lock (UPDATE vs UPDATE) <<<")
    print("Sprawdź zakładkę monitorowania blokad w aplikacji WWW (przez ok. 15 sekund).")
    
    def blocker():
        run_query("UPDATE lock_demo SET value = 'row_locked' WHERE id = 1;", sleep_after=15)
        
    def victim():
        time.sleep(2) # Dajemy chwilę pierwszemu wątkowi na zajęcie wiersza
        print(f"[{threading.current_thread().name}] Próba aktualizacji zablokowanego wiersza - powinno zawisnąć...")
        run_query("UPDATE lock_demo SET value = 'victim_update' WHERE id = 1;")

    t1 = threading.Thread(target=blocker, name="Blocker-Row")
    t2 = threading.Thread(target=victim, name="Victim-Row")
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print(">>> SCENARIO 1: Completed <<<\n")

def simulate_table_lock():
    print(">>> SCENARIO 2: Table-level Lock (ACCESS EXCLUSIVE vs SELECT) <<<")
    print("Sprawdź zakładkę monitorowania blokad w aplikacji WWW (przez ok. 15 sekund).")
    
    def blocker():
        run_query("LOCK TABLE lock_demo IN ACCESS EXCLUSIVE MODE;", sleep_after=15)
        
    def victim():
        time.sleep(2)
        print(f"[{threading.current_thread().name}] Próba wykonania SELECT na zablokowanej tabeli - powinno zawisnąć...")
        run_query("SELECT * FROM lock_demo;")

    t1 = threading.Thread(target=blocker, name="Blocker-Table")
    t2 = threading.Thread(target=victim, name="Victim-Table")
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print(">>> SCENARIO 2: Completed <<<\n")

if __name__ == "__main__":
    setup_db()
    
    print("Uruchamianie symulacji blokad bazy danych.")
    print("W trakcie ich działania, Endpoint /api/locks powinien zwrócić odpowiednie rekordy.")
    print("-" * 50)
    
    simulate_row_lock()
    time.sleep(2)
    simulate_table_lock()
    
    print("Wszystkie symulacje zakończone.")