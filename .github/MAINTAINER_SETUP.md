# Maintainer Setup

Use this file for one-time GitHub and repository administration. It is for
repository maintainers, not for ordinary local contributor bootstrap. Use
[SETUP.md](../SETUP.md) for local environment setup and
[CONTRIBUTING.md](../CONTRIBUTING.md) for the normal development workflow.

This playbook was rechecked against GitHub Docs on April 13, 2026. It matches
this repository's current release flow: `dev` is the default integration
branch, `main` is the protected release branch, and GitHub Actions uses
`PAT_TOKEN` to publish the release bump commit, tag, and GitHub Release.

## Target state

- `dev` is the default branch and normal PR target.
- `main` is the protected release branch.
- CI runs for pushes and pull requests on `dev` and `main`.
- A push to `main` triggers the release workflow.
- The release workflow bumps version and changelog, pushes the bump commit and
  tag, creates the GitHub Release, and fast-forwards `dev` to `main`.

## 1. Set the default branch

On GitHub, open the repository and go to `Settings -> Branches -> Default branch`, then set the default branch to `dev`.

Keep `main` non-default so ordinary work lands on `dev`.

## 2. Create the release token

Prefer a fine-grained personal access token.

On GitHub, go to `Profile -> Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens -> Generate new token`, then use:

- Resource owner: the owner of this repository
- Repository access: `Only select repositories` -> this repository
- Repository permissions: `Contents: Read and write`
- Expiration: use a finite lifetime unless policy requires something else

If the organization requires approval for fine-grained tokens, wait until the
token is approved before using it.

The current workflow does not use a GitHub App. A PAT can only do what its
owner can already do, so the token owner must already have the repository
access needed to push the release bump commit, push tags, and create releases.

## 3. Store `PAT_TOKEN`

On GitHub, go to `Settings -> Secrets and variables -> Actions -> New repository secret`, then create:

- Name: `PAT_TOKEN`
- Value: the fine-grained token created above

Keep GitHub Actions enabled for the repository. The expected workflows are
`ci.yml`, `release.yml`, and the optional manual `build-ci-image.yml`.

## 4. Protect `main`

Prefer `Settings -> Rules -> Rulesets -> New branch ruleset` and target
`main`.

Keep these rules enabled:

- require a pull request before merging
- require status checks before merging
- require branches to be up to date before merging
- block force pushes
- block branch deletion

Keep the release path compatible with the `PAT_TOKEN` owner. If your ruleset
would block the workflow's push back to `main`, either give the token owner a
valid bypass path through the ruleset model or move the release automation to a
GitHub App.

If you also protect `dev`, do not break the documented contributor flow in
[CONTRIBUTING.md](../CONTRIBUTING.md), which relies on local fast-forward merges
back into `dev`.

## 5. Configure required checks

Required checks must match the current job names from [`workflows/ci.yml`](workflows/ci.yml).
As of April 13, 2026, keep `main` protection aligned with:

- `Lint, typecheck, test`
- `E2E Slice (behavior-session)`
- `E2E Slice (behavior-routing)`
- `E2E Slice (behavior-resilience)`
- `E2E Slice (contract-tools)`
- `E2E Slice (contract-async)`
- `E2E Slice (contract-video)`

If CI job names change, update the ruleset at the same time.

## 6. Verify the setup

Check the full path once after setup:

1. Confirm `dev` is the default branch.
2. Open a PR to `main` and confirm the required checks are enforced.
3. Merge or push to `main` and confirm the `Release` workflow starts.
4. Confirm the workflow can:
   - run `cz bump --changelog --yes`
   - push the bump commit to `main`
   - push the tag
   - create the GitHub Release
   - fast-forward `dev` to `main`

If `dev` has diverged from `main`, the final fast-forward step fails by design.
