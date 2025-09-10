CREATE OR REPLACE FUNCTION refresh_topk_item_neighbors(v TEXT, k INT)
RETURNS void AS $$
BEGIN
    WITH pairs AS (
        SELECT itemA_id AS item_id, itemB_id AS neighbor_id, similarity_score
        FROM item_item_similarity WHERE version = v
        UNION ALL
        SELECT itemB_id, itemA_id, similarity_score
        FROM item_item_similarity WHERE version = v
    ),
    ranked AS (
        SELECT item_id, neighbor_id, similarity_score,
               ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY similarity_score DESC) AS rn
        FROM pairs
    )
    INSERT INTO item_similar_items (item_id, similar_item_id, similarity_score, rank, version)
    SELECT item_id, neighbor_id, similarity_score, rn, v
    FROM ranked
    WHERE rn <= k AND item_id <> neighbor_id
    ON CONFLICT (item_id, similar_item_id, rank, version)
    DO UPDATE SET similarity_score = EXCLUDED.similarity_score;
END;
$$ LANGUAGE plpgsql;
