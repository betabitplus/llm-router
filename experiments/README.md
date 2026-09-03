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
├── jupyter/kernels/<name>/kernel.json
├── pyproject.toml
├── uv.lock
└── .python-version
```

`src/experiment.py` is the canonical executable entrypoint. Provider-specific helpers and probes belong to the same capsule; experiments do not import production `llm_router`, project `src/`, tests, sibling capsules, or shared experiment helpers. Small causal media inputs are copied into each capsule rather than referenced from elsewhere in the repository.

The authoritative report is only `report/report.ipynb`. It follows one provider-level Question followed by ordered Step → captured Evidence pairs and a Conclusion. Evidence cells use `hide-input` and retain real Jupyter outputs such as text, JSON, images, and links to PDF/video inputs.

Capture is explicit through `uv run ternforge-docops experiments capture ####`. DocOps copies the capsule to an isolated temporary directory, executes the notebook through the capsule-owned Jupyter kernelspec, records the causal capsule digest, validates the captured report, and only then replaces retained evidence. Documentation and CI never execute provider calls.

Validate all capsules with `uv run ternforge-docops experiments validate`. Sphinx mounts the authoritative notebooks in place through DocOps with MyST-NB execution disabled; no generated notebook copy is kept under `docs/`.
