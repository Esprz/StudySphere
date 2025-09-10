CREATE OR REPLACE FUNCTION refresh_user_similarity(v TEXT)
RETURNS void AS $$
BEGIN
    WITH user_counts AS (
        SELECT user_id, COUNT(*) AS item_count
        FROM user_item_interest
        WHERE interest_score > 0 AND version = v
        GROUP BY user_id
    ),
    user_pairs AS (
        SELECT ui1.user_id AS u1,
               ui2.user_id AS u2,
               COUNT(*) AS inter_count
        FROM user_item_interest ui1
        JOIN user_item_interest ui2
          ON ui1.item_id = ui2.item_id
         AND ui1.user_id < ui2.user_id
         AND ui1.version = v
         AND ui2.version = v
        WHERE ui1.interest_score > 0 AND ui2.interest_score > 0
        GROUP BY ui1.user_id, ui2.user_id
    )
    INSERT INTO user_user_similarity (userA_id, userB_id, similarity_score, version)
    SELECT u1, u2,
           inter_count / SQRT(c1.item_count * c2.item_count)::float AS sim,
           v
    FROM user_pairs
    JOIN user_counts c1 ON u1 = c1.user_id
    JOIN user_counts c2 ON u2 = c2.user_id
    ON CONFLICT (userA_id, userB_id, version)
    DO UPDATE SET similarity_score = EXCLUDED.similarity_score;
END;
$$ LANGUAGE plpgsql;
