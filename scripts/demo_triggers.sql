CREATE OR REPLACE FUNCTION demo.log_employee_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO demo.employee_audit (employee_id, operation) VALUES (NEW.id, 'INSERT');
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO demo.employee_audit (employee_id, operation) VALUES (NEW.id, 'UPDATE');
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO demo.employee_audit (employee_id, operation) VALUES (OLD.id, 'DELETE');
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER demo_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON demo.employee
    FOR EACH ROW EXECUTE FUNCTION demo.log_employee_changes();

CREATE OR REPLACE FUNCTION demo.legacy_sync_noop()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE demo.employee SET last_name = NEW.last_name WHERE id = NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER demo_legacy_sync_trigger
    AFTER UPDATE ON demo.employee
    FOR EACH ROW EXECUTE FUNCTION demo.legacy_sync_noop();

ALTER TABLE demo.employee DISABLE TRIGGER demo_legacy_sync_trigger;
