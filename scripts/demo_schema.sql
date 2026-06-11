CREATE TABLE demo.program (
    id serial PRIMARY KEY,
    name varchar(100) NOT NULL,
    student_count integer DEFAULT 0
);

CREATE TABLE demo.course (
    id serial PRIMARY KEY,
    name varchar(100) NOT NULL,
    ects integer NOT NULL DEFAULT 3
);

CREATE TABLE demo.student (
    id bigint PRIMARY KEY,
    first_name varchar(50) NOT NULL,
    last_name varchar(50) NOT NULL,
    email varchar(120) NOT NULL,
    search_token varchar(40) NOT NULL,
    gender char(1) NOT NULL CHECK (gender IN ('M', 'F')),
    program_id integer NOT NULL REFERENCES demo.program (id),
    gpa numeric(3, 1) NOT NULL DEFAULT 3.0
);

CREATE TABLE demo.enrollment (
    id bigserial PRIMARY KEY,
    student_id bigint NOT NULL REFERENCES demo.student (id),
    course_id integer NOT NULL REFERENCES demo.course (id)
);

CREATE TABLE demo.employee (
    id serial PRIMARY KEY,
    first_name varchar(50) NOT NULL,
    last_name varchar(50) NOT NULL
);

CREATE TABLE demo.employee_audit (
    id serial PRIMARY KEY,
    employee_id integer,
    operation varchar(10),
    changed_at timestamp DEFAULT now()
);

CREATE TABLE demo.lock_target (
    id integer PRIMARY KEY,
    val text NOT NULL
);

INSERT INTO demo.lock_target (id, val) VALUES (1, 'seed');

CREATE TABLE demo.bloat_table (
    id bigserial PRIMARY KEY,
    payload text NOT NULL,
    marker integer NOT NULL DEFAULT 0
);

CREATE TABLE demo.size_data (
    id bigserial PRIMARY KEY,
    payload text NOT NULL
);

CREATE INDEX idx_demo_enrollment_student ON demo.enrollment (student_id);
CREATE INDEX idx_demo_enrollment_course ON demo.enrollment (course_id);
CREATE INDEX idx_demo_student_program ON demo.student (program_id);
