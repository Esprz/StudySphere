"""Standalone DB adapter tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from simulator_db_adapter.adapter import export_db_bundle


class TestSimulatorDbAdapter(unittest.TestCase):
    """Validate Prisma-compatible export from simulator output artifacts."""

    def test_export_db_bundle_maps_core_entities(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sim_db_adapter_") as tmp:
            root = Path(tmp)
            _write_jsonl(
                root / "users.jsonl",
                [
                    {
                        "user_id": "u_1",
                        "primary_interest": "math",
                        "secondary_interests": ["physics"],
                        "learning_intensity": "high",
                        "diligence_level": 0.8,
                        "created_at": "2026-04-22T12:00:00+00:00",
                    }
                ],
            )
            _write_jsonl(
                root / "posts.jsonl",
                [
                    {
                        "post_id": "p_1",
                        "author_id": "u_1",
                        "topic": "math",
                        "subtopic": "algebra",
                        "post_style": "knowledge_share",
                        "format": "note",
                        "study_context": "exam_prep",
                        "difficulty": 3,
                        "created_at": "2026-04-22T13:00:00+00:00",
                    }
                ],
            )
            _write_jsonl(
                root / "goals.jsonl",
                [
                    {
                        "goal_id": "g_1",
                        "user_id": "u_1",
                        "goal_category": "coursework",
                        "goal_type": "master_topic",
                        "related_topics": ["math", "algebra"],
                        "progress_state": "active",
                        "start_at": "2026-04-20T12:00:00+00:00",
                    }
                ],
            )
            _write_jsonl(
                root / "interactions.jsonl",
                [
                    {
                        "interaction_id": "i_like",
                        "event_type": "like",
                        "user_id": "u_1",
                        "post_id": "p_1",
                        "timestamp": "2026-04-22T13:05:00+00:00",
                    },
                    {
                        "interaction_id": "i_comment",
                        "event_type": "comment",
                        "user_id": "u_1",
                        "post_id": "p_1",
                        "timestamp": "2026-04-22T13:06:00+00:00",
                        "thread_depth": 0,
                    },
                ],
            )
            _write_jsonl(
                root / "focus_sessions.jsonl",
                [
                    {
                        "focus_id": "f_1",
                        "user_id": "u_1",
                        "related_goal_id": "g_1",
                        "topic": "math",
                        "trigger_post_id": "p_1",
                        "started_at": "2026-04-22T13:10:00+00:00",
                        "ended_at": "2026-04-22T13:40:00+00:00",
                    }
                ],
            )
            _write_jsonl(
                root / "propensity_logs.jsonl",
                [
                    {
                        "log_id": "pl_1",
                        "decision_stage": "follow_decision",
                        "user_id": "u_1",
                        "timestamp": "2026-04-22T13:07:00+00:00",
                        "sampled_outcome": True,
                        "metadata": {"target_author_id": "u_2"},
                    }
                ],
            )
            _write_jsonl(
                root / "openai_posts_rendered_posts.jsonl",
                [
                    {
                        "post_id": "p_1",
                        "title": "Rendered title",
                        "content": "Rendered content",
                    }
                ],
            )
            _write_jsonl(
                root / "openai_comment_sets_rendered_comments.jsonl",
                [
                    {
                        "interaction_id": "i_comment",
                        "comment_text": "Rendered comment text",
                    }
                ],
            )

            result = export_db_bundle(input_dir=root)

            self.assertEqual(result.record_counts["users"], 1)
            self.assertEqual(result.record_counts["posts"], 1)
            self.assertEqual(result.record_counts["comments"], 1)
            self.assertEqual(result.record_counts["likes"], 1)
            self.assertEqual(result.record_counts["follows"], 1)

            user_row = _read_first_jsonl(result.files["users"])
            self.assertEqual(user_row["email"], "math_1@sim.studysphere.local")
            self.assertEqual(user_row["habitLevel"], 0.8)

            post_row = _read_first_jsonl(result.files["posts"])
            self.assertEqual(post_row["title"], "Rendered title")
            self.assertEqual(post_row["content"], "Rendered content")

            comment_row = _read_first_jsonl(result.files["comments"])
            self.assertEqual(comment_row["content"], "Rendered comment text")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def _read_first_jsonl(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                return json.loads(stripped)
    raise AssertionError(f"missing row in {path}")


if __name__ == "__main__":
    unittest.main()
