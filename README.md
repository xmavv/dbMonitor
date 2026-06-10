# PG Inspector — Monitor i Analizator Bazy Danych PostgreSQL

**PG Inspector** to lekkie narzędzie webowe do monitorowania i analizy wydajności bazy danych **PostgreSQL**. Aplikacja udostępnia interaktywny panel (dashboard), który w czasie rzeczywistym prezentuje statystyki zapytań, kondycję tabel, wykorzystanie indeksów, blokady (locki), plany wykonania zapytań oraz informacje o konfiguracji serwera.

Projekt powstał jako narzędzie dydaktyczne i diagnostyczne. Pozwala obserwować, jak PostgreSQL wykonuje zapytania, gdzie powstają wąskie gardła i jak wpływają na to indeksy.

---

## Spis treści

- [Najważniejsze funkcje](#najważniejsze-funkcje)
- [Architektura](#architektura)
- [Stos technologiczny](#stos-technologiczny)
- [Wymagania](#wymagania)
- [Uruchomienie (Docker)](#uruchomienie-docker)
- [Uruchomienie lokalne](#uruchomienie-lokalne)
- [Konfiguracja](#konfiguracja)
- [Korzystanie z panelu](#korzystanie-z-panelu)
- [Dokumentacja API](#dokumentacja-api)
- [Struktura projektu](#struktura-projektu)
- [Model danych](#model-danych)
- [Skrypty pomocnicze](#skrypty-pomocnicze)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)

---

## Najważniejsze funkcje

| Moduł | Opis |
|-------|------|
| **Top Queries** | Najbardziej kosztowne zapytania (na podstawie `pg_stat_statements`) — liczba wywołań, średni i całkowity czas, liczba zwróconych wierszy. |
| **Analiza planu zapytania** | Interaktywny podgląd planu wykonania (`EXPLAIN`) w formie drzewa, z porównaniem wariantów **z indeksami** oraz **bez indeksów** (poprzez wyłączenie `enable_indexscan`/`enable_bitmapscan`). |
| **Table Health** | Kondycja tabel: liczba żywych i martwych krotek, poziom „rozdęcia” (bloat), stosunek skanów sekwencyjnych do indeksowych, statystyki INSERT/UPDATE/DELETE, daty ostatniego VACUUM/ANALYZE oraz współczynnik trafień w cache. |
| **DB Sizes** | Rozmiary tabel i indeksów z wizualizacją udziału danych i indeksów w całkowitym rozmiarze relacji. |
| **Index Usage** | Statystyki wykorzystania indeksów wraz z automatycznym wykrywaniem indeksów **nieużywanych** oraz **zduplikowanych**. |
| **Lock Monitor** | Wykrywanie blokad: które zapytanie blokuje które, czas oczekiwania, a także lista aktywnych/długich zapytań. |
| **Triggers** | Lista wyzwalaczy (triggerów) zdefiniowanych w bazie wraz z ich statusem i definicją. |
| **Buffer Cache** | Wykorzystanie pamięci podręcznej serwera (`pg_buffercache`) — które tabele zajmują najwięcej buforów. |
| **Extensions** | Lista zainstalowanych rozszerzeń PostgreSQL wraz z wersją i schematem. |

---

## Architektura

Aplikacja zbudowana jest w architekturze **API + frontend**:

```
┌─────────────────────────────────────────────────────────┐
│                  Przeglądarka (Frontend)                  │
│   templates/index.html  +  static/js/app.js (Vanilla JS)  │
│   pobiera dane asynchronicznie (fetch) z endpointów /api  │
└───────────────────────────┬───────────────────────────────┘
                            │ HTTP / JSON
┌───────────────────────────▼───────────────────────────────┐
│                    app.py (Flask)                          │
│   Warstwa webowa: routing, endpointy REST, serializacja    │
└───────────────────────────┬───────────────────────────────┘
                            │ wywołania funkcji
┌───────────────────────────▼───────────────────────────────┐
│                       db.py                                │
│   Warstwa dostępu do danych: połączenie, zapytania         │
│   do widoków systemowych PostgreSQL (pg_stat_*, pg_locks…) │
└───────────────────────────┬───────────────────────────────┘
                            │ psycopg2
┌───────────────────────────▼───────────────────────────────┐
│                  PostgreSQL 15                             │
│   pg_stat_statements, pg_buffercache, widoki systemowe     │
└─────────────────────────────────────────────────────────────┘
```

- **`db.py`** — warstwa dostępu do danych. Zawiera wyłącznie logikę połączenia oraz zapytania SQL do katalogów i widoków systemowych PostgreSQL (`pg_stat_statements`, `pg_stat_user_tables`, `pg_stat_user_indexes`, `pg_locks`, `pg_stat_activity`, `pg_buffercache`, `pg_extension` i in.).
- **`app.py`** — warstwa webowa (Flask). Definiuje endpointy REST zwracające JSON oraz stronę główną renderującą szablon.
- **`templates/` + `static/`** — frontend. Pojedyncza strona (SPA-like) pobierająca dane asynchronicznie z API i renderująca poszczególne widoki bez przeładowania strony.

---

## Stos technologiczny

- **Python 3.11**
- **Flask** — serwer webowy i routing
- **psycopg2** — sterownik PostgreSQL
- **PostgreSQL 15** — monitorowana baza danych
- **HTML + CSS + Vanilla JavaScript** — frontend (bez frameworków)
- **Docker / Docker Compose** — konteneryzacja i uruchamianie

---

## Wymagania

- **Docker** oraz **Docker Compose** (zalecany sposób uruchomienia), **lub**
- **Python 3.11+** i działająca instancja **PostgreSQL 15** (uruchomienie lokalne).

> **Ważne:** moduł *Top Queries* korzysta z rozszerzenia `pg_stat_statements`, które musi zostać załadowane przez serwer poprzez parametr `shared_preload_libraries`. W konfiguracji Docker jest to ustawione automatycznie.

---

## Uruchomienie (Docker)

Najprostszy sposób — całe środowisko (baza + aplikacja) startuje jednym poleceniem:

```bash
docker compose up --build
```

Po uruchomieniu:

- **Panel aplikacji:** [http://localhost:5001](http://localhost:5001)
- **PostgreSQL:** `localhost:5432` (baza `mydb`, użytkownik `postgres`, hasło `postgres`)

`docker-compose.yml` uruchamia dwie usługi:

| Usługa | Opis |
|--------|------|
| `postgres` | PostgreSQL 15 z załadowanym `pg_stat_statements`. Posiada healthcheck (`pg_isready`). |
| `db-inspector` | Aplikacja Flask. Startuje dopiero po osiągnięciu przez bazę stanu „healthy”. |

> Domyślnie wolumen danych PostgreSQL jest **wyłączony** (zakomentowany w `docker-compose.yml`), więc dane znikają po usunięciu kontenera. Aby je utrwalić, odkomentuj sekcje `volumes`.

---

## Uruchomienie lokalne

1. Zainstaluj zależności:

   ```bash
   pip install -r requirements.txt
   ```

2. Ustaw zmienne środowiskowe wskazujące na bazę (patrz [Konfiguracja](#konfiguracja)), np.:

   ```bash
   export POSTGRES_USER=postgres
   export POSTGRES_PASSWORD=postgres
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DB=mydb
   ```

3. Uruchom aplikację:

   ```bash
   python app.py
   ```

   Panel będzie dostępny pod adresem [http://localhost:5001](http://localhost:5001).

Podczas startu aplikacja automatycznie (funkcja `setup_database`):

- tworzy rozszerzenia `pg_stat_statements` oraz `pg_buffercache` (jeśli nie istnieją),
- tworzy użytkownika `inspector`,
- nadaje uprawnienie `pg_read_all_stats`.

> Operacje te wymagają konta o odpowiednich uprawnieniach (np. `postgres`). Jeśli uprawnień brak, aplikacja zgłosi to w komunikatach, ale będzie kontynuować pracę.

---

## Konfiguracja

Połączenie z bazą konfigurowane jest przez zmienne środowiskowe (funkcja `get_db_url` w `db.py`):

| Zmienna | Domyślna wartość | Opis |
|---------|------------------|------|
| `POSTGRES_USER` | — | Nazwa użytkownika bazy (wymagana) |
| `POSTGRES_PASSWORD` | — | Hasło (wymagane) |
| `POSTGRES_DB` | — | Nazwa bazy danych (wymagana) |
| `POSTGRES_HOST` | `localhost` | Host serwera PostgreSQL |
| `POSTGRES_PORT` | `5432` | Port serwera |

Adres połączenia budowany jest w formacie:
`postgresql://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB>`

Jeżeli wymagane zmienne (`USER`, `PASSWORD`, `DB`) nie zostaną ustawione, aplikacja zgłosi błąd `No DB URL provided`.

---

## Korzystanie z panelu

Po wejściu na [http://localhost:5001](http://localhost:5001) dostępne jest menu boczne z modułami pogrupowanymi w sekcje: **Queries**, **Storage**, **Indexes**, **Runtime**, **Trgrs**, **System**.

- Kliknięcie pozycji menu ładuje dany widok (dane pobierane są asynchronicznie przy pierwszym otwarciu).
- Przycisk **↺ Refresh** (na dole menu) odświeża aktualnie wyświetlany widok.
- W module **Top Queries** zapytania typu `SELECT` można przeanalizować przyciskiem **Analyze** — otwiera się okno z planem wykonania w formie drzewa oraz wariantami „With Indexes” / „Without Indexes”.

---

## Dokumentacja API

Wszystkie endpointy zwracają dane w formacie **JSON**. W przypadku błędu zwracany jest obiekt `{"error": "..."}`.

| Metoda | Endpoint | Opis | Źródło danych |
|--------|----------|------|---------------|
| `GET` | `/` | Strona główna (panel) | — |
| `GET` | `/api/stats` | Najbardziej kosztowne zapytania | `pg_stat_statements` |
| `GET` | `/api/indexes` | Statystyki indeksów + duplikaty | `pg_stat_user_indexes`, `pg_index` |
| `GET` | `/api/table-health` | Kondycja tabel + cache hit ratio | `pg_stat_user_tables`, `pg_statio_user_tables` |
| `GET` | `/api/sizes` | Rozmiary tabel i indeksów | `pg_stat_user_tables` |
| `GET` | `/api/locks` | Blokady i aktywne zapytania | `pg_locks`, `pg_stat_activity` |
| `POST` | `/api/analyze` | Plan wykonania zapytania (`EXPLAIN`) | — |
| `GET` | `/api/triggers` | Lista wyzwalaczy | `pg_trigger` |
| `GET` | `/api/cache` | Wykorzystanie buffer cache | `pg_buffercache` |
| `GET` | `/api/extensions` | Zainstalowane rozszerzenia | `pg_extension` |

### `POST /api/analyze`

Treść żądania:

```json
{ "query": "SELECT * FROM student WHERE last_name = 'Kowalski'" }
```

> Ze względów bezpieczeństwa analizowane mogą być **wyłącznie** zapytania zaczynające się od `SELECT`. Endpoint obsługuje zapytania z parametrami (`$1`, `$2`, …) — przygotowuje je jako `PREPARE` i podstawia wartości zastępcze odpowiednie dla typów argumentów.

Odpowiedź zawiera m.in.:
- `plan_json` — plan w formacie JSON (do widoku drzewa),
- `with_index` — plan tekstowy z włączonymi skanami indeksowymi,
- `without_index` — plan tekstowy z wyłączonymi skanami indeksowymi (dla porównania).

---

## Struktura projektu

```
dbMonitor/
├── app.py                      # Warstwa webowa (Flask) — endpointy i routing
├── db.py                       # Warstwa dostępu do danych — zapytania SQL
├── requirements.txt            # Zależności Python (flask, psycopg2-binary)
├── Dockerfile                  # Obraz aplikacji (Python 3.11)
├── docker-compose.yml          # Definicja usług: postgres + db-inspector
├── templates/
│   └── index.html              # Szablon panelu (HTML + CSS)
├── static/
│   └── js/
│       └── app.js              # Logika frontendu (fetch + renderowanie)
└── scrpts/                     # Skrypty pomocnicze (SQL i Python)
    ├── script.sql              # Schemat bazy + dane przykładowe
    ├── triggers_and_idx.sql    # Triggery, funkcje i indeksy
    ├── test_queries.sql        # Przykładowe zapytania testowe
    ├── batch_data_inserter.py  # Masowe generowanie danych (10 000 rekordów)
    ├── random_pracownik.py     # Generowanie losowych pracowników
    ├── traffic_simulator.py    # Symulacja ruchu i blokad
    └── message-2.py            # Symulacja blokad (wariant z db.get_db_url)
```

---

## Model danych

Aplikacja monitoruje przykładową bazę o tematyce **uczelnianej**. Schemat (`scrpts/script.sql`) obejmuje:

**Tabele:**

| Tabela | Opis |
|--------|------|
| `program` | Kierunki studiów |
| `course` | Przedmioty (z kolumnami `lecturer`, `semester`) |
| `building` | Budynki |
| `room` | Sale (powiązane z budynkiem) |
| `employee` | Pracownicy |
| `phd_student` | Doktoranci (powiązani z kierunkiem) |
| `student` | Studenci (z ograniczeniami CHECK na ocenę i płeć) |
| `enrollment` | Tabela łącząca studentów z przedmiotami |
| `employee_audit` | Tabela audytu wypełniana przez trigger |

**Widoki:** `student_program_v`, `employee_v`
**Sekwencje:** `student_seq`, `sec_seq`

**Triggery** (`scrpts/triggers_and_idx.sql`):
- `employee_audit_trigger` — loguje operacje INSERT/UPDATE/DELETE na tabeli `employee` do tabeli `employee_audit`.
- `student_program_trigger` — automatycznie aktualizuje `student_count` w tabeli `program` przy dodaniu/usunięciu studenta.

Skrypt `triggers_and_idx.sql` celowo tworzy też **indeksy nieużywane** (`idx_student_gender_unused`, `idx_phd_student_year_unused`) — do demonstracji modułu *Index Usage*.

---

## Skrypty pomocnicze

Katalog `scrpts/` zawiera narzędzia do przygotowania i obciążenia bazy (do uruchomienia lokalnie; domyślnie łączą się z `localhost:5432`, baza `mydb`):

| Skrypt | Przeznaczenie |
|--------|---------------|
| `script.sql` | Tworzy schemat bazy i wstawia dane przykładowe. Uruchom jako pierwszy. |
| `triggers_and_idx.sql` | Dodaje triggery, funkcje PL/pgSQL oraz indeksy. |
| `test_queries.sql` | Zestaw przykładowych zapytań SELECT/INSERT/UPDATE i indeksów. |
| `batch_data_inserter.py` | Masowo generuje po 10 000 rekordów do każdej tabeli (do testów wydajności). |
| `random_pracownik.py` | Wstawia partię losowych pracowników. |
| `traffic_simulator.py` | Generuje ciągły ruch w tle oraz symuluje blokady (row-level i table-level) — przydatne do demonstracji modułów *Top Queries* i *Lock Monitor*. |
| `message-2.py` | Wariant symulatora blokad korzystający z `get_db_url` z `db.py`. |

**Typowa kolejność przygotowania środowiska testowego:**

```bash
psql -h localhost -U postgres -d mydb -f scrpts/script.sql
psql -h localhost -U postgres -d mydb -f scrpts/triggers_and_idx.sql
python scrpts/batch_data_inserter.py     # opcjonalnie: dużo danych
python scrpts/traffic_simulator.py       # opcjonalnie: ruch i blokady
```

---

## Rozwiązywanie problemów

| Problem | Możliwa przyczyna i rozwiązanie |
|---------|---------------------------------|
| **Pusty moduł *Top Queries*** | Rozszerzenie `pg_stat_statements` nie jest załadowane przez `shared_preload_libraries`. W Dockerze jest to ustawione automatycznie; przy uruchomieniu lokalnym dodaj parametr do konfiguracji serwera i zrestartuj PostgreSQL. |
| **`No DB URL provided`** | Nie ustawiono wymaganych zmiennych `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`. |
| **Błąd `Cannot create extension`** | Konto użytkownika nie ma uprawnień do `CREATE EXTENSION`. Użyj konta administracyjnego (np. `postgres`). |
| **Pusty moduł *Buffer Cache*** | Rozszerzenie `pg_buffercache` nie zostało utworzone lub w cache nie ma jeszcze relacji użytkownika — wykonaj kilka zapytań i odśwież widok. |
| **Aplikacja nie łączy się z bazą w Dockerze** | Upewnij się, że baza osiągnęła stan „healthy”. Usługa `db-inspector` czeka na healthcheck, ale przy ręcznym uruchamianiu sprawdź `docker compose logs postgres`. |



