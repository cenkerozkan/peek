# 010 — GitHub Actions workflow for PyPI publishing

## Goal

A GitHub Actions workflow that automatically builds and publishes `peek-db`
to real PyPI whenever code is pushed to the `main` branch.

## Context

This is the production counterpart of task 009 (TestPyPI on the `testing`
branch). The release flow is: `dev` → `testing` (TestPyPI) → `main` (PyPI).
By the time code reaches `main`, it has been tested on TestPyPI and approved
via PR review.

The structure is nearly identical to the TestPyPI workflow from task 009,
with two differences: it triggers on `main` instead of `testing`, and it
publishes to real PyPI instead of TestPyPI.

Publishing uses PyPI trusted publishing (OIDC), same as task 009. The owner
has configured the trusted publisher on PyPI to trust this workflow file
and the `pypi` GitHub environment.

Important: the existing `ci.yml` also triggers on push to `main`. That is
fine — CI and the publish workflow run as separate workflows in parallel.
CI gives fast lint/test feedback; this workflow gates publishing on its own
test run.

## Files

You may create or modify only these:

- `.github/workflows/publish-pypi.yml` — new: the PyPI publish workflow

## Specification

### `.github/workflows/publish-pypi.yml`

Create a new workflow with two jobs: `build` and `publish`. The structure
mirrors the TestPyPI workflow from task 009.

**Trigger:** push to the `main` branch only.

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
on `ubuntu-latest`. Uses the GitHub environment named `pypi`. Requires
these permissions: `id-token: write` (for OIDC token request) and
`contents: read`.

Steps:
- Download the `distribution-packages` artifact into `dist/` using
  `actions/download-artifact@v4`.
- Publish to PyPI using `pypa/gh-action-pypi-publish@release/v1`. Unlike
  the TestPyPI workflow, do not set `repository-url` — the action defaults
  to real PyPI.

## Constraints

- Do not store any API tokens or passwords in the workflow. Trusted
  publishing (OIDC) handles authentication.
- The `publish` job must use `environment: pypi` — this is what PyPI
  matches against the trusted publisher configuration.
- The `build` job must run the full test suite before building.
- Do not modify `ci.yml` or the TestPyPI workflow — this task adds one
  new file only.
- Use the same uv setup pattern as the existing `ci.yml`.

## Acceptance check

```bash
python -c "
import yaml, sys
wf = yaml.safe_load(open('.github/workflows/publish-pypi.yml'))
trigger = wf['on']['push']['branches']
assert 'main' in trigger, 'missing main trigger'
jobs = list(wf['jobs'].keys())
assert 'build' in jobs, 'missing build job'
assert 'publish' in jobs, 'missing publish job'
pub = wf['jobs']['publish']
assert pub.get('needs') == 'build' or 'build' in pub.get('needs', []), 'publish must depend on build'
assert pub.get('environment', {}).get('name', pub.get('environment')) == 'pypi', 'wrong environment'
perms = pub.get('permissions', {})
assert perms.get('id-token') == 'write', 'missing id-token permission'
steps = pub.get('steps', [])
pub_step = [s for s in steps if 'pypa/gh-action-pypi-publish' in str(s.get('uses', ''))]
assert pub_step, 'missing pypi publish action'
assert 'test.pypi' not in str(pub_step[0].get('with', {})), 'must target real PyPI, not TestPyPI'
print('All checks passed')
"
```

## Out of scope

- TestPyPI workflow (done in task 009).
- Version bumping strategy or automation.
- Branch protection rules or GitHub environment configuration.
- Changes to any Python code or existing workflows.

---

## Outcome

**Status:** done

**Files changed:**
- .github/workflows/publish-pypi.yml (new)

**Acceptance check:** passed

**Deviations:** none

**Problems:** none
