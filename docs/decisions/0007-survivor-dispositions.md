# Resolve every survivor into one disposition and keep requirement silence and ineffective code open

```{adr} Resolve every survivor into one disposition and keep requirement silence and ineffective code open
:id: ADR_0007
:status: accepted
:decision_date: 2026-10-02

**Context.** ADR_0006 ends every survivor as a pin, a suppression with a reason (equivalent or
irrelevant) or an escalation. Two different findings fall into the suppressions and disappear.
The first is a requirement that says nothing about a behaviour a caller can observe: irrelevant
is defined as a difference "in nothing any requirement asks for", so every irrelevant verdict
already records requirement silence, whether the behaviour matters or not. The second is code
that does not do what it is meant to do: removing it changes nothing, so the verdict is
equivalent. Both were found on 2026-10-02 only through a flaky test. A synchronous route attempt
abandoned at its timeout keeps running in a background thread and can still send provider
requests and run the caller's tools. The mutants that remove its `future.cancel()` and
`cancel_futures=True` survived and were judged equivalent, correctly, because neither can stop a
running thread; the requirement only promises to stop waiting. DO-178C (6.4.4.3) and NASA's
SWE-189 resolve every structure that requirements-based tests leave unexplained into exactly one
category: a missing test, a missing requirement, extraneous or dead code, or deactivated code
kept on purpose. Formal verification measures specification coverage the same way: a mutated
system that still satisfies the specification marks a part the specification does not cover
(Chockler, Kupferman and Vardi; MutDafny).

**Decision.** A survivor ends in exactly one disposition, and none of them hides a finding:

- **pin**: the change breaks something the requirement asks for; a test pins it (as in ADR_0006);
- **unspecified**: the versions differ in what a caller could rely on (whether a request is sent, a
  tool runs, data is kept or lost, a resource is held or released, the result, an error, the cost)
  and no requirement says what it must be. The mutant leaves its fault class and opens a finding
  "silent requirement" on the contract's Completeness layer;
- **ineffective**: the code the change removes or alters does not achieve what it is meant to do,
  so the change makes no difference a caller can see (it cannot cancel, close, release or guard
  here, or nothing reaches it). The mutant leaves its fault class and opens a finding "no effect" on
  the code;
- **irrelevant**: the versions differ only in what no caller should rely on, such as formatting,
  the wording of a message or log line, or the order of internal steps; suppressed with its reason;
- **equivalent**: no input tells the versions apart and the code the change touches still does its
  job, only in another form; suppressed with its reason;
- **escalate**: as in ADR_0006, only for a Feature or Goal promise.

The verdict names the finding in one sentence: for unspecified, the behaviour no requirement
settles and what a requirement would say; for ineffective, what the code means to do and why it
does nothing. Suppressions still need the review's agreement (ADR_0006); unspecified and
ineffective do not, since they open a finding instead of closing one, and a review that disagrees
with a suppression opens the finding it names instead of pinning. The owner's delegate decides
each finding below Goal and Feature and records the disposition: `require` or `not-required` for
requirement silence, `fix` or `kept` for code with no effect. A finding stays open until its mutant
is caught or gone, or until the delegate closes it with a reason.

**Consequences.** The Fault model layer keeps answering whether the tests catch what the
requirements ask for. A new Completeness layer answers whether everything a contract's code lets
a caller observe is either required or decided as not required, and the explorer lists the
silent-requirement and no-effect findings with their decisions. The suppressions recorded under
ADR_0006 are asked again with these dispositions; the verdict's canaries gain a known silent
requirement and a known ineffective line. Escaped defects get a record of their own in the
development history: what escaped, which check should have caught it and what was added.

**Alternatives considered.** Keeping irrelevant and equivalent and reading their reasons by eye
was rejected: 117 suppressions in force hide the few that matter, as the timeout case showed. A
pre-filter of the recorded reasons by a cheaper model was rejected: models find omissions with
low recall, and a candidate filtered out would vanish without a decision. Asking the person about
every silent requirement was rejected: the person owns Goals and Features only (ADR_0006).
```
