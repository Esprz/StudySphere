"""Phase 0 model tests."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.models import (
    ActivityState,
    ExposureRecord,
    FocusSessionRecord,
    InteractionRecord,
    PostRecord,
    SessionContext,
    SourceBundle,
    UserGoal,
    UserProfile,
    WorldState,
)


class TestModels(unittest.TestCase):
    def test_model_instantiation_smoke(self) -> None:
        now = datetime.now(timezone.utc)
        user = UserProfile(
            user_id="u_1",
            primary_interest="Software Development",
            secondary_interests=["Data Science & AI"],
            learning_intensity="heavy",
            sleep_habit_skew=0.7,
            posting_tendency="medium",
            interaction_tendency="likes_and_saves",
            writing_style_family="reflective",
            register_level="plain",
            curiosity_level=0.6,
            diligence_level=0.8,
            social_affinity=0.4,
            exploration_rate=0.2,
            drift_rate=0.1,
            created_at=now,
        )
        goal = UserGoal(
            goal_id="g_1",
            user_id=user.user_id,
            goal_category="Career_And_Performance",
            goal_type="Technical_Upskilling",
            related_topics=["Software Development"],
            priority=0.9,
            strength=0.8,
            progress_state="active",
            start_at=now,
            end_at=now,
        )
        session = SessionContext(
            session_id="s_1",
            user_id=user.user_id,
            activity_id="a_1",
            surface="feed",
            started_at=now,
            wall_clock_time=now,
            hour_segment="evening",
            day_type="weekday",
            academic_season="regular_term",
            goal_topic="Software Development",
            activity_intent="Project_Execution",
            candidate_pool_size=80,
            items_exposed_count=12,
            session_duration_seconds=900,
            fatigue_start=0.2,
            activity_transition_count=0,
        )
        activity = ActivityState(
            activity_id="a_1",
            user_id=user.user_id,
            goal_id=goal.goal_id,
            activity_intent="Project_Execution",
            topic="Software Development",
            urgency=0.7,
            available_minutes=45,
            target_difficulty=3,
            session_id=session.session_id,
            timestamp=now,
        )
        post = PostRecord(
            post_id="p_1",
            author_id=user.user_id,
            topic="Software Development",
            subtopic="distributed systems",
            format="project_log",
            post_style="progress_update",
            creator_type="project_builder",
            difficulty=4,
            true_latent_quality=0.8,
            observed_quality=0.5,
            freshness_hours=10,
            study_context="project_deadline",
            utility_style="worked_example",
            social_affordance="question_inviting",
            goal_relation_type="on_goal",
            created_at=now,
        )
        exposure = ExposureRecord(
            exposure_id="e_1",
            session_id=session.session_id,
            user_id=user.user_id,
            post_id=post.post_id,
            surface="feed",
            timestamp=now,
            rank_position=1,
            candidate_score=0.7,
            exposure_reasons=["goal_aligned"],
        )
        interaction = InteractionRecord(
            interaction_id="i_1",
            event_type="view",
            user_id=user.user_id,
            post_id=post.post_id,
            session_id=session.session_id,
            exposure_id=exposure.exposure_id,
            timestamp=now,
        )
        focus = FocusSessionRecord(
            focus_id="f_1",
            user_id=user.user_id,
            session_id=session.session_id,
            trigger_post_id=post.post_id,
            related_goal_id=goal.goal_id,
            topic="Software Development",
            started_at=now,
            ended_at=now,
            duration_minutes=30,
            trigger_strength=0.7,
        )
        bundle = SourceBundle(base_path=Path("/tmp"), sources={"dummy": {"version": "1.0"}})
        state = WorldState(
            users=[user],
            goals_by_user={user.user_id: [goal]},
            posts=[post],
            sessions=[session],
            exposures=[exposure],
            interactions=[interaction],
            focus_sessions=[focus],
        )

        self.assertEqual(activity.session_id, session.session_id)
        self.assertEqual(bundle.require("dummy")["version"], "1.0")
        self.assertEqual(len(state.users), 1)


if __name__ == "__main__":
    unittest.main()
