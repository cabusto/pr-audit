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
pr-audit analyze --base main --head HEAD
```

If you have not installed the console script yet, use:

```bash
python3 -m pr_audit analyze --base main --head HEAD
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
- Changed Python functions
- Cyclomatic complexity and nesting
- Deterministic review hotspots
