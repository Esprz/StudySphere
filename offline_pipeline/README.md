## StudySphere Offline Pipeline

This service owns the Spec 4 offline feature build for StudySphere.

It reads behavioral data from `etl_behavior_events`, computes versioned collaborative-filtering and trending artifacts, writes them into Postgres, and warms serving keys in Redis.

### What It Produces

- `feature_metadata`
- `user_item_interest`
- `user_user_similarity`
- `item_item_similarity`
- `user_similar_users`
- `item_similar_items`
- `user_interested_items`
- `item_popularity`
- `trending_items`
- Redis session markers:
  - `offline:cf:active_version`
  - `offline:trending:active_version`
- Redis cache keys:
  - `rec:trending`
  - `rec:feed:{user_id}`

### Entrypoints

- Scheduler service:
  - `python scheduler.py`
- One-shot CLI:
  - `python -m src.main healthcheck`
  - `python -m src.main run cf-refresh`
  - `python -m src.main run popularity`
  - `python -m src.main run cache-warmup`
  - `python -m src.main run partition-maintenance`
  - `python -m src.main run-all`
  - `python -m src.main cleanup-versions cf <version>`
  - `python -m src.main cleanup-versions trending <version>`

### Default Schedule

- `cf-refresh`: daily at `02:00 UTC`
- `popularity`: hourly
- `cache-warmup`: daily at `05:00 UTC`
- `partition-maintenance`: monthly on day `1` at `01:00 UTC`

### Local Docker Usage

Build and run the offline service:

```bash
docker compose --profile offline build offline-pipeline
docker compose --profile offline run --rm offline-pipeline python -m src.main healthcheck
docker compose --profile offline run --rm offline-pipeline python -m src.main run-all
```

Run only the partition migration / maintenance job:

```bash
docker compose --profile offline run --rm offline-pipeline python -m src.main run partition-maintenance
```

### Validation Checks

Inspect active versions:

```bash
docker compose exec -T db psql -U sy -d studysphere -c \
  "SELECT * FROM feature_metadata ORDER BY feature_name;"
```

Inspect active CF/trending row counts:

```bash
docker compose exec -T db psql -U sy -d studysphere -c \
  "SELECT COUNT(*) FROM user_item_interest WHERE version = (SELECT active_version FROM feature_metadata WHERE feature_name='cf');"

docker compose exec -T db psql -U sy -d studysphere -c \
  "SELECT COUNT(*) FROM trending_items WHERE version = (SELECT active_version FROM feature_metadata WHERE feature_name='trending');"
```

Inspect Redis outputs:

```bash
docker compose exec -T redis-session redis-cli MGET offline:cf:active_version offline:trending:active_version
docker compose exec -T redis-cache redis-cli -n 1 --raw GET rec:trending
docker compose exec -T redis-cache redis-cli -n 1 --scan --pattern 'rec:feed:*' | wc -l
```

Inspect partitioning:

```bash
docker compose exec -T db psql -U sy -d studysphere -c \
  "SELECT EXISTS (SELECT 1 FROM pg_partitioned_table pt JOIN pg_class c ON c.oid = pt.partrelid WHERE c.relname = 'etl_behavior_events');"
```

### Notes

- This service assumes the app tables and recommender feature tables already exist.
- `etl_behavior_events` is migrated to a monthly partitioned table on demand.
- Event deduplication is handled through `etl_behavior_event_keys`, not a global unique index on the partitioned event table.
- Cleanup is explicit today through `cleanup-versions ...`; the scheduler also has the hooks needed to enqueue deferred cleanup after cutover.
