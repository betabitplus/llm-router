"""Tests package routing.

Why:
    Documents how the test tree is organized.

What belongs here:
    `tests/support/` for reusable infrastructure.
    `tests/<project>/support/` for project-specific helpers.
    `tests/<project>/e2e/` for scenario scripts and replay artifacts.

What does not belong here:
    Do not mix project-specific helpers into `tests/support/`.
"""

from tests.support.setup import load_repo_env_file

load_repo_env_file()
