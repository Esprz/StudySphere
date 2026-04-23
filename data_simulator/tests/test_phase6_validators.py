"""Phase 6 validator tests with intentionally broken fixtures."""

from __future__ import annotations

import copy
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import InteractionRecord, RunConfig, SourceBundle
from pipeline.build_truth import build_truth
from pipeline.validate import validate_world_state
from validators.causality import validate_causality, validate_propensity_logging
from validators.dependencies import validate_signal_dependencies
from validators.distributions import validate_batch_distributions
from validators.schema import validate_schema


class TestPhase6Validators(unittest.TestCase):
    """Validate schema/dependency/causal/propensity/distribution checks."""

    def setUp(self) -> None:
        """Load canonical sources and generate one baseline valid world state."""
        design_final_dir = Path(__file__).resolve().parents[1] / "default_source_bundle"
        self.sources = load_sources(design_final_dir)
        self.now = datetime(2026, 4, 22, 16, 0, tzinfo=timezone.utc)
        self.base_state = build_truth(
            RunConfig(seed=6201, user_count=24, timeline_ticks=3, items_per_session=10),
            self.sources,
            now=self.now,
        )
        self.assertTrue(self.base_state.exposures)
        self.assertTrue(self.base_state.propensity_logs)

    def test_schema_failure_fixture(self) -> None:
        """Out-of-range user fields should fail schema validation."""
        broken = copy.deepcopy(self.base_state)
        broken.users[0] = replace(broken.users[0], exploration_rate=0.91)

        issues = validate_schema(broken)
        self.assertTrue(any(issue["code"] == "user_exploration_rate_range" for issue in issues))

    def test_dependency_failure_fixture(self) -> None:
        """Undefined signals in formulas should fail dependency validation."""
        mutated_sources = copy.deepcopy(self.sources.sources)
        mutated_sources["signal_catalog"]["signals"] = [
            item
            for item in mutated_sources["signal_catalog"]["signals"]
            if item.get("name") != "candidate_score"
        ]
        broken_bundle = SourceBundle(base_path=self.sources.base_path, sources=mutated_sources)

        issues = validate_signal_dependencies(self.base_state, broken_bundle)
        self.assertTrue(
            any(
                issue["code"] == "undefined_signal_in_catalog"
                and issue["context"].get("signal") == "candidate_score"
                for issue in issues
            )
        )

    def test_causal_failure_fixture(self) -> None:
        """Post-view actions without a preceding view should fail causality."""
        broken = copy.deepcopy(self.base_state)
        session = broken.sessions[0]
        exposure = next(item for item in broken.exposures if item.session_id == session.session_id)
        broken.interactions = [
            InteractionRecord(
                interaction_id="i_bad_like",
                event_type="like",
                user_id=exposure.user_id,
                post_id=exposure.post_id,
                session_id=exposure.session_id,
                exposure_id=exposure.exposure_id,
                timestamp=session.started_at,
                deterministic_prob=0.4,
                final_prob=0.4,
                prob_jitter=0.0,
                sampling_policy="internal_heuristic_v1",
                sampling_policy_version="1.0",
                sampled_outcome=True,
            )
        ]

        issues = validate_causality(broken)
        self.assertTrue(any(issue["code"] == "post_view_action_without_view" for issue in issues))

    def test_propensity_failure_fixture(self) -> None:
        """Mismatched sampled outcome should fail propensity validation."""
        broken = copy.deepcopy(self.base_state)
        target_index = next(
            idx
            for idx, log in enumerate(broken.propensity_logs)
            if log.decision_stage == "view_decision"
        )
        target = broken.propensity_logs[target_index]
        broken.propensity_logs[target_index] = replace(
            target,
            sampled_outcome=not bool(target.sampled_outcome),
        )

        issues = validate_propensity_logging(broken)
        self.assertTrue(any(issue["code"] == "propensity_outcome_mismatch" for issue in issues))

    def test_flat_distribution_fixture(self) -> None:
        """Uniform true-latent quality should raise a flat-distribution warning."""
        broken = copy.deepcopy(self.base_state)
        broken.posts = [replace(post, true_latent_quality=0.5) for post in broken.posts]
        for post_id, payload in broken.content_memory.items():
            payload["true_latent_quality"] = 0.5
            broken.content_memory[post_id] = payload

        issues = validate_batch_distributions(broken)
        self.assertTrue(
            any(
                issue["code"] == "flat_true_quality_distribution" and issue["severity"] == "warning"
                for issue in issues
            )
        )

    def test_validation_report_contains_fail_counters(self) -> None:
        """Validation pipeline report should include hard/soft fail counters."""
        broken = copy.deepcopy(self.base_state)
        broken.users[0] = replace(broken.users[0], exploration_rate=0.91)

        report = validate_world_state(broken, self.sources)
        self.assertEqual(report["status"], "failed")
        self.assertGreater(report["total_hard_fails"], 0)
        self.assertIn("hard_fail_count_by_validator", report)
        self.assertIn("soft_fail_count_by_validator", report)
        self.assertIn("propensity_logging_completeness", report)


if __name__ == "__main__":
    unittest.main()
