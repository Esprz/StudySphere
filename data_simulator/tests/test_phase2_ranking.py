"""Phase 2 ranking and exposure tests."""

from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import ActivityState, PostRecord, RunConfig, SessionContext, SourceBundle, UserProfile
from core.random import make_rng
from generators.ranking import _derive_exposure_reasons, _score_weights_from_sources, build_candidate_pool
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

    def test_score_formula_parser_handles_spaces_around_multiply(self) -> None:
        tuned = copy.deepcopy(self.sources.sources)
        for fn in tuned["decision_formulas"]["functions"]:
            if fn.get("name") == "score_exposure":
                fn["formula"] = (
                    "clip_0_1(0.31 * topic_match + 0.21 * goal_alignment + 0.17 * activity_alignment "
                    "+ 0.09 * freshness_bonus + 0.11 * observed_quality + 0.06 * social_bonus + 0.05 * exploration_bonus)"
                )
                break
        bundle = SourceBundle(base_path=self.sources.base_path, sources=tuned)
        weights = _score_weights_from_sources(bundle)

        self.assertEqual(weights["topic_match"], 0.31)
        self.assertEqual(weights["goal_alignment"], 0.21)
        self.assertEqual(weights["activity_alignment"], 0.17)
        self.assertEqual(weights["freshness_bonus"], 0.09)
        self.assertEqual(weights["observed_quality"], 0.11)
        self.assertEqual(weights["social_bonus"], 0.06)
        self.assertEqual(weights["exploration_bonus"], 0.05)

    def test_social_retrieval_reason_is_labeled_social_match(self) -> None:
        user = UserProfile(
            user_id="u_1",
            primary_interest="Data Science",
            secondary_interests=["Machine Learning"],
            learning_intensity="medium",
            sleep_habit_skew=0.5,
            posting_tendency="medium",
            interaction_tendency="high",
            writing_style_family="analytical",
            register_level="technical",
            curiosity_level=0.6,
            diligence_level=0.6,
            social_affinity=0.8,
            exploration_rate=0.2,
            drift_rate=0.1,
            created_at=self.now,
        )
        session = SessionContext(
            session_id="s_1",
            user_id=user.user_id,
            activity_id="a_1",
            surface="feed",
            started_at=self.now,
            wall_clock_time=self.now,
            hour_segment="evening",
            day_type="weekday",
            academic_season="regular_term",
            goal_topic="Software Development",
            activity_intent="Concept_Learning",
            candidate_pool_size=80,
            items_exposed_count=0,
            session_duration_seconds=900,
            fatigue_start=0.1,
            activity_transition_count=0,
        )
        post = PostRecord(
            post_id="p_1",
            author_id="u_followed",
            topic="Biology",
            subtopic="cell biology",
            format="short_post",
            post_style="knowledge_share",
            creator_type="peer_student",
            difficulty=3,
            true_latent_quality=0.4,
            observed_quality=0.4,
            freshness_hours=72,
            study_context="regular_week",
            utility_style="overview",
            social_affordance="low_discussion",
            goal_relation_type="off_topic_noise",
            created_at=self.now,
        )

        reasons = _derive_exposure_reasons(
            user=user,
            session=session,
            post=post,
            follow_graph={user.user_id: {"u_followed"}},
        )
        self.assertIn("social_match", reasons)
        self.assertNotIn("exploration", reasons)


if __name__ == "__main__":
    unittest.main()
