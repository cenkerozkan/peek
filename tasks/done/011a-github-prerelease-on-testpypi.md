# 011a — Automatic GitHub pre-release after TestPyPI publish

## Goal

When the TestPyPI publish workflow (`.github/workflows/publish-testpypi.yml`)
successfully publishes a new version, it creates a Git tag and a GitHub
pre-release so the repo's Releases page tracks test publishes too.

## Context

Task 011 adds a GitHub Release to the PyPI workflow (`main` branch). This
is the TestPyPI counterpart: when a version is published to TestPyPI from
the `testing` branch, a GitHub pre-release is created so the team can see
what was published and when.

The release is marked as a **pre-release** (not a full release) to
distinguish it from production PyPI releases. The tag format uses an
`rc` suffix to avoid colliding with the production tag that task 011
creates — e.g. `v0.2.0-rc` for a TestPyPI publish of version `0.2.0`.

The version is defined in `pyproject.toml` (the `version` field). The
workflow must read it from there to create the correct tag.

## Files

You may create or modify only these:

- `.github/workflows/publish-testpypi.yml` — modify: add a `release` job
  after the `publish` job

## Specification

### `.github/workflows/publish-testpypi.yml`

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
3. Create a GitHub pre-release using the `softprops/action-gh-release`
   action (or `gh release create` via the GitHub CLI, which is
   pre-installed on `ubuntu-latest` runners). The release should:
   - Use the tag `v$VERSION-rc` (e.g. `v0.2.0-rc`).
   - Target the current commit (the one that triggered the workflow).
   - Use GitHub's auto-generated release notes (`generate_release_notes:
     true` for the action, or `--generate-notes` for the CLI).
   - Be marked as a **pre-release** (not a full release).
   - Attach the built distribution files (sdist and wheel) from the
     `distribution-packages` artifact as release assets.

The `release` job must download the `distribution-packages` artifact
(same pattern as the `publish` job) so it can attach the files to the
GitHub Release.

## Constraints

- The `release` job must depend on `publish`, not on `build`. A GitHub
  pre-release must never be created if the TestPyPI upload failed.
- Do not modify the existing `build` or `publish` jobs.
- Do not modify any other workflow files.
- The tag format must be `v` + version + `-rc` (e.g. `v0.2.0-rc`) to
  avoid colliding with production release tags from task 011.
- The release must be marked as a pre-release.
- Do not hardcode the version — it must be read from `pyproject.toml`
  at workflow runtime.

## Acceptance check

```bash
python -c "
import yaml
wf = yaml.safe_load(open('.github/workflows/publish-testpypi.yml'))
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

- PyPI workflow changes (that is task 011).
- Version bumping strategy or automation.
- Changes to any Python code.

---

## Outcome

**Status:** done

**Files changed:**
- .github/workflows/publish-testpypi.yml (modified)

**Acceptance check:** passed — All checks passed

**Deviations:** none

**Problems:** none
