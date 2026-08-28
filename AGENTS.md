Engineering work starts from the requirements graph, not from tests or code in isolation.

- Author goals, features, requirements, and optional technical requirements in the docs graph.
- Declare the minimum required evidence with `needs_artifacts`.
- Link pytest evidence with `verifies` and an explicit `verification_kind`.
- Link implementation evidence in source with `# @impl Title, IMPL_ID, [REQ_ID]`.
- Do not invent requirements merely to justify existing tests or implementation.
- Do not infer verification kind from test directory names.
