# Demo scripts — PG Inspector

Skrypty w tym katalogu budują schemat **`demo`** i generują problemy widoczne w dashboardzie. Użyj ich razem z [/docs](http://localhost:5001/docs) (wyszukiwarka u góry).

## Docker — jak odpalać

**Z hosta (WSL)**, gdy działa `docker compose up`:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_DB=mydb
```

**Z kontenera aplikacji:**

```bash
docker compose exec db-inspector bash
# POSTGRES_HOST=postgres jest już ustawione
python scripts/demo_init.py
```

Pliki SQL:

```bash
python scripts/demo_run_sql.py demo_triggers.sql
```

---

## Jednorazowy setup (przed prezentacją)

Uruchom **raz**, w tej kolejności:

```bash
python scripts/demo_init.py
python scripts/demo_run_sql.py demo_triggers.sql
python scripts/demo_run_sql.py demo_index_usage.sql
python scripts/demo_run_sql.py demo_db_sizes.sql
python scripts/demo_run_sql.py demo_extensions.sql
```

Skala: `demo_init.py --scale medium` (domyślnie ≈ 500k studentów). Także: `small`, `large`.

---

## Instrukcja per panel

Dla każdego panelu: **odpal skrypt → Refresh w dashboardzie → sprawdź sygnały → w /docs wpisz keyword**.

---

### Top Queries

| | |
|---|---|
| **Odpal** | `python scripts/demo_top_queries.py --fresh` |
| **Panel** | Queries → **Top Queries** → **↺ Refresh** |
| **Na co patrzeć** | Na górze listy: `SELECT count(*) FROM demo.student WHERE search_token = …` — wysoki **Total (ms)** i **Mean (ms)**. Kliknij **Analyze** → w drzewie **Seq Scan** na dużej tabeli. |
| **Docs — wpisz** | `top queries`, `slow`, `analyze`, `sequential scan` |

**Wymaga wcześniej:** setup + `demo_index_usage.sql` (indeks na `email` do porównania w Analyze).

---

### Query Plan (EXPLAIN) — okno z Top Queries

| | |
|---|---|
| **Odpal** | Najpierw `demo_top_queries.py --fresh`, potem w panelu **Analyze** na wolnym SELECT |
| **Panel** | Top Queries → **Analyze** → zakładki Tree / With Indexes / Without Indexes |
| **Na co patrzeć** | Tree: węzły z **czerwoną/żółtą** obwódką (wysoki cost). Without Indexes vs With Indexes — różnica kosztu seq scan vs index scan. |
| **Docs — wpisz** | `explain`, `analyze`, `sequential scan`, `index` |

---

### Table Health

| | |
|---|---|
| **Odpal** | `python scripts/demo_table_health.py` |
| **Panel** | Storage → **Table Health** → **↺ Refresh** |
| **Na co patrzeć** | Tabela **`bloat_table`**: **czerwony** badge **Dead %** (~33%). Karty u góry: **Bloated Tables** (czerwona liczba > 0). Opcjonalnie niski **Cache Hit** na `student`. |
| **Docs — wpisz** | `dead tuples`, `VACUUM`, `bloat`, `table health`, `cache hit` |

**Wymaga wcześniej:** setup + `demo_db_sizes.sql` (autovacuum wyłączony na `bloat_table`).

**Anomaly log:** po ~5–60 s sprawdź `logs/db_anomalies.jsonl` — wpis `dead_tuples`. Docs: `anomaly`.

---

### DB Sizes

| | |
|---|---|
| **Odpal** | Setup wystarczy (`demo_init.py` + `demo_db_sizes.sql`) — nic extra przed demo |
| **Panel** | Storage → **DB Sizes** → **↺ Refresh** |
| **Na co patrzeć** | **`demo.size_data`**: **fioletowy** pasek (indeksy) większy niż **cyan** (dane) — index overhead ~90%. Duże **`demo.student`** / **`demo.enrollment`**. |
| **Docs — wpisz** | `DB sizes`, `index overhead`, `disk` |

---

### Index Usage

| | |
|---|---|
| **Odpal** | Setup: `demo_index_usage.sql` (bez dodatkowego skryptu Python) |
| **Panel** | Indexes → **Index Usage** → **↺ Refresh** |
| **Na co patrzeć** | Baner **Duplicate Indexes Detected** (`demo.student`, `demo.size_data`). Badge **Unused** (czerwony) na `idx_demo_student_gender_unused`, indeksach `size_payload_*`. Badge **Duplicate** (żółty) na `idx_demo_student_dup_*`. |
| **Docs — wpisz** | `unused`, `duplicate`, `DROP INDEX`, `index usage` |

**Opcjonalnie:** `demo_top_queries.py --fresh` — indeks `idx_demo_student_email_used` zacznie mieć scans > 0.

---

### Lock Monitor

| | |
|---|---|
| **Odpal** | `python scripts/demo_locks.py --duration 45` |
| **Panel** | Runtime → **Lock Monitor** → **↺ Refresh** *podczas* działania skryptu (masz ~45 s na scenariusz) |
| **Na co patrzeć** | Sekcja **Blocking Locks**: czerwone karty, strzałka blocker → blocked, **Wait time** rośnie. **Active Queries**: długi **Duration** (żółty). Po zakończeniu skryptu: zielony tekst *No blocking locks*. |
| **Docs — wpisz** | `lock`, `blocked`, `idle in transaction`, `pg_cancel_backend` |

Tryby: `--mode row`, `idle`, `both` (domyślnie oba scenariusze).

---

### Triggers

| | |
|---|---|
| **Odpal** | `python scripts/demo_run_sql.py demo_triggers.sql` (w setup) |
| **Panel** | Trgrs → **Triggers** → **↺ Refresh** |
| **Na co patrzeć** | **`demo_audit_trigger`** → badge **ENABLED** (zielony). **`demo_legacy_sync_trigger`** → badge **DISABLED** (czerwony) — kandydat do usunięcia po weryfikacji. |
| **Docs — wpisz** | `trigger`, `DISABLED`, `ENABLED`, `slow writes` |

---

### Extensions

| | |
|---|---|
| **Odpal** | `python scripts/demo_run_sql.py demo_extensions.sql` (w setup) |
| **Panel** | System → **Extensions** → **↺ Refresh** |
| **Na co patrzeć** | **`pg_trgm`** na liście (oprócz `pg_stat_statements`, `plpgsql`). |
| **Docs — wpisz** | `extensions`, `CREATE EXTENSION`, `pg_stat_statements` |

---

### Anomaly Log (panel + plik w tle)

| | |
|---|---|
| **Odpal** | `python scripts/demo_table_health.py` i/lub `python scripts/demo_locks.py --duration 45` |
| **Panel** | Runtime → **Anomaly Log** → **↺ Refresh** |
| **Na co patrzeć** | Lista zdarzeń: timestamp, severity (badge), type, message, szczegóły JSON |
| **Docs — wpisz** | `anomaly`, `dead tuples`, `blocked`, `configuration` |

---

## Szybka ściąga — keyword → panel

| Szukasz w docs | Panel | Skrypt |
|----------------|-------|--------|
| `slow` / `top queries` | Top Queries | `demo_top_queries.py --fresh` |
| `analyze` / `sequential scan` | Top Queries → Analyze | ↑ |
| `dead tuples` / `VACUUM` | Table Health | `demo_table_health.py` |
| `DB sizes` / `index overhead` | DB Sizes | setup |
| `unused` / `duplicate` | Index Usage | setup (`demo_index_usage.sql`) |
| `lock` / `blocked` | Lock Monitor | `demo_locks.py --duration 45` |
| `trigger` / `DISABLED` | Triggers | setup (`demo_triggers.sql`) |
| `extensions` | Extensions | setup (`demo_extensions.sql`) |
| `anomaly` | log + Table Health / Locks | `demo_table_health.py` |

---

## Legacy

Stare skrypty (schemat `public`): katalog **`legacy/`**.
