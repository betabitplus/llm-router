# Keep the monitor's history, hold every exception to a reason and a date, mark loosened metric bases and freeze each release

```{adr} Keep the monitor's history, hold every exception to a reason and a date, mark loosened metric bases and freeze each release
:id: ADR_0009
:status: accepted
:decision_date: 2026-10-03

**Context.** A monitor page compares its run only with the previous one (Changes): how a number
moved over weeks stays unseen, and a slow creep looks like no change. Exceptions live apart, each in
its own form: survivor verdicts and decisions, code exemptions, the comments the tools read
(`# noqa`, `# pragma: no cover`, `pytest.skip`), a pin the oracle rule spares; none says until when
it holds, and their number can grow unseen. A number improves because the product did, or because
what it is measured against was loosened (Goodhart's law): a held number raised, an exception added,
a required path or fault class dropped from a profile, a rule ignored; done in the same commit as
the code, a reviewer sees only the better number. What was open when a version shipped is lost when
the next run redraws the pages. Coverage counts lines only, and the lines a branch adds are not
shown apart. Mature practice: SonarQube's activity history and its new-code period; coverage.py's
branch measurement and diff-cover for changed lines; suppressions that expire (Trivy's
`expired_at`, OWASP dependency-check's `until`); counts that may only fall (ESLint's bulk
suppressions, betterer); MISRA Compliance:2020 deviation records with a rationale each;
`git describe` for naming a build; git's union merge for an append-only log.

**Decision.**

- History: every retained run adds one row to `.ai-bridge/monitor-history.jsonl`, committed: its
  run, its commit and whether its inputs were exactly that commit's files, and the numbers its pages
  show (failing marks per layer of the Health Map and the Code map, failing items per kind of the
  Explorer, exceptions per type, line, branch and new-line coverage, bases loosened with the code).
  A run drawn again replaces its own row; git merges the file as a union, so rows two clones add
  both keep. Each number shows its trend from these rows; what fails rising is red, falling green.
  The runs still retained when the history began seed it, their commits marked as not recorded.
- Exceptions: an exception is a recorded decision that something which would count as a failure
  does not. The registry reads every one where it lives, with no second copy: survivors a model
  judged out (equivalent, irrelevant) or a person or the delegate decided out, findings closed (not
  required, kept), the Code map's exemptions, the comments in the product that tell a tool to look
  away (`# noqa`, `# type: ignore`, `# pyright:`, `# ty: ignore`, `# pragma: no cover`,
  `# pragma: no branch`, `# pragma: no mutate`, `# nosec`), the places in the tests that skip or
  expect a failure, the pins the oracle rule spares and the imports an architecture contract lets
  through. Each names what it excuses, who decided, why, when, and until when it holds:
  - a verdict a model gave holds while its question is unchanged: it counts only for the exact
    question it answered, and a change of the code, the requirement or the tests asks again;
  - every other exception holds for 90 days from its decision, then fails until it is confirmed
    with a new date or removed;
  - its reason is its record's own, the text after the comment's codes (`# noqa: E402 - why`), or
    an entry in `.ai-bridge/exception-records.json`, which carries the decision date too; an
    exception without a reason fails, and so does an entry that excuses nothing any more;
  - per type, the number of exceptions may only fall: `.ai-bridge/exceptions-baseline.json` drops
    with them, and a rise fails the gate until a reason recorded there accepts it.
  Suppressions in test code are outside: they excuse nothing the monitor counts, since tests are
  neither measured for coverage nor type-checked; so are the project-wide rule settings, which are
  the coding standard itself, not exceptions to it.
- Metric bases: the files a number is measured against — the held baselines, the exception records
  and exemptions, the survivor verdicts and decisions, the verification profiles, the tools' tables
  in `pyproject.toml` and the CI workflow. Every commit since the merge base with main, and the
  uncommitted change, that changes a base is listed with how: looser (a held number rose, an
  exception was added or renewed, a profile drops a criterion or a required fault class or asks a
  criterion for fewer paths, a tool excludes more), tighter, or changed when the reading cannot
  tell; a criterion or fault class that only moves to another contract is neither. One that loosens
  a base together with the product's code or tests fails in the Explorer; the gate does not.
- Releases: the first retained run of a commit `git describe` names as a release tag, when its
  inputs are that commit's files, or any run on `--release-snapshot`, freezes
  `.ai-bridge/release-snapshots/<name>.json`: the run, the commit, the numbers, every item that
  failed and every exception in force. A snapshot is never rewritten. The Releases page lists them;
  each opens what was open then in the Explorer's own list, with what became of each item since.
- Coverage: the retained run measures branches (`--cov-branch`). The Code map's Unexecuted lines
  layer adds a Branches view and a New lines view (the lines the branch changes against its merge
  base with main, as diff-cover reads them), and its table gives every function and module its
  line and branch coverage and how many of its new lines its tests run; the branches no test takes
  join the numbers that may only fall.

**Consequences.** The map pages carry the trend of each number; the Explorer lists every exception
under one kind, failing ones first, and every base change; the Releases page keeps what was open at
each snapshot. The registry's first reading found 19 exceptions in and beside the code without a
reason, which the delegate recorded after checking each, among them 1 pin the oracle rule spares.
The 39 decisions on survivors and findings and the 19 records in the code fall due between
30 December 2026 and 1 January 2027. The pre-push pytest and
`pyproject.toml` stay without branch measurement until the campaign's next refresh, since editing
`pyproject.toml` makes the whole campaign stale; the chain and CI pass `--cov-branch`. A release tag
on main gets its snapshot from the monitor's first run at that commit, once the monitor is merged;
until then a snapshot taken on request is named by its distance from the last release.

**Alternatives considered.** A metrics server (SonarQube) was rejected for a committed file the
static portal reads; its activity graph and new-code period are adopted. A separate registry file
copying every exception was rejected: a copy drifts from the verdicts and comments that actually
excuse. Calendar review of a model's verdict was rejected: asking an unchanged question again
repeats its answer and costs model calls. Lapsing an overdue exception at once (Trivy) was deferred:
a contract's verdict would then change with the calendar without any change of its inputs; the
registry fails on it instead, so the lapse is seen and decided. diff-cover's rule for changed lines
is adopted, while the monitor computes the lines itself, since it needs them per function.
```
