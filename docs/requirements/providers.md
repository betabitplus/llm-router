# Provider requirements

```{goal} Preserve one public contract across provider families
:id: GOAL_PROVIDER_PORTABILITY

Callers should be able to change provider families without changing the meaning of successful responses, asynchronous execution, or provider failures.
```

```{feature} Provider interoperability
:id: FEAT_PROVIDER_INTEROPERABILITY
:derives: GOAL_PROVIDER_PORTABILITY

Each supported provider adapter translates the normalized router request into its native transport and translates the provider result back into the common contract.
```

```{req} Provider adapters preserve normalized semantics
:id: REQ_PROVIDER_ADAPTER_INTEROPERABILITY
:status: accepted
:revision: 1
:required_evidence: impl
:derives: FEAT_PROVIDER_INTEROPERABILITY

**Statement.** Every supported provider adapter shall preserve the normalized router contract across its native HTTP or SDK boundary, including the request and response semantics used by the capabilities that adapter declares supported.

**Rationale.** Provider portability depends on adapters changing transport details without changing the meaning of the public router contract.

**Verification intent.** Require source implementation evidence for each supported adapter and verify provider-specific transport invariants through the derived engineering constraints below rather than duplicating every capability in this broad product requirement.
```

```{treq} OpenAI-compatible transport boundary
:id: TREQ_OPENAI_ADAPTER_BOUNDARY
:status: accepted
:revision: 1
:required_evidence: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

**Constraint.** The OpenAI-compatible adapter shall preserve synchronous and asynchronous success, tool-result messages, retryable transport failures, malformed responses, and public provider-error translation across a real HTTP boundary.

**Rationale.** OpenAI-compatible providers share a transport shape but still expose enough protocol behavior that adapter correctness must be proven at an HTTP boundary rather than only through mocks of internal calls.

**Verification intent.** Exercise the adapter against a deterministic HTTP test server and verify request translation, successful responses, tool messages, retryable failures, malformed responses, and public error translation.
```

```{treq} QwenChat transport boundary
:id: TREQ_QWENCHAT_ADAPTER_BOUNDARY
:status: accepted
:revision: 1
:required_evidence: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

**Constraint.** The QwenChat adapter shall preserve proxy HTTP behavior, media uploads, upload retry, normalized tool outputs, and provider-error translation across its transport boundary.

**Rationale.** QwenChat uses provider-specific proxy and upload protocols that can fail independently of the normalized router model.

**Verification intent.** Exercise the adapter through its deterministic transport boundary and verify proxy requests, media upload behavior, retry handling, tool-output normalization, and public error translation.
```

```{treq} AI Studio transport boundary
:id: TREQ_AISTUDIO_ADAPTER_BOUNDARY
:status: accepted
:revision: 1
:required_evidence: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

**Constraint.** The AI Studio adapter shall use the intended text and native-media transports and translate retryable native failures into the public provider-error boundary.

**Rationale.** Text and native-media execution follow different provider paths, so adapter correctness requires preserving the intended transport selection as well as normalized failures.

**Verification intent.** Exercise both transport modes at the adapter boundary and verify native transport selection, successful normalization, and retryable failure translation.
```

```{treq} Gemini WebAPI transport boundary
:id: TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY
:status: accepted
:revision: 1
:required_evidence: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

**Constraint.** The Gemini WebAPI adapter shall preserve synchronous and asynchronous SDK behavior, local media paths, structured and textual tool outputs, retryable failures, and provider-specific error codes.

**Rationale.** The WebAPI SDK exposes provider-specific session, media, tool, and error shapes that must not leak through or be lost during normalization.

**Verification intent.** Exercise the adapter with a deterministic SDK boundary covering synchronous/asynchronous calls, local media, tool results, retryable failures, and provider error codes.
```

```{treq} Google GenAI transport boundary
:id: TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY
:status: accepted
:revision: 1
:required_evidence: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

**Constraint.** The Google GenAI adapter shall preserve synchronous and asynchronous SDK behavior and translate retryable SDK failures into the public provider-error boundary.

**Rationale.** Both execution modes must preserve the same normalized semantics even though the provider SDK exposes separate synchronous and asynchronous call paths.

**Verification intent.** Exercise both SDK call paths at the adapter boundary and verify successful normalization and retryable failure translation.
```

```{feature} Asynchronous execution
:id: FEAT_ASYNC_EXECUTION
:derives: GOAL_PROVIDER_PORTABILITY

The public asynchronous router API preserves the same normalized capabilities as synchronous execution across supported provider families.
```

```{req} Asynchronous provider execution
:id: REQ_ASYNC_PROVIDER_EXECUTION
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_ASYNC_EXECUTION

**Statement.** Asynchronous requests shall support text, structured output, and media-capable provider routes without changing the public response contract.

**Rationale.** Callers choosing asynchronous execution should not have to accept a reduced or semantically different public API for otherwise supported capabilities.

**Verification intent.** Execute representative text, structured-output, and media-capable requests through the public asynchronous router across supported provider families and verify the normalized public response contract.
```

```{feature} Public response contract
:id: FEAT_PUBLIC_RESPONSE_CONTRACT
:derives: GOAL_PROVIDER_PORTABILITY

Provider-specific response and failure details are normalized into stable public result and error types.
```

```{req} Equivalent provider replies normalize consistently
:id: REQ_RESPONSE_NORMALIZATION
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_PUBLIC_RESPONSE_CONTRACT

**Statement.** Semantically equivalent successful replies from different provider families shall normalize into the same public response semantics.

**Rationale.** Provider choice should affect transport and availability, not force callers to interpret a different result model for equivalent operations.

**Verification intent.** Exercise equivalent successful provider replies through the public router and compare the normalized response fields that constitute the public contract.
```

```{treq} Provider usage normalization
:id: TREQ_USAGE_NORMALIZATION
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_RESPONSE_NORMALIZATION

**Constraint.** Provider-specific usage mappings and objects shall normalize into the common usage statistics model with a consistent total token count.

**Rationale.** Usage metadata arrives in provider-specific shapes but downstream accounting and diagnostics require one stable representation.

**Verification intent.** Directly verify normalization for the supported provider usage shapes, including calculation or preservation of total token counts.
```

```{req} Provider failures preserve the public error boundary
:id: REQ_PROVIDER_ERROR_BOUNDARY
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_PUBLIC_RESPONSE_CONTRACT

**Statement.** Provider HTTP or SDK failures shall surface through the public provider-error type rather than leaking provider-specific exception shapes.

**Rationale.** Stable failure semantics let callers implement recovery and reporting without coupling application code to each provider library.

**Verification intent.** Trigger representative provider HTTP and SDK failures through public router execution and verify the resulting public error type and stable error metadata.
```
