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

first_names = ["Jan", "Anna", "Piotr", "Kasia", "Marek", "Ewa", "Tomasz", "Ola"]
last_names = ["Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski"]

def random_date(start_year=1990, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    # return (start + timedelta(days=random_days)).date()
    return "2022-01-01"

def get_start_id():
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM employee;")
    return cursor.fetchone()[0] + 1

def generate_employees(count=50):
    start_id = get_start_id()
    data = []

    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        date = random_date()
        data.append((start_id + i, first_name, last_name, date))

    return data

def insert_batch(data):
    query = """
            INSERT INTO employee (id, first_name, last_name, hire_date)
            VALUES (%s, %s, %s, %s) \
            """
    cursor.executemany(query, data)
    conn.commit()

if __name__ == "__main__":
    data = generate_employees(1000)
    insert_batch(data)
    print("Data inserted")

    cursor.close()
    conn.close()
