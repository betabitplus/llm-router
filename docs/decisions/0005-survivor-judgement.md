# Decide survivors by symbolic search first and by calibrated model assessors second

```{adr} Decide survivors by symbolic search first and by calibrated model assessors second
:id: ADR_0005
:status: accepted
:decision_date: 2026-09-26

**Context.** A survivor is a mutant that every passing test of its contract lets through.
ADR_0003 keeps a semantic survivor UNKNOWN until an input tells it apart from the original. The
differential property run searches for that input at random and misses rare ones. The first
generated set of `TREQ_USAGE_NORMALIZATION` shows it: a negative count that is no longer clamped
to zero stayed UNKNOWN after 300 generated inputs. The 68 surviving rule mutants of the campaign
carry no such input, so a reader cannot tell a real gap from a mutant no input can expose.
Deciding equivalence is undecidable in general. A symbolic search (CrossHair, symbolic execution
over Z3) finds rare inputs within a bound. In the pilot it found the unclamped negative count in
about 20 s, and it confirmed two known leaks of `TREQ_RUNTIME_LOG_SAFETY`. It decided 8 of the
28 labelled calibration pairs within 10 s each. Its search order is seeded, but a bound on time
is not: the unclamped count took about 250 paths, found in 23 s on one run and missed within 20
s on the next, while a bound on paths repeated the same search on every run. It needs typed
parameters: a parameter typed `object` has to be searched as a payload. It prints some found
values in a form that does not evaluate back, so its claims need checking. It also compares
return values and arguments only, not effects such as log records. Model assessors reason about
effects and intent, but they invent inputs and misjudge equivalence. Asked about payloads, both
Claude assessors judged a mutant that skips validating an installed configuration equivalent,
because no payload is a configuration; asked the right question, Gemini still judged it
equivalent, on the wrong premise that a configuration is validated when it is built. Asked
without the definitions of the project's types, the assessors invented constructors and enum
members that do not exist. The three inputs the search found for the rate limiter told the
versions apart only by a clock reading or a memory address. A model's equivalent cannot be
checked by execution; a model's distinct can. Split conformal calibration bounds how often a
threshold passes a distinct mutant, for mutants exchangeable with the calibration pairs.

**Decision.** Every survivor goes through the same judgement, and none of it can make a survivor
caught. The first step is a symbolic search over a typed harness of the original and the mutant,
bounded by the Test Plan's number of paths, with a time limit only as a safety net. The harness
observes a function by its return value, a method by its return value and its object's state
afterwards, an initializer by the object it builds, and an exception by its type. The second
step asks every assessor the Test Plan lists about the parameters as the code declares them,
never the search's payloads, and shows how the project's types the target takes or names are
built: distinct with an input, equivalent, or unsure, each with a confidence. An input from any
source counts only when execution confirms it: called with it twice, each version repeats
itself, and the original and the mutant are observed to differ. The input must be an expression
of literals and the project's dataclasses, exceptions and enum members, and nothing else is
evaluated. A semantic survivor with a confirmed input is distinguished. A rule survivor keeps
its outcome and gains the input as its test goal. When every assessor answers equivalent with a
confidence above the calibrated threshold, the survivor is labelled likely equivalent. The label
is advisory: the survivor stays UNKNOWN, or survived for a rule mutant, until its verdict is
recorded (ADR_0006). The threshold is split conformal over the distinct pairs: labelled pairs,
every distinct one with an input that execution confirms, and observed pairs, real survivors the
symbolic search left unsure and a mutation pin proves distinct (amended 2026-09-27: on those,
single assessors called survivors equivalent that the hand-made pairs never made them call). An assessor may call at most the
false-equivalent rate of all distinct pairs equivalent. The assessors' calibration answers are
frozen and replayed by the qualification. A change of assessor, model, prompt or pairs leaves the ensemble
uncalibrated until it is calibrated again. The judgement of rule survivors runs on request,
apart from the campaign, and never changes a mutant's outcome.

**Consequences.** UNKNOWN shrinks only through confirmed inputs or a person's verdict, never
through a model's opinion. Rule survivors become test goals with inputs, or candidates for an
`equivalent` pragma with the assessors' reason. Assessor calls use the generation budget of
ADR_0004. The Test Plan lists assessors of two model families, so one family's blind spot does
not label a survivor alone; the calibration pairs are easier than real survivors, so the
false-equivalent rate is an aim, not a guarantee, which the advisory label reflects. After the
pilot the pieces move to their owners. The harness, the symbolic step, the input check, the
judgement, the calibration pairs, the threshold and their qualification controls go to
`py-testkit`. The judgement views go to `ternforge-tooling-docops`. The retention of answers
and results goes to `ternforge-infra-ci`; judgement runs stay local runs on request. The default assessors and
settings go to the project template.

**Alternatives considered.** Counting an assessed equivalent above the threshold as equivalent
was rejected: a false equivalent would take a real gap out of its class and could turn the class
green. Symbolic search alone cannot see effects and stops at its time bound. Model assessors
alone invent inputs. Many more random examples still miss inputs that need one exact value.
Trivial compiler equivalence has no optimizing compiler to lean on in Python, and the cascade
already compares normalized syntax trees.
```
