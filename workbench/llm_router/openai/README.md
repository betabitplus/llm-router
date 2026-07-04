# OpenAI-Compatible Workbench

Index of generic OpenAI-compatible workbench entrypoints.

- `text_generation_async.py`: async text generation with temperature and seed
- `retry_text_generation_async.py`: async text generation wrapped in the same Tenacity retry exception set used in `src/`
- `logprobs_text_generation.py`: sync NVIDIA-backed text generation with token logprobs
- `image_structured.py`: image input plus structured JSON output
- `tool_loop_structured_async.py`: async multi-round tool calling with a final structured JSON answer
- `tool_choice_named_structured.py`: named-function tool choice plus final structured JSON
