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
├── pyproject.toml
├── uv.lock
└── .python-version
```

Capsules are deliberately temporally isolated. They do not import `llm_router`, project `src/`, tests, sibling experiments, or shared experiment helpers. Repeated helper code and small inputs are copied into the capsule rather than coupled across experiments. Every capsule has its own locked uv environment and exact Python version.

## Report format

A provider report has one overall Question and then a sequence of related provider capability checks. Each Evidence cell is executed during an explicit live capture and tagged `hide-input`, so MyST-NB keeps the captured output visible while implementation code stays behind the **Show experiment code** toggle. Rich Jupyter MIME output is retained directly in the notebook: images render inline, JSON/text stays beside the action that produced it, and causal PDF/video inputs remain linked from the report.

The notebook is the only report representation. There is no parallel Jupytext Markdown source and no committed copy under `docs/`. Sphinx copies the authoritative capsule notebook into a gitignored build-time integration directory and renders it with `nb_execution_mode = "off"`; documentation builds never contact providers.

## Capture and validation

Use `scripts/capture_experiment.py` to capture one experiment from a temporary copy outside the monorepo. The temporary copy is executed with the capsule's own `uv.lock` and managed Python. A successful capture stores a SHA-256 capsule digest over `src/**`, `inputs/**`, `pyproject.toml`, `uv.lock`, `.python-version`, and executable notebook code cells. Changing causal code, input, or dependencies makes retained evidence stale, while prose-only notebook edits do not.

Use `scripts/check_experiment_reports.py` to validate all five capsules and reports. The narrow project validator checks capsule layout/isolation, the single EXP record, path/ID agreement, Question → `(Step → Evidence)+` → Conclusion ordering, sequential execution counts, captured outputs, `hide-input`, accidental errors, and the capsule digest. Standard tooling handles the rest: uv owns environments, nbformat validates notebooks, nbdime handles semantic notebook diff/merge, MyST-NB renders stored evidence, Sphinx-Needs owns graph metadata/relations, and existing repository checks cover formatting and secrets.

```{toctree}
:hidden:
:maxdepth: 1

_generated/exp_0001_aistudio/report
_generated/exp_0002_google_genai/report
_generated/exp_0003_gemini_webapi/report
_generated/exp_0004_openai_compatible/report
_generated/exp_0005_qwenchat/report
```
