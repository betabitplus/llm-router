# llm-router

A provider-agnostic LLM routing and orchestration library.

## Highlights

- One stable public entrypoint: `LLMRouter`.
- Portable public routing vocabulary through `Model`, `Provider`, and `RouterProfile`.
- `Structured output`, `tool loop`, retries, fallback routing, and `Session` continuity.
- Multimodal request content including images, PDFs, local videos, and remote video URLs where a provider path exists.
- One normalized public response wrapper with `output_text`, usage, tool trace, and routing trace.

## Provider Families

- Google GenAI and AI Studio
- Gemini WebAPI
- QwenChat
- OpenAI-compatible providers such as OpenRouter, Mistral, NVIDIA, Groq, and Alibaba

## Install

- Python: `3.13+`
- PyPI: `pip install llm-router`

## Configuration

Runtime requests need provider credentials and, in non-trivial setups,
installed router configuration. For local repo setup and environment loading,
use [SETUP.md](SETUP.md). For package usage patterns and public API shapes, use
[docs/llm_router/usage.md](docs/llm_router/usage.md).

## Quick Start

```python
from llm_router import LLMRouter, Model

router = LLMRouter(Model.GEMINI_FLASH)
response = router.query("Reply only OK.")
print(response.output_text)
```

## Project Docs

- Import from the top-level package only: `from llm_router import LLMRouter`
- Package architecture and usage docs: [docs/llm_router/README.md](docs/llm_router/README.md)
- Repository documentation index: [docs/README.md](docs/README.md)
- Test suite layout and execution notes: [tests/README.md](tests/README.md)
- Local setup: [SETUP.md](SETUP.md)
- Contributor workflow: [CONTRIBUTING.md](CONTRIBUTING.md)
- Repository maintainer setup: [.github/MAINTAINER_SETUP.md](.github/MAINTAINER_SETUP.md)

## Using In Other Projects (Private Repo)

Install from Git (track `main`):

```bash
uv add "llm-router @ git+https://github.com/betabitplus/llm-router.git@main"
```

For reproducible installs (recommended for CI), pin to a tag instead:

- `...@vX.Y.Z`

Git must be able to authenticate to the private repo (recommended: macOS
Keychain credential helper or SSH keys).

## License

MIT. See [LICENSE](LICENSE).
