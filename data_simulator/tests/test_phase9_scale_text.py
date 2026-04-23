"""Phase 9 scale batch preparation and collection tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from config.loader import load_sources
from config.models import RenderedPostText, RunConfig
from pipeline.build_truth import build_truth
from pipeline.render_text import collect_scale_batch_results, prepare_scale_text_batches, select_seed_post_targets
from pipeline.run import run_simulation


class TestPhase9ScaleText(unittest.TestCase):
    """Validate batch-only phase 9 preparation, provider split, and collection."""

    def setUp(self) -> None:
        self.design_final_dir = Path(__file__).resolve().parents[1] / "design" / "design_final"
        self.sources = load_sources(self.design_final_dir)
        self.now = datetime(2026, 4, 22, 20, 0, tzinfo=timezone.utc)

    def test_prepare_scale_posts_split_between_openai_and_gemini(self) -> None:
        """Scale post requests should split deterministically by configured user-level Gemini share."""
        world_state = build_truth(
            RunConfig(seed=9101, user_count=28, timeline_ticks=4, items_per_session=10),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_phase9_posts_") as tmp:
            artifacts = prepare_scale_text_batches(
                world_state,
                output_dir=tmp,
                openai_model_name="gpt-5-nano",
                gemini_model_name="gemini-2.5-flash-lite",
                gemini_share_percentage=40,
                post_target_count=5,
            )

            self.assertEqual(artifacts["status"], "prepared_posts_only")
            self.assertEqual(artifacts["comment_stage_status"], "blocked_missing_rendered_posts")
            self.assertEqual(sum(artifacts["post_request_counts"].values()), 5)
            self.assertGreaterEqual(artifacts["post_request_counts"]["openai"], 0)
            self.assertGreaterEqual(artifacts["post_request_counts"]["gemini"], 0)
            self.assertEqual(artifacts["comment_request_counts"], {"openai": 0, "gemini": 0})

            files = artifacts["files"]
            self.assertTrue(Path(files["scale_posts_openai_batch_input"]).is_file())
            self.assertTrue(Path(files["scale_posts_gemini_batch_input"]).is_file())
            split_report = json.loads(Path(files["scale_posts_provider_split"]).read_text(encoding="utf-8"))
            self.assertEqual(split_report["gemini_share_percentage"], 40)
            self.assertEqual(len(split_report["gemini_prompt_ids"]) + len(split_report["openai_prompt_ids"]), 5)
            self.assertEqual(split_report["provider_user_counts"]["openai"], 17)
            self.assertEqual(split_report["provider_user_counts"]["gemini"], 11)
            _assert_users_do_not_cross_providers(
                files=files,
                openai_post_key="scale_posts_openai_prompt_registry",
                gemini_post_key="scale_posts_gemini_prompt_registry",
                openai_comment_key="missing",
                gemini_comment_key="missing",
            )

    def test_comment_stage_waits_for_rendered_post_sidecars(self) -> None:
        """Comment-set batch preparation must not proceed until rendered post text exists."""
        world_state = build_truth(
            RunConfig(seed=9102, user_count=24, timeline_ticks=3, items_per_session=10),
            self.sources,
            now=self.now,
        )

        artifacts = prepare_scale_text_batches(
            world_state,
            openai_model_name="gpt-5-nano",
            gemini_model_name="gemini-2.5-flash-lite",
            gemini_share_percentage=50,
            post_target_count=4,
            comment_target_count=3,
        )

        self.assertEqual(artifacts["comment_stage_status"], "blocked_missing_rendered_posts")
        self.assertEqual(artifacts["comment_prompts"], [])
        self.assertEqual(artifacts["missing_rendered_post_ids"], [])

    def test_comment_stage_uses_rendered_post_text(self) -> None:
        """Comment prompts should include collected rendered post text once available."""
        world_state = build_truth(
            RunConfig(seed=9103, user_count=22, timeline_ticks=3, items_per_session=8),
            self.sources,
            now=self.now,
        )
        post_targets = select_seed_post_targets(world_state, limit=4)

        with tempfile.TemporaryDirectory(prefix="sim_phase9_comments_") as tmp:
            rendered_posts_path = Path(tmp) / "rendered_posts.jsonl"
            rendered_posts = [
                RenderedPostText(
                    render_id=f"rpost_{post.post_id}",
                    post_id=post.post_id,
                    prompt_id=f"pp_{index}",
                    model_name="gpt-5-nano",
                    provider="openai_batch",
                    title=f"{post.topic} title {index}",
                    content=f"Concrete post text about {post.topic} and {post.subtopic}.",
                    validator_status="collected",
                )
                for index, post in enumerate(post_targets)
            ]
            rendered_posts_path.write_text(
                "".join(json.dumps(record.__dict__, sort_keys=True) + "\n" for record in rendered_posts),
                encoding="utf-8",
            )

            artifacts = prepare_scale_text_batches(
                world_state,
                output_dir=tmp,
                openai_model_name="gpt-5-nano",
                gemini_model_name="gemini-2.5-flash-lite",
                gemini_share_percentage=50,
                rendered_posts_path=rendered_posts_path,
                post_target_count=4,
                comment_target_count=2,
                max_comments_per_post_request=2,
            )

            self.assertIn(artifacts["status"], {"prepared", "prepared_with_warnings"})
            self.assertTrue(artifacts["comment_prompts"])
            combined = "\n".join(message.content for message in artifacts["comment_prompts"][0].messages)
            self.assertIn("Concrete post text about", combined)
            self.assertIn("target_post_text", combined)
            self.assertIn("comment_targets", combined)

            files = artifacts["files"]
            self.assertTrue(
                any(key.startswith("scale_comment_sets_openai") or key.startswith("scale_comment_sets_gemini") for key in files)
            )
            _assert_users_do_not_cross_providers(
                files=files,
                openai_post_key="scale_posts_openai_prompt_registry",
                gemini_post_key="scale_posts_gemini_prompt_registry",
                openai_comment_key="scale_comment_sets_openai_prompt_registry",
                gemini_comment_key="scale_comment_sets_gemini_prompt_registry",
            )

    def test_collect_scale_batch_results_supports_gemini_jsonl_outputs(self) -> None:
        """Gemini collector should parse keyed batch output JSONL into rendered sidecars."""
        world_state = build_truth(
            RunConfig(seed=9104, user_count=20, timeline_ticks=2, items_per_session=8),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_phase9_collect_") as tmp:
            prepared = prepare_scale_text_batches(
                world_state,
                output_dir=tmp,
                openai_model_name="gpt-5-nano",
                gemini_model_name="gemini-2.5-flash-lite",
                gemini_share_percentage=100,
                post_target_count=2,
            )
            manifest_path = Path(prepared["files"]["scale_posts_gemini_submit_manifest"])
            registry = _read_jsonl(Path(prepared["files"]["scale_posts_gemini_prompt_registry"]))
            prompt_id = registry[0]["prompt_id"]

            batch_status_path = Path(tmp) / "gemini_batch_status.json"
            batch_status_path.write_text(
                json.dumps({"name": "batches/123", "metadata": {"state": "JOB_STATE_SUCCEEDED"}}),
                encoding="utf-8",
            )
            output_jsonl_path = Path(tmp) / "gemini_batch_output.jsonl"
            output_jsonl_path.write_text(
                json.dumps(
                    {
                        "key": prompt_id,
                        "response": {
                            "candidates": [
                                {
                                    "content": {
                                        "parts": [
                                            {
                                                "text": json.dumps(
                                                    {"title": "Gemini post title", "content": "Gemini post body"}
                                                )
                                            }
                                        ]
                                    }
                                }
                            ]
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = collect_scale_batch_results(
                provider="gemini",
                batch_kind="posts",
                manifest_path=manifest_path,
                batch_status_path=batch_status_path,
                output_jsonl_path=output_jsonl_path,
            )

            self.assertEqual(report["status"], "JOB_STATE_SUCCEEDED")
            self.assertEqual(len(report["rendered_posts"]), 1)
            self.assertEqual(report["rendered_posts"][0].title, "Gemini post title")
            self.assertEqual(report["rendered_posts"][0].provider, "gemini_batch")

    def test_run_summary_uses_batch_preparation_fields(self) -> None:
        """Top-level summary should report prepared batch counts instead of local render counts."""
        with tempfile.TemporaryDirectory(prefix="sim_phase9_summary_") as tmp:
            with patch("pipeline.run.prepare_scale_text_batches") as mocked_scale_prepare:
                mocked_scale_prepare.return_value = {
                    "status": "prepared_posts_only",
                    "comment_stage_status": "blocked_missing_rendered_posts",
                    "post_request_counts": {"openai": 8, "gemini": 2},
                    "comment_request_counts": {"openai": 0, "gemini": 0},
                    "missing_rendered_post_ids": [],
                    "files": {},
                }
                summary = run_simulation(
                    config=RunConfig(
                        seed=9105,
                        user_count=14,
                        timeline_ticks=2,
                        items_per_session=8,
                        render_scale_text=True,
                        scale_gemini_share_percentage=20,
                    ),
                    design_root=self.design_final_dir,
                    output_dir=tmp,
                    now=self.now,
                )

        self.assertIn("scale_text_batch", summary)
        self.assertEqual(summary["scale_text_batch"]["prepared_post_request_count"], 10)
        self.assertEqual(summary["scale_text_batch"]["prepared_comment_request_count"], 0)
        self.assertEqual(summary["scale_text_batch"]["post_request_counts_by_provider"]["gemini"], 2)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    """Load a small JSONL test fixture from disk."""
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def _assert_users_do_not_cross_providers(
    *,
    files: dict[str, str],
    openai_post_key: str,
    gemini_post_key: str,
    openai_comment_key: str,
    gemini_comment_key: str,
) -> None:
    """Assert the same user never appears in both provider registries."""
    seen: dict[str, str] = {}
    for provider, key, field in (
        ("openai", openai_post_key, "author_id"),
        ("gemini", gemini_post_key, "author_id"),
    ):
        if key not in files:
            continue
        for record in _read_jsonl(Path(files[key])):
            user_id = str(record[field])
            if user_id in seen:
                assert seen[user_id] == provider
            seen[user_id] = provider
    for provider, key in (("openai", openai_comment_key), ("gemini", gemini_comment_key)):
        if key not in files:
            continue
        for record in _read_jsonl(Path(files[key])):
            for user_id in record.get("commenter_user_ids", []):
                user_key = str(user_id)
                if user_key in seen:
                    assert seen[user_key] == provider
                seen[user_key] = provider


if __name__ == "__main__":
    unittest.main()
