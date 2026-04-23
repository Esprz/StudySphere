"""Pipeline entrypoints for simulator runtime flows."""

from .build_truth import build_truth
from .validate import validate_and_write, validate_world_state, write_validation_report


def run_simulation(*args, **kwargs):
    """Lazy import run entrypoint to avoid `python -m pipeline.run` warnings."""
    from .run import run_simulation as _run_simulation

    return _run_simulation(*args, **kwargs)


__all__ = [
    "build_truth",
    "run_simulation",
    "validate_and_write",
    "validate_world_state",
    "write_validation_report",
]
