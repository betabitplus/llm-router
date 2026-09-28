# Generate semantic mutants and draft tests through subscription CLIs behind one metered adapter

```{adr} Generate semantic mutants and draft tests through subscription CLIs behind one metered adapter
:id: ADR_0004
:status: accepted
:decision_date: 2026-09-26

**Context.** ADR_0003 made semantic mutants part of fault-class judgement. In its pilot
an agent session wrote the proposals and draft tests by hand from the prompt the cascade
renders. Nothing regenerated a stale proposal, and nothing recorded what a generation
cost. The project has two subscriptions and no API budget. The Claude Pro CLI runs
headless under the subscription, also in CI through an OAuth token. It reports each
call's tokens, the list-price equivalent and the utilization of the plan's 5-hour and
weekly windows. The Antigravity CLI runs headless only where a person signed in. It
reports tokens but no cost, and Google's terms forbid using the product login from
servers. Its print mode keeps the agent's tools, its own system prompt and its conversation
history, about 14k tokens per call. Asked about code, it once reached for a command, which
headless mode denies, and answered nothing. With Claude Code's default context a headless call carries about 29k tokens of
tool and memory context; with tools, plugins, MCP servers and memory switched off, about
600. Measured on 2026-09-26: three mutants for one function with Sonnet 5 took about 2.2k
input and 1.6k output tokens ($0.025 at list price, 18 s), and sixteen such calls moved
the 5-hour window by two points. The windows are shared with the person's own work. An
exhausted window rejects calls and never bills. Antigravity serves two quotas and reports neither to the CLI;
its settings page showed on 2026-09-28 that about 58 of the pilot's calls to Claude models
had used 90% of the smaller quota's week, and about 285 calls to Gemini 31% of the larger
one's. Model output is untrusted: it may break
the schema, call helpers that do not exist, or reach outside the function through
imports or `exec`. Text taken from the repository into a prompt may carry instructions.

**Decision.** Every model call goes through one adapter with interchangeable backends,
`claude-cli` and `antigravity-cli`, tried per role in the order the Test Plan lists. A
call runs in an empty temporary directory with a JSON schema. A `claude-cli` call has no
tools, plugins, MCP servers or memory and a replaced system prompt. An `antigravity-cli`
call, which cannot drop its tools, is told to answer from the text alone, and a call that
reaches for a tool is refused. On receipt the answer is validated again
against the same schema. The adapter writes nothing a model did not return. Each accepted
answer is stored as a response file. Every proposal or draft taken from it carries the
call id, the backend and its version, the model, and the digests of the prompt, the
schema and the response, so the gate can recompute the chain. Every call, accepted or
not, appends one row to a consumption ledger. The row holds the tokens, the list-price
equivalent where the backend reports it, the duration and the plan windows. Before each
call a budget guard compares the last known windows and the run's call count with the
Test Plan's limits. A quota pool that reports no window, Antigravity's smaller one, is
bounded by the calls the ledger shows it took in the last seven days. Above a limit no call is made and the target is deferred. A deferred,
rejected or invalid generation, or an unavailable backend, leaves the target without
current mutants, and its class stays UNKNOWN. None of them is ever a pass. Generation
runs only on request, for targets whose proposals are missing or stale. The gate, the
cascade and the portal build never call a model. The cascade confines model code before
running it. A replacement may use only the names and capabilities its module already
has. A draft test may use only the allowed imports and no process, file-system or
dynamic-code primitives. A draft the cascade rejects is regenerated at most once, with
the reason. A mutant every draft missed climbs a ladder (amended 2026-09-28): one draft from the
draft author with tools, then one from the last resort, the verdict's own model, each working
in a copy of the project where it may read and search, write the one file its pin will be and run
the cascade's own check, with nothing allowed under the person's home. Only `claude-cli` serves
them, since its permissions hold the tools to the copy; the cascade judges the final answer
again, and a pin the last resort wrote says so.

**Consequences.** Proposal sets become reproducible: one command regenerates a stale
target, and its drafts follow. The portal shows which model generated each mutant, links
the stored response, and shows per contract what the generation cost in tokens, list
price and window share. Generation competes with the person's own sessions for the same
windows, so the limits defer work instead of exhausting the plan. A machine may keep several
Claude sign-ins as named CLI profiles and choose one; every ledger row names it, and a call
never inherits the variables of the agent session that started the run. Antigravity stays
local, and CI never calls a model: generation is a local run on request. After the pilot the
pieces move to their owners. The adapter, the backends, the ledger format, the budget
guard, the confinement rules and their qualification controls go to `py-testkit`. The
provenance and spend views go to `ternforge-tooling-docops`. The retention of responses
and ledger goes to `ternforge-infra-ci`. The
default roles and limits go to the project template.

**Alternatives considered.** Pay-as-you-go API keys (Anthropic, Gemini, Vertex) give
exact billing, but they need a separate budget and keys to guard, for work the
subscriptions already cover; they stay possible as further backends. The Gemini API free
tier was rejected because its terms allow using submitted content to improve Google's
products. GitHub Models was retired on 30 July 2026. An agent session writing proposals
by hand from the rendered prompt, as in the pilot, stays possible as generator kind
`agent`, but it is neither reproducible nor metered. One fixed backend without a
fallback order would stop all generation whenever that account's window is full or its
login lapses. Tools for every draft were rejected: a fixed pipeline with the right context
settles most mutants for less (Agentless), so tools are a rung for what it cannot settle; a
person writing the rest by hand was rejected as a hack that does not scale.
```
