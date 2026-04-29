-- Apply manually during the ETL partitioning migration if the shared table
-- has not already been converted. Runtime code only manages future partitions.
ALTER TABLE etl_behavior_events
PARTITION BY RANGE (processed_at);

CREATE TABLE IF NOT EXISTS etl_behavior_events_2026_04
PARTITION OF etl_behavior_events
FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
