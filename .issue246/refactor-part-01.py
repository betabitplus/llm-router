
write(
    "src/llm_router/_api/types.py",
    facade(
        "Public vocabulary type facade for `llm_router`.\n\nCaller-facing names remain here while authoritative declarations live behind\nthe private implementation root.",
        api_types_names,
    ),
)
write(
    "src/llm_router/_api/contracts.py",
    facade(
        "Public schema and DTO facade for `llm_router`.\n\nThis module preserves the established import path while the private contract\npackage owns the authoritative declarations used by runtime code.",
        api_contract_names,
    ),
)
write(
    "src/llm_router/_api/errors.py",
    facade(
        "Public exception facade for `llm_router`.\n\nThe exported classes keep their public identity while private code imports the\nauthoritative declarations without depending on facade modules.",
        api_error_names,
    ),
)
write(
    "src/llm_router/_api/defaults.py",
    facade(
        "Compatibility facade for built-in `llm_router` defaults.\n\nDefaults are implementation inputs owned by private config assembly. Existing\nimports remain valid through this facade.",
        api_default_names,
    ),
)

# Public declaration package marker.
write(
    "src/llm_router/_internal/contracts/__init__.py",
    '"""Authoritative product contracts used by public facades and runtime code."""\n',
)

# Move loose private modules into a real private subpackage.
for old, new in (
    ("src/llm_router/_internal/errors.py", "src/llm_router/_internal/runtime/errors.py"),
    ("src/llm_router/_internal/ids.py", "src/llm_router/_internal/runtime/ids.py"),
    ("src/llm_router/_internal/output.py", "src/llm_router/_internal/runtime/output.py"),
):
    source = repo / old
    target = repo / new
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    source.unlink()

# All private implementation code imports authoritative private declarations.
replacements = {
    "from llm_router._api.contracts import": "from llm_router._internal.contracts.models import",
    "from llm_router._api.errors import": "from llm_router._internal.contracts.errors import",
    "from llm_router._api.types import": "from llm_router._internal.contracts.types import",
    "from llm_router._api.defaults import": "from llm_router._internal.config.defaults import",
    "from llm_router._internal.errors import": "from llm_router._internal.runtime.errors import",
    "from llm_router._internal.ids import": "from llm_router._internal.runtime.ids import",
    "from llm_router._internal.output import": "from llm_router._internal.runtime.output import",
}
for root_name in ("src/llm_router/_internal", "tests/llm_router"):
    root = repo / root_name
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = text.replace(
            "from llm_router._api import defaults as api_defaults",
            "from llm_router._internal.config import defaults as config_defaults",
        )
        text = text.replace("api_defaults.", "config_defaults.")
        path.write_text(text, encoding="utf-8")

# Remove module export lists from private implementation modules. The imported
# names remain available for normal explicit imports; only the supported root
# package declares `__all__`.
for relative in (
    "src/llm_router/_internal/capabilities/__init__.py",
    "src/llm_router/_internal/config/__init__.py",
    "src/llm_router/_internal/runtime/__init__.py",
    "src/llm_router/_internal/session/__init__.py",
    "src/llm_router/_internal/providers/qwenchat.py",
):
    path = repo / relative
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(r"\n__all__\s*=\s*\[(?:.|\n)*?\]\n", "\n", text, count=1)
    if count != 1:
        raise RuntimeError(f"{relative}: expected one __all__ list")
    path.write_text(text, encoding="utf-8")

# Rebuild the private root as the single facade bridge.
root_import_groups: list[tuple[str, list[str]]] = [
    ("llm_router._internal.config", [
        "BehaviorDefaults", "LLMRouterConfig", "ProviderCatalog", "ProviderSpec",
        "RetryPolicy", "RouterPolicyDefaults", "get_config", "install_config",
    ]),
    ("llm_router._internal.contracts.errors", api_error_names),
    ("llm_router._internal.contracts.models", api_contract_names),
    ("llm_router._internal.contracts.types", api_types_names),
    ("llm_router._internal.config.defaults", api_default_names),
    ("llm_router._internal.providers.registry", ["clear_adapter_caches"]),
    ("llm_router._internal.runtime", ["RouterRuntime"]),
    ("llm_router._internal.session", ["SessionStore"]),
]
root_lines = [
    '"""Private implementation root for `llm_router`.\n\nPublic facade modules import authoritative product declarations and private\nentrypoints only through this narrow package boundary.\n"""',
    "",
    "from __future__ import annotations",
    "",
]
for module, names in root_import_groups:
    root_lines.append(f"from {module} import (")
    root_lines.extend(f"    {name}," for name in names)
    root_lines.append(")")
root_lines.append("")
write("src/llm_router/_internal/__init__.py", "\n".join(root_lines))

# Standard baseline public-boundary test slice, adapted to the real config model.
write(
    "tests/llm_router/e2e/public_boundary/__init__.py",
    '"""Public-boundary end-to-end tests for `llm_router`."""\n',
)
