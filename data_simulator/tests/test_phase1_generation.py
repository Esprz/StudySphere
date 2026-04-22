"""Phase 1 generation tests."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import RunConfig
from core.random import make_rng
from core.time import derive_global_time_context
from generators.goals import generate_initial_goals, select_active_goal
from generators.sessions import generate_activity_state, open_session
from generators.users import generate_user_profiles
from pipeline.build_truth import build_truth


class TestPhase1Generation(unittest.TestCase):
    def setUp(self) -> None:
        design_final_dir = Path(__file__).resolve().parents[1] / "design" / "design_final"
        self.sources = load_sources(design_final_dir)
        self.now = datetime(2026, 4, 21, 20, 0, tzinfo=timezone.utc)

    def test_user_generation_ranges_and_enums(self) -> None:
        config = RunConfig(seed=123, user_count=20, timeline_ticks=1)
        rng = make_rng(config.seed)
        users = generate_user_profiles(config, self.sources, rng, now=self.now)
        persona_axes = self.sources.require("persona_axes")
        fields = {f["name"]: f for f in persona_axes["fields"]}

        self.assertEqual(len(users), 20)
        for user in users:
            self.assertEqual(user.primary_interest != "", True)
            self.assertTrue(1 <= len(user.secondary_interests) <= 3)
            self.assertIn(user.learning_intensity, fields["learning_intensity"]["allowed_values"])
            self.assertIn(user.posting_tendency, fields["posting_tendency"]["allowed_values"])
            self.assertIn(user.interaction_tendency, fields["interaction_tendency"]["allowed_values"])
            self.assertTrue(0.0 <= user.sleep_habit_skew <= 1.0)
            self.assertTrue(0.0 <= user.curiosity_level <= 1.0)
            self.assertTrue(0.0 <= user.diligence_level <= 1.0)
            self.assertTrue(0.0 <= user.social_affinity <= 1.0)
            self.assertTrue(0.0 <= user.exploration_rate <= 0.5)
            self.assertTrue(0.0 <= user.drift_rate <= 0.3)

    def test_goal_generation_reproducibility(self) -> None:
        config = RunConfig(seed=77, user_count=8, timeline_ticks=1)
        users_a = generate_user_profiles(config, self.sources, make_rng(config.seed), now=self.now)
        users_b = generate_user_profiles(config, self.sources, make_rng(config.seed), now=self.now)

        goals_a = generate_initial_goals(users_a, self.sources, make_rng(998), now=self.now)
        goals_b = generate_initial_goals(users_b, self.sources, make_rng(998), now=self.now)

        sig_a = [
            (
                uid,
                [(g.goal_id, g.goal_type, g.priority, g.strength, tuple(g.related_topics)) for g in goals]
            )
            for uid, goals in sorted(goals_a.items())
        ]
        sig_b = [
            (
                uid,
                [(g.goal_id, g.goal_type, g.priority, g.strength, tuple(g.related_topics)) for g in goals]
            )
            for uid, goals in sorted(goals_b.items())
        ]
        self.assertEqual(sig_a, sig_b)

    def test_session_contains_world_clock_fields(self) -> None:
        config = RunConfig(seed=5, user_count=15, timeline_ticks=2)
        state = build_truth(config, self.sources, now=self.now)
        self.assertGreater(len(state.sessions), 0)
        for session in state.sessions:
            self.assertTrue(session.wall_clock_time.tzinfo is not None)
            self.assertNotEqual(session.hour_segment, "")
            self.assertIn(session.day_type, ("weekday", "weekend"))
            self.assertNotEqual(session.academic_season, "")
            self.assertNotEqual(session.activity_intent, "")

    def test_activity_state_ranges(self) -> None:
        config = RunConfig(seed=8, user_count=4, timeline_ticks=1)
        users = generate_user_profiles(config, self.sources, make_rng(config.seed), now=self.now)
        goals_by_user = generate_initial_goals(users, self.sources, make_rng(80), now=self.now)
        user = users[0]
        active_goal = select_active_goal(user, goals_by_user[user.user_id], self.now)
        global_ctx = derive_global_time_context(self.now, self.sources.require("world_clock"))
        session = open_session(
            user=user,
            time_tick=self.now,
            active_goal=active_goal,
            global_time_context=global_ctx,
            rng=make_rng(11),
            max_candidate_pool_size=80,
        )
        activity = generate_activity_state(
            user=user,
            session=session,
            active_goal=active_goal,
            sources=self.sources,
            global_time_context=global_ctx,
            rng=make_rng(12),
        )
        self.assertTrue(0.0 <= activity.urgency <= 1.0)
        self.assertTrue(10 <= activity.available_minutes <= 200)
        self.assertTrue(1 <= activity.target_difficulty <= 5)
        self.assertEqual(activity.session_id, session.session_id)
        self.assertEqual(activity.user_id, user.user_id)


if __name__ == "__main__":
    unittest.main()

