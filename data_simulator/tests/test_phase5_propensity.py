"""Phase 5 propensity logging tests."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import RunConfig
from core.time import clip_0_1
from pipeline.build_truth import build_truth


class TestPhase5Propensity(unittest.TestCase):
    """Validate propensity completeness and consistency for stochastic decisions."""

    def setUp(self) -> None:
        design_final_dir = Path(__file__).resolve().parents[1] / "default_source_bundle"
        self.sources = load_sources(design_final_dir)
        self.now = datetime(2026, 4, 22, 15, 0, tzinfo=timezone.utc)

    def test_propensity_fields_are_present(self) -> None:
        """Every logged stochastic decision should include deterministic/final policy fields."""
        state = build_truth(
            RunConfig(seed=5201, user_count=24, timeline_ticks=3, items_per_session=12),
            self.sources,
            now=self.now,
        )
        self.assertTrue(state.propensity_logs)
        for log in state.propensity_logs:
            self.assertIsNotNone(log.deterministic_prob)
            self.assertIsNotNone(log.final_prob)
            self.assertIsNotNone(log.prob_jitter)
            self.assertIsNotNone(log.sampled_outcome)
            self.assertEqual(log.sampling_policy, "internal_heuristic_v1")
            self.assertEqual(log.sampling_policy_version, "1.0")
            self.assertTrue(0.0 <= float(log.final_prob) <= 1.0)

    def test_negative_outcomes_keep_probability_logs(self) -> None:
        """Sampled-false decisions should still keep full propensity information."""
        state = build_truth(
            RunConfig(seed=5202, user_count=28, timeline_ticks=3, items_per_session=12),
            self.sources,
            now=self.now,
        )
        negatives = [log for log in state.propensity_logs if log.sampled_outcome is False]
        self.assertTrue(negatives, "Expected at least one sampled-false propensity log")
        for log in negatives:
            self.assertIsNotNone(log.deterministic_prob)
            self.assertIsNotNone(log.final_prob)
            self.assertIsNotNone(log.prob_jitter)
            self.assertEqual(log.sampling_policy, "internal_heuristic_v1")
            self.assertEqual(log.sampling_policy_version, "1.0")

    def test_final_probability_matches_used_sampling_probability(self) -> None:
        """`final_prob` should equal the exact probability expression used for sampling."""
        state = build_truth(
            RunConfig(seed=5203, user_count=22, timeline_ticks=3, items_per_session=10),
            self.sources,
            now=self.now,
        )
        self.assertTrue(state.propensity_logs)
        for log in state.propensity_logs:
            deterministic = float(log.deterministic_prob or 0.0)
            jitter = float(log.prob_jitter or 0.0)
            if log.decision_stage == "view_decision":
                floor = float(log.metadata.get("off_interest_click_floor", 0.0))
                expected = clip_0_1(max(deterministic, floor) + jitter)
            else:
                expected = clip_0_1(deterministic + jitter)
            self.assertAlmostEqual(float(log.final_prob or 0.0), expected, delta=2e-6)

    def test_policy_fields_are_consistent_across_entities(self) -> None:
        """Interaction/focus/propensity records should use consistent policy identifiers."""
        state = build_truth(
            RunConfig(seed=5204, user_count=20, timeline_ticks=3, items_per_session=10),
            self.sources,
            now=self.now,
        )
        stochastic_interactions = [item for item in state.interactions if item.deterministic_prob is not None]
        self.assertTrue(stochastic_interactions)
        for interaction in stochastic_interactions:
            self.assertEqual(interaction.sampling_policy, "internal_heuristic_v1")
            self.assertEqual(interaction.sampling_policy_version, "1.0")

        for focus in state.focus_sessions:
            self.assertEqual(focus.sampling_policy, "internal_heuristic_v1")
            self.assertEqual(focus.sampling_policy_version, "1.0")

        self.assertTrue(state.propensity_logs)
        for log in state.propensity_logs:
            self.assertEqual(log.sampling_policy, "internal_heuristic_v1")
            self.assertEqual(log.sampling_policy_version, "1.0")


if __name__ == "__main__":
    unittest.main()
