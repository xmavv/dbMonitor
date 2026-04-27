-- Indeks na nazwisko i imię
CREATE INDEX idx_student_dane ON student (nazwisko, imie);

-- Indeks na adres budynku
CREATE INDEX idx_budynek_adres ON budynek (adres);

-- Indeks na datę zatrudnienia pracowników
CREATE INDEX idx_pracownik_data ON pracownik (data_zatrudnienia);

-- Dodanie nowego studenta (sekwencja zadziała automatycznie dla numer_indeksu)
INSERT INTO student (imie, nazwisko, data_ur, srednia_ocen, plec, kierunek_id)
VALUES ('Krystyna2', 'Zielińska', '2001-02-12', 4.8, 'F', 5);

-- Dodanie nowego przedmiotu (używamy 'id' zamiast 'Identyfikator')
INSERT INTO przedmiot (id, nazwa, ects, prowadzacy, semestr)
VALUES (10, 'Programowanie Obiektowe', 5, 'dr inż. Jan Kowalski', 3);

-- Top 3 studentów według średniej
SELECT imie, nazwisko, srednia_ocen
FROM student
ORDER BY srednia_ocen DESC
LIMIT 3;

-- Sale o pojemności powyżej 20
SELECT s.numer_sali, s.pojemnosc, b.nazwa AS budynek, b.adres
FROM sala s
         JOIN budynek b ON s.budynek_id = b.id
WHERE s.pojemnosc > 20;

-- Liczba zapisanych studentów na kierunki
SELECT k.nazwa, COUNT(s.numer_indeksu) AS liczba_zapisanych
FROM kierunek k
         LEFT JOIN student s ON k.id = s.kierunek_id
GROUP BY k.nazwa;

-- Studenci bez zapisów na przedmioty
SELECT imie, nazwisko
FROM student
WHERE numer_indeksu NOT IN (SELECT student_id FROM zapisy_na_przedmioty);

-- Aktualizacja ECTS
UPDATE przedmiot
SET ects = ects + 1
WHERE semestr = 3;

-- Złożone zestawienie danych (Raport)
SELECT
    s.numer_indeksu,
    s.nazwisko || ' ' || s.imie AS student_full_name,
    s.srednia_ocen,
    k.nazwa AS kierunek_nazwa,
    p.nazwa AS przedmiot_nazwa,
    p.ects,
    p.prowadzacy AS wykladowca,
    b.nazwa AS budynek_nazwa,
    sa.numer_sali AS sala_nr,
    sa.rodzaj AS typ_sali
FROM student s
         JOIN kierunek k ON s.kierunek_id = k.id
         JOIN zapisy_na_przedmioty zp ON s.numer_indeksu = zp.student_id
         JOIN przedmiot p ON zp.przedmiot_id = p.id
         LEFT JOIN sala sa ON sa.rodzaj = 'Wykladowa'
         LEFT JOIN budynek b ON sa.budynek_id = b.id
WHERE s.srednia_ocen > 3.5
  AND b.rok_budowy > 2010
ORDER BY k.nazwa, s.nazwisko;