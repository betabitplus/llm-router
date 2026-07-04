#!/usr/bin/env bash
set -euo pipefail

echo "Setting up development environment..."

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

# Install dev dependencies (creates/updates .venv)
uv sync --group dev

# Install all pre-commit hook types
uv run pre-commit install -t pre-commit -t pre-push -t commit-msg -t post-merge -t post-checkout -t post-rewrite

echo "Setup complete! All pre-commit hooks installed."
