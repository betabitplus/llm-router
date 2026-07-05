# %%
"""QwenChat workbench structured-output runner helpers.

Why:
    Keeps the local JSON validation and repair loop separate from the lower-
    level upload and completion helpers so those modules stay focused on one
    transport concern each.

When to use:
    Import from QwenChat workbench scripts that need prompt-enforced
    structured output with local validation and repair.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

import httpx
from pydantic import BaseModel

from workbench.llm_router.qwenchat._chat_completions import (
    QwenCompletionResponse,
    QwenUsageSummary,
    build_payload,
    post_completion_async,
    post_completion_sync,
    response_text,
    usage_snapshot,
)
from workbench.llm_router.qwenchat._structured_output import (
    build_json_instruction,
    validate_json_text,
)
from workbench.llm_router.qwenchat._uploads import (
    QwenMessageItem,
    QwenUserContent,
    build_user_content_async,
    build_user_content_sync,
)

# ======================================================================================
# Structured Run Configuration
# ======================================================================================


@dataclass(frozen=True, slots=True)
class StructuredRunConfig:
    """Inputs for one local structured-output run."""

    model: str
    base_items: list[QwenMessageItem]
    schema_model: type[BaseModel]
    temperature: float | None
    seed: int | None
    max_attempts: int = 3


class StructuredRunResult(TypedDict):
    """JSON-ready evidence returned by the structured-output runner."""

    attempts: int
    parsed: dict[str, Any]
    text: str
    usage: QwenUsageSummary | None


# ======================================================================================
# Repair Prompt Helpers
# ======================================================================================


def _repair_instruction(*, last_text: str, last_error: Exception | None) -> str:
    """Build the repair prompt for one failed structured-output attempt."""
    return (
        "The previous response did not match the required schema.\n\n"
        "Original request is above.\n\n"
        f"Previous response:\n{last_text}\n\n"
        f"Validation error:\n{last_error}\n\n"
        "Return ONLY corrected JSON."
    )


def _attempt_items(
    *,
    instruction: str,
    config: StructuredRunConfig,
    attempt: int,
    last_text: str,
    last_error: Exception | None,
) -> list[QwenMessageItem]:
    """Build the workbench items for one structured-output attempt."""
    items: list[QwenMessageItem] = [instruction, *config.base_items]
    if attempt > 1:
        items.append(_repair_instruction(last_text=last_text, last_error=last_error))
    return items


def _structured_result(
    *,
    attempt: int,
    parsed: BaseModel,
    text: str,
    response: QwenCompletionResponse,
) -> StructuredRunResult:
    """Build the stable JSON-ready evidence payload for one successful run."""
    return {
        "attempts": attempt,
        "parsed": parsed.model_dump(mode="json"),
        "text": text,
        "usage": usage_snapshot(response),
    }


# ======================================================================================
# Sync Runner
# ======================================================================================


def run_structured_sync(
    *,
    client: httpx.Client,
    config: StructuredRunConfig,
    initial_user_content: QwenUserContent | None = None,
) -> StructuredRunResult:
    """Run one sync structured-output loop with local validation and repair."""
    instruction = build_json_instruction(config.schema_model)
    last_text = ""
    last_error: Exception | None = None

    for attempt in range(1, config.max_attempts + 1):
        # 1. Reuse the initial uploaded content when provided, otherwise build a
        # fresh request that includes the JSON instruction and optional repair.
        if attempt == 1 and initial_user_content is not None:
            user_content = initial_user_content
        else:
            user_content = build_user_content_sync(
                client=client,
                items=_attempt_items(
                    instruction=instruction,
                    config=config,
                    attempt=attempt,
                    last_text=last_text,
                    last_error=last_error,
                ),
            )

        response = post_completion_sync(
            client=client,
            payload=build_payload(
                model=config.model,
                user_content=user_content,
                temperature=config.temperature,
                seed=config.seed,
            ),
        )
        text = response_text(response)
        try:
            parsed = validate_json_text(text=text, schema=config.schema_model)
        except Exception as exc:
            # Keep the failed text and validation error so the next attempt can
            # explicitly repair the previous response.
            last_text = text
            last_error = exc
            continue
        return _structured_result(
            attempt=attempt,
            parsed=parsed,
            text=text,
            response=response,
        )

    msg = f"Structured output validation failed after {config.max_attempts} attempts."
    raise RuntimeError(msg) from last_error


# ======================================================================================
# Async Runner
# ======================================================================================


async def run_structured_async(
    *,
    client: httpx.AsyncClient,
    config: StructuredRunConfig,
    initial_user_content: QwenUserContent | None = None,
) -> StructuredRunResult:
    """Run one async structured-output loop with local validation and repair."""
    instruction = build_json_instruction(config.schema_model)
    last_text = ""
    last_error: Exception | None = None

    for attempt in range(1, config.max_attempts + 1):
        # 1. Reuse the initial uploaded content when provided, otherwise build a
        # fresh request that includes the JSON instruction and optional repair.
        if attempt == 1 and initial_user_content is not None:
            user_content = initial_user_content
        else:
            user_content = await build_user_content_async(
                client=client,
                items=_attempt_items(
                    instruction=instruction,
                    config=config,
                    attempt=attempt,
                    last_text=last_text,
                    last_error=last_error,
                ),
            )

        response = await post_completion_async(
            client=client,
            payload=build_payload(
                model=config.model,
                user_content=user_content,
                temperature=config.temperature,
                seed=config.seed,
            ),
        )
        text = response_text(response)
        try:
            parsed = validate_json_text(text=text, schema=config.schema_model)
        except Exception as exc:
            # Keep the failed text and validation error so the next attempt can
            # explicitly repair the previous response.
            last_text = text
            last_error = exc
            continue
        return _structured_result(
            attempt=attempt,
            parsed=parsed,
            text=text,
            response=response,
        )

    msg = f"Structured output validation failed after {config.max_attempts} attempts."
    raise RuntimeError(msg) from last_error
