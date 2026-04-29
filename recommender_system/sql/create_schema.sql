CREATE TABLE IF NOT EXISTS feature_metadata (
    feature_name VARCHAR(100) PRIMARY KEY,
    active_version VARCHAR(50) NOT NULL,
    computed_at TIMESTAMP NOT NULL,
    row_count INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
);

/* 
Collaborative Filtering Recommendations
Tables to store similar users and similar items
*/

CREATE TABLE IF NOT EXISTS item_item_similarity (
    itemA_id VARCHAR(255) NOT NULL,
    itemB_id VARCHAR(255) NOT NULL,
    similarity_score FLOAT NOT NULL,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (itemA_id, itemB_id, version)
);

CREATE TABLE IF NOT EXISTS user_user_similarity (
    userA_id VARCHAR(255) NOT NULL,
    userB_id VARCHAR(255) NOT NULL,
    similarity_score FLOAT NOT NULL,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (userA_id, userB_id, version)
);

CREATE TABLE IF NOT EXISTS user_item_interest (
    user_id VARCHAR(255) NOT NULL,
    item_id VARCHAR(255) NOT NULL,
    interest_score FLOAT NOT NULL,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, item_id, version)
);

CREATE TABLE IF NOT EXISTS user_similar_users (
    user_id VARCHAR(255) NOT NULL,
    similar_user_id VARCHAR(255) NOT NULL,
    similarity_score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, similar_user_id, rank, version)
);

CREATE TABLE IF NOT EXISTS item_similar_items (
    item_id VARCHAR(255) NOT NULL,
    similar_item_id VARCHAR(255) NOT NULL,
    similarity_score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id, similar_item_id, rank, version)
);

CREATE TABLE IF NOT EXISTS user_interested_items (
    user_id VARCHAR(255) NOT NULL,
    item_id VARCHAR(255) NOT NULL,
    interest_score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, item_id, rank, version)
);
CREATE INDEX IF NOT EXISTS interested_items_user_idx ON user_interested_items (user_id);

/*
Trending Recommendations
*/

CREATE TABLE IF NOT EXISTS item_popularity (
    item_id VARCHAR(255) PRIMARY KEY,
    popularity INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trending_items (
    item_id VARCHAR(255) NOT NULL,
    popularity FLOAT NOT NULL,
    version VARCHAR(50) NOT NULL,
    rank INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id, version)
);

CREATE INDEX IF NOT EXISTS trending_items_popularity_idx ON trending_items (popularity DESC);
CREATE INDEX IF NOT EXISTS feature_metadata_computed_at_idx ON feature_metadata (computed_at DESC);
