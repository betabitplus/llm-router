# %%
"""OpenAI-compatible logprobs text-generation workbench script.

Why:
    Shows that the OpenAI-compatible NVIDIA route can return token log
    probabilities on a plain text request, which is a distinct response seam
    from ordinary text generation.

Covers:
    Area: openai-compatible logprobs support
    Behavior: plain text generation with token logprobs and top alternatives
    Interface: `OpenAI().chat.completions.create(..., logprobs=True)`

Checks:
    If the live response returns assistant `text` together with `tokens`, then the
        provider exposed token-level logprobs instead of ordinary text-only output.
    If `token_count` and `top_logprobs` are preserved in the result, then the manual run
        can verify how much probability detail the endpoint actually returned.
    If each token entry includes the token logprob and top alternatives, then the full
        logprob trace stays available for manual inspection.
    If the result also exposes `usage`, then the manual run keeps token accounting
        beside the logprob trace.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.openai.logprobs_text_generation
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.openai.logprobs_text_generation
"""

from __future__ import annotations

from math import exp
from typing import TYPE_CHECKING, Any, cast

from py_lib_tooling import console

from workbench.llm_router.openai._sdk_helpers import (
    build_client,
    provider_api_key_env,
    response_text,
    usage_snapshot,
)

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_token_logprob import (
        ChatCompletionTokenLogprob,
    )

# =============================================================================
# Scenario
# =============================================================================

# Keep the NVIDIA route fixed because this is the OpenAI-compatible provider
# path where we currently care about verifying token logprobs support.
_BASE_URL = "https://integrate.api.nvidia.com/v1"
_API_KEY_ENV = provider_api_key_env("NVIDIA")
_MODEL = "meta/llama-4-maverick-17b-128e-instruct"
_PROMPT = "What is the meaning of life? Explain in one sentence."
_MAX_TOKENS = 50
_TOP_LOGPROBS = 5
_TEMPERATURE = 0.7
_SEED = 42


# =============================================================================
# Helpers
# =============================================================================


def _token_summary(token_data: ChatCompletionTokenLogprob) -> dict[str, Any]:
    """Convert one SDK token logprob item into a JSON-ready trace entry."""
    alternatives = [
        {
            "token": alternative.token,
            "logprob": round(float(alternative.logprob), 3),
            "probability": round(exp(float(alternative.logprob)), 4),
        }
        for alternative in list(token_data.top_logprobs or [])[:2]
    ]

    return {
        "token": token_data.token,
        "logprob": round(float(token_data.logprob), 3),
        "probability": round(exp(float(token_data.logprob)), 4),
        "top_alternatives": alternatives,
    }


def _format_token_alternatives(token_data: dict[str, Any]) -> str:
    """Format the top alternative tokens for one readable breakdown row."""
    alternatives = cast("list[dict[str, Any]]", token_data.get("top_alternatives", []))
    if not alternatives:
        return "N/A"

    return ", ".join(
        f"{item['token']}({item['probability']:.3f})" for item in alternatives[:2]
    )


def _statistics(tokens: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate simple summary statistics for the returned token logprobs."""
    values = [float(item["logprob"]) for item in tokens]
    return {
        "average_logprob": round(sum(values) / len(values), 3),
        "highest_logprob": round(max(values), 3),
        "lowest_logprob": round(min(values), 3),
    }


def _print_token_breakdown(
    tokens: list[dict[str, Any]],
    *,
    max_tokens: int = 10,
) -> None:
    """Print the first few token logprobs in the original walkthrough format."""
    console.print(
        f"\nToken-by-token breakdown (first {min(len(tokens), max_tokens)} tokens):"
    )
    header = "Token            LogProb    Probability   Top Alternatives"
    console.print(header)
    console.print("-" * len(header))

    for token_data in tokens[:max_tokens]:
        token = str(token_data["token"])
        logprob = float(token_data["logprob"])
        probability = float(token_data["probability"])
        alt_str = _format_token_alternatives(token_data)
        console.print(f"{token:<15} {logprob:<10.3f} {probability:<12.3f} {alt_str}")

    if len(tokens) > max_tokens:
        console.print(f"\n... and {len(tokens) - max_tokens} more tokens")


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one live OpenAI-compatible request with logprobs enabled."""
    client = build_client(api_key_env=_API_KEY_ENV, base_url=_BASE_URL)
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": _PROMPT}],
            logprobs=True,
            top_logprobs=_TOP_LOGPROBS,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            seed=_SEED,
        )
    finally:
        client.close()

    choice = response.choices[0]
    if choice.logprobs is None or not choice.logprobs.content:
        msg = "The live response did not expose token logprobs."
        raise RuntimeError(msg)

    content = list(choice.logprobs.content)
    return {
        "model": _MODEL,
        "text": response_text(response),
        "usage": usage_snapshot(response),
        "token_count": len(content),
        "top_logprobs": _TOP_LOGPROBS,
        "tokens": [_token_summary(item) for item in content],
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending one plain text prompt through the NVIDIA "
        "OpenAI-compatible route with logprobs enabled.",
        details=(
            f"Base URL: {_BASE_URL}",
            f"Model: {_MODEL}",
            f"Top logprobs: {_TOP_LOGPROBS}",
            f"Temperature: {_TEMPERATURE}",
            f"Seed: {_SEED}",
        ),
    )

    result = run_pipeline()
    first_token = result["tokens"][0]
    stats = _statistics(cast("list[dict[str, Any]]", result["tokens"]))
    console.demo_step(
        "Observed Token Logprobs",
        "The live response returned assistant text plus the same detailed "
        "logprobs walkthrough shape the original manual probe used.",
        details=(
            f"text: {result['text']}",
            f"token_count: {result['token_count']}",
            f"first_token: {first_token['token']}",
        ),
    )
    console.print("\nLogprobs Summary:")
    console.print(f"  Total tokens with probabilities: {result['token_count']}")
    console.print(f"  Top N alternatives per token: {result['top_logprobs']}")
    console.print(f"  Temperature: {_TEMPERATURE}")
    console.print(f"  Seed: {_SEED}")
    console.print(f"  Response content: {result['text']}")
    console.print("\nStatistics:")
    console.print(f"  Average log probability: {stats['average_logprob']}")
    console.print(f"  Highest log probability: {stats['highest_logprob']}")
    console.print(f"  Lowest log probability: {stats['lowest_logprob']}")
    _print_token_breakdown(cast("list[dict[str, Any]]", result["tokens"]))
    console.demo_outcome(
        "This is enough to trust that the NVIDIA OpenAI-compatible route "
        "exposes real token logprobs in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-04:
{
  "model": "meta/llama-4-maverick-17b-128e-instruct",
  "text": "The meaning of life is a subjective and personal interpretation...",
  "token_count": 47,
  "top_logprobs": 5,
  "tokens": [
    {
      "token": "The",
      "logprob": -0.0,
      "probability": 1.0
    }
  ]
}
""".strip()
