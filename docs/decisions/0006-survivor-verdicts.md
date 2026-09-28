# Let a verdict model decide survivors and escalate only product decisions

```{adr} Let a verdict model decide survivors and escalate only product decisions
:id: ADR_0006
:status: accepted
:decision_date: 2026-09-26

**Context.** ADR_0005 judges survivors and leaves the verdict to a person: every likely
equivalent, every test goal and every unsure survivor waits. The person owns the project's
Goals and Features and looks at Requirements and Technical requirements only by exception.
The first full judgement left 68 surviving rule mutants: 31 test goals with a confirmed input,
4 likely equivalents, 5 unsure and 28 without a harness. Nearly all of them are decisions
inside one requirement's scope, such as whether a boundary check or a key order is part of
the contract. A person reviewing each would block the Features they serve on details the
person does not own. A model can read the requirement, the Feature and Goal above it and both
versions of the code; its equivalent is still an opinion, but a pinning test it asks for can
be checked by execution. Models change and degrade silently, so a model that decides must be
requalified whenever it changes.

**Decision.** A verdict model, named by the Test Plan's Survivor verdict role, gives every
judged survivor, and every mutant no test of its contract reaches, one verdict with its
reason: pin, equivalent, irrelevant or escalate.
Escalate is allowed only when deciding changes what a Feature or Goal promises and no
requirement settles it; a verdict inside a requirement's scope is never escalated. Equivalent
is never allowed for a survivor with a confirmed input. An equivalent or irrelevant verdict
takes the mutant out of its class as suppressed, with the reason and the model that gave it,
only when the Test Plan's Survivor verdict review, a model of another family asked the same
question, agrees; when it does not, the mutant is pinned (amended 2026-09-27, after PoLL:
judges of one family favour their own). The verdict and the review cite what they rest on,
copied word for word from their question: the words of the requirement it turns on and a line
the change touches; a check finds each in the question, and an answer that breaks it does not
count and is asked once more with what broke (amended 2026-09-28). A pin verdict asks the draft author for a test; the
test is adopted as a mutation pin only when, in the project's style (formatted and safely
fixed by its ruff rules), it breaks no lint rule, passes on the original five times, fails on
the mutant and imports only what the contract's tests may and, for a Technical requirement,
the module of the code it tests and the project modules it imports. A mutation pin verifies its contract and names its mutant;
it proves no coverage case and no depth. When the pin rules change, every pin is judged again,
and a pin no draft brings within them is removed. An escalated survivor keeps its class failing and waits for the person, whose
verdict wins over the model's. A verdict counts while the code, the tests and the question it
answered are unchanged. Every model a role lists passes that role's canaries, cases with a
known outcome, before its answers count, and again after any change of model, question or
canary set; an assessor passes the calibration floors.

**Consequences.** The person sees only escalations, which should be rare and product-level;
survivors inside a requirement end as pins, as suppressed equivalents with a reason, or as a
decision on the list. A wrong equivalent from the verdict model hides a real gap until the
code or the tests change, so its reason stays visible on the mutant and the canaries check the
model on known cases. Mutation pins grow the suite automatically, and the campaign counts
them. Verdict calls use the Claude subscription and its budget; the rest of the models run on
Antigravity. After the pilot the pieces move to their owners. The verdict question, the
application of verdicts to classes, the pin adoption and the canaries go to `py-testkit`. The
verdict and escalation views go to `ternforge-tooling-docops`. The pull-request diff that
applies the recorded verdicts goes to `ternforge-infra-ci`; verdict and canary runs stay local
runs on request. The default roles and canaries go to the project template.

A requirement's new revision retires the pins of the old one: `--revise-pins` removes every pin
that verifies an older revision than the docs declare, with its record, and rebuilds the
assessors' calibration from stored answers without asking a model; the next decision asks the
new question and pins the mutant anew.

**Alternatives considered.** A person reviewing every survivor was rejected: it blocks
Features on decisions the person does not own. Taking the assessors' unanimous equivalent as
the verdict was rejected: they are calibrated on hand-made pairs and cannot see effects, and a
separate, stronger model reading the requirement and its Feature is a second opinion. No
escalation at all was rejected: a change to what a Feature promises is the person's to make.
Writing pragmas into the source for equivalents was rejected in favour of a ledger bound to
the code, so a verdict goes stale when the code changes.
```
