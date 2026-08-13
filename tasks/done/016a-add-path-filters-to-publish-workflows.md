# 016 — Add path filters to publish workflows

## Goal

Both publish workflows (`publish-pypi.yml` and `publish-testpypi.yml`)
currently trigger on every push to their branch, even for docs-only or
task-file changes. After this task, only pushes that touch source code or
packaging metadata trigger a build and publish.

## Context

The project has two GitHub Actions publish workflows:

- `.github/workflows/publish-pypi.yml` triggers on push to `main`
- `.github/workflows/publish-testpypi.yml` triggers on push to `testing`

Both run lint, type check, test, build, publish, and create a GitHub
release. A README typo fix or a new task file should not trigger any of
that.

GitHub Actions supports a `paths` filter on push triggers. When `paths`
is present, the workflow only runs if at least one changed file matches
a listed pattern. This is the standard way to skip irrelevant runs.

## Files

You may create or modify only these:

- `.github/workflows/publish-pypi.yml` — modify: add `paths` filter
- `.github/workflows/publish-testpypi.yml` — modify: add `paths` filter

## Specification

Add a `paths` filter to the `on.push` trigger in both workflow files.
The filter should include these patterns:

- `src/**` (any source code change)
- `pyproject.toml` (version bump, dependency change, package metadata)
- `uv.lock` (locked dependency change)

The rest of each workflow file stays exactly as it is. Only the `on`
block changes.

The resulting trigger block should look like this in both files:

```yaml
on:
  push:
    branches: [<branch>]
    paths:
      - 'src/**'
      - 'pyproject.toml'
      - 'uv.lock'
```

Where `<branch>` is `main` for the PyPI workflow and `testing` for the
TestPyPI workflow.

## Constraints

- Do not change anything else in either workflow file. The jobs, steps,
  permissions, environment names, and action versions must remain
  identical.
- Do not add `paths-ignore` as an alternative. Use `paths` (allowlist),
  not `paths-ignore` (denylist), because new top-level directories or
  files added in the future should default to not triggering a publish.
- Do not add workflow_dispatch or any other trigger.

## Acceptance check

```bash
python -c "
import yaml, sys

for name, branch in [('publish-pypi', 'main'), ('publish-testpypi', 'testing')]:
    path = f'.github/workflows/{name}.yml'
    with open(path) as f:
        wf = yaml.safe_load(f)
    push = wf['on']['push']
    assert push.get('branches') == [branch], f'{name}: wrong branch'
    paths = push.get('paths')
    assert paths is not None, f'{name}: no paths filter'
    assert 'src/**' in paths, f'{name}: missing src/**'
    assert 'pyproject.toml' in paths, f'{name}: missing pyproject.toml'
    assert 'uv.lock' in paths, f'{name}: missing uv.lock'
    print(f'{name}: OK')

print('All checks passed')
"
```

## Out of scope

- Adding a separate CI workflow for linting/testing on PRs.
- Adding workflow_dispatch triggers.
- Changing any job steps, permissions, or action versions.
- Modifying any files outside `.github/workflows/`.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:** completed

**Files changed:**
- `.github/workflows/publish-pypi.yml` — added `paths` filter under `on.push`
- `.github/workflows/publish-testpypi.yml` — added `paths` filter under `on.push`

**Acceptance check:** passed

**Deviations:** None

**Problems:** None
