#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import shutil
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
src = repo / "src/llm_router"
api = src / "_api"
internal = src / "_internal"
contracts = internal / "contracts"
contracts.mkdir(parents=True, exist_ok=True)


def read(relative: str) -> str:
    return (repo / relative).read_text(encoding="utf-8")


def write(relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replace_exact(text: str, old: str, new: str, *, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"{label}: expected text not found: {old!r}")
    return text.replace(old, new)


def public_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.append(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                names.append(node.target.id)
    return names


def facade(module_doc: str, names: list[str]) -> str:
    imports = "\n".join(f"    {name}," for name in names)
    return (
        f'"""{module_doc}"""\n\n'
        "from __future__ import annotations\n\n"
        "# pyright: reportUnusedImport=false\n"
        "from llm_router._internal import (  # noqa: F401\n"
        f"{imports}\n"
        ")\n"
    )


# Move authoritative public declarations behind the private implementation root.
types_source = read("src/llm_router/_api/types.py")
types_source = types_source.replace(
    '"""Public vocabulary types for `llm_router`.',
    '"""Authoritative vocabulary types for `llm_router`.',
    1,
)
write("src/llm_router/_internal/contracts/types.py", types_source)

contracts_source = read("src/llm_router/_api/contracts.py")
contracts_source = contracts_source.replace(
    '"""Public schemas and DTOs for `llm_router`.',
    '"""Authoritative schemas and DTOs for `llm_router`.',
    1,
)
contracts_source = replace_exact(
    contracts_source,
    "from llm_router._api.types import KeyId, Model, Provider",
    "from llm_router._internal.contracts.types import KeyId, Model, Provider",
    label="contracts types import",
)
write("src/llm_router/_internal/contracts/models.py", contracts_source)

errors_source = read("src/llm_router/_api/errors.py")
errors_source = errors_source.replace(
    '"""Public exceptions for `llm_router`.',
    '"""Authoritative public exceptions for `llm_router`.',
    1,
)
errors_source = replace_exact(
    errors_source,
    "from llm_router._api.types import Model, Provider",
    "from llm_router._internal.contracts.types import Model, Provider",
    label="errors types import",
)
write("src/llm_router/_internal/contracts/errors.py", errors_source)

api_types_names = public_names(api / "types.py")
api_contract_names = public_names(api / "contracts.py")
api_error_names = public_names(api / "errors.py")
api_default_names = public_names(api / "defaults.py")

# Product defaults are implementation input; the legacy facade remains import-compatible.
defaults_source = read("src/llm_router/_api/defaults.py")
defaults_source = defaults_source.replace(
    '"""Built-in defaults for `llm_router`.',
    '"""Authoritative built-in defaults for `llm_router`.',
    1,
)
defaults_source = defaults_source.replace(
    "from llm_router._api.contracts import ProviderLimits",
    "from llm_router._internal.contracts.models import ProviderLimits",
)
defaults_source = defaults_source.replace(
    "from llm_router._api.types import Model, Provider",
    "from llm_router._internal.contracts.types import Model, Provider",
)
write("src/llm_router/_internal/config/defaults.py", defaults_source)
