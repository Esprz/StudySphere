"""Phase 2 ranking and exposure tests."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import ActivityState, RunConfig
from core.random import make_rng
from generators.ranking import build_candidate_pool
from pipeline.build_truth import build_truth


class TestPhase2Ranking(unittest.TestCase):
    def setUp(self) -> None:
        design_final_dir = Path(__file__).resolve().parents[1] / "design" / "design_final"
        self.sources = load_sources(design_final_dir)
        self.now = datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc)

    def test_candidate_pool_has_no_duplicates(self) -> None:
        config = RunConfig(seed=321, user_count=20, timeline_ticks=2, items_per_session=12)
        state = build_truth(config, self.sources, now=self.now)
        self.assertTrue(state.sessions, "Expected at least one session")

        session = state.sessions[0]
        user = next(u for u in state.users if u.user_id == session.user_id)
        goal_id = state.goals_by_user[user.user_id][0].goal_id
        activity = ActivityState(
            activity_id=session.activity_id,
            user_id=user.user_id,
            goal_id=goal_id,
            activity_intent=session.activity_intent,
            topic=session.goal_topic,
            urgency=0.5,
            available_minutes=45,
            target_difficulty=3,
            session_id=session.session_id,
            timestamp=session.started_at,
        )
        pool = build_candidate_pool(user, session, activity, state, make_rng(7))
        post_ids = [p.post_id for p in pool]
        self.assertEqual(len(post_ids), len(set(post_ids)))

    def test_exposure_scores_are_clipped(self) -> None:
        config = RunConfig(seed=222, user_count=15, timeline_ticks=2, items_per_session=10)
        state = build_truth(config, self.sources, now=self.now)
        self.assertTrue(state.exposures)
        for exposure in state.exposures:
            self.assertTrue(0.0 <= exposure.candidate_score <= 1.0)
            self.assertIsNotNone(exposure.deterministic_exposure_score)
            self.assertTrue(0.0 <= float(exposure.deterministic_exposure_score) <= 1.0)

    def test_score_breakdown_is_present(self) -> None:
        config = RunConfig(seed=223, user_count=15, timeline_ticks=2, items_per_session=10)
        state = build_truth(config, self.sources, now=self.now)
        self.assertTrue(state.exposures)
        for exposure in state.exposures:
            self.assertIsInstance(exposure.score_breakdown, dict)
            self.assertIn("topic_match", exposure.score_breakdown)
            self.assertIn("goal_alignment", exposure.score_breakdown)

    def test_ranking_policy_fields_are_emitted(self) -> None:
        config = RunConfig(seed=224, user_count=10, timeline_ticks=2, items_per_session=8)
        state = build_truth(config, self.sources, now=self.now)
        self.assertTrue(state.exposures)
        for exposure in state.exposures:
            self.assertEqual(exposure.ranking_policy, "internal_heuristic_v1")
            self.assertEqual(exposure.ranking_policy_version, "1.0")

    def test_same_seed_produces_stable_exposure_order(self) -> None:
        config = RunConfig(seed=990, user_count=25, timeline_ticks=2, items_per_session=12)
        state_a = build_truth(config, self.sources, now=self.now)
        state_b = build_truth(config, self.sources, now=self.now)

        sig_a = [
            (e.session_id, e.rank_position, e.post_id, e.candidate_score, e.score_jitter)
            for e in state_a.exposures
        ]
        sig_b = [
            (e.session_id, e.rank_position, e.post_id, e.candidate_score, e.score_jitter)
            for e in state_b.exposures
        ]
        self.assertEqual(sig_a, sig_b)


if __name__ == "__main__":
    unittest.main()

