#!/usr/bin/env bash
set -euo pipefail

pass_count=0
warn_count=0
fail_count=0

pass() {
  printf '[PASS] %s\n' "$1"
  pass_count=$((pass_count + 1))
}

warn() {
  printf '[WARN] %s\n' "$1"
  warn_count=$((warn_count + 1))
}

fail() {
  printf '[FAIL] %s\n' "$1"
  fail_count=$((fail_count + 1))
}

require_command() {
  local command_name="$1"
  local hint="$2"

  if command -v "$command_name" >/dev/null 2>&1; then
    pass "Found \`$command_name\`"
    return 0
  fi

  fail "Missing \`$command_name\`. $hint"
  return 1
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

printf 'LLMRouter contributor doctor\n'
printf 'Repo: %s\n\n' "$repo_root"

require_command "git" "Install Git and rerun this check."
require_command "uv" "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
require_command "direnv" "Install direnv and enable it in your shell."

if [ -x ".venv/bin/python" ]; then
  pass "Project virtualenv exists at \`.venv/\`"

  venv_python_version="$(
    .venv/bin/python - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:3])))
raise SystemExit(0 if sys.version_info >= (3, 13) else 1)
PY
  )" || {
    fail "Repo virtualenv must use Python 3.13+. Current \`.venv\` interpreter: ${venv_python_version:-unknown}"
    venv_python_version=""
  }

  if [ -n "$venv_python_version" ]; then
    pass "Repo virtualenv uses Python ${venv_python_version}"
  fi
else
  fail "Project virtualenv is missing. Run \`bash scripts/env/setup.sh\`."

  if command -v python3 >/dev/null 2>&1; then
    system_python_version="$(
      python3 - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:3])))
PY
    )"
    warn "System \`python3\` is ${system_python_version}. The repo still needs a local Python 3.13 environment."
  else
    fail "Missing \`python3\`. Install Python 3.13+ or let \`uv\` manage it during setup."
  fi
fi

env_file="${LLM_ROUTER_ENV_FILE:-$HOME/researcher-local/.env}"
if [ -f "$env_file" ]; then
  pass "Shared env file exists at \`$env_file\`"
else
  warn "Shared env file not found at \`$env_file\`. Hermetic tests can still work, but live provider runs will fail."
fi

direnv_probe_output=""
if direnv_probe_output="$(DIRENV_LOG_FORMAT='' direnv exec . python - <<'PY' 2>&1
from __future__ import annotations

import os
import sys

import llm_router

print(f"PYTHON={sys.executable}")
print(f"VIRTUAL_ENV={os.environ.get('VIRTUAL_ENV', '')}")
print(f"PYTHONPATH={os.environ.get('PYTHONPATH', '')}")
print(f"LLM_ROUTER_ENV_FILE={os.environ.get('LLM_ROUTER_ENV_FILE', '')}")
print(f"VERSION={llm_router.__version__}")
PY
)"; then
  direnv_python="$(printf '%s\n' "$direnv_probe_output" | sed -n 's/^PYTHON=//p')"
  direnv_venv="$(printf '%s\n' "$direnv_probe_output" | sed -n 's/^VIRTUAL_ENV=//p')"
  direnv_pythonpath="$(printf '%s\n' "$direnv_probe_output" | sed -n 's/^PYTHONPATH=//p')"
  direnv_env_file="$(printf '%s\n' "$direnv_probe_output" | sed -n 's/^LLM_ROUTER_ENV_FILE=//p')"

  pass "Repo environment loads through \`direnv exec .\`"

  case "$direnv_venv" in
    "$repo_root/.venv")
      pass "direnv activates the repo virtualenv"
      ;;
    *)
      fail "direnv did not activate the repo virtualenv. Expected \`$repo_root/.venv\`, got \`${direnv_venv:-empty}\`."
      ;;
  esac

  has_repo_src=0
  has_repo_root=0

  case ":$direnv_pythonpath:" in
    *":$repo_root/src:"*)
      has_repo_src=1
      ;;
  esac

  case ":$direnv_pythonpath:" in
    *":$repo_root:"*)
      has_repo_root=1
      ;;
  esac

  if [ "$has_repo_src" -eq 1 ] && [ "$has_repo_root" -eq 1 ]; then
    pass "direnv exports the repo PYTHONPATH"
  else
    fail "direnv PYTHONPATH is missing repo paths."
  fi

  if [ -n "$direnv_env_file" ]; then
    pass "direnv exports \`LLM_ROUTER_ENV_FILE\`"
  else
    warn "direnv did not export \`LLM_ROUTER_ENV_FILE\`."
  fi

  if [ -n "${VIRTUAL_ENV:-}" ] && [ "${VIRTUAL_ENV:-}" = "$repo_root/.venv" ]; then
    pass "Current shell already looks repo-ready"
  else
    warn "Current shell does not look direnv-loaded. Interactive runs may need \`direnv allow\` and a fresh shell."
  fi

  if [ -n "$direnv_python" ]; then
    pass "Repo Python resolves to \`$direnv_python\`"
  fi
else
  fail "Repo environment failed to load through direnv. Run \`bash scripts/env/setup.sh\`, then \`direnv allow\`. Details: $direnv_probe_output"
fi

pre_commit_hook="$(git rev-parse --git-path hooks/pre-commit)"
pre_push_hook="$(git rev-parse --git-path hooks/pre-push)"

if [ -f "$pre_commit_hook" ] && [ -f "$pre_push_hook" ]; then
  pass "Git hooks are installed"
else
  warn "Git hooks are missing. Run \`bash scripts/env/setup.sh\` to install them."
fi

if command -v gh >/dev/null 2>&1; then
  if gh auth status -h github.com >/dev/null 2>&1; then
    pass "GitHub CLI is installed and authenticated"
  else
    warn "GitHub CLI is installed but not authenticated. Run \`gh auth login\`."
  fi
else
  warn "GitHub CLI is not installed. Recommended for PR and CI workflows."
fi

printf '\nSummary: %s passed, %s warnings, %s failed\n' \
  "$pass_count" "$warn_count" "$fail_count"

if [ "$fail_count" -gt 0 ]; then
  printf '%s\n' "Suggested fixes: bash scripts/env/setup.sh, direnv allow, and optionally gh auth login."
  exit 1
fi
