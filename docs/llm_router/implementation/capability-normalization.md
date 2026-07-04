# Capability Normalization

## Scope

Capability modules convert public DTOs and request options into provider-neutral
internal shapes. They do not import provider SDKs or construct SDK payloads.
Adapters own provider-specific translation.

## Content And Media

`capabilities.content` normalizes public role-less content into
`NormalizedMessage` values with stable roles and ordered parts.

Text becomes `TextPart`. Public media wrappers and raw Pillow images become
`MediaPart` values that hold descriptors from `capabilities.media`:

- `FileMedia` stores a local path and optional MIME type.
- `ImageMedia` stores the Pillow object plus mode and dimensions, without
  serializing bytes.
- `VideoFileMedia` stores a local path and sampling hints.
- `VideoUrlMedia` stores a remote URL and sampling hints.

Raw images are revalidated during normalization so callers cannot bypass the
public image boundary by passing an unchecked Pillow object into a mixed content
sequence.

## Schemas And Repair

`capabilities.schema` converts Pydantic model types and JSON-schema mappings
into `SchemaSpec` values. Pydantic specs validate through Pydantic. Mapping
specs use a small provider-neutral validator for object schemas, required
fields, primitive field types, `minLength`, and `minItems`.

Adapters may transform a schema with `with_schema_transform()` for provider
quirks such as `$ref` inlining. The transform returns a new spec and leaves the
original unchanged.

Repair state is tracked by `SchemaRepairState`. Repair prompts include the
schema name, a bounded schema preview, a bounded validation error preview, and a
bounded previous-output preview. The prompt builder does not log or store raw
provider payloads.

At runtime, structured-output repair stays on the selected route. A failed
validation appends a provider-neutral repair prompt to the same message stream
and calls the same provider again until `structured_output_max_attempts` is
exhausted. The repair prompt begins with the stable explanation that the
previous response did not match the required schema, then includes bounded
schema, error, and previous-output evidence.

## Tools

`capabilities.tools` normalizes callable tools and dict descriptors into a
`ToolRegistry`.

Callable tools derive a compact JSON-schema object from the function signature,
preserve the docstring as a description, and retain the local callable for
execution. Dict tools preserve the descriptor and are descriptor-only until a
future adapter or caller supplies executable behavior.

`normalize_tool_choice()` preserves the public choice forms:

- `None` and `"auto"` become automatic choice.
- `"none"` disables tool choice.
- `"required"` requires a tool call.
- a named string targets a registry tool.
- provider-shaped mappings are copied as raw choices while extracting a name
  when one is present.

`parse_tool_call()` accepts the internal `ToolCall` shape, OpenAI-style
`function.arguments`, and Google-style `functionCall.args`.

`ToolLoopState` records completed rounds, public `ToolStep` traces, and
outstanding tool calls when the max round limit has been reached. Local tool
exceptions are converted to public `ToolExecutionError` with bounded argument
previews from the public error type.

The runtime executes local tool calls before asking the provider for another
turn. Tool results are appended as provider-neutral user context. If the model
continues to request tools after the configured round limit, the response is a
successful `LLMRouterResponse` with empty `output_text`, the last outstanding
tool calls, and the completed tool trace.

## Usage

`capabilities.usage.normalize_usage()` accepts `None`, existing `UsageStats`,
mappings, nested usage mappings, and attribute objects. It recognizes common
snake-case and camelCase token fields from OpenAI-compatible and Google-style
providers. When total tokens are absent but input/output counts exist, it
computes total as their sum.
