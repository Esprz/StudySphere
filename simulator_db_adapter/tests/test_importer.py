"""DB bundle importer tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from simulator_db_adapter.importer import import_db_bundle, resolve_bundle_dir


class _FakeCursor:
    def __init__(self, connection: "_FakeConnection") -> None:
        self.connection = connection
        self.rowcount = 0
        self._fetchone = {"exists": False}

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params=None) -> None:
        self.connection.executed.append(("execute", sql, params))
        self.rowcount = 1
        if "SELECT EXISTS" in sql:
            self._fetchone = {"exists": False}
        elif "RETURNING event_id" in sql:
            self._fetchone = {"event_id": "inserted"}
        else:
            self._fetchone = None

    def executemany(self, sql: str, payload) -> None:
        payload = list(payload)
        self.connection.executed.append(("executemany", sql, payload))
        self.rowcount = len(payload)

    def fetchone(self):
        return self._fetchone


class _FakeConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, str, object]] = []
        self.autocommit = False
        self.committed = False

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def commit(self) -> None:
        self.committed = True


class TestImporter(unittest.TestCase):
    """Validate bundle resolution and import ordering."""

    def test_resolve_bundle_dir_accepts_run_dir_and_bundle_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sim_bundle_resolve_") as tmp:
            root = Path(tmp)
            bundle_dir = root / "db_bundle"
            bundle_dir.mkdir()
            (bundle_dir / "db_bundle_manifest.json").write_text("{}", encoding="utf-8")
            self.assertEqual(resolve_bundle_dir(root), bundle_dir.resolve())
            self.assertEqual(resolve_bundle_dir(bundle_dir), bundle_dir.resolve())

    def test_import_db_bundle_runs_tables_in_dependency_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sim_bundle_import_") as tmp:
            bundle = Path(tmp)
            _write_manifest(bundle)
            _write_jsonl(bundle / "users.jsonl", [{"user_id": "u1", "username": "u1", "display_name": "U1", "email": "u1@sim.local", "password_hash": "x", "goalTags": [], "habitLevel": 0.5, "timezone": "UTC", "created_at": "2026-04-01T00:00:00+00:00", "updated_at": "2026-04-01T00:00:00+00:00"}])
            _write_jsonl(bundle / "goals.jsonl", [{"goal_id": "g1", "content": "goal", "user_id": "u1", "status": "ONGOING", "created_at": "2026-04-01T00:00:00+00:00"}])
            _write_jsonl(bundle / "posts.jsonl", [{"post_id": "p1", "title": "t", "content": "c", "user_id": "u1", "image": None, "extra": None, "topicTags": [], "difficulty": 1, "created_at": "2026-04-01T00:00:00+00:00", "updated_at": "2026-04-01T00:00:00+00:00"}])
            _write_jsonl(bundle / "follows.jsonl", [{"follow_id": "f1", "follower_id": "u1", "followee_id": "u2", "created_at": "2026-04-01T00:00:00+00:00"}])
            _write_jsonl(bundle / "comments.jsonl", [{"comment_id": "c1", "content": "x", "user_id": "u1", "post_id": "p1", "parent_id": None, "created_at": "2026-04-01T00:00:00+00:00"}])
            _write_jsonl(bundle / "likes.jsonl", [{"like_id": "l1", "post_id": "p1", "user_id": "u1", "created_at": "2026-04-01T00:00:00+00:00"}])
            _write_jsonl(bundle / "saves.jsonl", [{"save_id": "s1", "post_id": "p1", "user_id": "u1", "created_at": "2026-04-01T00:00:00+00:00"}])
            _write_jsonl(bundle / "focus_times.jsonl", [{"ft_id": "ft1", "start": "2026-04-01T00:00:00+00:00", "end": None, "user_id": "u1", "goal_id": "g1", "tags": [], "sourceTrigger": "post:p1", "created_at": "2026-04-01T00:00:00+00:00"}])

            fake_connection = _FakeConnection()
            with patch("simulator_db_adapter.importer.psycopg.connect", return_value=fake_connection):
                result = import_db_bundle(
                    bundle_dir=bundle,
                    database_url="postgresql://example",
                )

            self.assertTrue(fake_connection.committed)
            self.assertEqual(result.imported_counts["users"], 1)
            ordered_sql = [entry[1] for entry in fake_connection.executed]
            insert_sql = [sql for sql in ordered_sql if sql.strip().startswith('INSERT INTO "')]
            self.assertIn('INSERT INTO "User"', insert_sql[0])
            self.assertIn('INSERT INTO "Goal"', insert_sql[1])
            self.assertIn('INSERT INTO "Post"', insert_sql[2])

    def test_import_db_bundle_dry_run_reports_counts_without_db(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sim_bundle_dry_run_") as tmp:
            bundle = Path(tmp)
            _write_manifest(bundle, users=2)
            result = import_db_bundle(
                bundle_dir=bundle,
                database_url="postgresql://example",
                dry_run=True,
            )
            self.assertTrue(result.dry_run)
            self.assertEqual(result.imported_counts["users"], 2)


def _write_manifest(bundle: Path, **overrides: int) -> None:
    counts = {
        "users": 1,
        "goals": 1,
        "posts": 1,
        "follows": 1,
        "comments": 1,
        "likes": 1,
        "saves": 1,
        "focus_times": 1,
    }
    counts.update(overrides)
    (bundle / "db_bundle_manifest.json").write_text(
        json.dumps({"record_counts": counts}, sort_keys=True),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


if __name__ == "__main__":
    unittest.main()
