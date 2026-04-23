"""Phase 3 interaction simulation tests."""

from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import ActivityState, PostRecord, RunConfig, SourceBundle, UserProfile
from core.random import make_rng
from generators.interactions import compute_off_interest_click_floor, simulate_session_interactions
from pipeline.build_truth import build_truth


class TestPhase3Interactions(unittest.TestCase):
    """Phase-3 behavioral and causal validation tests."""

    def setUp(self) -> None:
        """Load canonical design sources and a fixed reference timestamp."""
        design_final_dir = Path(__file__).resolve().parents[1] / "default_source_bundle"
        self.sources = load_sources(design_final_dir)
        self.now = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)

    def test_no_view_without_exposure(self) -> None:
        """Every view event must reference an existing exposure event."""
        state = build_truth(
            RunConfig(seed=2026, user_count=24, timeline_ticks=3, items_per_session=12),
            self.sources,
            now=self.now,
        )
        exposure_ids = {e.exposure_id for e in state.exposures}
        for interaction in state.interactions:
            if interaction.event_type != "view":
                continue
            self.assertIn(interaction.exposure_id, exposure_ids)

    def test_no_post_view_action_without_view(self) -> None:
        """Post-view actions are only valid after a view for the same exposure."""
        state = build_truth(
            RunConfig(seed=2027, user_count=24, timeline_ticks=3, items_per_session=12),
            self.sources,
            now=self.now,
        )
        ordered = sorted(state.interactions, key=lambda x: x.timestamp)
        seen_views: set[str] = set()
        action_events = {"quick_bounce", "like", "save", "comment"}
        for interaction in ordered:
            if interaction.event_type == "view":
                seen_views.add(interaction.exposure_id)
            if interaction.event_type in action_events:
                self.assertIn(interaction.exposure_id, seen_views)

    def test_propensity_fields_exist_for_stochastic_interactions(self) -> None:
        """Stochastic events must carry deterministic/final probabilities and policy metadata."""
        state = build_truth(
            RunConfig(seed=2028, user_count=28, timeline_ticks=4, items_per_session=12),
            self.sources,
            now=self.now,
        )
        stochastic_events = {"scroll_past", "hide", "view", "like", "save", "comment"}
        observed = [i for i in state.interactions if i.event_type in stochastic_events]
        self.assertTrue(observed, "Expected stochastic interactions to be present")
        for interaction in observed:
            self.assertIsNotNone(interaction.deterministic_prob)
            self.assertIsNotNone(interaction.final_prob)
            self.assertIsNotNone(interaction.prob_jitter)
            self.assertEqual(interaction.sampling_policy, "internal_heuristic_v1")
            self.assertEqual(interaction.sampling_policy_version, "1.0")
            self.assertIsInstance(interaction.sampled_outcome, bool)

    def test_quick_bounce_path_works(self) -> None:
        """A tuned session configuration should reliably produce quick-bounce events."""
        config = RunConfig(seed=2029, user_count=16, timeline_ticks=2, items_per_session=10)
        state = build_truth(config, self.sources, now=self.now)
        self.assertTrue(state.sessions)

        session = state.sessions[0]
        user = next(u for u in state.users if u.user_id == session.user_id)
        goal_id = state.goals_by_user[user.user_id][0].goal_id
        activity = ActivityState(
            activity_id=session.activity_id,
            user_id=user.user_id,
            goal_id=goal_id,
            activity_intent=session.activity_intent,
            topic=session.goal_topic,
            urgency=0.6,
            available_minutes=45,
            target_difficulty=3,
            session_id=session.session_id,
            timestamp=session.started_at,
        )
        session_exposures = [e for e in state.exposures if e.session_id == session.session_id]
        self.assertTrue(session_exposures)

        tuned_sources = copy.deepcopy(self.sources.sources)
        tuned_sources["session_dynamics"]["parameters"]["base_view_probability"] = 1.0
        tuned_sources["session_dynamics"]["parameters"]["detail_dwell_ms_range"] = [2500, 2500]
        tuned_sources["session_dynamics"]["parameters"]["quick_bounce_dwell_threshold_ms"] = 4000
        tuned_sources["jitter_noise_rules"]["rules"]["view_probability_jitter"]["range"] = [0.0, 0.0]
        tuned = SourceBundle(base_path=self.sources.base_path, sources=tuned_sources)

        interactions, _, _, _ = simulate_session_interactions(
            user=user,
            session=session,
            activity_state=activity,
            exposures=session_exposures,
            world_state=state,
            sources=tuned,
            rng=make_rng(88),
        )
        self.assertTrue(any(i.event_type == "quick_bounce" for i in interactions))

    def test_off_interest_click_floor_is_bounded(self) -> None:
        """Off-interest click floor should be positive but capped by configured maximum."""
        now = self.now
        user = UserProfile(
            user_id="u_test",
            primary_interest="Data Science",
            secondary_interests=["Machine Learning"],
            learning_intensity="heavy",
            sleep_habit_skew=0.5,
            posting_tendency="medium",
            interaction_tendency="high",
            writing_style_family="question_asking",
            register_level="plain",
            curiosity_level=1.0,
            diligence_level=0.7,
            social_affinity=0.6,
            exploration_rate=0.2,
            drift_rate=0.1,
            created_at=now,
        )
        off_interest_post = PostRecord(
            post_id="p_test",
            author_id="u_author",
            topic="Biology",
            subtopic="biology foundations",
            format="short_post",
            post_style="resource_share",
            creator_type="peer_student",
            difficulty=3,
            true_latent_quality=0.5,
            observed_quality=0.5,
            freshness_hours=1,
            study_context="regular_week",
            utility_style="overview",
            social_affordance="low_discussion",
            goal_relation_type="off_topic_noise",
            created_at=now,
        )
        on_interest_post = PostRecord(
            post_id="p_test_2",
            author_id="u_author",
            topic="Data Science",
            subtopic="data science foundations",
            format="short_post",
            post_style="knowledge_share",
            creator_type="peer_student",
            difficulty=3,
            true_latent_quality=0.5,
            observed_quality=0.5,
            freshness_hours=1,
            study_context="regular_week",
            utility_style="overview",
            social_affordance="low_discussion",
            goal_relation_type="interest_adjacent",
            created_at=now,
        )

        floor_off_interest = compute_off_interest_click_floor(user, off_interest_post, self.sources)
        floor_on_interest = compute_off_interest_click_floor(user, on_interest_post, self.sources)
        self.assertGreaterEqual(floor_off_interest, 0.0)
        self.assertLessEqual(floor_off_interest, 0.05)
        self.assertGreater(floor_off_interest, 0.0)
        self.assertEqual(floor_on_interest, 0.0)


if __name__ == "__main__":
    unittest.main()
