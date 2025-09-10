CREATE OR REPLACE FUNCTION refresh_item_similarity(v TEXT)
RETURNS void AS $$
BEGIN
    WITH item_norms AS (
        SELECT item_id, SUM(interest_score^2) AS norm_sq
        FROM user_item_interest
        WHERE interest_score > 0 AND version = v
        GROUP BY item_id
    ),
    item_pairs AS (
        SELECT i1.item_id AS i1,
               i2.item_id AS i2,
               SUM(i1.interest_score * i2.interest_score) AS numerator
        FROM user_item_interest i1
        JOIN user_item_interest i2
          ON i1.user_id = i2.user_id
         AND i1.item_id < i2.item_id
         AND i1.version = v
         AND i2.version = v
        WHERE i1.interest_score > 0 AND i2.interest_score > 0
        GROUP BY i1.item_id, i2.item_id
    )
    INSERT INTO item_item_similarity (itemA_id, itemB_id, similarity_score, version)
    SELECT i1, i2,
           numerator / NULLIF(SQRT(n1.norm_sq * n2.norm_sq), 0)::float AS sim,
           v
    FROM item_pairs
    JOIN item_norms n1 ON i1 = n1.item_id
    JOIN item_norms n2 ON i2 = n2.item_id
    ON CONFLICT (itemA_id, itemB_id, version)
    DO UPDATE SET similarity_score = EXCLUDED.similarity_score;
END;
$$ LANGUAGE plpgsql;
