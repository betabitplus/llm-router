"""Private appearance settings for manual demo console output.

Why:
    Keeps theme choices and notebook HTML styling separate from `DemoConsole`
    behavior.

When to use:
    Import from here when the shared demo console needs visual defaults or
    notebook-specific HTML post-processing.

How:
    Use `DEFAULT_DEMO_CONSOLE_APPEARANCE` as the single source of truth for Rich
    theme settings and notebook display styling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rich.theme import Theme

# ================================================================================
# HTML Style Helpers
# ================================================================================

_PRE_STYLE_PATTERN = re.compile(r'(<pre style=")([^"]*)(")')
_CODE_STYLE_PATTERN = re.compile(r'(<code style=")([^"]*)(")')


def _append_inline_styles(match: re.Match[str], extra_styles: str) -> str:
    """Append CSS declarations to one inline `style="..."` attribute."""
    styles = match.group(2).rstrip()
    if styles and not styles.endswith(";"):
        styles = f"{styles};"
    return f"{match.group(1)}{styles} {extra_styles}{match.group(3)}"


@dataclass(frozen=True, slots=True)
class DemoConsoleAppearance:
    """Visual defaults for manual demo console output."""

    theme: Theme
    notebook_pre_wrap_styles: str
    notebook_code_wrap_styles: str
    notebook_html_overrides: str

    def apply_notebook_html(self, html: str) -> str:
        """Apply wrap-friendly and theme-friendly styles to Rich HTML output."""
        styled_html = _CODE_STYLE_PATTERN.sub(
            lambda match: _append_inline_styles(match, self.notebook_code_wrap_styles),
            _PRE_STYLE_PATTERN.sub(
                lambda match: _append_inline_styles(
                    match,
                    self.notebook_pre_wrap_styles,
                ),
                html,
                count=1,
            ),
            count=1,
        )
        return styled_html.replace(
            "</style>",
            f"</style>{self.notebook_html_overrides}",
            1,
        )


# ================================================================================
# Default Appearance
# ================================================================================


DEFAULT_DEMO_CONSOLE_APPEARANCE = DemoConsoleAppearance(
    theme=Theme(
        {
            "header": "bold cyan",
            "subheader": "bold",
            "info": "dim",
            "success": "bold green",
            "error": "bold red",
            "warning": "yellow",
            "key": "cyan",
            "value": "white",
            "url": "blue underline",
            "progress": "magenta",
        }
    ),
    notebook_pre_wrap_styles=(
        "white-space: pre-wrap; "
        "overflow-wrap: anywhere; "
        "word-break: break-word; "
        "margin: 0;"
    ),
    notebook_code_wrap_styles=(
        "white-space: inherit; overflow-wrap: inherit; word-break: inherit;"
    ),
    notebook_html_overrides="""
<style>
html, body {
    background: transparent !important;
    color: inherit !important;
}
pre, code {
    background: transparent !important;
}
</style>
""",
)
