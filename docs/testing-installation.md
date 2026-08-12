# Testing installation

How to install and test `peek-db` from TestPyPI before a production release,
and how to verify the installed package works.

## Installing from TestPyPI

TestPyPI is a separate package index that mirrors the real PyPI interface.
Every push to the `testing` branch publishes the current version there, so
you can try a release candidate before it reaches production PyPI.

### With uv

```sh
uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ peek-db
```

The `--extra-index-url` fallback to real PyPI is required because peek-db's
dependencies (click, sqlalchemy, etc.) are not on TestPyPI.

To install with a database driver extra:

```sh
uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ 'peek-db[postgres]'
```

### With pip

```sh
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ peek-db
```

### With pipx

```sh
pipx install --index-url https://test.pypi.org/simple/ peek-db --pip-args='--extra-index-url https://pypi.org/simple/'
```

### Upgrading an existing TestPyPI install

If you already have a previous TestPyPI version installed:

```sh
uv pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ peek-db
```

## Installing from production PyPI

After a merge to `main`, the package is published to real PyPI.

```sh
uv tool install peek-db
```

Or with pip / pipx:

```sh
pip install peek-db
pipx install peek-db
```

To upgrade:

```sh
uv tool upgrade peek-db
pip install --upgrade peek-db
pipx upgrade peek-db
```

## Verifying the installation

### Check the version

```sh
peek --version
```

This should print the version from `pyproject.toml` (e.g. `0.1.1`). If it
prints `0.0.0+unknown`, the package metadata was not installed correctly.

### Check that the server starts

```sh
peek
```

A healthy server prints nothing and waits on stdin (it speaks MCP over
stdio). Press `Ctrl+C` to stop it.

### Run the CLI

```sh
peek --help
peek db --help
```

These should list the available commands (`init`, `db add`, `db remove`,
`db list`).

### Initialize a project config

```sh
mkdir /tmp/peek-test && cd /tmp/peek-test
peek init
```

This creates a `.peek/` directory with a `databases.toml` template.

### Register a test database

The fastest way to test a real connection is with an in-memory SQLite
database (no driver install needed):

```sh
peek db add demo sqlite:///
```

Then verify it was registered:

```sh
peek db list
```

### Connect from an editor

Once registered, add `peek` to your editor to verify the full MCP flow.
See the [main README](../README.md#add-peek-to-your-editor) for
editor-specific setup (Claude Code, Cursor, VS Code).

For a quick test with Claude Code:

```sh
claude mcp add peek -- uvx --from peek-db peek
```

Or, to test the locally installed version instead of fetching from PyPI:

```sh
claude mcp add peek -- peek
```

Open a chat and ask something like "list my databases" -- the agent should
call `list_databases` and return the aliases you registered.

## Release workflow summary

| Branch    | Publishes to | Tag format    | Release type |
| --------- | ------------ | ------------- | ------------ |
| `testing` | TestPyPI     | `v0.1.1-rc`  | Pre-release  |
| `main`    | PyPI         | `v0.1.1`     | Full release |

Both workflows also create a GitHub Release with auto-generated notes and
the built distribution files (wheel + sdist) attached as assets.

## Troubleshooting

### "No matching distribution found" on TestPyPI

TestPyPI sometimes has availability delays. Wait a minute after the
workflow completes and retry. Also ensure you included the
`--extra-index-url https://pypi.org/simple/` flag -- without it, pip
cannot resolve peek-db's dependencies.

### Version conflict when upgrading

If uv or pip refuses to upgrade because the version number hasn't changed,
the same version was already published. TestPyPI does not allow overwriting
an existing version. Bump the version in `pyproject.toml` before pushing
to `testing`.

### "peek: command not found" after install

The install directory may not be on your `PATH`. With `uv tool install`,
run `uv tool dir` to find where tools are installed and add that to your
shell profile. With `pipx`, run `pipx ensurepath`.
