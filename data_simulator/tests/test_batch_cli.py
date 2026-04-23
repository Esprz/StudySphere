"""Batch workflow CLI helper tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from config.loader import load_sources
from config.models import RunConfig
from pipeline.batch_cli import (
    collect_scale_to_files,
    download_openai_batch_files,
    fetch_openai_batch_status,
    prepare_seed_bundle,
    prepare_scale_bundle,
    write_gemini_submit_script,
    write_openai_submit_script,
)
from pipeline.build_truth import build_truth
from pipeline.render_text import prepare_batch_retry_artifacts, prepare_openai_seed_batches, prepare_scale_text_batches


class TestBatchCli(unittest.TestCase):
    """Validate submit-script generation and collect/retry helpers."""

    def setUp(self) -> None:
        self.design_final_dir = Path(__file__).resolve().parents[1] / "default_source_bundle"
        self.sources = load_sources(self.design_final_dir)
        self.now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)

    def test_prepare_scale_bundle_runs_prepare_only_workflow(self) -> None:
        """Prepare-scale wrapper should return the same batch-oriented summary shape as run_simulation."""
        with tempfile.TemporaryDirectory(prefix="sim_batch_prepare_scale_") as tmp:
            summary = prepare_scale_bundle(
                config=RunConfig(
                    seed=9901,
                    user_count=16,
                    timeline_ticks=2,
                    items_per_session=8,
                    scale_gemini_share_percentage=25,
                ),
                design_root=self.design_final_dir,
                output_dir=tmp,
                now=self.now,
            )

            self.assertIn("scale_text_batch", summary)
            self.assertEqual(summary["scale_text_batch"]["comment_stage_status"], "blocked_missing_rendered_posts")
            self.assertGreater(summary["scale_text_batch"]["prepared_post_request_count"], 0)

    def test_prepare_seed_bundle_unlocks_comment_stage_when_rendered_posts_are_provided(self) -> None:
        """Prepare-seed wrapper should forward seed_rendered_posts_path into the runtime config."""
        world_state = build_truth(
            RunConfig(seed=9900, user_count=16, timeline_ticks=2, items_per_session=8),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_batch_prepare_seed_comments_") as tmp:
            posts_by_id = {post.post_id: post for post in world_state.posts}
            rendered_posts_path = Path(tmp) / "seed_rendered_posts.jsonl"
            rendered_posts_path.write_text(
                "".join(
                    json.dumps(
                        {
                            "render_id": f"rpost_{post.post_id}",
                            "post_id": post.post_id,
                            "prompt_id": f"pp_{post.post_id}",
                            "model_name": "gpt-5.4-nano",
                            "provider": "openai_batch",
                            "title": f"{post.topic} title",
                            "content": (
                                f"Concrete seed post text about {post.topic} "
                                f"and {post.subtopic}."
                            ),
                            "validator_status": "collected",
                        },
                        sort_keys=True,
                    )
                    + "\n"
                    for post in world_state.posts
                ),
                encoding="utf-8",
            )

            summary = prepare_seed_bundle(
                config=RunConfig(
                    seed=9900,
                    user_count=16,
                    timeline_ticks=2,
                    items_per_session=8,
                    seed_rendered_posts_path=str(rendered_posts_path),
                ),
                design_root=self.design_final_dir,
                output_dir=tmp,
                now=self.now,
            )

            self.assertEqual(summary["run_config"]["seed_rendered_posts_path"], str(rendered_posts_path))
            self.assertGreater(summary["seed_text_batch"]["prepared_comment_request_count"], 0)

    def test_write_openai_submit_script_uses_batch_and_file_endpoints(self) -> None:
        """OpenAI submit helper should emit a runnable shell script without jq dependency."""
        world_state = build_truth(
            RunConfig(seed=9902, user_count=12, timeline_ticks=1, items_per_session=6),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_batch_submit_openai_") as tmp:
            prepared = prepare_openai_seed_batches(
                world_state,
                output_dir=tmp,
                seed_model_name="gpt-5.4-nano",
                post_target_count=2,
            )
            files = write_openai_submit_script(
                manifest_path=prepared["files"]["openai_posts_submit_manifest"],
                output_dir=tmp,
            )
            script = Path(files["submit_script"]).read_text(encoding="utf-8")

            self.assertIn("/v1/files", script)
            self.assertIn("/v1/batches", script)
            self.assertIn("/v1/responses", script)
            self.assertIn("purpose=batch", script)
            self.assertNotIn("jq", script)
            self.assertIn('PYTHON_BIN="${PYTHON_BIN:-python3}"', script)
            self.assertTrue(Path(files["submit_script"]).is_file())

    def test_write_gemini_submit_script_uses_file_upload_and_batch_generate_content(self) -> None:
        """Gemini submit helper should emit resumable file upload plus batch create shell steps without jq."""
        world_state = build_truth(
            RunConfig(seed=9903, user_count=18, timeline_ticks=2, items_per_session=8),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_batch_submit_gemini_") as tmp:
            prepared = prepare_scale_text_batches(
                world_state,
                output_dir=tmp,
                openai_model_name="gpt-5-nano",
                gemini_model_name="gemini-2.5-flash-lite",
                gemini_share_percentage=100,
                post_target_count=2,
            )
            files = write_gemini_submit_script(
                manifest_path=prepared["files"]["scale_posts_gemini_submit_manifest"],
                output_dir=tmp,
            )
            script = Path(files["submit_script"]).read_text(encoding="utf-8")

            self.assertIn("/upload/v1beta/files", script)
            self.assertIn(":batchGenerateContent", script)
            self.assertIn("X-Goog-Upload-Protocol: resumable", script)
            self.assertNotIn("jq", script)
            self.assertIn('PYTHON_BIN="${PYTHON_BIN:-python3}"', script)
            self.assertTrue(Path(files["submit_script"]).is_file())

    def test_collect_scale_to_files_writes_report_and_sidecars(self) -> None:
        """Scale collect helper should normalize the collect report and emitted rendered sidecars."""
        world_state = build_truth(
            RunConfig(seed=9904, user_count=18, timeline_ticks=2, items_per_session=8),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_batch_collect_scale_") as tmp:
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
            status_path = Path(tmp) / "status.json"
            output_path = Path(tmp) / "output.jsonl"
            status_path.write_text(
                json.dumps({"name": "batches/123", "metadata": {"state": "JOB_STATE_SUCCEEDED"}}),
                encoding="utf-8",
            )
            output_path.write_text(
                json.dumps(
                    {
                        "key": prompt_id,
                        "response": {
                            "candidates": [
                                {
                                    "content": {
                                        "parts": [
                                            {"text": json.dumps({"title": "t", "content": "c"})}
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

            report = collect_scale_to_files(
                provider="gemini",
                batch_kind="posts",
                manifest_path=manifest_path,
                batch_status_path=status_path,
                output_jsonl_path=output_path,
                output_dir=tmp,
            )

            self.assertEqual(report["status"], "JOB_STATE_SUCCEEDED")
            self.assertIn("collect_report", report["files"])
            self.assertIn("rendered_posts", report["files"])
            self.assertTrue(Path(report["files"]["collect_report"]).is_file())
            self.assertTrue(Path(report["files"]["rendered_posts"]).is_file())

    def test_prepare_batch_retry_artifacts_supports_gemini_reports(self) -> None:
        """Retry preparation should work for Gemini scale batches, not only OpenAI seed batches."""
        world_state = build_truth(
            RunConfig(seed=9905, user_count=18, timeline_ticks=2, items_per_session=8),
            self.sources,
            now=self.now,
        )

        with tempfile.TemporaryDirectory(prefix="sim_batch_retry_") as tmp:
            prepared = prepare_scale_text_batches(
                world_state,
                output_dir=tmp,
                openai_model_name="gpt-5-nano",
                gemini_model_name="gemini-2.5-flash-lite",
                gemini_share_percentage=100,
                post_target_count=2,
            )
            manifest_path = prepared["files"]["scale_posts_gemini_submit_manifest"]
            registry = _read_jsonl(Path(prepared["files"]["scale_posts_gemini_prompt_registry"]))
            collect_report_path = Path(tmp) / "collect_report.json"
            collect_report_path.write_text(
                json.dumps(
                    {
                        "provider": "gemini",
                        "batch_kind": "posts",
                        "manifest_path": manifest_path,
                        "failed_custom_ids": [registry[0]["prompt_id"]],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            retry_files = prepare_batch_retry_artifacts(
                collect_report_path=collect_report_path,
                output_dir=Path(tmp) / "retry",
            )

            self.assertTrue(Path(retry_files["retry_batch_input"]).is_file())
            retry_manifest = json.loads(Path(retry_files["retry_submit_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(retry_manifest["provider"], "gemini_batch")
            self.assertEqual(retry_manifest["request_count"], 1)
            self.assertNotIn("endpoint", retry_manifest)

    def test_fetch_openai_batch_status_writes_json_payload(self) -> None:
        """OpenAI batch-status fetch helper should persist the retrieved JSON document."""
        with tempfile.TemporaryDirectory(prefix="sim_batch_fetch_status_") as tmp:
            output_path = Path(tmp) / "batch_status.json"

            class _FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self) -> bytes:
                    return json.dumps({"id": "batch_test_1", "status": "completed"}).encode("utf-8")

            def _fake_urlopen(request):
                self.assertTrue(request.full_url.endswith("/v1/batches/batch_test_1"))
                self.assertEqual(request.headers["Authorization"], "Bearer test-key")
                return _FakeResponse()

            with patch("pipeline.batch_cli.urlopen", _fake_urlopen):
                report = fetch_openai_batch_status(
                    batch_id="batch_test_1",
                    output_path=output_path,
                    api_key="test-key",
                )

            self.assertEqual(report["status"], "completed")
            self.assertTrue(output_path.is_file())
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["id"], "batch_test_1")

    def test_download_openai_batch_files_writes_output_and_error_files(self) -> None:
        """OpenAI file downloader should write available output and error file contents to disk."""
        with tempfile.TemporaryDirectory(prefix="sim_batch_download_files_") as tmp:
            status_path = Path(tmp) / "openai_posts_batch_status.json"
            status_path.write_text(
                json.dumps(
                    {
                        "id": "batch_test_2",
                        "status": "completed",
                        "output_file_id": "file_out_1",
                        "error_file_id": "file_err_1",
                    }
                ),
                encoding="utf-8",
            )

            class _FakeResponse:
                def __init__(self, payload: bytes):
                    self._payload = payload

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self) -> bytes:
                    return self._payload

            def _fake_urlopen(request):
                if request.full_url.endswith("/v1/files/file_out_1/content"):
                    return _FakeResponse(b'{"ok":"output"}\n')
                if request.full_url.endswith("/v1/files/file_err_1/content"):
                    return _FakeResponse(b'{"ok":"error"}\n')
                raise AssertionError(f"Unexpected URL: {request.full_url}")

            with patch("pipeline.batch_cli.urlopen", _fake_urlopen):
                report = download_openai_batch_files(
                    batch_status_path=status_path,
                    output_dir=tmp,
                    api_key="test-key",
                )

            self.assertEqual(report["status"], "completed")
            output_jsonl_path = Path(str(report["files"]["output_jsonl_path"]))
            error_jsonl_path = Path(str(report["files"]["error_jsonl_path"]))
            self.assertTrue(output_jsonl_path.is_file())
            self.assertTrue(error_jsonl_path.is_file())
            self.assertEqual(output_jsonl_path.read_text(encoding="utf-8"), '{"ok":"output"}\n')
            self.assertEqual(error_jsonl_path.read_text(encoding="utf-8"), '{"ok":"error"}\n')


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    """Load a JSONL fixture from disk."""
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


if __name__ == "__main__":
    unittest.main()
