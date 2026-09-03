# Engineering experiments

Engineering experiments preserve **what was observed while answering an uncertain engineering question**. Each retained experiment is one self-contained provider capsule under `experiments/llm_router/` with one canonical executable entrypoint and one authoritative captured notebook report. Experiments may inform an ADR, Requirement, or Engineering Constraint; they never verify a production contract.

## Experiment log

```{needtable} Engineering experiment log
:columns: id;title;experiment_date;informs
:style: table
:filter: type == "exp"
:sort: id
```

The pilot intentionally contains five provider-level experiments:

- **EXP_0001 — AI Studio:** text, retries, model discovery, image/PDF structured output, named tools, tool loops, schema-reference normalization, local video, and remote video.
- **EXP_0002 — Google GenAI:** text, retries, model discovery, image/PDF structured output, local/remote video, tool loops, and named tool choice.
- **EXP_0003 — Gemini WebAPI:** authenticated runtime preflight, text, retries, image/PDF/video structured output, remote video, tool loops, and named tool choice.
- **EXP_0004 — OpenAI-compatible:** text, retries, token logprobs, structured image input, tool loops, and named tool choice.
- **EXP_0005 — QwenChat:** text, retries, image/PDF structured output, mixed message parts, tool-assisted flows, named tool choice, and local video.

## Capsule contract

```text
experiments/llm_router/exp_####_<slug>/
├── src/
│   ├── experiment.py       # canonical executable entrypoint
│   └── ...                 # experiment-owned provider probes/helpers
├── report/
│   └── report.ipynb        # authoritative captured report
├── inputs/                 # causal media/schema inputs when needed
├── artifacts/              # retained supplementary evidence when needed
├── jupyter/kernels/<name>/kernel.json
├── pyproject.toml
├── uv.lock
└── .python-version
```

Capsules are deliberately temporally isolated. They do not import `llm_router`, project `src/`, tests, sibling experiments, or shared experiment helpers. Repeated helper code and small inputs are copied into the capsule rather than coupled across experiments. Every capsule has its own locked uv environment and exact Python version.

## Report format

A provider report has one overall Question and then a sequence of related provider capability checks. Each Evidence cell is executed during an explicit live capture and tagged `hide-input`, so MyST-NB keeps the captured output visible while implementation code stays behind the **Show experiment code** toggle. Rich Jupyter MIME output is retained directly in the notebook: images render inline, JSON/text stays beside the action that produced it, and causal PDF/video inputs remain linked from the report.

The notebook is the only report representation. There is no parallel Jupytext Markdown source and no committed copy under `docs/`. DocOps mounts the authoritative capsule notebook directly into the Sphinx source graph and renders stored outputs with MyST-NB execution disabled; documentation builds never contact providers.

## Capture and validation

Use `uv run ternforge-docops experiments capture ####` to capture one experiment from an isolated temporary copy. The capsule-owned Jupyter kernelspec defines its language/runtime command; for these Python capsules that command enters the locked uv `report` group and starts `ipykernel`. A successful capture stores a SHA-256 digest over causal capsule state. Python source and executable notebook cells are canonicalized structurally, so comment-only changes do not stale evidence, while runtime, dependency, input, kernelspec, or executable-code changes do.

Use `uv run ternforge-docops experiments validate` to validate all five capsules and reports. DocOps owns the retained-report contract: capsule-owned kernelspec, single EXP record, path/ID agreement, Question → `(Step → Evidence)+` → Conclusion ordering, sequential execution counts, captured outputs, `hide-input`, accidental errors, and freshness. `py-lib-policy` owns reusable repository/layout/isolation rules; uv owns capsule environments; MyST-NB renders stored evidence; Sphinx-Needs owns graph metadata and relations.

```{toctree}
:hidden:
:maxdepth: 1

_generated/exp_0001_aistudio/report
_generated/exp_0002_google_genai/report
_generated/exp_0003_gemini_webapi/report
_generated/exp_0004_openai_compatible/report
_generated/exp_0005_qwenchat/report
```
