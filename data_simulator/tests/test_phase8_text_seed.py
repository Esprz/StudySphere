"""Phase 8 seed text layer tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from config.loader import load_sources
from config.models import RenderedPostText, RunConfig
from pipeline.build_truth import build_truth
from pipeline.render_text import (
    collect_openai_seed_batch_results,
    prepare_openai_seed_batches,
    prepare_openai_seed_retry_batches,
    render_seed_text,
    select_seed_comment_target_groups,
)
from renderers.prompts import build_comment_render_prompt, build_comment_render_target, build_post_render_prompt
from validators.text_rules import validate_rendered_posts


class TestPhase8SeedText(unittest.TestCase):
    """Validate prompt building, local stub rendering, and batch artifact lifecycle."""

    def setUp(self) -> None:
        """Load design sources and a deterministic reference timestamp."""
        self.design_final_dir = Path(__file__).resolve().parents[1] / "design" / "design_final"
        self.sources = load_sources(self.design_final_dir)
        self.now = datetime(2026, 4, 22, 18, 0, tzinfo=timezone.utc)

    def test_post_prompt_builder_includes_structured_truth_and_author_persona(self) -> None:
        """Post prompts should include structured truth, persona, and length guidance only."""
        world_state = build_truth(
            RunConfig(seed=8101, user_count=12, timeline_ticks=1, items_per_session=8),
            self.sources,
            now=self.now,
        )
        post = world_state.posts[0]
        author = next(user for user in world_state.users if user.user_id == post.author_id)
        prompt = build_post_render_prompt(post, author_profile=author)

        combined = "\n".join(message.content for message in prompt.messages)
        self.assertIn(post.topic, combined)
        self.assertIn(post.subtopic, combined)
        self.assertIn(post.format, combined)
        self.assertIn(post.post_style, combined)
        self.assertIn(post.goal_relation_type, combined)
        self.assertIn(post.creator_type, combined)
        self.assertIn(str(post.difficulty), combined)
        self.assertIn("author_persona", combined)
        self.assertIn(author.primary_interest, combined)
        self.assertIn(author.writing_style_family, combined)
        self.assertIn(author.register_level, combined)
        self.assertIn("length_guidance", combined)
        self.assertNotIn("Seed examples:", combined)
        self.assertNotIn("TITLE:", combined)
        self.assertNotIn("CONTENT:", combined)

    def test_comment_set_prompt_includes_target_post_text_and_multiple_personas(self) -> None:
        """Comment-set prompts should contain target post text plus grouped commenter personas."""
        world_state = build_truth(
            RunConfig(seed=8101, user_count=28, timeline_ticks=4, items_per_session=10),
            self.sources,
            now=self.now,
        )
        groups = select_seed_comment_target_groups(world_state, limit=1, max_comments_per_post_request=4)
        post, interactions = groups[0]
        users_by_id = {user.user_id: user for user in world_state.users}
        rendered_post = RenderedPostText(
            render_id="rpost_test",
            post_id=post.post_id,
            prompt_id="pp_test",
            model_name="stub",
            provider="stub",
            title="Software Development: project log notes",
            content="This project log is about software development debugging and retry logic.",
        )
        comment_targets = [
            build_comment_render_target(interaction, users_by_id.get(interaction.user_id))
            for interaction in interactions
        ]
        prompt = build_comment_render_prompt(
            post,
            rendered_post=rendered_post,
            comment_targets=comment_targets,
        )

        combined = "\n".join(message.content for message in prompt.messages)
        self.assertIn(rendered_post.title, combined)
        self.assertIn(rendered_post.content, combined)
        self.assertIn("comment_targets", combined)
        self.assertIn("interaction_id", combined)
        self.assertIn("writing_style_family", combined)
        self.assertIn("register_level", combined)
        self.assertIn(post.post_style, combined)
        self.assertIn(post.goal_relation_type, combined)
        self.assertIn("comment: 12-40 words", combined)
        self.assertNotIn("Seed examples:", combined)
        self.assertNotIn("json_schema", combined)

    def test_text_validator_catches_obvious_contradictions(self) -> None:
        """Rule-based text validator should fail clear topic/difficulty contradictions."""
        world_state = build_truth(
            RunConfig(seed=8102, user_count=10, timeline_ticks=1, items_per_session=8),
            self.sources,
            now=self.now,
        )
        post = next(item for item in world_state.posts if item.difficulty >= 4)
        bad = RenderedPostText(
            render_id="r_bad",
            post_id=post.post_id,
            prompt_id="pp_bad",
            model_name="stub",
            provider="stub",
            title="Absolute beginner intro",
            content="This absolute beginner guide explains biology from scratch.",
        )

        issues = validate_rendered_posts([bad], {post.post_id: post})
        codes = {issue["code"] for issue in issues}
        self.assertIn("difficulty_contradiction", codes)
        self.assertIn("topic_missing", codes)

    def test_seed_render_pipeline_can_be_stubbed_and_validated(self) -> None:
        """Local stub render path should still pass validators and write sidecars."""
        world_state = build_truth(
            RunConfig(seed=8101, user_count=28, timeline_ticks=4, items_per_session=10),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_phase8_render_") as tmp:
            artifacts = render_seed_text(
                world_state,
                output_dir=tmp,
                seed_model_name="gpt-5.4-nano",
                post_target_count=8,
                comment_target_count=4,
                max_comments_per_post_request=4,
            )

            self.assertEqual(artifacts["status"], "passed")
            self.assertTrue(artifacts["rendered_posts"])
            self.assertTrue(artifacts["rendered_comments"])
            self.assertEqual(artifacts["rule_issues"], [])
            self.assertEqual(artifacts["llm_issues"], [])

            files = artifacts["files"]
            for key in ("rendered_posts", "rendered_comments", "text_validation_report"):
                self.assertTrue(Path(files[key]).is_file(), f"missing file for {key}")

    def test_prepare_batch_artifacts_use_responses_api_and_gate_comments_on_rendered_posts(self) -> None:
        """Batch preparation should only unlock comment requests after rendered post sidecars exist."""
        world_state = build_truth(
            RunConfig(seed=8101, user_count=28, timeline_ticks=4, items_per_session=10),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_phase8_prepare_") as tmp:
            prepared = prepare_openai_seed_batches(
                world_state,
                output_dir=tmp,
                seed_model_name="gpt-5.4-nano",
                post_target_count=6,
                comment_target_count=3,
                max_comments_per_post_request=4,
            )

            self.assertEqual(prepared["status"], "prepared_posts_only")
            self.assertEqual(prepared["comment_stage_status"], "blocked_missing_rendered_posts")
            self.assertEqual(len(prepared["comment_prompts"]), 0)
            self.assertTrue(all(request["url"] == "/v1/responses" for request in prepared["post_requests"]))
            self.assertEqual(prepared["comment_requests"], [])

            post_body = prepared["post_requests"][0]["body"]
            self.assertEqual(post_body["text"]["format"]["type"], "json_schema")
            self.assertTrue(post_body["text"]["format"]["strict"])
            self.assertNotIn("openai_comment_sets_submit_manifest", prepared["files"])

    def test_collect_and_retry_prepare_are_separate(self) -> None:
        """Collect should only map outputs and failures; retry preparation should be explicit and separate."""
        world_state = build_truth(
            RunConfig(seed=8101, user_count=28, timeline_ticks=4, items_per_session=10),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_phase8_collect_") as tmp:
            root = Path(tmp)
            prepared = prepare_openai_seed_batches(
                world_state,
                output_dir=root,
                seed_model_name="gpt-5.4-nano",
                post_target_count=2,
                comment_target_count=1,
                max_comments_per_post_request=4,
            )

            post_manifest_path = Path(prepared["files"]["openai_posts_submit_manifest"])
            post_registry = _read_jsonl(Path(prepared["files"]["openai_posts_prompt_registry"]))

            post_status_path = root / "post_batch_status.json"
            post_output_path = root / "post_batch_output.jsonl"
            post_error_path = root / "post_batch_errors.jsonl"
            post_status_path.write_text(json.dumps({"id": "batch_posts_1", "status": "completed"}), encoding="utf-8")

            first_post = post_registry[0]
            post_output = {
                "custom_id": first_post["prompt_id"],
                "response": {
                    "body": {
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": json.dumps(
                                            {"title": "Study note title", "content": "Study note content"}
                                        ),
                                    }
                                ],
                            }
                        ]
                    }
                },
            }
            post_output_path.write_text(json.dumps(post_output) + "\n", encoding="utf-8")
            post_error_path.write_text("", encoding="utf-8")

            post_collect = collect_openai_seed_batch_results(
                batch_kind="posts",
                manifest_path=post_manifest_path,
                batch_status_path=post_status_path,
                output_jsonl_path=post_output_path,
                error_jsonl_path=post_error_path,
            )

            posts_by_id = {post.post_id: post for post in world_state.posts}
            rendered_posts_path = root / "seed_rendered_posts.jsonl"
            rendered_post_sidecars = [
                RenderedPostText(
                    render_id=f"rpost_{item['post_id']}",
                    post_id=str(item["post_id"]),
                    prompt_id=str(item["prompt_id"]),
                    model_name="gpt-5.4-nano",
                    provider="openai_batch",
                    title=f"{posts_by_id[str(item['post_id'])].topic} title",
                    content=(
                        f"Concrete seed post text about {posts_by_id[str(item['post_id'])].topic} "
                        f"and {posts_by_id[str(item['post_id'])].subtopic}."
                    ),
                    validator_status="collected",
                )
                for item in post_registry
            ]
            rendered_posts_path.write_text(
                "".join(json.dumps(record.__dict__, sort_keys=True) + "\n" for record in rendered_post_sidecars),
                encoding="utf-8",
            )
            comment_prepared = prepare_openai_seed_batches(
                world_state,
                output_dir=root,
                seed_model_name="gpt-5.4-nano",
                rendered_posts_path=rendered_posts_path,
                post_target_count=2,
                comment_target_count=1,
                max_comments_per_post_request=4,
            )
            comment_manifest_path = Path(comment_prepared["files"]["openai_comment_sets_submit_manifest"])
            comment_registry = _read_jsonl(Path(comment_prepared["files"]["openai_comment_sets_prompt_registry"]))

            comment_status_path = root / "comment_batch_status.json"
            comment_output_path = root / "comment_batch_output.jsonl"
            comment_error_path = root / "comment_batch_errors.jsonl"
            comment_status_path.write_text(json.dumps({"id": "batch_comments_1", "status": "completed"}), encoding="utf-8")

            first_comment = comment_registry[0]
            failed_comment_id = first_comment["comment_interaction_ids"][0]
            comment_output = {
                "custom_id": first_comment["prompt_id"],
                "response": {
                    "body": {
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": json.dumps(
                                            {
                                                "comments": [
                                                    {
                                                        "interaction_id": failed_comment_id,
                                                        "comment_text": "Useful post. The debugging path is clear.",
                                                    }
                                                ]
                                            }
                                        ),
                                    }
                                ],
                            }
                        ]
                    }
                },
            }
            comment_output_path.write_text(json.dumps(comment_output) + "\n", encoding="utf-8")
            comment_error_path.write_text(
                json.dumps({"custom_id": first_comment["prompt_id"], "error": {"message": "mock failure"}}) + "\n",
                encoding="utf-8",
            )

            comment_collect = collect_openai_seed_batch_results(
                batch_kind="comment_sets",
                manifest_path=comment_manifest_path,
                batch_status_path=comment_status_path,
                output_jsonl_path=comment_output_path,
                error_jsonl_path=comment_error_path,
            )

            self.assertEqual(len(post_collect["rendered_posts"]), 1)
            self.assertEqual(len(comment_collect["rendered_comments"]), 1)
            self.assertEqual(comment_collect["failed_custom_ids"], [first_comment["prompt_id"]])

            collect_report_path = root / "comment_collect_report.json"
            collect_report_path.write_text(
                json.dumps(
                    {
                        "batch_kind": comment_collect["batch_kind"],
                        "manifest_path": comment_collect["manifest_path"],
                        "failed_custom_ids": comment_collect["failed_custom_ids"],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            retry_files = prepare_openai_seed_retry_batches(
                collect_report_path=collect_report_path,
                output_dir=root / "retry",
            )
            self.assertTrue(Path(retry_files["retry_batch_input"]).is_file())
            self.assertTrue(Path(retry_files["retry_submit_manifest"]).is_file())


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    """Read a small JSONL file into memory for assertions."""
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


if __name__ == "__main__":
    unittest.main()
