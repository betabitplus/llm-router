Engineering work starts from the requirements graph, not from tests or code in isolation.

- Author goals, features, product requirements, and optional engineering constraints in the docs graph.
- Record significant architecture choices as `ADR_####` Architecture Decision needs in `docs/decisions/`; ADRs explain why and never substitute for requirements or engineering constraints.
- Keep ADRs minimal: Context, Decision, Consequences, and Alternatives considered. Use `affects` for material impact and a new accepted ADR with `supersedes` when a decision is replaced.
- If an ADR creates an enforceable invariant, capture that invariant as an Engineering Constraint; implementation and tests trace to the constraint, not to the ADR.
- Declare the minimum required evidence with `required_evidence`.
- Link pytest evidence with a revision-pinned `verifies` reference (`REQ_ID[revision==N]`) and an explicit `verification_kind`.
- Link implementation evidence in source with a revision-pinned target: `# @impl Title, IMPL_ID, [REQ_ID[revision==N]]`.
- Use ubCode/`ubc` for fast graph navigation, queries, references, and impact analysis when available; Sphinx-Needs remains the authoritative graph.
- When ubConnect is licensed, use GitHub Issues only as tracking mirrors via the typed `issue` field; do not import Issues as authoritative requirements.
- Treat `llms.txt`, `llms-full.txt`, and generated page Markdown as derived agent-readable views of the built documentation, never as editable engineering sources.
- Do not invent requirements merely to justify existing tests or implementation.
- Do not infer verification kind from test directory names.
