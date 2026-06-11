# Legacy scripts

These scripts targeted the original `public` schema (university sample). They are **superseded** by the `demo_*` scripts in the parent folder.

| File | Notes |
|------|-------|
| `script.sql` | Old schema bootstrap |
| `triggers_and_idx.sql` | Old triggers/indexes |
| `batch_data_inserter.py` | 10k rows per table in public schema |
| `traffic_simulator.py` | Locks + background traffic |
| `simulate_anomalies.py` | One-shot anomaly setup |
| `message-2.py` | Lock demo on `lock_demo` table |
| `random_pracownik.py` | Bulk employee insert |
| `test_queries.sql` | Manual SQL examples |

Use `../demo_init.py` and related scripts for presentations.
