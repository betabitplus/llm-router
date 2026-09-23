"""pytest plugin: make pytest-gremlins run every mutant through real pytest.

pytest-gremlins 1.9 ships a "lightweight runner" that imports test modules and calls
test functions without pytest. It cannot provide fixtures, parametrization or
pytest-bdd scenarios, and it reports every test it cannot call as a caught mutant,
so on a real suite it fabricates kills. Disabling it makes the engine fall back to
its own bootstrap, which runs the selected tests with full pytest for each mutant.

When TERNFORGE_GREMLIN_SCOPE names a JSON file mapping source paths to line numbers,
only mutants on those lines are kept. The filter runs after the engine generated and
numbered every mutant of the target files, so a kept mutant has the same id, the same
instrumented source and the same selected tests as in an unfiltered run; the others
are simply never executed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest_gremlins.plugin as _gremlins_plugin  # ty: ignore[unresolved-import]

SCOPE_ENV = "TERNFORGE_GREMLIN_SCOPE"


def _no_lightweight_runner(*_args: object, **_kwargs: object) -> None:
    return None


def _scope_lines() -> set[tuple[str, int]] | None:
    scope_file = os.environ.get(SCOPE_ENV)
    if not scope_file:
        return None
    mapping = json.loads(Path(scope_file).read_text())
    return {
        (str(Path(path).resolve()), int(line))
        for path, lines in mapping.items()
        for line in lines
    }


_generate_all_gremlins = _gremlins_plugin._generate_gremlins


def _generate_gremlins_in_scope(gremlin_session, source_files, rootdir) -> None:  # noqa: ANN001
    _generate_all_gremlins(gremlin_session, source_files, rootdir)
    scope = _scope_lines()
    if scope is None:
        return
    gremlin_session.gremlins = [
        gremlin
        for gremlin in gremlin_session.gremlins
        if (str(Path(gremlin.file_path).resolve()), int(gremlin.line_number)) in scope
    ]


_gremlins_plugin.build_lightweight_command = _no_lightweight_runner
_gremlins_plugin._generate_gremlins = _generate_gremlins_in_scope
