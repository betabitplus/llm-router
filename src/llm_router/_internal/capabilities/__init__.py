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
    MediaPart as MediaPart,
    NormalizedMessage as NormalizedMessage,
    NormalizedPart as NormalizedPart,
    TextPart as TextPart,
    normalize_chat_message as normalize_chat_message,
    normalize_content as normalize_content,
    normalize_parts as normalize_parts,
)
from llm_router._internal.capabilities.media import (
    FileMedia as FileMedia,
    ImageMedia as ImageMedia,
    MediaDescriptor as MediaDescriptor,
    VideoFileMedia as VideoFileMedia,
    VideoUrlMedia as VideoUrlMedia,
    describe_media as describe_media,
)
from llm_router._internal.capabilities.schema import (
    SchemaRepairState as SchemaRepairState,
    SchemaSpec as SchemaSpec,
    SchemaValidationResult as SchemaValidationResult,
    advance_repair_attempt as advance_repair_attempt,
    build_repair_prompt as build_repair_prompt,
    normalize_schema as normalize_schema,
    validate_schema_output as validate_schema_output,
    with_schema_transform as with_schema_transform,
)
from llm_router._internal.capabilities.tools import (
    ToolChoice as ToolChoice,
    ToolDefinition as ToolDefinition,
    ToolLoopState as ToolLoopState,
    ToolRegistry as ToolRegistry,
    normalize_tool as normalize_tool,
    normalize_tool_choice as normalize_tool_choice,
    parse_tool_call as parse_tool_call,
    run_tool_round as run_tool_round,
)
from llm_router._internal.capabilities.usage import normalize_usage as normalize_usage
