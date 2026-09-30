# Judge fault classes with one rule-based mutation engine and targeted semantic mutants

```{adr} Judge fault classes with one rule-based mutation engine and targeted semantic mutants
:id: ADR_0003
:status: accepted
:decision_date: 2026-09-26

**Context.** The project ran two mutation engines. mutmut produced a per-contract
mutation score (Test Strength) behind a Mutation Analysis page, suppressions, operator
feedback and history; pytest-gremlins challenged the Test Plan's Implementation fault
classes contract by contract. The two answered different questions with the same words:
REQ_INVALID_CONFIGURATION_ERRORS showed 76.4% at mutmut and 10 of 23 caught faults at
gremlins, because mutmut's mutants were mostly data replacements that the tests catch
easily. mutmut was never a qualified evidence producer, and its score could not be
pinned on one contract where code is shared. The Test Plan also carried project-wide
mutation floors (Mutation Reach and Mutation Sensitivity ≥ 80%) that only one profile
selected. Industrial practice points the other way: Google surfaces a few surviving
mutants on changed and covered lines as review findings and computes no score, skips
arid code (logging, time, caching), and found statement-block removal among the most
productive operators; Stryker, PIT/Arcmutate and cargo-mutants run the diff on a pull
request and a full run on a schedule, and do not fail the build on a score by default;
research on pseudo-tested methods finds that about one method in ten can lose its whole
body without a failing test. Meta's LLM-generated mutants reach risks that rule
operators cannot, but only a cascade of executable filters keeps their noise out
(identical or comment-only changes, duplicates, equivalents).

**Decision.** Mutation testing exists to judge fault classes, not to produce a score.
One rule-based engine, pytest-gremlins behind the project's campaign adapter, plants
mutants only on each contract's attributable `@impl` lines (amended 2026-09-28: every line
its scopes claim, a line several contracts claim challenged for each with its own tests,
where before such a line was left out and ten contracts had no mutant at all) and runs the full pytest
suite of the contract's passing tests per mutant. Rule operators map to Implementation
classes: comparison → `impl.comparison`; boundary → `impl.boundary`; arithmetic → the
class `impl.arithmetic` (Google's AOR, added 2026-09-27 after an audit found the engine's
operator unused); boolean and return → `impl.control-flow`; statement removal and
function-body removal → the new class `impl.effect`. Python's own faults were added on
2026-09-28, after PyTation (arXiv 2601.19088), whose operators made mostly mutants the
general operators do not: a removed optional argument, conversion, method call or container
element and a swapped attribute read → `impl.effect`; a removed operand of `and`/`or`, a
condition replaced by `True`/`False` (Stryker, PIT) and a negated plain-value condition
(Google's unary operator insertion) → `impl.control-flow`. An audit on 2026-09-30 closed the gaps
the mature tools do not have: an inverted identity or membership test (`is`/`is not`, `in`/`not in`,
as mutmut 3 mutates them) → `impl.comparison`; a removed slice bound (MutPy's slice index removal)
→ `impl.boundary`; a strict comparison made inclusive or back also challenges `impl.boundary`, as
PIT's conditionals-boundary mutator does; a write to a `global` or `nonlocal` name is an effect;
nothing inside a type annotation is mutated, as mutmut leaves annotations alone; and code that runs
when its module is imported counts as reached, since the engine runs every selected test for it, as
Stryker runs its static mutants (before, 21 such mutants showed as not reached and got no verdict). Two deterministic mutant kinds
challenge the levels above the code (2026-09-28): a scenario oracle mutant changes what one Then
step compares with, and the scenarios that use it must fail (`spec.wrong-outcome`); an architecture
mutant adds an import an import-linter rule forbids, and the rule must break
(`architecture.forbidden-edge`). A class is caught only when every valid, unsuppressed mutant of that
class in the contract's code fails at least one of its tests; a mutant no test reaches
is reported as not reached, a mutant that breaks collection as invalid. Noise is
removed before anything runs: arid-code rules declared in the Test Plan (profiles may
turn a rule off where that code is the contract's subject), a static validity filter,
and a suppression pragma with a category and a reason that stays visible and never
counts as caught. A pull request mutates only changed, attributable and covered lines
and reports at most one surviving mutant per line as a review finding, choosing the
operator by the recorded verdicts' productivity as Google chooses by usefulness, and
reports no survivor a recorded verdict judged equivalent or irrelevant; the retained
campaign reruns every contract whose inputs changed, several contracts at once, each in
its own copy of the working tree. A contract's inputs are, as in PIT and Stryker, the product
files that hold its mutants, its tests and the shared test support, each counted by what it
does rather than by its bytes, so a comment or a reformatting reruns nothing. A mutant's time
limit follows its tests, as in PIT: 1.25 times their time in the retained run plus 10 s; one
that outruns it counts as caught only when a second run with twice the limit runs out of time
too. Where a profile asks for them,
semantic mutants generated by an LLM challenge `spec.*` and `interface.*` classes: each
is frozen as a patch, passes a deterministic cascade (valid, differs after comment and
AST normalization, not a duplicate, survives the current tests, a distinguishing input
found by a differential property run), and without a distinguishing input it is
UNKNOWN, never green. The cascade is an evidence producer qualified on a calibration
set. mutmut, its score, its page and its pipeline are removed.

**Consequences.** Every Verification Profile classifies `impl.effect`, and no profile
selects a mutation percentage. Contract Evidence counts caught, surviving, unreached,
suppressed and invalid mutants per class and routes to the Verification Explorer, where
each mutant is one row with its operator, patch and cause; the Health Map names the
same causes. A full campaign is needed once after the operator set changes, and grows
with the new operators. Surviving mutants become test goals on the change instead of a
number to defend. After the pilot, the pieces move to their owners: the engine
adapter, operators, arid rules, validity filter, pragma, semantic-mutant cascade and
their qualification controls to `py-testkit`; class judgement, the explorer and the
monitors to `ternforge-tooling-docops`; the pull-request diff job and the storage of
frozen patches, run snapshots and the engine cache to `ternforge-infra-ci`, with no
scheduled full campaign (a full campaign is a local run on request); enabling it by
default to the project template.

**Alternatives considered.** Keep mutmut as a second engine for data mutations: it is
not qualified, has no mapping to fault classes and duplicates gremlins on comparisons;
a data-mutation class would first have to exist in the Test Plan. Keep a project-wide
mutation floor: a score depends on the suite's size and on how many trivial mutants the
engine plants, so it rewards the wrong work, and one selecting profile does not make a
project rule. Generate every mutant with an LLM: cost and noise grow with the codebase,
while rule operators already express Implementation faults exactly. Cosmic Ray (heavy
distributed runner) and Mutahunter (LLM-only) were not better fits than extending the
qualified engine.
```
