CREATE TABLE employee_audit (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER,
    operation VARCHAR(10),
    changed_at TIMESTAMP DEFAULT now()
);

CREATE OR REPLACE FUNCTION log_employee_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO employee_audit (employee_id, operation) VALUES (NEW.id, 'INSERT');
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO employee_audit (employee_id, operation) VALUES (NEW.id, 'UPDATE');
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO employee_audit (employee_id, operation) VALUES (OLD.id, 'DELETE');
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER employee_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON employee
FOR EACH ROW EXECUTE FUNCTION log_employee_changes();

CREATE OR REPLACE FUNCTION update_student_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE program SET student_count = COALESCE(student_count, 0) + 1 WHERE id = NEW.program_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE program SET student_count = COALESCE(student_count, 0) - 1 WHERE id = OLD.program_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER student_program_trigger
AFTER INSERT OR DELETE ON student
FOR EACH ROW EXECUTE FUNCTION update_student_count();

CREATE INDEX idx_student_program_id ON student(program_id);
CREATE INDEX idx_enrollment_student_id ON enrollment(student_id);
CREATE INDEX idx_enrollment_course_id ON enrollment(course_id);
CREATE INDEX idx_room_building_id ON room(building_id);

CREATE INDEX idx_student_gender_unused ON student(gender);
CREATE INDEX idx_phd_student_year_unused ON phd_student(start_year);
