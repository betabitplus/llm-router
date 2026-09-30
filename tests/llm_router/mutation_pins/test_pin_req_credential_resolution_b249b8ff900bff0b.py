# mutation-pin: REQ_CREDENTIAL_RESOLUTION b249b8ff900bff0b
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_rotation_covers_custom_mapped_and_numeric_ids_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = Provider.NVIDIA
    prefix = f"{provider.name}_API_KEY_"
    for number in range(100):
        monkeypatch.delenv(f"{prefix}{number}", raising=False)

    # Key id 3 is read from a custom name that shares the provider prefix but
    # has a non-numeric suffix; key id 2 follows the numeric convention.
    custom_name = f"{prefix}PRIMARY"
    numeric_name = f"{prefix}2"
    primary_value = "nvidia-primary-credential"
    numeric_value = "nvidia-numbered-credential"
    monkeypatch.setenv(custom_name, primary_value)
    monkeypatch.setenv(numeric_name, numeric_value)
    # A variable named only with digits is not a provider credential.
    monkeypatch.setenv("4096", "unrelated-digits-only-value")

    base = get_config()
    spec = replace(base.catalog.providers[provider], api_key_env_vars={3: custom_name})
    catalog = replace(
        base.catalog,
        providers={**base.catalog.providers, provider: spec},
    )
    install_config(replace(base, catalog=catalog))
    unspaced_limits = replace(
        base.provider_limits,
        rps=0.0,
        rpm=0.0,
        cooldown_after_failures=0,
    )

    path = openai_chat_path()
    replies = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=openai_success_response(text=f"rotation reply {index}"),
        )
        for index in range(3)
    ]
    with (
        ScriptedHTTPServer(port=0, routes={("POST", path): replies}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router = LLMRouter(
            RouterProfile(model=Model.LLAMA_8B, provider=provider),
            key_id="auto",
            default_limits=unspaced_limits,
        )
        responses = [router.query(f"rotation probe {index}") for index in range(3)]
        recorded = server.recorded_requests("POST", path)

    assert [response.output_text for response in responses] == [
        "rotation reply 0",
        "rotation reply 1",
        "rotation reply 2",
    ]
    assert [
        [attempt.key_id for attempt in response.routing_trace] for response in responses
    ] == [[2], [3], [2]]
    assert [request.headers["Authorization"] for request in recorded] == [
        f"Bearer {numeric_value}",
        f"Bearer {primary_value}",
        f"Bearer {numeric_value}",
    ]
