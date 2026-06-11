CREATE INDEX idx_student_data ON student (last_name, first_name);

CREATE INDEX idx_building_address ON building (address);

CREATE INDEX idx_employee_date ON employee (hire_date);

INSERT INTO student (first_name, last_name, birth_date, gpa, gender, program_id)
VALUES ('Krystyna2', 'Zielińska', '2001-02-12', 4.8, 'F', 5);

INSERT INTO course (name, ects, lecturer, semester)
VALUES ('Programowanie Obiektowe', 5, 'dr inż. Jan Kowalski', 3);

SELECT first_name, last_name, gpa
FROM student
ORDER BY gpa DESC
LIMIT 3;

SELECT r.room_number, r.capacity, b.name AS building, b.address
FROM room r
         JOIN building b ON r.building_id = b.id
WHERE r.capacity > 20;

SELECT p.name, COUNT(s.index_number) AS enrolled_count
FROM program p
         LEFT JOIN student s ON p.id = s.program_id
GROUP BY p.name;

SELECT first_name, last_name
FROM student
WHERE index_number NOT IN (SELECT student_id FROM enrollment);

UPDATE course
SET ects = ects + 1
WHERE semester = 3;

SELECT
    s.index_number,
    s.last_name || ' ' || s.first_name AS student_full_name,
    s.gpa,
    p.name AS program_name,
    c.name AS course_name,
    c.ects,
    c.lecturer AS lecturer,
    b.name AS building_name,
    r.room_number AS room_nr,
    r.type AS room_type
FROM student s
         JOIN program p ON s.program_id = p.id
         JOIN enrollment e ON s.index_number = e.student_id
         JOIN course c ON e.course_id = c.id
         LEFT JOIN room r ON r.type = 'Wykladowa'
         LEFT JOIN building b ON r.building_id = b.id
WHERE s.gpa > 3.5
  AND b.build_year > 2010
ORDER BY p.name, s.last_name;
