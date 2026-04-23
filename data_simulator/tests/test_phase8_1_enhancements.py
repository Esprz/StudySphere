"""Phase 8.1 structured-truth enhancement tests."""

from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import RunConfig, SourceBundle
from pipeline.build_truth import build_truth


class TestPhase81Enhancements(unittest.TestCase):
    """Validate language-style, post-style, goal-relation, and comment-reply enhancements."""

    def setUp(self) -> None:
        self.design_final_dir = Path(__file__).resolve().parents[1] / "design" / "design_final"
        self.sources = load_sources(self.design_final_dir)
        self.now = datetime(2026, 4, 22, 19, 0, tzinfo=timezone.utc)

    def test_user_language_style_fields_are_generated_from_persona_axes(self) -> None:
        """User style fields should be generated and constrained by persona-axis enums."""
        state = build_truth(
            RunConfig(seed=8811, user_count=30, timeline_ticks=2, items_per_session=8),
            self.sources,
            now=self.now,
        )
        fields = {item["name"]: item for item in self.sources.require("persona_axes").get("fields", [])}
        allowed_families = set(fields["writing_style_family"]["allowed_values"])
        allowed_registers = set(fields["register_level"]["allowed_values"])

        self.assertTrue(state.users)
        for user in state.users:
            self.assertIn(user.writing_style_family, allowed_families)
            self.assertIn(user.register_level, allowed_registers)

    def test_post_style_and_goal_relation_fields_are_generated(self) -> None:
        """Post style and goal relation should be generated from content taxonomy values."""
        state = build_truth(
            RunConfig(seed=8812, user_count=30, timeline_ticks=2, items_per_session=8),
            self.sources,
            now=self.now,
        )
        taxonomy = self.sources.require("content_taxonomy")
        allowed_styles = set(taxonomy.get("post_styles", []))
        allowed_relations = set(taxonomy.get("goal_relation_types", []))

        self.assertTrue(state.posts)
        for post in state.posts:
            self.assertIn(post.post_style, allowed_styles)
            self.assertIn(post.goal_relation_type, allowed_relations)

    def test_post_style_is_modeled_separately_from_format(self) -> None:
        """Post style should behave as a separate semantic field rather than a format alias."""
        state = build_truth(
            RunConfig(seed=8815, user_count=80, timeline_ticks=2, items_per_session=8),
            self.sources,
            now=self.now,
        )
        self.assertTrue(state.posts)

        # 1) Field-level separation: they should not collapse to the same token.
        for post in state.posts:
            self.assertNotEqual(post.post_style, post.format)

        # 2) Behavioral separation: same format should map to multiple post styles in a non-trivial batch.
        styles_by_format: dict[str, set[str]] = {}
        for post in state.posts:
            styles_by_format.setdefault(post.format, set()).add(post.post_style)
        self.assertTrue(any(len(styles) >= 2 for styles in styles_by_format.values()))

    def test_off_topic_noise_share_is_bounded(self) -> None:
        """Off-topic posts should exist but remain a minority share."""
        state = build_truth(
            RunConfig(seed=8813, user_count=60, timeline_ticks=2, items_per_session=10),
            self.sources,
            now=self.now,
        )
        self.assertTrue(state.posts)
        off_topic_count = sum(1 for post in state.posts if post.goal_relation_type == "off_topic_noise")
        off_topic_share = off_topic_count / float(len(state.posts))

        self.assertGreaterEqual(off_topic_share, 0.02)
        self.assertLessEqual(off_topic_share, 0.35)

    def test_goal_relation_sampling_is_source_driven(self) -> None:
        """Changing goal-relation sampling config should change generated relation mix."""
        tuned_sources = copy.deepcopy(self.sources.sources)
        tuned_sources["content_taxonomy"]["goal_relation_sampling"] = {
            "off_topic_base": 0.95,
            "off_topic_exploration_weight": 0.0,
            "on_goal_base_with_goals": 0.0,
            "on_goal_exploration_weight": 0.0,
            "on_goal_base_without_goals": 0.0,
        }
        tuned_bundle = SourceBundle(base_path=self.sources.base_path, sources=tuned_sources)

        state = build_truth(
            RunConfig(seed=8816, user_count=40, timeline_ticks=1, items_per_session=8),
            tuned_bundle,
            now=self.now,
        )
        self.assertTrue(state.posts)
        off_topic_share = sum(1 for post in state.posts if post.goal_relation_type == "off_topic_noise") / float(
            len(state.posts)
        )
        self.assertGreaterEqual(off_topic_share, 0.80)

    def test_post_style_mapping_is_source_driven(self) -> None:
        """Changing post-style mapping config should directly control sampled post styles."""
        tuned_sources = copy.deepcopy(self.sources.sources)
        tuned_sources["content_taxonomy"]["goal_relation_sampling"] = {
            "off_topic_base": 0.0,
            "off_topic_exploration_weight": 0.0,
            "on_goal_base_with_goals": 1.0,
            "on_goal_exploration_weight": 0.0,
            "on_goal_base_without_goals": 1.0,
        }
        tuned_sources["content_taxonomy"]["post_style_by_goal_relation"] = {
            "on_goal": ["question_help"],
            "interest_adjacent": ["resource_share"],
            "off_topic_noise": ["reflection"],
        }
        tuned_bundle = SourceBundle(base_path=self.sources.base_path, sources=tuned_sources)

        state = build_truth(
            RunConfig(seed=8817, user_count=30, timeline_ticks=1, items_per_session=8),
            tuned_bundle,
            now=self.now,
        )
        self.assertTrue(state.posts)
        self.assertTrue(all(post.goal_relation_type == "on_goal" for post in state.posts))
        self.assertTrue(all(post.post_style == "question_help" for post in state.posts))

    def test_comment_reply_metadata_is_consistent_when_present(self) -> None:
        """Reply metadata should be causally and structurally consistent for comment events."""
        tuned_sources = copy.deepcopy(self.sources.sources)
        tuned_sources["session_dynamics"]["parameters"]["base_view_probability"] = 1.0
        tuned_sources["session_dynamics"]["parameters"]["quick_bounce_dwell_threshold_ms"] = 1000
        tuned_sources["session_dynamics"]["parameters"]["detail_dwell_ms_range"] = [12000, 12000]
        tuned_sources["session_dynamics"]["parameters"]["reply_probability_base"] = 0.95
        tuned_sources["session_dynamics"]["parameters"]["reply_probability_social_affinity_weight"] = 0.05
        tuned_sources["session_dynamics"]["parameters"]["top_level_comment_delay_seconds_range"] = [10, 20]
        tuned_sources["session_dynamics"]["parameters"]["reply_comment_delay_seconds_range"] = [5, 15]
        tuned_sources["jitter_noise_rules"]["rules"]["view_probability_jitter"]["range"] = [0.0, 0.0]
        tuned_bundle = SourceBundle(base_path=self.sources.base_path, sources=tuned_sources)

        state = build_truth(
            RunConfig(seed=8814, user_count=32, timeline_ticks=4, items_per_session=12),
            tuned_bundle,
            now=self.now,
        )
        comments = [item for item in state.interactions if item.event_type == "comment"]
        self.assertTrue(comments)

        interactions_by_id = {item.interaction_id: item for item in state.interactions}
        replies = [item for item in comments if item.reply_to_interaction_id is not None]
        self.assertTrue(replies)

        for reply in replies:
            parent = interactions_by_id[reply.reply_to_interaction_id]
            self.assertEqual(parent.event_type, "comment")
            self.assertEqual(parent.post_id, reply.post_id)
            self.assertLessEqual(parent.timestamp, reply.timestamp)
            self.assertEqual(reply.reply_to_user_id, parent.user_id)
            self.assertIsNotNone(reply.thread_depth)
            self.assertGreaterEqual(int(reply.thread_depth), 1)
            self.assertLessEqual(int(reply.thread_depth), 3)
            self.assertIsNotNone(reply.reply_delay_seconds)
            self.assertGreaterEqual(int(reply.reply_delay_seconds), 0)
            observed_delay = int((reply.timestamp - parent.timestamp).total_seconds())
            self.assertGreaterEqual(observed_delay, int(reply.reply_delay_seconds))

        top_level = [item for item in comments if item.reply_to_interaction_id is None]
        self.assertTrue(top_level)
        for comment in top_level:
            self.assertIsNone(comment.reply_to_user_id)
            self.assertEqual(int(comment.thread_depth or 0), 0)
            self.assertIsNotNone(comment.reply_delay_seconds)
            self.assertGreaterEqual(int(comment.reply_delay_seconds), 0)


if __name__ == "__main__":
    unittest.main()
