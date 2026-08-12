# 011 — Automatic GitHub Release after PyPI publish

## Goal

When the PyPI publish workflow (`.github/workflows/publish-pypi.yml`)
successfully publishes a new version, it also creates a Git tag and a
GitHub Release so the repo's Releases page reflects every published version.

## Context

The PyPI publish workflow (task 010) builds and uploads `peek-db` to real
PyPI on every push to `main`. It does not currently tag the commit or
create a GitHub Release. Users and contributors expect a repo's Releases
page to list each published version with a tag like `v0.1.0`.

The version is defined in `pyproject.toml` (the `version` field). The
workflow must read it from there to create the correct tag. The version is
bumped manually before merging to `main` (decision #23), so by the time
the workflow runs, `pyproject.toml` already contains the new version.

This step must only run after a successful PyPI publish — a failed upload
must not create a release.

## Files

You may create or modify only these:

- `.github/workflows/publish-pypi.yml` — modify: add a `release` job
  after the `publish` job

## Specification

### `.github/workflows/publish-pypi.yml`

Add a third job named `release` that runs after `publish` succeeds
(`needs: publish`).

**Job 3 — `release`:** Runs on `ubuntu-latest`. Requires
`contents: write` permission (to create tags and releases).

Steps:

1. Check out the repo (needed to read `pyproject.toml`).
2. Extract the version string from `pyproject.toml`. Use a shell command
   to parse the version — for example, grep or a small Python one-liner
   that reads the `version` field. Store it in a step output or
   environment variable (e.g. `VERSION`). The extracted version must not
   include quotes or whitespace.
3. Create a GitHub Release using the `softprops/action-gh-release` action
   (or `gh release create` via the GitHub CLI, which is pre-installed on
   `ubuntu-latest` runners). The release should:
   - Use the tag `v$VERSION` (e.g. `v0.1.0`).
   - Target the current commit (the one that triggered the workflow).
   - Use GitHub's auto-generated release notes (`generate_release_notes:
     true` for the action, or `--generate-notes` for the CLI).
   - Be marked as a regular release, not a draft or pre-release.
   - Attach the built distribution files (sdist and wheel) from the
     `distribution-packages` artifact as release assets.

The `release` job must download the `distribution-packages` artifact
(same pattern as the `publish` job) so it can attach the files to the
GitHub Release.

## Constraints

- The `release` job must depend on `publish`, not on `build`. A GitHub
  Release must never be created if the PyPI upload failed.
- Do not modify the existing `build` or `publish` jobs.
- Do not modify any other workflow files.
- The tag format must be `v` followed by the version (e.g. `v0.1.0`),
  not the bare version number.
- Do not hardcode the version — it must be read from `pyproject.toml`
  at workflow runtime.

## Acceptance check

```bash
python -c "
import yaml
wf = yaml.safe_load(open('.github/workflows/publish-pypi.yml'))
jobs = list(wf['jobs'].keys())
assert 'release' in jobs, 'missing release job'
rel = wf['jobs']['release']
needs = rel.get('needs')
if isinstance(needs, str):
    assert needs == 'publish', 'release must depend on publish'
else:
    assert 'publish' in needs, 'release must depend on publish'
perms = rel.get('permissions', {})
assert perms.get('contents') == 'write', 'missing contents:write permission'
print('All checks passed')
"
```

## Out of scope

- TestPyPI workflow changes (no releases for dry runs).
- Changelog file generation or conventional-commit tooling.
- Version bump automation.
- Changes to any Python code.

---

## Outcome

<!-- Filled in by the coding agent before moving this file to tasks/done/ -->

**Status:**

**Files changed:**

**Acceptance check:**

**Deviations:**

**Problems:**
