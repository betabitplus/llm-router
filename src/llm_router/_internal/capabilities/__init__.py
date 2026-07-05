"""Provider-neutral capability normalization package.

Why:
    Owns conversion between public request DTOs and provider-independent
    content, media, schema, tool, and usage shapes.

What belongs here:
    Capability logic that can run without importing provider SDK clients.

What does not belong here:
    Concrete provider request payloads or SDK-specific client calls.
"""

from llm_router._internal.capabilities.content import (
    MediaPart,
    NormalizedMessage,
    NormalizedPart,
    TextPart,
    normalize_chat_message,
    normalize_content,
    normalize_parts,
)
from llm_router._internal.capabilities.media import (
    FileMedia,
    ImageMedia,
    MediaDescriptor,
    VideoFileMedia,
    VideoUrlMedia,
    describe_media,
)
from llm_router._internal.capabilities.schema import (
    SchemaRepairState,
    SchemaSpec,
    SchemaValidationResult,
    advance_repair_attempt,
    build_repair_prompt,
    normalize_schema,
    validate_schema_output,
    with_schema_transform,
)
from llm_router._internal.capabilities.tools import (
    ToolChoice,
    ToolDefinition,
    ToolLoopState,
    ToolRegistry,
    normalize_tool,
    normalize_tool_choice,
    parse_tool_call,
    run_tool_round,
)
from llm_router._internal.capabilities.usage import normalize_usage

