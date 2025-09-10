CREATE OR REPLACE FUNCTION refresh_topk_user_neighbors(v TEXT, k INT)
RETURNS void AS $$
BEGIN
    WITH pairs AS (
        SELECT userA_id AS user_id, userB_id AS neighbor_id, similarity_score
        FROM user_user_similarity WHERE version = v
        UNION ALL
        SELECT userB_id, userA_id, similarity_score
        FROM user_user_similarity WHERE version = v
    ),
    ranked AS (
        SELECT user_id, neighbor_id, similarity_score,
               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY similarity_score DESC) AS rn
        FROM pairs
    )
    INSERT INTO user_similar_users (user_id, similar_user_id, similarity_score, rank, version)
    SELECT user_id, neighbor_id, similarity_score, rn, v
    FROM ranked
    WHERE rn <= k AND user_id <> neighbor_id
    ON CONFLICT (user_id, similar_user_id, rank, version)
    DO UPDATE SET similarity_score = EXCLUDED.similarity_score;
END;
$$ LANGUAGE plpgsql;
