from __future__ import annotations

from types import SimpleNamespace

import pytest
from py_lib_testkit import evidence

from llm_router import Model, Provider, ProviderError
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.google_genai import GoogleGenAIAdapter
from tests.llm_router.support.fault_observation import retain_local_fault_injection


class FakeAPIError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeModels:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, object]] = []

    def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: object,
    ) -> object:
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeAsyncModels(FakeModels):
    async def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: object,
    ) -> object:
        return super().generate_content(model=model, contents=contents, config=config)


class FakeClient:
    def __init__(self, outcomes: list[object]) -> None:
        evidence.observation(
            "Google GenAI SDK substitute",
            kind="external-substitute",
            payload={
                "producer": "GoogleGenAIFakeClient",
                "producer_id": "PRODUCER_GOOGLE_GENAI_FAKE_SDK",
                "boundary": "provider-sdk",
                "mode": "in-process-fake-sdk",
                "transport": "SDK surface",
                "target": "Google GenAI SDK/provider",
            },
        )
        self.models = FakeModels(outcomes)
        self.aio = SimpleNamespace(models=FakeAsyncModels(list(outcomes)))


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=2,
            candidates_token_count=3,
            total_token_count=5,
        ),
    )


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH,
        provider_model="gemini-3.6-flash",
        credential=ProviderCredential(
            key_id=1,
            env_var="GOOGLE_API_KEY_1",
            value="secret",
        ),
        messages=[normalize_content("hello")],
        temperature=0.0,
        seed=7,
    )


pytestmark = [
    pytest.mark.verifies("TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY[revision==1]"),
    pytest.mark.verification_kind("integration"),
]


@pytest.mark.coverage_path("sync-success")
def test_sync_google_adapter_uses_sdk_boundary_and_normalizes_result() -> None:
    client = FakeClient([_response("ok")])

    result = GoogleGenAIAdapter(client=client).execute(_request())

    assert result.output_text == "ok"
    assert result.usage.total_tokens == 5
    assert client.models.calls[0]["model"] == "gemini-3.6-flash"
    config = client.models.calls[0]["config"]
    assert config.temperature == 0.0
    assert config.seed == 7


@pytest.mark.asyncio
@pytest.mark.coverage_path("async-success")
async def test_async_google_adapter_uses_sdk_async_boundary() -> None:
    client = FakeClient([_response("async ok")])

    result = await GoogleGenAIAdapter(client=client).aexecute(_request())

    assert result.output_text == "async ok"
    assert client.aio.models.calls[0]["model"] == "gemini-3.6-flash"


@pytest.mark.coverage_path("retryable-sdk-status")
@pytest.mark.fault_item("TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY", "interface.error-status")
def test_google_sdk_retryable_status_is_translated_to_provider_error() -> None:
    client = FakeClient([FakeAPIError(503, "provider said no")])
    retain_local_fault_injection(
        contract_id="TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY",
        fault_class="interface.error-status",
        mechanism="fake Google GenAI client raises an API error 503",
        details={"status_code": 503},
    )

    with pytest.raises(ProviderError) as exc_info:
        GoogleGenAIAdapter(client=client).execute(_request())

    assert exc_info.value.cause.status_code == 503
    assert exc_info.value.cause.retryable is True
    assert exc_info.value.cause.retry_reason == "retryable_status"


@pytest.mark.verifies("REQ_PROVIDER_ADAPTER_INTEROPERABILITY[revision==2]")
@pytest.mark.fault_item(
    "REQ_PROVIDER_ADAPTER_INTEROPERABILITY", "interface.payload-schema"
)
def test_google_answer_without_candidate_content_is_a_provider_error() -> None:
    empty_candidate = SimpleNamespace(content=SimpleNamespace(parts=[]))
    client = FakeClient(
        [SimpleNamespace(text=None, candidates=[empty_candidate], usage_metadata=None)]
    )
    retain_local_fault_injection(
        contract_id="REQ_PROVIDER_ADAPTER_INTEROPERABILITY",
        fault_class="interface.payload-schema",
        mechanism="fake Google GenAI client answers a candidate without content parts",
    )

    with pytest.raises(ProviderError) as exc_info:
        GoogleGenAIAdapter(client=client).execute(_request())

    assert exc_info.value.cause.retryable is False
    assert exc_info.value.cause.retry_reason == "missing_candidate_content"


def test_google_answer_with_only_a_function_call_is_a_result() -> None:
    call_part = SimpleNamespace(
        text=None,
        function_call=SimpleNamespace(id="call-1", name="lookup", args={"q": "x"}),
        thought_signature=None,
    )
    client = FakeClient(
        [
            SimpleNamespace(
                text=None,
                candidates=[
                    SimpleNamespace(content=SimpleNamespace(parts=[call_part]))
                ],
                usage_metadata=None,
            )
        ]
    )

    result = GoogleGenAIAdapter(client=client).execute(_request())

    assert result.output_text == ""
    assert [call.name for call in result.tool_calls] == ["lookup"]


for _test_name in (
    "test_sync_google_adapter_uses_sdk_boundary_and_normalizes_result",
    "test_async_google_adapter_uses_sdk_async_boundary",
    "test_google_sdk_retryable_status_is_translated_to_provider_error",
):
    globals()[_test_name] = pytest.mark.coverage_item(
        "VC_PROVIDER_GOOGLE_GENAI_ADAPTER_BOUNDARY"
    )(globals()[_test_name])
del _test_name
