-- Used by demo_top_queries.py (indexed lookup)
CREATE INDEX idx_demo_student_email_used ON demo.student (email);

-- Never queried on purpose
CREATE INDEX idx_demo_student_gender_unused ON demo.student (gender);

-- Duplicate pair (same column, same opclass)
CREATE INDEX idx_demo_student_dup_a ON demo.student (last_name);
CREATE INDEX idx_demo_student_dup_b ON demo.student (last_name);

-- Large unused index on bloat_table (0 scans until you query marker)
CREATE INDEX idx_demo_bloat_marker_unused ON demo.bloat_table (marker);

ANALYZE demo.student;
ANALYZE demo.bloat_table;
