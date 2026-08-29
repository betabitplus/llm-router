Engineering work starts from the requirements graph, not from tests or code in isolation.

- Author goals, features, requirements, and optional technical requirements in the docs graph.
- Declare the minimum required evidence with `needs_artifacts`.
- Link pytest evidence with a revision-pinned `verifies` reference (`REQ_ID[revision==N]`) and an explicit `verification_kind`.
- Link implementation evidence in source with a revision-pinned target: `# @impl Title, IMPL_ID, [REQ_ID[revision==N]]`.
- Use ubCode/`ubc` for fast graph navigation, queries, references, and impact analysis when available; Sphinx-Needs remains the authoritative graph.
- When ubConnect is licensed, use GitHub Issues only as tracking mirrors via the typed `issue` field; do not import Issues as authoritative requirements.
- Treat `llms.txt`, `llms-full.txt`, and generated page Markdown as derived agent-readable views of the built documentation, never as editable engineering sources.
- Do not invent requirements merely to justify existing tests or implementation.
- Do not infer verification kind from test directory names.
