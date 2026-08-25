---
name: provider-sdk-wrapping-verification
doc_type: verification
description: Transitional map of the provider SDK wrapping scenarios that still live in the legacy e2e slice.
---

# Provider SDK Wrapping

Behavior already migrated to Living Specifications is defined under `features/` and published as `/specifications/`. Do not duplicate those guarantees here.

This page exists only while the remaining provider-specific scenarios still use the legacy `tests/llm_router/e2e/provider_sdk_wrapping/` layout.

## Remaining legacy coverage

### AI Studio

- [`test_aistudio_async_text_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_async_text_structured_pipeline.py)
- [`test_aistudio_image_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_image_structured_pipeline.py)
- [`test_aistudio_pdf_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_pdf_structured_pipeline.py)
- [`test_aistudio_tool_choice_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_tool_choice_pipeline.py)
- [`test_aistudio_tools_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_tools_structured_pipeline.py)
- [`test_aistudio_video_file_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_video_file_structured_pipeline.py)
- [`test_aistudio_video_url_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_aistudio_video_url_structured_pipeline.py)

### Gemini WebAPI

- [`test_gemini_webapi_async_text_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_async_text_pipeline.py)
- [`test_gemini_webapi_file_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_file_structured_pipeline.py)
- [`test_gemini_webapi_image_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_image_structured_pipeline.py)
- [`test_gemini_webapi_tool_choice_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_tool_choice_structured_pipeline.py)
- [`test_gemini_webapi_tools_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_tools_structured_pipeline.py)
- [`test_gemini_webapi_video_file_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_video_file_structured_pipeline.py)
- [`test_gemini_webapi_video_url_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_gemini_webapi_video_url_structured_pipeline.py)

### Google GenAI

- [`test_google_genai_async_image_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_async_image_structured_pipeline.py)
- [`test_google_genai_file_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_file_structured_pipeline.py)
- [`test_google_genai_profile_tools_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_profile_tools_structured_pipeline.py)
- [`test_google_genai_video_file_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_video_file_structured_pipeline.py)
- [`test_google_genai_video_url_structured_pipeline.py`](../../../../tests/llm_router/e2e/provider_sdk_wrapping/test_google_genai_video_url_structured_pipeline.py)

These files remain replayable regression coverage until their behavior is modeled in the semantic specification hierarchy. When the last one migrates, delete this legacy slice document rather than maintaining a second behavioral description.
