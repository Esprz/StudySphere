"""CLI for batch-oriented prepare/submit/collect/retry workflows."""

from __future__ import annotations

import argparse
import json
import os
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from config.models import RunConfig
from exporters.simulator_json import _to_jsonable
from pipeline.render_text import (
    collect_openai_seed_batch_results,
    collect_scale_batch_results,
    prepare_batch_retry_artifacts,
)
from pipeline.run import run_simulation


def prepare_seed_bundle(
    *,
    config: RunConfig,
    design_root: str | Path,
    output_dir: str | Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run one prepare-only seed workflow and return the summary bundle."""
    return run_simulation(
        config=RunConfig(
            seed=config.seed,
            user_count=config.user_count,
            timeline_ticks=config.timeline_ticks,
            items_per_session=config.items_per_session,
            max_candidate_pool_size=config.max_candidate_pool_size,
            render_text=True,
            seed_model_name=config.seed_model_name,
            seed_post_target_count=config.seed_post_target_count,
            seed_comment_target_count=config.seed_comment_target_count,
            seed_max_comments_per_post_request=config.seed_max_comments_per_post_request,
            seed_rendered_posts_path=config.seed_rendered_posts_path,
        ),
        design_root=design_root,
        output_dir=output_dir,
        now=now,
    )


def prepare_scale_bundle(
    *,
    config: RunConfig,
    design_root: str | Path,
    output_dir: str | Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run one prepare-only scale workflow and return the summary bundle."""
    return run_simulation(
        config=RunConfig(
            seed=config.seed,
            user_count=config.user_count,
            timeline_ticks=config.timeline_ticks,
            items_per_session=config.items_per_session,
            max_candidate_pool_size=config.max_candidate_pool_size,
            render_scale_text=True,
            scale_openai_model_name=config.scale_openai_model_name,
            scale_gemini_model_name=config.scale_gemini_model_name,
            scale_gemini_share_percentage=config.scale_gemini_share_percentage,
            scale_post_target_count=config.scale_post_target_count,
            scale_comment_target_count=config.scale_comment_target_count,
            scale_max_comments_per_post_request=config.scale_max_comments_per_post_request,
            scale_rendered_posts_path=config.scale_rendered_posts_path,
        ),
        design_root=design_root,
        output_dir=output_dir,
        now=now,
    )


def write_openai_submit_script(
    *,
    manifest_path: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    """Write one OpenAI upload+batch-create shell script from a submit manifest."""
    manifest = _load_json(Path(manifest_path))
    root = _resolve_output_root(output_dir, manifest_path)
    stem = Path(manifest_path).stem.replace("_submit_manifest", "")
    upload_response_path = root / f"{stem}_upload_response.json"
    create_request_path = root / f"{stem}_batch_create_request.json"
    create_response_path = root / f"{stem}_batch_create_response.json"
    script_path = root / f"{stem}_submit.sh"

    input_file_path = shlex.quote(str(manifest["batch_input_path"]))
    upload_response_path_q = shlex.quote(str(upload_response_path))
    create_request_path_q = shlex.quote(str(create_request_path))
    create_response_path_q = shlex.quote(str(create_response_path))
    endpoint = str(manifest["endpoint"])
    completion_window = str(manifest["completion_window"])
    request_kind = str(manifest["request_kind"])
    model_name = str(manifest["model_name"])
    script = f"""#!/usr/bin/env bash
set -euo pipefail

OPENAI_API_KEY="${{OPENAI_API_KEY:?set OPENAI_API_KEY}}"
OPENAI_BASE_URL="${{OPENAI_BASE_URL:-https://api.openai.com}}"
PYTHON_BIN="${{PYTHON_BIN:-python3}}"

INPUT_FILE_PATH={input_file_path}
UPLOAD_RESPONSE_PATH={upload_response_path_q}
CREATE_REQUEST_PATH={create_request_path_q}
CREATE_RESPONSE_PATH={create_response_path_q}

curl -sS "${{OPENAI_BASE_URL}}/v1/files" \\
  -H "Authorization: Bearer ${{OPENAI_API_KEY}}" \\
  -F "purpose=batch" \\
  -F "file=@${{INPUT_FILE_PATH}}" \\
  > "${{UPLOAD_RESPONSE_PATH}}"

INPUT_FILE_ID="$("${{PYTHON_BIN}}" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["id"])' "${{UPLOAD_RESPONSE_PATH}}")"

cat > "${{CREATE_REQUEST_PATH}}" <<JSON
{{
  "input_file_id": "${{INPUT_FILE_ID}}",
  "endpoint": "{endpoint}",
  "completion_window": "{completion_window}",
  "metadata": {{
    "request_kind": "{request_kind}",
    "model_name": "{model_name}",
    "manifest_path": {json.dumps(str(Path(manifest_path).expanduser().resolve()))}
  }}
}}
JSON

curl -sS "${{OPENAI_BASE_URL}}/v1/batches" \\
  -H "Authorization: Bearer ${{OPENAI_API_KEY}}" \\
  -H "Content-Type: application/json" \\
  -d @"${{CREATE_REQUEST_PATH}}" \\
  > "${{CREATE_RESPONSE_PATH}}"

cat "${{CREATE_RESPONSE_PATH}}"
"""
    _write_executable_script(script_path, script)
    return {
        "submit_script": str(script_path),
        "upload_response_path": str(upload_response_path),
        "batch_create_request_path": str(create_request_path),
        "batch_create_response_path": str(create_response_path),
    }


def write_gemini_submit_script(
    *,
    manifest_path: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    """Write one Gemini file-upload+batch-create shell script from a submit manifest."""
    manifest = _load_json(Path(manifest_path))
    root = _resolve_output_root(output_dir, manifest_path)
    stem = Path(manifest_path).stem.replace("_submit_manifest", "")
    header_path = root / f"{stem}_upload_headers.tmp"
    upload_response_path = root / f"{stem}_upload_response.json"
    create_request_path = root / f"{stem}_batch_create_request.json"
    create_response_path = root / f"{stem}_batch_create_response.json"
    script_path = root / f"{stem}_submit.sh"
    display_name = stem.replace("_", "-")

    input_file_path = shlex.quote(str(manifest["batch_input_path"]))
    header_path_q = shlex.quote(str(header_path))
    upload_response_path_q = shlex.quote(str(upload_response_path))
    create_request_path_q = shlex.quote(str(create_request_path))
    create_response_path_q = shlex.quote(str(create_response_path))
    model_name = str(manifest["model_name"])

    script = f"""#!/usr/bin/env bash
set -euo pipefail

GEMINI_API_KEY="${{GEMINI_API_KEY:?set GEMINI_API_KEY}}"
GEMINI_BASE_URL="${{GEMINI_BASE_URL:-https://generativelanguage.googleapis.com}}"
PYTHON_BIN="${{PYTHON_BIN:-python3}}"

INPUT_FILE_PATH={input_file_path}
HEADER_PATH={header_path_q}
UPLOAD_RESPONSE_PATH={upload_response_path_q}
CREATE_REQUEST_PATH={create_request_path_q}
CREATE_RESPONSE_PATH={create_response_path_q}
DISPLAY_NAME={json.dumps(display_name)}
NUM_BYTES="$(wc -c < "${{INPUT_FILE_PATH}}" | tr -d ' ')"

curl -sS "${{GEMINI_BASE_URL}}/upload/v1beta/files?key=${{GEMINI_API_KEY}}" \\
  -D "${{HEADER_PATH}}" \\
  -H "X-Goog-Upload-Protocol: resumable" \\
  -H "X-Goog-Upload-Command: start" \\
  -H "X-Goog-Upload-Header-Content-Length: ${{NUM_BYTES}}" \\
  -H "X-Goog-Upload-Header-Content-Type: jsonl" \\
  -H "Content-Type: application/json" \\
  -d "{{\\"file\\": {{\\"display_name\\": \\"${{DISPLAY_NAME}}\\"}}}}"

UPLOAD_URL="$(grep -i 'x-goog-upload-url:' "${{HEADER_PATH}}" | cut -d' ' -f2- | tr -d '\\r')"
rm -f "${{HEADER_PATH}}"

curl -sS "${{UPLOAD_URL}}" \\
  -H "Content-Length: ${{NUM_BYTES}}" \\
  -H "X-Goog-Upload-Offset: 0" \\
  -H "X-Goog-Upload-Command: upload, finalize" \\
  --data-binary @"${{INPUT_FILE_PATH}}" \\
  > "${{UPLOAD_RESPONSE_PATH}}"

FILE_NAME="$("${{PYTHON_BIN}}" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["file"]["name"])' "${{UPLOAD_RESPONSE_PATH}}")"

cat > "${{CREATE_REQUEST_PATH}}" <<JSON
{{
  "batch": {{
    "display_name": "${{DISPLAY_NAME}}",
    "input_config": {{
      "file_name": "${{FILE_NAME}}"
    }}
  }}
}}
JSON

curl -sS "${{GEMINI_BASE_URL}}/v1beta/models/{model_name}:batchGenerateContent?key=${{GEMINI_API_KEY}}" \\
  -H "Content-Type: application/json" \\
  -X POST \\
  -d @"${{CREATE_REQUEST_PATH}}" \\
  > "${{CREATE_RESPONSE_PATH}}"

cat "${{CREATE_RESPONSE_PATH}}"
"""
    _write_executable_script(script_path, script)
    return {
        "submit_script": str(script_path),
        "upload_response_path": str(upload_response_path),
        "batch_create_request_path": str(create_request_path),
        "batch_create_response_path": str(create_response_path),
    }


def collect_openai_seed_to_files(
    *,
    batch_kind: str,
    manifest_path: str | Path,
    batch_status_path: str | Path,
    output_jsonl_path: str | Path | None = None,
    error_jsonl_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Collect one OpenAI seed batch and write normalized report artifacts."""
    report = collect_openai_seed_batch_results(
        batch_kind=batch_kind,
        manifest_path=manifest_path,
        batch_status_path=batch_status_path,
        output_jsonl_path=output_jsonl_path,
        error_jsonl_path=error_jsonl_path,
    )
    return _write_collect_bundle(
        report=report,
        manifest_path=manifest_path,
        output_dir=output_dir,
    )


def collect_scale_to_files(
    *,
    provider: str,
    batch_kind: str,
    manifest_path: str | Path,
    batch_status_path: str | Path,
    output_jsonl_path: str | Path | None = None,
    error_jsonl_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Collect one scale batch and write normalized report artifacts."""
    report = collect_scale_batch_results(
        provider=provider,
        batch_kind=batch_kind,
        manifest_path=manifest_path,
        batch_status_path=batch_status_path,
        output_jsonl_path=output_jsonl_path,
        error_jsonl_path=error_jsonl_path,
    )
    return _write_collect_bundle(
        report=report,
        manifest_path=manifest_path,
        output_dir=output_dir,
    )


def fetch_openai_batch_status(
    *,
    batch_id: str,
    output_path: str | Path,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com",
) -> dict[str, Any]:
    """Fetch one OpenAI batch status payload and write it to disk."""
    resolved_api_key = _resolve_api_key(api_key, env_var="OPENAI_API_KEY")
    request = Request(
        f"{base_url.rstrip('/')}/v1/batches/{batch_id}",
        headers={"Authorization": f"Bearer {resolved_api_key}"},
        method="GET",
    )
    with urlopen(request) as response:
        payload = json.loads(response.read().decode("utf-8"))
    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "batch_id": str(payload.get("id", batch_id)),
        "status_path": str(target),
        "status": str(payload.get("status", "unknown")),
    }


def download_openai_batch_files(
    *,
    batch_status_path: str | Path,
    output_dir: str | Path | None = None,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com",
) -> dict[str, Any]:
    """Download available OpenAI output/error files referenced by one batch status."""
    resolved_api_key = _resolve_api_key(api_key, env_var="OPENAI_API_KEY")
    status_payload = _load_json(Path(batch_status_path))
    root = _resolve_output_root(output_dir, batch_status_path)
    stem = Path(batch_status_path).stem.replace("_status", "")
    files: dict[str, str | None] = {
        "batch_status_path": str(Path(batch_status_path).expanduser().resolve()),
        "output_jsonl_path": None,
        "error_jsonl_path": None,
    }

    output_file_id = status_payload.get("output_file_id")
    if output_file_id:
        output_path = root / f"{stem}_output.jsonl"
        _download_openai_file_content(
            file_id=str(output_file_id),
            output_path=output_path,
            api_key=resolved_api_key,
            base_url=base_url,
        )
        files["output_jsonl_path"] = str(output_path)

    error_file_id = status_payload.get("error_file_id")
    if error_file_id:
        error_path = root / f"{stem}_errors.jsonl"
        _download_openai_file_content(
            file_id=str(error_file_id),
            output_path=error_path,
            api_key=resolved_api_key,
            base_url=base_url,
        )
        files["error_jsonl_path"] = str(error_path)

    return {
        "batch_id": str(status_payload.get("id", "")),
        "status": str(status_payload.get("status", "unknown")),
        "files": files,
    }


def _write_collect_bundle(
    *,
    report: dict[str, Any],
    manifest_path: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Write collect report plus any rendered sidecars to disk."""
    root = _resolve_output_root(output_dir, manifest_path)
    stem = Path(manifest_path).stem.replace("_submit_manifest", "")
    report_path = root / f"{stem}_collect_report.json"
    report["files"] = {"collect_report": str(report_path)}
    if report.get("rendered_posts"):
        rendered_posts_path = root / f"{stem}_rendered_posts.jsonl"
        _write_jsonl_records(report["rendered_posts"], rendered_posts_path)
        report["files"]["rendered_posts"] = str(rendered_posts_path)
    if report.get("rendered_comments"):
        rendered_comments_path = root / f"{stem}_rendered_comments.jsonl"
        _write_jsonl_records(report["rendered_comments"], rendered_comments_path)
        report["files"]["rendered_comments"] = str(rendered_comments_path)
    report_path.write_text(json.dumps(_to_jsonable(report), indent=2, sort_keys=True), encoding="utf-8")
    return report


def _build_parser() -> argparse.ArgumentParser:
    """Build batch CLI parser."""
    parser = argparse.ArgumentParser(description="StudySphere batch workflow CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_seed = subparsers.add_parser("prepare-seed", help="Build truth and prepare OpenAI seed batch artifacts")
    _add_prepare_args(prepare_seed)

    prepare_scale = subparsers.add_parser("prepare-scale", help="Build truth and prepare scale batch artifacts")
    _add_prepare_args(prepare_scale, include_scale_args=True)

    submit_openai_seed = subparsers.add_parser("submit-openai-seed", help="Write OpenAI seed submit shell script")
    _add_submit_args(submit_openai_seed)

    submit_scale_openai = subparsers.add_parser("submit-scale-openai", help="Write OpenAI scale submit shell script")
    _add_submit_args(submit_scale_openai)

    submit_scale_gemini = subparsers.add_parser("submit-scale-gemini", help="Write Gemini scale submit shell script")
    _add_submit_args(submit_scale_gemini)

    fetch_openai_batch = subparsers.add_parser(
        "fetch-openai-batch-status",
        help="Fetch one OpenAI batch status JSON",
    )
    _add_openai_fetch_args(fetch_openai_batch)

    download_openai_files = subparsers.add_parser(
        "download-openai-batch-files",
        help="Download output/error files referenced by one OpenAI batch status JSON",
    )
    download_openai_files.add_argument("--batch-status-path", type=Path, required=True)
    download_openai_files.add_argument("--output-dir", type=Path, default=None)
    download_openai_files.add_argument("--api-key", type=str, default=None)
    download_openai_files.add_argument("--base-url", type=str, default="https://api.openai.com")

    collect_openai_seed = subparsers.add_parser("collect-openai-seed", help="Collect one OpenAI seed batch")
    _add_collect_args(collect_openai_seed)
    collect_openai_seed.add_argument("--batch-kind", choices=["posts", "comment_sets"], required=True)

    collect_scale_openai = subparsers.add_parser("collect-scale-openai", help="Collect one OpenAI scale batch")
    _add_collect_args(collect_scale_openai)
    collect_scale_openai.add_argument("--batch-kind", choices=["posts", "comment_sets"], required=True)

    collect_scale_gemini = subparsers.add_parser("collect-scale-gemini", help="Collect one Gemini scale batch")
    _add_collect_args(collect_scale_gemini)
    collect_scale_gemini.add_argument("--batch-kind", choices=["posts", "comment_sets"], required=True)

    prepare_retry = subparsers.add_parser("prepare-retry", help="Prepare retry shard from a collect report")
    prepare_retry.add_argument("--collect-report-path", type=Path, required=True)
    prepare_retry.add_argument("--output-dir", type=Path, required=True)

    return parser


def _add_prepare_args(parser: argparse.ArgumentParser, *, include_scale_args: bool = False) -> None:
    """Add common prepare args."""
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--user-count", type=int, default=100)
    parser.add_argument("--timeline-ticks", type=int, default=30)
    parser.add_argument("--items-per-session", type=int, default=12)
    parser.add_argument("--max-candidate-pool-size", type=int, default=80)
    parser.add_argument(
        "--design-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "default_source_bundle",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--now", type=str, default=None)
    parser.add_argument("--seed-model-name", type=str, default="gpt-5.4-nano")
    parser.add_argument("--seed-post-target-count", type=int, default=12)
    parser.add_argument("--seed-comment-target-count", type=int, default=12)
    parser.add_argument("--seed-max-comments-per-post-request", type=int, default=4)
    parser.add_argument("--seed-rendered-posts-path", type=str, default=None)
    if include_scale_args:
        parser.add_argument("--scale-openai-model-name", type=str, default="gpt-5-nano")
        parser.add_argument("--scale-gemini-model-name", type=str, default="gemini-2.5-flash-lite")
        parser.add_argument("--scale-gemini-share-percentage", type=int, default=0)
        parser.add_argument("--scale-post-target-count", type=int, default=None)
        parser.add_argument("--scale-comment-target-count", type=int, default=None)
        parser.add_argument("--scale-max-comments-per-post-request", type=int, default=6)
        parser.add_argument("--scale-rendered-posts-path", type=str, default=None)


def _add_submit_args(parser: argparse.ArgumentParser) -> None:
    """Add common submit-script args."""
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)


def _add_openai_fetch_args(parser: argparse.ArgumentParser) -> None:
    """Add OpenAI batch fetch args."""
    parser.add_argument("--batch-id", type=str, default=None)
    parser.add_argument("--create-response-path", type=Path, default=None)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--base-url", type=str, default="https://api.openai.com")


def _add_collect_args(parser: argparse.ArgumentParser) -> None:
    """Add common collect args."""
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--batch-status-path", type=Path, required=True)
    parser.add_argument("--output-jsonl-path", type=Path, default=None)
    parser.add_argument("--error-jsonl-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)


def main() -> None:
    """Execute batch workflow CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command in {"prepare-seed", "prepare-scale"}:
        now = datetime.fromisoformat(args.now) if args.now else None
        config = RunConfig(
            seed=args.seed,
            user_count=args.user_count,
            timeline_ticks=args.timeline_ticks,
            items_per_session=args.items_per_session,
            max_candidate_pool_size=args.max_candidate_pool_size,
            seed_model_name=getattr(args, "seed_model_name", "gpt-5.4-nano"),
            seed_post_target_count=getattr(args, "seed_post_target_count", 12),
            seed_comment_target_count=getattr(args, "seed_comment_target_count", 12),
            seed_max_comments_per_post_request=getattr(args, "seed_max_comments_per_post_request", 4),
            seed_rendered_posts_path=getattr(args, "seed_rendered_posts_path", None),
            scale_openai_model_name=getattr(args, "scale_openai_model_name", "gpt-5-nano"),
            scale_gemini_model_name=getattr(args, "scale_gemini_model_name", "gemini-2.5-flash-lite"),
            scale_gemini_share_percentage=getattr(args, "scale_gemini_share_percentage", 0),
            scale_post_target_count=getattr(args, "scale_post_target_count", None),
            scale_comment_target_count=getattr(args, "scale_comment_target_count", None),
            scale_max_comments_per_post_request=getattr(args, "scale_max_comments_per_post_request", 6),
            scale_rendered_posts_path=getattr(args, "scale_rendered_posts_path", None),
        )
        if args.command == "prepare-seed":
            summary = prepare_seed_bundle(
                config=config,
                design_root=args.design_root,
                output_dir=args.output_dir,
                now=now,
            )
        else:
            summary = prepare_scale_bundle(
                config=config,
                design_root=args.design_root,
                output_dir=args.output_dir,
                now=now,
            )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return

    if args.command == "submit-openai-seed":
        print(json.dumps(write_openai_submit_script(manifest_path=args.manifest_path, output_dir=args.output_dir), indent=2, sort_keys=True))
        return
    if args.command == "submit-scale-openai":
        print(json.dumps(write_openai_submit_script(manifest_path=args.manifest_path, output_dir=args.output_dir), indent=2, sort_keys=True))
        return
    if args.command == "submit-scale-gemini":
        print(json.dumps(write_gemini_submit_script(manifest_path=args.manifest_path, output_dir=args.output_dir), indent=2, sort_keys=True))
        return
    if args.command == "fetch-openai-batch-status":
        batch_id = args.batch_id
        if batch_id is None:
            if args.create_response_path is None:
                raise ValueError("Provide either --batch-id or --create-response-path")
            batch_id = str(_load_json(args.create_response_path).get("id", ""))
            if not batch_id:
                raise ValueError("Could not read batch id from create response")
        report = fetch_openai_batch_status(
            batch_id=batch_id,
            output_path=args.output_path,
            api_key=args.api_key,
            base_url=args.base_url,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "download-openai-batch-files":
        report = download_openai_batch_files(
            batch_status_path=args.batch_status_path,
            output_dir=args.output_dir,
            api_key=args.api_key,
            base_url=args.base_url,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    if args.command == "collect-openai-seed":
        report = collect_openai_seed_to_files(
            batch_kind=args.batch_kind,
            manifest_path=args.manifest_path,
            batch_status_path=args.batch_status_path,
            output_jsonl_path=args.output_jsonl_path,
            error_jsonl_path=args.error_jsonl_path,
            output_dir=args.output_dir,
        )
        print(json.dumps(_to_jsonable(report), indent=2, sort_keys=True))
        return
    if args.command == "collect-scale-openai":
        report = collect_scale_to_files(
            provider="openai",
            batch_kind=args.batch_kind,
            manifest_path=args.manifest_path,
            batch_status_path=args.batch_status_path,
            output_jsonl_path=args.output_jsonl_path,
            error_jsonl_path=args.error_jsonl_path,
            output_dir=args.output_dir,
        )
        print(json.dumps(_to_jsonable(report), indent=2, sort_keys=True))
        return
    if args.command == "collect-scale-gemini":
        report = collect_scale_to_files(
            provider="gemini",
            batch_kind=args.batch_kind,
            manifest_path=args.manifest_path,
            batch_status_path=args.batch_status_path,
            output_jsonl_path=args.output_jsonl_path,
            error_jsonl_path=args.error_jsonl_path,
            output_dir=args.output_dir,
        )
        print(json.dumps(_to_jsonable(report), indent=2, sort_keys=True))
        return

    if args.command == "prepare-retry":
        files = prepare_batch_retry_artifacts(
            collect_report_path=args.collect_report_path,
            output_dir=args.output_dir,
        )
        print(json.dumps(files, indent=2, sort_keys=True))
        return

    raise ValueError(f"Unsupported command: {args.command}")


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON document from disk."""
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _resolve_output_root(output_dir: str | Path | None, manifest_path: str | Path) -> Path:
    """Resolve output directory for generated operational artifacts."""
    if output_dir is None:
        root = Path(manifest_path).expanduser().resolve().parent
    else:
        root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_executable_script(path: Path, content: str) -> Path:
    """Write one shell script and mark it executable."""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
    return path


def _write_jsonl_records(records: list[Any], path: Path) -> Path:
    """Write JSONL records for collected sidecars."""
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_to_jsonable(record), sort_keys=True))
            handle.write("\n")
    return path


def _resolve_api_key(api_key: str | None, *, env_var: str) -> str:
    """Resolve API key from arg or environment."""
    if api_key:
        return api_key
    resolved = os.environ.get(env_var, "").strip()
    if not resolved:
        raise ValueError(f"Missing API key: pass --api-key or set {env_var}")
    return resolved


def _download_openai_file_content(
    *,
    file_id: str,
    output_path: Path,
    api_key: str,
    base_url: str,
) -> Path:
    """Download one OpenAI file content payload to disk."""
    request = Request(
        f"{base_url.rstrip('/')}/v1/files/{file_id}/content",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urlopen(request) as response:
        payload = response.read()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    return output_path


if __name__ == "__main__":
    main()
