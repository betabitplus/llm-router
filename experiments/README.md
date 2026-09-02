# Engineering experiments

This directory preserves durable investigations of uncertain provider behavior. The pilot uses five provider-level Engineering Experiment capsules under `experiments/llm_router/`.

Each capsule is intentionally autonomous:

```text
exp_####_<provider>/
├── src/experiment.py
├── src/...
├── report/report.ipynb
├── inputs/
├── artifacts/
├── pyproject.toml
├── uv.lock
└── .python-version
```

`src/experiment.py` is the canonical executable entrypoint. Provider-specific helpers and probes belong to the same capsule; experiments do not import production `llm_router`, project `src/`, tests, sibling capsules, or shared experiment helpers. Small causal media inputs are copied into each capsule rather than referenced from elsewhere in the repository.

The authoritative report is only `report/report.ipynb`. It follows one provider-level Question followed by ordered Step → captured Evidence pairs and a Conclusion. Evidence cells use `hide-input` and retain real Jupyter outputs such as text, JSON, images, and links to PDF/video inputs.

Capture is performed explicitly through `scripts/capture_experiment.py`. The script copies the capsule to a temporary directory outside the monorepo, executes the notebook with the capsule's locked uv environment and managed Python, then records a capsule digest before copying the captured report back. Documentation and CI never execute provider calls.

Validate all capsules with `scripts/check_experiment_reports.py`. Sphinx renders the authoritative notebooks through a gitignored build-time copy under `docs/experiments/_generated/` with MyST-NB execution disabled.
