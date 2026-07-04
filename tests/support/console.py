"""Reusable rich console helpers for manual test/demo output.

Why:
    Keeps demo-only terminal rendering in the shared support layer instead of a
    top-level utility module.

When to use:
    Import `console` from here when a manual test/demo entry point needs
    consistent rich output.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from io import StringIO
from pathlib import Path
from typing import Any

from IPython import get_ipython
from IPython.display import HTML, Image, display
from rich.console import Console

from tests.support._console_appearance import (
    DEFAULT_DEMO_CONSOLE_APPEARANCE,
    DemoConsoleAppearance,
)


class DemoConsole(Console):
    """Rich console with narrative helpers for manual demo runs."""

    # =================================================================================
    # Public API
    # =================================================================================

    def __init__(
        self,
        *args: Any,
        appearance: DemoConsoleAppearance = DEFAULT_DEMO_CONSOLE_APPEARANCE,
        **kwargs: Any,
    ) -> None:
        """Store appearance settings separately from rendering behavior."""
        self._appearance = appearance
        kwargs.setdefault("theme", appearance.theme)
        super().__init__(*args, **kwargs)

    def print_json(self, value: object, **kwargs: Any) -> None:
        """Print JSON with stable indentation and no Rich-inserted hard wraps."""
        json_text = self._normalize_json_text(value)
        if json_text is None:
            msg = "print_json() expects a dict, list, or JSON string."
            raise TypeError(msg)

        if self._in_notebook_output():
            self._display_via_rich_html(
                lambda render_console: render_console.print(
                    json_text,
                    soft_wrap=True,
                    markup=False,
                    highlight=False,
                )
            )
            return

        json_kwargs = dict(kwargs)
        json_kwargs.setdefault("soft_wrap", True)
        json_kwargs["markup"] = False
        json_kwargs["highlight"] = False
        super().print(json_text, **json_kwargs)

    def print(self, *objects: Any, **kwargs: Any) -> None:
        """Auto-render dict/list or JSON-string payloads as stable JSON text."""
        if len(objects) == 1:
            json_text = self._normalize_json_text(objects[0])
            if json_text is not None:
                self.print_json(json_text, **kwargs)
                return
        if self._in_notebook_output():
            notebook_kwargs = dict(kwargs)
            notebook_kwargs.pop("file", None)
            self._display_via_rich_html(
                lambda render_console: render_console.print(
                    *objects,
                    **notebook_kwargs,
                )
            )
            return
        super().print(*objects, **kwargs)

    def rule(
        self,
        title: str = "",
        *,
        characters: str = "─",
        style: str = "rule.line",
        align: str = "center",
    ) -> None:
        """Render rules through Rich HTML in notebooks to preserve styling and wrap."""
        if self._in_notebook_output():
            self._display_via_rich_html(
                lambda render_console: render_console.rule(
                    title,
                    characters=characters,
                    style=style,
                    align=align,
                )
            )
            return
        super().rule(
            title,
            characters=characters,
            style=style,
            align=align,
        )

    def demo_intro(self, doc: str | None) -> None:
        """Print the why and success criteria for a manual demo run."""
        if not doc:
            return

        why_lines = self._split_doc_lines(self._extract_doc_section(doc, "Why"))
        check_lines = self._split_doc_lines(self._extract_doc_section(doc, "Checks"))

        if why_lines:
            self.rule("[header]What This Demo Is Proving[/]")
            for line in why_lines:
                self.print(f"[subheader]-[/] {line}")

        if check_lines:
            self.rule("[header]What Success Should Look Like[/]")
            for line in check_lines:
                self.print(f"[subheader]-[/] {line}")

    def demo_step(
        self,
        title: str,
        summary: str,
        *,
        details: Sequence[str] | None = None,
    ) -> None:
        """Print one readable narrative step."""
        self.rule(f"[header]{title}[/]")
        self.print(summary)
        if details:
            for line in details:
                self.print(f"[info]- {line}[/]")

    def demo_outcome(
        self,
        summary: str,
        *,
        details: Sequence[str] | None = None,
    ) -> None:
        """Print the final outcome in human-readable form."""
        self.rule("[header]Why This Counts As Success[/]")
        self.print(f"[success]{summary}[/]")
        if details:
            for line in details:
                self.print(f"[info]- {line}[/]")

    def demo_skip(self, reason: str) -> None:
        """Print a clean skip outcome for manual demo runs."""
        self.rule("[header]Demo Skipped[/]")
        self.print(f"[warning]{reason}[/]")

    def display_image_if_available(self, image: object) -> None:
        """Display an image inline in notebook-like environments when possible."""
        if not isinstance(image, Path) or not self._in_notebook_output():
            self.print(f"[info]Image preview available: {image}[/]")
            return

        display(Image(filename=str(image)))

    # =================================================================================
    # Rendering Helpers
    # =================================================================================

    def _in_notebook_output(self) -> bool:
        """Return whether output is going to a notebook-like IPython frontend."""
        shell = get_ipython()
        return bool(shell and shell.__class__.__name__ != "TerminalInteractiveShell")

    def _display_via_rich_html(
        self,
        render_fn: Any,
    ) -> None:
        """Display Rich-rendered HTML with wrap-friendly notebook CSS."""
        buffer = StringIO()
        render_console = Console(
            file=buffer,
            record=True,
            force_terminal=False,
            force_jupyter=False,
            highlight=False,
            theme=self._appearance.theme,
            width=self.width,
        )
        render_fn(render_console)
        html = self._appearance.apply_notebook_html(
            render_console.export_html(inline_styles=True)
        )
        display(HTML(html))

    def _normalize_json_text(self, value: object) -> str | None:
        """Return pretty JSON text for dict/list or JSON string input."""
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate or candidate[0] not in {"{", "["}:
                return None
            try:
                parsed = json.loads(candidate)
            except ValueError:
                return None
            if not isinstance(parsed, dict | list):
                return None
            return json.dumps(parsed, indent=2, sort_keys=True, ensure_ascii=False)

        if isinstance(value, dict | list):
            return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)

        return None

    # =================================================================================
    # Docstring Utilities
    # =================================================================================

    def _extract_doc_section(self, doc: str, heading: str) -> str:
        """Extract one standard section from a structured module docstring."""
        pattern = rf"^{heading}:\n(?P<body>(?:^[ \t]+.*\n?)*)"
        match = re.search(pattern, doc, flags=re.MULTILINE)
        if not match:
            return ""
        return match.group("body").strip()

    def _split_doc_lines(self, block: str) -> list[str]:
        """Normalize an indented docstring block into readable lines."""
        if not block:
            return []
        return [line.strip() for line in block.splitlines() if line.strip()]


console = DemoConsole(highlight=True)
