# Default Source Bundle

This directory is the simulator's default runtime source bundle.

Rules:

- production and local runs should read JSON source files from here
- `design/design_final/` remains the editable design/spec area
- changes should be promoted from design into this runtime bundle explicitly, not consumed in-place

Current contents:

- `sources/*.json`: copied runtime source snapshot used by `run.py` and `pipeline.batch_cli`
- `templates/*.json`: copied record-shape templates kept with the bundle for contract clarity and future runtime/export use

Current runtime behavior:

- the simulator currently loads `sources/*.json`
- `templates/*.json` are not yet consumed by loader code, but they are kept here so the default bundle stays complete and decoupled from `design_final/`
