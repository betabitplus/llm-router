# AI Studio Workbench

Index of AI Studio-specific workbench entrypoints.

- `text_generation_async.py`: async plain text generation on the non-video path
- `retry_text_generation_async.py`: async non-video text generation wrapped in the same Tenacity retry exception set used in `src/`
- `models_list.py`: live AI Studio OpenAI-compatible model catalog
- `image_structured.py`: image input with structured JSON output
- `pdf_structured.py`: native local PDF upload plus structured JSON output
- `tool_choice_named_structured.py`: forced named-tool choice plus final structured JSON
- `tool_loop_structured_async.py`: async tool loop plus final structured JSON on the non-video path
- `schema_ref_resolution.py`: `$ref` and `$defs` schema inlining for AI Studio
- `video_file_structured.py`: native streamed local-video structured output
- `video_url_structured.py`: native streamed remote-video structured output
