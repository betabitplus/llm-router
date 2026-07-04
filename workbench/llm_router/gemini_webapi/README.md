# Gemini WebAPI Workbench

Index of Gemini WebAPI workbench entrypoints.

- `runtime_preflight.py`: local Opera cookie runtime and SDK cache preflight
- `text_generation_async.py`: explicit async live text generation
- `retry_text_generation_async.py`: explicit async text generation wrapped in the same Tenacity retry exception set used in `src/`
- `image_structured.py`: local image upload plus structured JSON output
- `pdf_structured.py`: local PDF upload plus structured JSON extraction
- `video_file_structured.py`: local video upload plus structured JSON output
- `video_url_structured.py`: public video URL in prompt plus structured JSON output
- `tool_loop_structured_async.py`: explicit async prompt-driven tool loop plus final structured JSON
- `tool_choice_named_structured.py`: prompt-driven named tool choice plus final structured JSON
