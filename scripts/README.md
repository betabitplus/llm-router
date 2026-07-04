# Scripts

Purpose-grouped repository scripts live here.

## Shared repo config

`_shared/project_config.py` is the single reader for repo-local tooling
metadata in `[tool.py_lib_starter]` in `pyproject.toml`.

- Use it from repository scripts and `tests/support/` when behavior depends on
  the distribution name, the primary package, the package list, or repo-scoped
  env vars.
- Do not hardcode project package names in reusable checks, smokes, or
  shared test support; read them from `[tool.py_lib_starter]`.
- When this repo shape is copied into another library, update `[project].name`
  and `[tool.py_lib_starter]` in `pyproject.toml`; the shared checks and smoke
  scripts should then follow that config.
- `package_names` supports future multi-package repos; `primary_package`
  remains the default import/smoke target.
- Keep this helper out of runtime package code under `src/`; it is only for
  repository tooling and test support.

Example:

```python
from scripts._shared.project_config import get_project_tooling_config

project_config = get_project_tooling_config()
package_name = project_config.primary_package
package_names = project_config.package_names
env_file_var = project_config.env_file_var
```

- `checks/`
  Lightweight repository boundary and structure checks. Some checks read
  `[tool.py_lib_starter]` so CI and hooks can target the configured package
  without hiding complex behavior behind generated config.
- `_shared/`
  Shared helpers used by repository-local scripts and test support, including
  `pyproject.toml`-backed tooling config.
- `env/`
  Local contributor environment setup and health checks.
- `smoke/`
  Small package and public-surface smoke checks.
  This folder is the canonical list of smoke scripts.
- `runtime/`
  Runtime-context helpers such as already-running-loop reproduction.
