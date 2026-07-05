# Scripts

Repo-local scripts live here only when the implementation is specific to this
repository. Shared development commands come from `py-lib-tooling` console
scripts.

## Shared Repo Config

`py_lib_tooling.get_project_tooling_config` is the single reader for repo-local tooling
metadata in `[tool.py_lib_starter]` in `pyproject.toml`.

- Use it when behavior depends on the distribution name, the primary package,
  the package list, or the env var prefix.
- Do not hardcode project package names in reusable checks, smokes, or shared
  test support; read them from `[tool.py_lib_starter]`.
- When the template is rendered or updated for another library, keep
  `[project].name` and `[tool.py_lib_starter]` in `pyproject.toml` accurate; the
  shared checks and smoke commands should then follow that config.
- `package_names` supports future multi-package repos; `primary_package`
  remains the default import/smoke target.
- Keep this helper out of runtime package code under `src/`; it is only for
  repository tooling and test support.

Example:

```python
from py_lib_tooling import get_project_tooling_config

project_config = get_project_tooling_config()
package_name = project_config.primary_package
package_names = project_config.package_names
```

## Local Scripts

- `env/`
  Local contributor environment setup and health checks. `project_config.sh`
  reads `[tool.py_lib_starter]` from `pyproject.toml`.

Use shared smoke commands directly:

```bash
uv run py-lib-smoke-installed-artifact
uv run py-lib-smoke-public-api
```

Check and apply starter template and shared package updates through the shared
commands:

```bash
uv run py-lib-template-check
uv run py-lib-template-update
```

Run cleanup, structural, and artifact checks directly when needed:

```bash
uv run py-lib-check-legacy-support-cleanup
uv run py-lib-check-project-docs-structure
uv run py-lib-smoke-built-artifacts
```

Use the running-loop diagnostic helper only for real workbench modules:

```bash
uv run py-lib-reproduce-running-loop workbench.llm_router.<module>
```
