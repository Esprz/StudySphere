"""Structured truth pipeline for simulator."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from config.models import RunConfig, SourceBundle, WorldState
from core.random import make_rng
from core.time import derive_global_time_context
from generators.content import generate_initial_content
from generators.goals import generate_initial_goals, select_active_goal
from generators.ranking import build_candidate_pool, emit_exposures, rank_candidates_for_exposure
from generators.sessions import generate_activity_state, open_session, sample_active_users
from generators.state_updates import initialize_follow_graph, seed_content_memory, seed_user_memory
from generators.users import generate_user_profiles


def build_truth(
    config: RunConfig,
    source_bundle: SourceBundle,
    *,
    now: datetime | None = None,
) -> WorldState:
    now_utc = now or datetime.now(timezone.utc).replace(second=0, microsecond=0)
    rng = make_rng(config.seed)

    users = generate_user_profiles(config, source_bundle, rng, now=now_utc)
    goals_by_user = generate_initial_goals(users, source_bundle, rng, now=now_utc)
    posts = generate_initial_content(users, source_bundle, rng, now=now_utc)
    follow_graph = initialize_follow_graph(users)
    user_memory = seed_user_memory(users, goals_by_user)
    content_memory = seed_content_memory(posts)

    world_state = WorldState(
        users=users,
        goals_by_user=goals_by_user,
        posts=posts,
        follow_graph=follow_graph,
        user_memory=user_memory,
        content_memory=content_memory,
        sessions=[],
        exposures=[],
        interactions=[],
        focus_sessions=[],
    )

    world_clock = source_bundle.require("world_clock")
    for tick in range(config.timeline_ticks):
        time_tick = now_utc + timedelta(hours=tick * 6)
        global_time_context = derive_global_time_context(time_tick, world_clock)
        active_users = sample_active_users(
            time_tick=time_tick,
            users=users,
            user_memory=world_state.user_memory,
            global_time_context=global_time_context,
            rng=rng,
        )
        for user in active_users:
            user_goals = world_state.goals_by_user.get(user.user_id, [])
            if not user_goals:
                continue

            active_goal = select_active_goal(user, user_goals, time_tick)
            session = open_session(
                user=user,
                time_tick=time_tick,
                active_goal=active_goal,
                global_time_context=global_time_context,
                rng=rng,
                max_candidate_pool_size=config.max_candidate_pool_size,
            )
            activity = generate_activity_state(
                user=user,
                session=session,
                active_goal=active_goal,
                sources=source_bundle,
                global_time_context=global_time_context,
                rng=rng,
            )
            session = replace(
                session,
                activity_intent=activity.activity_intent,
                goal_topic=activity.topic,
            )

            candidate_pool = build_candidate_pool(
                user=user,
                session=session,
                activity_state=activity,
                world_state=world_state,
                rng=rng,
            )
            ranked = rank_candidates_for_exposure(
                user=user,
                activity_state=activity,
                candidates=candidate_pool,
                world_state=world_state,
                sources=source_bundle,
                rng=rng,
            )
            exposure_records = emit_exposures(
                user=user,
                session=session,
                ranked_candidates=ranked,
                world_state=world_state,
                rng=rng,
                items_per_session=config.items_per_session,
            )
            session = replace(session, items_exposed_count=len(exposure_records))
            world_state.sessions.append(session)
            world_state.exposures.extend(exposure_records)
            world_state.user_memory[user.user_id]["recent_sessions"].append(session.session_id)

    return world_state
