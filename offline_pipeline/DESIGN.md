## Offline Pipeline Design

### Purpose

The offline pipeline converts raw behavioral history into serving-time recommendation features.

It is intentionally separate from:

- `etl_service`: event ingestion and vector-side enrichment
- `recommender_system`: online recall/ranking
- `data_simulator`: synthetic data generation
- `simulator_db_adapter`: simulator output to DB import/export

### Inputs

Primary input table:

- `etl_behavior_events`

Supporting app tables:

- `"User"`
- `"Post"`
- `"Like"`
- `"Save"`
- `"Comment"`

### Core Feature Families

#### CF

Built from recent behavior, default window `90 days`.

Output tables:

- `user_item_interest`
- `user_user_similarity`
- `item_item_similarity`
- `user_similar_users`
- `item_similar_items`
- `user_interested_items`

Activation metadata:

- `feature_metadata.feature_name = 'cf'`
- Redis session key `offline:cf:active_version`

#### Trending

Built from recent behavior, default window `24 hours`.

Output tables:

- `item_popularity`
- `trending_items`

Activation metadata:

- `feature_metadata.feature_name = 'trending'`
- Redis session key `offline:trending:active_version`

Serving cache:

- Redis cache key `rec:trending`

### Job Graph

```text
partition-maintenance
  ensures etl_behavior_events is partitioned
  ensures current/next month partitions exist

cf-refresh
  -> feature-processor
     reads etl_behavior_events
     writes user_item_interest
     writes user_interested_items
  -> similarity-builder
     reads user_item_interest(version)
     writes user_user_similarity
     writes item_item_similarity
     writes user_similar_users
     writes item_similar_items
  -> cutover
     updates feature_metadata(cf)
     writes offline:cf:active_version

popularity
  reads etl_behavior_events
  writes item_popularity
  writes trending_items(version)
  -> cutover
     updates feature_metadata(trending)
     writes offline:trending:active_version
     writes rec:trending

cache-warmup
  reads feature_metadata(cf)
  reads user_item_interest/versioned item_similar_items
  writes rec:feed:{user_id}

cleanup-versions
  deletes non-active rows from one feature family
```

### Versioning Model

Each feature family uses timestamped versions:

- `cf_YYYYMMDDTHHMMSSZ`
- `trending_YYYYMMDDTHHMMSSZ`

Write path:

1. Generate a new version tag.
2. Write all rows using that version.
3. Update `feature_metadata`.
4. Write the active-version marker into Redis session.
5. Optionally clean up older versions after a grace period.

This avoids partial reads from online services during recomputation.

### Redis Contract

Redis cache DB:

- `rec:trending`: JSON array of top trending post ids
- `rec:feed:{user_id}`: JSON array of warmed feed candidates

Redis session DB:

- `offline:cf:active_version`
- `offline:trending:active_version`

### Partitioning Strategy

`etl_behavior_events` is monthly range-partitioned on `processed_at`.

Child tables follow:

- `etl_behavior_events_YYYY_MM`

Why this matters:

- bounded scans for `90 day` and `24 hour` windows
- easier long-term retention and maintenance
- cheaper future offline runs as data volume grows

### Event Deduplication

Because a partitioned Postgres table cannot enforce a simple global unique index on `event_id` unless the partition key participates, this design uses:

- `etl_behavior_event_keys`

That registry stores one row per `event_id` and is checked first by ETL/import paths. The partitioned event table then stores the full event payload.

### Failure Model

- If a feature build fails before cutover, `feature_metadata` stays on the previous version.
- Cleanup is safe only after a new version is active.
- Cache warmup depends on an active CF version; if none exists, it skips rather than writing partial garbage.

### Scheduler Model

The scheduler is APScheduler-based, single service, UTC-clocked.

It is intentionally simple:

- no Airflow
- no distributed DAG executor
- one process, cron triggers, explicit DB/Redis writes

This matches the project’s Spec 4-7 direction.
