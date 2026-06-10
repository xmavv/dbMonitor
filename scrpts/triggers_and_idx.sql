CREATE TABLE audyt_pracownik (
    id SERIAL PRIMARY KEY,
    pracownik_id INTEGER,
    operacja VARCHAR(10),
    data_zmiany TIMESTAMP DEFAULT now()
);

CREATE OR REPLACE FUNCTION loguj_zmiany_pracownika()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audyt_pracownik (pracownik_id, operacja) VALUES (NEW.id, 'INSERT');
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audyt_pracownik (pracownik_id, operacja) VALUES (NEW.id, 'UPDATE');
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audyt_pracownik (pracownik_id, operacja) VALUES (OLD.id, 'DELETE');
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pracownik_audyt_trigger
AFTER INSERT OR UPDATE OR DELETE ON pracownik
FOR EACH ROW EXECUTE FUNCTION loguj_zmiany_pracownika();

CREATE OR REPLACE FUNCTION aktualizuj_liczbe_studentow()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE kierunek SET liczba_studentow = COALESCE(liczba_studentow, 0) + 1 WHERE id = NEW.kierunek_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE kierunek SET liczba_studentow = COALESCE(liczba_studentow, 0) - 1 WHERE id = OLD.kierunek_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER student_kierunek_trigger
AFTER INSERT OR DELETE ON student
FOR EACH ROW EXECUTE FUNCTION aktualizuj_liczbe_studentow();

CREATE INDEX idx_student_kierunek_id ON student(kierunek_id);
CREATE INDEX idx_zapisy_student_id ON zapisy_na_przedmioty(student_id);
CREATE INDEX idx_zapisy_przedmiot_id ON zapisy_na_przedmioty(przedmiot_id);
CREATE INDEX idx_sala_budynek_id ON sala(budynek_id);

CREATE INDEX idx_student_plec_nieuzywany ON student(plec);
CREATE INDEX idx_doktorant_rok_nieuzywany ON doktorant(rok_rozpoczecia);