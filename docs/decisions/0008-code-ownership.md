# Trace the code to its requirements per function and resolve every unexecuted line into a cause

```{adr} Trace the code to its requirements per function and resolve every unexecuted line into a cause
:id: ADR_0008
:status: accepted
:decision_date: 2026-10-03

**Context.** The `@impl` markers serve the mutation campaign, which narrows them to statements so
that one contract's mutants are not pinned on another. Nothing shows the code side: which functions
serve no requirement, which owned functions their requirement's tests never run, which code nothing
uses, and why the lines no test runs stay unrun. DO-178C (6.4.4.3) resolves every structure that
requirements-based tests leave unexecuted into exactly one cause: a missing test, a missing
requirement, extraneous or dead code, or deactivated code kept on purpose. BMW LOBSTER traces every
function to a requirement or records why it needs none (`lobster-exclude`). Coverage.py reports
each function's region and which test runs each line; vulture finds code nothing uses.

**Decision.** The unit of code ownership is the function:

- a function serves the contracts whose `@impl` marker sits on it or inside it: for ownership a
  marker covers its whole function, while the campaign keeps its narrower scopes for its mutants;
  a marker on a class covers its methods, and one on module-level code (a registration) covers the
  functions it names;
- a function no marker names serves the contracts of the functions that call it (a helper inherits
  its callers' owners), along a static call graph of plain names, imported names, module aliases,
  `self`/`cls` methods and the attributes a class keeps instances in; a function reached only
  dynamically stays unowned rather than borrow an owner it may not have;
- a function that serves no contract fails, unless the owner's delegate records why it needs no
  requirement (`.ai-bridge/code-exemptions.json`, outside the product while the owner keeps the
  product unchanged);
- a marker claims that its function implements each contract it names, so the tests of each of
  them must run it; a helper is confirmed when a test of any contract it serves runs it; a test
  counts for a contract when it verifies the contract or one derived from it;
- vulture names the code nothing uses; code the package exports counts as used by its callers, and
  a class nothing uses becomes a mark of its own, since no function shows it;
- a line no test runs takes one cause: no test (in an owned or exempt function), no requirement (in
  an unowned one), extraneous (unused or unreachable code, counted even though coverage.py drops
  unreachable statements) or deactivated (excluded from coverage on purpose);
- the functions and classes that serve no requirement, those their requirements' tests never run,
  those nothing uses and the unexecuted lines of each failing cause may only fall: the gate holds
  them to a baseline that drops with them and rises only with a reason recorded in it.

**Consequences.** A Code map shows the product bottom-up on the Health Map's own map, with the
package's areas and modules in place of goals and capabilities and its functions in place of
contracts: four layers (Owner, Run by its tests, Used, Unexecuted lines), each as a map and a table,
with the same filters, Find, links and Changes; its table lists every function with what each
layer says of it. A contract page lists the code that serves it and whether its own tests run each
function, and links to that code on the map, which links back to the contract. The first map is the
honest baseline: most of the public facade and glue code serves no requirement by a marker, and
stays red until a requirement or a recorded reason covers it.

**Alternatives considered.** LOBSTER itself was rejected as a second tracing system beside
Sphinx-Needs; its rule, trace or justify every function, is adopted. Ownership from coverage
contexts alone was rejected: a helper that many tests run would inherit every contract. A page of
its own was rejected for the Health Map's shared map, so that both read, filter and link alike.
Exemption markers inside the product are deferred while the owner keeps the product unchanged.
```
