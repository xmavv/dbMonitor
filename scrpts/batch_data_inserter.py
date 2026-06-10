import random
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import string

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "database": os.getenv("POSTGRES_DB", "mydb"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres")
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

    print("Generating and inserting data. Please wait...")

    # 1. PROGRAM
    start_id = get_next_id(cur, "program")
    programs = [(start_id + i, f"Program_{random_string(5)}_{i}", random.randint(50, 1000), random.choice([6, 7, 8])) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO program (id, name, student_count, semester_count) VALUES %s", programs)
    cur.execute("SELECT id FROM program")
    program_ids = [row[0] for row in cur.fetchall()]

    # 2. COURSE
    start_id = get_next_id(cur, "course")
    courses = [(start_id + i, f"Course_{random_string(6)}_{i}", random.randint(1, 10), f"Prof. {random_string(5)}", random.randint(1, 8)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO course (id, name, ects, lecturer, semester) VALUES %s", courses)
    cur.execute("SELECT id FROM course")
    course_ids = [row[0] for row in cur.fetchall()]

    # 3. BUILDING
    start_id = get_next_id(cur, "building")
    buildings = [(start_id + i, f"Building_{random_string(4)}", f"Street_{random_string(8)} {random.randint(1,200)}", random.randint(1950, 2024), random.randint(1, 15)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO building (id, name, address, build_year, floor_count) VALUES %s", buildings)
    cur.execute("SELECT id FROM building")
    building_ids = [row[0] for row in cur.fetchall()]

    # 4. EMPLOYEE
    start_id = get_next_id(cur, "employee")
    first_names = ["Jan", "Anna", "Piotr", "Ewa", "Marek", "Zofia", "Kamil", "Karolina"]
    last_names = ["Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski"]
    employees = [(start_id + i, random.choice(first_names), random.choice(last_names), generate_random_date(2000, 2023)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO employee (id, first_name, last_name, hire_date) VALUES %s", employees)

    # 5. PHD_STUDENT
    start_id = get_next_id(cur, "phd_student")
    phd_students = [(start_id + i, random.choice(first_names), random.choice(last_names), f"{random.randint(100000, 999999)}_{i}", random.randint(2018, 2023), random.choice(program_ids)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO phd_student (id, first_name, last_name, index_number, start_year, program_id) VALUES %s", phd_students)

    # 6. STUDENT
    start_id = get_next_id(cur, "student", "index_number")
    students = [(start_id + i, random.choice(first_names), random.choice(last_names), generate_random_date(), round(random.uniform(2.0, 5.5), 1), random.choice(['M', 'F']), random.choice(program_ids)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO student (index_number, first_name, last_name, birth_date, gpa, gender, program_id) VALUES %s", students)
    cur.execute("SELECT index_number FROM student")
    student_ids = [row[0] for row in cur.fetchall()]

    # 7. ROOM
    start_id = get_next_id(cur, "room")
    rooms = [(start_id + i, f"{random.randint(1, 999)}{random.choice(['A', 'B', 'C', ''])}", random.randint(15, 300), random.choice(["Wykładowa", "Laboratoryjna", "Ćwiczeniowa"]), random.choice(building_ids)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO room (id, room_number, capacity, type, building_id) VALUES %s", rooms)

    start_id = get_next_id(cur, "enrollment")
    enrollments = [(start_id + i, random.choice(student_ids), random.choice(course_ids)) for i in range(target_count)]
    psycopg2.extras.execute_values(cur, "INSERT INTO enrollment (id, student_id, course_id) VALUES %s", enrollments)

    tables_with_serial = ["building", "room", "phd_student", "enrollment"]
    for tbl in tables_with_serial:
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), COALESCE(MAX(id), 1)) FROM {tbl};")

    cur.execute("SELECT setval('student_seq', COALESCE(MAX(index_number), 1)) FROM student;")

    conn.commit()
    cur.close()
    conn.close()
    print("Done! Inserted thousands of records without collisions.")

if __name__ == "__main__":
    generate_data()
