CREATE TABLE IF NOT EXISTS feature_metadata (
    feature_name VARCHAR(100) PRIMARY KEY,
    active_version VARCHAR(50) NOT NULL,
    computed_at TIMESTAMP NOT NULL,
    row_count INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
);
