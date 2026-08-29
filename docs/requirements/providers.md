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
:revision: 1
:needs_artifacts: impl
:derives: FEAT_PROVIDER_INTEROPERABILITY

Supported provider adapters must preserve normalized request, response, media, structured-output, tool, and error semantics across their native HTTP or SDK boundaries.
```

```{treq} OpenAI-compatible transport boundary
:id: TREQ_OPENAI_ADAPTER_BOUNDARY
:revision: 1
:needs_artifacts: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

The OpenAI-compatible adapter must preserve synchronous and asynchronous success, tool-result messages, retryable transport failures, malformed responses, and public provider-error translation across a real HTTP boundary.
```

```{treq} QwenChat transport boundary
:id: TREQ_QWENCHAT_ADAPTER_BOUNDARY
:revision: 1
:needs_artifacts: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

The QwenChat adapter must preserve proxy HTTP behavior, media uploads, upload retry, normalized tool outputs, and provider-error translation across its transport boundary.
```

```{treq} AI Studio transport boundary
:id: TREQ_AISTUDIO_ADAPTER_BOUNDARY
:revision: 1
:needs_artifacts: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

The AI Studio adapter must use its intended text and native-media transports and translate retryable native failures into the public provider-error boundary.
```

```{treq} Gemini WebAPI transport boundary
:id: TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY
:revision: 1
:needs_artifacts: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

The Gemini WebAPI adapter must preserve synchronous and asynchronous SDK behavior, local media paths, structured and textual tool outputs, retryable failures, and provider-specific error codes.
```

```{treq} Google GenAI transport boundary
:id: TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY
:revision: 1
:needs_artifacts: impl;integration
:derives: REQ_PROVIDER_ADAPTER_INTEROPERABILITY

The Google GenAI adapter must preserve synchronous and asynchronous SDK behavior and translate retryable SDK failures into the public provider-error boundary.
```

```{feature} Asynchronous execution
:id: FEAT_ASYNC_EXECUTION
:derives: GOAL_PROVIDER_PORTABILITY

The public asynchronous router API preserves the same normalized capabilities as synchronous execution across supported provider families.
```

```{req} Asynchronous provider execution
:id: REQ_ASYNC_PROVIDER_EXECUTION
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_ASYNC_EXECUTION

Asynchronous requests must support text, structured output, and media-capable provider routes without changing the public response contract.
```

```{feature} Public response contract
:id: FEAT_PUBLIC_RESPONSE_CONTRACT
:derives: GOAL_PROVIDER_PORTABILITY

Provider-specific response and failure details are normalized into stable public result and error types.
```

```{req} Equivalent provider replies normalize consistently
:id: REQ_RESPONSE_NORMALIZATION
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_PUBLIC_RESPONSE_CONTRACT

Equivalent successful replies from different provider families must normalize into the same public response semantics.
```

```{treq} Provider usage normalization
:id: TREQ_USAGE_NORMALIZATION
:revision: 1
:needs_artifacts: impl;unit
:derives: REQ_RESPONSE_NORMALIZATION

Provider-specific usage mappings and objects must normalize into the common usage statistics model with a consistent total token count.
```

```{req} Provider failures preserve the public error boundary
:id: REQ_PROVIDER_ERROR_BOUNDARY
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_PUBLIC_RESPONSE_CONTRACT

Provider HTTP or SDK failures must surface through the public provider-error type rather than leaking provider-specific exception shapes.
```
