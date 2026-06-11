import psycopg2
import time
import os
import threading

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "mydb")

def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )

def setup_structural_anomalies():
    print("Setting up structural anomalies...")
    conn = get_conn()
    conn.autocommit = True
    cur = conn.cursor()
    
    # 1. High index overhead
    print("- Creating high index overhead...")
    cur.execute("DROP TABLE IF EXISTS index_heavy;")
    cur.execute("CREATE TABLE index_heavy (id serial, val text);")
    cur.execute("INSERT INTO index_heavy (val) SELECT md5(random()::text) FROM generate_series(1, 10000);")
    for i in range(20):
        cur.execute(f"CREATE INDEX idx_heavy_{i} ON index_heavy(val);")
        
    # 2. Large table for unused indexes and dead tuples
    print("- Creating large table for empty scans and dead tuples...")
    cur.execute("DROP TABLE IF EXISTS anomaly_test;")
    cur.execute("CREATE TABLE anomaly_test (id serial, val1 text, val2 text);")
    cur.execute("INSERT INTO anomaly_test (val1, val2) SELECT md5(random()::text), md5(random()::text) FROM generate_series(1, 200000);")
    cur.execute("ALTER TABLE anomaly_test SET (autovacuum_enabled = false);")
    
    # duplicate indexes and unused large index
    cur.execute("CREATE INDEX idx_dup1 ON anomaly_test(val1);")
    cur.execute("CREATE INDEX idx_dup2 ON anomaly_test(val1);")
    cur.execute("CREATE INDEX idx_large_unused ON anomaly_test(val2);")
    cur.execute("ANALYZE anomaly_test;")
    
    # 3. Create dead tuples
    print("- Creating dead tuples...")
    cur.execute("UPDATE anomaly_test SET val2 = 'dead' WHERE id <= 100000;")
    
    # 4. Low cache hit
    print("- Inducing sequential scans to trigger low cache hits...")
    cur.execute("DROP TABLE IF EXISTS flush_cache;")
    cur.execute("CREATE TABLE flush_cache (val text);")
    cur.execute("INSERT INTO flush_cache SELECT md5(random()::text) FROM generate_series(1, 1000000);")
    
    # Reset stats so new reads are guaranteed to be the baseline
    cur.execute("SELECT pg_stat_reset();")
    cur.execute("SELECT pg_stat_statements_reset();")
    
    # Scan the large table to force disk reads and lower the cache hit ratio
    cur.execute("SELECT count(*) FROM flush_cache;")
    # Scan index to force index disk reads
    cur.execute("SET enable_seqscan = off;")
    cur.execute("SELECT count(*) FROM anomaly_test WHERE val1 > 'a';")
    cur.execute("SET enable_seqscan = on;")
    
    cur.close()
    conn.close()

def simulate_long_query():
    print("Starting long query simulation (>30s)...")
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT pg_sleep(35);")
        cur.close()
        conn.close()
        print("Long query finished.")
    except Exception as e:
        print("Long query error:", e)

def simulate_blocking():
    print("Starting blocking simulation (~6s)...")
    conn1 = get_conn()
    conn2 = get_conn()
    conn1.autocommit = False
    conn2.autocommit = False
    
    cur1 = conn1.cursor()
    cur1.execute("BEGIN;")
    cur1.execute("UPDATE anomaly_test SET val1 = 'lock1' WHERE id = 1;")
    
    def block_query():
        cur2 = conn2.cursor()
        print("Executing blocked query...")
        try:
            cur2.execute("UPDATE anomaly_test SET val1 = 'lock2' WHERE id = 1;")
        except Exception as e:
            pass
        cur2.close()
        conn2.close()
        
    t = threading.Thread(target=block_query)
    t.start()
    
    # default lock_wait_seconds is 5 in app
    time.sleep(6)
    cur1.execute("COMMIT;")
    cur1.close()
    conn1.close()
    t.join()
    print("Blocking simulation finished.")

if __name__ == "__main__":
    setup_structural_anomalies()
    
    t_long = threading.Thread(target=simulate_long_query)
    t_long.start()
    
    simulate_blocking()
    
    # Wait for the long query so script doesn't exit immediately
    print("Waiting for long query to finish...")
    t_long.join()
    print("All anomaly simulations triggered! You can check logs/db_anomalies.jsonl after 5 seconds.")

