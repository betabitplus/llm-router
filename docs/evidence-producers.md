# Pilot evidence producers

This page contributes only llm-router-specific evidence producers to the authoritative
Sphinx-Needs graph. Generic pytest, py-testkit, Allure, VCR, DocOps, and scripted HTTP
producers are package-owned by DocOps.

```{qualification} Google GenAI fake SDK success-path contract
:id: QUAL_GOOGLE_GENAI_FAKE_SUCCESS
:hide:
:qualification_kind: integration-contract
:target_version: llm-router current revision
:evidence_url: https://github.com/betabitplus/llm-router/blob/main/tests/llm_router/integration/test_google_genai_adapter_fake.py

The fake SDK is exercised through the real adapter sync and async success paths.
```

```{qualification} Google GenAI fake SDK error-path contract
:id: QUAL_GOOGLE_GENAI_FAKE_ERROR
:hide:
:qualification_kind: cross-check
:target_version: llm-router current revision
:evidence_url: https://github.com/betabitplus/llm-router/blob/main/tests/llm_router/integration/test_google_genai_adapter_fake.py

The fake SDK also exercises provider error translation and retry classification.
```

```{producer} Google GenAI fake SDK
:id: PRODUCER_GOOGLE_GENAI_FAKE_SDK
:hide:
:producer_role: test-substitute
:producer_version: llm-router current revision
:producer_impact: high
:producer_purpose: Reproduce the Google GenAI SDK surface used by the adapter in-process.
:risk_if_wrong: Adapter integration proof can claim SDK behavior not supported by the live provider.
:residual_doubt: The live provider and SDK may change after the retained calibration experiment.
:qualified_by: QUAL_GOOGLE_GENAI_FAKE_SUCCESS;QUAL_GOOGLE_GENAI_FAKE_ERROR

The live provider capability experiment EXP_0002 supplies calibration, not verification.
```

```{qualification} Gemini WebAPI fake SDK success-path contract
:id: QUAL_GEMINI_WEBAPI_FAKE_SUCCESS
:hide:
:qualification_kind: integration-contract
:target_version: llm-router current revision
:evidence_url: https://github.com/betabitplus/llm-router/blob/main/tests/llm_router/integration/test_gemini_webapi_adapter_fake.py

The fake client is exercised through text, async video, structured output, and tool paths.
```

```{qualification} Gemini WebAPI fake SDK error-path contract
:id: QUAL_GEMINI_WEBAPI_FAKE_ERROR
:hide:
:qualification_kind: cross-check
:target_version: llm-router current revision
:evidence_url: https://github.com/betabitplus/llm-router/blob/main/tests/llm_router/integration/test_gemini_webapi_adapter_fake.py

The fake client exercises HTTP-like status and provider-specific error translation.
```

```{producer} Gemini WebAPI fake SDK
:id: PRODUCER_GEMINI_WEBAPI_FAKE_SDK
:hide:
:producer_role: test-substitute
:producer_version: llm-router current revision
:producer_impact: high
:producer_purpose: Reproduce the Gemini WebAPI client surface used by the adapter in-process.
:risk_if_wrong: Adapter integration proof can claim client behavior not supported by the live service.
:residual_doubt: Browser-authenticated provider behavior may change after the retained calibration experiment.
:qualified_by: QUAL_GEMINI_WEBAPI_FAKE_SUCCESS;QUAL_GEMINI_WEBAPI_FAKE_ERROR

The live provider capability experiment EXP_0003 supplies calibration, not verification.
```

Use the generated Evidence trust page to inspect these producers together with the
generic producer chain and its current calibration gaps.
