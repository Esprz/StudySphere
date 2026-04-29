"""Pure offline-pipeline unit tests that do not require live DB/Redis services."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.config import OfflinePipelineConfig
from src.feature_store import FeatureStore
from src.service import build_scheduler_job_specs


class _NoopConnection:
    def cursor(self):  # pragma: no cover - not used by these pure tests
        raise NotImplementedError


class TestOfflinePipelineService(unittest.TestCase):
    """Validate pure helpers that define scheduler shape and version ids."""

    def test_build_scheduler_job_specs_matches_spec4_defaults(self) -> None:
        specs = build_scheduler_job_specs()
        self.assertEqual([spec["job_id"] for spec in specs], [
            "cf-refresh",
            "popularity",
            "cache-warmup",
            "partition-maintenance",
        ])
        self.assertEqual(specs[0]["trigger"], {"hour": 2, "minute": 0})
        self.assertEqual(specs[1]["trigger"], {"minute": 0})

    def test_feature_store_version_tag_is_timestamped(self) -> None:
        store = FeatureStore(_NoopConnection())
        version = store.create_version_tag(
            "cf",
            computed_at=datetime(2026, 4, 28, 2, 15, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(version, "cf_20260428T021530Z")

    def test_config_reads_new_session_redis_defaults(self) -> None:
        config = OfflinePipelineConfig.from_env()
        self.assertIsInstance(config.redis_session_port, int)
        self.assertIsInstance(config.cleanup_grace_period_seconds, int)


if __name__ == "__main__":
    unittest.main()
