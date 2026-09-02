# Keep provider protocols behind provider adapters

```{adr} Keep provider protocols behind provider adapters
:id: ADR_0001
:status: accepted
:decision_date: 2026-08-31
:affects: FEAT_PROVIDER_INTEROPERABILITY, REQ_PROVIDER_ADAPTER_INTEROPERABILITY, TREQ_OPENAI_ADAPTER_BOUNDARY, TREQ_QWENCHAT_ADAPTER_BOUNDARY, TREQ_AISTUDIO_ADAPTER_BOUNDARY, TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY, TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY, IMPL_PROVIDER_ADAPTER_INTEROPERABILITY

**Context.** `llm-router` presents one public request and response model while its
providers use materially different HTTP APIs, SDKs, media transports, tool
formats, and failure shapes. Routing and capability orchestration need a stable
provider-neutral contract even as those native protocols change independently.

**Decision.** Runtime orchestration talks to providers only through the
provider-neutral `ProviderAdapter` contract. The runtime creates a
`ProviderRequest`; each concrete adapter owns translation to its native transport
and translates success or failure back into `ProviderResult` or the normalized
provider-failure boundary. Provider-specific SDK objects, upload/session details,
and protocol quirks stay behind the adapter boundary.

**Consequences.** Adding or changing a provider concentrates protocol work in its
adapter instead of branching the central router by provider. Common routing,
tooling, structured-output, and response logic can operate on normalized types.
The adapters carry the translation complexity and therefore need
provider-boundary integration evidence for behavior that cannot be established by
the common contract alone.

**Alternatives considered.** Put provider-specific branches directly in the
router; expose provider SDK request and response objects through the public API;
or force all providers through one transport abstraction even when their native
media, tool, and session protocols differ. Each alternative couples shared
orchestration more strongly to provider details or weakens support for genuinely
different provider capabilities.
```
