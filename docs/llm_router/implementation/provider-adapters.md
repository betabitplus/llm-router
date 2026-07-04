# Provider Adapters

## Ownership

`src/llm_router/_internal/providers` owns provider-neutral execution ports and
concrete provider translation.

The runtime resolves routes, keys, limits, settings, messages, schemas, tools,
and timeouts before a request reaches an adapter. Adapters translate that
normalized envelope into provider-native HTTP or SDK payloads and return
provider-neutral results.

## Port Shape

`ProviderRequest` carries one resolved route attempt:

- public provider and model identifiers,
- the concrete provider model string,
- the selected credential metadata and key value,
- normalized messages,
- generation settings,
- optional structured-output schema,
- optional tool registry and tool choice,
- provider-specific passthrough kwargs,
- the stable route index for trace and log correlation.

`ProviderResult` carries JSON-safe provider data, normalized output text,
normalized usage, and normalized tool calls. It must not carry SDK response
objects.

`ProviderFailure` is the private classified failure type behind public
`ProviderError`. It records provider, model, safe message, status code when
available, retryability, and retry reason without storing secrets or raw
payloads.

## Registry And Caches

`providers.registry` centralizes adapter factory lookup and adapter cache
lifecycle. Adapters are cached by `(id(config), provider)` so a provider client
is tied to the config snapshot used to construct it.

The public config install path clears adapter caches after a new config is
installed. Adapters with their own mutable client caches can register those
caches with `register_adapter_cache()`.

Built-in OpenAI-compatible factories are registered for OpenRouter, Mistral,
NVIDIA, Groq, Alibaba, and the AI Studio non-video OpenAI-compatible path.
Google GenAI, Gemini WebAPI, and QwenChat use provider-specific adapters.

## OpenAI-Compatible Adapter

`providers.openai_compatible.OpenAICompatibleAdapter` owns chat-completions
payload translation for providers that expose an OpenAI-style API.

It translates:

- text-only normalized messages to simple string `content`,
- mixed text and image messages to content-part arrays with JPEG data URLs,
- structured-output schemas to `response_format.type=json_schema`,
- normalized tool descriptors to OpenAI-compatible `tools`,
- named, automatic, required, disabled, and raw tool choice forms,
- provider kwargs such as `logprobs` after generated fields.

The last rule means passthrough kwargs may intentionally override generated
fields such as `response_format` when a provider requires a custom shape.

File and video media fail fast in this adapter because the generic
OpenAI-compatible path does not own uploads or video sampling. Provider-specific
adapters own those richer media paths.

## Response And Retry Boundaries

The OpenAI-compatible adapter parses text from string content and content-part
arrays, extracts OpenAI-style tool calls, and normalizes usage before returning
`ProviderResult`.

HTTP status failures are converted to public `ProviderError` with a
`ProviderFailure` cause. Status codes `408`, `409`, `429`, `500`, `502`, `503`,
`504`, and other `>=500` responses are retryable. Caller and auth statuses such
as `400`, `401`, `403`, `404`, and `422` are not retryable.

Transport exceptions with timeout, connection, network, disconnect, remote,
protocol, read, or write failure names are classified as retryable transport
failures. Malformed success JSON is a non-retryable provider response-format
failure. Malformed error JSON still preserves the HTTP status classification.

Provider request logs use stable event names and safe fields only: request id,
provider, model, route index, key id, status code, retryability, retry reason,
and bounded error message. Credentials, prompts, media bytes, and raw response
bodies are not logged.

## Google GenAI

`providers.google_genai.GoogleGenAIAdapter` owns the native
`google.genai.Client` path for `Provider.GOOGLE`.

The adapter imports `google.genai.types` for request DTO construction, but it
constructs clients through `genai.Client(...)` at call time so test and e2e
patches can still replace the SDK client. Tests may inject a small fake client
with `models.generate_content(...)` and `aio.models.generate_content(...)`.

Google content translation uses native `Content` and `Part` values:

- text becomes `Part(text=...)`,
- images become PNG `Blob` inline data,
- files and PDFs become inline `Blob` parts with the configured MIME type,
- local videos become inline video blobs plus `VideoMetadata`,
- remote videos become `FileData(file_uri=...)` plus `VideoMetadata`.

Structured output uses `GenerateContentConfig(response_mime_type="application/json")`
and either the original Pydantic model type or a normalized JSON schema mapping.
Tool descriptors become native function declarations, and tool choice maps to
Google function-calling modes: `AUTO`, `NONE`, or `ANY` with an optional allowed
function name.

Responses are normalized from `.text`, `.parsed`, `.usage_metadata`, and
candidate content parts. Function calls are extracted from
`candidates[0].content.parts[*].function_call` and converted to public
`ToolCall` values.

SDK exceptions are classified by duck-typing `status_code`, `code`, or
`response.status_code`; transport-style exceptions fall back to the shared retry
classifier.

## AI Studio

`providers.aistudio.AIStudioAdapter` owns the AI Studio split:

- ordinary text, image, structured-output, and tool requests delegate to the
  OpenAI-compatible adapter;
- file, PDF, local video, and remote video requests use the native
  Gemini-style `streamGenerateContent` HTTP endpoint.

Before delegation, AI Studio schemas are transformed with adapter-local
`$defs`/`$ref` inlining. This keeps both the OpenAI-compatible branch and the
native media branch away from schema references that AI Studio can mishandle.
The parser contract stays attached to the original schema spec.

The native branch derives its endpoint by stripping OpenAI-style suffixes from
the configured base URL, then posting to:

```text
/v1beta/models/{model}:streamGenerateContent
```

Native parts are Gemini REST dictionaries:

- `{"text": ...}` for text,
- `{"inlineData": {"mimeType": ..., "data": ...}}` for files and local video,
- `{"fileData": {"mimeType": ..., "fileUri": ...}}` for remote video,
- optional `videoMetadata` with `fps`, `startOffset`, and `endOffset`.

Native responses may arrive as SSE `data:` lines or as joined JSON bodies.
The adapter collects candidate text parts, normalizes `usageMetadata`, and
wraps HTTP status failures in `ProviderError` with the same shared retry
classification used by other adapters.

## Gemini WebAPI

`providers.gemini_webapi.GeminiWebAPIAdapter` owns the browser-cookie-backed
`gemini_webapi.GeminiClient` path for `Provider.GEMINI_WEBAPI`.

The live path performs a runtime preflight before client construction:

- the configured Opera cookie database must exist;
- decrypted `google.com` cookies must include `__Secure-1PSID`;
- optional `__Secure-1PSIDTS` and `NID` cookies are detected without logging
  cookie values;
- `GEMINI_COOKIE_PATH` is initialized to the private temp cache when absent.

Preflight failures become non-retryable `ProviderError` values with a
`runtime_preflight_failed` retry reason. Request logs include safe presence
flags for optional cookies, not cookie contents.

Client construction stays lazy so tests and e2e patchers can inject fake SDK
clients. The live adapter builds `GeminiClient(psid, psidts, proxy=None)`,
sets `NID` when available, then initializes with `auto_close=False`,
`auto_refresh=True`, and bounded timeout settings. The initialized client is
cached on the adapter instance behind a lock, so a request does not repeat
runtime preflight or SDK initialization. Config installation clears the adapter
registry, which drops that cached client with the old config snapshot. Media
files remain per-request temporary files.

Gemini WebAPI request translation is prompt-led:

- text and assistant history are flattened into role-prefixed prompt text;
- in-memory images are saved as temporary PNG files and passed via
  `generate_content(..., files=[...])`;
- local files, PDFs, and local videos pass their existing paths in `files`;
- remote video URLs are included in prompt text because this WebAPI path does
  not upload remote URLs as files;
- schemas prepend a JSON-only instruction generated from the normalized
  `SchemaSpec`;
- tools prepend exact textual function-call guidance built from the normalized
  `ToolRegistry` and `ToolChoice`.

Responses are normalized from SDK-like `.text` and optional usage fields.
Prompt-led structured responses are parsed back through the shared schema
validator when valid, and exact textual calls such as `add(a=2, b=3)` are
converted into provider-neutral `ToolCall` values for later tool-loop handling.

SDK failures are classified by HTTP-like `status_code`, `code`, or
`response.status_code` when available. Gemini WebAPI stream/provider codes such
as `1060` are treated separately from HTTP status codes and are non-retryable.
Transport-style exception names use the shared retry classifier.

## QwenChat

`providers.qwenchat.QwenChatAdapter` owns the local QwenChat proxy path for
`Provider.QWENCHAT`.

The adapter uses the configured provider base URL, defaulting to the proxy-style
`/api` root. It posts completions to `/chat/completions` and uploads local
media to `/files/upload`. When a credential value is selected, it is sent as a
bearer token but never logged.

QwenChat completion payloads are OpenAI-like but keep the workbench proxy
semantics:

```json
{
  "model": "...",
  "messages": [{"role": "user", "content": "..."}],
  "stream": false
}
```

Temperature, seed, tools, tool choice, and passthrough provider kwargs are added
when present.

Mixed content preserves caller order while buffering consecutive text:

- text-only content remains a plain string;
- uploaded images become `{"type": "image", "image": "<url>"}`;
- uploaded files, PDFs, and local videos become
  `{"type": "file", "file": "<url>"}`;
- remote video URLs become file parts using the URL directly.

Uploads use a deterministic single-file multipart body with field name `file`
and boundary `llm-router-qwenchat-upload`. Successful upload responses must
include `{"file": {"url": "..."}}`; malformed upload success payloads are
non-retryable provider errors.

QwenChat structured output and tools are prompt-led. Schemas prepend the shared
JSON-only instruction to the first user message. Tool registries are sent both
as OpenAI-style `tools` descriptors and as a safe system prompt telling the
model to emit exact textual calls when it needs a tool. Valid JSON responses
are parsed through the shared schema validator, and exact textual calls are
converted to provider-neutral `ToolCall` values.

Completion and upload HTTP failures share the same retry classification used by
the other HTTP adapters: `429` and server errors are retryable; request/auth
statuses such as `400`, `401`, and `403` are not. Transport exceptions use the
shared transport classifier. The adapter opens HTTP clients per request, so
upload state is request-local and safe under concurrent route attempts.
