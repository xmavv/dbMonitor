# PG Inspector — Przewodnik użytkownika

Ten przewodnik tłumaczy **jak korzystać** z PG Inspectora w codziennej pracy z bazą danych — bez wchodzenia w szczegóły techniczne. Jeśli szukasz informacji o instalacji, architekturze czy API, zajrzyj do pliku [`README.md`](README.md).

> **Dla kogo jest to narzędzie?**
> Wyobraź sobie, że masz dużą, działającą bazę PostgreSQL — sklep internetowy, system uczelni, aplikację z tysiącami użytkowników. Coś działa wolno, ktoś zgłasza „zawieszki", a Ty chcesz wiedzieć **co dokładnie** dzieje się w bazie: które zapytania są kosztowne, gdzie brakuje indeksów, czy coś się nie zablokowało. PG Inspector pokazuje to wszystko na jednym ekranie, w czytelnej formie — nie musisz pisać zapytań do katalogów systemowych PostgreSQL.

---

## Spis treści

- [Pierwsze kroki](#pierwsze-kroki)
- [Jak wygląda panel](#jak-wygląda-panel)
- [Co możesz sprawdzić — przegląd ekranów](#co-możesz-sprawdzić--przegląd-ekranów)
  - [Top Queries — najcięższe zapytania](#1-top-queries--najcięższe-zapytania)
  - [Table Health — kondycja tabel](#2-table-health--kondycja-tabel)
  - [DB Sizes — co zajmuje miejsce](#3-db-sizes--co-zajmuje-miejsce)
  - [Buffer Cache — co siedzi w pamięci](#4-buffer-cache--co-siedzi-w-pamięci)
  - [Index Usage — które indeksy się przydają](#5-index-usage--które-indeksy-się-przydają)
  - [Lock Monitor — kto kogo blokuje](#6-lock-monitor--kto-kogo-blokuje)
  - [Triggers — wyzwalacze w bazie](#7-triggers--wyzwalacze-w-bazie)
  - [Extensions — zainstalowane rozszerzenia](#8-extensions--zainstalowane-rozszerzenia)
- [Analiza planu zapytania (EXPLAIN)](#analiza-planu-zapytania-explain)
- [Automatyczne wykrywanie problemów (dziennik anomalii)](#automatyczne-wykrywanie-problemów-dziennik-anomalii)
- [Typowe scenariusze — od czego zacząć](#typowe-scenariusze--od-czego-zacząć)
- [Wskazówki i częste pytania](#wskazówki-i-częste-pytania)

---

## Pierwsze kroki

1. **Uruchom aplikację** (najprościej przez Docker — szczegóły w `README.md`):
   ```bash
   docker compose up
   ```
2. **Otwórz przeglądarkę** i wejdź na adres:
   ```
   http://localhost:5001
   ```
3. **Gotowe.** Panel automatycznie łączy się z bazą i przy pierwszym uruchomieniu sam włącza potrzebne rozszerzenie do zbierania statystyk (`pg_stat_statements`). Od tej chwili wszystko, co widzisz, to dane „na żywo" z Twojej bazy.

> 💡 Jeśli chcesz podłączyć się do **własnej, istniejącej bazy**, podaj jej adres przez zmienną środowiskową `DATABASE_URL` (lub parametr `--db-url`). Sposób konfiguracji opisuje `README.md`.

---

## Jak wygląda panel

Panel jest podzielony na trzy obszary:

```
┌──────────────┬────────────────────────────────────────────┐
│              │  Nazwa ekranu                         ● live │  ← górny pasek
│  MENU        ├────────────────────────────────────────────┤
│  (po lewej)  │                                            │
│              │   Tabele, wykresy i karty z danymi         │  ← główny obszar
│  • Top Q.    │                                            │
│  • Tabele    │                                            │
│  • ...       │                                            │
│              │                                            │
│  ↺ Refresh   │                                            │
└──────────────┴────────────────────────────────────────────┘
```

- **Menu po lewej** — przełączasz się między ekranami jednym kliknięciem.
- **Zielona kropka** w prawym górnym rogu oznacza, że połączenie z bazą działa.
- **Przycisk `↺ Refresh`** (na dole menu) odświeża dane na aktualnie otwartym ekranie. Dane **nie** odświeżają się same — klikasz, gdy chcesz zobaczyć najnowszy stan.

---

## Co możesz sprawdzić — przegląd ekranów

Poniżej każdy ekran opisany jest według schematu: **co pokazuje**, **na co zwrócić uwagę** i **co z tym zrobić**.

### 1. Top Queries — najcięższe zapytania

**Co pokazuje:** ranking zapytań, które najbardziej obciążają bazę. Dla każdego widzisz: ile razy zostało wykonane, ile trwało średnio, ile czasu pochłonęło łącznie i ile wierszy zwróciło.

**Na co zwrócić uwagę:**
- Zapytania z **dużym całkowitym czasem** — to one realnie spowalniają system (nawet jeśli pojedyncze wykonanie jest szybkie, ale powtarza się tysiące razy).
- Zapytania z **wysokim średnim czasem** — pojedynczo wolne, kandydaci do optymalizacji.

**Co z tym zrobić:** kliknij treść zapytania, aby przeanalizować jego plan wykonania (patrz [Analiza planu zapytania](#analiza-planu-zapytania-explain)) i sprawdzić, czy pomógłby indeks.

> To najlepszy ekran na start, gdy „baza działa wolno, ale nie wiem dlaczego".

### 2. Table Health — kondycja tabel

**Co pokazuje:** stan „zdrowia" każdej tabeli:
- **żywe vs. martwe krotki** — martwe krotki (dead tuples) to pozostałości po `UPDATE`/`DELETE`, które zajmują miejsce, dopóki nie posprząta ich `VACUUM`,
- **skany sekwencyjne vs. indeksowe** — czy baza musi przeglądać całą tabelę, czy korzysta z indeksów,
- **statystyki INSERT / UPDATE / DELETE**,
- **kiedy ostatnio wykonano VACUUM i ANALYZE**,
- **skuteczność cache** dla tabeli.

**Na co zwrócić uwagę:**
- Wysoki **procent martwych krotek** → tabela jest „rozdęta" (bloat), warto rozważyć `VACUUM`.
- Dużo **skanów sekwencyjnych** na dużej tabeli → prawdopodobnie brakuje indeksu.
- Dawno (lub nigdy) niewykonany **ANALYZE** → planer może podejmować złe decyzje.

**Co z tym zrobić:** zaplanuj `VACUUM`/`ANALYZE` dla problematycznych tabel, albo dodaj indeksy tam, gdzie dominują skany sekwencyjne.

### 3. DB Sizes — co zajmuje miejsce

**Co pokazuje:** rozmiar każdej tabeli wraz z paskiem pokazującym, ile zajmują **same dane**, a ile **indeksy**. Widać też udział procentowy indeksów w rozmiarze tabeli.

**Na co zwrócić uwagę:**
- Tabele, które urosły nieproporcjonalnie duże.
- Tabele, w których **indeksy zajmują więcej niż same dane** — to sygnał, że indeksów może być za dużo (lub są zbędne).

**Co z tym zrobić:** połącz tę wiedzę z ekranem **Index Usage**, żeby zdecydować, które indeksy można usunąć.

### 4. Buffer Cache — co siedzi w pamięci

**Co pokazuje:** które tabele zajmują najwięcej **pamięci podręcznej** serwera (buforów). To pamięć, z której PostgreSQL czyta najszybciej.

**Na co zwrócić uwagę:**
- Czy w cache siedzą tabele, których faktycznie często używasz — to dobrze.
- Czy cache zajmują tabele, których prawie nie ruszasz — może to oznaczać nieefektywne wykorzystanie pamięci.

**Co z tym zrobić:** to ekran bardziej diagnostyczny/edukacyjny — pomaga zrozumieć, jak baza gospodaruje pamięcią i dlaczego niektóre zapytania są błyskawiczne, a inne wolne (bo muszą sięgać na dysk).

### 5. Index Usage — które indeksy się przydają

**Co pokazuje:** listę wszystkich indeksów i to, jak często są używane (liczba skanów). Narzędzie automatycznie oznacza:
- **indeksy nieużywane** — istnieją, ale nikt z nich nie korzysta,
- **indeksy zduplikowane** — kilka indeksów robi praktycznie to samo.

**Na co zwrócić uwagę:**
- Indeksy z **zerową lub znikomą liczbą skanów**, zwłaszcza duże — kosztują przy każdym zapisie, a nic nie dają.
- Oznaczone **duplikaty** — niepotrzebnie spowalniają zapisy i zajmują miejsce.

**Co z tym zrobić:** rozważ usunięcie nieużywanych/zduplikowanych indeksów. Mniej indeksów = szybsze `INSERT`/`UPDATE` i mniejsza baza.

### 6. Lock Monitor — kto kogo blokuje

**Co pokazuje:** dwie rzeczy:
- **Blokady (locki)** — graficznie, w stylu „zapytanie A czeka na zapytanie B", wraz z czasem oczekiwania,
- **Aktywne zapytania** — co aktualnie wykonuje się w bazie i jak długo.

**Na co zwrócić uwagę:**
- Każdy widoczny **lock** z długim czasem oczekiwania — to klasyczna przyczyna „zawieszania się" aplikacji.
- Zapytania działające **bardzo długo** — mogły się zaciąć lub blokują innych.

**Co z tym zrobić:** zidentyfikuj zapytanie blokujące (jego PID i treść), a następnie zdecyduj, czy je zakończyć / zoptymalizować transakcję, która trzyma blokadę zbyt długo.

> To pierwszy ekran, na który warto zajrzeć, gdy użytkownicy zgłaszają nagłe „przestoje".

### 7. Triggers — wyzwalacze w bazie

**Co pokazuje:** listę wszystkich wyzwalaczy (triggerów) zdefiniowanych w bazie — na której tabeli działają, czy są włączone oraz ich pełną definicję.

**Na co zwrócić uwagę:**
- Triggery, o których nie wiedziałeś — często to one „po cichu" wykonują dodatkową pracę przy zapisach i potrafią spowalniać operacje.
- Status (włączony / wyłączony).

**Co z tym zrobić:** jeśli zapisy do jakiejś tabeli są wolne, sprawdź, czy nie wisi na niej kosztowny trigger.

### 8. Extensions — zainstalowane rozszerzenia

**Co pokazuje:** listę rozszerzeń PostgreSQL zainstalowanych w bazie wraz z ich wersją i schematem (np. `pg_stat_statements`, `pg_buffercache`).

**Na co zwrócić uwagę:** czy zainstalowane są rozszerzenia, których oczekujesz (np. do zbierania statystyk). To głównie ekran informacyjny.

---

## Analiza planu zapytania (EXPLAIN)

To jedna z najpotężniejszych funkcji. Pozwala zobaczyć, **jak dokładnie** PostgreSQL wykona dane zapytanie `SELECT` — krok po kroku.

**Jak użyć:**
1. Przejdź na ekran **Top Queries** i kliknij treść interesującego Cię zapytania (albo wskaż zapytanie, które chcesz przeanalizować).
2. Otworzy się okno z planem wykonania. Masz w nim trzy zakładki:
   - **Tree View** — plan w formie czytelnego drzewa: które operacje (skany, złączenia, sortowania) są wykonywane i w jakiej kolejności. Kosztowne lub podejrzane kroki są podświetlone.
   - **With Indexes** — plan, gdy baza może korzystać z indeksów (stan normalny).
   - **Without Indexes** — plan z **wyłączonymi** indeksami. Dzięki temu na własne oczy zobaczysz, jak bardzo (lub jak mało) dany indeks pomaga.

**Po co to robić:** porównując oba warianty, jednoznacznie ocenisz, czy indeks ma sens — zamiast zgadywać. Widać, gdzie powstaje wąskie gardło (np. kosztowny skan sekwencyjny dużej tabeli lub drogie złączenie).

> ⚠️ Analizować można tylko zapytania `SELECT` — narzędzie celowo nie pozwala uruchamiać `UPDATE`/`DELETE` itp., żeby nie zmodyfikować danych.

---

## Automatyczne wykrywanie problemów (dziennik anomalii)

Oprócz ekranów, które oglądasz „na żądanie", PG Inspector **w tle, automatycznie** monitoruje bazę i zapisuje wykryte problemy do pliku-dziennika. Działa to nieprzerwanie od momentu uruchomienia aplikacji — nie musisz nic klikać.

**Co potrafi wykryć (przykłady):**

| Rodzaj zdarzenia | Co oznacza |
|------------------|------------|
| **Zablokowane zapytanie** | Jakieś zapytanie czeka zbyt długo, bo zablokowało je inne. |
| **Długo trwające zapytanie** | Zapytanie działa dłużej niż ustalony próg (może się zaciąć). |
| **Martwe krotki** | Tabela jest mocno „rozdęta" i wymaga `VACUUM`. |
| **Niska skuteczność cache** | Tabela lub jej indeksy zbyt często czytane są z dysku, a nie z pamięci. |
| **Zduplikowane indeksy** | Wykryto nadmiarowe indeksy. |
| **Nieużywany duży indeks** | Duży indeks, z którego nikt nie korzysta. |
| **Wysoki narzut indeksów** | Indeksy zajmują nieproporcjonalnie dużo miejsca względem danych. |

**Gdzie to znaleźć:** zdarzenia trafiają do pliku `logs/db_anomalies.jsonl` (każda linia to jedno zdarzenie z datą, poziomem ważności i opisem). Możesz go przeglądać, archiwizować albo podpiąć pod własny system alertów.

**Co można dostroić (bez znajomości kodu):** wszystkie progi i częstotliwość sprawdzania ustawia się przez zmienne środowiskowe — np.:
- jak często sprawdzać bazę (`DBMONITOR_LOG_INTERVAL_SECONDS`),
- po ilu sekundach uznać zapytanie za „za długie" (`DBMONITOR_LONG_QUERY_SECONDS`),
- po ilu sekundach reagować na blokadę (`DBMONITOR_LOCK_WAIT_SECONDS`),
- jaki poziom ważności zapisywać (`DBMONITOR_LOG_MIN_SEVERITY`).

Pełną listę ustawień znajdziesz w `README.md`. Dzięki temu możesz dopasować czułość monitoringu do swojej bazy — inaczej ustawisz progi dla małej aplikacji, inaczej dla dużego systemu produkcyjnego.

---

## Typowe scenariusze — od czego zacząć

**„Aplikacja działa wolno, ale nie wiem dlaczego"**
→ Zacznij od **Top Queries** (znajdź kosztowne zapytania) → kliknij je i otwórz **plan wykonania** → porównaj wariant z indeksami i bez → ewentualnie sprawdź **Table Health**, czy nie brakuje indeksu lub czy tabela nie jest rozdęta.

**„Coś się zawiesiło, użytkownicy nie mogą zapisać danych"**
→ Wejdź na **Lock Monitor**. Sprawdź, które zapytanie blokuje pozostałe i jak długo. Tam znajdziesz „winowajcę".

**„Baza zajmuje za dużo miejsca"**
→ Otwórz **DB Sizes** (które tabele/indeksy urosły) → przejdź do **Index Usage** i usuń nieużywane oraz zduplikowane indeksy.

**„Zapisy do tabeli są podejrzanie wolne"**
→ Sprawdź **Index Usage** (czy nie ma za dużo indeksów do aktualizacji) oraz **Triggers** (czy nie wisi kosztowny wyzwalacz).

**„Chcę być uprzedzany o problemach, zanim zauważą je użytkownicy"**
→ Skonfiguruj **dziennik anomalii** i monitoruj plik `logs/db_anomalies.jsonl`.

---

## Wskazówki i częste pytania

- **Czy narzędzie może coś zepsuć w bazie?** Nie zmienia Twoich danych. Czyta statystyki, a analiza planów obsługuje wyłącznie zapytania `SELECT`. Przy pierwszym starcie zakłada jedynie pomocnicze rozszerzenia/konto techniczne do monitoringu.
- **Dane się nie odświeżają same** — kliknij `↺ Refresh`, gdy chcesz zobaczyć aktualny stan. Wyjątkiem jest dziennik anomalii, który działa w tle bez przerwy.
- **Niektóre ekrany są puste** — to normalne, jeśli baza jest świeża albo nic się akurat nie dzieje (np. brak blokad). Statystyki gromadzą się z czasem, w miarę ruchu w bazie.
- **Chcę przetestować narzędzie na „żywym" ruchu** — w katalogu `scrpts/` znajdują się skrypty generujące sztuczny ruch, blokady i anomalie. Pozwalają zobaczyć, jak panel reaguje na realne sytuacje (szczegóły w `README.md`).
- **Gdzie znajdę szczegóły techniczne (instalacja, API, konfiguracja)?** W pliku [`README.md`](README.md).
