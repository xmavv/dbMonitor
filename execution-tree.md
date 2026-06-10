# Dokumentacja i Analiza Zapytań Diagnostycznych PostgreSQL

Niniejsza notatka zawiera szczegółową analizę sześciu zapytań SQL służących do monitorowania wydajności, statystyk oraz stanu blokad w bazie danych PostgreSQL.

---

## 1. Statystyki Operacyjne Tabel (`pg_stat_user_tables`)
```sql
SELECT
schemaname,
relname AS table_name,
n_live_tup,
n_dead_tup,
CASE WHEN n_live_tup > 0
THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 2)
ELSE 0
END AS dead_ratio_pct,
seq_scan,
idx_scan,
CASE WHEN (seq_scan + idx_scan) > 0
THEN round(100.0 * idx_scan / (seq_scan + idx_scan), 2)
ELSE 0
END AS idx_ratio_pct,
n_tup_ins,
n_tup_upd,
n_tup_del,
last_vacuum,
last_autovacuum,
last_analyze,
last_autoanalyze,
pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS total_size,
pg_total_relation_size(schemaname||'.'||relname) AS total_size_bytes
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC;
```
### Opis
Zapytanie służy do monitorowania "zdrowia" tabel użytkownika. Pozwala zidentyfikować tabele z dużą ilością "martwych krotek" (dead tuples), co wskazuje na potrzebę próżniowania (*VACUUM*) oraz ocenić efektywność indeksowania.

### Elementy Zapytania i Zwracane Wartości:
* **`n_live_tup` / `n_dead_tup`**: Liczba żywych i martwych rekordów. Martwe rekordy to stare wersje wierszy pozostałe po operacjach `UPDATE` lub `DELETE`.
* **`dead_ratio_pct`**: Procentowy udział martwych wierszy. Jeśli przekracza 10-20%, tabela może wymagać częstszego *Autovacuum*.
* **`seq_scan` vs `idx_scan`**: Liczba skanowań sekwencyjnych (cała tabela) vs skanowań po indeksie.
* **`idx_ratio_pct`**: Skuteczność użycia indeksów. Niska wartość na dużych tabelach sugeruje brak optymalnych indeksów.
* **`last_vacuum` / `last_analyze`**: Daty ostatnich procesów czyszczenia i zbierania statystyk planisty.

---

## 2. Wydajność Pamięci Cache (`pg_statio_user_tables`)
```sql
SELECT
    relname AS table_name,
    heap_blks_read,
    heap_blks_hit,
    CASE WHEN (heap_blks_hit + heap_blks_read) > 0
        THEN round(100.0 * heap_blks_hit / (heap_blks_hit + heap_blks_read), 2)
        ELSE NULL
    END AS cache_hit_pct,
    idx_blks_read,
    idx_blks_hit,
    CASE WHEN (idx_blks_hit + idx_blks_read) > 0
        THEN round(100.0 * idx_blks_hit / (idx_blks_hit + idx_blks_read), 2)
        ELSE NULL
    END AS idx_cache_hit_pct
FROM pg_statio_user_tables
WHERE (heap_blks_hit + heap_blks_read) > 0
ORDER BY heap_blks_read DESC;
```
### Opis
To zapytanie sprawdza efektywność pamięci podręcznej (*Buffer Cache*) dla danych tabeli i jej indeksów.

### Elementy Zapytania i Zwracane Wartości:
* **`heap_blks_read` / `heap_blks_hit`**: Liczba bloków odczytanych z dysku vs liczba bloków znalezionych w pamięci RAM (*shared buffers*).
* **`cache_hit_pct`**: Współczynnik trafień cache. W dobrze zoptymalizowanych systemach powinien wynosić > 95-99%.
* **`idx_cache_hit_pct`**: Efektywność cache dla samych indeksów.

---

## 3. Wykrywanie Blokad (Locks)

```sql
SELECT
    bl.pid AS blocked_pid,
    ba.usename AS blocked_user,
    ba.query AS blocked_query,
    ba.query_start AS blocked_query_start,
    kl.pid AS blocking_pid,
    ka.usename AS blocking_user,
    ka.query AS blocking_query,
    ka.query_start AS blocking_query_start,
    bl.locktype,
    bl.relation::regclass AS relation,
    extract(epoch FROM (now() - ba.query_start))::int AS wait_seconds
FROM pg_catalog.pg_locks bl
JOIN pg_catalog.pg_stat_activity ba ON bl.pid = ba.pid
JOIN pg_catalog.pg_locks kl ON kl.transactionid = bl.transactionid AND kl.pid != bl.pid
JOIN pg_catalog.pg_stat_activity ka ON kl.pid = ka.pid
WHERE NOT bl.granted
ORDER BY wait_seconds DESC;
```
### Opis
Najbardziej złożone z zestawu zapytanie, które łączy tabelę systemową blokad (`pg_locks`) z aktywnością sesji (`pg_stat_activity`), aby pokazać, który proces blokuje inny proces.

### Budowa i Logika:
Zapytanie wykonuje **Self-Join** (złączenie tabeli samej ze sobą) na `pg_locks`:
1.  **`bl` (Blocked Lock)**: Szuka blokad, które nie zostały przyznane (`NOT granted`).
2.  **`kl` (Key Lock/Blocking)**: Szuka blokad na tym samym obiekcie (ten sam `transactionid`), które trzymają inne procesy.
3.  **`ba` i `ka`**: Dołączają informacje o użytkowniku i treści zapytania dla obu stron konfliktu.

### Zwracane Wartości:
* **`blocked_pid` / `blocking_pid`**: ID procesów czekającego i blokującego.
* **`wait_seconds`**: Czas trwania blokady w sekundach.

---

## 4. Aktywne Sesje i Długie Zapytania (`pg_stat_activity`)

```sql
SELECT
    pid,
    usename,
    application_name,
    state,
    wait_event_type,
    wait_event,
    query,
    query_start,
    extract(epoch FROM (now() - query_start))::int AS duration_seconds,
    client_addr
FROM pg_stat_activity
WHERE state != 'idle'
  AND pid != pg_backend_pid()
ORDER BY query_start ASC;
```
### Opis
Zapewnia wgląd w czasie rzeczywistym w to, co aktualnie robi baza danych.

### Elementy Zapytania i Zwracane Wartości:
* **`state`**: Stan sesji (np. `active`, `idle in transaction`). Szczególnie niebezpieczne jest `idle in transaction`, które może trzymać blokady.
* **`wait_event_type` / `wait_event`**: Informacja, na co proces czeka (np. na I/O dysku, na sieć, na blokadę).
* **`duration_seconds`**: Obliczane jako różnica między `now()` a `query_start`. Pozwala wykryć "wiszące" zapytania.

---

## 5. Analiza Rozmiaru i Narzutu Indeksów

```sql
SELECT
    schemaname,
    relname AS table_name,
    pg_size_pretty(pg_relation_size(schemaname||'.'||relname)) AS table_size,
    pg_relation_size(schemaname||'.'||relname) AS table_size_bytes,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||relname)) AS indexes_size,
    pg_indexes_size(schemaname||'.'||relname) AS indexes_size_bytes,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS total_size,
    pg_total_relation_size(schemaname||'.'||relname) AS total_size_bytes,
    CASE WHEN pg_relation_size(schemaname||'.'||relname) > 0
        THEN round(100.0 * pg_indexes_size(schemaname||'.'||relname) / pg_total_relation_size(schemaname||'.'||relname), 1)
        ELSE 0
    END AS index_overhead_pct
FROM pg_stat_user_tables
ORDER BY total_size_bytes DESC;
```
### Opis
Zapytanie analizuje fizyczny rozmiar tabel oraz to, jaką część całkowitej wielkości zajmują indeksy (*index overhead*).

### Funkcje Systemowe:
* **`pg_relation_size`**: Rozmiar samej tabeli (bez indeksów).
* **`pg_indexes_size`**: Łączny rozmiar wszystkich indeksów danej tabeli.
* **`pg_total_relation_size`**: Tabela + Indeksy + TOAST (dodatkowe dane).
* **`pg_size_pretty`**: Formatuje bajty na czytelne jednostki (kB, MB, GB).

### Kluczowa Wartość:
* **`index_overhead_pct`**: Jeśli indeksy zajmują znacznie więcej niż tabela (np. > 60-70%), warto sprawdzić, czy wszystkie są używane lub czy nie nastąpiło ich nadmierne spuchnięcie (*bloat*).

---

## 6. Wykrywanie Zduplikowanych Indeksów (`pg_index`)

```sql
SELECT
    indrelid::regclass AS table_name,
    array_agg(indexrelid::regclass::text ORDER BY indexrelid::regclass::text) AS indexes,
    array_agg(pg_size_pretty(pg_relation_size(indexrelid)) ORDER BY indexrelid::regclass::text) AS sizes,
    pg_get_expr(indexprs, indrelid) AS expressions,
    array_agg(pg_relation_size(indexrelid)) AS size_bytes
FROM pg_index
GROUP BY indrelid, indkey, indexprs, indpred
HAVING count(*) > 1
ORDER BY table_name;
```
### Opis
Identyfikuje tabele, które mają więcej niż jeden indeks na tych samych kolumnach lub wyrażeniach. Zduplikowane indeksy spowalniają operacje `INSERT/UPDATE` i marnują miejsce.

### Logika Budowy:
* **`indkey`**: Wewnętrzna reprezentacja kolumn indeksu.
* **`GROUP BY indrelid, indkey... HAVING count(*) > 1`**: Grupuje indeksy o tych samych parametrach. Jeśli licznik jest większy niż 1, mamy do czynienia z duplikacją.
* **`array_agg`**: Agreguje nazwy i rozmiary zduplikowanych indeksów w czytelną listę (tablicę).

---

## Podsumowanie Funkcji i Typów Danych

| Element | Wyjaśnienie |
| :--- | :--- |
| **`regclass`** | Typ danych rzutujący OID (Internal ID) na czytelną nazwę tabeli. |
| **`epoch`** | Wyciąga całkowitą liczbę sekund z interwału czasu. |
| **`pg_catalog`** | Schemat systemowy, w którym przechowywane są metadane. |
| **`CASE WHEN`** | Konstrukcja warunkowa zapobiegająca np. dzieleniu przez zero. |