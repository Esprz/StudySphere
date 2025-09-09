-- 索引元数据表
CREATE TABLE IF NOT EXISTS index_metadata (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    dimensions INTEGER NOT NULL,
    num_vectors INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 内容特征表
CREATE TABLE IF NOT EXISTS content_features (
    id VARCHAR(255) PRIMARY KEY,
    embedding FLOAT[],
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以加速向量搜索
CREATE INDEX IF NOT EXISTS content_features_updated_idx ON content_features (updated_at);

-- 用户特征表
CREATE TABLE IF NOT EXISTS user_features (
    id VARCHAR(255) PRIMARY KEY,
    embedding FLOAT[],
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以加速向量搜索
CREATE INDEX IF NOT EXISTS user_features_updated_idx ON user_features (updated_at);

-- 协同过滤用户因子表
CREATE TABLE IF NOT EXISTS user_factors (
    user_id VARCHAR(255) PRIMARY KEY,
    factors FLOAT[],
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 协同过滤物品因子表
CREATE TABLE IF NOT EXISTS item_factors (
    item_id VARCHAR(255) PRIMARY KEY,
    factors FLOAT[],
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 热门物品表
CREATE TABLE IF NOT EXISTS trending_items (
    item_id VARCHAR(255) PRIMARY KEY,
    score FLOAT NOT NULL,
    category VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以加速基于类别的查询
CREATE INDEX IF NOT EXISTS trending_items_category_idx ON trending_items (category);
CREATE INDEX IF NOT EXISTS trending_items_score_idx ON trending_items (score DESC);

-- 用户活跃度表
CREATE TABLE IF NOT EXISTS user_activity (
    user_id VARCHAR(255) PRIMARY KEY,
    activity INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 物品热度表
CREATE TABLE IF NOT EXISTS item_popularity (
    item_id VARCHAR(255) PRIMARY KEY,
    popularity INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户-物品交互表
CREATE TABLE IF NOT EXISTS user_item_interactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    item_id VARCHAR(255) NOT NULL,
    rating FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, item_id)
);

-- 创建索引以加速查询
CREATE INDEX IF NOT EXISTS interactions_user_idx ON user_item_interactions (user_id);
CREATE INDEX IF NOT EXISTS interactions_item_idx ON user_item_interactions (item_id);