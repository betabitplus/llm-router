# Session Persistence

## Ownership

`src/llm_router/_internal/session` owns provider-neutral conversation state
behind the public `Session` facade. It stores public library semantics only:
roles, public chat parts, optional system prompt, and assistant metadata.

## Message Building

`SessionStore.build_messages()` returns a readable public transcript. The
system prompt appears first when present. User messages are labelled as
`User: ...`; assistant messages are labelled as `Assistant: ...`. For
multimodal user turns, a text first part is folded into the label and the
remaining parts keep their original order. If the first user part is media,
`User:` is emitted as a standalone label before the media parts.

## History And Forking

`remember()` appends one user/assistant pair and copies caller-supplied metadata
before storing it. `history` returns tuple snapshots. `fork()` copies the current
provider-neutral transcript so future branch mutations diverge independently.
`clear()` empties only history and keeps the session object reusable.

## Save And Load

`save()` writes a versioned JSON envelope with same-directory atomic replacement.
Local file, video, and image parts are embedded as base64 bytes in the JSON so
the artifact contains library-level meaning rather than references to provider
SDK payloads. `load()` validates the envelope before accepting it and
materializes embedded file and video bytes into local public DTOs.

## Safety Rules

Session files must not contain provider-native request or response objects.
Save failures remove temporary files and do not replace an existing target
unless the full JSON artifact was written successfully.
