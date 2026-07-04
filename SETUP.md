# Setup

Use this file to provision a local contributor environment. For day-to-day
workflow, tests, hooks, and release conventions, use
[CONTRIBUTING.md](CONTRIBUTING.md).

## Prerequisites

- Python 3.13+
- `uv` installed
- access to the repo secrets file at `$HOME/researcher-local/.env` or an
  override through `LLM_ROUTER_ENV_FILE`

## First-time setup

Run this from the repository root:

```bash
bash scripts/env/setup.sh
direnv allow
bash scripts/env/doctor.sh
```

`scripts/env/setup.sh` runs `uv sync --group dev` and installs all configured git
hook types. Run `direnv allow` after that so the tracked `.envrc` can activate
the freshly created `.venv`. `scripts/env/doctor.sh` then checks the usual
local failure points: required tools, `.venv`, `direnv`, shared env file,
hooks, and GitHub CLI auth.

## Local environment

### Base environment

The project uses [`uv`](https://docs.astral.sh/uv/) to manage environments and
lock files. After cloning the repo, install the base dependencies like so:

```bash
uv sync
```

### Development tooling

If you need the development tooling (linters, notebooks, etc.), include the
`dev` group when syncing:

```bash
uv sync --group dev
```

These commands ensure packages such as `jupyter` and `ipywidgets` are
available.

For a quick setup including dev dependencies and git hooks, run:

```bash
bash scripts/env/setup.sh
```

To run a script with the development stack without activating a shell, use:

```bash
uv run --group dev python path/to/script.py
```

### Lockfile updates

If you change dependencies in `pyproject.toml`, regenerate the lockfile with:

```bash
uv lock
```

### Git hooks

Install all hook types after setting up the dev environment:

```bash
uv run pre-commit install -t pre-commit -t pre-push -t commit-msg -t post-merge -t post-checkout -t post-rewrite
```

After checkout or merge, local hooks may run `uv sync --group dev --frozen`
automatically when `pyproject.toml` or `uv.lock` changed.

## Worktree environment

In each new worktree, run:

```bash
direnv allow
```

That is enough to let the tracked `.envrc` activate `.venv`, set `PYTHONPATH`,
and load the shared external env file. By default it reads
`$HOME/researcher-local/.env`, and `.envrc.local` can extend one worktree
without changing the tracked file.

Keep secrets outside the repo. Test fixture data and replay artifacts are
tracked in git and should remain in the repository.

If a command runs in a non-direnv-aware shell or automation context, run it
through `direnv exec .`, for example:

```bash
direnv exec . uv run pytest tests/llm_router -m hermetic -q
direnv exec . uv run python -m workbench.llm_router.qwenchat.text_generation_async
```

If local setup still feels suspicious after that, rerun:

```bash
bash scripts/env/doctor.sh
```

## Dev Container notes (recommended)

If you open this repo in VS Code with Dev Containers:

- Virtual environment: The container provisions a Linux-specific `.venv/`
  inside the workspace (backed by a volume) while your host keeps its own
  `.venv`.
- Dependencies: On first create, it runs `uv sync --group dev` inside that
  `.venv` so pytest/linters/notebook tooling are available in-container.
- Interpreter: VS Code points to `${workspaceFolder}/.venv/bin/python`, and
  new integrated terminals activate it automatically.
- If VS Code ever loses the interpreter, run `Python: Clear Workspace Interpreter Setting` and reselect `llm-router (.venv)`; the devcontainer
  hooks also trigger this on rebuild.

## Clean rebuild with uv

If your environment or lockfile gets out of sync, you can do a clean reset and
re-provision from scratch:

```bash
# Remove virtual environment and lockfile (if present)
rm -rf .venv
rm -f uv.lock

# Clear caches (optional but recommended)
uv cache clean
uv cache prune

# Recreate the lockfile and environment
uv lock
uv sync

# With dev tools
# uv sync --group dev
```

Tips:

- To force a full reinstall without deleting the venv: `uv sync --reinstall`.
- To see where the cache lives: `uv cache dir`.
- For one-off runs using dev group without activating: `uv run --group dev <cmd>`.
- If the repo environment is required too, prefer `direnv exec . uv run ...`.
