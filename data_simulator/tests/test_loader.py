"""Phase 0 loader tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from config.loader import SOURCE_FILES, load_sources, validate_source_bundle


class TestSourceLoader(unittest.TestCase):
    def setUp(self) -> None:
        self.design_final_dir = Path(__file__).resolve().parents[1] / "design" / "design_final"

    def test_load_sources_smoke(self) -> None:
        bundle = load_sources(self.design_final_dir)
        self.assertEqual(set(bundle.sources.keys()), set(SOURCE_FILES.keys()))
        self.assertIn("world_clock", bundle.sources)
        self.assertTrue(bundle.base_path.name == "sources")

    def test_validate_source_bundle_smoke(self) -> None:
        bundle = load_sources(self.design_final_dir)
        validate_source_bundle(bundle)


if __name__ == "__main__":
    unittest.main()

