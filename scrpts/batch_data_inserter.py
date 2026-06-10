import random
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import string

DB_CONFIG = {
    "host": "localhost",
    "database": "mydb",
    "user": "postgres",
    "password": "postgres"
}

def generate_random_date(start_year=1980, end_year=2003):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).date()

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))

def get_next_id(cur, table_name, pk_col="id"):
    cur.execute(f"SELECT COALESCE(MAX({pk_col}), 0) + 1 FROM {table_name};")
    return cur.fetchone()[0]

def generate_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    target_count = 10000

    print("Generowanie i wstawianie danych. Proszę czekać...")

    # 1. KIERUNEK
    start_id = get_next_id(cur, "kierunek")
    kierunki = [(start_id + i, f"Kierunek_{random_string(5)}_{i}", random.randint(50, 1000), random.choice([6, 7, 8])) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO kierunek (id, nazwa, liczba_studentow, liczba_semestrow) VALUES %s", kierunki)
    cur.execute("SELECT id FROM kierunek")
    kierunek_ids = [row[0] for row in cur.fetchall()]

    # 2. PRZEDMIOT
    start_id = get_next_id(cur, "przedmiot")
    przedmioty = [(start_id + i, f"Przedmiot_{random_string(6)}_{i}", random.randint(1, 10), f"Prof. {random_string(5)}", random.randint(1, 8)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO przedmiot (id, nazwa, ects, prowadzacy, semestr) VALUES %s", przedmioty)
    cur.execute("SELECT id FROM przedmiot")
    przedmiot_ids = [row[0] for row in cur.fetchall()]

    # 3. BUDYNEK
    start_id = get_next_id(cur, "budynek")
    budynki = [(start_id + i, f"Budynek_{random_string(4)}", f"Ulica_{random_string(8)} {random.randint(1,200)}", random.randint(1950, 2024), random.randint(1, 15)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO budynek (id, nazwa, adres, rok_budowy, liczba_pieter) VALUES %s", budynki)
    cur.execute("SELECT id FROM budynek")
    budynek_ids = [row[0] for row in cur.fetchall()]

    # 4. PRACOWNIK
    start_id = get_next_id(cur, "pracownik")
    imiona = ["Jan", "Anna", "Piotr", "Ewa", "Marek", "Zofia", "Kamil", "Karolina"]
    nazwiska = ["Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski"]
    pracownicy = [(start_id + i, random.choice(imiona), random.choice(nazwiska), generate_random_date(2000, 2023)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO pracownik (id, imie, nazwisko, data_zatrudnienia) VALUES %s", pracownicy)

    # 5. DOKTORANT
    start_id = get_next_id(cur, "doktorant")
    doktoranci = [(start_id + i, random.choice(imiona), random.choice(nazwiska), f"{random.randint(100000, 999999)}_{i}", random.randint(2018, 2023), random.choice(kierunek_ids)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO doktorant (id, imie, nazwisko, nr_indeksu, rok_rozpoczecia, kierunek_id) VALUES %s", doktoranci)

    # 6. STUDENT
    start_id = get_next_id(cur, "student", "numer_indeksu")
    studenci = [(start_id + i, random.choice(imiona), random.choice(nazwiska), generate_random_date(), round(random.uniform(2.0, 5.5), 1), random.choice(['M', 'F']), random.choice(kierunek_ids)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO student (numer_indeksu, imie, nazwisko, data_ur, srednia_ocen, plec, kierunek_id) VALUES %s", studenci)
    cur.execute("SELECT numer_indeksu FROM student")
    student_ids = [row[0] for row in cur.fetchall()]

    # 7. SALA
    start_id = get_next_id(cur, "sala")
    sale = [(start_id + i, f"{random.randint(1, 999)}{random.choice(['A', 'B', 'C', ''])}", random.randint(15, 300), random.choice(["Wykładowa", "Laboratoryjna", "Ćwiczeniowa"]), random.choice(budynek_ids)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO sala (id, numer_sali, pojemnosc, rodzaj, budynek_id) VALUES %s", sale)

    start_id = get_next_id(cur, "zapisy_na_przedmioty")
    zapisy = [(start_id + i, random.choice(student_ids), random.choice(przedmiot_ids)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO zapisy_na_przedmioty (id, student_id, przedmiot_id) VALUES %s", zapisy)

    tables_with_serial = ["budynek", "sala", "doktorant", "zapisy_na_przedmioty"]
    for tbl in tables_with_serial:
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), COALESCE(MAX(id), 1)) FROM {tbl};")

    cur.execute("SELECT setval('student_seq', COALESCE(MAX(numer_indeksu), 1)) FROM student;")

    conn.commit()
    cur.close()
    conn.close()
    print("Zakończono! Wstawiono bezbłędnie tysiące rekordów omijając kolizje.")

if __name__ == "__main__":
    generate_data()