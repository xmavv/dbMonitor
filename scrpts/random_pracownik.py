import random
import os
from datetime import datetime, timedelta
import psycopg2

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    database=os.getenv("POSTGRES_DB", "mydb"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres")
)

cursor = conn.cursor()

imiona = ["Jan", "Anna", "Piotr", "Kasia", "Marek", "Ewa", "Tomasz", "Ola"]
nazwiska = ["Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski"]

def losowa_data(start_year=1990, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    # return (start + timedelta(days=random_days)).date()
    return "2022-01-01"

def pobierz_startowe_id():
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM pracownik;")
    return cursor.fetchone()[0] + 1

def generuj_pracownikow(liczba=50):
    start_id = pobierz_startowe_id()
    dane = []

    for i in range(liczba):
        imie = random.choice(imiona)
        nazwisko = random.choice(nazwiska)
        data = losowa_data()
        dane.append((start_id + i, imie, nazwisko, data))

    return dane

def insert_batch(dane):
    query = """
            INSERT INTO pracownik (id, imie, nazwisko, data_zatrudnienia)
            VALUES (%s, %s, %s, %s) \
            """
    cursor.executemany(query, dane)
    conn.commit()

if __name__ == "__main__":
    dane = generuj_pracownikow(1000)
    insert_batch(dane)
    print("Dane dodane")

    cursor.close()
    conn.close()
