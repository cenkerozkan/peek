# 009 — GitHub Actions workflow for TestPyPI publishing

## Goal

A GitHub Actions workflow that automatically builds and publishes `peek-db`
to TestPyPI whenever code is pushed to the `testing` branch. Also widen the
existing CI trigger to cover `dev` and `testing` branches.

## Context

The project uses a three-branch release flow: `dev` for active work,
`testing` for pre-release validation, and `main` for production releases.
Merging into `testing` should automatically publish the current version to
TestPyPI so the team can install and verify the package before promoting to
real PyPI.

The project already has a CI workflow at `.github/workflows/ci.yml` that
runs lint, type-check, tests, wheel build, and smoke tests. It currently
triggers on `push: [main]` and `pull_request`. It needs to also cover the
`dev` and `testing` branches so CI runs everywhere.

Publishing uses PyPI trusted publishing (OIDC). This means no API tokens
are stored in GitHub secrets. The workflow requests an OIDC token from
GitHub, and PyPI verifies it against the trusted publisher configuration.
The owner has already configured the trusted publisher on TestPyPI (or will
before the first run).

The build system is hatchling. `uv build` produces both sdist and wheel
in `dist/`.

## Files

You may create or modify only these:

- `.github/workflows/publish-testpypi.yml` — new: the TestPyPI publish workflow
- `.github/workflows/ci.yml` — modify: add `dev` and `testing` to push branch list

## Specification

### `.github/workflows/ci.yml`

Add `dev` and `testing` to the `push.branches` list alongside `main`. Do
not change anything else in this file.

### `.github/workflows/publish-testpypi.yml`

Create a new workflow with two jobs: `build` and `publish`.

**Trigger:** push to the `testing` branch only.

**Job 1 — `build`:** Runs on `ubuntu-latest`. Steps:
- Check out the repo.
- Install uv (using `astral-sh/setup-uv@v5` with Python 3.13 and caching
  enabled, same as the existing CI workflow).
- Run the full lint/type-check/test suite (same commands as `ci.yml`:
  `uv run ruff check src tests`, `uv run isort --check-only src tests`,
  `uv run ty check src tests`, `uv run pytest -q`).
- Build the distribution with `uv build`.
- Upload the contents of `dist/` as a GitHub Actions artifact named
  `distribution-packages` using `actions/upload-artifact@v4`.

**Job 2 — `publish`:** Runs after `build` succeeds (`needs: build`). Runs
on `ubuntu-latest`. Uses the GitHub environment named `testpypi`. Requires
these permissions: `id-token: write` (for OIDC token request) and
`contents: read`.

Steps:
- Download the `distribution-packages` artifact into `dist/` using
  `actions/download-artifact@v4`.
- Publish to TestPyPI using `pypa/gh-action-pypi-publish@release/v1` with
  the repository URL set to `https://test.pypi.org/legacy/`.

## Constraints

- Do not store any API tokens or passwords in the workflow. Trusted
  publishing (OIDC) handles authentication.
- The `publish` job must use `environment: testpypi` — this is what PyPI
  matches against the trusted publisher configuration.
- The `build` job must run the full test suite before building. A broken
  package must never reach TestPyPI.
- Do not change the existing CI workflow behavior — only add branches to
  its trigger.
- Use the same uv setup pattern as the existing `ci.yml` (astral-sh/setup-uv
  v5, Python 3.13, caching enabled).

## Acceptance check

```bash
python -c "
import yaml, sys
wf = yaml.safe_load(open('.github/workflows/publish-testpypi.yml'))
trigger = wf['on']['push']['branches']
assert 'testing' in trigger, 'missing testing trigger'
jobs = list(wf['jobs'].keys())
assert 'build' in jobs, 'missing build job'
assert 'publish' in jobs, 'missing publish job'
pub = wf['jobs']['publish']
assert pub.get('needs') == 'build' or 'build' in pub.get('needs', []), 'publish must depend on build'
assert pub.get('environment', {}).get('name', pub.get('environment')) == 'testpypi', 'wrong environment'
perms = pub.get('permissions', {})
assert perms.get('id-token') == 'write', 'missing id-token permission'
print('All checks passed')
"
```

Also verify that ci.yml now includes dev and testing:

```bash
grep -E "dev|testing" .github/workflows/ci.yml
```

This should show both branch names in the push trigger.

## Out of scope

- Real PyPI publishing (that is task 010).
- Version bumping strategy or automation.
- Branch protection rules or GitHub environment configuration (done manually
  by the owner).
- Changes to any Python code.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:**

**Files changed:**

**Acceptance check:**

**Deviations:**

**Problems:**
