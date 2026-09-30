# mutation-pin: REQ_CREDENTIAL_RESOLUTION b30cea8391ac9160
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
    qwen_chat_path,
    qwen_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")

PROVIDER = Provider.QWENCHAT
FIXED_KEY_ID = 4


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_fixed_optional_credential_resolves_to_empty_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fixed QwenChat key id with no variable set still yields a usable key.

    QwenChat permits an absent bearer credential, so resolving fixed key id 4
    whose ``QWENCHAT_API_KEY_4`` is unset must produce the permitted empty
    value for that key id: the request is sent without an Authorization header
    and the routing trace records key id 4.
    """
    monkeypatch.delenv(f"{PROVIDER.name}_API_KEY_{FIXED_KEY_ID}", raising=False)
    config = get_config()
    path = qwen_chat_path()
    reply = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=qwen_success_response(text="anonymous session reply"),
    )
    with ScriptedHTTPServer(port=0, routes={("POST", path): [reply]}) as server:
        base_urls = {**config.provider_base_urls, PROVIDER: f"{server.base_url}/api"}
        catalog = replace(config.catalog, provider_base_urls=base_urls)
        install_config(replace(config, catalog=catalog))
        router = LLMRouter(
            RouterProfile(
                model=Model.QWEN_MAX_LATEST,
                provider=PROVIDER,
                key_id=FIXED_KEY_ID,
            ),
            max_attempts=1,
        )
        response = router.query("Say hello without signing in.")
        recorded = server.recorded_requests("POST", path)

    assert response.output_text == "anonymous session reply"
    assert [attempt.key_id for attempt in response.routing_trace] == [FIXED_KEY_ID]
    assert len(recorded) == 1
    sent_header_names = {name.lower() for name in next(iter(recorded)).headers}
    assert "authorization" not in sent_header_names
