# Contributing

Start with [SETUP.md](SETUP.md) to provision the local environment.
If your local environment feels off, run `bash scripts/env/doctor.sh` before
debugging deeper.

Use [docs/llm_router/README.md](docs/llm_router/README.md) for package docs,
[tests/README.md](tests/README.md) for test-tree layout, and
[docs/llm_router/verification/workbench.md](docs/llm_router/verification/workbench.md)
for the live probe matrix.
Use [.github/MAINTAINER_SETUP.md](.github/MAINTAINER_SETUP.md) for one-time GitHub and
repository administration setup.
Repository-wide package and reusable-zone checks read their repo metadata from
`[tool.py_lib_starter]` in `pyproject.toml`. When repo-local scripts or shared
test support need package names or env-var prefixes, use
`scripts._shared.project_config` instead of hardcoding package names.

## Branch and target flow

- Normal development lands on `dev`.
- Direct pushes to `main` are blocked by a pre-push hook.
- Branch names must match the enforced local convention:
  `feature/`, `fix/`, `chore/`, `hotfix/`, `release/`, `codex/`, or the
  long-lived `dev` / `main` branches.

## Worktree flow

### Merge back into `dev`

When finished: commit on a `feature/...` branch, ensure hooks pass (`uv run pre-commit run --all-files` + `uv run pre-commit run --all-files --hook-stage pre-push`), then merge **locally** into `dev` and push `dev`:

```bash
git checkout dev
git pull --ff-only
git merge --ff-only feature/your-branch
git push origin dev  # or your preferred remote (see `git remote -v`)
```

### Cleanup after merge/push

```bash
# From the main/original checkout
git worktree remove /path/to/worktree
git branch -d feature/your-branch
git worktree prune
```

## Local validation

### Commit-time hooks

Run the same commit-time hook stage that local commits use:

```bash
uv run pre-commit run --all-files
```

This stage covers formatting, fast linting, branch policy, secret scanning,
docs formatting, file hygiene, and other repository checks.

### Push-time hooks

Run the heavier push-time hook stage before pushing:

```bash
uv run pre-commit run --all-files --hook-stage pre-push
```

This stage adds strict typing, architecture checks, security and dependency
scanning, package-manifest checks, link checks, and the default automated test
path.

## Running tests

### Full suite

Run the package test suite:

```bash
uv run pytest tests/llm_router
```

### Hermetic tests

Run only hermetic tests:

- Some hermetic scenarios replay committed VCR cassettes.
- Others are fully local and use scripted servers or worker helpers instead of
  network replay.

```bash
uv run pytest tests/llm_router -m hermetic
```

### Update VCR cassettes (if needed)

```bash
uv run pytest tests/llm_router -m hermetic --record-mode=all
```

### Update snapshots

```bash
uv run pytest tests/llm_router --snapshot-update
```

### Running tests directly

If you run test files directly (e.g.,
`python tests/<package>/e2e/test_server_errors.py`), you may encounter import
errors for `tests.*` modules. To fix this, ensure the repo root is on
`PYTHONPATH`:

- For shell/direnv: the tracked `.envrc` configures `PYTHONPATH`
  automatically.
- For VS Code/Jupyter in the devcontainer: the container reads
  `$HOME/researcher-local/.env` directly, and notebook kernels inherit that
  environment.
- For VS Code/Jupyter on the host: start VS Code or Jupyter from a shell where
  `direnv allow` has already loaded the repo environment, or use a
  direnv-aware editor workflow.

Reload VS Code and restart kernels after changes. For pytest, this is not
needed.

## Live workbench scripts

`workbench/` is manual-only. It is not part of the default commit or CI path.

Run one script directly:

```bash
direnv exec . uv run python -m workbench.llm_router.qwenchat.text_generation_async
```

Reproduce the same script inside an already-running event loop:

```bash
direnv exec . uv run python scripts/runtime/reproduce_running_loop.py \
    workbench.llm_router.qwenchat.text_generation_async
```

## Commit and release conventions

This project uses [Commitizen](https://commitizen-tools.github.io/commitizen/)
for version management and changelog generation.

### Commit messages

**Commit messages** must follow
[Conventional Commits](https://www.conventionalcommits.org/) format (enforced
by pre-commit hook):

```text
feat: add new feature
fix: resolve bug
docs: update documentation
refactor: restructure code
```

### Release flow (recommended)

```bash
# 1) Merge conventional-commit PRs into main
# 2) GitHub Actions "Release" workflow bumps version/changelog automatically
# 3) Workflow pushes bump commit+tag and creates GitHub Release
```

The workflow runs `cz bump --changelog --yes` on `main`, pushes the bump
commit/tag, creates a GitHub Release, and syncs `main` back to `dev`.

CI runs on pushes and pull requests targeting `dev` and `main`. It reruns both
commit-time and push-time hooks, builds package artifacts, and then runs the
hermetic e2e suite in slices.

### GitHub prerequisite for protected `main`

Configure `PAT_TOKEN` secret with a token/user that is allowed by your
repository rules to push release commits to `main`.
