# PR Audit

PR Audit is a deterministic, local-first CLI for orienting yourself in a Python pull request.

It compares two Git refs, classifies the changed files, analyzes dependency and Python function changes, and writes a stable audit in:

- `audit.json`
- `audit.md`

It is meant to help a reviewer decide where to start, not to judge whether the change is good or bad.

## Install

```bash
python3 -m pip install -e .
```

## Run

```bash
pr-audit analyze
```

By default, the CLI infers the base ref from the repo's default branch
(`origin/HEAD`, `origin/main`, `main`, and a few common fallbacks).

If you need an explicit range, use:

```bash
pr-audit analyze --base main --head HEAD
```

If you have not installed the console script yet, use:

```bash
python3 -m pr_audit analyze
```

## Output

By default, files are written to the current directory.

```bash
pr-audit analyze --base main --head HEAD --output out/
```

Use `--format json`, `--format markdown`, or `--format both`.

## Help

```bash
pr-audit --help
pr-audit analyze --help
```

## GitHub Actions

- `.github/workflows/pr-audit.yml` runs on PR open, ready-for-review, synchronize, and reopen events, skipping draft PRs, then comments with `audit.md`.
- The PR workflow updates a single bot comment in place instead of creating a new comment each run.
- `.github/workflows/release.yml` publishes the package to PyPI when a GitHub Release is published.
- Set the repository secret `PYPI_API_TOKEN` before using the release workflow.

## Example

```bash
$ pr-audit analyze --base HEAD~1 --head HEAD
Analyzing HEAD~1...HEAD
✓ 2 changed files
✓ dependencies analyzed
✓ Python functions analyzed
✓ audit.json
✓ audit.md
```

The generated Markdown stays short and scannable:

```md
# PR Audit

## Scope
+3 / -1 LOC
2 files changed · 0 added · 0 deleted

Production  1
Tests       0
Config      0
Docs        0
Dependency  1
Other       0

## Dependencies
Added
+ jsonschema
```

## What it reports

- Scope metrics
- File classification
- Dependency changes from `pyproject.toml` and `requirements.txt`
- Test vs production LOC
- Changed Python functions, shown as `file.py: function`
- Cyclomatic complexity and nesting
- Deterministic review hotspots

Cyclomatic complexity is a rough count of the independent control-flow paths in a function. It increases with branches, loops, `except` blocks, boolean operators, ternaries, and `match` cases. Higher numbers mean more paths to reason about, not necessarily bad code.

Nesting depth is the deepest level of nested control flow inside the function.

## Stable metrics

These are the stable metric names used by the underlying audit model.

| Metric | Meaning |
| --- | --- |
| `pr.loc.added` | Total added LOC across the audit |
| `pr.loc.deleted` | Total deleted LOC across the audit |
| `pr.files.changed` | Total changed files |
| `pr.files.added` | Total added files |
| `pr.files.deleted` | Total deleted files |
| `dependency.runtime.added` | Runtime dependencies added in supported manifests |
| `dependency.runtime.removed` | Runtime dependencies removed in supported manifests |
| `dependency.runtime.changed` | Runtime dependency version changes |
| `tests.files.changed` | Changed files classified as tests |
| `tests.files.added` | Added files classified as tests |
| `tests.loc.added` | Added LOC in test files |
| `complexity.cyclomatic.max.before` | Highest cyclomatic complexity before the change |
| `complexity.cyclomatic.max.after` | Highest cyclomatic complexity after the change |
| `complexity.nesting.max.before` | Highest nesting depth before the change |
| `complexity.nesting.max.after` | Highest nesting depth after the change |
