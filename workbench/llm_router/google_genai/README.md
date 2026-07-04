# Google GenAI Workbench

Index of Google GenAI workbench entrypoints.

- `text_generation_async.py`: async text generation with config options
- `retry_text_generation_async.py`: async text generation wrapped in the same Tenacity retry predicate used in `src/`
- `models_list.py`: live native Google GenAI model catalog
- `image_structured.py`: sync image input plus structured output
- `pdf_structured.py`: local PDF part plus structured extraction
- `video_file_structured.py`: local video blob plus video metadata
- `video_url_structured.py`: remote video URL plus video metadata
- `tool_loop_structured_async.py`: async callable-based tool loop plus final structured result
- `tool_choice_named_structured.py`: named-function allowlist plus final structured result
