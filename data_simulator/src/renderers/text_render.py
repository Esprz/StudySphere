"""Text rendering adapters for stubbed seed rendering and OpenAI Batch artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.models import (
    CommentSetRenderPrompt,
    PostRenderPrompt,
    RenderedCommentText,
    RenderedPostText,
)
from core.ids import new_id
from exporters.simulator_json import _to_jsonable


class StubSeedTextRenderer:
    """Deterministic renderer used by tests and offline local validation."""

    provider_name = "stub_seed_renderer"
    model_name = "stub-seed-v1"

    def render_posts(self, prompts: list[PostRenderPrompt]) -> list[RenderedPostText]:
        """Render post sidecar text synchronously from prompt metadata."""
        rendered: list[RenderedPostText] = []
        for prompt in prompts:
            title = _stub_post_title(prompt)
            content = _stub_post_content(prompt)
            rendered.append(
                RenderedPostText(
                    render_id=new_id("rpost"),
                    post_id=prompt.post_id,
                    prompt_id=prompt.prompt_id,
                    model_name=self.model_name,
                    provider=self.provider_name,
                    title=title,
                    content=content,
                )
            )
        return rendered

    def render_comments(self, prompts: list[CommentSetRenderPrompt]) -> list[RenderedCommentText]:
        """Render grouped comment sidecar text synchronously from prompt metadata."""
        rendered: list[RenderedCommentText] = []
        for prompt in prompts:
            for target in prompt.comment_targets:
                comment_text = (
                    f"Useful {prompt.topic.lower()} post. The main idea is clear and the explanation stays focused."
                )
                rendered.append(
                    RenderedCommentText(
                        render_id=new_id("rcmt"),
                        interaction_id=target.interaction_id,
                        post_id=prompt.post_id,
                        prompt_id=prompt.prompt_id,
                        model_name=self.model_name,
                        provider=self.provider_name,
                        comment_text=comment_text,
                    )
                )
        return rendered


class OpenAISeedBatchBuilder:
    """Build OpenAI Batch API input/output artifacts without requiring live network calls."""

    provider_name = "openai_batch"

    def __init__(
        self,
        *,
        model_name: str = "gpt-5.4-nano",
        endpoint: str = "/v1/responses",
    ) -> None:
        self.model_name = model_name
        self.endpoint = endpoint

    def build_post_requests(self, post_prompts: list[PostRenderPrompt]) -> list[dict[str, Any]]:
        """Convert post prompt packages into OpenAI Batch JSONL request objects."""
        requests: list[dict[str, Any]] = []
        for prompt in post_prompts:
            requests.append(
                {
                    "custom_id": prompt.prompt_id,
                    "method": "POST",
                    "url": self.endpoint,
                    "body": _responses_body(
                        model_name=self.model_name,
                        messages=prompt.messages,
                        schema_name="rendered_post_text",
                        schema=_post_response_schema(),
                    ),
                }
            )
        return requests

    def build_comment_set_requests(self, comment_prompts: list[CommentSetRenderPrompt]) -> list[dict[str, Any]]:
        """Convert comment-set prompts into OpenAI Batch JSONL request objects."""
        requests: list[dict[str, Any]] = []
        for prompt in comment_prompts:
            requests.append(
                {
                    "custom_id": prompt.prompt_id,
                    "method": "POST",
                    "url": self.endpoint,
                    "body": _responses_body(
                        model_name=self.model_name,
                        messages=prompt.messages,
                        schema_name="rendered_comment_set",
                        schema=_comment_set_response_schema(prompt),
                    ),
                }
            )
        return requests

    def write_batch_input(
        self,
        requests: list[dict[str, Any]],
        path: str | Path,
    ) -> Path:
        """Write OpenAI Batch input JSONL file."""
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for request in requests:
                handle.write(json.dumps(_to_jsonable(request), sort_keys=True))
                handle.write("\n")
        return target

    def write_batch_manifest(
        self,
        *,
        batch_input_path: str | Path,
        request_count: int,
        path: str | Path,
        request_kind: str,
        prompt_registry_path: str | Path,
    ) -> Path:
        """Write a local manifest that describes how this batch should be submitted."""
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "provider": self.provider_name,
            "model_name": self.model_name,
            "endpoint": self.endpoint,
            "completion_window": "24h",
            "request_kind": request_kind,
            "batch_input_path": str(Path(batch_input_path).expanduser().resolve()),
            "prompt_registry_path": str(Path(prompt_registry_path).expanduser().resolve()),
            "request_count": request_count,
            "notes": [
                "Upload the input file with purpose=batch.",
                "Create a batch pointing at the same endpoint used in each JSONL line.",
                "Match outputs back to prompts with custom_id.",
                "Batch submission, collection, and retry preparation are separate steps.",
            ],
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return target

    def parse_batch_output(self, path: str | Path) -> dict[str, Any]:
        """Parse Responses API Batch output JSONL into custom_id -> structured payload."""
        outputs: dict[str, Any] = {}
        source = Path(path).expanduser().resolve()
        with source.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                payload = json.loads(stripped)
                custom_id = str(payload.get("custom_id"))
                response = payload.get("response", {})
                body = response.get("body", {})
                text_payload = _extract_response_output_text(body)
                if not text_payload:
                    continue
                try:
                    outputs[custom_id] = json.loads(text_payload)
                except json.JSONDecodeError:
                    outputs[custom_id] = text_payload.strip()
        return outputs


def _responses_body(
    *,
    model_name: str,
    messages: list[Any],
    schema_name: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Build a Responses API request body with strict JSON schema output."""
    return {
        "model": model_name,
        "input": [
            {
                "type": "message",
                "role": message.role,
                "content": [{"type": "input_text", "text": message.content}],
            }
            for message in messages
        ],
        "temperature": 0.4,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
    }


def _post_response_schema() -> dict[str, Any]:
    """Return strict schema for one rendered post payload."""
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["title", "content"],
        "additionalProperties": False,
    }


def _comment_set_response_schema(prompt: CommentSetRenderPrompt) -> dict[str, Any]:
    """Return strict schema for one rendered comment set payload."""
    interaction_ids = [target.interaction_id for target in prompt.comment_targets]
    return {
        "type": "object",
        "properties": {
            "comments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "interaction_id": {
                            "type": "string",
                            "enum": interaction_ids,
                        },
                        "comment_text": {"type": "string"},
                    },
                    "required": ["interaction_id", "comment_text"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["comments"],
        "additionalProperties": False,
    }


def _extract_response_output_text(body: dict[str, Any]) -> str:
    """Extract the JSON text payload from a Responses API result body."""
    output = body.get("output", [])
    for item in output:
        if item.get("type") != "message":
            continue
        for content_item in item.get("content", []):
            if content_item.get("type") == "output_text":
                return str(content_item.get("text", ""))
    return ""


def _stub_post_title(prompt: PostRenderPrompt) -> str:
    """Create a deterministic title aligned with prompt metadata."""
    if prompt.content_format == "qa_post":
        return f"{prompt.topic}: what is the key idea behind this question?"
    return f"{prompt.topic}: {prompt.content_format.replace('_', ' ')} notes"


def _stub_post_content(prompt: PostRenderPrompt) -> str:
    """Create deterministic post body text that satisfies Phase-8 validators."""
    difficulty_label = {
        1: "beginner",
        2: "intro",
        3: "intermediate",
        4: "advanced",
        5: "expert",
    }.get(prompt.difficulty, "intermediate")
    return (
        f"This {prompt.content_format.replace('_', ' ')} is about {prompt.topic.lower()}. "
        f"It targets a {difficulty_label} level and stays focused on the structured topic."
    )
