-- 1. DROP OLD OBJECTS
DROP VIEW IF EXISTS employee_v;
DROP VIEW IF EXISTS student_program_v;
DROP TABLE IF EXISTS enrollment;
DROP TABLE IF EXISTS phd_student;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS room;
DROP TABLE IF EXISTS building;
DROP TABLE IF EXISTS employee;
DROP TABLE IF EXISTS course;
DROP TABLE IF EXISTS program;
DROP SEQUENCE IF EXISTS student_seq;
DROP SEQUENCE IF EXISTS sec_seq;

-- 2. SEQUENCES
CREATE SEQUENCE student_seq
    START WITH 1
    INCREMENT BY 2
    MINVALUE 1;

CREATE SEQUENCE sec_seq
    START WITH 0
    INCREMENT BY 2
    MINVALUE 0
    MAXVALUE 99999;

-- 3. BASE TABLES
CREATE TABLE program (
                          id                serial PRIMARY KEY,
                          name              varchar(100) NOT NULL,
                          student_count     integer,
                          semester_count    integer
);

CREATE TABLE course (
                           id                serial PRIMARY KEY,
                           name              varchar(100) NOT NULL,
                           ects              integer
);

CREATE TABLE building (
                         id                serial PRIMARY KEY,
                         name              varchar(100) NOT NULL,
                         address           varchar(255) NOT NULL,
                         build_year        integer,
                         floor_count       integer
);

CREATE TABLE employee (
                           id                serial PRIMARY KEY,
                           first_name        varchar(50),
                           last_name         varchar(50),
                           hire_date         date
);

-- 4. TABLES WITH FOREIGN KEYS
CREATE TABLE phd_student (
                           id              serial PRIMARY KEY,
                           first_name      varchar(50)        NOT NULL,
                           last_name       varchar(50)        NOT NULL,
                           index_number    varchar(20) UNIQUE NOT NULL,
                           start_year      integer,
                           program_id      integer,
                           CONSTRAINT fk_phd_student_program FOREIGN KEY (program_id) REFERENCES program (id)
);

CREATE TABLE student (
                         index_number   integer PRIMARY KEY DEFAULT nextval('student_seq'),
                         first_name     varchar(16) NOT NULL,
                         last_name      varchar(32) NOT NULL,
                         birth_date     date,
                         gpa            numeric(2, 1),
                         gender         char(1)     NOT NULL,
                         program_id     integer,
                         CONSTRAINT chk_gpa CHECK (gpa >= 2.0 AND gpa <= 5.5),
                         CONSTRAINT chk_gender CHECK (gender IN ('M', 'F')),
                         CONSTRAINT fk_student_program FOREIGN KEY (program_id) REFERENCES program (id)
);

CREATE TABLE room (
                      id          serial PRIMARY KEY,
                      room_number varchar(50) NOT NULL,
                      capacity    integer,
                      type        varchar(100),
                      building_id integer,
                      CONSTRAINT fk_room_building FOREIGN KEY (building_id) REFERENCES building (id)
);

CREATE TABLE enrollment (
                                      id             serial PRIMARY KEY,
                                      student_id     integer,
                                      course_id      integer,
                                      CONSTRAINT fk_enrollment_student FOREIGN KEY (student_id) REFERENCES student (index_number),
                                      CONSTRAINT fk_enrollment_course FOREIGN KEY (course_id) REFERENCES course (id)
);

-- 5. VIEWS
CREATE VIEW student_program_v AS
SELECT s.index_number, s.first_name, s.last_name, p.name AS program_name
FROM student s
         JOIN program p ON s.program_id = p.id
         JOIN enrollment e ON s.index_number = e.student_id
ORDER BY s.last_name ASC;

CREATE VIEW employee_v AS
SELECT e.id,
       e.first_name || ' ' || e.last_name AS person,
       e.hire_date
FROM employee e;

-- 6. DATA
INSERT INTO program (name, student_count, semester_count)
VALUES ('Informatyka Techniczna', 554, 7),
       ('Informatyka Stosowana', 497, 7),
       ('Telekomunikacja', 512, 7);

INSERT INTO student (index_number, first_name, last_name, birth_date, gpa, gender, program_id)
VALUES (123456, 'Jan', 'Kowalski', '1995-05-10', 4.5, 'M', 1),
       (234567, 'Anna', 'Nowak', '1998-09-15', 4.2, 'F', 2),
       (345678, 'Piotr', 'Wiśniewski', '1997-03-25', 3.8, 'M', 3);

INSERT INTO building (name, address, build_year, floor_count)
VALUES ('Technopolis', 'ul. Janiszewskiego 15', 2020, 5),
       ('C5', 'ul. Janiszewskiego 21', 2007, 3),
       ('D-21', 'ul. Janiszewskiego 34', 2015, 6);

INSERT INTO room (room_number, capacity, type, building_id)
VALUES ('32', 35, 'Cwiczeniowa', 1),
       ( '24', 16, 'Laboratoryjna', 1),
       ( '135', 200, 'Wykladowa', 1);

INSERT INTO phd_student (first_name, last_name, index_number, start_year, program_id)
VALUES ( 'Maksymilian', 'Wajda', '272345', 2019, 1),
       ( 'Weronika', 'Janda', '290564', 2023, 1),
       ( 'Marta', 'Cholubek', '342908', 2022, 1);

INSERT INTO course (name, ects)
VALUES ('Teoria Systemów', 3),
       ('Bazy danych', 4),
       ('Architektura komputerów', 5);

INSERT INTO employee (first_name, last_name, hire_date)
VALUES ('Mariusz', 'Potylica', '2023-01-01'),
       ('Weronika', 'Grzyb', '2023-01-01'),
       ('Albert', 'Wieszcz', '2023-01-01');

INSERT INTO enrollment (student_id, course_id)
VALUES (123456, 1),
       (234567, 2),
       (345678, 3);

SELECT setval(pg_get_serial_sequence('building', 'id'), coalesce(max(id), 1)) FROM building;
SELECT setval(pg_get_serial_sequence('room', 'id'), coalesce(max(id), 1)) FROM room;
SELECT setval(pg_get_serial_sequence('phd_student', 'id'), coalesce(max(id), 1)) FROM phd_student;

-- 7. INDEXES
CREATE INDEX idx_student_last_name ON student (last_name);
CREATE INDEX idx_program_student_count ON program (student_count);

-- 8. STRUCTURE MODIFICATIONS
ALTER TABLE course ADD COLUMN lecturer varchar(50);
ALTER TABLE course ADD COLUMN semester integer;
