# Simulator Design

## Goal

`data_simulator` is the current synthetic data generator for StudySphere.

It is designed to produce:

- structured user/content/session/interactions truth
- analytics logs for offline analysis
- batch text-generation artifacts for seed and scale workflows

It is not currently a direct DB seeder.

## Core Principles

The simulator keeps a strict separation between:

1. structured truth generation
2. text generation
3. validation
4. release packaging

That boundary matters:

- structured truth is the causal ground truth
- LLM text is only a surface layer
- validation can reject weak text without changing truth

## Runtime Shape

There are two main entrypoints:

### `pipeline.run`

Use for:

- structured-only runs
- runs that also prepare seed text batch artifacts
- runs that also prepare scale text batch artifacts

This command writes a run directory containing:

- entity JSONL
- analytics logs
- `validation_report.json`
- `run_summary.json`
- optional batch preparation artifacts

### `pipeline.batch_cli`

Use for:

- prepare
- submit
- fetch status
- download batch files
- collect
- prepare retry shards

This keeps batch operations explicit and separable.

## Data Model

The structured simulator truth centers on:

- users
- goals
- posts
- sessions
- exposures
- interactions
- focus sessions
- propensity logs

These records are exported as simulator-native JSONL, not DB rows.

## Truth Layer

The truth layer is rule-based.

It determines:

- user latent traits
- goals
- activity intent
- content metadata
- candidate ranking
- interaction probabilities
- session outcomes

This is the canonical causal layer of the simulator.

## Text Layer

The text layer is batch-oriented.

### Seed text

- provider: OpenAI Batch
- purpose: high-quality seed post/comment text
- request shape:
  - one post -> one request
  - one post -> one comment-set request

### Scale text

- providers: OpenAI Batch + Gemini Batch
- provider split happens at user level
- one user's posts/comments must stay on one provider within the run

Comments depend on concrete rendered post text, so text generation is always
two-stage:

1. render posts
2. collect rendered posts
3. render comments against those collected post sidecars

## Runtime Configuration

Important knobs:

- `user_count`
- `timeline_ticks`
- `items_per_session`
- `max_candidate_pool_size`
- `seed_post_target_count`
- `seed_comment_target_count`
- `seed_max_comments_per_post_request`
- `scale_gemini_share_percentage`
- `scale_post_target_count`
- `scale_comment_target_count`
- `scale_max_comments_per_post_request`

The defaults are intentionally small so local dry runs stay cheap and fast.

## Calibrated Recipes

The current operating recipes are:

- dry run
- seed quality build
- first scale run
- medium production run

At a high level:

- dry run uses small seed text coverage just to verify workflow
- seed quality build increases seed post/comment coverage
- first scale run uses mixed-provider scale generation with conservative Gemini share

## Output Contract

The simulator currently writes a flat working directory for operations.

That working directory may contain:

- canonical runtime outputs
- batch manifests
- batch input JSONL
- collect reports
- rendered sidecars
- provider output/status files

For release purposes, these should later be packaged into a curated release
bundle with a stable manifest and a smaller public surface area.

## Current Boundary

What is implemented:

- structured truth generation
- validators
- JSONL export
- seed batch workflow
- scale batch workflow
- generation recipe controls

What is still deferred:

- DB adapter
- release packager
- first real scale dry run and calibration loop

## Internal Specs

There are deeper internal design/specification files under `design/`, but this
document is the intended high-level design summary for normal development and
operations.
