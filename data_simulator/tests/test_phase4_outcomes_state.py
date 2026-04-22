"""Phase 4 outcomes and state-mutation tests."""

from __future__ import annotations

import copy
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import ActivityState, FocusSessionRecord, InteractionRecord, RunConfig, SessionOutcomes, SourceBundle
from core.random import make_rng
from generators.state_updates import update_goal_progress, update_world_state_after_session
from pipeline.build_truth import build_truth


class TestPhase4OutcomesState(unittest.TestCase):
    """Validate Phase-4 outcome generation and world-state mutation behavior."""

    def setUp(self) -> None:
        design_final_dir = Path(__file__).resolve().parents[1] / "design" / "design_final"
        self.sources = load_sources(design_final_dir)
        self.now = datetime(2026, 4, 22, 14, 0, tzinfo=timezone.utc)

    def test_focus_session_only_after_valid_session(self) -> None:
        """Focus sessions should reference existing sessions and valid trigger fields."""
        tuned_sources = copy.deepcopy(self.sources.sources)
        tuned_sources["session_dynamics"]["parameters"]["base_view_probability"] = 1.0
        tuned_sources["jitter_noise_rules"]["rules"]["view_probability_jitter"]["range"] = [0.0, 0.0]
        for func in tuned_sources["decision_formulas"]["functions"]:
            if func.get("name") == "sample_focus_trigger":
                func["formula"] = (
                    "clip_0_1(1.0 + 0.0*diligence_level + 0.0*goal_strength + 0.0*goal_alignment "
                    "+ 0.0*saved_in_session + 0.0*liked_in_session + 0.0*detail_dwell_norm)"
                )
                break
        bundle = SourceBundle(base_path=self.sources.base_path, sources=tuned_sources)
        state = build_truth(RunConfig(seed=4101, user_count=22, timeline_ticks=3, items_per_session=10), bundle, now=self.now)

        self.assertTrue(state.focus_sessions, "Expected at least one focus session in tuned run")
        session_ids = {session.session_id for session in state.sessions}
        post_ids = {post.post_id for post in state.posts}
        for focus in state.focus_sessions:
            self.assertIn(focus.session_id, session_ids)
            self.assertIn(focus.trigger_post_id, post_ids)
            self.assertGreater(focus.ended_at, focus.started_at)
            self.assertGreaterEqual(focus.duration_minutes, 15)

    def test_follow_graph_updates_persist_to_later_state(self) -> None:
        """Follow edges added by one update should remain in later updates."""
        state = build_truth(RunConfig(seed=4102, user_count=14, timeline_ticks=2, items_per_session=8), self.sources, now=self.now)
        self.assertTrue(state.sessions)
        session = state.sessions[0]
        user = next(item for item in state.users if item.user_id == session.user_id)
        active_goal = next(goal for goal in state.goals_by_user[user.user_id] if goal.progress_state == "active")
        activity = ActivityState(
            activity_id=session.activity_id,
            user_id=user.user_id,
            goal_id=active_goal.goal_id,
            activity_intent=session.activity_intent,
            topic=session.goal_topic,
            urgency=0.5,
            available_minutes=45,
            target_difficulty=3,
            session_id=session.session_id,
            timestamp=session.started_at,
        )
        target_author = next(item.user_id for item in state.users if item.user_id != user.user_id)

        update_world_state_after_session(
            user=user,
            session=session,
            activity_state=activity,
            active_goal=active_goal,
            interactions=[],
            outcomes=SessionOutcomes(follow_events=[(user.user_id, target_author)]),
            world_state=state,
            sources=self.sources,
            rng=make_rng(9),
            now=self.now,
        )
        self.assertIn(target_author, state.follow_graph[user.user_id])

        update_world_state_after_session(
            user=user,
            session=session,
            activity_state=activity,
            active_goal=next(goal for goal in state.goals_by_user[user.user_id] if goal.goal_id == active_goal.goal_id),
            interactions=[],
            outcomes=SessionOutcomes(),
            world_state=state,
            sources=self.sources,
            rng=make_rng(10),
            now=self.now,
        )
        self.assertIn(target_author, state.follow_graph[user.user_id])

    def test_goal_progress_mutates_in_expected_direction(self) -> None:
        """Positive aligned signals should move goal progress upward."""
        state = build_truth(RunConfig(seed=4103, user_count=10, timeline_ticks=1, items_per_session=8), self.sources, now=self.now)
        user = state.users[0]
        active_goal = next(goal for goal in state.goals_by_user[user.user_id] if goal.progress_state == "active")
        goal_topic = active_goal.related_topics[0]
        goal_post = next((post for post in state.posts if post.topic == goal_topic), state.posts[0])
        activity = ActivityState(
            activity_id="a_test",
            user_id=user.user_id,
            goal_id=active_goal.goal_id,
            activity_intent="Project_Execution",
            topic=goal_topic,
            urgency=0.8,
            available_minutes=60,
            target_difficulty=goal_post.difficulty,
            session_id="s_test",
            timestamp=self.now,
        )
        interactions = [
            InteractionRecord(
                interaction_id="i_view",
                event_type="view",
                user_id=user.user_id,
                post_id=goal_post.post_id,
                session_id="s_test",
                exposure_id="e_test",
                timestamp=self.now,
                dwell_ms=60000,
            ),
            InteractionRecord(
                interaction_id="i_save",
                event_type="save",
                user_id=user.user_id,
                post_id=goal_post.post_id,
                session_id="s_test",
                exposure_id="e_test",
                timestamp=self.now,
            ),
            InteractionRecord(
                interaction_id="i_comment",
                event_type="comment",
                user_id=user.user_id,
                post_id=goal_post.post_id,
                session_id="s_test",
                exposure_id="e_test",
                timestamp=self.now,
                comment_text="helpful",
            ),
        ]
        focus = FocusSessionRecord(
            focus_id="f_test",
            user_id=user.user_id,
            session_id="s_test",
            trigger_post_id=goal_post.post_id,
            related_goal_id=active_goal.goal_id,
            topic=goal_post.topic,
            started_at=self.now,
            ended_at=self.now,
            duration_minutes=30,
            trigger_strength=0.8,
            deterministic_focus_prob=0.8,
            final_focus_prob=0.8,
            sampling_policy="internal_heuristic_v1",
        )
        outcomes = SessionOutcomes(focus_session=focus)

        before_progress = active_goal.progress
        updated_goal, _ = update_goal_progress(
            user=user,
            active_goal=active_goal,
            activity_state=activity,
            interactions=interactions,
            outcomes=outcomes,
            world_state=state,
            sources=self.sources,
            rng=make_rng(11),
            now=self.now,
        )
        self.assertGreater(updated_goal.progress, before_progress)

    def test_replacement_goals_only_appear_when_allowed(self) -> None:
        """Replacement goals should only be sampled after completion or drop."""
        state = build_truth(RunConfig(seed=4104, user_count=8, timeline_ticks=1, items_per_session=8), self.sources, now=self.now)
        user = state.users[0]
        active_goal = next(goal for goal in state.goals_by_user[user.user_id] if goal.progress_state == "active")
        activity = ActivityState(
            activity_id="a_replace",
            user_id=user.user_id,
            goal_id=active_goal.goal_id,
            activity_intent="Revision_Queueing",
            topic=active_goal.related_topics[0],
            urgency=0.7,
            available_minutes=50,
            target_difficulty=3,
            session_id="s_replace",
            timestamp=self.now,
        )

        # No strong signals: replacement should not appear.
        updated_no_replace, no_replace = update_goal_progress(
            user=user,
            active_goal=active_goal,
            activity_state=activity,
            interactions=[],
            outcomes=SessionOutcomes(),
            world_state=state,
            sources=self.sources,
            rng=make_rng(12),
            now=self.now,
        )
        self.assertIsNone(no_replace)
        self.assertEqual(updated_no_replace.progress_state, "active")

        # Force completion path: replacement should appear.
        almost_done = replace(updated_no_replace, progress=0.95, strength=max(0.2, updated_no_replace.strength))
        for idx, goal in enumerate(state.goals_by_user[user.user_id]):
            if goal.goal_id == almost_done.goal_id:
                state.goals_by_user[user.user_id][idx] = almost_done
                break
        goal_post = next((post for post in state.posts if post.topic == activity.topic), state.posts[0])
        completing_interactions = [
            InteractionRecord(
                interaction_id="i_save_done",
                event_type="save",
                user_id=user.user_id,
                post_id=goal_post.post_id,
                session_id="s_replace",
                exposure_id="e_replace",
                timestamp=self.now,
            )
        ]
        focus = FocusSessionRecord(
            focus_id="f_done",
            user_id=user.user_id,
            session_id="s_replace",
            trigger_post_id=goal_post.post_id,
            related_goal_id=almost_done.goal_id,
            topic=activity.topic,
            started_at=self.now,
            ended_at=self.now,
            duration_minutes=25,
            trigger_strength=0.9,
        )
        updated_done, replacement = update_goal_progress(
            user=user,
            active_goal=almost_done,
            activity_state=activity,
            interactions=completing_interactions,
            outcomes=SessionOutcomes(focus_session=focus),
            world_state=state,
            sources=self.sources,
            rng=make_rng(13),
            now=self.now,
        )
        self.assertEqual(updated_done.progress_state, "completed")
        self.assertIsNotNone(replacement)


if __name__ == "__main__":
    unittest.main()
