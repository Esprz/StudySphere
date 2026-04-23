"""Pipeline entrypoints for simulator runtime flows."""

from .build_truth import build_truth
from .render_text import (
    collect_scale_batch_results,
    collect_openai_seed_batch_results,
    prepare_openai_seed_batches,
    prepare_openai_seed_retry_batches,
    prepare_scale_text_batches,
    render_seed_text,
)
from .validate import validate_and_write, validate_world_state, write_validation_report


def run_simulation(*args, **kwargs):
    """Lazy import run entrypoint to avoid `python -m pipeline.run` warnings."""
    from .run import run_simulation as _run_simulation

    return _run_simulation(*args, **kwargs)


__all__ = [
    "build_truth",
    "collect_scale_batch_results",
    "collect_openai_seed_batch_results",
    "prepare_openai_seed_batches",
    "prepare_openai_seed_retry_batches",
    "prepare_scale_text_batches",
    "render_seed_text",
    "run_simulation",
    "validate_and_write",
    "validate_world_state",
    "write_validation_report",
]
