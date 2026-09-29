# semantic-mutant: SM-12FA1E31
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.config import BehaviorDefaults, LLMRouterConfig
from llm_router._internal.config import ProviderCatalog
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
    ProviderResult,
)
from llm_router._internal.runtime.executor import (
    _advance_structured_result,
    _ExecutionLoopState,
    _ExecutionPlan,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]")
def test_repair_step_keeps_schema_for_follow_up_request() -> None:
    spec = normalize_schema(
        {
            "title": "Out",
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        }
    )
    config = LLMRouterConfig(
        default_provider=Provider.GOOGLE,
        default_model=Model.GEMINI_FLASH,
        default_key_id=1,
        defaults=BehaviorDefaults(
            retry_policy=None,
            policy=None,
            default_max_tool_rounds=0,
            structured_output_max_attempts=2,
            provider_limits=None,
        ),
        catalog=ProviderCatalog(),
    )
    plan = _ExecutionPlan(
        schema=spec, tool_registry=None, tool_choice=None, max_tool_rounds=0
    )
    request = ProviderRequest(
        request_id="1",
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH,
        provider_model="gemini",
        credential=ProviderCredential(key_id=1, env_var="K", value="V"),
        messages=(),
    )
    result = ProviderResult(
        data={},
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH,
        provider_model="gemini",
        output_text="not json",
    )
    state = _ExecutionLoopState(
        messages=(),
        tool_state=None,
        tool_choice=None,
        tool_registry=None,
        schema=spec,
        structured_attempts=0,
    )
    step = _advance_structured_result(
        config=config,
        provider_request=request,
        plan=plan,
        state=state,
        result=result,
    )
    assert step.response is None
    assert step.state.structured_attempts == 1
    assert step.state.schema is spec
