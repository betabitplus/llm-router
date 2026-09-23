"""pytest plugin: make pytest-gremlins run every mutant through real pytest.

pytest-gremlins 1.9 ships a "lightweight runner" that imports test modules and calls
test functions without pytest. It cannot provide fixtures, parametrization or
pytest-bdd scenarios, and it reports every test it cannot call as a caught mutant,
so on a real suite it fabricates kills. Disabling it makes the engine fall back to
its own bootstrap, which runs the selected tests with full pytest for each mutant.
"""

from __future__ import annotations

import pytest_gremlins.plugin as _gremlins_plugin  # ty: ignore[unresolved-import]


def _no_lightweight_runner(*_args: object, **_kwargs: object) -> None:
    return None


_gremlins_plugin.build_lightweight_command = _no_lightweight_runner
