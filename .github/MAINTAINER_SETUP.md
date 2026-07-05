# Maintainer Setup

A repository generated from `py-lib-starter` may be either managed or standalone.
Ordinary contributor bootstrap is documented in [SETUP.md](../SETUP.md), and the
normal development workflow is in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Repository Mode

- A managed downstream is listed in the starter downstream registry and
  participates in fleet operations. Registry entries with `auto_sync: true`
  receive starter release dispatches.
- A standalone repository is generated from the same template but is absent from
  the registry. It keeps its own release and manual template-sync workflows
  without starter fleet dispatches.
- Template origin, GitHub App installation, or local discovery does not imply
  managed membership.

## Platform Setup

From an up-to-date `py-lib-starter` checkout, create or resume a managed
repository with:

```bash
uv run py-lib-create-managed-repository <repository-name>
```

For an existing standalone repository, configure GitHub App credentials, the
standard `main` ruleset, and repository checks without registry mutation:

```bash
scripts/platform/setup_github_app_repository.sh OWNER/REPOSITORY
```

Do not add a standalone repository to the downstream registry unless it is
intentionally joining the managed fleet and automatic starter synchronization.

## Target State

- `dev` is the default branch and normal pull-request target.
- `main` is the protected release branch.
- Pull requests to `main` come only from this repository's `dev` branch.
- Full CI runs on `dev` pushes and pull requests to `dev` or `main`.
- Release and template-sync commits use `betabitplus-py-lib-automation`.
- Public and private repositories use the same workflow and credential topology.

## Automation Identity

`betabitplus-py-lib-automation` must remain installed in `All repositories` mode
with:

- `Contents: Read and write`
- `Pull requests: Read and write`
- `Workflows: Read and write`

Repository Actions values are:

```text
Variable: PY_LIB_AUTOMATION_APP_ID
Variable: PY_LIB_AUTOMATION_CLIENT_ID
Secret:   PY_LIB_AUTOMATION_PRIVATE_KEY
```

Never commit the private key or add PAT fallback credentials. Generated local
reusable CI workflows create scoped App tokens only for trusted operations; fork
pull requests do not receive App credentials or repository secrets.

## Protection and Verification

`main` requires pull requests, an up-to-date branch, squash merge, and only
`ci/merge-gate`; force pushes and deletion remain blocked. Only the automation
App receives the narrow release and synchronization bypass.

For missing credentials, installation access, workflow permissions, ruleset
rejection, key rotation, repository transfer, or visibility changes, rerun the
appropriate setup command or follow the authoritative policy:

```text
https://github.com/betabitplus/py-lib-starter/blob/dev/docs/platform-ops/github-app-automation-policy.md
```
