"""Provider-neutral session package.

Why:
    Owns session history, semantic persistence, and transcript assembly behind
    the public `Session` facade.

What belongs here:
    Session storage, save/load serialization, and public-content transcript
    assembly.

What does not belong here:
    Provider-native payloads or SDK-specific conversation state.
"""

from llm_router._internal.session.store import SessionStore as SessionStore
