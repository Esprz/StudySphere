"""Phase 0 core helper tests."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from core.ids import new_id
from core.random import make_rng
from core.time import clip_0_1, derive_global_time_context


class TestCoreHelpers(unittest.TestCase):
    def setUp(self) -> None:
        design_final_dir = Path(__file__).resolve().parents[1] / "default_source_bundle"
        self.sources = load_sources(design_final_dir)

    def test_rng_is_deterministic(self) -> None:
        rng_a = make_rng(42)
        rng_b = make_rng(42)
        vals_a = [rng_a.random() for _ in range(3)]
        vals_b = [rng_b.random() for _ in range(3)]
        self.assertEqual(vals_a, vals_b)

    def test_new_id_is_deterministic_with_seeded_rng(self) -> None:
        rng_a = make_rng(9)
        rng_b = make_rng(9)
        self.assertEqual(new_id("u", rng=rng_a), new_id("u", rng=rng_b))

    def test_clip_0_1(self) -> None:
        self.assertEqual(clip_0_1(-0.2), 0.0)
        self.assertEqual(clip_0_1(2.0), 1.0)
        self.assertEqual(clip_0_1(0.3), 0.3)

    def test_derive_global_time_context(self) -> None:
        ts = datetime(2026, 4, 21, 20, 0, tzinfo=timezone.utc)
        world_clock = self.sources.require("world_clock")
        ctx = derive_global_time_context(ts, world_clock)
        self.assertEqual(ctx.hour_segment, "evening")
        self.assertEqual(ctx.day_type, "weekday")
        self.assertTrue(bool(ctx.academic_season))


if __name__ == "__main__":
    unittest.main()
