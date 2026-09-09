from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

from IPython.display import IFrame, Image, Markdown, Video, display

CASES = {
    "text_generation": {
        "module": "text_generation_async",
        "label": "Async text generation",
        "input": None,
    },
    "retry_text_generation": {
        "module": "retry_text_generation_async",
        "label": "Provider retry behavior",
        "input": None,
    },
    "models_list": {
        "module": "models_list",
        "label": "Live model catalog",
        "input": None,
    },
    "image_structured": {
        "module": "image_structured",
        "label": "Image input with structured output",
        "input": "test_image.png",
    },
    "pdf_structured": {
        "module": "pdf_structured",
        "label": "PDF input with structured output",
        "input": "variative.pdf",
    },
    "tool_choice_named": {
        "module": "tool_choice_named_structured",
        "label": "Named tool choice with structured output",
        "input": None,
    },
    "tool_loop": {
        "module": "tool_loop_structured_async",
        "label": "Multi-round tool loop with structured output",
        "input": None,
    },
    "schema_ref_resolution": {
        "module": "schema_ref_resolution",
        "label": "Nested schema reference normalization",
        "input": None,
    },
    "video_file": {
        "module": "video_file_structured",
        "label": "Local video input with structured output",
        "input": "jumper.mp4",
    },
    "video_url": {
        "module": "video_url_structured",
        "label": "Remote video URL with structured output",
        "input": None,
    },
}


def _validate_result(case: str, result: Any) -> None:
    if not isinstance(result, Mapping) or not result:
        raise AssertionError(f"{case}: expected a non-empty mapping result")
    for key in ("text", "parsed", "models", "usage", "final_result", "reply"):
        if key in result and result[key] in (None, "", [], {}):
            message = f"{case}: {key} is empty"
            raise AssertionError(message)


_INPUT_ATTRIBUTES = (
    ("_BASE_URL", "Endpoint"),
    ("_MODEL", "Model"),
    ("_SYSTEM_PROMPT", "System prompt"),
    ("_PROMPT", "Prompt"),
    ("_INITIAL_PROMPT", "Initial prompt"),
    ("_FOLLOW_UP_INSTRUCTION", "Follow-up prompt"),
    ("_FOLLOW_UP_PROMPT", "Follow-up prompt"),
    ("_VIDEO_URL", "Video URL"),
    ("_MAX_TOKENS", "Max tokens"),
    ("_TOP_LOGPROBS", "Top logprobs"),
    ("_MAX_ATTEMPTS", "Max attempts"),
    ("_TEMPERATURE", "Temperature"),
    ("_SEED", "Seed"),
)


def _case_module(case: str) -> Any:
    return importlib.import_module(CASES[case]["module"])


def _rendered_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _facts_markdown(title: str, facts: list[tuple[str, Any]]) -> str:
    lines = [f":::{{card}} {title}", ""]
    for label, value in facts:
        rendered = _rendered_value(value)
        if "\n" in rendered or len(rendered) > 120:
            lines.extend(
                (
                    f"**{label}**",
                    "",
                    "`````text",
                    rendered,
                    "`````",
                    "",
                )
            )
        else:
            lines.append(f"- **{label}:** {rendered}")
    lines.append(":::")
    return "\n".join(lines)


def _input_facts(case: str, module: Any) -> list[tuple[str, Any]]:
    facts: list[tuple[str, Any]] = []
    filename = CASES[case].get("input")
    if filename:
        facts.append(("Input file", filename))
    seen_labels = {label for label, _ in facts}
    for attribute, label in _INPUT_ATTRIBUTES:
        if label in seen_labels or not hasattr(module, attribute):
            continue
        value = getattr(module, attribute)
        if isinstance(value, (str, int, float, bool)):
            facts.append((label, value))
            seen_labels.add(label)
    if not facts:
        facts.append(
            (
                "Operation",
                "No content payload; this case exercises the provider operation directly.",
            )
        )
    return facts


def display_case_input(case: str) -> None:
    module = _case_module(case)
    display(Markdown(_facts_markdown("Input", _input_facts(case, module))))

    filename = CASES[case].get("input")
    if not filename:
        return
    path = Path(__file__).resolve().parent.parent / "inputs" / filename
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        display(Image(filename=str(path)))
        return

    relative_url = f"inputs/{quote(filename)}"
    if suffix == ".pdf":
        display(IFrame(relative_url, width="100%", height=640))
    elif suffix in {".mp4", ".webm", ".mov"}:
        display(
            Video(
                url=relative_url,
                width=900,
                html_attributes="controls preload='metadata'",
            )
        )
    else:
        display(Markdown(f"[Open {filename}]({relative_url})"))


def display_case_code(case: str) -> None:
    module = _case_module(case)
    source = inspect.getsource(module.run_pipeline).strip()
    comments: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped.startswith("# "):
            continue
        comment = stripped.removeprefix("# ").strip()
        if comment and comment not in comments:
            comments.append(comment)

    content: list[str] = []
    if comments:
        content.extend(("**Core flow**", ""))
        content.extend(f"- {comment}" for comment in comments[:6])
        content.append("")
    content.extend(
        (
            ":::{dropdown} Actual provider code",
            "This is the actual `run_pipeline()` executed for this capture, not notebook-only pseudocode.",
            "",
            "`````python",
            source,
            "`````",
            ":::",
        )
    )
    display(Markdown("\n".join(content)))


def _short_text(value: Any, *, limit: int = 260) -> str:
    text = str(value).strip()
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _summary_items(result: Mapping[str, Any]) -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []

    def add(label: str, value: Any) -> None:
        if value not in (None, "", [], {}):
            items.append((label, value))

    if "ready" in result:
        add("Ready", result["ready"])

    reply = result.get("normalized_reply") or result.get("reply") or result.get("text")
    if reply:
        add("Reply", _short_text(reply))

    if "model_count" in result:
        add("Models returned", result["model_count"])
        models = result.get("models")
        if isinstance(models, list) and models:
            first = models[0]
            if isinstance(first, Mapping):
                add("Example model", first.get("id") or first.get("name"))

    if "title_matches_expected" in result:
        add("Expected PDF title matched", result["title_matches_expected"])
        add("Observed title", result.get("observed_title"))

    parsed = result.get("parsed")
    structured = parsed if isinstance(parsed, Mapping) else result
    for key, label in (
        ("primary_subject", "Primary subject"),
        ("action", "Action"),
        ("location", "Location"),
        ("setting", "Setting"),
    ):
        if isinstance(structured, Mapping):
            add(label, structured.get(key))

    final_output = result.get("final_output")
    if isinstance(final_output, Mapping):
        add("Selected tool", final_output.get("tool_name"))
        add("Final result", final_output.get("final_result"))
        if final_output.get("steps"):
            add("Structured steps", final_output["steps"])

    trace = result.get("tool_trace")
    if isinstance(trace, list) and trace:
        compact_trace = []
        for step in trace:
            if not isinstance(step, Mapping):
                continue
            compact_trace.append(
                {
                    "tool": step.get("tool_name"),
                    "arguments": step.get("arguments"),
                    "result": step.get("result"),
                }
            )
        add("Tool trace", compact_trace)

    if "raw_has_ref" in result or "resolved_has_ref" in result:
        add(
            "Schema refs",
            {
                "raw_$defs": result.get("raw_has_defs"),
                "raw_$ref": result.get("raw_has_ref"),
                "resolved_$defs": result.get("resolved_has_defs"),
                "resolved_$ref": result.get("resolved_has_ref"),
            },
        )

    if "token_count" in result:
        add("Tokens with logprobs", result["token_count"])
        add("Top alternatives per token", result.get("top_logprobs"))

    if "part_types" in result:
        add("Message parts", result["part_types"])

    attempts = result.get("attempt_count") or result.get("attempts")
    if attempts is not None:
        add("Attempts", attempts)
    retry_events = result.get("retry_events")
    if isinstance(retry_events, list):
        add("Retries observed", len(retry_events))

    usage = result.get("usage") or result.get("final_usage")
    if isinstance(usage, Mapping):
        add("Total tokens", usage.get("total_tokens"))

    if not items:
        add("Captured fields", ", ".join(result))
    return items


async def run_case(case: str) -> dict[str, Any]:
    module = _case_module(case)
    result = module.run_pipeline()
    if inspect.isawaitable(result):
        result = await result
    _validate_result(case, result)
    return dict(result)


def display_result(result: Mapping[str, Any]) -> None:
    raw = json.dumps(result, indent=2, ensure_ascii=False, default=str).replace(
        "'", "\\u0027"
    )
    content = [
        _facts_markdown("Observed output", _summary_items(result)),
        "",
        "::::{card} Raw captured result",
        "",
        ":::{data-viewer}",
        raw,
        ":::",
        "::::",
    ]
    display(Markdown("\n".join(content)))


async def run_all() -> None:
    for case in CASES:
        print(f"\n=== {case} ===")
        display_case_input(case)
        display_case_code(case)
        display_result(await run_case(case))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", nargs="?", choices=[*CASES, "all"], default="all")
    args = parser.parse_args()
    if args.case == "all":
        asyncio.run(run_all())
    else:
        result = asyncio.run(run_case(args.case))
        display_result(result)


if __name__ == "__main__":
    main()
