CREATE OR REPLACE FUNCTION refresh_user_item_interest(
    v TEXT,                              -- target version to write
    half_life_days DOUBLE PRECISION DEFAULT 14.0,   -- time decay half-life (days)
    w_view  DOUBLE PRECISION DEFAULT 1.0,           -- weight for VIEW
    w_like  DOUBLE PRECISION DEFAULT 3.0,           -- weight for LIKE
    w_save  DOUBLE PRECISION DEFAULT 4.0,           -- weight for SAVE
    w_search DOUBLE PRECISION DEFAULT 0.5,          -- weight for SEARCH
    min_score DOUBLE PRECISION DEFAULT 0.01,        -- discard noisy low scores
    full_refresh BOOLEAN DEFAULT TRUE,              -- TRUE: delete old version first
    normalize_per_user BOOLEAN DEFAULT TRUE         -- TRUE: normalize scores per user
)
RETURNS void AS $$
BEGIN
    -- If full refresh, clear the existing records for this version
    IF full_refresh THEN
        DELETE FROM user_item_interest WHERE version = v;
    END IF;

    -- Step 1: select behavior events that map to posts
    WITH ev AS (
        SELECT
            user_id,
            post_id,
            event_type,
            processed_at
        FROM etl_behavior_events
        WHERE post_id IS NOT NULL
    ),

    -- Step 2: assign weights and apply time decay
    scored AS (
        SELECT
            user_id,
            post_id,
            (
                CASE UPPER(event_type)
                    WHEN 'VIEW'   THEN w_view
                    WHEN 'LIKE'   THEN w_like
                    WHEN 'SAVE'   THEN w_save
                    WHEN 'SEARCH' THEN w_search
                    ELSE 0.0
                END
            )
            *
            -- exponential time decay: 0.5^(age_days / half_life_days)
            POWER(
                0.5,
                GREATEST(
                    0.0,
                    (EXTRACT(EPOCH FROM (NOW() - processed_at)) / 86400.0) / half_life_days
                )
            ) AS score
        FROM ev
    ),

    -- Step 3: aggregate by (user, post)
    agg AS (
        SELECT user_id, post_id, SUM(score) AS raw_score
        FROM scored
        GROUP BY user_id, post_id
        HAVING SUM(score) >= min_score
    ),

    -- Step 4: optionally normalize scores per user into [0,1]
    norm AS (
        SELECT
            a.user_id,
            a.post_id,
            CASE
                WHEN NOT normalize_per_user THEN a.raw_score
                ELSE
                    CASE
                        WHEN m.max_score > 0 THEN a.raw_score / m.max_score
                        ELSE 0
                    END
            END AS interest_score
        FROM agg a
        LEFT JOIN (
            SELECT user_id, MAX(raw_score) AS max_score
            FROM agg
            GROUP BY user_id
        ) m USING (user_id)
    )

    -- Step 5: insert into user_item_interest, upsert on conflict
    INSERT INTO user_item_interest (user_id, item_id, interest_score, version)
    SELECT user_id, post_id, interest_score, v
    FROM norm
    ON CONFLICT (user_id, item_id, version)
    DO UPDATE SET interest_score = EXCLUDED.interest_score;

END;
$$ LANGUAGE plpgsql;
