-- 1. USUNIĘCIE STARYCH TABEL
DROP VIEW IF EXISTS pracownik_v;
DROP VIEW IF EXISTS student_kierunek_v;
DROP TABLE IF EXISTS zapisy_na_przedmioty;
DROP TABLE IF EXISTS doktorant;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS sala;
DROP TABLE IF EXISTS budynek;
DROP TABLE IF EXISTS pracownik;
DROP TABLE IF EXISTS przedmiot;
DROP TABLE IF EXISTS kierunek;
DROP SEQUENCE IF EXISTS student_seq;
DROP SEQUENCE IF EXISTS sec_seq;

-- 2. SEKWENCJE
CREATE SEQUENCE student_seq
    START WITH 1
    INCREMENT BY 2
    MINVALUE 1;

CREATE SEQUENCE sec_seq
    START WITH 0
    INCREMENT BY 2
    MINVALUE 0
    MAXVALUE 99999;

-- 3. TABELE PODSTAWOWE
CREATE TABLE kierunek (
                          id                integer PRIMARY KEY,
                          nazwa             varchar(100) NOT NULL,
                          liczba_studentow  integer,
                          liczba_semestrow  integer
);

CREATE TABLE przedmiot (
                           id                integer PRIMARY KEY,
                           nazwa             varchar(100) NOT NULL,
                           ects              integer
);

CREATE TABLE budynek (
                         id                serial PRIMARY KEY,
                         nazwa             varchar(100) NOT NULL,
                         adres             varchar(255) NOT NULL,
                         rok_budowy        integer,
                         liczba_pieter     integer
);

CREATE TABLE pracownik (
                           id                integer PRIMARY KEY,
                           imie              varchar(50),
                           nazwisko          varchar(50),
                           data_zatrudnienia date
);

-- 4. TABELE Z KLUCZAMI OBCYMI
CREATE TABLE doktorant (
                           id              serial PRIMARY KEY,
                           imie            varchar(50)        NOT NULL,
                           nazwisko        varchar(50)        NOT NULL,
                           nr_indeksu      varchar(20) UNIQUE NOT NULL,
                           rok_rozpoczecia integer,
                           kierunek_id     integer,
                           CONSTRAINT fk_doktorant_kierunek FOREIGN KEY (kierunek_id) REFERENCES kierunek (id)
);

CREATE TABLE student (
                         numer_indeksu  integer PRIMARY KEY DEFAULT nextval('student_seq'),
                         imie           varchar(16) NOT NULL,
                         nazwisko       varchar(32) NOT NULL,
                         data_ur        date,
                         srednia_ocen   numeric(2, 1),
                         plec           char(1)     NOT NULL,
                         kierunek_id    integer,
                         CONSTRAINT chk_srednia_ocen CHECK (srednia_ocen >= 2.0 AND srednia_ocen <= 5.5),
                         CONSTRAINT chk_plec CHECK (plec IN ('M', 'F')),
                         CONSTRAINT fk_student_kierunek FOREIGN KEY (kierunek_id) REFERENCES kierunek (id)
);

CREATE TABLE sala (
                      id         serial PRIMARY KEY,
                      numer_sali varchar(50) NOT NULL,
                      pojemnosc  integer,
                      rodzaj     varchar(100),
                      budynek_id integer,
                      CONSTRAINT fk_sala_budynek FOREIGN KEY (budynek_id) REFERENCES budynek (id)
);

CREATE TABLE zapisy_na_przedmioty (
                                      id             serial PRIMARY KEY,
                                      student_id     integer,
                                      przedmiot_id   integer,
                                      CONSTRAINT fk_zapisy_student FOREIGN KEY (student_id) REFERENCES student (numer_indeksu),
                                      CONSTRAINT fk_zapisy_przedmiot FOREIGN KEY (przedmiot_id) REFERENCES przedmiot (id)
);

-- 5. WIDOKI
CREATE VIEW student_kierunek_v AS
SELECT s.numer_indeksu, s.imie, s.nazwisko, k.nazwa AS nazwa_kierunku
FROM student s
         JOIN kierunek k ON s.kierunek_id = k.id
         JOIN zapisy_na_przedmioty z ON s.numer_indeksu = z.student_id
ORDER BY s.nazwisko ASC;

CREATE VIEW pracownik_v AS
SELECT p.id,
       p.imie || ' ' || p.nazwisko AS osoba,
       p.data_zatrudnienia
FROM pracownik p;

-- 6. DANE
INSERT INTO kierunek (id, nazwa, liczba_studentow, liczba_semestrow)
VALUES (5, 'Informatyka Techniczna', 554, 7),
       (6, 'Informatyka Stosowana', 497, 7),
       (7, 'Telekomunikacja', 512, 7);

INSERT INTO student (numer_indeksu, imie, nazwisko, data_ur, srednia_ocen, plec, kierunek_id)
VALUES (123456, 'Jan', 'Kowalski', '1995-05-10', 4.5, 'M', 5),
       (234567, 'Anna', 'Nowak', '1998-09-15', 4.2, 'F', 6),
       (345678, 'Piotr', 'Wiśniewski', '1997-03-25', 3.8, 'M', 7);

INSERT INTO budynek (id, nazwa, adres, rok_budowy, liczba_pieter)
VALUES (5, 'Technopolis', 'ul. Janiszewskiego 15', 2020, 5),
       (6, 'C5', 'ul. Janiszewskiego 21', 2007, 3),
       (7, 'D-21', 'ul. Janiszewskiego 34', 2015, 6);

INSERT INTO sala (id, numer_sali, pojemnosc, rodzaj, budynek_id)
VALUES (5, '32', 35, 'Cwiczeniowa', 5),
       (6, '24', 16, 'Laboratoryjna', 5),
       (7, '135', 200, 'Wykladowa', 5);

INSERT INTO doktorant (id, imie, nazwisko, nr_indeksu, rok_rozpoczecia, kierunek_id)
VALUES (5, 'Maksymilian', 'Wajda', '272345', 2019, 5),
       (6, 'Weronika', 'Janda', '290564', 2023, 5),
       (7, 'Marta', 'Cholubek', '342908', 2022, 5);

INSERT INTO przedmiot (id, nazwa, ects)
VALUES (5, 'Teoria Systemów', 3),
       (6, 'Bazy danych', 4),
       (7, 'Architektura komputerów', 5);

INSERT INTO pracownik (id, imie, nazwisko, data_zatrudnienia)
VALUES (5, 'Mariusz', 'Potylica', '2023-01-01'),
       (6, 'Weronika', 'Grzyb', '2023-01-01'),
       (7, 'Albert', 'Wieszcz', '2023-01-01');

INSERT INTO zapisy_na_przedmioty (id, student_id, przedmiot_id)
VALUES (5, 123456, 5),
       (6, 234567, 6),
       (7, 345678, 7);

SELECT setval(pg_get_serial_sequence('budynek', 'id'), coalesce(max(id), 1)) FROM budynek;
SELECT setval(pg_get_serial_sequence('sala', 'id'), coalesce(max(id), 1)) FROM sala;
SELECT setval(pg_get_serial_sequence('doktorant', 'id'), coalesce(max(id), 1)) FROM doktorant;

-- 7. INDEKSY
CREATE INDEX idx_student_nazwisko ON student (nazwisko);
CREATE UNIQUE INDEX idx_kierunek_liczba_studentow ON kierunek (liczba_studentow);

-- 8. MODYFIKACJE STRUKTURY
ALTER TABLE przedmiot ADD COLUMN prowadzacy varchar(50);
ALTER TABLE przedmiot ADD COLUMN semestr integer;