# Data Simulator

This directory contains the current StudySphere synthetic data simulator.

It generates:

- structured simulator truth as JSONL
- analytics logs
- validation reports
- seed text batch artifacts for OpenAI
- scale text batch artifacts for OpenAI and Gemini

It does not currently write directly into the app database.

For the high-level architecture, see
[SIMULATOR_DESIGN.md](/home/sy/projects/personal/StudySphere/data_simulator/SIMULATOR_DESIGN.md).

## Runtime Model

The simulator is organized around two runtime entrypoints:

- `pipeline.run`
  - one-shot structured run
  - optional seed or scale batch preparation
- `pipeline.batch_cli`
  - batch workflow commands for prepare / submit / fetch / download / collect / retry

The runtime reads configuration from:

- `default_source_bundle/sources/`

The runtime source bundle lives under:

- `default_source_bundle/`

## Local Setup

Use the project virtual environment.

```bash
cd /home/sy/projects/personal/StudySphere/data_simulator
python3 -m venv .venv
./.venv/bin/python -m unittest discover -s tests
```

## Common Local Commands

Structured-only run:

```bash
cd /home/sy/projects/personal/StudySphere/data_simulator
PYTHONPATH=src ./.venv/bin/python -m pipeline.run \
  --seed 1001 \
  --user-count 100 \
  --timeline-ticks 30 \
  --items-per-session 12 \
  --max-candidate-pool-size 80 \
  --output-dir tmp_runs/local_structured_100u
```

Prepare seed batch artifacts:

```bash
PYTHONPATH=src ./.venv/bin/python -m pipeline.batch_cli prepare-seed \
  --seed 1001 \
  --user-count 100 \
  --timeline-ticks 30 \
  --items-per-session 12 \
  --max-candidate-pool-size 80 \
  --seed-post-target-count 12 \
  --seed-comment-target-count 12 \
  --output-dir tmp_runs/seed_prepare_100u
```

Prepare scale batch artifacts:

```bash
PYTHONPATH=src ./.venv/bin/python -m pipeline.batch_cli prepare-scale \
  --seed 1001 \
  --user-count 1000 \
  --timeline-ticks 30 \
  --items-per-session 12 \
  --max-candidate-pool-size 80 \
  --scale-openai-model-name gpt-5-nano \
  --scale-gemini-model-name gemini-2.5-flash-lite \
  --scale-gemini-share-percentage 20 \
  --output-dir tmp_runs/scale_prepare_1000u
```

Run tests:

```bash
PYTHONPATH=src ./.venv/bin/python -m unittest discover -s tests
```

## Batch Workflow

Seed workflow:

1. `prepare-seed`
2. `submit-openai-seed`
3. `fetch-openai-batch-status`
4. `download-openai-batch-files`
5. `collect-openai-seed`
6. re-run `prepare-seed` with `--seed-rendered-posts-path ...`
7. submit / fetch / download / collect comments

Scale workflow:

1. `prepare-scale`
2. `submit-scale-openai`
3. `submit-scale-gemini`
4. fetch / download / collect provider post batches
5. re-run `prepare-scale` with `--scale-rendered-posts-path ...`
6. submit / fetch / download / collect provider comment-set batches

The simulator intentionally keeps:

- submit
- collect
- retry preparation

as separate steps.

## Output Shape

A normal run directory contains:

- entity JSONL
- analytics logs
- `validation_report.json`
- `run_summary.json`
- optional batch preparation artifacts
- optional collected text sidecars

Release packaging is a later step; the current runtime writes a flat working
directory for operations.

## Docker / Compose

The repo root `docker-compose.yml` exposes a `data-simulator` service for
offline runs.

Useful root-level shortcuts:

- `make simulator-run`
- `make simulator-prepare-seed`
- `make simulator-prepare-scale`
- `make simulator-test`

## Notes

- Runtime defaults are intentionally small and safe.
- DB adaptation, release packaging, and the first real scale dry run are still deferred.
