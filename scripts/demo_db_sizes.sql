-- Extra payload for DB Sizes: data vs many indexes
INSERT INTO demo.size_data (payload)
SELECT md5(random()::text || g::text)
FROM generate_series(1, 80000) AS g;

CREATE INDEX idx_demo_size_payload_0 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_1 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_2 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_3 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_4 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_5 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_6 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_7 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_8 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_9 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_10 ON demo.size_data (payload);
CREATE INDEX idx_demo_size_payload_11 ON demo.size_data (payload);

ALTER TABLE demo.bloat_table SET (autovacuum_enabled = false);

ANALYZE demo.size_data;
ANALYZE demo.bloat_table;
