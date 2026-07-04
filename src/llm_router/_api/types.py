"""Public vocabulary types for `llm_router`.

Why:
    Keeps the stable public naming layer for providers, models, and key
    selection in one place.

How:
    These names describe the public routing vocabulary, not every provider's
    raw SDK-specific naming scheme. The installed model registry maps the
    public `Model` values here to provider-native model strings.

Notes:
    This module is the right place to answer:
    - "what providers does the public API know about?"
    - "what portable model names can callers ask for?"
    - "how do I request a fixed key versus automatic key rotation?"
"""

from enum import StrEnum
from typing import Literal


class Provider(StrEnum):
    """Supported public provider identifiers.

    These values are stable routing names used across config, profiles,
    routing traces, and public error messages.
    """

    GOOGLE = "google"
    AISTUDIO = "aistudio"
    GEMINI_WEBAPI = "gemini_webapi"
    QWENCHAT = "qwenchat"
    OPENROUTER = "openrouter"
    MISTRAL = "mistral"
    NVIDIA = "nvidia"
    GROQ = "groq"
    ALIBABA = "alibaba"


class Model(StrEnum):
    """Supported public model identifiers.

    A `Model` is a portable model intent, not necessarily the exact string sent
    to a provider API. The configured model registry maps each public model to
    one or more provider-specific concrete names.
    """

    # Gemini models
    GEMINI_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_FLASH = "gemini-2.5-flash"
    GEMINI_FLASH_2_0 = "gemini-2.0-flash"
    GEMINI_PRO = "gemini-2.5-pro"
    GEMINI_3_FLASH = "gemini-3-flash"

    # OpenRouter models
    DEEPSEEK_V3 = "deepseek-chat-v3"
    QWEN_VL_32B = "qwen2.5-vl-32b-instruct"

    # Mistral models
    MISTRAL_LARGE = "mistral-large-latest"
    PIXTRAL_LARGE = "pixtral-large-latest"

    # NVIDIA models
    LLAMA_MAVERICK = "llama-4-maverick"

    # Groq models
    LLAMA_SCOUT = "llama-4-scout"

    # Alibaba models
    QWEN_VL_3B = "qwen2.5-vl-3b-instruct"

    # QwenChat models (FreeQwenApi)
    QWEN_MAX_LATEST = "qwen-max-latest"
    QWEN3_235B_A22B = "qwen3-235b-a22b"
    QWEN3_5_397B_A17B = "qwen3.5-397b-a17b"
    QWEN3_VL_PLUS = "qwen3-vl-plus"


# Common small type aliases (stdlib-only).
# `KeyId` is used anywhere the public API needs to pick credentials for a
# provider route. Integers pin one concrete key slot, while `"auto"` asks the
# runtime to choose among discovered keys for that provider.
KeyId = int | Literal["auto"]
