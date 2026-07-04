# QwenChat Workbench

Index of QwenChat workbench entrypoints.

- `text_generation_async.py`: async plain text generation through `/chat/completions`
- `retry_text_generation_async.py`: async text generation wrapped in the same Tenacity retry policy used by the direct proxy path in `src/`
- `image_structured.py`: image upload plus structured scene output
- `pdf_structured.py`: PDF upload plus structured document extraction
- `message_parts_mixed.py`: role-less mixed text and image parts flattened into one user message
- `tool_loop_structured_async.py`: async nonstandard tool-assisted flow plus final structured JSON
- `tool_choice_named_structured.py`: nonstandard named-tool choice plus final structured JSON
- `video_file_structured.py`: local MP4 upload plus structured video understanding
