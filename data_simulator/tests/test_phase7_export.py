"""Phase 7 export layer tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import RunConfig
from exporters.simulator_json import export_simulator_jsonl
from pipeline.build_truth import build_truth
from pipeline.run import run_simulation


class TestPhase7Export(unittest.TestCase):
    """Validate simulator-native output bundle export behavior."""

    def setUp(self) -> None:
        """Load canonical sources and choose deterministic run settings."""
        self.design_final_dir = Path(__file__).resolve().parents[1] / "design" / "design_final"
        self.sources = load_sources(self.design_final_dir)
        self.now = datetime(2026, 4, 22, 18, 0, tzinfo=timezone.utc)
        self.config = RunConfig(
            seed=7201,
            user_count=24,
            timeline_ticks=3,
            items_per_session=10,
        )

    def test_expected_files_are_written(self) -> None:
        """One run should produce full Phase-7 output bundle files."""
        with tempfile.TemporaryDirectory(prefix="sim_phase7_") as tmp:
            output_dir = Path(tmp)
            summary = run_simulation(
                config=self.config,
                design_root=self.design_final_dir,
                output_dir=output_dir,
                now=self.now,
            )

            expected = [
                "users.jsonl",
                "goals.jsonl",
                "posts.jsonl",
                "sessions.jsonl",
                "exposures.jsonl",
                "interactions.jsonl",
                "focus_sessions.jsonl",
                "event_log.jsonl",
                "propensity_logs.jsonl",
                "validation_report.json",
                "run_summary.json",
            ]
            for filename in expected:
                self.assertTrue((output_dir / filename).is_file(), f"missing export file: {filename}")
            self.assertIn("record_counts", summary)
            self.assertIn("validation", summary)

    def test_exported_records_preserve_key_fields(self) -> None:
        """Entity JSONL should preserve canonical key fields from world state."""
        world_state = build_truth(self.config, self.sources, now=self.now)
        self.assertTrue(world_state.users)
        self.assertTrue(world_state.exposures)
        self.assertTrue(world_state.interactions)

        with tempfile.TemporaryDirectory(prefix="sim_phase7_fields_") as tmp:
            output_dir = Path(tmp)
            paths = export_simulator_jsonl(world_state, output_dir)

            user_row = _read_first_jsonl_row(paths["users"])
            self.assertEqual(user_row["user_id"], world_state.users[0].user_id)
            self.assertEqual(user_row["primary_interest"], world_state.users[0].primary_interest)

            exposure_row = _read_first_jsonl_row(paths["exposures"])
            self.assertIn("deterministic_exposure_score", exposure_row)
            self.assertIn("ranking_policy_version", exposure_row)
            self.assertIn("candidate_score", exposure_row)

            interaction_row = _read_first_jsonl_row(paths["interactions"])
            self.assertIn("event_type", interaction_row)
            self.assertIn("exposure_id", interaction_row)
            self.assertIn("timestamp", interaction_row)

    def test_validation_report_is_emitted(self) -> None:
        """Run output should always include validation report and status fields."""
        with tempfile.TemporaryDirectory(prefix="sim_phase7_validate_") as tmp:
            output_dir = Path(tmp)
            summary = run_simulation(
                config=self.config,
                design_root=self.design_final_dir,
                output_dir=output_dir,
                now=self.now,
            )

            report_path = output_dir / "validation_report.json"
            self.assertTrue(report_path.is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))

            self.assertIn("status", report)
            self.assertIn("hard_fail_count_by_validator", report)
            self.assertIn("soft_fail_count_by_validator", report)
            self.assertIn("propensity_logging_completeness", report)
            self.assertEqual(summary["files"]["validation_report"], str(report_path.resolve()))


def _read_first_jsonl_row(path: Path) -> dict[str, object]:
    """Read first non-empty JSONL row from a file."""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            return json.loads(stripped)
    raise AssertionError(f"No JSONL rows found in {path}")


if __name__ == "__main__":
    unittest.main()
